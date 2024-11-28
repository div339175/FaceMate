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

                photo_url = f"/static/uploads/{student.photo}" if student.photo else "N/A"

                # Write the student's details to the CSV file
                writer.writerow([
                    student.roll_number,
                    student.name,
                    student.batch,
                    photo_url,  # Photo URL is now correctly added
                    "Absent"  # Default attendance status
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

    # Read the CSV file to get the attendance data
    students = []
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                students.append(row)
        # Render the view_attendance.html page with the student data
        return render_template('view_attendance.html', students=students, batch_id=batch_id,course_code=course_code)
    except Exception as e:
        return jsonify({"error": "Failed to read CSV file", "details": str(e)}), 500

@teacher_bp.route('/save_attendance', methods=['POST'])
def save_attendance():
    try:
        # Get the data from the request
        data = request.json
        attendance_data = data.get('attendance_data', [])
        course_code = data.get('course_code')  # Retrieve course_code from the request

        # Construct the path to the CSV file using course_code
        csv_file = os.path.join("attendance_files", f"attendance_session_{course_code}.csv")

        # Check if the file exists
        if not os.path.exists(csv_file):
            return jsonify({"error": "CSV file not found"}), 404

        # Read the existing CSV content
        students = []
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            students = list(reader)

        # Update the attendance status based on the received data
        roll_no_to_attendance = {str(item['roll_no']): item['attendance'] for item in attendance_data}

        for student in students:
            roll_no = student['Roll Number']
            if roll_no in roll_no_to_attendance:
                student['Attendance Status'] = roll_no_to_attendance[roll_no]

        # Write the updated content back to the CSV file
        with open(csv_file, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=students[0].keys())
            writer.writeheader()
            writer.writerows(students)

        return jsonify({"success": True, "message": "Attendance updated successfully!"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# from flask import render_template, make_response
# from weasyprint import HTML
# import os
# import csv

# @teacher_bp.route('/download_report', methods=['GET'])
# def download_report():
#     course_code = request.args.get('course_code')
#     if not course_code:
#         return jsonify({"error": "Course code is required"}), 400

#     # Construct the path to the attendance CSV
#     csv_file = os.path.join("attendance_files", f"attendance_session_{course_code}.csv")
#     if not os.path.exists(csv_file):
#         return jsonify({"error": "CSV file not found"}), 404

#     # Read the CSV file to get student data
#     students = []
#     with open(csv_file, mode='r', encoding='utf-8') as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             students.append(row)

#     # Prepare the context for the HTML report
#     context = {
#         'course_code': course_code,
#         'students': students
#     }

#     # Render the HTML template for the report
#     html_content = render_template('attendance_report.html', **context)

#     # Generate the PDF using WeasyPrint
#     pdf = HTML(string=html_content).write_pdf()

#     # Prepare the response to return the PDF file
#     response = make_response(pdf)
#     response.headers['Content-Type'] = 'application/pdf'
#     response.headers['Content-Disposition'] = f'attachment; filename="attendance_report_{course_code}.pdf"'
#     return response
