import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

class TrainingDataManager:
    """Handle training data operations with CRUD functionality."""
    
    TRAINING_QUERY = """
        SELECT 
            t.id,
            t.userid,
            p.first_name,
            p.last_name,
            t.courseid,
            c.venue,
            t.completion_date,
            t.due_date,
            t.status,
            p.eligibility
        FROM training_status_data t
        LEFT JOIN personal_data p 
            ON t.userid = p.userid
        INNER JOIN training_course_data c
            ON t.courseid = c.courseid
        ORDER BY 
            t.completion_date DESC NULLS LAST,
            p.last_name ASC
    """
        
    @staticmethod
    def get_training_data() -> pd.DataFrame:
        """Get training data with error handling and validation."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(TrainingDataManager.TRAINING_QUERY), conn)
            
            # Clean data
            df = TrainingDataManager._clean_training_data(df)
            
            logger.info(f"Successfully fetched {len(df)} training records")
            return df
                
        except Exception as e:
            logger.error(f"Error fetching training data: {str(e)}")
            raise

    @staticmethod
    def _clean_training_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize training data."""
        # Convert string columns to lowercase for consistent filtering
        string_columns = ['courseid', 'status', 'venue']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].str.lower().str.strip()
        
        # Convert date columns to datetime
        date_columns = ['completion_date', 'due_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Replace NaN values with empty strings for string columns
        df = df.fillna('')
        
        return df

def server_training_data(input, output, session):
    """Server logic for training data with CRUD operations."""
    
    # Reactive values for managing state
    selected_record = reactive.Value(None)
    training_data = reactive.Value(pd.DataFrame())
    
    @reactive.Effect
    def _load_initial_data():
        """Load initial training data."""
        try:
            data = TrainingDataManager.get_training_data()
            training_data.set(data)
        except Exception as e:
            ui.notification_show(
                f"Error loading training data: {str(e)}",
                type="error"
            )

    @reactive.Effect
    def update_training_table():
        """Refresh training data table."""
        try:
            data = TrainingDataManager.get_training_data()
            training_data.set(data)
            logger.info("Training data table updated successfully")
        except Exception as e:
            logger.error(f"Error refreshing training data: {str(e)}")
            ui.notification_show(
                f"Error refreshing training data: {str(e)}",
                type="error"
            )
        
    @output
    @render.data_frame
    def training_table():
        """Render training data table."""
        df = training_data.get()
        if not df.empty:
            df = df.copy()
            # Format dates for display
            if 'completion_date' in df.columns:
                df['completion_date'] = df['completion_date'].dt.strftime('%Y-%m-%d')
            if 'due_date' in df.columns:
                df['due_date'] = df['due_date'].dt.strftime('%Y-%m-%d')
                
            # Create display columns in desired order
            display_columns = [
                'first_name', 'last_name', 'courseid', 'venue',
                'completion_date', 'due_date', 'status'
            ]
            
            # Rename columns for display
            column_labels = {
                'first_name': 'First Name',
                'last_name': 'Last Name',
                'courseid': 'Course',
                'venue': 'Venue',
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
                height="400px",
                width="100%"
            )
        return None

    # Handle table selection
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
                logger.info(f"Selected training record ID: {record_id}")
                
                # Pre-fill the edit form with current completion date
                current_completion_date = df.iloc[selected_indices[0]]['completion_date']
                if current_completion_date:
                    ui.update_date(
                        "edit_training_date",
                        value=pd.to_datetime(current_completion_date).date()
                    )
        else:
            selected_record.set(None)

    return {
        'selected_record': selected_record,
        'training_data': training_data,
        'update_training_table': update_training_table
    }