"""
Unit tests for the GovKonek repository module.

Follows the crash course unit_testing_in_python pattern:
  - unittest.TestCase with setUp/tearDown
  - Uses temp file database for isolation (dependency injection)
  - Tests BaseRepository, UserRepository, PostRepository

Tests OOP principles:
  - INHERITANCE: All repos are instances of BaseRepository
  - ABSTRACTION: BaseRepository provides shared _execute/_execute_write
  - EXCEPTION HANDLING: Custom exceptions raised for error conditions

NOTE: SQLite :memory: databases are per-connection, so each _get_db()
call creates a new isolated in-memory DB.  Tests use a temp file so
all connections share the same database.
"""

import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repository import (
    BaseRepository, UserRepository, PostRepository,
    ProjectRepository, DBContext
)
from exceptions import (
    DatabaseError, DuplicateRecordError, ConnectionError
)


# ===========================================================================
# DBContext Tests
# ===========================================================================

class TestDBContext(unittest.TestCase):
    """
    Tests for the DBContext context manager.

    From the crash course (hardware_layer.py): uses `with` for automatic
    resource cleanup.
    """

    def setUp(self):
        """Create a temp file database for each test."""
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        """Clean up the temp database."""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_context_manager_returns_connection(self):
        """Entering the context should return a sqlite3 connection."""
        with DBContext(self.db_path) as conn:
            self.assertIsNotNone(conn)
            conn.execute('CREATE TABLE test (id INTEGER)')
            conn.execute('INSERT INTO test VALUES (1)')
            conn.commit()
            result = conn.execute('SELECT * FROM test').fetchone()
            self.assertEqual(result['id'], 1)

    def test_context_manager_closes_connection(self):
        """Connection should be closed after exiting the context."""
        with DBContext(self.db_path) as conn:
            pass
        import sqlite3
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute('SELECT 1')

    def test_context_manager_rollback_on_error(self):
        """
        EXCEPTION HANDLING: When an exception occurs inside the `with` block,
        the context manager should rollback uncommitted changes.
        """
        with DBContext(self.db_path) as conn:
            conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY)')
            conn.commit()

        try:
            with DBContext(self.db_path) as conn:
                conn.execute('INSERT INTO test VALUES (1)')
                raise ValueError("Simulated error")
        except ValueError:
            pass

        with DBContext(self.db_path) as conn:
            result = conn.execute('SELECT COUNT(*) FROM test').fetchone()
            self.assertEqual(result[0], 0)


# ===========================================================================
# BaseRepository Tests (INHERITANCE)
# ===========================================================================

class TestBaseRepository(unittest.TestCase):
    """Tests for the BaseRepository abstract class."""

    def setUp(self):
        """Create a concrete subclass with a temp file database."""
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

        class TestRepo(BaseRepository):
            pass
        self.repo = TestRepo(db_path=self.db_path)
        # Create schema using the repo's own connection
        self.repo._execute_write(
            'CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)'
        )

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_db_path_is_stored(self):
        """BaseRepository stores db_path (ENCAPSULATION)."""
        self.assertEqual(self.repo._db_path, self.db_path)

    def test_execute_fetch_all(self):
        """_execute with fetch='all' should return a list of rows."""
        self.repo._execute_write(
            'INSERT INTO items (name) VALUES (?)', ('apple',)
        )
        results = self.repo._execute('SELECT * FROM items', fetch='all')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'apple')

    def test_execute_fetch_one(self):
        """_execute with fetch='one' should return a single row or None."""
        result = self.repo._execute(
            'SELECT * FROM items WHERE id = 999', fetch='one'
        )
        self.assertIsNone(result)

    def test_execute_write_returns_cursor(self):
        """_execute_write should return a cursor with lastrowid."""
        cursor = self.repo._execute_write(
            'INSERT INTO items (name) VALUES (?)', ('banana',)
        )
        self.assertIsNotNone(cursor.lastrowid)
        self.assertGreater(cursor.lastrowid, 0)

    def test_database_error_on_bad_query(self):
        """
        EXCEPTION HANDLING: Invalid SQL should raise DatabaseError.
        From the lecture: 'Catch errors gracefully.'
        """
        with self.assertRaises(DatabaseError):
            self.repo._execute('SELECT * FROM nonexistent_table', fetch='all')


# ===========================================================================
# UserRepository Tests
# ===========================================================================

