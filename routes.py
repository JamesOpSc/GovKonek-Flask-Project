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
    Returns a dict with keys: auth, posts, post_repo, project_repo, service_repo, document_repo, voice, voice_repo.
    """
    ext = current_app.extensions
    return {
        'auth': ext['auth_service'],
        'posts': ext['post_service'],
        'post_repo': ext['post_repo'],
        'user_repo': ext['user_repo'],
        'project_repo': ext['project_repo'],
        'project_service': ext['project_service'],
        'service_repo': ext['service_repo'],
        'document_repo': ext['document_repo'],
        'document_service': ext['document_service'],
        'voice': ext['voice_service'],
        'voice_repo': ext['voice_repo'],
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
        svc = _get_services()
        user_data = svc['user_repo'].find_by_id(current_user.id)
        profile_pic = user_data['profile_picture'] if user_data else ''
        return render_template('dashboard.html',
                               name=current_user.username,
                               role=current_user.role,
                               profile_picture=profile_pic)

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
        """API: Get published posts with optional search, category filter, and sort."""
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        sort = request.args.get('sort', 'newest')
        svc = _get_services()
        posts = svc['posts'].get_feed(search=search, category=category, sort=sort)
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
        """
        API: Create a new post. ONLY publisher (barangay captain) can create.

        Accepts multipart/form-data (for image upload) or JSON.
        Fields: title, content, category, image (optional file upload)
        """
        # Check if multipart or JSON
        if request.content_type and 'multipart' in request.content_type:
            title = request.form.get('title', '')
            content = request.form.get('content', '')
            category = request.form.get('category', 'Announcement')
        else:
            data = request.get_json()
            title = data.get('title', '') if data else ''
            content = data.get('content', '') if data else ''
            category = data.get('category', 'Announcement') if data else 'Announcement'

        # Handle image upload
        image_path = ''
        uploaded_image = request.files.get('image') if request.files else None
        if uploaded_image and uploaded_image.filename:
            import os
            from datetime import datetime
            upload_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads'
            )
            os.makedirs(upload_dir, exist_ok=True)
            ext = uploaded_image.filename.rsplit('.', 1)[-1].lower()
            safe_name = f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            filepath = os.path.join(upload_dir, safe_name)
            uploaded_image.save(filepath)
            image_path = f'/static/uploads/{safe_name}'

        svc = _get_services()
        post, error = svc['posts'].create_post(current_user, title, content, category, image_path)
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
                               role=current_user.role,
                               user_id=current_user.id)

    @app.route('/services')
    @login_required
    def e_services():
        """E-Services page — services are hardcoded in the template."""
        return render_template('services.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/services/<service_name>')
    @login_required
    def service_detail(service_name):
        """
        Placeholder for individual e-service pages.

        Prevents 404 errors when users click service cards.
        Real service implementations can override this route later.
        """
        # Convert slug back to readable name
        readable = service_name.replace('-', ' ').title()
        return render_template('service_placeholder.html',
                               service_name=readable,
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/documents')
    @login_required
    def documents():
        """Transparency Documents page."""
        return render_template('documents.html',
                               name=current_user.username,
                               role=current_user.role)

    @app.route('/post/<int:post_id>')
    @login_required
    def post_detail(post_id):
        """
        Individual post view — the "clickable post" from the Backend Guide.

        Renders a full post with comments, reactions, and a "Discuss" / grievance
        link for citizens to engage constructively with barangay announcements.
        """
        svc = _get_services()
        detail = svc['posts'].get_post_detail(post_id, current_user.id)
        if not detail:
            flash('Post not found.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('post_detail.html',
                               post=detail,
                               name=current_user.username,
                               role=current_user.role,
                               user_id=current_user.id)

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

    @app.route('/api/projects/<int:project_id>')
    @login_required
    def api_get_project(project_id):
        """API: Get a single project by ID."""
        repo = _get_services()['project_repo']
        project = repo.get_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify({'project': project})

    @app.route('/api/projects', methods=['POST'])
    @login_required
    def api_create_project():
        """API: Create a new project. ONLY publisher (barangay captain) can create."""
        data = request.get_json()
        title = data.get('title', '') if data else ''
        description = data.get('description', '') if data else ''
        status = data.get('status', 'ongoing') if data else 'ongoing'
        budget = data.get('budget', 0) if data else 0
        location = data.get('location', '') if data else ''
        image_url = data.get('image_url', '') if data else ''
        start_date = data.get('start_date', '') if data else ''
        end_date = data.get('end_date', '') if data else ''
        svc = _get_services()
        project, error = svc['project_service'].create_project(
            current_user, title, description, status,
            budget, location, image_url, start_date, end_date
        )
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'project': project}), 201

    @app.route('/api/projects/<int:project_id>', methods=['PUT'])
    @login_required
    def api_update_project(project_id):
        """API: Update a project. ONLY the publisher who created it can edit."""
        data = request.get_json()
        title = data.get('title', '') if data else ''
        description = data.get('description', '') if data else ''
        status = data.get('status', 'ongoing') if data else 'ongoing'
        budget = data.get('budget', 0) if data else 0
        location = data.get('location', '') if data else ''
        image_url = data.get('image_url', '') if data else ''
        start_date = data.get('start_date', '') if data else ''
        end_date = data.get('end_date', '') if data else ''
        svc = _get_services()
        project, error = svc['project_service'].update_project(
            current_user, project_id, title, description, status,
            budget, location, image_url, start_date, end_date
        )
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'project': project})

    @app.route('/api/projects/<int:project_id>', methods=['DELETE'])
    @login_required
    def api_delete_project(project_id):
        """API: Delete a project. ONLY the publisher who created it can delete."""
        svc = _get_services()
        success, error = svc['project_service'].delete_project(current_user, project_id)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'success': True})

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

    # ================================================================
    # USER PROFILE API
    # ================================================================

    @app.route('/api/profile', methods=['GET', 'POST'])
    @login_required
    def api_profile():
        """
        API: Get or update the current user's profile.

        GET  → returns { profile: { email, address, phone_number, profile_picture } }
        POST → updates profile with multipart/form-data (supports profile_picture upload)
        """
        user_repo = _get_services()['user_repo']

        if request.method == 'GET':
            user_data = user_repo.find_by_id(current_user.id)
            if not user_data:
                return jsonify({'error': 'User not found'}), 404
            return jsonify({'profile': {
                'email': user_data['email'] or '',
                'address': user_data['address'] or '',
                'phone_number': user_data['phone_number'] or '',
                'profile_picture': user_data['profile_picture'] or '',
            }})

        # POST — update profile
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        profile_picture_path = ''

        # Handle profile picture upload
        uploaded_file = request.files.get('profile_picture')
        if uploaded_file and uploaded_file.filename:
            import os
            from datetime import datetime
            upload_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads'
            )
            os.makedirs(upload_dir, exist_ok=True)
            ext = uploaded_file.filename.rsplit('.', 1)[-1].lower()
            safe_name = f"profile_{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            filepath = os.path.join(upload_dir, safe_name)
            uploaded_file.save(filepath)
            profile_picture_path = f'/static/uploads/{safe_name}'

        user_repo.update_profile(
            current_user.id,
            email=email,
            address=address,
            phone_number=phone_number,
            profile_picture=profile_picture_path
        )
        return jsonify({'success': True, 'message': 'Profile updated!'})

    @app.route('/api/documents', methods=['POST'])
    @login_required
    def api_create_document():
        """
        API: Upload a new transparency document. ONLY publisher can upload.

        Expects multipart/form-data with:
          - title (str)
          - description (str)
          - category (str)
          - published_date (str, optional)
          - file (file upload)
        """
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        category = request.form.get('category', 'General')
        published_date = request.form.get('published_date', '')
        uploaded_file = request.files.get('file')

        svc = _get_services()
        doc, error = svc['document_service'].create_document(
            current_user, title, description, category, uploaded_file, published_date
        )
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'document': doc}), 201

    @app.route('/api/documents/<int:document_id>', methods=['DELETE'])
    @login_required
    def api_delete_document(document_id):
        """API: Delete a transparency document. ONLY publisher can delete."""
        svc = _get_services()
        success, error = svc['document_service'].delete_document(current_user, document_id)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'success': True})

    # ================================================================
    # LIVE WEATHER API
    # ================================================================

    @app.route('/api/weather')
    @login_required
    def api_get_weather():
        """
        API: Get live weather data for given coordinates using Open-Meteo.
        Query params: lat (float), lon (float)
        Returns: temperature, weather code, humidity, wind speed, and forecast.
        """
        import requests

        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)

        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon query parameters are required'}), 400

        try:
            # Open-Meteo API (free, no API key required)
            weather_url = (
                'https://api.open-meteo.com/v1/forecast'
                f'?latitude={lat}&longitude={lon}'
                '&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m'
                '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
                '&timezone=auto'
            )
            resp = requests.get(weather_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            current = data.get('current', {})
            daily = data.get('daily', {})

            return jsonify({
                'location': {
                    'lat': lat,
                    'lon': lon,
                },
                'current': {
                    'temperature': current.get('temperature_2m'),
                    'humidity': current.get('relative_humidity_2m'),
                    'wind_speed': current.get('wind_speed_10m'),
                    'weather_code': current.get('weather_code'),
                },
                'daily': {
                    'time': daily.get('time', []),
                    'weather_code': daily.get('weather_code', []),
                    'temp_max': daily.get('temperature_2m_max', []),
                    'temp_min': daily.get('temperature_2m_min', []),
                    'precip_prob': daily.get('precipitation_probability_max', []),
                },
            })
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Weather service unavailable: {str(e)}'}), 502

    # ================================================================
    # CITIZENS' VOICE — Community Forum
    # ================================================================

    @app.route('/citizens-voice')
    @login_required
    def citizens_voice():
        """Citizens' Voice community forum page."""
        return render_template('citizens_voice.html',
                               name=current_user.username,
                               role=current_user.role,
                               user_id=current_user.id)

    # -- Voice Posts API ------------------------------------------------

    @app.route('/api/voice')
    @login_required
    def api_get_voice_posts():
        """
        API: Get all voice posts, optionally filtered and sorted.

        Query params:
          - search:   Search in BOTH post titles AND author usernames (case-insensitive)
          - sort:     Sort order — 'newest' (default), 'oldest', 'most_voted', 'most_commented'
          - category: Filter by category (Grievance, Suggestion, etc.)
          - status:   Filter by status (open, resolved, closed)
        """
        category = request.args.get('category')
        status = request.args.get('status')
        search = request.args.get('search')
        sort = request.args.get('sort', 'newest')
        svc = _get_services()
        posts = svc['voice'].get_posts(category=category, status=status,
                                        search=search, sort=sort)
        return jsonify({'posts': posts})

    @app.route('/api/voice/<int:post_id>')
    @login_required
    def api_get_voice_post(post_id):
        """API: Get a single voice post with comments and user's vote."""
        svc = _get_services()
        detail = svc['voice'].get_post_detail(post_id, current_user.id)
        if not detail:
            return jsonify({'error': 'Post not found'}), 404
        return jsonify(detail)

    @app.route('/api/voice', methods=['POST'])
    @login_required
    def api_create_voice_post():
        """API: Create a new voice post. Any authenticated user can post."""
        data = request.get_json()
        title = data.get('title', '') if data else ''
        content = data.get('content', '') if data else ''
        category = data.get('category', 'General') if data else 'General'
        svc = _get_services()
        post, error = svc['voice'].create_post(current_user.id, title, content, category)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'post': post}), 201

    @app.route('/api/voice/<int:post_id>/status', methods=['PUT'])
    @login_required
    def api_update_voice_status(post_id):
        """API: Update a voice post's status (open/resolved/closed)."""
        data = request.get_json()
        status = data.get('status', '') if data else ''
        svc = _get_services()
        success, error = svc['voice'].update_status(post_id, status)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'success': True})

    @app.route('/api/voice/<int:post_id>', methods=['DELETE'])
    @login_required
    def api_delete_voice_post(post_id):
        """API: Delete a voice post. Only the author can delete."""
        svc = _get_services()
        success, error = svc['voice'].delete_post(post_id, current_user.id)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'success': True})

    # -- Voice Comments API --------------------------------------------

    @app.route('/api/voice/<int:post_id>/comments', methods=['POST'])
    @login_required
    def api_add_voice_comment(post_id):
        """API: Add a comment to a voice post."""
        data = request.get_json()
        content = data.get('content', '') if data else ''
        svc = _get_services()
        comment, error = svc['voice'].add_comment(post_id, current_user.id, content, current_user.role)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'comment': comment}), 201

    # -- Voice Votes API -----------------------------------------------

    @app.route('/api/voice/<int:post_id>/vote', methods=['POST'])
    @login_required
    def api_toggle_voice_vote(post_id):
        """API: Toggle up/down vote on a voice post."""
        data = request.get_json()
        vote_type = data.get('vote_type', '') if data else ''
        svc = _get_services()
        result, error = svc['voice'].toggle_vote(post_id, current_user.id, vote_type)
        if error:
            return jsonify({'error': error}), 400
        return jsonify(result)
