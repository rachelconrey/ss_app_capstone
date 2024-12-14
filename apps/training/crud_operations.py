# apps/training/crud_operations.py

from sqlalchemy import text
from datetime import datetime
import pandas as pd
from libs.database.db_engine import DatabaseConfig
import logging
from shiny import reactive, ui, render
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TrainingCRUDManager:
    """Handle CRUD operations for training data."""
    
    @staticmethod
    def get_available_courses() -> Dict[str, str]:
        """Get all available training courses."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = """
                    SELECT courseid, venue 
                    FROM training_course_data 
                    ORDER BY courseid
                """
                result = conn.execute(text(query))
                return {row.courseid: f"{row.courseid} - {row.venue}" 
                       for row in result}
        except Exception as e:
            logger.error(f"Error getting available courses: {str(e)}")
            raise

    @staticmethod
    def get_available_users(courseid: str) -> pd.DataFrame:
        """Get users without specified training."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = """
                    SELECT 
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
                result = conn.execute(text(query), {"courseid": courseid})
                return pd.DataFrame(result.fetchall(), columns=['userid', 'first_name', 'last_name'])
        except Exception as e:
            logger.error(f"Error getting available users: {str(e)}")
            raise

    @staticmethod
    def add_training_record(userid: int, courseid: str, completion_date: datetime) -> int:
        """Add new training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # Insert new record
                query = """
                    INSERT INTO training_status_data (userid, courseid, completion_date)
                    VALUES (:userid, :courseid, :completion_date)
                    RETURNING id
                """
                result = conn.execute(
                    text(query),
                    {
                        "userid": userid,
                        "courseid": courseid,
                        "completion_date": completion_date
                    }
                )
                record_id = result.scalar()
                
                # Update status and eligibility
                conn.execute(text("SELECT update_training_statuses()"))
                conn.commit()
                
                return record_id
        except Exception as e:
            logger.error(f"Error adding training record: {str(e)}")
            raise

    @staticmethod
    def update_training_record(record_id: int, completion_date: datetime) -> bool:
        """Update existing training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = """
                    UPDATE training_status_data
                    SET completion_date = :completion_date
                    WHERE id = :id
                    RETURNING true
                """
                result = conn.execute(
                    text(query),
                    {"id": record_id, "completion_date": completion_date}
                )
                
                # Update status and eligibility
                conn.execute(text("SELECT update_training_statuses()"))
                conn.commit()
                
                return bool(result.scalar())
        except Exception as e:
            logger.error(f"Error updating training record: {str(e)}")
            raise

    @staticmethod
    def delete_training_record(record_id: int) -> bool:
        """Delete training record."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = """
                    DELETE FROM training_status_data
                    WHERE id = :id
                    RETURNING true
                """
                result = conn.execute(text(query), {"id": record_id})
                
                # Update eligibility after deletion
                conn.execute(text("SELECT update_training_statuses()"))
                conn.commit()
                
                return bool(result.scalar())
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
    
    @reactive.Effect
    def initialize_course_dropdown():
        """Initialize course dropdown on startup."""
        try:
            courses = TrainingCRUDManager.get_available_courses()
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
                df = TrainingCRUDManager.get_available_users(course)
                choices = {
                    str(row['userid']): f"{row['last_name']}, {row['first_name']}"
                    for _, row in df.iterrows()
                }
                
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
            user_id = input.new_training_user()
            course_id = input.new_training_course()
            completion_date = input.new_training_date()
            
            if all([user_id, course_id, completion_date]):
                new_id = TrainingCRUDManager.add_training_record(
                    int(user_id), course_id, completion_date
                )
                ui.notification_show(
                    f"Successfully added training record (ID: {new_id})",
                    type="success"
                )
                update_training_table()
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
        try:
            record_id = selected_record.get()
            completion_date = input.edit_training_date()
            
            if not record_id:
                ui.notification_show(
                    "Please select a record to update",
                    type="warning"
                )
                return
                
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
            record_id = selected_record.get()
            
            if not record_id:
                ui.notification_show(
                    "Please select a record to delete",
                    type="warning"
                )
                return
                
            if TrainingCRUDManager.delete_training_record(record_id):
                ui.notification_show(
                    "Successfully deleted training record",
                    type="success"
                )
                update_training_table()
            else:
                ui.notification_show(
                    "Failed to delete training record",
                    type="error"
                )
        except Exception as e:
            ui.notification_show(
                f"Error deleting training record: {str(e)}",
                type="error"
            )
            
    # Add these output handlers to your server_training_crud function
    
    @output
    @render.text
    def selected_record_text():
        """Display information about the selected record for editing."""
        record_id = selected_record.get()
        if record_id is not None:
            df = training_data.get()
            if not df.empty:
                try:
                    record = df[df['id'] == record_id].iloc[0]
                    return (f"Selected Record:\n"
                           f"Name: {record['first_name']} {record['last_name']}\n"
                           f"Course: {record['courseid']}\n"
                           f"Current Completion Date: {record['completion_date']}")
                except Exception as e:
                    logger.error(f"Error displaying selected record: {str(e)}")
                    return "Error displaying record details"
        return "No record selected"

    @output
    @render.text
    def delete_record_text():
        """Display information about the selected record for deletion."""
        record_id = selected_record.get()
        if record_id is not None:
            df = training_data.get()
            if not df.empty:
                try:
                    record = df[df['id'] == record_id].iloc[0]
                    return (f"Selected for Deletion:\n"
                           f"Name: {record['first_name']} {record['last_name']}\n"
                           f"Course: {record['courseid']}\n"
                           f"Completion Date: {record['completion_date']}")
                except Exception as e:
                    logger.error(f"Error displaying delete record: {str(e)}")
                    return "Error displaying record details"
        return "No record selected for deletion"

    # Add this to handle tab changes based on selection
    @reactive.Effect
    @reactive.event(selected_record)
    def update_crud_tabs():
        """Update the active tab when a record is selected."""
        record_id = selected_record.get()
        if record_id:
            ui.update_navs(
                "training_crud_tabs",
                selected="Edit Training"
            )

    # Update the form when a record is selected
    @reactive.Effect
    @reactive.event(selected_record)
    def update_forms():
        """Update forms when a record is selected."""
        record_id = selected_record.get()
        if record_id is not None:
            df = training_data.get()
            if not df.empty:
                try:
                    record = df[df['id'] == record_id].iloc[0]
                    completion_date = pd.to_datetime(record['completion_date']).date()
                    ui.update_date("edit_training_date", value=completion_date)
                except Exception as e:
                    logger.error(f"Error updating forms: {str(e)}")

    return {
        'initialize_course_dropdown': initialize_course_dropdown,
        'update_user_choices': update_user_choices,
        'handle_add_training': handle_add_training,
        'handle_update_training': handle_update_training,
        'handle_delete_training': handle_delete_training
    }