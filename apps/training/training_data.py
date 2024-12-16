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
    filtered_data = reactive.Value(pd.DataFrame())
    courses = reactive.Value([])
    course_details = reactive.Value({})

    # Create a trigger for initialization
    init_trigger = reactive.Value(0)

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
                choices = {"All": "All"} | {c: c for c in courses}
                
                # Update both dropdowns
                ui.update_select("new_training_course", choices={"": "Select a course"} | {c: c for c in courses})
                ui.update_select("search_course", choices=choices)
                
        except Exception as e:
            logger.error(f"Error loading courses: {str(e)}")
            ui.notification_show(
                "Error loading courses",
                type="error"
            )

    @reactive.Effect
    def _initialize():
        """Load initial data and choices."""
        logger.info("Initializing training data...")
        fetch_training_data()
        load_course_choices()
        load_user_choices() 

    @reactive.Effect
    def _update_user_choices():
        """Update user choices when course selection changes."""
        course = input.new_training_course()
        if course:
            load_user_choices(course)
            
    def load_user_choices(course=None):
        """Load available users for dropdown."""
        engine = DatabaseConfig.get_db_engine()
        try:
            with engine.connect() as conn:
                # If no course selected, show all users
                if not course or course == "":
                    query = text("""
                        SELECT userid, first_name, last_name 
                        FROM personal_data 
                        ORDER BY last_name, first_name
                    """)
                    result = conn.execute(query)
                else:
                    # Show only users who haven't completed this course
                    query = text("""
                        SELECT DISTINCT p.userid, p.first_name, p.last_name
                        FROM personal_data p
                        LEFT JOIN training_status_data t 
                            ON p.userid = t.userid 
                            AND t.courseid = :course
                        WHERE t.userid IS NULL
                        ORDER BY p.last_name, p.first_name
                    """)
                    result = conn.execute(query, {'course': course})

                users = {str(row[0]): f"{row[2]}, {row[1]}" for row in result}
                
                ui.update_select(
                    "new_training_user",
                    choices={"": "Select a user"} | users
                )
                logger.info(f"Successfully loaded {len(users)} users")
                
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
            
            logger.info(f"Fetched {len(df)} training records")
            training_data.set(df)
            filtered_data.set(df)
            
        except Exception as e:
            logger.error(f"Error fetching training data: {str(e)}")
            ui.notification_show(
                "Error fetching training data",
                type="error"
            )

    def apply_filters():
        """Apply search and status filters to training data."""
        df = training_data.get()
        if df.empty:
            filtered_data.set(pd.DataFrame())
            return

        # Apply filters
        course_filter = input.search_course()
        if course_filter and course_filter != "All":
            df = df[df['courseid'] == course_filter]

        status_filter = input.status_filter_training()
        if status_filter and status_filter != "All":
            df = df[df['status'] == status_filter]

        filtered_data.set(df)
        logger.info(f"Applied filters: {len(df)} records after filtering")

    @reactive.Effect
    @reactive.event(input.refresh_data)
    def _handle_refresh():
        """Handle refresh button click."""
        load_course_choices()
        load_user_choices()
        fetch_training_data()

    def _handle_course_change():
        """Update user choices when course selection changes."""
        selected_course = input.new_training_course()
        load_user_choices(selected_course)

    @reactive.Effect
    @reactive.event(input.search_course, input.status_filter_training)
    def _handle_filters():
        """Handle changes to filters."""
        apply_filters()

    @output
    @render.data_frame
    def training_table():
        """Render training data table."""
        df = filtered_data.get()
        if df is None or df.empty:
            logger.warning("No training data to display")
            return None

        try:
            df = df.copy()
            
            # Format dates
            df['completion_date'] = pd.to_datetime(df['completion_date']).dt.strftime('%Y-%m-%d')
            df['due_date'] = pd.to_datetime(df['due_date']).dt.strftime('%Y-%m-%d')
            
            display_columns = [
                'first_name', 'last_name', 'courseid', 
                'completion_date', 'due_date', 'status'
            ]
            
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
            
            logger.info(f"Rendering table with {len(display_df)} records")
            return render.DataGrid(
                display_df,
                selection_mode="row",
                height="800px",
                width="100%"
            )
        except Exception as e:
            logger.error(f"Error rendering training table: {str(e)}")
            return None

    @reactive.Effect
    @reactive.event(input.add_training_btn)
    def handle_add_training():
        """Handle adding new training record."""
        try:
            if not input.new_training_course() or not input.new_training_user():
                ui.notification_show("Please select both course and user", type="error")
                return
                
            engine = DatabaseConfig.get_db_engine()
            new_record = {
                'userid': input.new_training_user(),
                'courseid': input.new_training_course(),
                'completion_date': input.new_training_date(),
                'status': 'Current'
            }
            
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO training_status_data 
                    (userid, courseid, completion_date, status)
                    VALUES (:userid, :courseid, :completion_date, :status)
                """)
                conn.execute(query, new_record)
                conn.commit()
                
            ui.notification_show("Training record added successfully", type="success")
            fetch_training_data()  # Refresh data
            
        except Exception as e:
            logger.error(f"Error adding training record: {str(e)}")
            ui.notification_show("Error adding training record", type="error")

    @reactive.Effect
    @reactive.event(input.update_training_btn)
    def handle_update_training():
        """Handle updating existing training record."""
        record_id = selected_record.get()
        if not record_id:
            ui.notification_show("Please select a record to update", type="error")
            return
            
        try:
            engine = DatabaseConfig.get_db_engine()
            with engine.connect() as conn:
                query = text("""
                    UPDATE training_status_data 
                    SET completion_date = :completion_date
                    WHERE id = :id
                """)
                conn.execute(query, {
                    'id': record_id,
                    'completion_date': input.edit_training_date()
                })
                conn.commit()
                
            ui.notification_show("Training record updated successfully", type="success")
            fetch_training_data()  # Refresh data
            
        except Exception as e:
            logger.error(f"Error updating training record: {str(e)}")
            ui.notification_show("Error updating training record", type="error")

    @reactive.Effect
    @reactive.event(input.delete_training_btn)
    def handle_delete_training():
        """Handle deleting training record."""
        record_id = selected_record.get()
        if not record_id:
            ui.notification_show("Please select a record to delete", type="error")
            return
            
        try:
            engine = DatabaseConfig.get_db_engine()
            with engine.connect() as conn:
                query = text("DELETE FROM training_status_data WHERE id = :id")
                conn.execute(query, {'id': record_id})
                conn.commit()
                
            ui.notification_show("Training record deleted successfully", type="success")
            selected_record.set(None)  # Clear selection
            fetch_training_data()  # Refresh data
            
        except Exception as e:
            logger.error(f"Error deleting training record: {str(e)}")
            ui.notification_show("Error deleting training record", type="error")

    @reactive.Effect
    @reactive.event(input.training_table_selected_rows)
    def handle_selection():
        """Update selected record when table selection changes."""
        selected_indices = input.training_table_selected_rows()
        if selected_indices and len(selected_indices) > 0:
            df = filtered_data.get()
            if not df.empty and selected_indices[0] < len(df):
                record_id = df.iloc[selected_indices[0]]['id']
                selected_record.set(record_id)
                
                # Pre-fill edit form
                completion_date = pd.to_datetime(df.iloc[selected_indices[0]]['completion_date'])
                ui.update_date("edit_training_date", value=completion_date.date())
        else:
            selected_record.set(None)

    @reactive.Effect
    def _trigger_init():
        """Trigger initialization after session starts."""
        session.on_ended(lambda: None)  # Ensure cleanup
        init_trigger.set(1)
        logger.info("Initialization triggered")

    return {
        'selected_record': selected_record,
        'training_data': training_data,
        'filtered_data': filtered_data,
        'courses': courses,
    }