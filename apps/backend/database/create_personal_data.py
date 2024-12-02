import pandas as pd
from pathlib import Path
from db_config import get_db_connection

def create_personal_table():
    conn = get_db_connection("ss_database")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS personal_data (
                id SERIAL PRIMARY KEY,
                userid VARCHAR(50) NOT NULL UNIQUE,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone_number VARCHAR(20),
                ice_first_name VARCHAR(100),
                ice_last_name VARCHAR(100),
                ice_phone_number VARCHAR(20),
                FOREIGN KEY (userid) REFERENCES login_data(userid)
                    ON DELETE CASCADE
            )
        """)
        
        csv_path = Path('apps/backend/database/csv_files/personal-data.csv')
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO personal_data (
                    userid, first_name, last_name, email, phone_number,
                    ice_first_name, ice_last_name, ice_phone_number
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (userid) DO NOTHING
            """, (
                row['userid'], row['first_name'], row['last_name'],
                row['email'], row['phone_number'], row['ice_first_name'],
                row['ice_last_name'], row['ice_phone_number']
            ))
        
        conn.commit()
        print("Personal data table created and populated successfully")
        
    except Exception as error:
        print(f"Error while creating personal table: {error}")
        conn.rollback()
        raise
    finally:
        conn.close()