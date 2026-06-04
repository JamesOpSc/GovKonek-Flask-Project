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

    def create_post(self, publisher_id, title, content, category='Announcement', status='published'):
        """Create a new post. Returns the created post as a dict."""
        conn = self._get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO posts (publisher_id, title, content, category, status) VALUES (?, ?, ?, ?, ?)',
                (publisher_id, title, content, category, status)
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

    def get_all_posts(self, search=None, category=None, sort='newest'):
        """
        Fetch published posts with optional search, category filter, and sorting.

        @param search: Text to search in title and content (case-insensitive).
        @param category: Filter by post category (e.g. 'Announcement', 'Emergency', 'Health', 'Project').
                         Pass None or empty string for all categories.
        @param sort: Sort order — 'newest' (default), 'oldest', 'title'.
        @return: List of sqlite3.Row objects.
        """
        conn = self._get_db()

        query = '''
            SELECT p.*, u.username as publisher_name
            FROM posts p
            JOIN users u ON p.publisher_id = u.id
            WHERE p.status = 'published'
        '''
        params = []

        if search and search.strip():
            query += ' AND (p.title LIKE ? OR p.content LIKE ?)'
            like_val = f'%{search.strip()}%'
            params.extend([like_val, like_val])

        if category and category.strip():
            query += ' AND p.category = ?'
            params.append(category.strip())

        # Sorting
        sort_map = {
            'newest': 'p.created_at DESC',
            'oldest': 'p.created_at ASC',
            'title': 'p.title ASC',
        }
        order_clause = sort_map.get(sort, 'p.created_at DESC')
        query += f' ORDER BY {order_clause}'

        posts = conn.execute(query, params).fetchall()
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


# ===========================================================================
# VoiceRepository — Citizens' Voice forum
# ===========================================================================

