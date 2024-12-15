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
            message.set("Login successful!")
            logger.info(f"Successful login for user: {username}")
        else:
            message.set("Invalid username or password")
            is_authenticated.set(False)
            logger.warning(f"Failed login attempt for user: {username}")

    @output
    @render.text
    def login_message():
        """Render login message."""
        return message.get()

    return {
        "is_authenticated": is_authenticated,
        "message": message
    }

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
            message.set("Login successful!")
        else:
            message.set("Invalid username or password")
            is_authenticated.set(False)

    @output
    @render.text
    def login_message():
        """Render login message."""
        return message.get()

    return {
        "is_authenticated": is_authenticated,
        "message": message
    }