from flask import Blueprint, render_template,jsonify, request, redirect, url_for, flash
from flask_login import login_user,LoginManager, login_required, current_user,logout_user
from models import User
from . import student_bp
import cv2
import os
import base64
import numpy as np
from models import Student,Course,db,AttendanceSession,Attendance,StudentCourse
from datetime import datetime


@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, role='student').first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('student.student_dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('s_login.html')

@student_bp.route('/logout')
def logout():
    # Logic for logging out the user
    logout_user()
    return redirect(url_for('student.login'))

def student_to_dict(student):
    return {
        'name': student.name,
        'email': student.email,
        'roll_number': student.roll_number,
        'enrollment_number': student.enrollment_number,
        'batch': student.batch,
        'year': student.year,
        'semester': student.semester,
        'photo': student.photo
    }

def session_to_dict(session):
    return {
        'course_name': session.course.name,
        'course_code': session.course.code,
        'active_session': session.active_session
    }

@student_bp.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('home'))
    
    # Use the email of the logged-in user to fetch student details
    student_email = current_user.email
    student = Student.query.filter_by(email=student_email).first()
    
    # Handle cases where no student details are found
    if not student:
        flash('Student details not found. Please contact support.', 'danger')
        return redirect(url_for('student.login'))

    # Convert student object to dictionary
    student_dict = student_to_dict(student)

    # Fetch all courses the student is enrolled in based on their roll number
    student_courses = StudentCourse.query.filter_by(roll_number=student.roll_number).all()

    # If no courses are found, display a message
    if not student_courses:
        flash('No courses found for this student.', 'warning')
        return render_template('student_dashboard.html', student=student_dict)

    active_sessions = []

    # Loop through each course the student is enrolled in and check for active sessions
    for student_course in student_courses:
        course = Course.query.filter_by(code=student_course.course_code).first()
        if course:
            # Get active session for the course
            active_session = get_active_session(course.code)

            if active_session:
                active_sessions.append({'course': course, 'active_session': active_session})

    # Convert active_sessions to dictionaries
    active_sessions_dict = [session_to_dict(session) for session in active_sessions]

    # Render the dashboard page with the student info and active sessions
    return render_template('student_dashboard.html', student=student_dict, active_sessions=active_sessions_dict)

# Helper function to check active session
def get_active_session(course_id):
    active_session = AttendanceSession.query.filter_by(course_id=course_id, active=True).first()
    if active_session and active_session.end_time > datetime.now():
        return active_session
    return None

# Load Haar Cascade for face detection
cascade_path = 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Initialize LBPH Face Recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Base folder for storing user data
base_user_folder = "modules/developer/static/uploads/"

@student_bp.route('/recognize', methods=['POST'])
def recognize_face():
    try:
        data = request.get_json()
        photo_data = data.get('photoData')
        roll_no = data.get('rollNO')  # Using roll number from the request data

        if not photo_data or not roll_no:
            return jsonify({"message": "Photo data or Roll Number is missing"}), 400

        # Get the student record based on roll number and logged-in user email
        student = Student.query.filter_by(email=current_user.email, roll_number=roll_no).first()
        if not student:
            return jsonify({"message": "Student not found"}), 404

         # Check for an active session
        active_session = get_active_session(student.course)
        if not active_session:
            return jsonify({"message": "No active attendance session available"}), 400


        # Check if the model exists for the student
        model_path = os.path.join(base_user_folder, roll_no, f"{roll_no}_model.yml")
        if not os.path.exists(model_path):
            return jsonify({"message": "Model not found. Please train the data first."}), 404

        # Load the trained model
        try:
            face_recognizer.read(model_path)
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return jsonify({"message": f"Error loading model: {str(e)}"}), 500

        # Decode the base64 photo data
        try:
            img_data = np.frombuffer(base64.b64decode(photo_data.split(",")[1]), dtype=np.uint8)
            img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"Error decoding base64 image: {str(e)}")
            return jsonify({"message": f"Error decoding image: {str(e)}"}), 400

        if img is None:
            return jsonify({"message": "Failed to decode image"}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({"message": "No face detected. Please try again."}), 400

        # Initialize a variable to track face recognition success
        face_recognized = False

        # Iterate over detected faces
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            label, confidence = face_recognizer.predict(face)

            print(f"Recognized label: {label}, Confidence: {confidence}")

            # Verify the label and confidence
            if confidence < 38 and label == int(roll_no):  # Directly compare with roll_no
                face_recognized = True
                break  # Stop once we find a match

        # Update attendance based on recognition result
        if face_recognized:
            # Save attendance record in the Attendance table
            new_attendance = Attendance(
                session_id=active_session.id,
                student_id=student.id,
                name=student.name,
                roll_number=student.roll_number,
                batch=student.batch,  # Assuming year represents batch
                status="Present",
                timestamp=datetime.now()
            )
            db.session.add(new_attendance)
            db.session.commit()
            return jsonify({"message": "Attendance Recorded"}), 200
        else:
            new_attendance.attendance_status = "absent"
            db.session.commit()
            return jsonify({"message": "Attendance Failed. Face not recognized."}), 400

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
