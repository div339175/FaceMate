from flask import Blueprint, render_template,jsonify,request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user
from models import User,Teacher,Student,db,AttendanceSession
from . import teacher_bp
from datetime import datetime

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

    # Get the latest active session for the teacher
    active_session = AttendanceSession.query.filter_by(
        teacher_id=teacher.id, active=True).order_by(AttendanceSession.start_time.desc()).first()


    if teacher:
        # If teacher details are found, render the dashboard template
        return render_template('teacher_dashboard.html', teacher=teacher)
    else:
        # Handle cases where the teacher is not found in the database
        flash('Teacher details not found. Please contact support.', 'danger')
        return redirect(url_for('teacher.login'))

from datetime import datetime, timedelta
import uuid

def create_attendance_session(teacher_id, course_id):
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Set start and end times
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=30)
    
    # Create a new attendance session
    new_session = AttendanceSession(
        session_id=session_id,
        teacher_id=teacher_id,
        course_id=course_id,
        start_time=start_time,
        end_time=end_time,
        active=True
    )
    
    # Save to the database
    db.session.add(new_session)
    db.session.commit()
    
    return new_session

def end_expired_sessions():
    now = datetime.now()
    expired_sessions = AttendanceSession.query.filter(AttendanceSession.end_time < now, AttendanceSession.active == True).all()
    for session in expired_sessions:
        session.active = False
    db.session.commit()


# @teacher_bp.route('/fetch_students')
# def fetch_students():
#     batch = request.args.get('batch')
#     students = Student.query.filter_by(batch=batch).all()
#     return jsonify([
#         {
#             'name': student.name,
#             'roll_number': student.roll_number,
#             'photo': student.photo,
#             'attendance_status': student.attendance_status
#         }
#         for student in students
#     ])

# @teacher_bp.route('/save_attendance', methods=['POST'])
# def save_attendance():
#     try:
#         attendance_data = request.json.get('attendance', [])
#         if not attendance_data:
#             return jsonify({'error': 'No attendance data provided'}), 400
        
#         updated_students = []
#         for data in attendance_data:
#             roll_number = data.get('roll_number')
#             status = data.get('status')

#             # Ensure required fields are present
#             if not roll_number or not status:
#                 continue

#             # Find the student by roll number
#             student = Student.query.filter_by(roll_number=roll_number).first()
#             if student:
#                 # Update the attendance status
#                 student.attendance_status = status
#                 updated_students.append({
#                     'roll_number': roll_number,
#                     'status': status
#                 })

#         # Commit all changes to the database
#         db.session.commit()

#         return jsonify({'message': 'Attendance saved successfully!',
#                         'updated_students': updated_students
#                         }), 200

#     except Exception as e:
#         # Handle errors and return a meaningful message
#         db.session.rollback()  # Roll back in case of error
#         return jsonify({'error': 'An error occurred while saving attendance', 'details': str(e)}), 500

# @teacher_bp.route('/start_session', methods=['POST'])
# @login_required
# def start_attendance_session():
#     if current_user.role != 'teacher':
#         return jsonify({'error': 'Unauthorized access'}), 403
    
#     batch_id = request.json.get('batch_id')
#     if not batch_id:
#         return jsonify({'error': 'Batch ID is required'}), 400
    
#     session = AttendanceSession(batch_id=batch_id)
#     db.session.add(session)
#     db.session.commit()
#     return jsonify({'message': 'Session started', 'session_id': session.id})

# @teacher_bp.route('/end_session', methods=['POST'])
# @login_required
# def end_session():
#     session_id = request.json.get('session_id')
#     session = AttendanceSession.query.filter_by(id=session_id, status='Active').first()
#     if session:
#         session.status = 'Closed'
#         session.end_time = datetime.utcnow()
#         db.session.commit()
#         return jsonify({'message': 'Session ended successfully'})
#     return jsonify({'error': 'No active session found'}), 404

# from models import AttendanceSession, AttendanceRecord, Student, db

# def mark_absent_after_timeout(session_id):
#     """
#     Marks students as absent if they haven't been marked present in the attendance session.
#     """
#     session = AttendanceSession.query.filter_by(id=session_id, status='Active').first()
#     if session:
#         # Find students who have no attendance record for this session
#         students = Student.query.join(AttendanceRecord, isouter=True)\
#             .filter(Student.batch == session.batch_id)\
#             .filter(AttendanceRecord.session_id != session_id)\
#             .all()
        
#         for student in students:
#             record = AttendanceRecord(
#                 session_id=session_id,
#                 student_id=student.id,
#                 status='Absent'
#             )
#             db.session.add(record)
        
#         # Close the session
#         session.status = 'Closed'
#         db.session.commit()

# @teacher_bp.route('/fetch_students')
# def fetch_students():
#     batch = request.args.get('batch')
#     students = Student.query.filter_by(batch=batch).all()
#     return jsonify([
#         {
#             'name': student.name,
#             'roll_number': student.roll_number,
#             'photo': student.photo,
#             'attendance_status': student.attendance_status
#         }
#         for student in students
#     ])

# @teacher_bp.route('/save_attendance', methods=['POST'])
# def save_attendance():
#     try:
#         attendance_data = request.json.get('attendance', [])
#         if not attendance_data:
#             return jsonify({'error': 'No attendance data provided'}), 400
        
#         updated_students = []
#         for data in attendance_data:
#             roll_number = data.get('roll_number')
#             status = data.get('status')

#             # Ensure required fields are present
#             if not roll_number or not status:
#                 continue

#             # Find the student by roll number
#             student = Student.query.filter_by(roll_number=roll_number).first()
#             if student:
#                 # Update the attendance status
#                 student.attendance_status = status
#                 updated_students.append({
#                     'roll_number': roll_number,
#                     'status': status
#                 })

#         # Commit all changes to the database
#         db.session.commit()

#         return jsonify({'message': 'Attendance saved successfully!',
#                         'updated_students': updated_students
#                         }), 200

#     except Exception as e:
#         # Handle errors and return a meaningful message
#         db.session.rollback()  # Roll back in case of error
#         return jsonify({'error': 'An error occurred while saving attendance', 'details': str(e)}), 500
