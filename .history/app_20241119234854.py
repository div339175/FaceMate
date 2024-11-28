from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user, UserMixin
from config import Config
from modules.developer import developer_bp
from modules.student import student_bp
from modules.teacher import teacher_bp

# Initialize Flask App and Extensions
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Default login view

# Register Blueprints
app.register_blueprint(developer_bp, url_prefix='/developer')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(teacher_bp, url_prefix='/teacher')

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Query user from database by user ID

@app.route('/')
def home():
    return render_template('home.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  # Check password (Use hashed passwords in production)
            login_user(user)
            if user.role == 'developer':
                return redirect(url_for('developer.developer_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student.student_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher.teacher_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
