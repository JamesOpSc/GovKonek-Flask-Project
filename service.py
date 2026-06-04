"""
GovKonek Service Module

Service Layer - ABSTRACTION PRINCIPLE
Purpose: Service layer orchestrates business logic without being tied to Flask.
Benefits: Easy to test, easy to reuse in different contexts (CLI, API, etc.)
Keeps routes thin and focused on HTTP handling.

REFACTORED for testability:
    - Services accept repository instances via constructor (dependency injection).
    - In tests, inject mock repositories to isolate business logic from the database.
    - Static methods kept as backward-compatible wrappers around a default instance.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from repository import UserRepository, PostRepository
from models import create_user_from_db


# ===========================================================================
# AuthService
# ===========================================================================

class AuthService:
    """
    Authentication and authorization business logic.

    REFACTORED: Now instance-based. Pass a UserRepository to the constructor.
    For testing, inject a mock or an in-memory repository.
    """

    def __init__(self, user_repo=None):
        """
        @param user_repo: UserRepository instance.
                          Defaults to a new UserRepository() if not provided.
        """
        self._user_repo = user_repo or UserRepository()

    # -- public API -------------------------------------------------------

    def register_user(self, username, password, role):
        """Register a new user. Returns (success: bool, message: str)."""
        if not username or not password or not role:
            return False, "All fields are required"

        if self._user_repo.find_by_username(username):
            return False, "Username already exists. Try another one."

        hashed_password = generate_password_hash(password)
        if self._user_repo.create(username, hashed_password, role):
            return True, "Registration successful! Please log in."
        return False, "Registration failed"

    def authenticate_user(self, username, password):
        """Authenticate a user. Returns (success: bool, user: User or None)."""
        user_data = self._user_repo.find_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = create_user_from_db(user_data)
            return True, user
        return False, None

    # AuthService: no static wrappers needed — routes use injected instances.
    # If external code needs a default instance, create one:
    #     from repository import UserRepository
    #     auth = AuthService(UserRepository())


# ===========================================================================
# PostService
# ===========================================================================

class PostService:
    """
    Post, comment, and reaction business logic.

    REFACTORED: Now instance-based. Pass a PostRepository to the constructor.
    For testing, inject a mock repository.
    """

    ALLOWED_EMOJI = {'👍', '❤️', '😄', '😢', '😡', '🎉'}

    def __init__(self, post_repo=None):
        """
        @param post_repo: PostRepository instance.
                          Defaults to a new PostRepository() if not provided.
        """
        self._post_repo = post_repo or PostRepository()

    # -- feed / detail ----------------------------------------------------

    def get_feed(self, search=None, category=None, sort=None):
        """Get published posts with optional search, category filter, and sorting."""
        posts = self._post_repo.get_all_posts(search=search, category=category, sort=sort)
        return [dict(p) for p in posts]

    def get_post_detail(self, post_id, user_id=None):
        """Get a single post with comments, reaction counts, and user's reaction."""
        post = self._post_repo.get_post_by_id(post_id)
        if not post:
            return None

        return {
            'post': dict(post),
            'comments': [dict(c) for c in self._post_repo.get_comments_for_post(post_id)],
            'reaction_counts': [dict(r) for r in self._post_repo.get_reactions_for_post(post_id)],
            'user_reaction': self._post_repo.get_user_reaction(post_id, user_id) if user_id else None,
        }

    # -- comments ---------------------------------------------------------

    def add_comment(self, post_id, user_id, content):
        """Add a comment. Returns (comment_dict, error)."""
        if not content or not content.strip():
            return None, "Comment cannot be empty."
        comment = self._post_repo.add_comment(post_id, user_id, content.strip())
        return dict(comment), None

    # -- reactions --------------------------------------------------------

    def toggle_reaction(self, post_id, user_id, emoji):
        """Toggle a reaction. Returns (result_dict, error)."""
        if emoji not in self.ALLOWED_EMOJI:
            return None, "Invalid emoji."

        action, _ = self._post_repo.toggle_reaction(post_id, user_id, emoji)
        reaction_counts = [dict(r) for r in self._post_repo.get_reactions_for_post(post_id)]
        user_reaction = self._post_repo.get_user_reaction(post_id, user_id)

        return {
            'action': action,
            'reaction_counts': reaction_counts,
            'user_reaction': user_reaction,
        }, None

    # -- publisher-only post management -----------------------------------

    def create_post(self, user, title, content, category='Announcement'):
        """
        Create a new post. ONLY publisher (barangay captain) can publish.
        Returns (post_dict, error).
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can publish announcements."
        if not title or not title.strip():
            return None, "Title is required."
        if not content or not content.strip():
            return None, "Content is required."

        # Validate category
        valid_categories = ['Announcement', 'Emergency', 'Health', 'Project']
        if category not in valid_categories:
            category = 'Announcement'

        post = self._post_repo.create_post(user.id, title.strip(), content.strip(), category)
        return (post, None) if post else (None, "Failed to create post.")

    def update_post(self, user, post_id, title, content):
        """
        Update a post. ONLY the publisher who created it can edit.
        Returns (post_dict, error).
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can edit announcements."
        if not title or not title.strip():
            return None, "Title is required."
        if not content or not content.strip():
            return None, "Content is required."

        post = self._post_repo.update_post(post_id, user.id, title.strip(), content.strip())
        return (post, None) if post else (None, "Post not found or you are not authorized to edit it.")

    def delete_post(self, user, post_id):
        """
        Delete a post. ONLY the publisher who created it can delete.
        Returns (success: bool, error).
        """
        if not user.can_publish():
            return False, "Only the Barangay Captain can delete announcements."
        self._post_repo.delete_post(post_id, user.id)
        return True, None

    # PostService: no static wrappers needed — routes use injected instances.