class VoiceRepository:
    """Repository for Citizens' Voice forum operations."""

    def __init__(self, db_path=None):
        self._db_path = db_path or DATABASE_NAME

    def _get_db(self):
        return _connect(self._db_path)

    # -- voice posts CRUD ------------------------------------------------

    def get_all(self, category=None, status=None):
        """Fetch all voice posts with author names, newest first. Optional filters."""
        conn = self._get_db()
        query = '''
            SELECT vp.*, u.username as author_name, u.role as author_role,
                   (SELECT COUNT(*) FROM voice_comments vc WHERE vc.voice_post_id = vp.id) as comment_count
            FROM voice_posts vp
            JOIN users u ON vp.user_id = u.id
            WHERE 1=1
        '''
        params = []
        if category:
            query += ' AND vp.category = ?'
            params.append(category)
        if status:
            query += ' AND vp.status = ?'
            params.append(status)
        query += ' ORDER BY vp.created_at DESC'
        posts = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(p) for p in posts]

    def get_by_id(self, voice_post_id):
        """Fetch a single voice post with author info."""
        conn = self._get_db()
        post = conn.execute('''
            SELECT vp.*, u.username as author_name, u.role as author_role,
                   (SELECT COUNT(*) FROM voice_comments vc WHERE vc.voice_post_id = vp.id) as comment_count
            FROM voice_posts vp
            JOIN users u ON vp.user_id = u.id
            WHERE vp.id = ?
        ''', (voice_post_id,)).fetchone()
        conn.close()
        return dict(post) if post else None

    def create(self, user_id, title, content, category='General'):
        """Create a new voice post. Returns the created post as a dict."""
        conn = self._get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO voice_posts (user_id, title, content, category) VALUES (?, ?, ?, ?)',
                (user_id, title, content, category)
            )
            conn.commit()
            post_id = cursor.lastrowid
            post = conn.execute('''
                SELECT vp.*, u.username as author_name, u.role as author_role, 0 as comment_count
                FROM voice_posts vp
                JOIN users u ON vp.user_id = u.id
                WHERE vp.id = ?
            ''', (post_id,)).fetchone()
            return dict(post) if post else None
        finally:
            conn.close()

    def update_status(self, voice_post_id, status):
        """Update the status of a voice post (open/resolved/closed)."""
        conn = self._get_db()
        try:
            conn.execute(
                'UPDATE voice_posts SET status = ? WHERE id = ?',
                (status, voice_post_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def delete(self, voice_post_id, user_id):
        """Delete a voice post. Only the author can delete."""
        conn = self._get_db()
        try:
            conn.execute(
                'DELETE FROM voice_posts WHERE id = ? AND user_id = ?',
                (voice_post_id, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_categories(self):
        """Get distinct categories used in voice posts."""
        conn = self._get_db()
        cats = conn.execute(
            'SELECT DISTINCT category FROM voice_posts ORDER BY category'
        ).fetchall()
        conn.close()
        return [c['category'] for c in cats]

    # -- voice comments --------------------------------------------------

    def get_comments(self, voice_post_id):
        """Fetch all comments for a voice post with author info."""
        conn = self._get_db()
        comments = conn.execute('''
            SELECT vc.*, u.username as author_name, u.role as author_role
            FROM voice_comments vc
            JOIN users u ON vc.user_id = u.id
            WHERE vc.voice_post_id = ?
            ORDER BY vc.created_at ASC
        ''', (voice_post_id,)).fetchall()
        conn.close()
        return [dict(c) for c in comments]

    def add_comment(self, voice_post_id, user_id, content, is_official=False):
        """Add a comment to a voice post. Returns the new comment as a dict."""
        conn = self._get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO voice_comments (voice_post_id, user_id, content, is_official) VALUES (?, ?, ?, ?)',
                (voice_post_id, user_id, content, 1 if is_official else 0)
            )
            conn.commit()
            comment_id = cursor.lastrowid
            comment = conn.execute('''
                SELECT vc.*, u.username as author_name, u.role as author_role
                FROM voice_comments vc
                JOIN users u ON vc.user_id = u.id
                WHERE vc.id = ?
            ''', (comment_id,)).fetchone()
            return dict(comment) if comment else None
        finally:
            conn.close()

    # -- voice votes -----------------------------------------------------

    def get_user_vote(self, voice_post_id, user_id):
        """Get the vote type a user cast on a voice post, or None."""
        conn = self._get_db()
        vote = conn.execute(
            'SELECT vote_type FROM voice_votes WHERE voice_post_id = ? AND user_id = ?',
            (voice_post_id, user_id)
        ).fetchone()
        conn.close()
        return vote['vote_type'] if vote else None

    def toggle_vote(self, voice_post_id, user_id, vote_type):
        """
        Toggle a vote on a voice post:
          - same vote_type → remove (returns 'removed')
          - different     → update (returns 'changed')
          - none          → add    (returns 'added')
        Returns (action, net_change) where net_change is the delta to apply to vote_count.
        """
        conn = self._get_db()
        try:
            existing = conn.execute(
                'SELECT id, vote_type FROM voice_votes WHERE voice_post_id = ? AND user_id = ?',
                (voice_post_id, user_id)
            ).fetchone()

            if existing:
                if existing['vote_type'] == vote_type:
                    # Remove vote
                    conn.execute('DELETE FROM voice_votes WHERE id = ?', (existing['id'],))
                    delta = -1 if vote_type == 'up' else 1
                    conn.execute(
                        'UPDATE voice_posts SET vote_count = vote_count + ? WHERE id = ?',
                        (delta, voice_post_id)
                    )
                    conn.commit()
                    return 'removed', delta
                else:
                    # Change vote
                    conn.execute(
                        'UPDATE voice_votes SET vote_type = ? WHERE id = ?',
                        (vote_type, existing['id'])
                    )
                    delta = 2 if vote_type == 'up' else -2
                    conn.execute(
                        'UPDATE voice_posts SET vote_count = vote_count + ? WHERE id = ?',
                        (delta, voice_post_id)
                    )
                    conn.commit()
                    return 'changed', delta
            else:
                # Add vote
                conn.execute(
                    'INSERT INTO voice_votes (voice_post_id, user_id, vote_type) VALUES (?, ?, ?)',
                    (voice_post_id, user_id, vote_type)
                )
                delta = 1 if vote_type == 'up' else -1
                conn.execute(
                    'UPDATE voice_posts SET vote_count = vote_count + ? WHERE id = ?',
                    (delta, voice_post_id)
                )
                conn.commit()
                return 'added', delta
        finally:
            conn.close()
