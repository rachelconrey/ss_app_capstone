# personal_data.py
import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from typing import Optional, Dict
from dataclasses import dataclass
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

@dataclass
class MemberRecord:
    """Data structure for member information."""
    id: int
    first_name: str
    last_name: str
    eligibility: str
    email: str
    phone_number: str
    ice_name: str
    ice_phone_number: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'MemberRecord':
        """Create MemberRecord from dictionary."""
        return cls(**data)

class PersonalDataManager:
    """Handle personal data display and filtering operations."""
    
    MEMBER_QUERY = """
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
    """

    @staticmethod
    def get_member_data() -> pd.DataFrame:
        """Fetch member data from database with error handling and validation."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(PersonalDataManager.MEMBER_QUERY), conn)
                
            # Validate required columns
            required_columns = {'id', 'first_name', 'last_name', 'eligibility', 'email'}
            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
                
            # Clean data
            df = PersonalDataManager._clean_member_data(df)
            
            logger.info(f"Successfully fetched {len(df)} member records")
            return df
                
        except Exception as e:
            logger.error(f"Error fetching member data: {str(e)}")
            raise

    @staticmethod
    def _clean_member_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize member data."""
        # Convert string columns to lowercase for consistent filtering
        string_columns = ['first_name', 'last_name', 'email']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].str.lower().str.strip()
        
        # Replace NaN values with empty strings for string columns
        df = df.fillna('')
        
        return df

    @staticmethod
    def filter_members(
        df: pd.DataFrame,
        search_term: Optional[str] = None,
        status: Optional[str] = None
    ) -> pd.DataFrame:
        """Filter member data based on search term and status."""
        if df.empty:
            return df

        if search_term:
            search_term = search_term.lower()
            mask = (
                df['first_name'].str.contains(search_term, na=False) |
                df['last_name'].str.contains(search_term, na=False) |
                df['email'].str.contains(search_term, na=False)
            )
            df = df[mask]
        
        if status and status != 'All':
            df = df[df['eligibility'] == status]
            
        return df

def server_personal_data(input, output, session):
    """Server logic for personal data page with improved error handling and state management."""
    
    data = reactive.Value(pd.DataFrame())
    
    @reactive.Effect
    def load_initial_data():
        """Load initial data with error handling."""
        try:
            results = PersonalDataManager.get_member_data()
            data.set(results)
            logger.info(f"Successfully loaded {len(results)} member records")
        except Exception as e:
            error_msg = f"Failed to load member data: {str(e)}"
            logger.error(error_msg)
            ui.notification_show(
                error_msg,
                type="error",
                duration=None  # Persist until user dismisses
            )

    @reactive.calc
    def filtered_data():
        """Calculate filtered data with input validation."""
        df = data.get()
        if df.empty:
            return df

        search_term = getattr(input, 'search_member', lambda: None)()
        status = getattr(input, 'status_filter_member', lambda: 'All')()
        
        return PersonalDataManager.filter_members(df, search_term, status)

    @output
    @render.data_frame
    def member_data():
        """Render member data table with configurable display options."""
        df = filtered_data()
    
        # Format display data
        display_df = df.copy()
        if not display_df.empty:
            # Capitalize names for display
            display_df['first_name'] = display_df['first_name'].str.title()
            display_df['last_name'] = display_df['last_name'].str.title()
        
        return render.DataGrid(
            display_df,
            filters=False,
            height="400px",
            row_selection_mode="single"
        )

    @output
    @render.text
    def record_count_member():
        """Display record count with percentage."""
        filtered_count = len(filtered_data())
        total_count = len(data.get())
        percentage = (filtered_count / total_count * 100) if total_count > 0 else 0
        return f"Showing {filtered_count:,} of {total_count:,} records ({percentage:.1f}%)"