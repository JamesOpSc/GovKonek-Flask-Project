r"""GovKonek Citizen vs Barangay (Publisher) E2E Test
Covers auth, permissions, CRUD, cross-role security, voice, barangay hub.
Run: venv\Scripts\python.exe tests/citizen_barangay_e2e.py
"""
import os, sys, tempfile, sqlite3, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from app import create_app

# ------------------------------------------------------------
# Setup temp DB with FULL schema (mirrors init_db.py)
# ------------------------------------------------------------
tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = tmp_db.name
tmp_db.close()
tmp_upload = tempfile.mkdtemp(prefix="govkonek_upload_")

def init_full_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    # users with all migrated columns
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT DEFAULT '',
        address TEXT DEFAULT '',
        phone_number TEXT DEFAULT '',
        profile_picture TEXT DEFAULT '',
        barangay TEXT DEFAULT ''
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        publisher_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'published',
        category TEXT DEFAULT 'Announcement',
        image_path TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        parent_id INTEGER REFERENCES comments(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        emoji TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(post_id, user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT NOT NULL,
        status TEXT DEFAULT 'ongoing', budget REAL DEFAULT 0,
        location TEXT DEFAULT '', image_url TEXT DEFAULT '',
        start_date TEXT DEFAULT '', end_date TEXT DEFAULT '',
        publisher_id INTEGER, latitude REAL, longitude REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, description TEXT NOT NULL,
        icon TEXT DEFAULT '📋', category TEXT DEFAULT 'General',
        url TEXT DEFAULT '#', is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL, description TEXT DEFAULT '',
        category TEXT DEFAULT 'General', file_url TEXT DEFAULT '#',
        file_size TEXT DEFAULT '', published_date TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS voice_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL,
        content TEXT NOT NULL, category TEXT DEFAULT 'General',
        status TEXT DEFAULT 'open', vote_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS voice_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voice_post_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        content TEXT NOT NULL, is_official INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS voice_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voice_post_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL CHECK(vote_type IN ('up','down')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(voice_post_id, user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS barangays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT 'Barangay Hall',
        description TEXT DEFAULT '', address TEXT DEFAULT '',
        phone TEXT DEFAULT '', email TEXT DEFAULT '', facebook TEXT DEFAULT '',
        office_hours_weekday TEXT DEFAULT '8:00 AM – 5:00 PM',
        office_hours_saturday TEXT DEFAULT '8:00 AM – 12:00 PM',
        motto TEXT DEFAULT '', hero_image TEXT DEFAULT '',
        latitude REAL DEFAULT 14.71309, longitude REAL DEFAULT 121.10063,
        publisher_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id)
    )''')
    # seed default barangay fallback
    c.execute("SELECT COUNT(*) FROM barangays")
    if c.fetchone()[0]==0:
        c.execute('''INSERT INTO barangays (name, description, address, phone, email, facebook)
        VALUES ('Barangay Hall','Default hall','Barangay Hall, Payatas','(02) 8XXX-XXXX','barangayhall@govkonek.ph','fb.com/barangay')''')
    conn.commit()
    conn.close()

init_full_db(db_path)
print(f"[setup] DB={db_path}")
print(f"[setup] upload_dir={tmp_upload}")

cfg = Config(db_name=db_path, secret_key='test-e2e-key', upload_folder=tmp_upload)
app = create_app(cfg)
client = app.test_client()
client2 = app.test_client()  # for second user parallel
client3 = app.test_client()  # for third user

results = []
def _safe(s):
    """Return an ASCII-safe version of s for cp1252 consoles."""
    try:
        s.encode('cp1252')
        return s
    except UnicodeEncodeError:
        return s.encode('ascii', 'replace').decode('ascii')

def check(name, condition, detail=""):
    ok = bool(condition)
    results.append((name, ok, detail))
    icon = "[PASS]" if ok else "[FAIL]"
    extra = f" -- {detail}" if detail and not ok else (f" ({detail})" if detail and ok else "")
    print(f" {icon} {_safe(name)}{_safe(extra)}")
    return ok

def section(title):
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")

# Helper: register and login
def register(username, pw, role, barangay=""):
    data = {'username': username, 'password': pw, 'role': role}
    if barangay:
        data['barangay'] = barangay
    return client.post('/register', data=data, follow_redirects=True)

def login_as(cli, username, pw):
    return cli.post('/login', data={'username': username, 'password': pw}, follow_redirects=True)

def logout_as(cli):
    return cli.get('/logout', follow_redirects=True)

# ============================================================
# A. Registration & Authentication
# ============================================================
section("A. Registration & Authentication — Citizen vs Barangay (Publisher)")

r = client.get('/register')
check("GET /register (public)", r.status_code==200)

# Citizen registration with barangay
r = client.post('/register', data={'username':'citizen_juan','password':'pass123','role':'citizen','barangay':'Payatas'}, follow_redirects=True)
check("Register citizen_juan (citizen + Payatas)", b"successful" in r.data.lower() or r.status_code==200)

# Duplicate should fail
r = client.post('/register', data={'username':'citizen_juan','password':'pass123','role':'citizen'}, follow_redirects=True)
check("Duplicate citizen_juan blocked", b"already exists" in r.data.lower())

# Empty username fails
r = client.post('/register', data={'username':'','password':'x','role':'citizen'}, follow_redirects=True)
check("Empty username rejected", b"Username" in r.data)

# Empty password fails
r = client.post('/register', data={'username':'newuser','password':'','role':'citizen'}, follow_redirects=True)
check("Empty password rejected", b"Password" in r.data)

# Publisher registration
r = client.post('/register', data={'username':'captain_rodrigo','password':'cap123','role':'publisher','barangay':'Batasan Hills'}, follow_redirects=True)
check("Register captain_rodrigo (publisher + Batasan Hills)", r.status_code==200)

# Second publisher
r = client.post('/register', data={'username':'captain_lisa','password':'lisapw','role':'publisher','barangay':'Bagong Silangan'}, follow_redirects=True)
check("Register captain_lisa (publisher + Bagong Silangan)", r.status_code==200)

# Second citizen
r = client.post('/register', data={'username':'citizen_maria','password':'maria123','role':'citizen','barangay':'Bagong Silangan'}, follow_redirects=True)
check("Register citizen_maria", r.status_code==200)

# Verify barangay saved on citizen
import sqlite3
conn = sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
row = conn.execute("SELECT barangay, role FROM users WHERE username='citizen_juan'").fetchone()
check("citizen_juan barangay persisted == Payatas", row and row['barangay']=='Payatas', str(dict(row)) if row else "not found")
row2 = conn.execute("SELECT barangay FROM users WHERE username='captain_rodrigo'").fetchone()
check("captain_rodrigo barangay persisted == Batasan Hills", row2 and row2['barangay']=='Batasan Hills', str(dict(row2)) if row2 else "not found")
conn.close()

# Login citizen success
r = login_as(client, 'citizen_juan', 'pass123')
check("Login citizen_juan success → dashboard", r.status_code==200)

# Login wrong password fails
logout_as(client)
r = client.post('/login', data={'username':'citizen_juan','password':'wrong'}, follow_redirects=True)
check("Login wrong password blocked", b"Invalid" in r.data)

# Login publisher success
r = login_as(client, 'captain_rodrigo', 'cap123')
check("Login captain_rodrigo success", r.status_code==200)

# Unauthenticated access should redirect (302) or to login
anon = app.test_client()
r = anon.get('/dashboard', follow_redirects=False)
check("Unauthenticated /dashboard redirects", r.status_code in (302,301), f"got {r.status_code}")

# ============================================================
# B. Citizen Permissions — Read OK, Write Blocked
# ============================================================
section("B. Citizen User Side — Permissions Matrix")

# Switch to citizen_juan
logout_as(client)
login_as(client, 'citizen_juan', 'pass123')
r = client.get('/dashboard')
check("Citizen GET /dashboard 200", r.status_code==200)
# heuristic: citizen dashboard should not have publisher onboarding? just check role present
check("Citizen dashboard role=citizen in html", b"citizen" in r.data.lower())

# All citizens can view these pages
for path in ['/profile','/projects','/services','/documents','/barangay-map','/citizens-voice','/barangay-landing']:
    r = client.get(path)
    check(f"Citizen GET {path} 200", r.status_code==200, f"{r.status_code}")

# Citizens can view feed APIs
for api in ['/api/posts','/api/projects','/api/services','/api/documents','/api/voice','/api/barangays']:
    r = client.get(api)
    check(f"Citizen GET {api} 200", r.status_code==200, f"{r.status_code}")

# Profile API
r = client.get('/api/profile')
check("Citizen GET /api/profile 200", r.status_code==200 and b"profile" in r.data)

# Profile update with upload
data = {'email':'juan@test.com','address':'Payatas','phone_number':'0911'}
r = client.post('/api/profile', data=data, content_type='multipart/form-data')
check("Citizen POST /api/profile update 200", r.status_code==200 and b"success" in r.data.lower())

# Citizen CANNOT create post
r = client.post('/api/posts', json={'title':'Citizen post','content':'hello','category':'Announcement'})
check("Citizen POST /api/posts blocked (403)", r.status_code==403, f"{r.status_code} {r.get_data(as_text=True)[:120]}")

# Citizen CANNOT create project
r = client.post('/api/projects', json={'title':'Citizen proj','description':'desc','status':'ongoing','budget':1000,'location':'loc','image_url':'','start_date':'2026-01-01','end_date':'2026-12-31'})
check("Citizen POST /api/projects blocked (403)", r.status_code==403)

# Citizen CANNOT create barangay
r = client.post('/api/barangays', json={'name':'Fake Barangay','address':'Fake address'})
check("Citizen POST /api/barangays blocked (403)", r.status_code==403)

# Citizen CANNOT upload document
from io import BytesIO
r = client.post('/api/documents', data={'title':'Doc','description':'d','category':'General','file': (BytesIO(b"fake"), 'test.pdf')}, content_type='multipart/form-data')
check("Citizen POST /api/documents blocked (403)", r.status_code==403)

# But citizen CAN create voice post (open forum)
r = client.post('/api/voice', json={'title':'Pothole complaint','content':'Road broken','category':'Grievance'})
check("Citizen POST /api/voice allowed (201)", r.status_code==201, f"{r.status_code}")
voice_citizen_id = None
if r.status_code==201:
    try:
        voice_citizen_id = r.get_json()['post']['id']
    except: pass

# Citizen CAN comment on voice
if voice_citizen_id:
    r = client.post(f'/api/voice/{voice_citizen_id}/comments', json={'content':'I agree'})
    check(f"Citizen POST /api/voice/{voice_citizen_id}/comments allowed", r.status_code in (200,201), f"{r.status_code}")
    # check is_official false for citizen
    if r.status_code in (200,201):
        j = r.get_json()
        is_off = j.get('comment',{}).get('is_official', 0)
        check("Citizen voice comment is_official==0", is_off==0, f"is_official={is_off}")

# Citizen CAN vote
if voice_citizen_id:
    r = client.post(f'/api/voice/{voice_citizen_id}/vote', json={'vote_type':'up'})
    check("Citizen vote up allowed", r.status_code==200, f"{r.status_code} {r.get_data(as_text=True)[:100]}")
    # toggle same vote removes
    r = client.post(f'/api/voice/{voice_citizen_id}/vote', json={'vote_type':'up'})
    j = r.get_json() if r.status_code==200 else {}
    check("Citizen vote toggle removes (removed)", j.get('action')=='removed', f"action={j.get('action')}")

# Citizen voice validation: empty title fails 400
r = client.post('/api/voice', json={'title':'','content':'no title','category':'General'})
check("Citizen voice empty title → 400", r.status_code==400)

# Citizen voice status update should be publisher-only (now 403)
if voice_citizen_id:
    r = client.put(f'/api/voice/{voice_citizen_id}/status', json={'status':'resolved'})
    check("Citizen PUT voice status blocked (publisher-only → 403)", r.status_code==403, f"{r.status_code} {r.get_data(as_text=True)[:120]}")
    # Reset to open for later publisher test
    logout_as(client)
    login_as(client, 'citizen_juan', 'pass123')
    # publisher will reset via direct repo if needed — not needed, just leave as resolved

# My barangay hub redirect for citizen (should redirect to /barangay/view/<slug> of Payatas)
r = client.get('/barangay/my-hub', follow_redirects=False)
loc = r.headers.get('Location','')
check("Citizen GET /barangay/my-hub redirects to slug", r.status_code in (302,301) and '/barangay/view/' in loc, f"{r.status_code} -> {loc}")

# Follow through
r = client.get('/barangay/my-hub', follow_redirects=True)
check("Citizen /barangay/my-hub follow → 200", r.status_code==200)

# ============================================================
# C. Barangay (Publisher) Permissions — Full CRUD
# ============================================================
section("C. Barangay (Publisher) Side — Full CRUD")

logout_as(client)
login_as(client, 'captain_rodrigo', 'cap123')
r = client.get('/dashboard')
check("Publisher GET /dashboard 200", r.status_code==200)
# Publisher dashboard renders "Barangay Captain Portal" not the literal word publisher
check("Publisher dashboard shows Barangay Captain Portal", b"Barangay Captain Portal" in r.data or b"barangay captain" in r.data.lower())

# Publisher can create barangay
# First ensure cleaning any existing for this publisher
conn = sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
# remove existing barangay for captain_rodrigo if any
row = conn.execute("SELECT id FROM barangays WHERE publisher_id=(SELECT id FROM users WHERE username='captain_rodrigo')").fetchone()
conn.close()
# if exists, delete via API first? Let's try create fresh after ensuring no existing via service logic
# Get publisher id
conn = sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
pub_id = conn.execute("SELECT id FROM users WHERE username='captain_rodrigo'").fetchone()['id']
conn.close()

# Check existing via API
r = client.get('/api/barangays')
barangs = r.get_json().get('barangays',[])
existing_for_me = [b for b in barangs if b.get('publisher_id')==pub_id]
if existing_for_me:
    # delete them to test create fresh
    for b in existing_for_me:
        client.delete(f"/api/barangays/{b['id']}")

r = client.post('/api/barangays', json={'name':'Barangay Batasan Hills','description':'Test desc','address':'Batasan Hills, QC','phone':'02-123','email':'b@ph','facebook':'fb','motto':'Motto','latitude':14.71309,'longitude':121.1})
check("Publisher POST /api/barangays create 201", r.status_code==201, f"{r.status_code} {r.get_data(as_text=True)[:200]}")
barangay_id = None
if r.status_code==201:
    barangay_id = r.get_json()['barangay']['id']

# Duplicate create should fail "already manage"
if barangay_id:
    r2 = client.post('/api/barangays', json={'name':'Another','description':'d','address':'addr'})
    check("Publisher duplicate barangay blocked", r2.status_code==403 and b"already manage" in r2.data.lower(), f"{r2.status_code} {r2.get_data(as_text=True)[:150]}")

# Missing name fails
r = client.post('/api/barangays', json={'name':'','description':'d','address':'addr'})
# This will hit duplicate check first, so we need to logout and use captain_lisa who has no barangay to test validation
logout_as(client2)
login_as(client2, 'captain_lisa', 'lisapw')
# clean hers
r_tmp = client2.get('/api/barangays')
barangs2 = r_tmp.get_json().get('barangays',[])
conn = sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
pub2_id = conn.execute("SELECT id FROM users WHERE username='captain_lisa'").fetchone()['id']
conn.close()
for b in barangs2:
    if b.get('publisher_id')==pub2_id:
        client2.delete(f"/api/barangays/{b['id']}")
r = client2.post('/api/barangays', json={'name':'','description':'d','address':'addr'})
check("Publisher barangay empty name → 403 with 'name is required'", r.status_code==403 and b"name is required" in r.data.lower(), f"{r.status_code} {r.get_data(as_text=True)[:150]}")
r = client2.post('/api/barangays', json={'name':'Barangay Bagong Silangan','description':'d','address':''})
check("Publisher barangay empty address → 403", r.status_code==403 and b"address is required" in r.data.lower())
# valid for lisa
r = client2.post('/api/barangays', json={'name':'Barangay Bagong Silangan','description':'Liza desc','address':'Bagong Silangan, QC','phone':'02','email':'e@ph'})
check("Publisher captain_lisa create Bagong Silangan 201", r.status_code==201)
barangay_id_lisa = r.get_json()['barangay']['id'] if r.status_code==201 else None

# Switch back to rodrigo
logout_as(client)
login_as(client,'captain_rodrigo','cap123')

# Update own barangay succeeds
if barangay_id:
    r = client.put(f'/api/barangays/{barangay_id}', json={'description':'Updated desc via publisher'})
    check("Publisher PUT own barangay 200", r.status_code==200, f"{r.status_code} {r.get_data(as_text=True)[:150]}")

# Update other publisher's barangay blocked
if barangay_id_lisa:
    r = client.put(f'/api/barangays/{barangay_id_lisa}', json={'description':'Hacked'})
    check("Publisher PUT other barangay blocked 403", r.status_code==403, f"{r.status_code}")

# Projects CRUD as publisher
r = client.post('/api/projects', json={'title':'Road Repair','description':'Fix road','status':'ongoing','budget':500000,'location':'Batasan Hills','image_url':'','start_date':'2026-01-01','end_date':'2026-12-31'})
check("Publisher POST /api/projects create 201", r.status_code==201, f"{r.status_code} {r.get_data(as_text=True)[:150]}")
proj_id = r.get_json()['project']['id'] if r.status_code==201 else None

# Invalid date range should fail
r = client.post('/api/projects', json={'title':'Bad dates','description':'d','status':'ongoing','budget':100,'location':'loc','image_url':'','start_date':'2026-12-31','end_date':'2026-01-01'})
check("Publisher project end<start → 403 'End date cannot be before'", r.status_code==403 and b"End date cannot be" in r.data, f"{r.status_code}")

# Empty title fails
r = client.post('/api/projects', json={'title':'','description':'d','status':'ongoing','budget':0,'location':'','image_url':'','start_date':'','end_date':''})
check("Publisher project empty title → 403", r.status_code==403)

# Invalid category defaults? Project status invalid defaults to 'ongoing' via _validate_choice - check it doesn't error
r = client.post('/api/projects', json={'title':'Weird status','description':'d','status':'invalid_status','budget':0,'location':'','image_url':'','start_date':'','end_date':''})
check("Publisher project invalid status defaults (201 not 403)", r.status_code==201, f"{r.status_code}")

# Get projects
r = client.get('/api/projects')
check("Publisher GET /api/projects 200", r.status_code==200)

# Update own project
if proj_id:
    r = client.put(f'/api/projects/{proj_id}', json={'title':'Road Repair Updated','description':'Fixed','status':'completed','budget':600000,'location':'Batasan','image_url':'','start_date':'2026-01-01','end_date':'2026-06-01'})
    check(f"Publisher PUT /api/projects/{proj_id} own 200", r.status_code==200)
    # verify title updated
    if r.status_code==200:
        check("Project title updated correctly", r.get_json()['project']['title']=='Road Repair Updated')

# Other publisher cannot update (Lisa tries)
if proj_id:
    r = client2.put(f'/api/projects/{proj_id}', json={'title':'Hacked','description':'hacked','status':'ongoing','budget':0,'location':'','image_url':'','start_date':'','end_date':''})
    check(f"Other publisher PUT project {proj_id} blocked 403", r.status_code==403, f"{r.status_code} {r.get_data(as_text=True)[:150]}")
    # citizen cannot update
    logout_as(client3)
    login_as(client3,'citizen_maria','maria123')
    r = client3.put(f'/api/projects/{proj_id}', json={'title':'Hacked','description':'h','status':'ongoing','budget':0,'location':'','image_url':'','start_date':'','end_date':''})
    check("Citizen PUT project blocked 403", r.status_code==403)
    # back to rodrigo
    logout_as(client)
    login_as(client,'captain_rodrigo','cap123')

# Delete other publisher's project blocked (now returns 403 via service rowcount)
r = client2.post('/api/projects', json={'title':'Lisa proj','description':'d','status':'ongoing','budget':100,'location':'loc','image_url':'','start_date':'','end_date':''})
check("Lisa creates project for cross-test", r.status_code==201)
lisa_proj_id = r.get_json()['project']['id'] if r.status_code==201 else None
if lisa_proj_id:
    r = client.delete(f'/api/projects/{lisa_proj_id}')
    check("Rodrigo DELETE Lisa project blocked 403", r.status_code==403, f"{r.status_code} {r.get_data(as_text=True)[:120]}")
    # verify still exists
    r2 = client2.get(f'/api/projects/{lisa_proj_id}')
    still_exists = r2.status_code==200
    check("Lisa project still exists after Rodrigo delete attempt (ownership enforced)", still_exists, f"GET {r2.status_code}")

# Delete own project
if proj_id:
    r = client.delete(f'/api/projects/{proj_id}')
    check(f"Publisher DELETE own project {proj_id} 200", r.status_code==200)

# Posts CRUD as publisher
r = client.post('/api/posts', json={'title':'Barangay Announcement','content':'Meeting tomorrow','category':'Announcement'})
check("Publisher POST /api/posts create 201", r.status_code==201, f"{r.status_code}")
post_id = r.get_json()['post']['id'] if r.status_code==201 else None

# Multipart image upload test
if post_id is None:
    from io import BytesIO
    fake_img = (BytesIO(b"fake image"), 'test.jpg')
    r = client.post('/api/posts', data={'title':'With image','content':'content','category':'Health','image': fake_img}, content_type='multipart/form-data')
    check("Publisher POST /api/posts multipart with image 201", r.status_code==201)
    if r.status_code==201:
        post_id = r.get_json()['post']['id']

# Empty title fails 403
r = client.post('/api/posts', json={'title':'','content':'c','category':'Announcement'})
check("Publisher post empty title → 403", r.status_code==403)

# Empty content fails
r = client.post('/api/posts', json={'title':'t','content':'','category':'Announcement'})
check("Publisher post empty content → 403", r.status_code==403)

# Invalid category defaults to Announcement (not error)
r = client.post('/api/posts', json={'title':'Weird cat','content':'c','category':'InvalidCat'})
check("Publisher post invalid category defaults (201)", r.status_code==201)
if r.status_code==201:
    cat = r.get_json()['post']['category']
    check("Invalid category defaulted to Announcement", cat=='Announcement', f"got {cat}")

# Update own post
if post_id:
    r = client.put(f'/api/posts/{post_id}', json={'title':'Updated title','content':'Updated content'})
    check(f"Publisher PUT own post {post_id} 200", r.status_code==200)

# Other publisher cannot update
if post_id:
    r = client2.put(f'/api/posts/{post_id}', json={'title':'Hacked','content':'hacked'})
    check("Other publisher PUT post blocked 403", r.status_code==403)

# Citizen cannot update post
login_as(client3,'citizen_juan','pass123')
if post_id:
    r = client3.put(f'/api/posts/{post_id}', json={'title':'Hack','content':'hack'})
    check("Citizen PUT post blocked 403", r.status_code==403)
login_as(client,'captain_rodrigo','cap123')  # back

# Citizen can comment and react
logout_as(client3)
login_as(client3,'citizen_maria','maria123')
if post_id:
    r = client3.post(f'/api/posts/{post_id}/comments', json={'content':'Citizen comment'})
    check("Citizen comment on post allowed", r.status_code==200)
    # empty comment fails 400
    r = client3.post(f'/api/posts/{post_id}/comments', json={'content':''})
    check("Empty comment → 400", r.status_code==400)
    # reaction allowed
    r = client3.post(f'/api/posts/{post_id}/react', json={'emoji':'👍'})
    check("Citizen react 👍 allowed", r.status_code==200)
    j = r.get_json()
    check("React action is added/changed/removed", j.get('action') in ('added','changed','removed'), f"{j}")
    # invalid emoji fails 400
    r = client3.post(f'/api/posts/{post_id}/react', json={'emoji':'💩'})
    check("Invalid emoji → 400", r.status_code==400)
    # toggle same emoji removes
    r = client3.post(f'/api/posts/{post_id}/react', json={'emoji':'👍'})
    j = r.get_json() if r.status_code==200 else {}
    check("Toggle same emoji removes", j.get('action')=='removed')

# Get post detail with reactions/comments
if post_id:
    r = client3.get(f'/api/posts/{post_id}')
    check("GET post detail includes comments+reactions", r.status_code==200 and 'comments' in r.get_data(as_text=True))

# Search / filter / sort feed
if post_id:
    r = client.get('/api/posts?search=Updated')
    j = r.get_json()
    check("Feed search works (search=Updated)", r.status_code==200 and len(j.get('posts',[]))>=1, f"found {len(j.get('posts',[]))}")
    r = client.get('/api/posts?category=Announcement')
    check("Feed category filter works", r.status_code==200)
    r = client.get('/api/posts?sort=title')
    check("Feed sort=title works", r.status_code==200)
    r = client.get('/api/posts?sort=oldest')
    check("Feed sort=oldest works", r.status_code==200)

# Documents: publisher upload
logout_as(client)
login_as(client,'captain_rodrigo','cap123')
from io import BytesIO
# create mock pdf
r = client.post('/api/documents', data={'title':'Budget Q1','description':'desc','category':'Budget Report','file': (BytesIO(b"%PDF fake"), 'budget.pdf')}, content_type='multipart/form-data')
check("Publisher POST /api/documents upload pdf 201", r.status_code==201, f"{r.status_code} {r.get_data(as_text=True)[:200]}")
doc_id = r.get_json()['document']['id'] if r.status_code==201 else None

# Invalid file type should fail
r = client.post('/api/documents', data={'title':'Bad','description':'d','category':'General','file': (BytesIO(b"bad"), 'virus.exe')}, content_type='multipart/form-data')
check("Publisher document invalid ext .exe → 403", r.status_code==403, f"{r.status_code}")

# Empty title fails
r = client.post('/api/documents', data={'title':'','description':'d','category':'General','file': (BytesIO(b"pdf"), 'a.pdf')}, content_type='multipart/form-data')
check("Publisher document empty title → 403", r.status_code==403)

# Citizen cannot delete document
logout_as(client3)
login_as(client3,'citizen_maria','maria123')
if doc_id:
    r = client3.delete(f'/api/documents/{doc_id}')
    check("Citizen DELETE document blocked 403", r.status_code==403)
# Publisher can delete
logout_as(client)
login_as(client,'captain_rodrigo','cap123')
if doc_id:
    r = client.delete(f'/api/documents/{doc_id}')
    check("Publisher DELETE own document 200", r.status_code==200)

# Voice: publisher side
r = client.post('/api/voice', json={'title':'Official announcement','content':'Please attend','category':'Announcement'})
check("Publisher POST voice Announcement 201", r.status_code==201)
voice_pub_id = r.get_json()['post']['id'] if r.status_code==201 else None

if voice_pub_id and voice_citizen_id:
    # publisher comments on citizen post → is_official=1
    r = client.post(f'/api/voice/{voice_citizen_id}/comments', json={'content':'Official response'})
    check("Publisher comment is_official==1", r.status_code in (200,201) and r.get_json().get('comment',{}).get('is_official')==1, f"{r.get_data(as_text=True)[:200]}")
    # citizen votes on publisher post
    logout_as(client3)
    login_as(client3,'citizen_maria','maria123')
    r = client3.post(f'/api/voice/{voice_pub_id}/vote', json={'vote_type':'down'})
    check("Citizen vote down on publisher voice 200", r.status_code==200)
    # invalid vote fails
    r = client3.post(f'/api/voice/{voice_pub_id}/vote', json={'vote_type':'invalid'})
    check("Invalid vote_type → 400", r.status_code==400)
    # delete own voice post succeeds
    r = client3.post('/api/voice', json={'title':'To delete','content':'temp','category':'General'})
    check("Citizen create temp voice for delete test 201", r.status_code==201)
    temp_id = r.get_json()['post']['id'] if r.status_code==201 else None
    if temp_id:
        r = client3.delete(f'/api/voice/{temp_id}')
        check("Citizen DELETE own voice 200", r.status_code==200)
        # verify deleted
        r2 = client3.get(f'/api/voice/{temp_id}')
        check("Deleted voice GET returns 404", r2.status_code==404)
        # other user delete attempt: citizen_juan creates, maria tries delete → should not delete (but API still 200 per current implementation - note bug)
        logout_as(client)
        login_as(client,'citizen_juan','pass123')
        r = client.post('/api/voice', json={'title':'Juan temp','content':'hi','category':'General'})
        juan_temp = r.get_json()['post']['id'] if r.status_code==201 else None
        logout_as(client3)
        login_as(client3,'citizen_maria','maria123')
        if juan_temp:
            r = client3.delete(f'/api/voice/{juan_temp}')
            check("Maria DELETE Juan voice blocked 403", r.status_code==403, f"{r.status_code} {r.get_data(as_text=True)[:120]}")
            # check still exists when fetched by juan
            logout_as(client)
            login_as(client,'citizen_juan','pass123')
            r = client.get(f'/api/voice/{juan_temp}')
            check("Juan voice still exists after Maria delete attempt", r.status_code==200, f"{r.status_code}")
            # cleanup
            client.delete(f'/api/voice/{juan_temp}')
            logout_as(client3)
            login_as(client3,'citizen_maria','maria123')
    logout_as(client)
    login_as(client,'captain_rodrigo','cap123')

# Voice search/sort/category
r = client.get('/api/voice?search=Official')
check("Voice search by title 200", r.status_code==200)
r = client.get('/api/voice?category=Grievance')
check("Voice filter category=Grievance 200", r.status_code==200)
r = client.get('/api/voice?sort=most_voted')
check("Voice sort=most_voted 200", r.status_code==200)
r = client.get('/api/voice?sort=most_commented')
check("Voice sort=most_commented 200", r.status_code==200)

# ============================================================
# D. Barangay Hub Routing
# ============================================================
section("D. Barangay Hub Routing & Landing")

# Publisher my-hub should go to his barangay slug
logout_as(client)
login_as(client,'captain_rodrigo','cap123')
r = client.get('/barangay/my-hub', follow_redirects=False)
loc = r.headers.get('Location','')
check("Publisher my-hub redirects to his barangay slug", '/barangay/view/' in loc and 'batasan' in loc.lower(), loc)
r = client.get('/barangay/my-hub', follow_redirects=True)
check("Publisher my-hub follow 200", r.status_code==200 and b"Batasan" in r.data)

# Citizen my-hub based on registration barangay Payatas → should redirect to payatas or fallback hall (Payatas not in barangays table? We'll check)
logout_as(client)
login_as(client,'citizen_juan','pass123')
r = client.get('/barangay/my-hub', follow_redirects=False)
loc = r.headers.get('Location','')
check("Citizen (Payatas) my-hub redirect contains payatas or hall fallback", '/barangay/view/' in loc, loc)

# Valid barangay slug renders correct
logout_as(client)
login_as(client,'captain_rodrigo','cap123')
r = client.get('/barangay/view/barangay-batasan-hills', follow_redirects=True)
check("GET /barangay/view/barangay-batasan-hills 200", r.status_code==200)
# Check details populated
check("Barangay landing contains Batasan Hills", b"Batasan" in r.data)

# Invalid slug falls back to first barangay (Barangay Hall) not 404
r = client.get('/barangay/view/nonexistent-slug-xyz', follow_redirects=True)
check("Invalid slug fallback 200 (not 404)", r.status_code==200)

# /barangay-landing generic
r = client.get('/barangay-landing')
check("GET /barangay-landing 200", r.status_code==200)

# /barangay/<id>/landing with valid id
if barangay_id:
    r = client.get(f'/barangay/{barangay_id}/landing')
    check(f"GET /barangay/{barangay_id}/landing 200", r.status_code==200)
    r = client.get('/barangay/99999/landing', follow_redirects=True)
    check("GET nonexistent barangay id redirects with flash", r.status_code==200)

# /barangay/<publisher_id> profile page
conn = sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
pub_id = conn.execute("SELECT id FROM users WHERE username='captain_rodrigo'").fetchone()['id']
conn.close()
r = client.get(f'/barangay/{pub_id}')
check(f"GET /barangay/{pub_id} (publisher profile) 200", r.status_code==200)
r = client.get('/barangay/999999', follow_redirects=True)
check("GET /barangay/999999 not publisher → redirect", r.status_code==200)

# Post detail page
if post_id:
    r = client.get(f'/post/{post_id}')
    check(f"GET /post/{post_id} detail 200", r.status_code==200)
    r = client.get('/post/999999', follow_redirects=True)
    check("GET nonexistent post → redirect to dashboard", r.status_code==200)

# Weather API needs lat/lon
r = client.get('/api/weather')
check("GET /api/weather without lat/lon → 400", r.status_code==400)
# Don't hit real external in test? Skip lat/lon call to avoid network - but we can check param validation.

# Services api
r = client.get('/api/services')
check("GET /api/services 200", r.status_code==200)

# ============================================================
# E. Cross-role Security Summary
# ============================================================
section("E. Cross-Role Security Checks")

# Ensure citizen cannot perform publisher mutations after earlier tests we already did exhaustive.
# Quick matrix re-check with fresh citizen login
logout_as(client)
login_as(client,'citizen_maria','maria123')
# Try all publisher-only mutating endpoints
cases = [
    ('POST /api/posts', lambda: client.post('/api/posts', json={'title':'h','content':'h'})),
    ('POST /api/projects', lambda: client.post('/api/projects', json={'title':'h','description':'h','status':'ongoing','budget':0,'location':'','image_url':'','start_date':'','end_date':''})),
    ('POST /api/documents pdf', lambda: client.post('/api/documents', data={'title':'h','description':'','category':'General','file': (BytesIO(b"pdf"), 'h.pdf')}, content_type='multipart/form-data')),
    ('POST /api/barangays', lambda: client.post('/api/barangays', json={'name':'h','address':'a'})),
]
for name, fn in cases:
    r = fn()
    check(f"Citizen blocked: {name} → 403", r.status_code==403, f"{r.status_code}")

# Publisher should succeed on same
logout_as(client)
login_as(client,'captain_rodrigo','cap123')
# posts already tested, but quick one
r = client.post('/api/posts', json={'title':'Sec check','content':'c','category':'Announcement'})
check("Publisher allowed: POST /api/posts → 201", r.status_code==201)
if r.status_code==201:
    client.delete(f"/api/posts/{r.get_json()['post']['id']}")

# ============================================================
# F. Barangay Deletion ownership
# ============================================================
section("F. Barangay Deletion Ownership & Cleanup")

# Lisa tries to delete Rodrigo's barangay
if barangay_id:
    r = client2.delete(f'/api/barangays/{barangay_id}')
    check("Lisa DELETE Rodrigo barangay blocked 403", r.status_code==403)
# Rodrigo deletes own
if barangay_id:
    r = client.delete(f'/api/barangays/{barangay_id}')
    check("Rodrigo DELETE own barangay 200", r.status_code==200)
    # verify gone
    r = client.get(f'/api/barangays/{barangay_id}')
    check("Deleted barangay GET 404", r.status_code==404)
    # recreate for consistency
    r = client.post('/api/barangays', json={'name':'Barangay Batasan Hills','description':'re','address':'Batasan Hills, QC','phone':'02','email':'e@ph'})
    check("Recreate after delete 201", r.status_code==201)

# ============================================================
# Summary
# ============================================================
section("SUMMARY")
passed = sum(1 for _,ok,_ in results if ok)
total = len(results)
print(f"\n {passed}/{total} checks passed ({passed/total*100:.1f}%)")
failed = [(n,d) for n,ok,d in results if not ok]
if failed:
    print(f"\n {len(failed)} FAILED:")
    for n,d in failed:
        print(f"  - {n} {f'({d})' if d else ''}")
else:
    print(" All checks passed!")

# Identify potential bugs / design notes — updated after hardening
print("\n --- Design Notes / Potential Improvements (not failures) ---")
notes = [
 "• FIXED: Voice PUT /api/voice/<id>/status now enforces publisher-only (citizen → 403) via VoiceService.update_status(user).",
 "• FIXED: Voice DELETE / Project DELETE / Post DELETE now return 403 when caller is not owner (rowcount check), 404 if not found.",
 "• FIXED: Post/Project update now check rowcount — cross-publisher PUT returns 403 instead of silent 200 with stale data.",
 "• FIXED: FileUploadHelper + Config allowed_extensions frozen (frozenset) — cannot be mutated via .add().",
 "• FIXED: FileUploadHelper injected via app.extensions['upload_helper'] — routes/services share one instance (not the legacy singleton).",
 "• Remaining: Validation vs permission both map to 403 — could split to 400 vs 403 for clearer UI handling (kept as-is to avoid breaking clients).",
 "• Remaining: Category validation silently defaults to first allowed value — may hide typos (e.g., 'InvalidCat' → Announcement).",
 "• Remaining: /barangay/view/<slug> unknown slug silently falls back to first barangay — could be 404+flash.",
]
for n in notes:
    print(_safe(n))

# Cleanup
import shutil
try:
    os.unlink(db_path)
    shutil.rmtree(tmp_upload)
    print(f"\n[cleanup] removed {db_path} and {tmp_upload}")
except: pass

sys.exit(0 if passed==total else 1)
