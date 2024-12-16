import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from shiny import App, ui, reactive, render
import sys
from dotenv import load_dotenv
import traceback
from libs.database.db_engine import DatabaseConfig
from sqlalchemy.sql import text

# Import ui components
from apps.dashboard.ui import create_dashboard_panel
from apps.member.ui import create_member_panel
from apps.training.ui import create_training_panel
from apps.login.ui import create_login_page

# Import server components
from apps.member.personal_data import server_personal_data
from apps.dashboard.dashboard import server_dashboard_data
from apps.training.training_data import server_training_data
from apps.login.server import server_login

class ApplicationConfig:
    REQUIRED_ENV_VARS = [
        'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME'
    ]
    
    @staticmethod
    def load_environment() -> None:
        """Load and validate environment variables."""
        load_dotenv()
        
        missing_vars = [var for var in ApplicationConfig.REQUIRED_ENV_VARS 
                       if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        try:
            engine = DatabaseConfig.get_db_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logging.info("Database connection successful")
        except Exception as e:
            raise EnvironmentError(f"Failed to connect to database: {str(e)}")

class LoggingConfig:
    """Logging configuration management."""
    
    @staticmethod
    def setup_logging() -> None:
        """Configure application logging."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                RotatingFileHandler(
                    log_dir / "app.log",
                    maxBytes=1024 * 1024,  # 1MB
                    backupCount=5
                ),
                logging.StreamHandler(sys.stdout)
            ]
        )

def create_main_content():
    """Create the main application content."""
    return ui.div(        
        ui.navset_bar(
            create_dashboard_panel(),
            create_member_panel(),
            create_training_panel(),
            id="selected_navset_bar",
            
            title=ui.tags.div(
                ui.img(src="sslogo.jpg", height="90px", style="margin:5px;"),
                ui.h4(" " + "Data Management System"), 
                style="display: flex; align-items: center; gap: 10px; font-size: 40; font-weight: bold; inline=True"
            ),
            bg="light",
            inverse=True,
        )
    )

# Enhanced app UI with responsive design
app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.meta(
            name="viewport",
            content="width=device-width, initial-scale=1.0"
        ),
        # Add responsive CSS
        ui.tags.style("""
            @media (max-width: 768px) {
                .shiny-input-container {
                    width: 100% !important;
                }
                .col-sm-4, .col-sm-8 {
                    width: 100% !important;
                    padding: 10px;
                }
                .nav-tabs {
                    display: flex;
                    flex-wrap: wrap;
                }
            }
            /* Add smooth transitions */
            .tab-pane {
                transition: all 0.3s ease-in-out;
            }
            /* Improve loading states */
            .shiny-busy {
                opacity: 0.5;
                transition: opacity 0.3s;
            }
            /* Responsive table */
            .table-responsive {
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }
        """)
    ),
    ui.include_css("static/css/styles.css"),
    ui.output_ui("page_content"),
    
    # Add loading spinner
    ui.tags.div(
        ui.tags.div(
            class_="spinner-border text-primary",
            role="status",
            style="display: none;"
        ),
        id="loading-spinner",
        style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 9999;"
    )
)

def update_training_statuses():
    """Update training due dates, status, and eligibility."""
    engine = DatabaseConfig.get_db_engine()
    
    try:
        with engine.connect() as conn:
            # Update due dates
            due_date_query = text("""
                UPDATE training_status_data t
                SET due_date = t.completion_date + (c.frequency_in_months * INTERVAL '1 month')
                FROM training_course_data c
                WHERE t.courseid = c.courseid
                AND t.completion_date IS NOT NULL
            """)
            
            # Update training status
            status_query = text("""
                UPDATE training_status_data
                SET status = 
                    CASE 
                        WHEN completion_date IS NULL THEN NULL
                        WHEN CAST(due_date AS DATE) >= CURRENT_DATE THEN 'Current'
                        ELSE 'Overdue'
                    END
                WHERE completion_date IS NOT NULL
            """)
            
            # Update eligibility query
            eligibility_query = text("""
                UPDATE personal_data p
                SET eligibility = 
                    CASE 
                        WHEN NOT EXISTS (
                            SELECT 1 
                            FROM training_course_data c
                            WHERE NOT EXISTS (
                                SELECT 1 
                                FROM training_status_data t
                                WHERE t.userid = p.userid 
                                AND t.courseid = c.courseid
                                AND t.status = 'Current'
                            )
                        ) THEN 'Eligible'
                        ELSE 'Ineligible'
                    END
            """)
            
            conn.execute(due_date_query)
            conn.execute(status_query)
            conn.execute(eligibility_query)
            conn.commit()
            
            logging.info("Successfully updated training statuses and eligibility")
            
    except Exception as e:
        logging.error(f"Error updating training statuses: {str(e)}")
        raise

def server(input, output, session):
    """Main server function that coordinates all components."""
    
    # Initialize login server
    login_data = server_login(input, output, session)
    
    # Initialize other server components
    server_personal_data(input, output, session)
    server_dashboard_data(input, output, session)
    server_training_data(input, output, session)
    
    @output
    @render.ui
    def page_content():
        """Render either login page or main content based on authentication state."""
        login_data["login_attempt"].get()  # Ensure reactivity to login attempts
        
        if not login_data["is_authenticated"].get():
            return create_login_page()
        
        return create_main_content()

# Initialize app
www_dir = Path(__file__).parent / "www"
app = App(app_ui, server, static_assets=www_dir)

if __name__ == "__main__":
    try:
        # Initialize logging
        LoggingConfig.setup_logging()
        
        # Load environment variables
        ApplicationConfig.load_environment()
        
        # Update training statuses before starting app
        update_training_statuses()
        
        options = {
            'host': os.getenv('HOST', '0.0.0.0'),
            'port': int(os.getenv('PORT', 8000)),
        }
        logging.info(f"Starting application server with options: {options}")
        app.run(**options)
    except Exception as e:
        logging.critical(f"Critical error starting app: {str(e)}")
        logging.critical(traceback.format_exc())
        sys.exit(1)