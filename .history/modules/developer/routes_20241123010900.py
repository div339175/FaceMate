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


# Load Haar Cascade for face detection
cascade_path = 'modules/developer/haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Initialize LBPH Face Recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Base folder for storing user data
base_user_folder = "modules/developer/static/uploads/"

# Ensure the base folder exists
os.makedirs(base_user_folder, exist_ok=True)

# Function to get the folder path for a user
def get_user_folder(user_id):
    user_folder = os.path.join(base_user_folder, str(user_id))
    os.makedirs(user_folder, exist_ok=True)  # Create the user's folder if it doesn't exist
    return user_folder

@developer_bp.route('/save_photo_sample', methods=['POST'])
def save_photo():
    # Get form data sent from frontend
    roll_number = request.form['roll_number']
    name = request.form['name']
    photo_base64 = request.form['photo_base64']  # Get the base64 string for the photo
    photo_count = int(request.form['photo_count'])  # Photo count (just for tracking)

    # Create a folder for the student using roll number and name
    student_folder = os.path.join('modules/developer/static/uploads', f'{roll_number}_{name}')
    os.makedirs(student_folder, exist_ok=True)

    try:
        # Decode the base64 image (photo_base64 should be the actual base64 string)
        img_data = np.frombuffer(base64.b64decode(photo_base64.split(",")[1]), dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"message": "Failed to decode image"}), 400
        
        # Convert to grayscale and detect faces
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({"message": "No face detected. Please try again."}), 400

        # Save photo count and face images in 'photo_samples' folder
        photo_folder = os.path.join(student_folder, 'photo_samples')
        os.makedirs(photo_folder, exist_ok=True)
        
        # Save the face images (if faces detected)
        for idx, (x, y, w, h) in enumerate(faces):
            face = img[y:y+h, x:x+w]  # Crop the face from the image
            face_filename = os.path.join(photo_folder, f"face_{photo_count}_{idx}.jpg")
            cv2.imwrite(face_filename, face)  # Save the face image
            print(f"Saved face image to {face_filename}")

        return jsonify({'message': 'Photo samples saved successfully', 'photo_count': photo_count}), 200

    except Exception as e:
        print(f"Error saving photo: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500



@developer_bp.route('/train_data', methods=['POST'])
def train_classifier():
    try:

    # Get form data sent from frontend
        name = request.form['name']
        # photo_base64 = request.form['photo_base64']  # Get the base64 string for the photo
        # photo_count = int(request.form['photo_count'])
        # # Initialize the LBPH face recognizer
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        faces = []
        labels = []
        label_dict = {}

        # Get all student folders from the uploads directory
        student_folders = os.listdir('modules/developer/static/uploads')
        
        for folder in student_folders:
            student_folder = os.path.join('modules/developer/static/uploads', folder)
            photo_folder = os.path.join(student_folder, 'photo_samples')

            if os.path.isdir(photo_folder):
                for photo_file in os.listdir(photo_folder):
                    if photo_file.endswith(('.jpg', '.jpeg', '.png')):
                        img_path = os.path.join(photo_folder, photo_file)
                        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)  # Read image as grayscale
                        
                        # Assuming roll_number is the first part of the folder name (before '_')
                        roll_number = folder.split('_')[0]
                        
                        # Map roll number to a unique label
                        if roll_number not in label_dict:
                            label_dict[roll_number] = len(label_dict) + 1
                        
                        label = label_dict[roll_number]
                        
                        # Append the image and its label
                        faces.append(img)
                        labels.append(label)

        # If no faces were found, return an error
        if len(faces) == 0:
            return jsonify({'message': 'No faces found for training'}), 400

        # Train the recognizer with the collected faces and labels
        recognizer.train(faces, np.array(labels))

        # Create a folder for the student using roll number and name
        student_folder = os.path.join('modules/developer/static/uploads', f'{roll_number}_{name}')
        os.makedirs(student_folder, exist_ok=True)


        # Save the trained model to a file
        classifier_path = os.path.join(student_folder, 'classifier.xml')
        recognizer.save(classifier_path)

        return jsonify({'message': 'Classifier trained successfully', 'classifier_path': classifier_path}), 200

    
    except Exception as e:
        print(f"Error during training: {str(e)}")
        return jsonify({'message': f"Error during training: {str(e)}"}), 500
    
# # @developer_bp.route('/train_classifier', methods=['POST'])
# def train_classifier():
#     try:
#         # Initialize LBPH face recognizer
#         recognizer = cv2.face.LBPHFaceRecognizer_create()
#         faces = []
#         labels = []
#         label_dict = {}

