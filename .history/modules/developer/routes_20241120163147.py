# modules/developer/routes.py
import cv2
from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify
from flask_login import logout_user,login_user, login_required, current_user
from models import Developer,Teacher,Student,db,User
from . import developer_bp
from werkzeug.utils import secure_filename
import os
import base64
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


@developer_bp.route('/save_photo_sample', methods=['POST'])
def save_photo_sample():
    photo_data = request.form['photo']
    roll_number = request.form['roll_number']
    name = request.form['name']

    # Create a folder for the student using roll number and name
    student_folder = os.path.join('static/uploads', roll_number + '_' + name)
    os.makedirs(student_folder, exist_ok=True)
    
    # Save the photo as an image
    photo_data = photo_data.split(',')[1]  # Remove data URL prefix
    photo_filename = f"{roll_number}_{name}_{photo_count}.jpg"
    photo_path = os.path.join(student_folder, 'photo_samples', photo_filename)
    
    # Save the image to the file system
    with open(photo_path, 'wb') as photo_file:
        photo_file.write(base64.b64decode(photo_data))
    
    return jsonify({'message': 'Photo saved successfully'}), 200

@developer_bp.route('/train_classifier', methods=['POST'])
def train_classifier():
    # Train the classifier using the saved images
    # Assuming you have a folder with images stored in photo_samples

    student_folders = os.listdir('static/uploads')
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []

    for folder in student_folders:
        photo_folder = os.path.join('static/uploads', folder, 'photo_samples')
        if os.path.isdir(photo_folder):
            for photo_file in os.listdir(photo_folder):
                img = cv2.imread(os.path.join(photo_folder, photo_file), cv2.IMREAD_GRAYSCALE)
                label = folder.split('_')[0]  # Roll number as label
                faces.append(img)
                labels.append(int(label))

    recognizer.train(faces, np.array(labels))

    # Save the classifier
    classifier_path = os.path.join('static/uploads', 'classifier.xml')
    recognizer.save(classifier_path)
    
    return jsonify({'message': 'Classifier trained successfully'}), 200

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
