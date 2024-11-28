from flask import send_file, render_template,jsonify,request, redirect, url_for, flash
from flask_login import login_user, login_required, current_user
from models import User,Teacher,StudentCourse,Course,Student,db,AttendanceSession,Attendance
from . import teacher_bp
from datetime import datetime, timedelta
import uuid
import os
import csv
import io

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
    try:
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

        # Create a new CSV file for the session
        create_csv(batch_id,course_code)

        return jsonify({'message': 'Session started successfully', 'session': {
            'session_id': session_id,
            'batch_id': batch_id,
            'course_code': course_code,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }}), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in start_session: {e}")
        return jsonify({'error': 'An error occurred while starting the session.'}), 500

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

def create_csv(batch_id, course_code):
    """
    Create a CSV for attendance session with default status 'Absent'.
    """
    try:
        # Define file path
        csv_dir = "attendance_files"
        os.makedirs(csv_dir, exist_ok=True)
        csv_file = os.path.join(csv_dir, f"attendance_session_{course_code}.csv")

        # Fetch students from the specified batch and course
        students = Student.query.join(StudentCourse, Student.roll_number == StudentCourse.roll_number).filter(
            StudentCourse.course_code == course_code,
            Student.batch == batch_id
        ).all()

        if not students:
            raise ValueError("No students found for the given batch and course.")

        # Write to CSV
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Roll Number", "Name", "Batch", "Photo", "Attendance Status"])  # Headers
            for student in students:
                writer.writerow([
                    student.roll_number,
                    student.name,
                    student.batch,
                    student.photo_url if hasattr(student, 'photo_url') else "N/A",
                    "Absent"
                ])

        return csv_file
    except Exception as e:
        print(f"Error creating CSV: {e}")
        raise

# Route to render the attendance view page

@teacher_bp.route('/view_attendance', methods=['GET'])
def view_attendance():
    # Get the batch_id and course_code from the URL parameters
    batch_id = request.args.get('batch_id')
    course_code = request.args.get('course_code')

    # Construct the path for the CSV file
    csv_file = os.path.join("attendance_files", f"attendance_session_{course_code}.csv")

    # Check if the CSV file exists
    if not os.path.exists(csv_file):
        return jsonify({"error": "No attendance file found for this session."}), 404

    # Query to get students in the given batch and course
    students = db.session.query(Student).filter(Student.batch == batch_id).all()

    # Read the CSV file to get the attendance data
    try:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            attendance_data = [row for row in reader]

        # Prepare a list of students with their attendance status and photo
        student_details = []
        for student in students:
            # Find the attendance record for the student based on roll number
            attendance_status = "Absent"  # Default status
            for record in attendance_data:
                if record['Roll Number'] == student.roll_number:
                    attendance_status = record['Attendance Status']
                    break

            # Add student details including the photo and attendance status
            student_details.append({
                'Roll Number': student.roll_number,
                'Name': student.name,
                'Batch': student.batch,
                'Photo': student.photo,  # Assuming the photo URL is stored in the 'photo' column of the Student table
                'Attendance Status': attendance_status
            })

        # Render the view_attendance.html page with the student data
        return render_template('view_attendance.html', students=student_details, batch_id=batch_id, course_code=course_code)

    except Exception as e:
        return jsonify({"error": "Failed to read CSV file", "details": str(e)}), 500
@teacher_bp.route('/save_attendance', methods=['POST'])
def save_attendance():
    try:
        data = request.json
        attendance_updates = data.get('attendance', [])

        # Update records in the database
        for student in attendance_updates:
            # Update attendance status in MySQL
            record = Attendance.query.filter_by(roll_no=student['roll_no']).first()
            if record:
                record.status = student['status']
                db.session.commit()

        # Also update the CSV file
        update_csv(attendance_updates)

        return jsonify({"message": "Attendance updated successfully!"})
    except Exception as e:
        return jsonify({"error": "Failed to save attendance", "details": str(e)}), 500

def update_csv(attendance_updates):
    csv_dir = "attendance_files"
    # Assuming `course_code` and `batch_id` are available globally or passed in
    csv_file = os.path.join(csv_dir, f"attendance_session_{attendance_updates[0]['course_code']}.csv")

    # Read existing CSV
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))

    # Update attendance status in CSV
    for update in attendance_updates:
        for row in rows:
            if row['Roll Number'] == update['roll_no']:
                row['Attendance Status'] = update['status']

    # Write back updated data to CSV
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

