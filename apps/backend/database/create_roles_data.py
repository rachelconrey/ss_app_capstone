import pandas as pd
from pathlib import Path
from db_config import get_db_connection

def create_roles_table():
    conn = get_db_connection("ss_database")
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roles_data (
                id SERIAL PRIMARY KEY,
                role VARCHAR(50) NOT NULL UNIQUE,
                role_description VARCHAR(255)
            )
        """)

        csv_path = Path('apps/backend/database/csv_files/roles-data.csv')
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO roles_data (role, role_description)
                VALUES (%s, %s)
                ON CONFLICT (role) DO NOTHING
            """, (row['role'], row['role_description']))
        
        conn.commit()
        print("Roles data table created and populated successfully")
        
    except Exception as error:
        print(f"Error while creating roles table: {error}")
        conn.rollback()
        raise
    finally:
        conn.close()