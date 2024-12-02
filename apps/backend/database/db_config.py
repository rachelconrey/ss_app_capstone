import psycopg

def get_db_connection(dbname: str = "postgres"):
    """Create and return a database connection"""
    try:
        connection = psycopg.connect(
            host="localhost",
            dbname="ss_database",
            user="postgres",
            password="WACcat2023!",
            autocommit=True
        )
        return connection
    except Exception as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        raise