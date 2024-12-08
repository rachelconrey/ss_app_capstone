import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

class TrainingDataManager:
    """Handle training data operations."""
    
    @staticmethod
    def get_training_data() -> pd.DataFrame:
        """Get training data."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            query = text("""
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
            """)
            
            with engine.connect() as conn:
                df = pd.read_sql_query(query, conn)
                logger.info(f"Successfully fetched {len(df)} training records")
                return df
                
        except Exception as e:
            logger.error(f"Error fetching training data: {str(e)}")
            raise

    @staticmethod
    def get_valid_training_types() -> set:
        """Get all valid training types from the database."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            with engine.connect() as conn:
                query = text("""
                SELECT DISTINCT courseid 
                FROM training_course_data
                """)
                
                result = conn.execute(query)
                return {row[0] for row in result}
                
        except Exception as e:
            logger.error(f"Error getting training types: {str(e)}")
            raise

def server_training_data(input, output, session):
    """Server logic for training data."""
    
    # Initialize reactive values
    training_data = reactive.Value(pd.DataFrame())
    valid_types = reactive.Value(set())
    
    # Load initial training data
    @reactive.Effect
    def _load_training_data():
        try:
            results = TrainingDataManager.get_training_data()
            training_data.set(results)
            logger.info(f"Successfully loaded {len(results)} training records")
        except Exception as e:
            logger.error(f"Error loading training data: {str(e)}")
            ui.notification_show(
                "Failed to load training data",
                type="error"
            )

    # Load valid training types
    @reactive.Effect
    def _load_training_types():
        try:
            types = TrainingDataManager.get_valid_training_types()
            valid_types.set(types)
            logger.info(f"Loaded {len(types)} valid training types")
        except Exception as e:
            logger.error(f"Error loading training types: {str(e)}")
            ui.notification_show(
                "Failed to load training types",
                type="error"
            )

    @output
    @render.data_frame
    def training_table():
        """Render training data table."""
        df = training_data.get()
        if df.empty:
            # Return empty DataFrame with expected columns
            return render.DataGrid(
                pd.DataFrame(columns=[
                    'id', 'first_name', 'last_name', 'courseid', 
                    'venue', 'completion_date', 'due_date', 
                    'status', 'eligibility'
                ]),
                filters=False,
                height="400px"
            )
        
        # Ensure data is properly formatted
        df = df.copy()
        
        # Safely handle date conversions
        try:
            # Convert to datetime if they aren't already
            if 'completion_date' in df.columns:
                df['completion_date'] = pd.to_datetime(df['completion_date']).fillna('')
                # Only format if not empty
                df.loc[df['completion_date'] != '', 'completion_date'] = \
                    df.loc[df['completion_date'] != '', 'completion_date'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')
                
            if 'due_date' in df.columns:
                df['due_date'] = pd.to_datetime(df['due_date']).fillna('')
                # Only format if not empty
                df.loc[df['due_date'] != '', 'due_date'] = \
                    df.loc[df['due_date'] != '', 'due_date'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '')
        except Exception as e:
            logger.error(f"Error formatting dates: {str(e)}")
            # If date formatting fails, just pass the original values
            
        # Fill NA values appropriately
        string_columns = ['first_name', 'last_name', 'courseid', 'venue', 'status', 'eligibility']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].fillna('')
        
        return render.DataGrid(
            df,
            filters=False,
            height="400px"
        )

    # @output
    # @render.ui
    # def training_type_choices():
    #     """Render training type choices."""
    #     types = valid_types.get()
    #     return ui.input_select(
    #         "training_type",
    #         "Filter by Training Type",
    #         choices=["ALL"] + sorted(list(types))
    #     )