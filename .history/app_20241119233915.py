from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, User

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db.init_app(app)

# Initialize LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Default login view

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  # Ideally use hashed password in production
            login_user(user)
            if user.role == 'student':
                return redirect(url_for('student.student_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher.teacher_dashboard'))
            elif user.role == 'developer':
                return redirect(url_for('developer.developer_dashboard'))
            else:
                flash("Invalid role", 'danger')
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')

# # Route for logout
# @app.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('login'))

# Home route
@app.route('/')
def home():
    return render_template('home.html')

# Register blueprints
from modules.student import student_bp
from modules.teacher import teacher_bp
from modules.developer import developer_bp

app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(developer_bp, url_prefix='/developer')

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
