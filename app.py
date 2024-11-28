from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, current_user
from config import Config
from modules.developer import developer_bp
from modules.student import student_bp
from modules.teacher import teacher_bp
from models import db, User  # Import db from models
import socket
from flask_migrate import Migrate,upgrade
import os
# from flask_cors import CORS
# Initialize Flask App and Extensions
app = Flask(__name__)
# CORS(app) 
app.config.from_object(Config)

# Initialize db with app using init_app
db.init_app(app)  # Using init_app instead of passing 'app' directly to db
migrate = Migrate(app, db)  # Bind Migrate to Flask app and SQLAlchemy

# Ensure migrations are applied on app startup
def apply_migrations():
    if not os.path.exists('migrations'):
        # Initialize the migrations folder if it doesn't exist
        print("Initializing migrations directory...")
        from flask_migrate import init
        init()

    print("Generating migration script...")
    from flask_migrate import migrate as db_migrate
    db_migrate(message="Auto migration on startup")

    print("Applying migrations...")
    upgrade()
# login_manager = LoginManager(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'developer.login'  # Default login view

@login_manager.user_loader
def load_user(email):
    return User.query.get(email)  # Load the user by their email from the database


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
    # Get the local IP address
    with app.app_context():
        apply_migrations()  # Automatically handle migration
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # Print the URL with the local IP
    print(f"App is running! Access it via: https://{local_ip}:80")

    app.run(host="0.0.0.0", port=80, ssl_context=("certs/cert.pem", "certs/key.pem"))
