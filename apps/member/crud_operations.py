from sqlalchemy import text
import logging
from shiny import reactive, ui, render
from libs.database.db_engine import DatabaseConfig
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MemberCRUDManager:
    """Handle CRUD operations for member data."""
    
    @staticmethod
    def add_member(member_data: dict) -> int:
        """Add new member record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # Add input validation
                required_fields = ['first_name', 'last_name', 'email']
                if not all(member_data.get(field) for field in required_fields):
                    raise ValueError("Missing required fields")

                # Get a valid role from roles_data table
                role_query = text("SELECT role FROM roles_data LIMIT 1")
                default_role = conn.execute(role_query).scalar()
                
                if not default_role:
                    raise ValueError("No roles found in roles_data table")

                # Generate username-style userid
                userid = f"{member_data['first_name'][0].lower()}{member_data['last_name'].lower()}"
                
                # Create login record with valid role
                login_query = text("""
                    INSERT INTO login_data (userid, password, role, date_created)
                    VALUES (:userid, 'default_password', :role, CURRENT_TIMESTAMP)
                    RETURNING id, userid
                """)
                
                login_result = conn.execute(login_query, {
                    'userid': userid,
                    'role': default_role
                })
                row = login_result.fetchone()
                login_id, userid = row

                # Rest of the function remains the same...
                personal_query = text("""
                    INSERT INTO personal_data (
                        userid, first_name, last_name, email, phone_number,
                        ice_first_name, ice_last_name, ice_phone_number,
                        eligibility
                    ) VALUES (
                        :userid, :first_name, :last_name, :email, :phone_number,
                        :ice_first_name, :ice_last_name, :ice_phone_number,
                        'Ineligible'
                    )
                    RETURNING id
                """)

                member_data['userid'] = userid
                member_data.setdefault('phone_number', '')
                member_data.setdefault('ice_first_name', '')
                member_data.setdefault('ice_last_name', '')
                member_data.setdefault('ice_phone_number', '')

                result = conn.execute(personal_query, member_data)
                member_id = result.scalar()
                conn.commit()
                logger.info(f"Successfully added member with ID: {member_id}")
                return member_id
        except Exception as e:
            logger.error(f"Error adding member: {str(e)}")
            raise

    @staticmethod
    def update_member(member_id: int, member_data: dict) -> bool:
        """Update existing member record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # Validate required fields
                required_fields = ['first_name', 'last_name', 'email']
                if not all(member_data.get(field) for field in required_fields):
                    raise ValueError("Missing required fields")

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
                    RETURNING true
                """)
                
                result = conn.execute(
                    query,
                    {**member_data, 'id': member_id}
                )
                success = bool(result.scalar())
                conn.commit()
                
                if success:
                    logger.info(f"Successfully updated member with ID: {member_id}")
                else:
                    logger.warning(f"No member found with ID: {member_id}")
                
                return success
        except Exception as e:
            logger.error(f"Error updating member: {str(e)}")
            raise

    @staticmethod
    def delete_member(member_id: int) -> bool:
        """Delete member record and associated training records."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # First get the userid for this member
                get_userid_query = text("""
                    SELECT userid FROM personal_data WHERE id = :id
                """)
                userid = conn.execute(get_userid_query, {'id': member_id}).scalar()

                # Delete training records using the userid
                training_query = text("""
                    DELETE FROM training_status_data
                    WHERE userid = :userid
                """)
                conn.execute(training_query, {'userid': str(userid)})
                
                # Delete login data
                login_query = text("""
                    DELETE FROM login_data
                    WHERE userid = :userid
                """)
                conn.execute(login_query, {'userid': str(userid)})
                
                # Then delete member
                member_query = text("""
                    DELETE FROM personal_data
                    WHERE id = :id
                    RETURNING true
                """)
                result = conn.execute(member_query, {'id': member_id})
                success = bool(result.scalar())
                conn.commit()
                
                if success:
                    logger.info(f"Successfully deleted member with ID: {member_id}")
                else:
                    logger.warning(f"No member found with ID: {member_id}")
                
                return success
        except Exception as e:
            logger.error(f"Error deleting member: {str(e)}")
            raise
class TrainingCRUDManager:
    """Handle CRUD operations for training data."""
    
    @staticmethod
    def add_training(training_data: dict) -> int:
        """Add new training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # Validate required fields
                required_fields = ['userid', 'courseid', 'completion_date']
                if not all(training_data.get(field) for field in required_fields):
                    raise ValueError("Missing required fields")

                query = text("""
                    INSERT INTO training_status_data (
                        userid, courseid, completion_date, created_at, updated_at
                    ) VALUES (
                        :userid, :courseid, :completion_date,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, training_data)
                training_id = result.scalar()
                
                # Update training status and eligibility
                status_query = text("SELECT update_training_statuses()")
                conn.execute(status_query)
                
                conn.commit()
                logger.info(f"Successfully added training record with ID: {training_id}")
                return training_id
        except Exception as e:
            logger.error(f"Error adding training record: {str(e)}")
            raise

    @staticmethod
    def update_training(training_id: int, training_data: dict) -> bool:
        """Update existing training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("""
                    UPDATE training_status_data
                    SET completion_date = :completion_date,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    RETURNING true
                """)
                
                result = conn.execute(
                    query,
                    {**training_data, 'id': training_id}
                )
                
                # Update training status and eligibility
                status_query = text("SELECT update_training_statuses()")
                conn.execute(status_query)
                
                success = bool(result.scalar())
                conn.commit()
                
                if success:
                    logger.info(f"Successfully updated training record with ID: {training_id}")
                else:
                    logger.warning(f"No training record found with ID: {training_id}")
                
                return success
        except Exception as e:
            logger.error(f"Error updating training record: {str(e)}")
            raise

    @staticmethod
    def delete_training(training_id: int) -> bool:
        """Delete training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("""
                    DELETE FROM training_status_data
                    WHERE id = :id
                    RETURNING true
                """)
                
                result = conn.execute(query, {'id': training_id})
                
                # Update eligibility after deletion
                status_query = text("SELECT update_training_statuses()")
                conn.execute(status_query)
                
                success = bool(result.scalar())
                conn.commit()
                
                if success:
                    logger.info(f"Successfully deleted training record with ID: {training_id}")
                else:
                    logger.warning(f"No training record found with ID: {training_id}")
                
                return success
        except Exception as e:
            logger.error(f"Error deleting training record: {str(e)}")
            raise

