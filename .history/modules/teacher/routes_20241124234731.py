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

   return render_template('teacher_dashboard.html', teacher=teacher,active_session=active_session)
   
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

# Start a session
@teacher_bp.route('/start_session', methods=['POST'])
@login_required
def start_session():
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized access'}), 403

    batch_id = request.json.get('batch_id')
    if not batch_id:
        return jsonify({'error': 'Batch ID is required'}), 400

    # End any expired sessions
    end_expired_sessions()

    # Create a new session
    session_id = str(uuid.uuid4())
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=30)  # Session expires in 30 minutes

    new_session = AttendanceSession(
        session_id=session_id,
        teacher_id=current_user.id,
        batch_id=batch_id,
        start_time=start_time,
        end_time=end_time,
        active=True
    )
    db.session.add(new_session)
    db.session.commit()

    return jsonify({'message': 'Session started successfully', 'session': {
        'session_id': session_id,
        'batch_id': batch_id,
        'start_time': start_time,
        'end_time': end_time
    }})

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

