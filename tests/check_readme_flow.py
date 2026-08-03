"""Integration test: verify the README flow works after refactoring."""
import sys, os, tempfile, sqlite3

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create temp file DB and initialize tables
tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = tmp.name
tmp.close()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()

tables_sql = [
    '''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT DEFAULT '',
        address TEXT DEFAULT '',
        phone_number TEXT DEFAULT '',
        profile_picture TEXT DEFAULT '',
        barangay TEXT DEFAULT '')''',
    '''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        publisher_id INTEGER NOT NULL,
        title TEXT NOT NULL, content TEXT NOT NULL,
        status TEXT DEFAULT 'published',
        category TEXT DEFAULT 'Announcement',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id))''',
    '''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id))''',
    '''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        emoji TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(post_id, user_id))''',
    '''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT NOT NULL,
        status TEXT DEFAULT 'ongoing', budget REAL DEFAULT 0,
        location TEXT DEFAULT '', image_url TEXT DEFAULT '',
        start_date TEXT DEFAULT '', end_date TEXT DEFAULT '',
        publisher_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id))''',
    '''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, description TEXT NOT NULL,
        icon TEXT DEFAULT '📋', category TEXT DEFAULT 'General',
        url TEXT DEFAULT '#', is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
    '''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT DEFAULT '',
        category TEXT DEFAULT 'General', file_url TEXT DEFAULT '#',
        file_size TEXT DEFAULT '', published_date TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
    '''CREATE TABLE IF NOT EXISTS voice_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL,
        content TEXT NOT NULL, category TEXT DEFAULT 'General',
        status TEXT DEFAULT 'open', vote_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id))''',
    '''CREATE TABLE IF NOT EXISTS voice_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voice_post_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        content TEXT NOT NULL, is_official INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id))''',
    '''CREATE TABLE IF NOT EXISTS voice_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voice_post_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(voice_post_id, user_id))''',
]

for sql in tables_sql:
    c.execute(sql)
conn.commit()
conn.close()
print(f"DB initialized at {db_path}")

# ---- Test the app ----
from config import Config
from app import create_app

app = create_app(Config(db_name=db_path, secret_key='test-key'))
client = app.test_client()

results = []

# 1. GET login page
r = client.get('/login')
results.append(('GET  /login', r.status_code == 200))

# 2. POST register
r = client.post('/register', data={
    'username': 'citizen1', 'password': 'pw123', 'role': 'citizen'
}, follow_redirects=True)
results.append(('POST /register', r.status_code == 200))

# 3. POST login
r = client.post('/login', data={
    'username': 'citizen1', 'password': 'pw123'
}, follow_redirects=True)
results.append(('POST /login', r.status_code == 200))

# 4. Dashboard
r = client.get('/dashboard')
results.append(('GET  /dashboard', r.status_code == 200))

# 5-9. Feature pages
for page in ['/profile', '/projects', '/services', '/documents', '/barangay-map', '/citizens-voice']:
    r = client.get(page)
    results.append((f'GET  {page}', r.status_code == 200))

# 10-14. API endpoints
for api in ['/api/posts', '/api/projects', '/api/services', '/api/documents', '/api/voice']:
    r = client.get(api)
    results.append((f'GET  {api}', r.status_code == 200))

# 15. Logout
r = client.get('/logout', follow_redirects=True)
results.append(('GET  /logout', r.status_code == 200))

# Cleanup
os.unlink(db_path)

# Report
passed = sum(1 for _, ok in results if ok)
total = len(results)
print(f"\n{'='*50}")
for name, ok in results:
    print(f"  {'✅' if ok else '❌'} {name}")
print(f"{'='*50}")
print(f"  {passed}/{total} passed")
if passed == total:
    print("  ALL TESTS PASSED! README flow works correctly.")
else:
    print("  SOME TESTS FAILED - see above.")
    sys.exit(1)
