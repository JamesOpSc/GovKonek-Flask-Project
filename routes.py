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

import sqlite3

import requests
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, login_user, logout_user, current_user
from exceptions import DatabaseError
from file_upload import get_upload_helper


def _get_services():
    """
    Convenience helper: fetch injected services and repositories from the
    Flask app. Returns a dict keyed by: auth, posts, post_repo, user_repo,
    project_repo, project_service, service_repo, document_repo,
    document_service, voice, voice_repo, barangay_repo, barangay_service.
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
        'barangay_repo': ext['barangay_repo'],
        'barangay_service': ext['barangay_service'],
    }


def _barangay_display_name(barangay):
    """
    Return a barangay's name without a leading 'Barangay ' prefix so that
    templates can render 'Barangay <Name>' without doubling the word.
    """
    name = (barangay or {}).get('name') or 'Barangay'
    return name[9:] if name.lower().startswith('barangay ') else name


def _project_payload(data):
    """
    Extract the shared project fields from a JSON payload.

    DRY: both api_create_project and api_update_project read the same
    fields, so the extraction lives in one place (thin-route principle).
    """
    data = data or {}
    return {
        'title': data.get('title', ''),
        'description': data.get('description', ''),
        'status': data.get('status', 'ongoing'),
        'budget': data.get('budget', 0),
        'location': data.get('location', ''),
        'image_url': data.get('image_url', ''),
        'start_date': data.get('start_date', ''),
        'end_date': data.get('end_date', ''),
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
        """
        Registration page and form handler.

        GET  → renders the registration form
        POST → validates form data, creates user, redirects to login

        The user's selected barangay is saved on the account so the app
        can resolve their barangay dynamically (e.g. /barangay/view/<slug>)
        instead of falling back to a hardcoded default.
        """
        svc = _get_services()
        # Dynamic barangay dropdown — real barangays from the DB when available.
        # Gracefully degrade if the barangays table is missing (e.g. minimal DBs).
        barangays = []
        try:
            all_barangays = svc['barangay_repo'].get_all()
            barangays = [b for b in all_barangays if b.get('publisher_id') is not None]
        except (DatabaseError, sqlite3.Error):
            # Gracefully degrade if the barangays table is missing (e.g. minimal DBs)
            barangays = []

        if request.method == 'POST':
            # Extract form fields
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            barangay = request.form.get('barangay', '')

            # Delegate to AuthService for validation and user creation
            success, message = svc['auth'].register_user(username, password, role, barangay)

            if success:
                flash(message, 'success')
                return redirect(url_for('login'))
            else:
                flash(message, 'error')

        return render_template('register.html', barangays=barangays)
    
    @app.route('/barangay/my-hub')
    @login_required
    def my_barangay_hub():
        """
        Resolves the logged-in user's barangay dynamically and redirects to
        its landing page (/barangay/view/<slug>).

        Resolution order:
          1. Publisher → their own barangay record (barangays.publisher_id)
          2. The barangay chosen at registration (users.barangay)
          3. Fallback: the first barangay in the database
        """
        svc = _get_services()

        barangay = None
        if current_user.role == 'publisher':
            barangay = svc['barangay_repo'].get_by_publisher(current_user.id)

        name = (barangay or {}).get('name') if barangay else ''
        if not name:
            name = getattr(current_user, 'barangay', '') or ''
        if not name:
            first = svc['barangay_repo'].get_first()
            name = (first or {}).get('name') or 'Payatas'

        slug = name.lower().replace(' ', '-')
        return redirect(f'/barangay/view/{slug}')


    @app.route('/barangay/view/<barangay_slug>')
    @login_required
    def barangay_hub(barangay_slug):
        """
        Renders a barangay's landing page from its name slug.

        The slug is derived from the real barangay name (e.g. 'Barangay
        Bagong Silangan' -> 'barangay-bagong-silangan'), so we resolve it
        against the barangays table instead of hardcoding any location.
        """
        svc = _get_services()

        def _slugify(name):
            return (name or '').lower().replace(' ', '-').replace(',', '')

        target = _slugify(barangay_slug)

        # Resolve the slug against real barangay records
        barangay = None
        for b in svc['barangay_repo'].get_all():
            if _slugify(b.get('name')) == target:
                barangay = b
                break
        if not barangay:
            barangay = svc['barangay_repo'].get_first()

        # Announcements published by this barangay's captain
        announcements = []
        if barangay and barangay.get('publisher_id'):
            posts = svc['post_repo'].get_posts_by_publisher(barangay['publisher_id'])
            announcements = [dict(p) for p in posts]

        projects = svc['project_repo'].get_all()

        return render_template(
            'barangay_landing.html',
            barangay_name=_barangay_display_name(barangay),
            barangay=barangay,
            details=barangay,
            announcements=announcements,
            projects=projects,
            is_owner=False,
            name=current_user.username,
            role=current_user.role,
        )

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
        Login page and form handler.

        GET  → renders the login form
        POST → authenticates credentials, redirects to the dashboard
        """
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            svc = _get_services()
            success, user = svc['auth'].authenticate_user(username, password)

            if success:
                # Flask-Login: create session for authenticated user
                login_user(user)

                # Both publishers and citizens land on the dashboard
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')

        return render_template('login.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """
        Dashboard page — the main feed view after login.

        Loads the current user's profile data and checks if a publisher
        has already created their barangay page (used for onboarding prompts).
        """
        svc = _get_services()

        # Fetch user profile data (email, address, profile picture, etc.)
        user_data = svc['user_repo'].find_by_id(current_user.id)
        profile_pic = user_data['profile_picture'] if user_data else ''

        # For publishers: check if they've set up their barangay page yet
        barangay = None
        has_barangay = False
        if current_user.role == 'publisher':
            barangay = svc['barangay_repo'].get_by_publisher(current_user.id)
            has_barangay = barangay is not None

        return render_template('dashboard.html',
                               name=current_user.username,
                               role=current_user.role,
                               profile_picture=profile_pic,
                               barangay=barangay,
                               has_barangay=has_barangay)

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

        # Handle image upload using centralized FileUploadHelper (OOP Abstraction)
        image_path = ''
        uploaded_image = request.files.get('image') if request.files else None
        if uploaded_image and uploaded_image.filename:
            try:
                image_path = get_upload_helper().save(uploaded_image, prefix='post')
            except ValueError:
                pass  # Invalid file type — silently skip image

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

    @app.route('/barangay-landing')
    @login_required
    def barangay_landing():
        """
        Barangay Hall landing page — dynamically pulls data from the barangays table.

        If a publisher is logged in, shows THEIR barangay.
        Otherwise, shows the first/default barangay.
        """
        svc = _get_services()

        # If the current user is a publisher, try to show their barangay
        barangay = None
        is_owner = False
        if current_user.role == 'publisher':
            barangay = svc['barangay_repo'].get_by_publisher(current_user.id)
            if barangay:
                is_owner = True

        # Fall back to the default/first barangay
        if not barangay:
            barangay = svc['barangay_repo'].get_first()

        # Fetch barangay stats for the landing page
        projects = svc['project_repo'].get_all()
        announcements = svc['posts'].get_feed(category='Announcement', sort='newest')

        return render_template('barangay_landing.html',
                               name=current_user.username,
                               role=current_user.role,
                               barangay=barangay,
                               barangay_name=_barangay_display_name(barangay),
                               is_owner=is_owner,
                               projects=projects,
                               announcements=announcements)

    @app.route('/barangay/<int:barangay_id>/landing')
    @login_required
    def barangay_landing_by_id(barangay_id):
        """View a specific barangay's landing page by ID."""
        svc = _get_services()
        barangay = svc['barangay_repo'].get_by_id(barangay_id)
        if not barangay:
            flash('Barangay not found.', 'error')
            return redirect(url_for('barangay_landing'))

        is_owner = (current_user.role == 'publisher' and
                    barangay.get('publisher_id') == current_user.id)

        projects = svc['project_repo'].get_all()
        announcements = svc['posts'].get_feed(category='Announcement', sort='newest')

        return render_template('barangay_landing.html',
                               name=current_user.username,
                               role=current_user.role,
                               barangay=barangay,
                               barangay_name=_barangay_display_name(barangay),
                               is_owner=is_owner,
                               projects=projects,
                               announcements=announcements)

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
        # Always render the full set of emoji reactions (0-count included) so
        # users can react to a post even when nobody has reacted yet.
        allowed_emoji = ['👍', '❤️', '😄', '😢', '😡', '🎉']
        reaction_map = {r['emoji']: r['count'] for r in detail['reaction_counts']}
        return render_template('post_detail.html',
                               post=detail,
                               name=current_user.username,
                               role=current_user.role,
                               user_id=current_user.id,
                               allowed_emoji=allowed_emoji,
                               reaction_map=reaction_map)

    @app.route('/barangay/<int:publisher_id>')
    @login_required
    def barangay_profile(publisher_id):
        """
        Barangay profile page — aggregates a publisher's barangay info,
        projects, announcements, and transparency documents in one view.

        Clicking a publisher name on any post in the feed navigates here.
        """
        svc = _get_services()

        # Look up the publisher's user record
        publisher = svc['user_repo'].find_by_id(publisher_id)
        if not publisher or publisher['role'] != 'publisher':
            flash('Barangay not found.', 'error')
            return redirect(url_for('dashboard'))

        # Get the barangay record for this publisher (if they created one)
        barangay = svc['barangay_repo'].get_by_publisher(publisher_id)

        # Gather all content associated with this publisher
        projects = svc['project_repo'].get_by_publisher(publisher_id)
        posts = svc['post_repo'].get_posts_by_publisher(publisher_id)
        documents = svc['document_repo'].get_all()

        # Determine if the viewing user is the owner of this barangay
        is_owner = (current_user.role == 'publisher' and
                    current_user.id == publisher_id)

        return render_template('barangay_profile.html',
                               publisher=dict(publisher),
                               barangay=barangay,
                               projects=projects,
                               posts=posts,
                               documents=documents,
                               is_owner=is_owner,
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
        payload = _project_payload(request.get_json())
        svc = _get_services()
        project, error = svc['project_service'].create_project(
            current_user, payload['title'], payload['description'], payload['status'],
            payload['budget'], payload['location'], payload['image_url'],
            payload['start_date'], payload['end_date']
        )
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'project': project}), 201

    @app.route('/api/projects/<int:project_id>', methods=['PUT'])
    @login_required
    def api_update_project(project_id):
        """API: Update a project. ONLY the publisher who created it can edit."""
        payload = _project_payload(request.get_json())
        svc = _get_services()
        project, error = svc['project_service'].update_project(
            current_user, project_id, payload['title'], payload['description'], payload['status'],
            payload['budget'], payload['location'], payload['image_url'],
            payload['start_date'], payload['end_date']
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

        # Handle profile picture upload using centralized FileUploadHelper
        uploaded_file = request.files.get('profile_picture')
        if uploaded_file and uploaded_file.filename:
            try:
                profile_picture_path = get_upload_helper().save(
                    uploaded_file, prefix=f'profile_{current_user.id}'
                )
            except ValueError:
                profile_picture_path = ''  # Invalid file type — skip

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

        Uses the free Open-Meteo API (no API key required) to fetch:
          - Current: temperature, humidity, wind speed, weather code
          - Daily forecast: 7-day min/max temps, precipitation probability

        Query params: lat (float), lon (float)
        """
        # Parse and validate coordinate parameters
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)

        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon query parameters are required'}), 400

        try:
            # Build the Open-Meteo API URL with current + daily forecast data
            # Open-Meteo is free and doesn't require an API key
            weather_url = (
                'https://api.open-meteo.com/v1/forecast'
                f'?latitude={lat}&longitude={lon}'
                '&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m'
                '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
                '&timezone=auto'
            )
            resp = requests.get(weather_url, timeout=10)
            resp.raise_for_status()  # Raise HTTPError for 4xx/5xx responses
            data = resp.json()

            # Extract current conditions and daily forecast from response
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
            # Network errors, DNS failures, timeouts, etc.
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

    # ================================================================
    # BARANGAY LANDING PAGE CRUD API (publisher-only)
    # ================================================================

    @app.route('/api/barangays')
    @login_required
    def api_get_barangays():
        """API: Get all barangays."""
        svc = _get_services()
        barangays = svc['barangay_repo'].get_all()
        return jsonify({'barangays': barangays})

    @app.route('/api/barangays/<int:barangay_id>')
    @login_required
    def api_get_barangay(barangay_id):
        """API: Get a single barangay by ID."""
        svc = _get_services()
        barangay = svc['barangay_repo'].get_by_id(barangay_id)
        if not barangay:
            return jsonify({'error': 'Barangay not found'}), 404
        return jsonify({'barangay': barangay})

    @app.route('/api/barangays', methods=['POST'])
    @login_required
    def api_create_barangay():
        """
        API: Create a new barangay landing page. ONLY publisher can create.

        Accepts JSON with fields:
          - name (required)
          - description, address, phone, email, facebook
          - office_hours_weekday, office_hours_saturday
          - motto, latitude, longitude
        """
        data = request.get_json() or {}
        svc = _get_services()
        barangay, error = svc['barangay_service'].create_barangay(
            user=current_user,
            name=data.get('name', ''),
            description=data.get('description', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            facebook=data.get('facebook', ''),
            office_hours_weekday=data.get('office_hours_weekday', '8:00 AM – 5:00 PM'),
            office_hours_saturday=data.get('office_hours_saturday', '8:00 AM – 12:00 PM'),
            motto=data.get('motto', ''),
            latitude=data.get('latitude', 14.71309),
            longitude=data.get('longitude', 121.10063),
        )
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'barangay': barangay}), 201

    @app.route('/api/barangays/<int:barangay_id>', methods=['PUT'])
    @login_required
    def api_update_barangay(barangay_id):
        """
        API: Update a barangay's landing-page info. ONLY the owning publisher.

        Accepts JSON with any of the updatable fields:
          name, description, address, phone, email, facebook,
          office_hours_weekday, office_hours_saturday, motto,
          latitude, longitude
        """
        data = request.get_json() or {}
        svc = _get_services()
        barangay, error = svc['barangay_service'].update_barangay(
            user=current_user,
            barangay_id=barangay_id,
            **{k: v for k, v in data.items() if v is not None}
        )
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'barangay': barangay})

    @app.route('/api/barangays/<int:barangay_id>', methods=['DELETE'])
    @login_required
    def api_delete_barangay(barangay_id):
        """API: Delete a barangay page. ONLY the owning publisher."""
        svc = _get_services()
        success, error = svc['barangay_service'].delete_barangay(current_user, barangay_id)
        if error:
            return jsonify({'error': error}), 403
        return jsonify({'success': True})
