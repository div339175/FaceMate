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
    csv_file = f"attendance_session_{session_id}.csv"
    
    if not os.path.exists(csv_file):  # Avoid overwriting if it already exists
        students = Student.query.filter_by(batch=batch_id).all()
        
        with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Roll Number", "Name", "Batch", "Photo", "Attendance Status"])  # Header
            
            for student in students:
                writer.writerow([
                    student.roll_number,
                    student.name,
                    student.batch,
                    os.path.join(base_user_folder, student.roll_number, f"{student.roll_number}.jpg"),  # Photo path
                    "Absent"  # Default status
                ])
    
    return csv_file


import pandas as pd

def update_csv_attendance(csv_file, roll_no):
    # Load CSV into a DataFrame
    df = pd.read_csv(csv_file)
    
    # Find the student by roll number
    student_row = df[df["Roll Number"] == roll_no]
    if not student_row.empty:
        # Update attendance status to "Present"
        df.loc[df["Roll Number"] == roll_no, "Attendance Status"] = "Present"
        
        # Save the updated DataFrame back to CSV
        df.to_csv(csv_file, index=False)
        return True
    else:
        return False


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

# Get the student record based on roll number and logged-in user email
        student = Student.query.filter_by(email=current_user.email, roll_number=roll_no).first()
        if not student:
            return jsonify({"message": "Student not found"}), 404

        student_course = StudentCourse.query.filter_by(roll_number=roll_no).first()
        if not student_course:
            return jsonify({"message": "Course not found"}), 404

        # Check for an active session
        active_session = AttendanceSession.query.filter(
            AttendanceSession.active == True,  # Only active sessions
            AttendanceSession.batch_id == student.batch,  # Match the student's batch
            AttendanceSession.course_id.in_(
                        db.session.query(StudentCourse.course_code).filter(StudentCourse.roll_number == roll_no)
            )
        ).first()
        
        if not active_session:
            print(f"No active session found for batch {student.batch} and roll number {roll_no}.")
            return jsonify({"message": f"No active attendance session available for your batch ({student.batch}) and course."}), 400


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