#         # Iterate over all student folders
#         base_upload_path = 'modules/developer/static/uploads'
#         student_folders = [f for f in os.listdir(base_upload_path) if os.path.isdir(os.path.join(base_upload_path, f))]

#         for folder in student_folders:
#             student_folder = os.path.join(base_upload_path, folder)
#             photo_folder = os.path.join(student_folder, 'photo_samples')

#             if os.path.isdir(photo_folder):
#                 for photo_file in os.listdir(photo_folder):
#                     if photo_file.endswith(('.jpg', '.jpeg', '.png')):
#                         img_path = os.path.join(photo_folder, photo_file)
#                         img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)  # Read as grayscale

#                         if img is None:
#                             continue

#                         # Extract roll number from folder name
#                         roll_number = folder.split('_')[0]

#                         # Assign unique labels for roll numbers
#                         if roll_number not in label_dict:
#                             label_dict[roll_number] = len(label_dict) + 1

#                         faces.append(img)
#                         labels.append(label_dict[roll_number])

#         # Check if there are faces to train
#         if len(faces) == 0:
#             return jsonify({'message': 'No faces found for training'}), 400

#         # Train the recognizer
#         recognizer.train(faces, np.array(labels))

#         # Save the trained model to a shared folder
#         classifier_path = os.path.join('modules/developer/static/uploads', 'trained_classifier.xml')
#         recognizer.save(classifier_path)

#         return jsonify({'message': 'Classifier trained successfully', 'classifier_path': classifier_path}), 200

#     except Exception as e:
#         print(f"Error during training: {str(e)}")
#         return jsonify({'message': f"Error during training: {str(e)}"}), 500


# Load Haar Cascade for face detection
cascade_path = 'modules/developer/haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Initialize LBPH Face Recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Base folder for storing user data
PHOTO_DIR ="modules/developer/static/uploads/"
# Ensure the base folder exists
os.makedirs(PHOTO_DIR, exist_ok=True)

# Route to save captured photo samples
@developer_bp.route('/developer/save-photo', methods=['POST'])
def save_photo():
    data = request.get_json()
    photo_data = data.get('photoData')
    roll_no = data.get('rollNo')

    if not roll_no or not photo_data:
        return jsonify({'message': 'Roll number or photo data is missing!'}), 400

    photo_folder = os.path.join(PHOTO_DIR, roll_no)
    if not os.path.exists(photo_folder):
        os.makedirs(photo_folder)
    try:
        # Convert base64 to image
        img_data = photo_data.split(',')[1]
        img_bytes = np.frombuffer(base64.b64decode(img_data), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"message": "Failed to decode image"}), 400
        
        # Convert to grayscale and detect faces
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({"message": "No face detected. Please try again."}), 400
        
        # Save photo count and face images in 'photo_samples' folder
        photo_folder = os.path.join(PHOTO_DIR,'photo_samples')
        os.makedirs(photo_folder, exist_ok=True)
            
        # Save the face images (if faces detected)
        for idx, (x, y, w, h) in enumerate(faces):
            face = img[y:y+h, x:x+w]  # Crop the face from the image
            face_filename = os.path.join(photo_folder, f"face_{len(os.listdir(photo_folder)) + 1}.jpg")
            cv2.imwrite(face_filename, face)  # Save the face image
            print(f"Saved face image to {face_filename}")

        return jsonify({'message': 'Photo saved successfully.'}), 200
    except Exception as e:
        print(f"Error saving photo: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

# Route to train the model
@developer_bp.route('/developer/train-data', methods=['POST'])
def train_data():
    data = request.get_json()
    photo_data = data.get('photoData')
    roll_no = data.get('rollNo')
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    detector = cv2.CascadeClassifier(cascade_path)
    faces = []
    labels = []

    # Iterate over all students' photos
    for folder_name in os.listdir(PHOTO_DIR):
        folder_path = os.path.join(PHOTO_DIR, folder_name)
        if os.path.isdir(folder_path):
            for img_name in os.listdir(folder_path):
                img_path = os.path.join(folder_path, img_name)
                img = cv2.imread(img_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # Detect faces
                faces_detected = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                for (x, y, w, h) in faces_detected:
                    faces.append(gray[y:y+h, x:x+w])
                    labels.append(int(folder_name))  # Roll number is used as label

    if faces and labels:
        recognizer.train(faces, np.array(labels))
        # Create a folder for the student using roll number and name
        model_path = os.path.join('modules/developer/static/uploads', f'{roll}')
        os.makedirs(model_path, exist_ok=True)
        # Save the trained model to a file
        classifier_path = os.path.join(model_path, 'classifier.xml')
        
        # model_path = os.path.join(MODEL_DIR, 'classifier.xml')
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
