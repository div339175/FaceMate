from flask import Blueprint, render_template,jsonify,request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user
from models import User,Teacher,Student,db
from . import teacher_bp

@teacher_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role='teacher').first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('teacher.teacher_dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('t_login.html')

@teacher_bp.route('/dashboard')
@login_required
def teacher_dashboard():
    # Check if the logged-in user is a teacher
    if current_user.role != 'teacher':
        flash('Access denied. This section is for teachers only.', 'danger')
        return redirect(url_for('home'))

    # Use the email of the logged-in user to fetch teacher details
    teacher_email = current_user.email
    teacher = Teacher.query.filter_by(email=teacher_email).first()

    if teacher:
        # If teacher details are found, render the dashboard template
        return render_template('teacher_dashboard.html', teacher=teacher)
    else:
        # Handle cases where the teacher is not found in the database
        flash('Teacher details not found. Please contact support.', 'danger')
        return redirect(url_for('teacher.login'))

@teacher_bp.route('/fetch_students')
def fetch_students():
    batch = request.args.get('batch')
    students = Student.query.filter_by(batch=batch).all()
    return jsonify([
        {
            'name': student.name,
            'roll_no': student.roll_number,
            'photo': student.photo,
            'attendance_status': student.attendance_status
        }
        for student in students
    ])

@teacher_bp.route('/save_attendance', methods=['POST'])
def save_attendance():
    attendance_data = request.json.get('attendance', [])
    for data in attendance_data:
        student = Student.query.filter_by(roll_no=data['roll_number']).first()
        if student:
            student.attendance_status = data['status']
    db.session.commit()
    return jsonify({'message': 'Attendance saved successfully!'})