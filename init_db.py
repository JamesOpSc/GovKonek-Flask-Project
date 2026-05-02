import sqlite3

def create_database():
    # 1. Connect to SQLite (This creates the 'govkonek.db' file if it doesn't exist)
    connection = sqlite3.connect('govkonek.db')
    
    # 2. Create a cursor object to execute SQL commands
    cursor = connection.cursor()
    
    # 3. Execute the schema blueprint for the User system
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # 4. Commit the changes and close the connection
    connection.commit()
    connection.close()
    
    print("Database and 'users' table created successfully!")

if __name__ == '__main__':
    create_database()