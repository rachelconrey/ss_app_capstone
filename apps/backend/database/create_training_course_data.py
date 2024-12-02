import pandas as pd
from pathlib import Path
from db_config import get_db_connection

def create_training_course_table():
    conn = get_db_connection("ss_database")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_course_data (
                id SERIAL PRIMARY KEY,
                courseid VARCHAR(50) NOT NULL UNIQUE,
                frequency_in_months INTEGER NOT NULL,
                venue VARCHAR(100) NOT NULL
            )
        """)
        
        csv_path = Path('apps/backend/database/csv_files/training-course-data.csv')
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO training_course_data (courseid, frequency_in_months, venue)
                VALUES (%s, %s, %s)
                ON CONFLICT (courseid) DO NOTHING
            """, (row['courseid'], row['frequency_in_months'], row['venue']))
        
        conn.commit()
        print("Training course data table created and populated successfully")
        
    except Exception as error:
        print(f"Error while creating training course table: {error}")
        conn.rollback()
        raise
    finally:
        conn.close()