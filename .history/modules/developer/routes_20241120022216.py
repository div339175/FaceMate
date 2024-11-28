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
        user = User.query.filter_by(email=email).first()

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
