# apps/member/crud_operations.py

from sqlalchemy import text
import logging
from shiny import reactive, ui, render
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

class MemberCRUDManager:
    """Handle CRUD operations for member data."""
    
    @staticmethod
    def add_member(member_data: dict) -> int:
        """Add new member record."""
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
                    )
                    RETURNING id
                """)
                result = conn.execute(query, member_data)
                member_id = result.scalar()
                conn.commit()
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
                result = conn.execute(text(query), {**member_data, 'id': member_id})
                conn.commit()
                return bool(result.scalar())
        except Exception as e:
            logger.error(f"Error updating member: {str(e)}")
            raise

    @staticmethod
    def delete_member(member_id: int) -> bool:
        """Delete member record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # First delete related training records
                query_training = text("""
                    DELETE FROM training_status_data
                    WHERE userid = :id
                """)
                conn.execute(query_training, {'id': member_id})
                
                # Then delete member
                query_member = text("""
                    DELETE FROM personal_data
                    WHERE id = :id
                    RETURNING true
                """)
                result = conn.execute(query_member, {'id': member_id})
                conn.commit()
                return bool(result.scalar())
        except Exception as e:
            logger.error(f"Error deleting member: {str(e)}")
            raise

def server_personal_crud(input, output, session, module_data):
    """Server logic for member CRUD operations."""
    
    if not module_data:
        raise ValueError("module_data is required")
    
    required_keys = ['selected_member', 'member_data', 'update_member_table']
    missing_keys = [key for key in required_keys if key not in module_data]
    if missing_keys:
        raise ValueError(f"Missing required module_data keys: {missing_keys}")
    
    # Get shared data from module_data
    selected_member = module_data['selected_member']
    member_data = module_data['member_data']
    update_member_table = module_data['update_member_table']
    
    # continuing crud_operations.py after the handle_add_member function...

    @reactive.Effect
    @reactive.event(input.add_member_btn)
    def handle_add_member():
        """Handle adding new member."""
        try:
            member_data = {
                'first_name': input.new_first_name(),
                'last_name': input.new_last_name(),
                'email': input.new_email(),
                'phone_number': input.new_phone(),
                'ice_first_name': input.new_ice_first_name(),
                'ice_last_name': input.new_ice_last_name(),
                'ice_phone_number': input.new_ice_phone()
            }
            
            # Validate required fields
            if not all([
                member_data['first_name'],
                member_data['last_name'],
                member_data['email']
            ]):
                ui.notification_show(
                    "Please fill in all required fields (First Name, Last Name, Email)",
                    type="warning"
                )
                return
            
            new_id = MemberCRUDManager.add_member(member_data)
            ui.notification_show(
                f"Successfully added member (ID: {new_id})",
                type="success"
            )
            update_member_table()
            
            # Clear form
            ui.update_text("new_first_name", value="")
            ui.update_text("new_last_name", value="")
            ui.update_text("new_email", value="")
            ui.update_text("new_phone", value="")
            ui.update_text("new_ice_first_name", value="")
            ui.update_text("new_ice_last_name", value="")
            ui.update_text("new_ice_phone", value="")
            
        except Exception as e:
            ui.notification_show(
                f"Error adding member: {str(e)}",
                type="error"
            )

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
                
            member_data = {
                'first_name': input.edit_first_name(),
                'last_name': input.edit_last_name(),
                'email': input.edit_email(),
                'phone_number': input.edit_phone(),
                'ice_first_name': input.edit_ice_first_name(),
                'ice_last_name': input.edit_ice_last_name(),
                'ice_phone_number': input.edit_ice_phone()
            }
            
            # Validate required fields
            if not all([
                member_data['first_name'],
                member_data['last_name'],
                member_data['email']
            ]):
                ui.notification_show(
                    "Please fill in all required fields (First Name, Last Name, Email)",
                    type="warning"
                )
                return
                
            if MemberCRUDManager.update_member(member_id, member_data):
                ui.notification_show(
                    "Member updated successfully",
                    type="success"
                )
                update_member_table()
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
                update_member_table()
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
    
    @output
    @render.text
    def selected_member_text():
        """Display information about the selected member for editing."""
        member_id = selected_member.get()
        if member_id is not None:
            df = member_data.get()
            if not df.empty:
                try:
                    member = df[df['id'] == member_id].iloc[0]
                    return (f"Selected Member:\n"
                           f"Name: {member['first_name'].title()} {member['last_name'].title()}\n"
                           f"Email: {member['email']}\n"
                           f"Status: {member['eligibility']}")
                except Exception as e:
                    logger.error(f"Error displaying selected member: {str(e)}")
                    return "Error displaying member details"
        return "No member selected"

    @output
    @render.text
    def delete_member_text():
        """Display information about the selected member for deletion."""
        member_id = selected_member.get()
        if member_id is not None:
            df = member_data.get()
            if not df.empty:
                try:
                    member = df[df['id'] == member_id].iloc[0]
                    return (f"Selected for Deletion:\n"
                           f"Name: {member['first_name'].title()} {member['last_name'].title()}\n"
                           f"Email: {member['email']}\n"
                           f"Status: {member['eligibility']}")
                except Exception as e:
                    logger.error(f"Error displaying delete member: {str(e)}")
                    return "Error displaying member details"
        return "No member selected for deletion"

    # Add this to handle tab changes based on selection
    @reactive.Effect
    @reactive.event(selected_member)
    def update_crud_tabs():
        """Update the active tab when a member is selected."""
        member_id = selected_member.get()
        if member_id:
            ui.update_navs(
                "member_crud_tabs",
                selected="Edit Member"
            )