"""
GovKonek Repository Module

Database Layer - ABSTRACTION PRINCIPLE
Purpose: The Repository pattern abstracts all database operations.
Benefits: Database code is isolated, easy to change database without touching business logic.
All database queries are centralized in one place for easier maintenance and testing.

REFACTORED for testability:
    - Each repository accepts a `db_path` in its constructor (dependency injection).
    - Instance methods use `self._db_path` instead of a module-level global.
    - In tests, inject `':memory:'` to get an isolated database.
    - Backward-compatible static methods delegate to a default singleton instance.
"""

import sqlite3
from config import DATABASE_NAME


# ---------------------------------------------------------------------------
# Helper: shared connection factory (not tied to any class)
# ---------------------------------------------------------------------------

def _connect(db_path):
    """Create a connection with Row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
# UserRepository
# ===========================================================================

class UserRepository:
    """
    Repository for user-related database operations.

    REFACTORED: Now instance-based. Pass `db_path` to the constructor.
    For backward compatibility, static methods still work using the default
    module-level singleton `_default_user_repo`.
    """

    def __init__(self, db_path=None):
        """
        @param db_path: Path to SQLite database file.
                        Defaults to config.DATABASE_NAME.
                        Use ':memory:' for isolated testing.
        """
        self._db_path = db_path or DATABASE_NAME

    # -- connection helper ------------------------------------------------

    def _get_db(self):
        """Create and return a new database connection."""
        return _connect(self._db_path)

    # -- user CRUD --------------------------------------------------------

    def find_by_id(self, user_id):
        """Fetch a user by their ID."""
        conn = self._get_db()
        user_data = conn.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        conn.close()
        return user_data

    def find_by_username(self, username):
        """Fetch a user by their username."""
        conn = self._get_db()
        user_data = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        return user_data

    def create(self, username, hashed_password, role):
        """Insert a new user. Returns True on success, False on duplicate."""
        conn = self._get_db()
        try:
            conn.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, hashed_password, role)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    # -- backward-compatible static interface -----------------------------
    # Only static methods that DON'T shadow instance methods are kept here.
    # Instance methods (find_by_id, find_by_username, create) are the
    # primary API.  Routes use injected instances via current_app.extensions.

    @staticmethod
    def get_db_connection():
        """Legacy: create a connection using the default database."""
        return _connect(DATABASE_NAME)


# ===========================================================================
# PostRepository
# ===========================================================================

class PostRepository:
    """
    Repository for post, comment, and reaction database operations.

    REFACTORED: Now instance-based. Pass `db_path` to the constructor.
    Static methods are kept as thin wrappers around a default instance.
    """

    def __init__(self, db_path=None):
        """
        @param db_path: Path to SQLite database file.
                        Defaults to config.DATABASE_NAME.
                        Use ':memory:' for isolated testing.
        """
        self._db_path = db_path or DATABASE_NAME

    def _get_db(self):
        return _connect(self._db_path)

    # -- post CRUD --------------------------------------------------------

    def create_post(self, publisher_id, title, content, status='published'):
        """Create a new post. Returns the created post as a dict."""
        conn = self._get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO posts (publisher_id, title, content, status) VALUES (?, ?, ?, ?)',
                (publisher_id, title, content, status)
            )
            conn.commit()
            post_id = cursor.lastrowid
            post = conn.execute('''
                SELECT p.*, u.username as publisher_name
                FROM posts p JOIN users u ON p.publisher_id = u.id
                WHERE p.id = ?
            ''', (post_id,)).fetchone()
            return dict(post) if post else None
        finally:
            conn.close()

    def update_post(self, post_id, publisher_id, title, content):
        """Update a post. Only the owning publisher can update."""
        conn = self._get_db()
        try:
            conn.execute(
                'UPDATE posts SET title = ?, content = ? WHERE id = ? AND publisher_id = ?',
                (title, content, post_id, publisher_id)
            )
            conn.commit()
            post = conn.execute('''
                SELECT p.*, u.username as publisher_name
                FROM posts p JOIN users u ON p.publisher_id = u.id
                WHERE p.id = ?
            ''', (post_id,)).fetchone()
            return dict(post) if post else None
        finally:
            conn.close()

    def delete_post(self, post_id, publisher_id):
        """Delete a post. Only the owning publisher can delete."""
        conn = self._get_db()
        try:
            conn.execute(
                'DELETE FROM posts WHERE id = ? AND publisher_id = ?',
                (post_id, publisher_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_all_posts(self):
        """Fetch all published posts, newest first."""
        conn = self._get_db()
        posts = conn.execute('''
            SELECT p.*, u.username as publisher_name
            FROM posts p
            JOIN users u ON p.publisher_id = u.id
            WHERE p.status = 'published'
            ORDER BY p.created_at DESC
        ''').fetchall()
        conn.close()
        return posts

    def get_post_by_id(self, post_id):
        """Fetch a single post by ID."""
        conn = self._get_db()
        post = conn.execute('''
            SELECT p.*, u.username as publisher_name
            FROM posts p
            JOIN users u ON p.publisher_id = u.id
            WHERE p.id = ?
        ''', (post_id,)).fetchone()
        conn.close()
        return post

    # -- comments ---------------------------------------------------------

    def get_comments_for_post(self, post_id):
        """Fetch all comments for a post with usernames."""
        conn = self._get_db()
        comments = conn.execute('''
            SELECT c.*, u.username
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
        ''', (post_id,)).fetchall()
        conn.close()
        return comments

    def add_comment(self, post_id, user_id, content):
        """Add a comment. Returns the new comment as a Row."""
        conn = self._get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)',
                (post_id, user_id, content)
            )
            conn.commit()
            comment_id = cursor.lastrowid
            comment = conn.execute('''
                SELECT c.*, u.username
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.id = ?
            ''', (comment_id,)).fetchone()
            return comment
        finally:
            conn.close()

    # -- reactions --------------------------------------------------------

    def get_reactions_for_post(self, post_id):
        """Fetch aggregated emoji counts for a post."""
        conn = self._get_db()
        counts = conn.execute('''
            SELECT emoji, COUNT(*) as count
            FROM reactions
            WHERE post_id = ?
            GROUP BY emoji
            ORDER BY count DESC
        ''', (post_id,)).fetchall()
        conn.close()
        return counts

    def get_user_reaction(self, post_id, user_id):
        """Get the emoji a specific user reacted with, or None."""
        conn = self._get_db()
        reaction = conn.execute(
            'SELECT emoji FROM reactions WHERE post_id = ? AND user_id = ?',
            (post_id, user_id)
        ).fetchone()
        conn.close()
        return reaction['emoji'] if reaction else None

    def toggle_reaction(self, post_id, user_id, emoji):
        """
        Toggle a reaction:
          - same emoji  → remove   (returns 'removed')
          - different   → update   (returns 'changed')
          - none        → add      (returns 'added')
        """
        conn = self._get_db()
        try:
            existing = conn.execute(
                'SELECT id, emoji FROM reactions WHERE post_id = ? AND user_id = ?',
                (post_id, user_id)
            ).fetchone()

            if existing:
                if existing['emoji'] == emoji:
                    conn.execute('DELETE FROM reactions WHERE id = ?', (existing['id'],))
                    conn.commit()
                    return 'removed', emoji
                else:
                    conn.execute(
                        'UPDATE reactions SET emoji = ? WHERE id = ?',
                        (emoji, existing['id'])
                    )
                    conn.commit()
                    return 'changed', emoji
            else:
                conn.execute(
                    'INSERT INTO reactions (post_id, user_id, emoji) VALUES (?, ?, ?)',
                    (post_id, user_id, emoji)
                )
                conn.commit()
                return 'added', emoji
        finally:
            conn.close()

    # -- backward-compatible static interface -----------------------------
    # Only static methods that DON'T shadow instance methods are kept here.

    @staticmethod
    def get_db_connection():
        """Legacy: create a connection using the default database."""
        return _connect(DATABASE_NAME)


# ===========================================================================
# ProjectRepository
# ===========================================================================

class ProjectRepository:
    """Repository for barangay project operations."""

    def __init__(self, db_path=None):
        self._db_path = db_path or DATABASE_NAME

    def _get_db(self):
        return _connect(self._db_path)

    def get_all(self):
        conn = self._get_db()
        projects = conn.execute(
            'SELECT * FROM projects ORDER BY created_at DESC'
        ).fetchall()
        conn.close()
        return [dict(p) for p in projects]

    def get_by_status(self, status):
        conn = self._get_db()
        projects = conn.execute(
            'SELECT * FROM projects WHERE status = ? ORDER BY created_at DESC',
            (status,)
        ).fetchall()
        conn.close()
        return [dict(p) for p in projects]

    def get_by_id(self, project_id):
        conn = self._get_db()
        project = conn.execute(
            'SELECT * FROM projects WHERE id = ?', (project_id,)
        ).fetchone()
        conn.close()
        return dict(project) if project else None


# ===========================================================================
# ServiceRepository
# ===========================================================================

class ServiceRepository:
    """Repository for e-services operations."""

    def __init__(self, db_path=None):
        self._db_path = db_path or DATABASE_NAME

    def _get_db(self):
        return _connect(self._db_path)

    def get_all(self):
        conn = self._get_db()
        services = conn.execute(
            'SELECT * FROM services WHERE is_active = 1 ORDER BY category, name'
        ).fetchall()
        conn.close()
        return [dict(s) for s in services]

    def get_by_category(self, category):
        conn = self._get_db()
        services = conn.execute(
            'SELECT * FROM services WHERE category = ? AND is_active = 1 ORDER BY name',
            (category,)
        ).fetchall()
        conn.close()
        return [dict(s) for s in services]

    def get_categories(self):
        conn = self._get_db()
        cats = conn.execute(
            'SELECT DISTINCT category FROM services WHERE is_active = 1 ORDER BY category'
        ).fetchall()
        conn.close()
        return [c['category'] for c in cats]


# ===========================================================================
# DocumentRepository
# ===========================================================================

class DocumentRepository:
    """Repository for transparency document operations."""

    def __init__(self, db_path=None):
        self._db_path = db_path or DATABASE_NAME

    def _get_db(self):
        return _connect(self._db_path)

    def get_all(self):
        conn = self._get_db()
        docs = conn.execute(
            'SELECT * FROM documents ORDER BY published_date DESC'
        ).fetchall()
        conn.close()
        return [dict(d) for d in docs]

    def get_by_category(self, category):
        conn = self._get_db()
        docs = conn.execute(
            'SELECT * FROM documents WHERE category = ? ORDER BY published_date DESC',
            (category,)
        ).fetchall()
        conn.close()
        return [dict(d) for d in docs]

    def get_categories(self):
        conn = self._get_db()
        cats = conn.execute(
            'SELECT DISTINCT category FROM documents ORDER BY category'
        ).fetchall()
        conn.close()
        return [c['category'] for c in cats]
