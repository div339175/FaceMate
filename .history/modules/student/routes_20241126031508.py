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
import csv

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

@student_bp.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('home'))

    # Get the logged-in student's details
    student = Student.query.filter_by(email=current_user.email).first()
    if not student:
        flash('Student details not found. Please contact support.', 'danger')
        return redirect(url_for('student.login'))

    # Fetch active sessions for the student's courses and batch
    active_sessions = AttendanceSession.query.filter(
        AttendanceSession.active == True,  # Only active sessions
        AttendanceSession.batch_id == student.batch,  # Match the student's batch
        AttendanceSession.course_id.in_(
            db.session.query(StudentCourse.course_code).filter(StudentCourse.roll_number == student.roll_number)
        )
    ).all()

    # Define `active_session` (True if there are active attendance sessions)
    active_session = len(active_sessions) > 0

     # Pass data directly to the template
    return render_template(
        'student_dashboard.html',
        student=student,
        active_sessions=[
            {
                'course_name': Course.query.filter_by(code=session.course_id).first().name,
                'course_code': session.course_id,
                'start_time': session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                'end_time': session.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                'session_id': session.session_id,
                'active_session': session.active
            }
            for session in active_sessions
        ],
        active_session=active_session  # Ensure this is passed to the template
    )

# Create a CSV file for attendance
def create_csv(session_id, batch_id):
    filename = f"attendance_{session_id}_{batch_id}.csv"
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Roll Number", "Name", "Batch", "Photo Path", "Attendance Status"])
    return filename

# Update CSV with recognized students
def update_csv(filename, student_data):
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(student_data)

# Load Haar Cascade for face detection
cascade_path = 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Initialize LBPH Face Recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Base folder for storing user data
base_user_folder = "modules/developer/static/uploads/"

@student_bp.route('/recognize', methods=['POST'])
def recognize_faces(session_id, batch_id):
    csv_file = create_csv(session_id, batch_id)
    
    try:
        data = request.get_json()
        photo_data = data.get('photoData')
        roll_no = data.get('rollNO')

        if not photo_data or not roll_no:
            return jsonify({"message": "Photo data or Roll Number is missing"}), 400

        # Fetch and validate student, session, and model as in original code...

        # Face recognition logic...
        face_recognized = False
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            label, confidence = face_recognizer.predict(face)

            if confidence < 60 and label == int(roll_no):
                face_recognized = True
                break

        if face_recognized:
            if update_csv_attendance(csv_file, roll_no):
                return jsonify({"message": "Attendance updated to Present"}), 200
            else:
                return jsonify({"message": "Student not found in CSV"}), 404
        else:
            return jsonify({"message": "Face not recognized"}), 400

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
