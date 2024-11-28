# modules/developer/routes.py
import cv2
from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify
from flask_login import logout_user,login_user, login_required, current_user
from models import Developer,Course,Teacher,Student,db,User,StudentCourse
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
        batch=request.form['batch']
        year = request.form['year']
        semester = request.form['semester']
        photo = request.files['photo']
        course_ids = request.form['courses']  # JSON string of course IDs
        
         # Parse course IDs
        selected_course_ids = []
        if course_ids:
            selected_course_ids = [int(course_id) for course_id in eval(course_ids)]


        new_user = User(email=email, password=password, role='student')
        db.session.add(new_user)
        db.session.commit()  # Commit to get the new_user ID
        
        
        # Save student information to the Student table
        new_student = Student(
            name=name,
            email=email,
            roll_number=roll_number,
            batch=batch,
            enrollment_number=enrollment_number,
            year=year,
            semester=semester,
            photo=photo.filename,  # Save the filename
        )
        
        db.session.add(new_student)
        db.session.commit()
        # Add selected courses
        for course_id in selected_course_ids:
            course = Course.query.get(course_id)
            if course:
                student_course = StudentCourse(
                    roll_number=roll_number,
                    course_name=course.name,
                     course_code=course.code
                )
                db.session.add(student_course)

        db.session.commit()

        if photo:
            photo.save(f'static/uploads/{photo.filename}')
        
        flash('Student registered successfully', 'success')
        # Log out the current user (so they can log in again)
        logout_user()
        return redirect(url_for('developer.developer_dashboard'))
    
    return render_template('register_student.html')


@developer_bp.route('/search_courses', methods=['GET'])
def search_courses():
    query = request.args.get('q', '').lower()
    courses = Course.query.filter(Course.name.ilike(f"%{query}%")).all()
    return jsonify([{'id': course.id, 'name': course.name, 'code': course.code} for course in courses])

@developer_bp.route('/submit-photo-sample')
def submit_photo_sample():
    return render_template('submit_photo_sample.html')

# Load Haar Cascade for face detection
cascade_path = 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

if face_cascade.empty():
    raise IOError("Failed to load Haar Cascade XML file.")

# # Initialize LBPH Face Recognizer
# PHOTO_DIR = "modules/developer/static/uploads/"
# os.makedirs(PHOTO_DIR, exist_ok=True)


@developer_bp.route('/save-photo', methods=['POST'])
def save_photo():
    data = request.get_json()
    photo_data = data.get('photoData')
    roll_no = data.get('rollNo')

# Create a folder for the student using roll number and name
    student_folder = os.path.join('modules/developer/static/uploads', f'{roll_no}')
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
        photo_folder = os.path.join(student_folder,'photo_samples')
        os.makedirs(photo_folder, exist_ok=True)

        for idx, (x, y, w, h) in enumerate(faces):
            face = gray[y:y + h, x:x + w]  # Crop the face
            face_filename = os.path.join(photo_folder, f"face_{len(os.listdir(photo_folder)) + 1}.jpg")
            cv2.imwrite(face_filename, face)

        return jsonify({'message': 'Photo saved successfully.'}), 200
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


@developer_bp.route('/trainData', methods=['POST'])
def train():
    try:
        data = request.get_json()
        roll_no = data.get('rollNo')

        if not roll_no:
            return jsonify({"message": "Roll number is missing!"}), 400

        # Path to student's photo samples
        student_folder = os.path.join('modules/developer/static/uploads', roll_no, 'photo_samples')

        if not os.path.exists(student_folder):
            return jsonify({"message": f"No photo samples found for Roll No: {roll_no}."}), 400

        # Prepare training data
        images = []
        labels = []
        for img_file in os.listdir(student_folder):
            if img_file.endswith(".jpg"):
                img_path = os.path.join(student_folder, img_file)
                gray_image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if gray_image is not None:
                    images.append(gray_image)
                    labels.append(int(roll_no))  # Use Roll No as the label

        if not images:
            return jsonify({"message": "No valid images found for training."}), 400

        # Train the LBPH model
        face_recognizer.train(images, np.array(labels))

        # Save the trained model
        model_path = os.path.join('modules/developer/static/uploads', roll_no, f"{roll_no}_model.yml")
        face_recognizer.save(model_path)

        return jsonify({"message": f"Training completed. Model saved at {model_path}."}), 200
    except Exception as e:
        return jsonify({"message": f"Error during training: {str(e)}"}), 500

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
        course = request.form['course']
        photo = request.files['photo']

        # Check if a user with the same email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            try:
                # Save user information to the User table
                new_user = User(email=email, password=password, role='teacher')
                db.session.add(new_user)
                db.session.commit()  # Commit to generate the new_user ID

                # Save photo file if uploaded
                photo_filename = None
                if photo:
                    photo_filename = secure_filename(photo.filename)
                    photo_path = os.path.join('static/uploads/',photo_filename)

                    photo.save(photo_path)  # Save the file to the designated directory

                # Save teacher information to the Teacher table
                new_teacher = Teacher(
                    name=name,
                    email=email,
                    course=course,
                    photo=photo_filename
                )
                db.session.add(new_teacher)
                db.session.commit()

                flash('Teacher registered successfully', 'success')
                logout_user()  # Log out after successful registration
                return redirect(url_for('developer.developer_dashboard'))
            except Exception as e:
                db.session.rollback()  # Rollback if an error occurs
                flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('register_teacher.html')