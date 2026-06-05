"""
GovKonek Database Initialization Script

Run this script once to create all required SQLite tables and seed default data.
This is a standalone utility — it's NOT imported by the Flask app at runtime.

Usage:
    python init_db.py          # Creates/resets govkonek.db with all tables

Database Schema:
    - users:              Citizen and publisher accounts
    - posts:              Barangay announcements with category support
    - comments:           Nested comments on posts
    - reactions:          Emoji reactions (one per user per post)
    - projects:           Barangay infrastructure projects with lat/lng
    - services:           E-services catalog
    - documents:          Transparency documents (budget reports, ordinances, etc.)
    - voice_posts:        Citizens' Voice forum topics
    - voice_comments:     Comments on voice posts (publisher = official response)
    - voice_votes:        Up/down votes on voice posts
    - barangays:          Configurable barangay landing-page content

Migration Strategy:
    Uses IF NOT EXISTS for CREATE TABLE and try/except for ALTER TABLE,
    so this script is safe to run repeatedly — it adds missing columns
    without destroying existing data.
"""

import sqlite3


def create_database():
    """
    Create all database tables and seed default data.

    This function is idempotent — running it multiple times will not
    duplicate tables or seed rows.
    """
    # Open (or create) the SQLite database file
    connection = sqlite3.connect('govkonek.db')
    connection.row_factory = sqlite3.Row  # Allows accessing columns by name
    cursor = connection.cursor()

    # ===================================================================
    # CORE TABLES
    # ===================================================================

    # -- Users -----------------------------------------------------------
    # Stores both citizen and publisher (barangay captain) accounts.
    # The 'role' column is the discriminator: 'citizen' or 'publisher'.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # -- Posts -----------------------------------------------------------
    # Barangay announcements published by barangay captains.
    # category supports: Announcement, Emergency, Health, Project.
    # status can be: published, draft, archived.
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

    # ===================================================================
    # MIGRATIONS — Safe ALTER TABLE operations
    # ===================================================================
    # Each migration is wrapped in try/except so the script is safe to
    # run repeatedly. If a column already exists, sqlite3 raises
    # OperationalError which we silently ignore.

    # -- Migration: add category column to posts -------------------------
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN category TEXT DEFAULT 'Announcement'")
    except sqlite3.OperationalError:
        pass  # column already exists

    # -- Migration: user profile fields ----------------------------------
    # email, address, phone_number, profile_picture were added after
    # the initial users table was created.
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
    # Allows attaching an image to a post (stored as a file path).
    try:
        cursor.execute("ALTER TABLE posts ADD COLUMN image_path TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # -- Migration: nested comments (parent_id) --------------------------
    # Enables threaded replies: a comment can reference another comment
    # as its parent via parent_id.
    try:
        cursor.execute("ALTER TABLE comments ADD COLUMN parent_id INTEGER REFERENCES comments(id)")
    except sqlite3.OperationalError:
        pass

# ===================================================================
    # INTERACTION TABLES
    # ===================================================================

    # -- Comments --------------------------------------------------------
    # Stores user comments on announcement posts.
    # parent_id (added via migration) enables threaded/nested replies.
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
    # Each user can react to a post with exactly ONE emoji at a time.
    # The UNIQUE(post_id, user_id) constraint enforces one-reaction-per-user.
    # Toggling: same emoji = remove, different emoji = change, none = add.
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

    # ===================================================================
    # FEATURE TABLES
    # ===================================================================

    # -- Barangay Projects -----------------------------------------------
    # Tracks infrastructure and community projects with geolocation.
    # latitude/longitude (added via migrations) enable map markers.
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

    # -- Migration: add publisher_id for ownership tracking ----------------
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN publisher_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass  # column already exists

    # -- Migration: add lat/lng columns for map markers ------------------
    # Duplicated intentionally as a safety measure — sqlite3 silently
    # ignores ALTER TABLE for existing columns.
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass

    # -- E-Services -----------------------------------------------------
    # Catalog of available barangay e-services (request certificates,
    # file complaints, etc.). is_active toggles service visibility.
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
    # Stores budget reports, audit reports, ordinances, resolutions, etc.
    # file_url is the relative path to the uploaded file.
    # file_size is a human-readable string (e.g., "2.4 MB").
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

    # ===================================================================
    # CITIZENS' VOICE FORUM TABLES
    # ===================================================================

    # -- Citizens' Voice Posts -------------------------------------------
    # Community forum where any user can post topics, grievances,
    # suggestions, or questions. status: open / resolved / closed.
    # vote_count is a cached counter updated via triggers/application logic.
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
    # is_official flag marks responses from barangay captains.
    # These are highlighted differently in the UI.
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
    # Each user gets ONE vote per voice post (up or down).
    # The UNIQUE constraint prevents multiple votes.
    # vote_type CHECK enforces only 'up' or 'down' values.
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

# ===================================================================
    # BARANGAY LANDING PAGE TABLES
    # ===================================================================

    # -- Barangays (configurable landing page per barangay) ---------------
    # Each barangay captain can create their own landing page with
    # custom info: name, description, address, contact details,
    # office hours, motto, and map coordinates.
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

    # -- Seed: default barangay (Payatas, Quezon City) ------------------
    # Creates a placeholder barangay so the landing page is never empty.
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

    # ===================================================================
    # FINALIZE
    # ===================================================================
    # Commit all changes and close the connection.
    connection.commit()
    connection.close()
    print("Database and all tables created successfully!")


# ===================================================================
# ENTRY POINT
# ===================================================================
if __name__ == '__main__':
    # Run this script directly to create/reset the database:
    #   python init_db.py
    create_database()