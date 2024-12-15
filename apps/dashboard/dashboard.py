import matplotlib
matplotlib.use('Agg')

from typing import Dict, Any
from shiny import render, ui, reactive
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import pandas as pd
import logging
import seaborn as sns
import matplotlib.pyplot as plt
from libs.database.db_engine import DatabaseConfig
from functools import wraps
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

course_data = reactive.Value(pd.DataFrame())

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

    @staticmethod
    def get_course_completion_data() -> pd.DataFrame:
        """Get course completion percentages."""
        engine = DatabaseConfig.get_db_engine()
        
        try:
            query = text("""
                WITH member_count AS (
                SELECT COUNT(DISTINCT userid) as total_members
                FROM personal_data
                ),
                course_completions AS (
                SELECT
                t.courseid,
                COUNT(DISTINCT t.userid) as completed_count
                FROM training_status_data t
                WHERE t.completion_date IS NOT NULL
                GROUP BY t.courseid
                )
                SELECT
                c.courseid,
                COALESCE(cc.completed_count, 0) as completed_count,
                m.total_members,
                ROUND((COALESCE(cc.completed_count, 0)::NUMERIC / m.total_members * 100)::NUMERIC, 2) as completion_percentage
                FROM training_course_data c
                CROSS JOIN member_count m
                LEFT JOIN course_completions cc ON c.courseid = cc.courseid
                ORDER BY c.courseid
            """)
            
            with engine.connect() as conn:
                df = pd.read_sql_query(query, conn)
                logger.info(f"Successfully fetched course completion data")
                return df
                
        except Exception as e:
            logger.error(f"Error getting course completion data: {str(e)}")
            return pd.DataFrame(columns=['courseid', 'completion_percentage'])

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
    
    @reactive.Effect
    def _load_course_data():
        """Load course completion data."""
        try:
            results = DashboardMetrics.get_course_completion_data()
            course_data.set(results)
            logger.info("Course completion data updated successfully")
        except Exception as e:
            logger.error(f"Error loading course data: {str(e)}")
            ui.notification_show(
                "Failed to load course data",
                type="error"
            )

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
    
    @output
    @render.plot(alt="A bar chart showing course completion percentages")
    def plot():
        """Render the course completion plot."""
        # Clear any existing plots
        plt.clf()
        
        # Get the course data
        data = course_data.get()
        
        if data.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No data available', 
                   horizontalalignment='center',
                   verticalalignment='center')
            return fig
        
        # Set the style
        sns.set_style("whitegrid")
        
        # Create figure and axes with specific size
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create bar plot using seaborn
        bars = sns.barplot(data=data, 
                          x='courseid', 
                          y='completion_percentage',
                          ax=ax,
                          color='#7BD953')
        
        ax.set_xlabel("Course ID", fontsize=12)
        ax.set_ylabel("Completion Percentage (%)", fontsize=12)
        
        # Add percentage labels on top of bars
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f%%', padding=3)
        
        plt.xticks(rotation=45, ha='right')
        
        ax.set_ylim(0, 100)
        
        plt.tight_layout()
        
        return fig

    @output
    @render.text
    def training_summary():
        """Display training summary statistics."""
        data = course_data.get()
        if data.empty:
            return "No training data available"
        
        avg_completion = data['completion_percentage'].mean()
        highest_completion = data['completion_percentage'].max()
        lowest_completion = data['completion_percentage'].min()
        
        return (f"Average completion rate: {avg_completion:.1f}% | "
                f"Highest: {highest_completion:.1f}% | "
                f"Lowest: {lowest_completion:.1f}%")

    @output
    @render.text
    def training_summary():
        """Display training summary statistics."""
        data = course_data.get()
        if data.empty:
            return "No training data available"
        
        avg_completion = data['completion_percentage'].mean()
        highest_completion = data['completion_percentage'].max()
        lowest_completion = data['completion_percentage'].min()
        
        return (f"Average completion rate: {avg_completion:.1f}% | "
                f"Highest: {highest_completion:.1f}% | "
                f"Lowest: {lowest_completion:.1f}%")