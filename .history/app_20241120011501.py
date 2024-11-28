from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user
from config import Config
from modules.developer import developer_bp
from modules.student import student_bp
from modules.teacher import teacher_bp
from models import db, User, Developer, Student, Teacher  # Import db from models

# Initialize Flask App and Extensions
app = Flask(__name__)
app.config.from_object(Config)

# Initialize db with app using init_app
db.init_app(app)  # Using init_app instead of passing 'app' directly to db

login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Default login view

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Load the user by their ID from the database

@app.route('/')
def home():
    return render_template('home.html')

# Register Blueprints
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(developer_bp, url_prefix='/developer')

# Function to create tables automatically when app starts
def create_tables():
    with app.app_context():
        db.create_all()  # This will create all tables defined in the models

if __name__ == '__main__':
    create_tables()  # Call the function to create tables before running the app
    app.run(debug=True)
