"""Integration test for Transparency Document upload feature."""
import sys, os, tempfile, sqlite3, io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup temp DB with necessary tables
tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
db_path = tmp.name
tmp.close()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL)''')
c.execute('''CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'General',
    file_url TEXT DEFAULT '#',
    file_size TEXT DEFAULT '',
    published_date TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()
conn.close()

# Ensure upload folder exists
os.makedirs('static/uploads', exist_ok=True)

from config import Config
from app import create_app

app = create_app(Config(db_name=db_path, secret_key='test'))
client = app.test_client()

results = []

# 1. Register publisher
client.post('/register', data={
    'username': 'captain', 'password': 'pw123', 'role': 'publisher'
})
# 2. Login
client.post('/login', data={'username': 'captain', 'password': 'pw123'})

# 3. Upload a document
data = {
    'title': 'Test Budget Report 2026',
    'description': 'This is a test document upload via the API.',
    'category': 'Budget Report',
    'published_date': '2026-06-04',
    'file': (io.BytesIO(b'This is test PDF content for upload.'), 'test_report.pdf')
}
r = client.post('/api/documents', data=data, content_type='multipart/form-data')
ok = r.status_code == 201
results.append(('POST /api/documents (upload)', ok))
if not ok:
    print(f'Upload failed: {r.get_json()}')

# 4. Verify document in list
r = client.get('/api/documents')
docs = r.get_json().get('documents', [])
ok = len(docs) > 0
results.append((f'GET /api/documents ({len(docs)} docs)', ok))

if docs:
    doc = docs[0]
    # Verify fields
    ok = doc['title'] == 'Test Budget Report 2026'
    results.append(('Document title matches', ok))
    ok = doc['category'] == 'Budget Report'
    results.append(('Document category matches', ok))
    ok = doc['file_url'].startswith('/static/uploads/')
    results.append(('File URL is correct path', ok))
    ok = doc['file_size'] is not None and len(doc['file_size']) > 0
    results.append(('File size recorded', ok))

    # Verify physical file exists
    file_path = os.path.join(os.getcwd(), doc['file_url'].lstrip('/'))
    ok = os.path.exists(file_path)
    results.append(('File exists on disk', ok))

    # 5. Delete document
    doc_id = doc['id']
    r = client.delete(f'/api/documents/{doc_id}')
    ok = r.status_code == 200
    results.append(('DELETE /api/documents/<id>', ok))

    # Verify file removed
    ok = not os.path.exists(file_path)
    results.append(('File removed from disk on delete', ok))

    # Verify not in list anymore
    r = client.get('/api/documents')
    remaining = r.get_json().get('documents', [])
    ok = all(d['id'] != doc_id for d in remaining)
    results.append(('Document removed from list', ok))

# 6. Citizen cannot upload
client.get('/logout')
client.post('/register', data={
    'username': 'citizen1', 'password': 'pw123', 'role': 'citizen'
})
client.post('/login', data={'username': 'citizen1', 'password': 'pw123'})
data2 = {
    'title': 'Hacker Doc',
    'description': 'Should fail',
    'category': 'General',
    'file': (io.BytesIO(b'bad'), 'bad.pdf')
}
r = client.post('/api/documents', data=data2, content_type='multipart/form-data')
ok = r.status_code == 403
results.append(('Citizen upload blocked (403)', ok))

# Cleanup
client.get('/logout')
os.unlink(db_path)
for f in os.listdir('static/uploads'):
    if f.startswith('2026'):
        os.remove(os.path.join('static/uploads', f))

# Report
print()
passed = sum(1 for _, ok in results if ok)
for name, ok in results:
    print(f"  {'✅' if ok else '❌'} {name}")
print(f"  {passed}/{len(results)} tests passed")
if passed == len(results):
    print("  ALL DOCUMENT UPLOAD TESTS PASSED!")
