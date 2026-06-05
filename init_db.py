import sqlite3

def create_database():
    connection = sqlite3.connect('govkonek.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # -- Users -----------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # -- Posts -----------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            publisher_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'published',
            category TEXT DEFAULT 'Announcement',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (publisher_id) REFERENCES users(id)
        )
    ''')

    # -- Migration: add category column if it doesn't exist -------------
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN category TEXT DEFAULT 'Announcement'")
    except sqlite3.OperationalError:
        pass  # column already exists

    # -- Migration: user profile fields ----------------------------------
    for col, col_def in [
        ('email', "TEXT DEFAULT ''"),
        ('address', "TEXT DEFAULT ''"),
        ('phone_number', "TEXT DEFAULT ''"),
        ('profile_picture', "TEXT DEFAULT ''"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass

    # -- Migration: post media support -----------------------------------
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN image_path TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # -- Migration: nested comments (parent_id) --------------------------
    try:
        cursor.execute("ALTER TABLE comments ADD COLUMN parent_id INTEGER REFERENCES comments(id)")
    except sqlite3.OperationalError:
        pass

    # -- Comments --------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # -- Reactions -------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(post_id, user_id)
        )
    ''')

    # -- Barangay Projects -----------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'ongoing',
            budget REAL DEFAULT 0,
            location TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            start_date TEXT DEFAULT '',
            end_date TEXT DEFAULT '',
            publisher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (publisher_id) REFERENCES users(id)
        )
    ''')

    # -- Migration: add publisher_id column if it doesn't exist ----------
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN publisher_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass  # column already exists

    # -- Migration: add lat/lng columns for map markers -----------------
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass

    # -- Migration: add lat/lng columns for map integration -------------
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass

    # -- E-Services -----------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '📋',
            category TEXT DEFAULT 'General',
            url TEXT DEFAULT '#',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # -- Transparency Documents ------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'General',
            file_url TEXT DEFAULT '#',
            file_size TEXT DEFAULT '',
            published_date TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # -- Citizens' Voice Posts -------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            status TEXT DEFAULT 'open',
            vote_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # -- Citizens' Voice Comments ----------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voice_post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_official INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # -- Citizens' Voice Votes -------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voice_post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(voice_post_id, user_id)
        )
    ''')

    # -- Barangays (configurable landing page per barangay) ---------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barangays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT 'Barangay Hall',
            description TEXT DEFAULT '',
            address TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            facebook TEXT DEFAULT '',
            office_hours_weekday TEXT DEFAULT '8:00 AM – 5:00 PM',
            office_hours_saturday TEXT DEFAULT '8:00 AM – 12:00 PM',
            motto TEXT DEFAULT '',
            hero_image TEXT DEFAULT '',
            latitude REAL DEFAULT 14.71309,
            longitude REAL DEFAULT 121.10063,
            publisher_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (publisher_id) REFERENCES users(id)
        )
    ''')

    # Seed a default barangay if none exists
    cursor.execute('SELECT COUNT(*) FROM barangays')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO barangays (name, description, address, phone, email, facebook,
                                   office_hours_weekday, office_hours_saturday, motto, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Barangay Hall',
            'The heart of local governance in our community. We are committed to transparent, efficient, and people-centered public service.',
            'Barangay Hall, Payatas, Quezon City, Metro Manila',
            '(02) 8XXX-XXXX',
            'barangayhall@govkonek.ph',
            'facebook.com/BarangayPayatasOfficial',
            '8:00 AM – 5:00 PM',
            '8:00 AM – 12:00 PM',
            'Serbisyong Tapat, Para sa Lahat!',
            14.71309,
            121.10063
        ))

    # -- Barangay Officials ------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS officials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barangay_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            rank_order INTEGER DEFAULT 0,
            image TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (barangay_id) REFERENCES barangays(id) ON DELETE CASCADE
        )
    ''')

    # Seed default officials for the first barangay if none exist
    cursor.execute('SELECT COUNT(*) FROM officials')
    if cursor.fetchone()[0] == 0:
        default_officials = [
            ('Juan Dela Cruz', 'Punong Barangay (Barangay Captain)', 1),
            ('Maria Santos', 'Barangay Kagawad (Councilor)', 2),
            ('Jose Rizal', 'Barangay Kagawad (Councilor)', 3),
            ('Ana Reyes', 'Barangay Kagawad (Councilor)', 4),
            ('Pedro Gonzales', 'Barangay Kagawad (Councilor)', 5),
            ('Sofia Mendoza', 'Barangay Kagawad (Councilor)', 6),
            ('Luis Torres', 'Barangay Kagawad (Councilor)', 7),
            ('Elena Cruz', 'Barangay Kagawad (Councilor)', 8),
            ('Carlos Bautista', 'SK Chairperson', 9),
            ('Teresa Villanueva', 'Barangay Secretary', 10),
            ('Ramon Flores', 'Barangay Treasurer', 11),
        ]
        for name, position, rank in default_officials:
            cursor.execute(
                'INSERT INTO officials (barangay_id, name, position, rank_order) VALUES (1, ?, ?, ?)',
                (name, position, rank)
            )

    connection.commit()
    connection.close()
    print("Database and all tables created successfully!")

if __name__ == '__main__':
    create_database()