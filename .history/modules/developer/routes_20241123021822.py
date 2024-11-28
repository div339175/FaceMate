# modules/developer/routes.py
import cv2
from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify
from flask_login import logout_user,login_user, login_required, current_user
from models import Developer,Teacher,Student,db,User
from . import developer_bp
from werkzeug.utils import secure_filename
import os
import base64
import numpy as np
# from werkzeug.security import generate_password_hash  # For hashing passwords

@developer_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email,role='developer').first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('developer.developer_dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('d_login.html')

@developer_bp.route('/dashboard')
@login_required
def developer_dashboard():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    return render_template('developer_dashboard.html')

# Route to register a new student
@developer_bp.route('/register_student', methods=['GET', 'POST'])
@login_required
def register_student():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        roll_number = request.form['roll_number']
        enrollment_number = request.form['enrollment_number']
        year = request.form['year']
        semester = request.form['semester']
        photo = request.files['photo']

 # Hash the password
        # hashed_password = generate_password_hash(password, method='sha256')
       
       # Save user information to the User table
        new_user = User(email=email, password=password, role='student')
        db.session.add(new_user)
        db.session.commit()  # Commit to get the new_user ID
        
        
        # Save student information to the Student table
        new_student = Student(
            name=name,
            email=email,
            roll_number=roll_number,
            enrollment_number=enrollment_number,
            year=year,
            semester=semester,
            photo=photo.filename,  # Save the filename
            user_id=new_user.id  # Associate with the User table using the ID
        )
        db.session.add(new_student)
        db.session.commit()  # Commit the new student data
        
        # Optionally, save the photo file
        if photo:
            photo.save(f'static/uploads/{photo.filename}')
        
        # # Check if a student with the same email already exists
        # if User.query.filter_by(email=email).first():
        #     flash('Email already registered', 'danger')
        # else:
        #     new_student = Student(name=name, email=email, password=password, role='student')
        #     db.session.add(new_student)
        #     db.session.commit()
            flash('Student registered successfully', 'success')
            # Log out the current user (so they can log in again)
            logout_user()
            return redirect(url_for('developer.developer_dashboard'))
    
    return render_template('register_student.html')

@developer_bp.route('/submit-photo-sample')
def submit_photo_sample():
    return render_template('submit_photo_sample.html')

# Load Haar Cascade for face detection
cascade_path = 'modules/developer/haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)
if face_cascade.empty():
    raise IOError("Failed to load Haar Cascade XML file.")

# Initialize LBPH Face Recognizer
PHOTO_DIR = "modules/developer/static/uploads/"
os.makedirs(PHOTO_DIR, exist_ok=True)


@developer_bp.route('/save-photo', methods=['POST'])
def save_photo():
    data = request.get_json()
    photo_data = data.get('photoData')
    roll_no = data.get('rollNo')

# Create a folder for the student using roll number and name
    student_folder = os.path.join('modules/developer/static/uploads', f'{}')
    os.makedirs(student_folder, exist_ok=True)

    if not roll_no or not photo_data:
        return jsonify({'message': 'Roll number or photo data is missing!'}), 400

    try:
        # Decode base64 to image
        img_data = photo_data.split(',')[1]
        img_bytes = np.frombuffer(base64.b64decode(img_data), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"message": "Failed to decode image"}), 400

        # # Convert to grayscale and detect faces
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({"message": "No face detected. Please try again."}), 400

        # Save detected faces
        photo_folder = os.path.join(PHOTO_DIR, roll_no)
        os.makedirs(photo_folder, exist_ok=True)

        for idx, (x, y, w, h) in enumerate(faces):
            face = gray[y:y + h, x:x + w]  # Crop the face
            face_filename = os.path.join(photo_folder, f"face_{len(os.listdir(photo_folder)) + 1}.jpg")
            cv2.imwrite(face_filename, face)

        return jsonify({'message': 'Photo saved successfully.'}), 200
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


@developer_bp.route('/train-data', methods=['POST'])
def train_data():
    data = request.get_json()
    roll_no = data.get('rollNo')

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    detector = cv2.CascadeClassifier(cascade_path)

    faces, labels = [], []
    for folder_name in os.listdir(PHOTO_DIR):
        if roll_no and folder_name != roll_no:
            continue  # Skip folders not matching the roll number
        folder_path = os.path.join(PHOTO_DIR, folder_name)
        if os.path.isdir(folder_path):
            for img_name in os.listdir(folder_path):
                img_path = os.path.join(folder_path, img_name)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

                # Detect faces
                faces_detected = detector.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                for (x, y, w, h) in faces_detected:
                    faces.append(img[y:y + h, x:x + w])
                    labels.append(int(folder_name))  # Use roll_no as label

    if faces and labels:
        recognizer.train(faces, np.array(labels))
        model_path = os.path.join(PHOTO_DIR, roll_no)
        os.makedirs(model_path, exist_ok=True)
        classifier_path = os.path.join(model_path, 'classifier.xml')
        recognizer.save(classifier_path)

        return jsonify({'message': 'Model trained and saved successfully.'}), 200
    else:
        return jsonify({'message': 'No faces detected for training.'}), 400

# Route to register a new teacher
@developer_bp.route('/register_teacher', methods=['GET', 'POST'])
@login_required
def register_teacher():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if a teacher with the same email already exists
        if Developer.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            new_teacher = Teacher(name=name, email=email, password=password, role='teacher')
            db.session.add(new_teacher)
            db.session.commit()
            flash('Teacher registered successfully', 'success')
            logout_user() 
            return redirect(url_for('developer.developer_dashboard'))
    
    return render_template('register_teacher.html')
