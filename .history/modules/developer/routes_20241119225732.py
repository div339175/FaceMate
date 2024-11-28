from flask import Blueprint,jsonify, render_template, request, flash, redirect, url_for
from models import db, User, Student, Teacher
from flask_login import login_required,current_user
# from . import developer_bp

developer_bp = Blueprint('developer', __name__, template_folder='templates')  # Ensure template_folder is correct


@developer_bp.route('/dashboard')
@login_required
def developer_dashboard():
    if current_user.role != 'developer':
        return redirect(url_for('login'))  # Redirect if not a developer
    return render_template('developer_dashboard.html')
# def register_student():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         password = request.form['password']
#         roll_number = request.form['roll_number']
#         year = request.form['year']
#         semester = request.form['semester']
        
#         student = Student(name=name, email=email, password=password, roll_number=roll_number, year=year, semester=semester)
#         db.session.add(student)
#         db.session.commit()
#         flash('Student registered successfully!', 'success')
#         return redirect(url_for('developer.developer_dashboard'))
    
#     return render_template('register_student.html')

# @developer_bp.route('/register_teacher', methods=['GET', 'POST'])
# @login_required
# def register_teacher():
#     if request.method == 'POST':
#         name = request.form['name']
#         email = request.form['email']
#         password = request.form['password']
#         course = request.form['course']
        
#         teacher = Teacher(name=name, email=email, password=password, course=course)
#         db.session.add(teacher)
#         db.session.commit()
#         flash('Teacher registered successfully!', 'success')
#         return redirect(url_for('developer.developer_dashboard'))
    
#     return render_template('register_teacher.html')
