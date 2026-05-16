from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
# The secret key is required by Flask to keep user sessions secure. 
# For a real production app, this should be a random string hidden in a .env file.
app.secret_key = 'govkonek_super_secret_key' 

# ==========================================
# 🎨 UI PROTOTYPING ROUTES (For Frontend Testing)
# ==========================================

@app.route('/ui/login')
def ui_login():
    return render_template('login.html')

@app.route('/ui/dashboard')
def ui_dashboard():
    # Passing dummy data just to see how the HTML looks
    return render_template('dashboard.html', name="Juan", role="citizen")

@app.route('/ui/feed')
def ui_feed():
    return render_template('components/feed.html')

# ==========================================

# Set up the Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # If someone tries to access a protected page, send them here

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('govkonek.db')
    conn.row_factory = sqlite3.Row # This lets us access columns by name (e.g., user['username'])
    return conn

# 1. Define the User Class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

# 2. Tell Flask-Login how to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
    return None

@app.route('/')
def home():
    return redirect(url_for('login'))

# 3. Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'] # 'citizen' or 'publisher'
        
        # Hash the password for security
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                         (username, hashed_password, role))
            conn.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # This triggers if the username already exists (due to the UNIQUE constraint we set)
            flash('Username already exists. Try another one.')
        finally:
            conn.close()
            
    return render_template('register.html')

# 4. Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        # Check if user exists and password is correct
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
            
    return render_template('login.html')

# 5. Protected Dashboard Route (Testing role-based logic)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username, role=current_user.role)

# 6. Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)