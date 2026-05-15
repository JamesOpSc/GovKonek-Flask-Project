from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from abc import ABC, abstractmethod

app = Flask(__name__)
app.secret_key = 'govkonek_super_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

#DATABASE LAYER (Abstraction)
class UserRepository:
    """Repository pattern: Abstracts all database operations for users"""
    
    @staticmethod
    def get_db_connection():
        conn = sqlite3.connect('govkonek.db')
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def find_by_id(user_id):
        """Fetch user from database by ID"""
        conn = UserRepository.get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return user_data
    
    @staticmethod
    def find_by_username(username):
        """Fetch user from database by username"""
        conn = UserRepository.get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return user_data
    
    @staticmethod
    def create(username, hashed_password, role):
        """Insert new user into database"""
        conn = UserRepository.get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                        (username, hashed_password, role))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

#DOMAIN MODELS (Encapsulation & Inheritance)
class User(UserMixin, ABC):
    """Abstract base User class with encapsulation (private attributes)"""
    
    def __init__(self, id, username, role):
        self._id = id
        self._username = username
        self._role = role
    
    # Properties provide controlled read-only access (Encapsulation)
    @property
    def id(self):
        """Read-only user ID"""
        return self._id
    
    @property
    def username(self):
        """Read-only username"""
        return self._username
    
    @property
    def role(self):
        """Read-only role"""
        return self._role
    
    @abstractmethod
    def get_permissions(self):
        """Abstract method: Return list of permissions for this user type (Polymorphism)"""
        pass
    
    @abstractmethod
    def can_publish(self):
        """Abstract method: Check if user can publish content (Polymorphism)"""
        pass

class CitizenUser(User):
    """Citizen user with limited permissions (Inheritance & Polymorphism)"""
    
    def get_permissions(self):
        """Citizens can only view and file complaints"""
        return ['view_dashboard', 'view_complaints', 'file_complaint']
    
    def can_publish(self):
        """Citizens cannot publish"""
        return False

class PublisherUser(User):
    """Publisher user with extended permissions (Inheritance & Polymorphism)"""
    
    def get_permissions(self):
        """Publishers have full access"""
        return ['view_dashboard', 'view_complaints', 'file_complaint', 'publish_updates', 'view_analytics']
    
    def can_publish(self):
        """Publishers can publish"""
        return True

# Factory function to create appropriate user type (Polymorphism)
def create_user_from_db(user_data):
    """Factory function: Instantiates the correct User subclass based on role"""
    if user_data['role'] == 'publisher':
        return PublisherUser(user_data['id'], user_data['username'], user_data['role'])
    else:
        return CitizenUser(user_data['id'], user_data['username'], user_data['role'])

#SERVICE LAYER (Abstraction)
class AuthService:
    """Service class: Encapsulates all authentication and authorization logic"""
    
    @staticmethod
    def register_user(username, password, role):
        """Register a new user with validation"""
        if not username or not password or not role:
            return False, "All fields are required"
        
        if UserRepository.find_by_username(username):
            return False, "Username already exists. Try another one."
        
        hashed_password = generate_password_hash(password)
        if UserRepository.create(username, hashed_password, role):
            return True, "Registration successful! Please log in."
        
        return False, "Registration failed"
    
    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user and return User object if valid"""
        user_data = UserRepository.find_by_username(username)
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            return True, create_user_from_db(user_data)
        
        return False, None

#FLASK-LOGIN INTEGRATION
@login_manager.user_loader
def load_user(user_id):
    """Tell Flask-Login how to load a user from the database"""
    user_data = UserRepository.find_by_id(user_id)
    if user_data:
        return create_user_from_db(user_data)
    return None

#ROUTES
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        success, message = AuthService.register_user(username, password, role)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        success, user = AuthService.authenticate_user(username, password)
        
        if success:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Now we can use polymorphic methods
    permissions = current_user.get_permissions()
    can_publish = current_user.can_publish()
    
    return render_template('dashboard.html', 
                          name=current_user.username, 
                          role=current_user.role,
                          permissions=permissions,
                          can_publish=can_publish)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def home():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)