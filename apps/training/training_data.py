import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from typing import Optional, Dict, Set
from dataclasses import dataclass
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

@dataclass
class TrainingRecord:
    """Data structure for training information."""
    id: int
    first_name: str
    last_name: str
    courseid: str
    venue: str
    completion_date: str
    due_date: str
    status: str
    eligibility: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'TrainingRecord':
        """Create TrainingRecord from dictionary."""
        return cls(**data)

class TrainingDataManager:
    """Handle training data operations."""
    
    TRAINING_QUERY = """
        SELECT 
            t.id,
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

    COURSE_TYPES_QUERY = """
        SELECT DISTINCT courseid 
        FROM training_course_data
    """

    @staticmethod
    def get_training_data() -> pd.DataFrame:
        """Get training data with error handling and validation."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(TrainingDataManager.TRAINING_QUERY), conn)
            
            # Validate required columns
            required_columns = {'id', 'courseid', 'status', 'completion_date'}
            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
                
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

    @staticmethod
    def get_valid_training_types() -> Set[str]:
        """Get all valid training types with error handling."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text(TrainingDataManager.COURSE_TYPES_QUERY))
                types = {str(row[0]).strip() for row in result if row[0]}
                logger.info(f"Retrieved {len(types)} valid training types")
                return types
                
        except Exception as e:
            logger.error(f"Error getting training types: {str(e)}")
            raise

    @staticmethod
    def filter_training_data(
        df: pd.DataFrame,
        search_term: Optional[str] = None,
        status: Optional[str] = None
    ) -> pd.DataFrame:
        """Filter training data based on search term and status."""
        if df.empty:
            return df

        if search_term:
            search_term = search_term.lower()
            df = df[
                df['courseid'].str.contains(search_term, na=False) |
                df['venue'].str.contains(search_term, na=False)
            ]
        
        if status and status != 'All':
            df = df[df['status'].str.lower() == status.lower()]
            
        return df

def server_training_data(input, output, session):
    """Server logic for training data with improved error handling and state management."""
    
    # Initialize reactive values
    training_data = reactive.Value(pd.DataFrame())
    valid_types = reactive.Value(set())
    
    @reactive.Effect
    def load_initial_data():
        """Load initial data with error handling."""
        try:
            results = TrainingDataManager.get_training_data()
            training_data.set(results)
            logger.info(f"Successfully loaded {len(results)} training records")
        except Exception as e:
            error_msg = f"Failed to load training data: {str(e)}"
            logger.error(error_msg)
            ui.notification_show(
                error_msg,
                type="error",
                duration=None
            )

    @reactive.Effect
    def load_training_types():
        """Load valid training types with error handling."""
        try:
            types = TrainingDataManager.get_valid_training_types()
            valid_types.set(types)
            logger.info(f"Loaded {len(types)} valid training types")
        except Exception as e:
            error_msg = f"Failed to load training types: {str(e)}"
            logger.error(error_msg)
            ui.notification_show(
                error_msg,
                type="error",
                duration=None
            )

    @reactive.calc
    def filtered_data():
        """Calculate filtered data with input validation."""
        df = training_data.get()
        if df.empty:
            return df

        search_term = getattr(input, 'search_course', lambda: None)()
        status = getattr(input, 'status_filter_training', lambda: 'All')()
        
        return TrainingDataManager.filter_training_data(df, search_term, status)

    @output
    @render.data_frame
    def training_table():
        """Render training data table with configured display options."""
        df = filtered_data()
        
        # Format display data
        display_df = df.copy()
        if not display_df.empty:
            # Format dates for display
            date_columns = ['completion_date', 'due_date']
            for col in date_columns:
                if col in display_df.columns:
                    display_df[col] = display_df[col].dt.strftime('%Y-%m-%-d')
        
        return render.DataGrid(
            display_df,
            filters=False,
            height="400px",
            selection_mode="row"
        )

    @output
    @render.text
    def record_count_training():
        """Display record count with percentage."""
        filtered_count = len(filtered_data())
        total_count = len(training_data.get())
        percentage = (filtered_count / total_count * 100) if total_count > 0 else 0
        return f"Showing {filtered_count:,} of {total_count:,} records ({percentage:.1f}%)"