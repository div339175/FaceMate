from flask import Blueprint, render_template,jsonify, request, redirect, url_for, flash
from flask_login import login_user,LoginManager, login_required, current_user
from models import User
from . import student_bp
import cv2
import os
import base64
import numpy as np
from models import Student

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
base_user_folder = "modules/student/static/uploads/"

# Route to recognize face for attendance
@student_bp.route('/recognize', methods=['POST'])
def recognize_face():
    try:
        data = request.get_json()
        photo_data = data.get('photoData')
        roll_no = data.get('rollNO')  # Using userID from the request data

        if not photo_data or not roll_no:
            return jsonify({"message": "Photo data or User ID is missing"}), 400

        # Get the student record based on roll number and logged-in user email
        student = Student.query.filter_by(email=current_user.email, roll_number=roll_no).first()
        if not student:
            return jsonify({"message": "Student not found"}), 404


        # Check if the model exists
        model_path = os.path.join(base_user_folder(roll_no), f"classifier_{roll_no}.yml")
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

        # Iterate over detected faces
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            label, confidence = face_recognizer.predict(face)

            print(f"Recognized label: {label}, Confidence: {confidence}")

            # Verify the label and confidence
            if confidence <38 and label == int(roll_no):  # Directly compare with user_id
                return jsonify({"message": "Attendance Recorded"}), 200
        
        return jsonify({"message": "Face not recognized. Ensure you are the correct user."}), 400

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500