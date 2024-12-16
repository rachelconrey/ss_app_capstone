import pandas as pd
from sqlalchemy import text
from shiny import reactive, render, ui
import logging
from libs.database.db_engine import DatabaseConfig
from libs.crud_manager import CRUDManager

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
            
            if df.empty:
                return pd.DataFrame()
                    
            df = PersonalDataManager._clean_member_data(df)
            
            return df
                    
        except Exception:
            return pd.DataFrame()

    @staticmethod
    def _clean_member_data(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize member data."""
        try:
            # Convert string columns to lowercase for consistent filtering
            string_columns = ['first_name', 'last_name', 'email']
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].str.lower().str.strip()
            
            # Replace NaN values with empty strings
            df = df.fillna('')
            
            return df
            
        except Exception as e:
            logger.warning(f"Error during data cleaning: {str(e)}")
            return df  

def server_personal_data(input, output, session):
    """Server logic for personal data with CRUD operations."""
    
    # Reactive values for managing state
    selected_member = reactive.Value(None)
    member_data = reactive.Value(pd.DataFrame())
    filtered_data = reactive.Value(pd.DataFrame())
    
    def fetch_member_data():
        """Fetch member data from database."""
        try:
            data = PersonalDataManager.get_member_data()
            member_data.set(data)
            apply_filters()  # Apply filters after fetching new data
        except Exception:
            pass
                
    # Add reactive effect for refresh button
    @reactive.Effect
    @reactive.event(input.refresh_data)
    def _handle_refresh():
        """Handle refresh button click."""
        with ui.Progress(min=0, max=100) as p:
            p.set(message="Refreshing data...", value=0)
            fetch_member_data()
            p.set(value=100)
        ui.notification_show(
            "Data refreshed successfully",
            type="success",
            duration=2000
        )
        
    def apply_filters():
        """Apply search and status filters to member data."""
        df = member_data.get()
        if df.empty:
            filtered_data.set(pd.DataFrame())
            return

        # Apply search filter
        search_term = input.search_member().lower().strip()
        if search_term:
            mask = (
                df['first_name'].str.contains(search_term, na=False) |
                df['last_name'].str.contains(search_term, na=False)
            )
            df = df[mask]

        # Apply status filter
        status_filter = input.status_filter_member()
        if status_filter != "All":
            df = df[df['eligibility'] == status_filter]

        filtered_data.set(df)

    @reactive.Effect
    def _load_initial_data():
        """Load initial member data."""
        fetch_member_data()

    @reactive.Effect
    @reactive.event(input.add_member_btn)
    def handle_add_member():
        """Handle adding new member."""
        try:
            member_data = {
                'first_name': input.new_first_name(),
                'last_name': input.new_last_name(),
                'email': input.new_email(),
                'phone_number': input.new_phone(),
                'ice_first_name': input.new_ice_first_name(),
                'ice_last_name': input.new_ice_last_name(),
                'ice_phone_number': input.new_ice_phone()
            }
            
            CRUDManager.add_member(member_data)
            
            # Clear form
            for field in ['first_name', 'last_name', 'email', 'phone', 
                         'ice_first_name', 'ice_last_name', 'ice_phone']:
                ui.update_text(f"new_{field}", value="")
            
            ui.notification_show(
                "Member added successfully",
                type="success",
                duration=3000
            )
            fetch_member_data()  # Refresh the table
            
        except Exception as e:
            logger.error(f"Error adding member: {str(e)}")
            ui.notification_show(
                f"Error adding member: {str(e)}",
                type="error",
                duration=5000
            )

    @reactive.Effect
    @reactive.event(input.update_member_btn)
    def handle_update_member():
        """Handle updating member."""
        try:
            member_id = selected_member.get()
            if not member_id:
                ui.notification_show(
                    "Please select a member to update",
                    type="error",
                    duration=5000
                )
                return

            member_data = {
                'first_name': input.edit_first_name(),
                'last_name': input.edit_last_name(),
                'email': input.edit_email(),
                'phone_number': input.edit_phone(),
                'ice_first_name': input.edit_ice_first_name(),
                'ice_last_name': input.edit_ice_last_name(),
                'ice_phone_number': input.edit_ice_phone()
            }
            
            try:
                success = CRUDManager.update_member(member_id, member_data)
                
                if success:
                    ui.notification_show(
                        "Member updated successfully",
                        type="success",
                        duration=3000
                    )
                    fetch_member_data()
                else:
                    ui.notification_show(
                        "Failed to update member - no record found",
                        type="error",
                        duration=5000
                    )
                    
            except Exception as e:
                ui.notification_show(
                    f"Error updating member: {str(e)}",
                    type="error",
                    duration=5000
                )
                logger.error(f"Error in update operation: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error preparing update data: {str(e)}")
            ui.notification_show(
                "Error preparing update data",
                type="error",
                duration=5000
            )

    @reactive.Effect
    @reactive.event(input.delete_member_btn)
    def handle_delete_member():
        """Handle deleting member."""
        try:
            member_id = selected_member.get()
            logger.info(f"Delete requested for member_id: {member_id}")
            
            if not member_id:
                ui.notification_show(
                    "Please select a member to delete",
                    type="error",
                    duration=5000
                )
                return

            # Log the current data before deletion
            df = member_data.get()
            if not df.empty:
                member_info = df[df['id'] == member_id]
                if not member_info.empty:
                    logger.info(f"Attempting to delete member: ID={member_id}, "
                            f"Data={member_info.iloc[0].to_dict()}")
                else:
                    logger.error(f"Member ID {member_id} not found in current data")

            success = CRUDManager.delete_member(member_id)
            
            if success:
                logger.info(f"Successfully deleted member {member_id}")
                # Clear selection first
                selected_member.set(None)
                # Show success message
                ui.notification_show(
                    "Member deleted successfully",
                    type="success",
                    duration=3000
                )
                # Finally refresh the data
                fetch_member_data()
            else:
                logger.error(f"Failed to delete member {member_id}")
                ui.notification_show(
                    "Failed to delete member - please try again",
                    type="error",
                    duration=5000
                )
                
        except Exception as e:
            logger.error(f"Error in handle_delete_member: {str(e)}")
            ui.notification_show(
                f"Error deleting member: {str(e)}",
                type="error",
                duration=5000
            )

    @output
    @render.data_frame
    def member_table():
        """Render member data table."""
        df = filtered_data.get()  # Use filtered data instead of raw data
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
            selection_mode="row",
            height="800px",
            width="100%"
        )

    @reactive.Effect
    @reactive.event(input.member_table_selected_rows)
    def handle_selection():
        """Update selected member when table selection changes."""
        selected_indices = input.member_table_selected_rows()
        if selected_indices and len(selected_indices) > 0:
            df = filtered_data.get()  # Use filtered data for selection
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
            # Clear the edit form when nothing is selected
            for field in ['first_name', 'last_name', 'email', 'phone', 
                         'ice_first_name', 'ice_last_name', 'ice_phone']:
                ui.update_text(f"edit_{field}", value="")

    # Add reactive effect for search/filter changes
    @reactive.Effect
    @reactive.event(input.search_member, input.status_filter_member)
    def _handle_filters():
        """Handle changes to search or filter inputs."""
        apply_filters()

    return {
        'selected_member': selected_member,
        'member_data': member_data,
        'filtered_data': filtered_data,
        'fetch_member_data': fetch_member_data
    }