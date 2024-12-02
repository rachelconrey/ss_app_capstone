from create_roles_data import create_roles_table
from create_login_data import create_login_table
from create_personal_data import create_personal_table
from create_training_course_data import create_training_course_table
from create_training_status_data import create_training_status_table

def main():
    try:
        create_roles_table()
        create_login_table()
        create_personal_table()
        create_training_course_table()
        create_training_status_table()
        print("All tables created and populated successfully")
    except Exception as error:
        print(f"Error during database initialization: {error}")

if __name__ == "__main__":
    main()