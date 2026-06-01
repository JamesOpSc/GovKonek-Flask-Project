"""
GovKonek Routes Module

Flask routes for user authentication and dashboard access.
This module handles HTTP requests and responses, delegating business logic to services.
Demonstrates the thin route principle - routes are simple and focused on HTTP concerns.
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, login_user, logout_user, current_user
from service import AuthService
from repository import UserRepository
from models import create_user_from_db


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
        
        GET: Display the registration form template
        POST: Process form submission and create new user account
        
        WORKFLOW:
        1. User submits registration form with username, password, role
        2. AuthService validates and creates user in database
        3. If successful, redirect to login page
        4. If unsuccessful, display error message and redisplay form
        """
        if request.method == 'POST':
            # Extract form data from user submission
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            
            # Delegate registration logic to AuthService (keeps route code simple)
            success, message = AuthService.register_user(username, password, role)
            
            if success:
                # Registration succeeded - show success message and redirect to login
                flash(message, 'success')
                return redirect(url_for('login'))
            else:
                # Registration failed - show error message and redisplay form
                flash(message, 'error')
        
        # Display the registration form template (GET request or after POST failure)
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
        Login page and form handler.
        
        GET: Display the login form template
        POST: Process form submission and authenticate user
        
        WORKFLOW:
        1. User submits login form with username and password
        2. AuthService authenticates user against database
        3. If successful, Flask-Login creates user session and redirects to dashboard
        4. If unsuccessful, display error message and redisplay form
        """
        if request.method == 'POST':
            # Extract form data from user submission
            username = request.form['username']
            password = request.form['password']
            
            # Delegate authentication logic to AuthService (keeps route code simple)
            success, user = AuthService.authenticate_user(username, password)
            
            if success:
                # Authentication succeeded - create session and redirect to dashboard
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                # Authentication failed - show error message and redisplay form
                flash('Invalid username or password.', 'error')
        
        # Display the login form template (GET request or after POST failure)
        return render_template('login.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """
        Dashboard page - accessible only to authenticated users.
        
        Displays user-specific information based on their role.
        Protected by @login_required - unauthenticated users are redirected to login.
        """
        return render_template('dashboard.html', name=current_user.username, role=current_user.role)

    @app.route('/profile')
    @login_required
    def profile():
        """
        User profile page - displays user information.
        
        Shows the authenticated user's profile including their username and role.
        Protected by @login_required - unauthenticated users are redirected to login.
        """
        return render_template('profile.html', name=current_user.username, role=current_user.role)

    @app.route('/logout')
    @login_required
    def logout():
        """
        Logout handler - clears user session and redirects to login page.
        The @login_required decorator ensures only authenticated users can logout.
        
        WORKFLOW:
        1. User clicks logout link
        2. @login_required checks that user is logged in
        3. logout_user() clears the session
        4. Redirect to login page
        """
        logout_user()
        return redirect(url_for('login'))

    @app.route('/')
    def home():
        """
        Home page - redirects to login page.
        No homepage is defined, so we direct all traffic to login.
        """
        return redirect(url_for('login'))
