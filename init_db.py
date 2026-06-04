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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (publisher_id) REFERENCES users(id)
        )
    ''')

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

    # ===================================================================
    # SEED DATA
    # ===================================================================

    publisher = cursor.execute(
        "SELECT id FROM users WHERE role = 'publisher' LIMIT 1"
    ).fetchone()
    publisher_id = publisher['id'] if publisher else 1

    # -- Seed posts ------------------------------------------------------
    cursor.execute('SELECT COUNT(*) FROM posts')
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            'INSERT INTO posts (publisher_id, title, content) VALUES (?, ?, ?)',
            [
                (publisher_id, 'Barangay Hall Solar Panel Installation',
                 'The transition to renewable energy for the main barangay hall is now 100% complete. '
                 'This initiative will reduce our electricity costs by approximately 40% annually.'),
                (publisher_id, 'Free Dental Mission Weekend',
                 'Free tooth extractions and checkups this Saturday at the Covered Court, 8AM to 12PM. '
                 'First-come, first-served basis.'),
                (publisher_id, 'New Barangay Ordinance: Waste Segregation',
                 'Starting next month, all households are required to segregate waste. '
                 'Fines imposed after a 30-day grace period.'),
            ]
        )

    # -- Seed projects ---------------------------------------------------
    cursor.execute('SELECT COUNT(*) FROM projects')
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            '''INSERT INTO projects (title, description, status, budget, location, image_url, start_date, end_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('Barangay Health Center Renovation',
                 'Full renovation and expansion of the barangay health center to accommodate more patients and provide better medical services including a new maternity wing and dental clinic.',
                 'ongoing', 2500000, 'Purok 3, Barangay Hall Compound',
                 'https://images.unsplash.com/photo-1587351021759-3e4e8e8e4e4e?w=600',
                 '2026-01-15', '2026-08-30'),
                ('Solar-Powered Street Lights Phase 2',
                 'Installation of 50 additional solar-powered LED street lights along main roads and alleyways to improve safety and reduce electricity costs.',
                 'ongoing', 1800000, 'All Major Roads, Barangay-wide',
                 'https://images.unsplash.com/photo-1613665813446-82a78c468a1d?w=600',
                 '2026-03-01', '2026-06-30'),
                ('Community Learning Hub & Digital Library',
                 'Construction of a two-story learning hub with free WiFi, computers, and a library to support students and lifelong learners in the community.',
                 'planned', 5000000, 'Beside Barangay Plaza',
                 'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=600',
                 '2026-07-01', '2027-01-31'),
                ('Drainage System Improvement - Zone 2',
                 'Rehabilitation and expansion of drainage canals in flood-prone areas of Zone 2 to prevent flooding during heavy rains and typhoons.',
                 'completed', 3200000, 'Zone 2, Riverside Area',
                 'https://images.unsplash.com/photo-1624969862644-791f3dc98927?w=600',
                 '2025-09-01', '2026-02-28'),
                ('Barangay Multi-Purpose Covered Court',
                 'Construction of a multi-purpose covered court for sports events, assemblies, disaster evacuation, and community gatherings.',
                 'completed', 4500000, 'Barangay Sports Complex',
                 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=600',
                 '2025-06-01', '2025-12-15'),
            ]
        )

    # -- Seed services ---------------------------------------------------
    cursor.execute('SELECT COUNT(*) FROM services')
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            '''INSERT INTO services (name, description, icon, category, url, is_active)
               VALUES (?, ?, ?, ?, ?, ?)''',
            [
                ('Barangay Clearance', 'Apply for and obtain your barangay clearance online. Required for employment, business permits, and other transactions.', '📋', 'Certificates', '/services/clearance', 1),
                ('Barangay ID Application', 'Register for your official Barangay ID. Valid government-issued identification for residents.', '🪪', 'IDs & Registration', '/services/barangay-id', 1),
                ('Business Permit Assistance', 'Get help with processing your business permit requirements at the barangay level.', '🏪', 'Business', '/services/business-permit', 1),
                ('Certificate of Indigency', 'Request a Certificate of Indigency for medical assistance, scholarship applications, and other needs.', '📜', 'Certificates', '/services/indigency', 1),
                ('Blotter / Incident Report', 'File an official blotter report for incidents, disputes, or complaints within the barangay.', '🚨', 'Public Safety', '/services/blotter', 1),
                ('Health Center Appointment', 'Book an appointment at the Barangay Health Center for checkups, vaccinations, and consultations.', '🏥', 'Health', '/services/health-appointment', 1),
                ('Grievance Filing', 'Submit a formal grievance or complaint to the Barangay Council for mediation and resolution.', '📝', 'Public Safety', '/services/grievance', 1),
                ('Senior Citizen Benefits', 'Apply for senior citizen benefits, discounts, and social pension programs.', '👴', 'Social Services', '/services/senior-citizen', 1),
            ]
        )

    # -- Seed documents --------------------------------------------------
    cursor.execute('SELECT COUNT(*) FROM documents')
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            '''INSERT INTO documents (title, description, category, file_url, file_size, published_date)
               VALUES (?, ?, ?, ?, ?, ?)''',
            [
                ('Barangay Annual Budget 2026',
                 'Comprehensive breakdown of the annual budget allocation for fiscal year 2026 including all programs, projects, and operational expenses.',
                 'Budget Report', '#', '2.4 MB', '2026-01-10'),
                ('Quarter 1 Financial Statement 2026',
                 'Detailed financial report for the first quarter of 2026 showing actual expenditures versus approved budget.',
                 'Budget Report', '#', '1.8 MB', '2026-04-05'),
                ('COA Audit Report 2025',
                 'Commission on Audit (COA) annual audit report for the barangay covering all financial transactions for fiscal year 2025.',
                 'Audit Report', '#', '3.1 MB', '2026-02-15'),
                ('Barangay Ordinance No. 12 Series 2025',
                 'An ordinance mandating mandatory waste segregation at source for all households and establishments within the barangay.',
                 'Ordinance', '#', '520 KB', '2025-11-20'),
                ('Barangay Resolution No. 05 Series 2026',
                 'A resolution adopting the Barangay Development Plan for 2026-2028 outlining strategic priorities and key initiatives.',
                 'Resolution', '#', '780 KB', '2026-01-05'),
                ('Barangay Ordinance No. 03 Series 2026',
                 'An ordinance establishing curfew hours for minors and regulating noise levels during evening hours.',
                 'Ordinance', '#', '445 KB', '2026-03-12'),
                ('Procurement Report - Q4 2025',
                 'Summary of all procurement activities and awarded contracts for the fourth quarter of 2025.',
                 'Procurement', '#', '1.2 MB', '2026-01-08'),
                ('Barangay Disaster Risk Reduction Plan 2026',
                 'Comprehensive disaster preparedness and response plan including evacuation routes, emergency contacts, and resource inventory.',
                 'Disaster Preparedness', '#', '4.5 MB', '2026-01-15'),
            ]
        )

    # -- Seed citizens' voice posts --------------------------------------
    cursor.execute('SELECT COUNT(*) FROM voice_posts')
    if cursor.fetchone()[0] == 0:
        citizen = cursor.execute(
            "SELECT id FROM users WHERE role = 'citizen' LIMIT 1"
        ).fetchone()
        citizen_id = citizen['id'] if citizen else 2

        cursor.executemany(
            '''INSERT INTO voice_posts (user_id, title, content, category, status, vote_count)
               VALUES (?, ?, ?, ?, ?, ?)''',
            [
                (citizen_id, 'Illegal Dumping at Purok 4 Creek',
                 'May mga nagtatapon ng basura sa creek malapit sa Purok 4. Nagdudulot ito ng masamang amoy at posibleng pagbaha. Pakiusap sana ay maaksyunan ito agad.',
                 'Grievance', 'open', 12),
                (citizen_id, 'Suggestion: Weekend Market sa Plaza',
                 'Magandang ideya siguro kung magkakaroon tayo ng weekend market sa barangay plaza para sa mga local vendors at farmers. Makakatulong ito sa ekonomiya ng barangay.',
                 'Suggestion', 'open', 8),
                (citizen_id, 'Tanong: Schedule ng Libreng Bakuna',
                 'Kailan po ang susunod na libreng bakuna para sa mga bata at senior citizens? May bagong schedule na po ba?',
                 'Question', 'open', 5),
                (citizen_id, 'Pasasalamat sa Bagong Street Lights',
                 'Gusto ko lang magpasalamat sa barangay captain at council para sa bagong street lights sa Zone 5. Malaking tulong ito sa seguridad namin sa gabi. Maraming salamat po!',
                 'General', 'open', 15),
                (publisher_id, 'Barangay Assembly This Saturday',
                 'Inaanyayahan ang lahat ng residents na dumalo sa ating quarterly Barangay Assembly ngayong Sabado, 9AM sa Covered Court. Pag-uusapan ang mga ongoing projects at concerns ng komunidad.',
                 'Announcement', 'open', 20),
                (citizen_id, 'Tricycle Terminal sa Kanto ng Purok 2',
                 'Ang daming nakaparadang tricycle sa kanto ng Purok 2 na nakakaabala sa daloy ng trapiko. Sana magkaroon ng designated terminal para maiwasan ang congestion.',
                 'Grievance', 'open', 7),
            ]
        )

        # -- Seed voice comments -----------------------------------------
        cursor.executemany(
            '''INSERT INTO voice_comments (voice_post_id, user_id, content, is_official)
               VALUES (?, ?, ?, ?)''',
            [
                (1, publisher_id, 'Napag-usapan na namin ito sa konseho. Magkakaroon ng cleanup drive sa Sabado at maglalagay tayo ng warning signs. Salamat sa pag-report.', 1),
                (2, publisher_id, 'Magandang suggestion! Pag-aaralan namin ito sa susunod na council meeting. Kailangan lang natin ng permits mula sa city hall.', 1),
                (1, citizen_id, 'Salamat po sa mabilis na aksyon, Kap! Sana matuloy ang cleanup drive.', 0),
                (4, publisher_id, 'Maraming salamat sa inyong appreciation. Tuloy-tuloy lang ang serbisyo para sa barangay!', 1),
            ]
        )

    connection.commit()
    connection.close()
    print("Database and all tables created successfully!")

if __name__ == '__main__':
    create_database()