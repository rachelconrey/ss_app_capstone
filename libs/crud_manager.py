from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any, List, Tuple
import logging
from libs.database.db_engine import DatabaseConfig
from passlib.hash import pbkdf2_sha256

logger = logging.getLogger(__name__)

class CRUDManager:
    """Unified CRUD operations manager with improved error handling and transactions."""
    
    class ValidationError(Exception):
        """Custom exception for validation errors."""
        pass

    @staticmethod
    def _validate_data(data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate required fields in data."""
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise CRUDManager.ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

    @staticmethod
    def _execute_transaction(queries: List[Tuple[str, Dict[str, Any]]]) -> Any:
        """Execute multiple queries in a single transaction."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:  # Automatically manages transactions
                result = None
                for query_str, params in queries:
                    result = conn.execute(text(query_str), params)
                return result
        except SQLAlchemyError as e:
            logger.error(f"Database error in transaction: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in transaction: {str(e)}")
            raise

    # Member Operations
    @staticmethod
    def add_member(member_data: Dict[str, Any]) -> int:
        """Add new member with proper validation and role assignment."""
        required_fields = ['first_name', 'last_name', 'email']
        CRUDManager._validate_data(member_data, required_fields)

        # Generate userid from name
        userid = f"{member_data['first_name'][0].lower()}{member_data['last_name'].lower()}"
        
        default_password = "default_password"  # You might want to generate this randomly
        hashed_password = pbkdf2_sha256.hash(default_password)
        
        queries = [
            # Create login record
            ("""
                INSERT INTO login_data (userid, password, role, date_created)
                VALUES (:userid, 'default_password', 
                    (SELECT role FROM roles_data LIMIT 1),
                    CURRENT_TIMESTAMP)
            """, {'userid': userid}),
            
            # Create personal record
            ("""
                INSERT INTO personal_data (
                    userid, first_name, last_name, email, phone_number,
                    ice_first_name, ice_last_name, ice_phone_number, eligibility
                ) VALUES (
                    :userid, :first_name, :last_name, :email, :phone_number,
                    :ice_first_name, :ice_last_name, :ice_phone_number, 'Ineligible'
                ) RETURNING id
            """, {
                **member_data,
                'userid': userid,
                'phone_number': member_data.get('phone_number', ''),
                'ice_first_name': member_data.get('ice_first_name', ''),
                'ice_last_name': member_data.get('ice_last_name', ''),
                'ice_phone_number': member_data.get('ice_phone_number', '')
            })
        ]
        
        result = CRUDManager._execute_transaction(queries)
        return result.scalar()

    @staticmethod
    def update_member(member_id: int, member_data: Dict[str, Any]) -> bool:
        """Update member with validation."""
        required_fields = ['first_name', 'last_name', 'email']
        CRUDManager._validate_data(member_data, required_fields)

        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("""
                        UPDATE personal_data
                        SET first_name = :first_name,
                            last_name = :last_name,
                            email = :email,
                            phone_number = :phone_number,
                            ice_first_name = :ice_first_name,
                            ice_last_name = :ice_last_name,
                            ice_phone_number = :ice_phone_number
                        WHERE id = :id
                        RETURNING true
                    """),
                    {**member_data, 'id': member_id}
                )
                success = bool(result.scalar())
                if success:
                    logger.info(f"Successfully updated member {member_id}")
                else:
                    logger.error(f"Failed to update member {member_id}")
                return success
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error in update_member: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in update_member: {str(e)}")
            raise

    @staticmethod
    def delete_member(member_id: int) -> bool:
        """Delete member and associated records in correct order."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:
                logger.info(f"Starting deletion process for member_id: {member_id}")
                
                # First get and verify the userid
                get_userid_query = text("""
                    SELECT userid, first_name, last_name 
                    FROM personal_data 
                    WHERE id = :id
                """)
                result = conn.execute(get_userid_query, {'id': member_id})
                row = result.fetchone()
                
                if not row:
                    logger.error(f"No member found with id {member_id}")
                    return False
                
                userid = row[0]
                logger.info(f"Found userid {userid} for member_id {member_id}")
                
                # Delete in correct order - reverse of creation
                # First delete dependent training records
                training_result = conn.execute(
                    text("""
                        DELETE FROM training_status_data
                        WHERE userid = :userid
                        RETURNING id
                    """),
                    {'userid': userid}
                )
                deleted_training = training_result.fetchall()
                logger.info(f"Deleted {len(deleted_training)} training records for userid {userid}")
                
                # Then delete personal data
                personal_result = conn.execute(
                    text("""
                        DELETE FROM personal_data
                        WHERE id = :id
                        RETURNING id
                    """),
                    {'id': member_id}
                )
                
                if not personal_result.scalar():
                    logger.error(f"Failed to delete personal data for member {member_id}")
                    return False
                
                logger.info(f"Successfully deleted personal data for member {member_id}")
                
                # Finally delete login data
                login_result = conn.execute(
                    text("""
                        DELETE FROM login_data
                        WHERE userid = :userid
                        RETURNING userid
                    """),
                    {'userid': userid}
                )
                
                if login_result.fetchone():
                    logger.info(f"Successfully deleted login data for userid {userid}")
                    return True
                else:
                    logger.error(f"Failed to delete login data for userid {userid}")
                    return False
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error in delete_member: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in delete_member: {str(e)}")
            raise

    @staticmethod
    def add_training(training_data: Dict[str, Any]) -> int:
        """Add training record with automatic status updates."""
        required_fields = ['userid', 'courseid', 'completion_date']
        CRUDManager._validate_data(training_data, required_fields)

        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:
                # Insert training record and get ID
                result = conn.execute(
                    text("""
                        INSERT INTO training_status_data (
                            userid, courseid, completion_date
                        ) VALUES (
                            :userid, :courseid, :completion_date
                        ) RETURNING id
                    """),
                    training_data
                )
                new_id = result.scalar_one()
                
                # Update due date
                conn.execute(
                    text("""
                        UPDATE training_status_data t
                        SET due_date = (t.completion_date::date + 
                            (SELECT frequency_in_months FROM training_course_data c 
                            WHERE c.courseid = t.courseid) * INTERVAL '1 month')::date
                        WHERE id = :id
                    """),
                    {'id': new_id}
                )
                
                # Update status
                conn.execute(
                    text("""
                        UPDATE training_status_data
                        SET status = CASE 
                            WHEN CAST(due_date AS date) >= CURRENT_DATE THEN 'Current'
                            ELSE 'Overdue'
                        END
                        WHERE id = :id
                    """),
                    {'id': new_id}
                )
                
                CRUDManager._update_member_eligibility(training_data['userid'])
                return new_id
                
        except Exception as e:
            logger.error(f"Database error in add_training: {str(e)}")
            raise

    @staticmethod
    def update_training(training_id: int, training_data: Dict[str, Any]) -> bool:
        """Update training record with automatic status updates."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:
                # Update training record and get userid
                result = conn.execute(
                    text("""
                        UPDATE training_status_data
                        SET completion_date = :completion_date
                        WHERE id = :id
                        RETURNING userid
                    """),
                    {**training_data, 'id': training_id}
                )
                userid = result.scalar_one_or_none()
                
                if not userid:
                    return False
                
                # Update due date
                conn.execute(
                    text("""
                        UPDATE training_status_data t
                        SET due_date = (t.completion_date::date + 
                            (SELECT frequency_in_months FROM training_course_data c 
                            WHERE c.courseid = t.courseid) * INTERVAL '1 month')::date
                        WHERE id = :id
                    """),
                    {'id': training_id}
                )
                
                # Update status
                conn.execute(
                    text("""
                        UPDATE training_status_data
                        SET status = CASE 
                            WHEN CAST(due_date AS date) >= CURRENT_DATE THEN 'Current'
                            ELSE 'Overdue'
                        END
                        WHERE id = :id
                    """),
                    {'id': training_id}
                )
                
                CRUDManager._update_member_eligibility(userid)
                return True
                
        except Exception as e:
            logger.error(f"Database error in update_training: {str(e)}")
            raise

    @staticmethod
    def delete_training(training_id: int) -> bool:
        """Delete training record and update member eligibility."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:
                # First get the userid for eligibility update
                get_userid_query = text("""
                    SELECT userid 
                    FROM training_status_data 
                    WHERE id = :id
                """)
                result = conn.execute(get_userid_query, {'id': training_id})
                userid = result.scalar()
                
                if not userid:
                    logger.error(f"No training record found with id {training_id}")
                    return False
                
                # Delete the training record
                delete_query = text("""
                    DELETE FROM training_status_data
                    WHERE id = :id
                    RETURNING true
                """)
                result = conn.execute(delete_query, {'id': training_id})
                success = bool(result.scalar())
                
                if success:
                    # Update the member's eligibility
                    update_eligibility_query = text("""
                        UPDATE personal_data p
                        SET eligibility = 
                            CASE 
                                WHEN EXISTS (
                                    SELECT 1 
                                    FROM training_status_data t 
                                    WHERE t.userid = p.userid 
                                    AND (t.status = 'Overdue' OR t.status IS NULL)
                                ) THEN 'Ineligible'
                                WHEN EXISTS (
                                    SELECT 1 
                                    FROM training_status_data t 
                                    WHERE t.userid = p.userid
                                    AND t.status = 'Current'
                                ) THEN 'Eligible'
                                ELSE 'Ineligible'
                            END
                        WHERE userid = :userid
                    """)
                    conn.execute(update_eligibility_query, {'userid': userid})
                    
                    logger.info(f"Successfully deleted training record {training_id}")
                    return True
                else:
                    logger.error(f"Failed to delete training record {training_id}")
                    return False
                    
        except SQLAlchemyError as e:
            logger.error(f"Database error in delete_training: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in delete_training: {str(e)}")
            raise

    @staticmethod
    def _update_member_eligibility(userid: str) -> None:
        """Update member eligibility based on training status."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE personal_data
                        SET eligibility = CASE 
                            WHEN EXISTS (
                                SELECT 1 FROM training_status_data 
                                WHERE userid = :userid 
                                AND status = 'Overdue'
                            ) THEN 'Ineligible'
                            WHEN NOT EXISTS (
                                SELECT 1 FROM training_status_data 
                                WHERE userid = :userid
                            ) THEN 'Ineligible'
                            ELSE 'Eligible'
                        END
                        WHERE userid = :userid
                    """),
                    {'userid': userid}
                )
        except Exception as e:
            logger.error(f"Database error in update_member_eligibility: {str(e)}")
            raise