# crud_manager.py

from sqlalchemy import text
import pandas as pd
from datetime import datetime
import logging
from typing import Optional, Dict, Any
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

class CRUDManager:
    """Unified CRUD operations manager for both personal and training data."""
    
    @staticmethod
    def validate_member_data(data: Dict[str, Any]) -> bool:
        """Validate member data before database operations."""
        required_fields = ['first_name', 'last_name', 'email', 'phone_number']
        return all(data.get(field) for field in required_fields)

    @staticmethod
    def validate_training_data(data: Dict[str, Any]) -> bool:
        """Validate training data before database operations."""
        required_fields = ['userid', 'courseid', 'completion_date']
        return all(data.get(field) for field in required_fields)

    @staticmethod
    def add_member(data: Dict[str, Any]) -> int:
        """Add new member with validation."""
        if not CRUDManager.validate_member_data(data):
            raise ValueError("Missing required member data fields")

        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO personal_data (
                        first_name, last_name, email, phone_number,
                        ice_first_name, ice_last_name, ice_phone_number, 
                        eligibility
                    ) VALUES (
                        :first_name, :last_name, :email, :phone_number,
                        :ice_first_name, :ice_last_name, :ice_phone_number,
                        'Ineligible'
                    ) RETURNING id
                """)
                result = conn.execute(query, data)
                member_id = result.scalar()
                conn.commit()
                return member_id
        except Exception as e:
            logger.error(f"Error adding member: {str(e)}")
            raise

    @staticmethod
    def update_member(member_id: int, data: Dict[str, Any]) -> bool:
        """Update existing member."""
        if not CRUDManager.validate_member_data(data):
            raise ValueError("Missing required member data fields")

        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("""
                    UPDATE personal_data 
                    SET first_name = :first_name,
                        last_name = :last_name,
                        email = :email,
                        phone_number = :phone_number,
                        ice_first_name = :ice_first_name,
                        ice_last_name = :ice_last_name,
                        ice_phone_number = :ice_phone_number
                    WHERE id = :id
                """)
                data['id'] = member_id
                result = conn.execute(query, data)
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating member: {str(e)}")
            raise

    @staticmethod
    def delete_member(member_id: int) -> bool:
        """Delete member and associated training records."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # First delete training records
                delete_training = text("""
                    DELETE FROM training_status_data 
                    WHERE userid = :member_id
                """)
                conn.execute(delete_training, {'member_id': member_id})
                
                # Then delete member
                delete_member = text("""
                    DELETE FROM personal_data 
                    WHERE id = :member_id
                """)
                result = conn.execute(delete_member, {'member_id': member_id})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting member: {str(e)}")
            raise

    @staticmethod
    def add_training(data: Dict[str, Any]) -> int:
        """Add new training record with validation."""
        if not CRUDManager.validate_training_data(data):
            raise ValueError("Missing required training data fields")

        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO training_status_data (
                        userid, courseid, completion_date
                    ) VALUES (
                        :userid, :courseid, :completion_date
                    ) RETURNING id
                """)
                result = conn.execute(query, data)
                training_id = result.scalar()
                conn.commit()
                
                # Update eligibility after adding training
                CRUDManager._update_member_eligibility(conn, data['userid'])
                return training_id
        except Exception as e:
            logger.error(f"Error adding training record: {str(e)}")
            raise

    @staticmethod
    def update_training(training_id: int, data: Dict[str, Any]) -> bool:
        """Update existing training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # Get userid for eligibility update
                get_userid = text("SELECT userid FROM training_status_data WHERE id = :id")
                userid = conn.execute(get_userid, {'id': training_id}).scalar()
                
                # Update training record
                query = text("""
                    UPDATE training_status_data 
                    SET completion_date = :completion_date
                    WHERE id = :id
                """)
                data['id'] = training_id
                result = conn.execute(query, data)
                
                # Update eligibility
                if userid:
                    CRUDManager._update_member_eligibility(conn, userid)
                
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating training record: {str(e)}")
            raise

    @staticmethod
    def delete_training(training_id: int) -> bool:
        """Delete training record and update eligibility."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # Get userid for eligibility update
                get_userid = text("SELECT userid FROM training_status_data WHERE id = :id")
                userid = conn.execute(get_userid, {'id': training_id}).scalar()
                
                # Delete training record
                query = text("DELETE FROM training_status_data WHERE id = :id")
                result = conn.execute(query, {'id': training_id})
                
                # Update eligibility
                if userid:
                    CRUDManager._update_member_eligibility(conn, userid)
                
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting training record: {str(e)}")
            raise

    @staticmethod
    def _update_member_eligibility(conn, userid: int) -> None:
        """Update member eligibility based on training status."""
        query = text("""
            UPDATE personal_data 
            SET eligibility = CASE 
                WHEN EXISTS (
                    SELECT 1 
                    FROM training_status_data t 
                    WHERE t.userid = personal_data.id 
                    AND status = 'Overdue'
                ) THEN 'Ineligible'
                WHEN NOT EXISTS (
                    SELECT 1 
                    FROM training_status_data t 
                    WHERE t.userid = personal_data.id
                ) THEN 'Ineligible'
                ELSE 'Eligible'
            END
            WHERE id = :userid
        """)
        conn.execute(query, {'userid': userid})