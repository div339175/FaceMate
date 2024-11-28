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
            'roll_number': student.roll_number,
            'photo': student.photo,
            'attendance_status': student.attendance_status
        }
        for student in students
    ])

@from flask import request, jsonify
from app.models import db, Student

@teacher_bp.route('/save_attendance', methods=['POST'])
def save_attendance():
    try:
        attendance_data = request.json.get('attendance', [])
        if not attendance_data:
            return jsonify({'error': 'No attendance data provided'}), 400
        
        updated_students = []
        for data in attendance_data:
            roll_number = data.get('roll_number')
            status = data.get('status')

            # Ensure required fields are present
            if not roll_number or not status:
                continue

            # Find the student by roll number
            student = Student.query.filter_by(roll_number=roll_number).first()
            if student:
                # Update the attendance status
                student.attendance_status = status
                updated_students.append({
                    'roll_number': roll_number,
                    'status': status
                })

        # Commit all changes to the database
        db.session.commit()

        return jsonify({'message': 'Attendance saved successfully!',
                        'updated_students': updated_students
                        }), 200

    except Exception as e:
        # Handle errors and return a meaningful message
        db.session.rollback()  # Roll back in case of error
        return jsonify({'error': 'An error occurred while saving attendance', 'details': str(e)}), 500
