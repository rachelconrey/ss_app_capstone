import pandas as pd
from pathlib import Path
from db_config import get_db_connection

def create_login_table():
    conn = get_db_connection("ss_database")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_data (
                id SERIAL PRIMARY KEY,
                userid VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(100) NOT NULL,
                role VARCHAR(50) NOT NULL,
                date_created DATE NOT NULL,
                FOREIGN KEY (role) REFERENCES roles_data(role)
                    ON DELETE CASCADE
            )
        """)
        
        csv_path = Path('apps/backend/database/csv_files/login-data.csv')
        df = pd.read_csv(csv_path)
        df['date_created'] = pd.to_datetime(df['date_created'])
        
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO login_data (userid, password, role, date_created)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (userid) DO NOTHING
            """, (row['userid'], row['password'], row['role'], row['date_created']))
        
        conn.commit()
        print("Login data table created and populated successfully")
        
    except Exception as error:
        print(f"Error while creating login table: {error}")
        conn.rollback()
        raise
    finally:
        conn.close()