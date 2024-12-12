# apps/training/crud_operations.py

from sqlalchemy import text
from datetime import datetime
import pandas as pd
from libs.database.db_engine import DatabaseConfig
import logging
from shiny import reactive, ui, render

logger = logging.getLogger(__name__)

class TrainingCRUDManager:
    """Handle CRUD operations for training data."""
    
    @staticmethod
    def get_available_users(courseid: str) -> pd.DataFrame:
        """Get users without specified training."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM get_users_without_training(:courseid)"),
                    {"courseid": courseid}
                )
                return pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            logger.error(f"Error getting available users: {str(e)}")
            raise

    @staticmethod
    def add_training_record(userid: int, courseid: str, completion_date: datetime) -> int:
        """Add new training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT insert_training_record(:userid, :courseid, :completion_date)"),
                    {
                        "userid": userid,
                        "courseid": courseid,
                        "completion_date": completion_date
                    }
                )
                conn.commit()
                return result.scalar()
        except Exception as e:
            logger.error(f"Error adding training record: {str(e)}")
            raise

    @staticmethod
    def update_training_record(record_id: int, completion_date: datetime) -> bool:
        """Update existing training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT update_training_record(:id, :completion_date)"),
                    {"id": record_id, "completion_date": completion_date}
                )
                conn.commit()
                return result.scalar()
        except Exception as e:
            logger.error(f"Error updating training record: {str(e)}")
            raise

    @staticmethod
    def delete_training_record(record_id: int) -> bool:
        """Delete training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT delete_training_record(:id)"),
                    {"id": record_id}
                )
                conn.commit()
                return result.scalar()
        except Exception as e:
            logger.error(f"Error deleting training record: {str(e)}")
            raise

def server_training_crud(input, output, session, module_data):
    """Server logic for training CRUD operations."""
    
    if not module_data:
        raise ValueError("module_data is required")
    
    # Get shared data from module_data
    selected_record = module_data['selected_record']
    training_data = module_data['training_data']
    update_training_table = module_data['update_training_table']
    
    # Load initial courses for dropdown
    @reactive.Effect
    def initialize_course_dropdown():
        """Initialize course dropdown on startup."""
        try:
            with DatabaseConfig.get_db_engine().connect() as conn:
                # Get all courses
                query = "SELECT courseid, venue FROM training_course_data ORDER BY courseid"
                result = conn.execute(text(query))
                courses = {row.courseid: f"{row.courseid} - {row.venue}" 
                          for row in result}
                
                # Update the course dropdown
                ui.update_select(
                    "new_training_course",
                    choices=courses,
                    selected=None
                )
        except Exception as e:
            ui.notification_show(
                f"Error loading courses: {str(e)}",
                type="error"
            )
            
    @reactive.Effect
    @reactive.event(input.new_training_course)
    def update_user_choices():
        """Update available users when course selection changes."""
        course = input.new_training_course()
        if course:
            try:
                query = """
                    SELECT DISTINCT
                        p.userid,
                        p.first_name,
                        p.last_name
                    FROM personal_data p
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM training_status_data t
                        WHERE t.userid = p.userid
                        AND t.courseid = :courseid
                        AND t.status = 'Current'
                    )
                    ORDER BY p.last_name, p.first_name
                """
                
                with DatabaseConfig.get_db_engine().connect() as conn:
                    result = conn.execute(text(query), {"courseid": course})
                    users = [dict(row) for row in result]
                
                choices = {str(user['userid']): f"{user['last_name']}, {user['first_name']}"
                          for user in users}
                
                if not choices:
                    choices = {"": "No users need this training"}
                
                ui.update_select(
                    "new_training_user",
                    choices=choices,
                    selected=None
                )
            except Exception as e:
                ui.notification_show(
                    f"Error loading available users: {str(e)}",
                    type="error"
                )
        else:
            ui.update_select(
                "new_training_user",
                choices={"": "Select a course first"},
                selected=None
            )

    @reactive.Effect
    @reactive.event(input.add_training_btn)
    def handle_add_training():
        """Handle adding new training record."""
        try:
            userid = int(input.new_training_user())
            courseid = input.new_training_course()
            completion_date = input.new_training_date()
            
            if all([userid, courseid, completion_date]):
                new_id = TrainingCRUDManager.add_training_record(
                    userid, courseid, completion_date
                )
                ui.notification_show(
                    f"Successfully added training record (ID: {new_id})",
                    type="success"
                )
                # Trigger data refresh
                training_data.invalidate()
            else:
                ui.notification_show(
                    "Please fill in all required fields",
                    type="warning"
                )
        except Exception as e:
            ui.notification_show(
                f"Error adding training record: {str(e)}",
                type="error"
            )

    @reactive.Effect
    @reactive.event(input.update_training_btn)
    def handle_update_training():
        """Handle updating training record."""
        record_id = selected_record.get()
        completion_date = input.edit_training_date()
        
        if not record_id:
            ui.notification_show(
                "Please select a record to update",
                type="warning"
            )
            return
            
        try:
            if TrainingCRUDManager.update_training_record(
                record_id, completion_date
            ):
                ui.notification_show(
                    "Training record updated successfully",
                    type="success"
                )
                update_training_table()
            else:
                ui.notification_show(
                    "Failed to update training record",
                    type="error"
                )
        except Exception as e:
            ui.notification_show(
                f"Error updating training record: {str(e)}",
                type="error"
            )

    @reactive.Effect
    @reactive.event(input.delete_training_btn)
    def handle_delete_training():
        """Handle deleting training record."""
        try:
            record_id = input.selected_record()
            
            if record_id:
                success = TrainingCRUDManager.delete_training_record(record_id)
                if success:
                    ui.notification_show(
                        "Successfully deleted training record",
                        type="success"
                    )
                    # Trigger data refresh
                    training_data.invalidate()
                else:
                    ui.notification_show(
                        "Failed to delete training record",
                        type="error"
                    )
            else:
                ui.notification_show(
                    "Please select a record to delete",
                    type="warning"
                )
        except Exception as e:
            ui.notification_show(
                f"Error deleting training record: {str(e)}",
                type="error"
            )

    @reactive.Effect
    @reactive.event(input.training_table_selected)
    def handle_selection():
        selected_index = input.training_table_selected()
        if selected_index and training_data:
            df = training_data.get()
            record_id = df.iloc[selected_index[0]]['id']
            selected_record.set(record_id)
            
    @output
    @render.text
    def selected_record_info():
        record_id = selected_record.get()
        if record_id and training_data:
            df = training_data.get()
            record = df[df['id'] == record_id].iloc[0]
            return f"Selected: {record['first_name']} {record['last_name']} - {record['courseid']}"
        return "No record selected"

    @output
    @render.ui
    def edit_training_inputs():
        record_id = selected_record.get()
        if record_id and training_data:
            df = training_data.get()
            record = df[df['id'] == record_id].iloc[0]
            return ui.div(
                ui.input_date(
                    "edit_training_date",
                    "New Completion Date",
                    value=record['completion_date']
                )
            )
        return ui.div("Select a record to edit")