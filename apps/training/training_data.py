# training_data.py
import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from typing import Optional, Dict, Set
from dataclasses import dataclass
from libs.database.db_engine import DatabaseConfig
from datetime import datetime

logger = logging.getLogger(__name__)

class TrainingDataManager:
    """Handle training data operations with CRUD functionality."""
    
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
    def initialize_data():
        """Load initial training data."""
        try:
            data = TrainingDataManager.get_training_data()
            training_data.set(data)
        except Exception as e:
            ui.notification_show(
                f"Error loading training data: {str(e)}",
                type="error"
            )
    
    def update_training_table():
        """Refresh training data table."""
        try:
            data = TrainingDataManager.get_training_data()
            training_data.set(data)
        except Exception as e:
            ui.notification_show(
                f"Error refreshing training data: {str(e)}",
                type="error"
            )
        
    @output
    @render.data_frame
    def training_table():
        """Render training data table."""
        df = training_data.get()
        return render.DataGrid(
            df,
            row_selection_mode="single",
            height="400px"
        )
        
    module_data = {
        'selected_record': selected_record,
        'training_data': training_data,
        'update_training_table': update_training_table
    }
    
    # Important: Return the module data
    return module_data