# ===========================================================================
# VoiceService — Citizens' Voice forum business logic
# ===========================================================================

class VoiceService:
    """
    Business logic for the Citizens' Voice forum.

    Any authenticated user can post topics, comment, and vote.
    Publisher (barangay captain) comments are flagged as official responses.
    """

    CATEGORIES = ['General', 'Grievance', 'Suggestion', 'Question', 'Announcement']
    VALID_STATUSES = {'open', 'resolved', 'closed'}

    def __init__(self, voice_repo=None):
        """
        @param voice_repo: VoiceRepository instance.
        """
        from repository import VoiceRepository
        self._repo = voice_repo or VoiceRepository()

    # -- voice posts -----------------------------------------------------

    def get_posts(self, category=None, status=None):
        """Get all voice posts, optionally filtered."""
        return self._repo.get_all(category=category, status=status)

    def get_post_detail(self, voice_post_id, user_id=None):
        """Get a voice post with comments and user's vote."""
        post = self._repo.get_by_id(voice_post_id)
        if not post:
            return None
        return {
            'post': post,
            'comments': self._repo.get_comments(voice_post_id),
            'user_vote': self._repo.get_user_vote(voice_post_id, user_id) if user_id else None,
        }

    def create_post(self, user_id, title, content, category='General'):
        """Create a new voice post. Returns (post_dict, error)."""
        if not title or not title.strip():
            return None, "Title is required."
        if not content or not content.strip():
            return None, "Content is required."
        if category not in self.CATEGORIES:
            category = 'General'
        post = self._repo.create(user_id, title.strip(), content.strip(), category)
        return (post, None) if post else (None, "Failed to create post.")

    def update_status(self, voice_post_id, status):
        """Update a voice post's status. Returns (success, error)."""
        if status not in self.VALID_STATUSES:
            return False, f"Invalid status. Must be one of: {', '.join(self.VALID_STATUSES)}"
        self._repo.update_status(voice_post_id, status)
        return True, None

    def delete_post(self, voice_post_id, user_id):
        """Delete a voice post. Only the original author can delete. Returns (success, error)."""
        self._repo.delete(voice_post_id, user_id)
        return True, None

    # -- comments --------------------------------------------------------

    def add_comment(self, voice_post_id, user_id, content, role):
        """Add a comment. Publisher comments are marked official. Returns (comment_dict, error)."""
        if not content or not content.strip():
            return None, "Comment cannot be empty."
        is_official = (role == 'publisher')
        comment = self._repo.add_comment(voice_post_id, user_id, content.strip(), is_official)
        return (comment, None) if comment else (None, "Failed to add comment.")

    # -- votes -----------------------------------------------------------

    def toggle_vote(self, voice_post_id, user_id, vote_type):
        """Toggle up/down vote. Returns (result_dict, error)."""
        if vote_type not in ('up', 'down'):
            return None, "Vote must be 'up' or 'down'."
        action, delta = self._repo.toggle_vote(voice_post_id, user_id, vote_type)
        user_vote = self._repo.get_user_vote(voice_post_id, user_id)
        return {
            'action': action,
            'net_change': delta,
            'user_vote': user_vote,
        }, None

    def get_categories(self):
        """Return the list of valid categories."""
        return self.CATEGORIES
