# modules/developer/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user
from models import Developer,Teacher,Student,db,User
from . import developer_bp
from werkzeug.security import check_password_hash

@developer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Developer.query.filter_bimport logging

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a file handler and a stream handler
file_handler = logging.FileHandler('developer_routes.log')
stream_handler = logging.StreamHandler()

# Create a formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

@developer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Developer.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            logger.info(f'User {email} logged in successfully')
            return redirect(url_for('developer_dashboard'))
        else:
            logger.warning(f'Invalid login attempt for user {email}')
            flash('Invalid email or password', 'danger')

    logger.info('Login page accessed')
    return render_template('login.html')

@developer_bp.route('/dashboard')
@login_required
def developer_dashboard():
    if current_user.role != 'developer':
        logger.warning(f'Non-developer user {current_user.email} attempted to access developer dashboard')
        return redirect(url_for('home'))
    logger.info(f'Developer {current_user.email} accessed dashboard')
    return render_template('developer_dashboard.html')

# Route to register a new student
@developer_bp.route('/register_student', methods=['GET', 'POST'])
@login_required
def register_student():
    if current_user.role != 'developer':
        logger.warning(f'Non-developer user {current_user.email} attempted to register a student')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if a student with the same email already exists
        if User.query.filter_by(email=email).first():
            logger.warning(f'Attempt to register student with existing email {email}')
            flash('Email already registered', 'danger')
        else:
            new_student = Student(name=name, email=email, password=password, role='student')
            db.session.add(new_student)
            db.session.commit()
            logger.info(f'Student {email} registered successfully')
            flash('Student registered successfully', 'success')
            return redirect(url_for('developer.developer_dashboard'))
    
    logger.info('Register student page accessed')
    return render_template('register_student.html')

# Route to register a new teacher
@developer_bp.route('/register_teacher', methods=['GET', 'POST'])
@login_required
def register_teacher():
    if current_user.role != 'developer':
        logger.warning(f'Non-developer user {current_user.email} attempted to register a teacher')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if a teacher with the same email already exists
        if User.query.filter_by(email=email).first():
            logger.warning(f'Attempt to register teacher with existing email {email}')
            flash('Email already registered', 'danger')
        else:
            new_teacher = Teacher(name=name, email=email, password=password, role='teacher')
            db.session.add(new_teacher)
            db.session.commit()
            logger.info(f'Teacher {email} registered successfully')
            flash('Teacher registered successfully', 'success')
            return redirect(url_for('developer.developer_dashboard'))
    
    logger.info('Register teacher page accessed')
    return render_template('register_teacher.html')y(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('developer_dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('login.html')

@developer_bp.route('/dashboard')
@login_required
def developer_dashboard():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    return render_template('developer_dashboard.html')

# Route to register a new student
@developer_bp.route('/register_student', methods=['GET', 'POST'])
@login_required
def register_student():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if a student with the same email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            new_student = Student(name=name, email=email, password=password, role='student')
            db.session.add(new_student)
            db.session.commit()
            flash('Student registered successfully', 'success')
            return redirect(url_for('developer.developer_dashboard'))
    
    return render_template('register_student.html')

# Route to register a new teacher
@developer_bp.route('/register_teacher', methods=['GET', 'POST'])
@login_required
def register_teacher():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if a teacher with the same email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            new_teacher = Teacher(name=name, email=email, password=password, role='teacher')
            db.session.add(new_teacher)
            db.session.commit()
            flash('Teacher registered successfully', 'success')
            return redirect(url_for('developer.developer_dashboard'))
    
    return render_template('register_teacher.html')
