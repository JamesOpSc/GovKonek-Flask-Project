"""
GovKonek Routes Module

Flask routes for user authentication and dashboard access.
This module handles HTTP requests and responses, delegating business logic to services.
Demonstrates the thin route principle - routes are simple and focused on HTTP concerns.

REFACTORED for testability:
    - Routes access services via current_app.extensions (dependency injection).
    - No direct imports of concrete AuthService / PostService.
    - In tests, inject mock services into app.extensions before calling routes.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, login_user, logout_user, current_user


def _get_services():
    """
    Convenience helper: fetch injected services from the Flask app.
    Returns a dict with keys: auth, posts, post_repo, project_repo, service_repo, document_repo.
    """
    ext = current_app.extensions
    return {
        'auth': ext['auth_service'],
        'posts': ext['post_service'],
        'post_repo': ext['post_repo'],
        'project_repo': ext['project_repo'],
        'service_repo': ext['service_repo'],
        'document_repo': ext['document_repo'],
    }


def create_routes(app):
    """
    Factory function to register all routes with the Flask app.

    This approach allows routes to be separated from app initialization,
    making the code more modular and testable.

    @param app: Flask application instance
    """

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Registration page and form handler."""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']

            svc = _get_services()
            success, message = svc['auth'].register_user(username, password, role)

            if success:
                flash(message, 'success')
                return redirect(url_for('login'))
            else:
                flash(message, 'error')

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login page and form handler."""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            svc = _get_services()
            success, user = svc['auth'].authenticate_user(username, password)

            if success:
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')

        return render_template('login.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard page - accessible only to authenticated users."""
        return render_template('dashboard.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/profile')
    @login_required
    def profile():
        """User profile page."""
        return render_template('profile.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/logout')
    @login_required
    def logout():
        """Logout handler."""
        logout_user()
        return redirect(url_for('login'))

    # ================================================================
    # POST, COMMENT, AND REACTION API ROUTES
    # ================================================================

    @app.route('/api/posts')
    @login_required
    def api_get_posts():
        """API: Get all published posts for the feed."""
        svc = _get_services()
        posts = svc['posts'].get_feed()
        return jsonify({'posts': posts})

    @app.route('/api/posts/<int:post_id>')
    @login_required
    def api_get_post_detail(post_id):
        """API: Get a single post with comments and reactions."""
        svc = _get_services()
        detail = svc['posts'].get_post_detail(post_id, current_user.id)
        if not detail:
            return jsonify({'error': 'Post not found'}), 404
        return jsonify(detail)

    @app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
    @login_required
    def api_add_comment(post_id):
        """API: Add a comment to a post."""
        data = request.get_json()
        content = data.get('content', '') if data else ''
        svc = _get_services()
        comment, error = svc['posts'].add_comment(post_id, current_user.id, content)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'comment': comment})

    @app.route('/api/posts/<int:post_id>/react', methods=['POST'])
    @login_required
    def api_toggle_reaction(post_id):
        """API: Toggle an emoji reaction on a post."""
        data = request.get_json()
        emoji = data.get('emoji', '') if data else ''
        svc = _get_services()
        result, error = svc['posts'].toggle_reaction(post_id, current_user.id, emoji)
        if error:
            return jsonify({'error': error}), 400
        return jsonify(result)

    @app.route('/api/posts/<int:post_id>/comments')
    @login_required
    def api_get_comments(post_id):
        """API: Get comments for a post."""
        svc = _get_services()
        comments = [dict(c) for c in svc['post_repo'].get_comments_for_post(post_id)]
        return jsonify({'comments': comments})

    # ================================================================
    # PUBLISHER-ONLY POST MANAGEMENT ROUTES
    # ================================================================

    @app.route('/api/posts', methods=['POST'])
    @login_required
    def api_create_post():
        """API: Create a new post. ONLY publisher (barangay captain) can create."""
        data = request.get_json()
        title = data.get('title', '') if data else ''
        content = data.get('content', '') if data else ''
        svc = _get_services()
        post, error = svc['posts'].create_post(current_user, title, content)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'post': post}), 201

    @app.route('/api/posts/<int:post_id>', methods=['PUT'])
    @login_required
    def api_update_post(post_id):
        """API: Update a post. ONLY the publisher who created it can edit."""
        data = request.get_json()
        title = data.get('title', '') if data else ''
        content = data.get('content', '') if data else ''
        svc = _get_services()
        post, error = svc['posts'].update_post(current_user, post_id, title, content)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'post': post})

    @app.route('/api/posts/<int:post_id>', methods=['DELETE'])
    @login_required
    def api_delete_post(post_id):
        """API: Delete a post. ONLY the publisher who created it can delete."""
        svc = _get_services()
        success, error = svc['posts'].delete_post(current_user, post_id)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'success': True})

    @app.route('/')
    def home():
        """Home page - redirects to login page."""
        return redirect(url_for('login'))

    # ================================================================
    # FEATURE PAGES
    # ================================================================

    @app.route('/barangay-map')
    @login_required
    def barangay_map():
        """Interactive Barangay Map page."""
        return render_template('barangay_map.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/projects')
    @login_required
    def projects():
        """Barangay Projects page."""
        return render_template('projects.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/services')
    @login_required
    def e_services():
        """E-Services page."""
        return render_template('services.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/documents')
    @login_required
    def documents():
        """Transparency Documents page."""
        return render_template('documents.html',
                               name=current_user.username,
                               role=current_user.role)

    # ================================================================
    # FEATURE DATA APIs
    # ================================================================

    @app.route('/api/projects')
    @login_required
    def api_get_projects():
        """API: Get all barangay projects."""
        repo = _get_services()['project_repo']
        projects = repo.get_all()
        return jsonify({'projects': projects})

    @app.route('/api/services')
    @login_required
    def api_get_services():
        """API: Get all e-services."""
        repo = _get_services()['service_repo']
        services = repo.get_all()
        return jsonify({'services': services})

    @app.route('/api/documents')
    @login_required
    def api_get_documents():
        """API: Get all transparency documents."""
        repo = _get_services()['document_repo']
        documents = repo.get_all()
        return jsonify({'documents': documents})
