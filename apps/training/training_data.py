import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from datetime import datetime
from libs.database.db_engine import DatabaseConfig
from libs.crud_manager import CRUDManager

logger = logging.getLogger(__name__)

def server_training_data(input, output, session):
    """Server logic for training data with CRUD operations."""
    
    # Reactive values for managing state
    selected_record = reactive.Value(None)
    training_data = reactive.Value(pd.DataFrame())
    
    def load_course_choices():
        """Load available courses for dropdown."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("SELECT courseid FROM training_course_data ORDER BY courseid")
                result = conn.execute(query)
                courses = [row[0] for row in result]
                ui.update_select(
                    "new_training_course",
                    choices={"": "Select a course"} | {c: c for c in courses}
                )
        except Exception as e:
            logger.error(f"Error loading courses: {str(e)}")
            ui.notification_show(
                "Error loading courses",
                type="error"
            )

    def load_user_choices(courseid):
        """Load available users for selected course."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT p.userid, p.first_name || ' ' || p.last_name as full_name
                    FROM personal_data p
                    WHERE NOT EXISTS (
                        SELECT 1 FROM training_status_data t
                        WHERE t.userid = p.userid AND t.courseid = :courseid
                    )
                    ORDER BY p.last_name, p.first_name
                """)
                result = conn.execute(query, {"courseid": courseid})
                users = {str(row[0]): row[1] for row in result}
                ui.update_select(
                    "new_training_user",
                    choices={"": "Select a user"} | users
                )
        except Exception as e:
            logger.error(f"Error loading users: {str(e)}")
            ui.notification_show(
                "Error loading users",
                type="error"
            )

    def fetch_training_data():
        """Fetch training data from database."""
        try:
            engine = DatabaseConfig.get_db_engine()
            query = text("""
                SELECT 
                    t.id,
                    t.userid,
                    p.first_name,
                    p.last_name,
                    t.courseid,
                    t.completion_date,
                    t.due_date,
                    t.status
                FROM training_status_data t
                JOIN personal_data p ON t.userid = p.userid
                ORDER BY t.completion_date DESC NULLS LAST
            """)
            with engine.connect() as conn:
                df = pd.read_sql_query(query, conn)
            training_data.set(df)
        except Exception as e:
            logger.error(f"Error fetching training data: {str(e)}")
            ui.notification_show(
                "Error fetching training data",
                type="error"
            )

    @reactive.Effect
    def _load_initial_data():
        """Load initial data."""
        fetch_training_data()
        load_course_choices()

    @reactive.Effect
    def _update_user_choices():
        """Update user choices when course selection changes."""
        course = input.new_training_course()
        if course:
            load_user_choices(course)

    @reactive.Effect
    @reactive.event(input.add_training_btn)
    def handle_add_training():
        """Handle adding new training record."""
        try:
            if not input.new_training_user() or not input.new_training_course():
                ui.notification_show(
                    "Please select both a user and a course",
                    type="error"
                )
                return

            training_data = {
                'userid': input.new_training_user(),
                'courseid': input.new_training_course(),
                'completion_date': input.new_training_date()
            }
            
            CRUDManager.add_training(training_data)
            
            # Reset form
            ui.update_select("new_training_course", selected="")
            ui.update_select("new_training_user", selected="")
            ui.update_date("new_training_date", value=datetime.now().date())
            
            ui.notification_show(
                "Training record added successfully",
                type="success"
            )
            fetch_training_data()
            
        except Exception as e:
            logger.error(f"Error adding training: {str(e)}")
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
            if not record_id:
                ui.notification_show(
                    "Please select a record to update",
                    type="error"
                )
                return

            training_data = {
                'completion_date': input.edit_training_date()
            }
            
            CRUDManager.update_training(record_id, training_data)
            
            ui.notification_show(
                "Training record updated successfully",
                type="success"
            )
            fetch_training_data()
            
        except Exception as e:
            logger.error(f"Error updating training: {str(e)}")
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
                    type="error"
                )
                return

            CRUDManager.delete_training(record_id)
            
            ui.notification_show(
                "Training record deleted successfully",
                type="success"
            )
            fetch_training_data()
            selected_record.set(None)
            
        except Exception as e:
            logger.error(f"Error deleting training: {str(e)}")
            ui.notification_show(
                f"Error deleting training record: {str(e)}",
                type="error"
            )

    @output
    @render.data_frame
    def training_table():
        """Render training data table."""
        df = training_data.get()
        if not df.empty:
            df = df.copy()
            
            # Format dates
            df['completion_date'] = pd.to_datetime(df['completion_date']).dt.strftime('%Y-%m-%d')
            df['due_date'] = pd.to_datetime(df['due_date']).dt.strftime('%Y-%m-%d')
            
            # Create display columns
            display_columns = [
                'first_name', 'last_name', 'courseid', 
                'completion_date', 'due_date', 'status'
            ]
            
            # Rename columns for display
            column_labels = {
                'first_name': 'First Name',
                'last_name': 'Last Name',
                'courseid': 'Course',
                'completion_date': 'Completion Date',
                'due_date': 'Due Date',
                'status': 'Status'
            }
            
            display_df = df[display_columns].rename(columns=column_labels)
            
            # Capitalize names
            display_df['First Name'] = display_df['First Name'].str.title()
            display_df['Last Name'] = display_df['Last Name'].str.title()
            
            return render.DataGrid(
                display_df,
                selection_mode="row",
                height="800px",
                width="100%"
            )
        return None

    @reactive.Effect
    @reactive.event(input.training_table_selected_rows)
    def handle_selection():
        """Update selected record when table selection changes."""
        selected_indices = input.training_table_selected_rows()
        if selected_indices and len(selected_indices) > 0:
            df = training_data.get()
            if not df.empty and selected_indices[0] < len(df):
                record_id = df.iloc[selected_indices[0]]['id']
                selected_record.set(record_id)
                
                # Pre-fill edit form
                completion_date = pd.to_datetime(df.iloc[selected_indices[0]]['completion_date'])
                ui.update_date("edit_training_date", value=completion_date.date())
        else:
            selected_record.set(None)

    # Return necessary data for other modules
    return {
        'selected_record': selected_record,
        'training_data': training_data
    }