def server_personal_crud(input, output, session, module_data):
    """Server logic for member CRUD operations."""
    
    # Validate module_data
    if not module_data or not all(key in module_data for key in ['selected_member', 'member_data', 'update_member_table']):
        raise ValueError("Invalid module_data provided")
    
    selected_member = module_data['selected_member']
    member_data = module_data['member_data']
    update_member_table = module_data['update_member_table']
    
    # Add reactive value to store current page
    current_page = reactive.Value(0)
    
    @reactive.Effect
    @reactive.event(input.member_table_page)
    def update_current_page():
        """Store the current page number when it changes."""
        current_page.set(input.member_table_page())

    def refresh_table_and_maintain_state():
        """Update table while maintaining current page and selection."""
        try:
            # Store current page
            page = current_page.get()
            
            # Update the table data
            update_member_table()
            
            # Restore page after brief delay to ensure table is updated
            @reactive.Effect
            def restore_state():
                ui.update_data_grid(
                    "member_table",
                    page=page
                )
                
        except Exception as e:
            logger.error(f"Error refreshing table: {str(e)}")

    @reactive.Effect
    @reactive.event(input.add_member_btn)
    def handle_add_member():
        """Handle adding new member."""
        try:
            new_member_data = {
                'first_name': input.new_first_name(),
                'last_name': input.new_last_name(),
                'email': input.new_email(),
                'phone_number': input.new_phone(),
                'ice_first_name': input.new_ice_first_name(),
                'ice_last_name': input.new_ice_last_name(),
                'ice_phone_number': input.new_ice_phone()
            }
            
            if not all([
                new_member_data['first_name'],
                new_member_data['last_name'],
                new_member_data['email']
            ]):
                ui.notification_show(
                    "Please fill in all required fields (First Name, Last Name, Email)",
                    type="warning"
                )
                return
            
            new_id = MemberCRUDManager.add_member(new_member_data)
            
            ui.notification_show(
                f"Successfully added member (ID: {new_id})",
                type="success"
            )
            
            # Clear form fields
            for field in [
                'new_first_name', 'new_last_name', 'new_email', 'new_phone',
                'new_ice_first_name', 'new_ice_last_name', 'new_ice_phone'
            ]:
                ui.update_text(field, value="")
            
            # Refresh table while maintaining state
            refresh_table_and_maintain_state()
            
        except Exception as e:
            ui.notification_show(
                f"Error adding member: {str(e)}",
                type="error"
            )
            logger.error(f"Error in handle_add_member: {str(e)}")

    @reactive.Effect
    @reactive.event(input.update_member_btn)
    def handle_update_member():
        """Handle updating member."""
        try:
            member_id = selected_member.get()
            if not member_id:
                ui.notification_show(
                    "Please select a member to update",
                    type="warning"
                )
                return
            
            updated_data = {
                'first_name': input.edit_first_name(),
                'last_name': input.edit_last_name(),
                'email': input.edit_email(),
                'phone_number': input.edit_phone(),
                'ice_first_name': input.edit_ice_first_name(),
                'ice_last_name': input.edit_ice_last_name(),
                'ice_phone_number': input.edit_ice_phone()
            }
            
            if not all([
                updated_data['first_name'],
                updated_data['last_name'],
                updated_data['email']
            ]):
                ui.notification_show(
                    "Please fill in all required fields (First Name, Last Name, Email)",
                    type="warning"
                )
                return
            
            if MemberCRUDManager.update_member(member_id, updated_data):
                ui.notification_show(
                    "Member updated successfully",
                    type="success"
                )
                # Refresh table while maintaining state
                refresh_table_and_maintain_state()
            else:
                ui.notification_show(
                    "Failed to update member",
                    type="error"
                )
            
        except Exception as e:
            ui.notification_show(
                f"Error updating member: {str(e)}",
                type="error"
            )
            logger.error(f"Error in handle_update_member: {str(e)}")

    @reactive.Effect
    @reactive.event(input.delete_member_btn)
    def handle_delete_member():
        """Handle deleting member."""
        try:
            member_id = selected_member.get()
            if not member_id:
                ui.notification_show(
                    "Please select a member to delete",
                    type="warning"
                )
                return
            
            if MemberCRUDManager.delete_member(member_id):
                ui.notification_show(
                    "Successfully deleted member",
                    type="success"
                )
                # Refresh table while maintaining state
                refresh_table_and_maintain_state()
                # Clear selection after delete
                selected_member.set(None)
            else:
                ui.notification_show(
                    "Failed to delete member",
                    type="error"
                )
            
        except Exception as e:
            ui.notification_show(
                f"Error deleting member: {str(e)}",
                type="error"
            )
            logger.error(f"Error in handle_delete_member: {str(e)}")

    return {
        'handle_add_member': handle_add_member,
        'handle_update_member': handle_update_member,
        'handle_delete_member': handle_delete_member
    }