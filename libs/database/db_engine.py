from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

class DatabaseConfig:
    """Database configuration and engine management."""
    
    _instance: Optional[Engine] = None
    
    @staticmethod
    def get_db_engine() -> Engine:
        """
        Get or create SQLAlchemy engine with connection pooling.
        
        Returns:
            Engine: SQLAlchemy database engine
        
        Raises:
            ValueError: If required environment variables are missing
        """
        if DatabaseConfig._instance is None:
            # Validate environment variables
            required_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
            # URL encode the password to handle special characters
            password = quote_plus(os.getenv('DB_PASSWORD', ''))
            
            # Use psycopg driver instead of psycopg2
            connection_string = (
                f"postgresql+psycopg://{os.getenv('DB_USER')}:{password}"
                f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
            )
            
            try:
                DatabaseConfig._instance = create_engine(
                    connection_string,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_pre_ping=True,  # Enables automatic reconnection
                    connect_args={
                        "sslmode": "prefer"  # Add SSL mode if needed
                    }
                )
            except Exception as e:
                raise ConnectionError(f"Failed to create database engine: {str(e)}")
        
        return DatabaseConfig._instance