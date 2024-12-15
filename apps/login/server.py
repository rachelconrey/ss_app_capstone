from shiny import reactive, render, ui
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from passlib.hash import pbkdf2_sha256
import logging
from libs.database.db_engine import DatabaseConfig

logger = logging.getLogger(__name__)

def validate_login(username: str, password: str) -> bool:
    """
    Validate login credentials against database with secure password handling.
    Automatically upgrades plain text passwords to hashed versions.
    """
    try:
        engine = DatabaseConfig.get_db_engine()
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    SELECT password 
                    FROM login_data 
                    WHERE userid = :username
                """),
                {"username": username}
            )
            stored_password = result.scalar()
            
            if not stored_password:
                logger.warning(f"Login attempt failed: User {username} not found")
                return False
            
            try:
                if not stored_password.startswith('$pbkdf2'):
                    if password == stored_password:
                        hashed_password = pbkdf2_sha256.hash(password)
                        conn.execute(
                            text("""
                                UPDATE login_data 
                                SET password = :hashed_password 
                                WHERE userid = :username
                            """),
                            {
                                "username": username,
                                "hashed_password": hashed_password
                            }
                        )
                        return True
                    return False
                
                return pbkdf2_sha256.verify(password, stored_password)
                
            except ValueError as e:
                logger.error(f"Password verification error for user {username}: {str(e)}")
                return False
                
    except SQLAlchemyError as e:
        logger.error(f"Database error in login validation: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in login validation: {str(e)}")
        return False

def server_login(input, output, session):
    """Server logic for login functionality."""
    # Reactive values
    is_authenticated = reactive.Value(False)
    message = reactive.Value("")
    
    # Add a reactive value to track login state changes
    login_attempt = reactive.Value(0)

    @reactive.Effect
    @reactive.event(input.login_button)
    def handle_login():
        """Handle login button click."""
        try:
            username = input.username()
            password = input.password()
            
            if not username or not password:
                message.set("Please enter both username and password")
                return
                
            # Update login attempt counter to trigger reactivity
            login_attempt.set(login_attempt.get() + 1)
            
            if validate_login(username, password):
                message.set("Login successful!")
                is_authenticated.set(True)
                logger.info(f"Successful login for user: {username}")
                ui.notification_show(
                    "Login successful! Loading dashboard...",
                    type="message",
                    duration=2
                )
            else:
                message.set("Invalid username or password")
                is_authenticated.set(False)
                logger.warning(f"Failed login attempt for user: {username}")
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            message.set("An error occurred during login")
            is_authenticated.set(False)

    @output
    @render.text
    def login_message():
        """Render login message."""
        # Depend on login_attempt to ensure proper reactivity
        login_attempt.get()
        return message.get()

    return {
        "is_authenticated": is_authenticated,
        "message": message,
        "login_attempt": login_attempt
    }