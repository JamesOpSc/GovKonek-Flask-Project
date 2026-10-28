"""
GovKonek UI Page & Template Rendering Tests

Tests that verify UI bug fixes, template rendering, flash alert categorization,
and responsive components.
"""

import unittest
import tempfile
import os
import sqlite3
from config import Config
from app import create_app


def init_test_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
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
        vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voice_post_id) REFERENCES voice_posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(voice_post_id, user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS barangays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT 'Barangay Hall',
        description TEXT DEFAULT '', address TEXT DEFAULT '',
        phone TEXT DEFAULT '', email TEXT DEFAULT '',
        facebook TEXT DEFAULT '', office_hours_weekday TEXT DEFAULT '8:00 AM – 5:00 PM',
        office_hours_saturday TEXT DEFAULT '8:00 AM – 12:00 PM',
        motto TEXT DEFAULT '', hero_image TEXT DEFAULT '',
        latitude REAL DEFAULT 14.71309, longitude REAL DEFAULT 121.10063,
        publisher_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (publisher_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()


class TestUIPages(unittest.TestCase):
    """Integration tests checking UI templates, flash messages, and rendering."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        init_test_db(self.db_path)

        self.config = Config(db_name=self.db_path, secret_key='test-secret-key')
        self.app = create_app(self.config)
        self.client = self.app.test_client()

        # Register publisher and citizen accounts
        self.client.post('/register', data={
            'username': 'ui_captain',
            'password': 'password123',
            'role': 'publisher',
            'barangay': 'Payatas'
        })
        self.client.post('/register', data={
            'username': 'ui_citizen',
            'password': 'password123',
            'role': 'citizen',
            'barangay': 'Payatas'
        })

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except OSError:
            pass

    def test_login_page_renders_with_closed_card(self):
        """Verify login page renders properly with .login-card container and brand header."""
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('class="login-card"', html)
        self.assertIn('GovKonek', html)
        self.assertIn('Sign In', html)
        self.assertIn('</div>\n\n</body>', html)

    def test_login_flash_success_and_error_classes(self):
        """Verify flash messages on login have alert-success or alert-error classes."""
        # 1. Registration success flash message on login page
        resp = self.client.post('/register', data={
            'username': 'new_resident',
            'password': 'password123',
            'role': 'citizen',
            'barangay': 'Payatas'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('alert-success', html)
        self.assertIn('Registration successful', html)

        # 2. Invalid login error flash message
        resp = self.client.post('/login', data={
            'username': 'non_existent_user',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('alert-error', html)
        self.assertIn('Invalid username or password', html)

    def test_projects_page_rendering_and_data_attributes(self):
        """Verify projects page renders and data-project-id attributes are used."""
        # Log in as publisher
        self.client.post('/login', data={'username': 'ui_captain', 'password': 'password123'})
        resp = self.client.get('/projects')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('Barangay Projects', html)
        self.assertIn('projectGrid', html)
        self.assertIn('data-project-id', html)

    def test_citizens_voice_category_pills(self):
        """Verify citizens' voice page contains category filter pills."""
        self.client.post('/login', data={'username': 'ui_citizen', 'password': 'password123'})
        resp = self.client.get('/citizens-voice')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('voice-filters', html)
        self.assertIn('data-category="Grievance"', html)
        self.assertIn('data-category="Suggestion"', html)
        self.assertIn('data-category="Question"', html)

    def test_sidebar_active_page_matching(self):
        """Verify sidebar includes barangay-landing matching in page targets."""
        self.client.post('/login', data={'username': 'ui_citizen', 'password': 'password123'})
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('/barangay-landing', html)
        self.assertIn('data-page="barangay"', html)

    def test_barangay_landing_announcements_clickable(self):
        """Verify announcements on barangay landing page are clickable links."""
        self.client.post('/login', data={'username': 'ui_captain', 'password': 'password123'})
        resp = self.client.get('/barangay-landing')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('announcementsList', html)

    def test_documents_transparency_page(self):
        """Verify transparency documents page renders with filter elements."""
        self.client.post('/login', data={'username': 'ui_citizen', 'password': 'password123'})
        resp = self.client.get('/documents')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('Transparency Documents', html)
        self.assertIn('categorySelect', html)


if __name__ == '__main__':
    unittest.main()
