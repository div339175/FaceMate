# modules/developer/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user
from models import Developer,Teacher,Student,db,User
from . import developer_bp
# from werkzeug.security import generate_password_hash  # For hashing passwords

@developer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email,role='developer').first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('developer.developer_dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('d_login.html')

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
        roll_number = request.form['roll_number']
        enrollment_number = request.form['enrollment_number']
        year = request.form['year']
        semester = request.form['semester']
        photo = request.files['photo']

 # Hash the password
        # hashed_password = generate_password_hash(password, method='sha256')
       
       # Save user information to the User table
        new_user = User(email=email, password=hashed_password, role='student')
        db.session.add(new_user)
        db.session.commit()  # Commit to get the new_user ID
        
        
        # Save student information to the Student table
        new_student = Student(
            name=name,
            email=email,
            roll_number=roll_number,
            enrollment_number=enrollment_number,
            year=year,
            semester=semester,
            photo=photo.filename,  # Save the filename
            user_id=new_user.id  # Associate with the User table using the ID
        )
        db.session.add(new_student)
        db.session.commit()  # Commit the new student data
        
        # Optionally, save the photo file
        if photo:
            photo.save(f'static/uploads/{photo.filename}')
        
        # # Check if a student with the same email already exists
        # if User.query.filter_by(email=email).first():
        #     flash('Email already registered', 'danger')
        # else:
        #     new_student = Student(name=name, email=email, password=password, role='student')
        #     db.session.add(new_student)
        #     db.session.commit()
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
        if Developer.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            new_teacher = Teacher(name=name, email=email, password=password, role='teacher')
            db.session.add(new_teacher)
            db.session.commit()
            flash('Teacher registered successfully', 'success')
            return redirect(url_for('developer.developer_dashboard'))
    
    return render_template('register_teacher.html')
