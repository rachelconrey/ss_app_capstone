import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

class PersonalDataManager:
    """Handle personal data operations and filtering."""
    
    @staticmethod
    def get_member_data() -> pd.DataFrame:  # Fixed indentation
        engine = DatabaseConfig.get_db_engine()
        
        try:
            query = text("""
                SELECT 
                    id,
                    first_name,
                    last_name,
                    eligibility,
                    email,
                    phone_number,
                    CONCAT(ice_first_name, ' ', ice_last_name) AS ice_name,
                    ice_phone_number
                FROM personal_data 
                ORDER BY last_name, first_name
            """)
            
            with engine.connect() as conn:
                df = pd.read_sql_query(query, conn)
                logger.info(f"Successfully fetched {len(df)} member records")
                return df
                
        except Exception as e:
            logger.error(f"Error fetching member data: {str(e)}")
            raise

def server_personal_data(input, output, session):
    """Server logic for personal data page."""
    
    # Initialize reactive value for data
    data = reactive.Value(pd.DataFrame())
    
    @reactive.Effect
    def load_initial_data():
        """Load initial data on startup."""
        try:
            results = PersonalDataManager.get_member_data()
            data.set(results)
            logger.info(f"Successfully loaded {len(results)} member records")
        except Exception as e:
            logger.error(f"Error loading member data: {str(e)}")
            ui.notification_show(
                "Failed to load member data",
                type="error"
            )

    @reactive.calc
    def filtered_data():
        """Calculate filtered data based on inputs."""
        df = data.get()
        if df.empty:
            return df

        if hasattr(input, 'search') and input.search():
            search_term = input.search().lower()
            df = df[
                df['first_name'].str.lower().str.contains(search_term, na=False) |
                df['last_name'].str.lower().str.contains(search_term, na=False) |
                df['email'].str.lower().str.contains(search_term, na=False)
            ]
            
        if hasattr(input, 'status_filter') and input.status_filter() != 'All':
            df = df[df['eligibility'] == input.status_filter()]  # Changed from status to eligibility
            
        return df

    @output
    @render.data_frame
    def member_data():
        """Render member data table."""
        df = filtered_data()
        return render.DataGrid(
            df,
            filters=False,
            height="400px"
        )

    @output
    @render.text
    def record_count():
        """Display the count of filtered records."""
        filtered_count = len(filtered_data())
        total_count = len(data.get())
        return f"Showing {filtered_count} of {total_count} records"