from flask import render_template, request, jsonify, redirect, url_for
from . import student_bp
import os
import numpy as np
import cv2
import base64
from PIL import Image

# Load Haar Cascade for face detection
cascade_path = 'modules/student/haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Initialize LBPH Face Recognizer
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

# Base folder for storing user data
base_user_folder = "modules/student/static/uploads/"

# Ensure the base folder exists
os.makedirs(base_user_folder, exist_ok=True)

# Function to get the folder path for a user
def get_user_folder(user_id):
    user_folder = os.path.join(base_user_folder, str(user_id))
    os.makedirs(user_folder, exist_ok=True)  # Create the user's folder if it doesn't exist
    return user_folder

# Route to register or login
@student_bp.route('/login')
def login():
    return render_template('login.html')

@student_bp.route('/register')
def register():
    return render_template('register.html')

@student_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Route to save photo samples
@student_bp.route('/take_photo', methods=['POST'])
def save_photo():
    data = request.get_json()
    photo_data = data.get('photoData')
    user_id = data.get('userID')  # Using userID from the request data

    if not photo_data or not user_id:
        return jsonify({"message": "Photo data or User ID is missing"}), 400

    try:
        # Decode the base64 image
        img_data = np.frombuffer(base64.b64decode(photo_data.split(",")[1]), dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"message": "Failed to decode image"}), 400

        # Convert to grayscale and detect faces
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) == 0:
            return jsonify({"message": "No face detected. Please try again."}), 400

        # Get the user-specific folder
        user_folder = get_user_folder(user_id)
        photo_samples_folder = os.path.join(user_folder, "photo_samples")
        os.makedirs(photo_samples_folder, exist_ok=True)

        # Save the photo with a unique name
        photo_path = os.path.join(photo_samples_folder, f"photo_{len(os.listdir(photo_samples_folder)) + 1}.jpg")
        cv2.imwrite(photo_path, img)

        return jsonify({"message": "Photo saved successfully"}), 200

    except Exception as e:
        print(f"Error saving photo: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

# Route to train data for a user
@student_bp.route('/train_data', methods=['POST'])
def train_data():
    data = request.get_json()
    user_id = data.get('userID')  # Using userID from the request data

    if not user_id:
        return jsonify({"message": "User ID is missing"}), 400

    user_folder = f"modules/student/static/uploads/{user_id}/photo_samples"
    if not os.path.exists(user_folder):
        return jsonify({"message": "No photo samples found for this User ID"}), 404

    try:
        images = []
        labels = []

        # Loop through each photo sample for the user
        for file_name in os.listdir(user_folder):
            image_path = os.path.join(user_folder, file_name)
            img = cv2.imread(image_path)
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            for (x, y, w, h) in faces:
                face = gray[y:y + h, x:x + w]
                images.append(face)
                labels.append(int(user_id))  # Use user_id as the label

        if len(images) == 0:
            return jsonify({"message": "No valid faces found in the photo samples"}), 400

        # Train the recognizer with the collected faces and labels
        face_recognizer.train(images, np.array(labels))

        # Save the trained model
        model_path = f"modules/student/static/uploads/{user_id}/classifier_{user_id}.xml"
        face_recognizer.save(model_path)

        return jsonify({"message": "Training data successfully saved"}), 200

    except Exception as e:
        print(f"Error training data: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

# Route to recognize face for attendance
@student_bp.route('/recognize', methods=['POST'])
def recognize_face():
    try:
        data = request.get_json()
        photo_data = data.get('photoData')
        user_id = data.get('userID')  # Using userID from the request data

        if not photo_data or not user_id:
            return jsonify({"message": "Photo data or User ID is missing"}), 400

        # Check if the model exists
        model_path = os.path.join(get_user_folder(user_id), f"classifier_{user_id}.xml")
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
            if confidence <38 and label == int(user_id):  # Directly compare with user_id
                return jsonify({"message": "Attendance Recorded"}), 200

        return jsonify({"message": "Face not recognized. Ensure you are the correct user."}), 400

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500











# project_folder/
# │
# ├── app.py
# ├── config.py
# ├── extensions.py
# ├── models.py
# │
# ├── modules/
# │   ├── developer/
# │   │   ├── __init__.py
# │   │   ├── routes.py
# │   │   └── templates/
# │   │       ├── developer_dashboard.html
# │   │       └── login.html
# │   │
# │   ├── student/
# │   │   ├── __init__.py
# │   │   ├── routes.py
# │   │   └── templates/
# │   │       ├── student_dashboard.html
# │   │       └── login.html
# │   │
# │   ├── teacher/
# │   │   ├── __init__.py
# │   │   ├── routes.py
# │   │   └── templates/
# │   │       ├── teacher_dashboard.html
# │   │       └── login.html
# │
# └── templates/
#     ├── home.html
