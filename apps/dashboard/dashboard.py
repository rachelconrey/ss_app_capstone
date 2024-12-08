from typing import Dict, Any
from shiny import render, ui, reactive
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import pandas as pd
import logging
import seaborn as sns
from libs.database.db_engine import DatabaseConfig
from functools import wraps
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

def handle_db_errors(func):
    """Decorator to handle database operation errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            return "Error loading data"
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            return "Unexpected error occurred"
    return wrapper

class DashboardMetrics:
    """Handle dashboard metrics calculations and caching."""
    
    _cache: Dict[str, Any] = {}
    CACHE_DURATION = timedelta(minutes=5)
    
    @classmethod
    def get_member_metrics(cls) -> Dict[str, int]:
        """Get member counts with caching."""
        cache_key = "member_metrics"
        if cache_key in cls._cache:
            cached_value, timestamp = cls._cache[cache_key]
            if datetime.now() - timestamp < cls.CACHE_DURATION:
                return cached_value

        try:
            engine = DatabaseConfig.get_db_engine()
            with engine.connect() as conn:
                query = text("""
                    SELECT 
                        COUNT(*) as total_members,
                        SUM(CASE WHEN eligibility = 'Eligible' THEN 1 ELSE 0 END) as eligible_members,
                        SUM(CASE WHEN eligibility = 'Ineligible' THEN 1 ELSE 0 END) as ineligible_members
                    FROM personal_data
                """)
                result = conn.execute(query).fetchone()
                logger.info("Successfully executed metrics query")
                
                metrics = {
                    'total': result[0] or 0,
                    'eligible': result[1] or 0,
                    'ineligible': result[2] or 0
                }
                
                cls._cache[cache_key] = (metrics, datetime.now())
                logger.info(f"Updated metrics cache: {metrics}")
                return metrics
                
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return {'total': 0, 'eligible': 0, 'ineligible': 0}

def server_dashboard_data(input, output, session):
    """Server logic for dashboard data."""
    
    # Initialize reactive value for metrics
    metrics = reactive.Value({'total': 0, 'eligible': 0, 'ineligible': 0})
    
    @reactive.Effect
    def update_metrics():
        """Update metrics in reactive value."""
        try:
            new_metrics = DashboardMetrics.get_member_metrics()
            metrics.set(new_metrics)
            logger.info("Dashboard metrics updated successfully")
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
            metrics.set({'total': 0, 'eligible': 0, 'ineligible': 0})
            ui.notification_show(
                "Failed to load dashboard metrics",
                type="error"
            )
            
    @render.plot 
    def plot():  
        ax = sns.histplot(data=training_percentage, x="courseid", bins=input.n())  
        ax.set_title("Course Completion Summary")
        ax.set_xlabel("Course")
        ax.set_ylabel("Percentage Completed")
        return ax  

    

    @output
    @render.text
    def total_members() -> str:
        """Display total members count."""
        return f"{metrics.get()['total']:,}"

    @output
    @render.text
    def eligible_members() -> str:
        """Display eligible members count."""
        return f"{metrics.get()['eligible']:,}"

    @output
    @render.text
    def ineligible_members() -> str:
        """Display ineligible members count."""
        return f"{metrics.get()['ineligible']:,}"