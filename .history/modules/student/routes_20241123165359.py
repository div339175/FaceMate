from flask import Blueprint, render_template,js request, redirect, url_for, flash
from flask_login import login_user,LoginManager, login_required, current_user
from models import User
from . import student_bp

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
    return render_template('student_dashboard.html')

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
