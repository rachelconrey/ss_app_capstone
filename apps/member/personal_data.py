import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

class PersonalDataManager:
    """Handle personal data operations."""
    
    MEMBER_QUERY = """
        SELECT 
            p.id,
            p.userid,
            p.first_name,
            p.last_name,
            p.email,
            p.phone_number,
            p.ice_first_name,
            p.ice_last_name,
            p.ice_phone_number,
            p.eligibility
        FROM personal_data p
        ORDER BY 
            p.last_name ASC,
            p.first_name ASC
    """
    
    @staticmethod
    def get_member_data() -> pd.DataFrame:
        """Get member data with error handling and validation."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql_query(text(PersonalDataManager.MEMBER_QUERY), conn)
            
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
        
        # Replace NaN values with empty strings
        df = df.fillna('')
        
        return df

def server_personal_data(input, output, session):
    """Server logic for personal data with CRUD operations."""
    
    # Reactive values for managing state
    selected_member = reactive.Value(None)
    member_data = reactive.Value(pd.DataFrame())
    
    @reactive.Effect
    def _load_initial_data():
        """Load initial member data."""
        try:
            data = PersonalDataManager.get_member_data()
            member_data.set(data)
        except Exception as e:
            ui.notification_show(
                f"Error loading member data: {str(e)}",
                type="error",
                duration=5000
            )

    @reactive.Effect
    @reactive.event(input.update_member_btn, input.add_member_btn, input.delete_member_btn)
    def refresh_data():
        """Refresh data after any CRUD operation."""
        try:
            data = PersonalDataManager.get_member_data()
            member_data.set(data)
            logger.info("Member data refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing member data: {str(e)}")
            ui.notification_show(
                "Error refreshing data. Please try again.",
                type="error",
                duration=5000
            )

    @output
    @render.data_frame
    def member_table():
        """Render member data table."""
        df = member_data.get()
        if df.empty:
            return None
            
        df = df.copy()
        # Format names for display
        df['first_name'] = df['first_name'].str.title()
        df['last_name'] = df['last_name'].str.title()
        
        display_columns = [
            'first_name', 'last_name', 'email', 'phone_number',
            'ice_first_name', 'ice_last_name', 'ice_phone_number', 'eligibility'
        ]
        
        column_labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email',
            'phone_number': 'Phone',
            'ice_first_name': 'ICE First Name',
            'ice_last_name': 'ICE Last Name',
            'ice_phone_number': 'ICE Phone',
            'eligibility': 'Status'
        }
        
        display_df = df[display_columns].rename(columns=column_labels)
        
        return render.DataGrid(
            display_df,
            row_selection_mode="single",
            height="400px",
            width="100%"
        )

    @reactive.Effect
    @reactive.event(input.member_table_selected_rows)
    def handle_selection():
        """Update selected member when table selection changes."""
        selected_indices = input.member_table_selected_rows()
        if selected_indices and len(selected_indices) > 0:
            df = member_data.get()
            if not df.empty and selected_indices[0] < len(df):
                selected_row = df.iloc[selected_indices[0]]
                selected_member.set(selected_row['id'])
                
                # Pre-fill the edit form
                ui.update_text("edit_first_name", value=selected_row['first_name'].title())
                ui.update_text("edit_last_name", value=selected_row['last_name'].title())
                ui.update_text("edit_email", value=selected_row['email'])
                ui.update_text("edit_phone", value=selected_row['phone_number'])
                ui.update_text("edit_ice_first_name", value=selected_row['ice_first_name'])
                ui.update_text("edit_ice_last_name", value=selected_row['ice_last_name'])
                ui.update_text("edit_ice_phone", value=selected_row['ice_phone_number'])
        else:
            selected_member.set(None)

    return {
        'selected_member': selected_member,
        'member_data': member_data,
        'refresh_data': refresh_data
    }