class TestUserRepository(unittest.TestCase):
    """Tests for UserRepository (INHERITANCE + CRUD)."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

        self.repo = UserRepository(db_path=self.db_path)
        # Create schema via repo's own connection
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_is_instance_of_base_repository(self):
        """INHERITANCE: UserRepository IS-A BaseRepository."""
        self.assertIsInstance(self.repo, BaseRepository)

    def test_create_user_success(self):
        """Create a user should return True."""
        result = self.repo.create('juan', 'hashed_pw', 'citizen')
        self.assertTrue(result)

    def test_create_duplicate_user_fails(self):
        """
        EXCEPTION HANDLING: Creating a duplicate username should return False
        (catches DuplicateRecordError internally).
        """
        self.repo.create('juan', 'hash1', 'citizen')
        result = self.repo.create('juan', 'hash2', 'citizen')
        self.assertFalse(result)

    def test_find_by_id_returns_user(self):
        """find_by_id should return the user row."""
        self.repo.create('maria', 'hash_maria', 'citizen')
        user = self.repo.find_by_username('maria')
        self.assertIsNotNone(user)
        found = self.repo.find_by_id(user['id'])
        self.assertEqual(found['username'], 'maria')

    def test_find_by_id_nonexistent_returns_none(self):
        """find_by_id for nonexistent user should return None."""
        result = self.repo.find_by_id(99999)
        self.assertIsNone(result)

    def test_find_by_username_returns_user(self):
        """find_by_username should return the correct user."""
        self.repo.create('pedro', 'hash_pedro', 'publisher')
        user = self.repo.find_by_username('pedro')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'pedro')
        self.assertEqual(user['role'], 'publisher')

    def test_find_by_username_nonexistent_returns_none(self):
        """find_by_username for nonexistent user should return None."""
        result = self.repo.find_by_username('nobody')
        self.assertIsNone(result)


# ===========================================================================
# PostRepository Tests
# ===========================================================================

class TestPostRepository(unittest.TestCase):
    """Tests for PostRepository CRUD operations."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

        self.repo = PostRepository(db_path=self.db_path)
        # Create all needed tables
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publisher_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'published',
                category TEXT DEFAULT 'Announcement',
                image_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (publisher_id) REFERENCES users(id)
            )
        ''')
        self.repo._execute_write('''
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
        self.repo._execute_write('''
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

        # Create a test publisher user
        user_repo = UserRepository(db_path=self.db_path)
        user_repo.create('captain', 'hash', 'publisher')
        self.publisher = user_repo.find_by_username('captain')
        self.publisher_id = self.publisher['id']

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_is_instance_of_base_repository(self):
        """INHERITANCE: PostRepository IS-A BaseRepository."""
        self.assertIsInstance(self.repo, BaseRepository)

    def test_create_post(self):
        """Create a post and verify it's returned."""
        post = self.repo.create_post(
            self.publisher_id, 'Test Title', 'Test Content', 'Announcement'
        )
        self.assertIsNotNone(post)
        self.assertEqual(post['title'], 'Test Title')
        self.assertEqual(post['category'], 'Announcement')
        self.assertEqual(post['publisher_name'], 'captain')

    def test_get_all_posts_returns_published(self):
        """get_all_posts should return only published posts."""
        self.repo.create_post(self.publisher_id, 'Post 1', 'C1', 'Announcement')
        self.repo.create_post(self.publisher_id, 'Post 2', 'C2', 'Health')
        posts = self.repo.get_all_posts()
        self.assertEqual(len(posts), 2)

    def test_get_all_posts_with_category_filter(self):
        """get_all_posts should filter by category."""
        self.repo.create_post(self.publisher_id, 'P1', 'C1', 'Announcement')
        self.repo.create_post(self.publisher_id, 'P2', 'C2', 'Health')
        posts = self.repo.get_all_posts(category='Health')
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['category'], 'Health')

    def test_get_all_posts_with_search(self):
        """get_all_posts should search in title and content."""
        self.repo.create_post(self.publisher_id, 'Barangay Cleanup', 'Join us!', 'Announcement')
        self.repo.create_post(self.publisher_id, 'Health Mission', 'Free checkup', 'Health')
        posts = self.repo.get_all_posts(search='Cleanup')
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['title'], 'Barangay Cleanup')

    def test_get_post_by_id(self):
        """get_post_by_id should return the correct post."""
        created = self.repo.create_post(self.publisher_id, 'T1', 'C1', 'Announcement')
        post = self.repo.get_post_by_id(created['id'])
        self.assertEqual(post['title'], 'T1')

    def test_get_post_by_id_nonexistent(self):
        """get_post_by_id for nonexistent post returns None."""
        result = self.repo.get_post_by_id(99999)
        self.assertIsNone(result)

    def test_update_post(self):
        """update_post should modify the post."""
        created = self.repo.create_post(self.publisher_id, 'Old', 'OldC', 'Announcement')
        updated = self.repo.update_post(created['id'], self.publisher_id, 'New', 'NewC')
        self.assertIsNotNone(updated)
        self.assertEqual(updated['title'], 'New')
        self.assertEqual(updated['content'], 'NewC')

    def test_delete_post(self):
        """delete_post should remove the post."""
        created = self.repo.create_post(self.publisher_id, 'Del', 'DelC', 'Announcement')
        result = self.repo.delete_post(created['id'], self.publisher_id)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
