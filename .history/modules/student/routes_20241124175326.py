from flask import Blueprint, render_template,jsonify, request, redirect, url_for, flash
from flask_login import login_user,LoginManager, login_required, current_user,logout_user
from models import User
from . import student_bp
import cv2
import os
import base64
import numpy as np
from models import Student,db,AttendanceSession,AttendanceRecord
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
    
    return render_template('student_dashboard.html',student=student)

# Load Haar Cascade for face detection
cascade_path = 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Initialize LBPH Face Recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Base folder for storing user data
base_user_folder = "modules/developer/static/uploads/"

@student_bp.route('/recognize_face', methods=['POST'])
@login_required
def recognize_face():
    try:
        # Get data from the request
        session_id = request.json.get('session_id')
        photo_data = request.json.get('photoData')
        roll_no = request.json.get('rollNO')  # Roll number is unique for students

        if not session_id or not photo_data or not roll_no:
            return jsonify({'error': 'Session ID, photo data, and roll number are required'}), 400

        # Validate the active session
        session = AttendanceSession.query.filter_by(id=session_id, status='Active').first()
        if not session:
            return jsonify({'error': 'No active session found'}), 404

        # Fetch the student using roll number
        student = Student.query.filter_by(roll_number=roll_no).first()
        if not student or student.id != current_user.id:
            return jsonify({'error': 'Student not found or unauthorized access'}), 403

        # Validate that the student belongs to the session batch
        if student.batch != session.batch_id:
            return jsonify({'error': 'Student does not belong to this session batch'}), 403

        # Perform face recognition
        try:
            img_data = np.frombuffer(base64.b64decode(photo_data.split(",")[1]), dtype=np.uint8)
            img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
        except Exception as e:
            return jsonify({'error': f'Error decoding image: {str(e)}'}), 400

        if img is None:
            return jsonify({'error': 'Failed to decode image'}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({'error': 'No face detected. Please try again'}), 400

        # Initialize face recognition status
        face_recognized = False

        # Iterate through detected faces
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            label, confidence = face_recognizer.predict(face)

            # Validate if the recognized face matches the student roll number
            if confidence < 38 and label == int(roll_no):
                face_recognized = True
                break

        # Record attendance based on recognition result
        record = AttendanceRecord.query.filter_by(session_id=session_id, student_id=student.id).first()
        if not record:
            record = AttendanceRecord(
                session_id=session_id,
                student_id=student.id,
                status='Present' if face_recognized else 'Absent',
                recognized_time=datetime.utcnow() if face_recognized else None
            )
            db.session.add(record)
        else:
            # Update the record if it already exists
            record.status = 'Present' if face_recognized else 'Absent'
            record.recognized_time = datetime.utcnow() if face_recognized else None

        db.session.commit()

        return jsonify({
            'message': 'Attendance marked',
            'status': 'Present' if face_recognized else 'Absent'
        }), 200

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        db.session.rollback()  # Rollback in case of an error
        return jsonify({'error': f'Error: {str(e)}'}), 500
