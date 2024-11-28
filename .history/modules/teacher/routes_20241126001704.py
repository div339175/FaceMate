from flask import Blueprint, render_template,jsonify,request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user
from models import User,Teacher,StudentCourse,Course,Student,db,AttendanceSession,Attendance
from . import teacher_bp
from datetime import datetime, timedelta
import uuid

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

    teacher_email = current_user.email
    teacher = Teacher.query.filter_by(email=teacher_email).first()

    # Get the latest active session for the teacher
    active_session = AttendanceSession.query.filter_by(
        teacher_id=teacher.id, active=True
    ).order_by(AttendanceSession.start_time.desc()).first()


    # Convert active_session to a dictionary
    active_session_data = None
    if active_session:
        active_session_data = {
            'session_id': active_session.session_id,
            'batch_id': active_session.batch_id,
            'course_code': active_session.course_id,
            'start_time': active_session.start_time.isoformat(),
            'end_time': active_session.end_time.isoformat(),
            'active': active_session.active,
        }

    return render_template(
        'teacher_dashboard.html', 
        teacher=teacher, 
        active_session=active_session_data
    )

# Start a session
@teacher_bp.route('/start_session', methods=['POST'])
@login_required
def start_session():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized access'}), 403

    batch_id = request.json.get('batch_id')
    course_code = request.json.get('course_code')  # Use course_code instead of course_id for clarity

    if not batch_id or not course_code:
        return jsonify({'error': 'Batch ID and Course Code are required'}), 400

    # Verify if the course exists
    course = Course.query.filter_by(code=course_code).first()
    if not course:
        return jsonify({'error': 'Invalid course'}), 400

    # Get the teacher ID from the Teacher table
    teacher = Teacher.query.filter_by(email=current_user.email).first()
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    teacher_id = teacher.id

    # Fetch students enrolled in the course and batch
    enrolled_students = Student.query.join(StudentCourse, Student.roll_number == StudentCourse.roll_number).filter(
        StudentCourse.course_code == course.code,
        Student.batch == batch_id
    ).all()

    if not enrolled_students:
        return jsonify({'error': 'No students found for this batch and course'}), 400


    # End any expired sessions
    end_expired_sessions()

    # Create a new session
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=30)  # Session expires in 30 minutes

    new_session = AttendanceSession(
        session_id=session_id,
        teacher_id=teacher_id,
        batch_id=batch_id,
        course_id=course_code,
        start_time=start_time,
        end_time=end_time,
        active=True
    )
    db.session.add(new_session)
    db.session.commit()

    return jsonify({'message': 'Session started successfully', 'session': {
        'session_id': session_id,
        'batch_id': batch_id,
        'course_code': course_code,
        'start_time': start_time,
        'end_time': end_time
    }})

# @teacher_bp.route('/active_sessions/<int:student_id>', methods=['GET'])
# def get_active_sessions(student_id):
#     student = Student.query.get(student_id)
#     if not student:
#         return jsonify({"message": "Student not found"}), 404
#     active_sessions = AttendanceSession.query.filter(
#         AttendanceSession.batch_id == student.batch,
#         AttendanceSession.active == True
#     ).all()
#     return jsonify([{"session_id": s.session_id, "course_id": s.course_id} for s in active_sessions])

@teacher_bp.route('/active_session', methods=['GET'])
@login_required
def get_active_session():
    """Fetch the active session for the current teacher."""
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized access'}), 403

    teacher = Teacher.query.filter_by(email=current_user.email).first()
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    active_session = AttendanceSession.query.filter_by(
        teacher_id=teacher.id, active=True
    ).order_by(AttendanceSession.start_time.desc()).first()

    if active_session:
        session_data = {
            'session_id': active_session.session_id,
            'batch_id': active_session.batch_id,
            'course_code': active_session.course_id,
            'start_time': active_session.start_time.isoformat(),
            'end_time': active_session.end_time.isoformat(),
            'active': active_session.active,
        }
        return jsonify({'active_session': session_data})

    return jsonify({'active_session': None})


# End a session
@teacher_bp.route('/end_session', methods=['POST'])
@login_required
def end_session():
    session_id = request.json.get('session_id')
    session = AttendanceSession.query.filter_by(session_id=session_id, active=True).first()
    if not session:
        return jsonify({'error': 'No active session found'}), 404

    session.active = False
    db.session.commit()

    return jsonify({'message': 'Session ended successfully'})

def end_expired_sessions():
    now = datetime.now()
    expired_sessions = AttendanceSession.query.filter(
        AttendanceSession.end_time < now,
        AttendanceSession.active == True
    ).all()

    for session in expired_sessions:
        session.active = False
    db.session.commit()

@teacher_bp.route('/save_attendance', methods=['POST'])
@login_required
def save_attendance():
   # Get attendance data from request
    attendance_data = request.json.get('attendance', [])
    if not attendance_data:
        return jsonify({'error': 'No attendance data provided'}), 400

    for record in attendance_data:
        roll_number = record.get('roll_number')
        session_id = record.get('session_id')
        status = record.get('status')

        # Validate record fields
        if not roll_number or not session_id or not status:
            return jsonify({'error': 'Incomplete attendance record'}), 400

        # Fetch the student and session
        student = Student.query.filter_by(roll_number=roll_number).first()
        session = AttendanceSession.query.filter_by(session_id=session_id, active=True).first()

        if not student or not session:
            continue  # Skip invalid records


        # Check if the student is enrolled in the course and batch for this session
        enrolled_in_course = StudentCourse.query.filter_by(
            roll_number=roll_number,
            course_code=session.course_id
        ).first()

        if not enrolled_in_course or student.batch != session.batch_id:
            continue  # Skip if the student is not enrolled in the course and batch for the session



        # Record attendance
        attendance = Attendance(
            session_id=session.id,
            student_id=student.id,
            name=student.name,
            roll_number=student.roll_number,
            batch_id=student.batch,
            status=status,
            timestamp=datetime.now()
        )
        db.session.add(attendance)

    db.session.commit()
    return jsonify({'message': 'Attendance saved successfully'})

@teacher_bp.route('/fetch_students', methods=['GET'])
@login_required
def fetch_students():
    batch_id = request.args.get('batch_id')
    course_code = request.args.get('course_code')

    if not batch_id or not course_code:
        return jsonify({'error': 'Batch ID and Course Code are required'}), 400

    # Fetch students enrolled in the course and batch
    students = Student.query.join(StudentCourse, Student.roll_number == StudentCourse.roll_number).filter(
        StudentCourse.course_code == course_code,
        Student.batch == batch_id
    ).all()

    if not students:
        return jsonify({'error': 'No students found for this batch and course'}), 400

    # Prepare student data
    student_list = [{'name': student.name, 'roll_number': student.roll_number, 'attendance_status': 'Absent'} for student in students]
    return jsonify(student_list)