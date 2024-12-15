from shiny import reactive, render, ui
from sqlalchemy import text
from libs.database.db_engine import DatabaseConfig
import logging

logger = logging.getLogger(__name__)

def server_login(input, output, session):
    """Server logic for login functionality."""
    # Reactive values
    is_authenticated = reactive.Value(False)
    message = reactive.Value("")  # Add reactive value for message
    
    def validate_login(username: str, password: str) -> bool:
        """Validate login credentials against database."""
        try:
            engine = DatabaseConfig.get_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM login_data 
                        WHERE userid = :username AND password = :password
                    """),
                    {"username": username, "password": password}
                )
                return result.scalar() > 0
        except Exception as e:
            logger.error(f"Login validation error: {str(e)}")
            return False

    @reactive.Effect
    @reactive.event(input.login_button)
    def handle_login():
        """Handle login button click."""
        username = input.username()
        password = input.password()
        
        if not username or not password:
            message.set("Please enter both username and password")
            return
            
        if validate_login(username, password):
            is_authenticated.set(True)
            message.set("")  # Clear message
        else:
            message.set("Invalid username or password")
            is_authenticated.set(False)

    @output
    @render.text
    def login_message():
        """Render login message."""
        return message.get()
    
    @render.image  
    def logo():
        img = {"src": "www" / "sslogo.jpg", "width": "100px"}
        return img if input.show() else None

    return {"is_authenticated": is_authenticated}