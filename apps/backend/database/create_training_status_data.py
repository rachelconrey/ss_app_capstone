import pandas as pd
from pathlib import Path
from db_config import get_db_connection

def create_training_status_table():
    conn = get_db_connection("ss_database")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_status_data (
                id SERIAL PRIMARY KEY,
                userid VARCHAR(50) NOT NULL,
                courseid VARCHAR(50) NOT NULL,
                completion_date DATE NOT NULL,
                eligibility VARCHAR(50) NOT NULL,
                FOREIGN KEY (userid) REFERENCES login_data(userid)
                    ON DELETE CASCADE,
                FOREIGN KEY (courseid) REFERENCES training_course_data(courseid)
                    ON DELETE CASCADE,
                UNIQUE (userid, courseid)
            )
        """)
        
        csv_path = Path('apps/backend/database/csv_files/training-status-data.csv')
        df = pd.read_csv(csv_path)
        df['completion_date'] = pd.to_datetime(df['completion_date'])
        
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO training_status_data (userid, courseid, completion_date, eligibility)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (userid, courseid) DO NOTHING
            """, (row['userid'], row['courseid'], row['completion_date'], row['eligibility']))
        
        conn.commit()
        print("Training status data table created and populated successfully")
        
    except Exception as error:
        print(f"Error while creating training status table: {error}")
        conn.rollback()
        raise
    finally:
        conn.close()