import sqlite3

def seed():
    conn = sqlite3.connect('govkonek.db')
    cursor = conn.cursor()
    
    # 📄 Ensure your schema matches this table definition
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barangays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            population INTEGER
        )
    ''')
    
    # 🎯 Insert the core multi-tenant test cases
    sample_barangays = [
        ('Payatas', 'A vibrant community focusing on sustainable livelihood programs, urban agriculture, and upgraded local infrastructure.', 130000),
        ('Bagong Silangan', 'A residential haven in Quezon City dedicated to community resilience, climate action, and family-centric public services.', 85000),
        ('Batasan Hills', 'The administrative heart of local governance, housing major government hubs, expansive road networks, and active citizen councils.', 160000)
    ]
    
    for name, desc, pop in sample_barangays:
        cursor.execute('''
            INSERT OR IGNORE INTO barangays (name, description, population)
            VALUES (?, ?, ?)
        ''', (name, desc, pop))
        
    conn.commit()
    conn.close()
    print("✅ Database successfully seeded with local multi-tenant hubs!")

if __name__ == '__main__':
    seed()