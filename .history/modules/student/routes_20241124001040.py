from flask import Blueprint, render_template,jsonify, request, redirect, url_for, flash
from flask_login import login_user,LoginManager, login_required, current_user,logout_user
from models import User
from . import student_bp
import cv2
import os
import base64
import numpy as np
from models import Student,db


<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Dashboard</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            display: flex;
        }
        
        .sidebar {
            width: 250px;
            background: #333;
            color: #fff;
            height: 100vh;
            position: fixed;
            left: -250px;
            transition: left 0.3s ease;
            padding: 10px;
        }
        
        .sidebar ul {
            list-style: none;
            padding: 0;
        }
        
        .sidebar ul li {
            margin: 10px 0;
        }
        
        .sidebar ul li a {
            color: #fff;
            text-decoration: none;
        }
        
        .content {
            margin-left: 0;
            padding: 20px;
            transition: margin-left 0.3s ease;
            flex: 1;
        }
        
        .sidebar.open {
            left: 0;
        }
        
        .content.open {
            margin-left: 250px;
        }

        /* Arrow button styles */
        .toggle-arrow {
            position: absolute;
            top: 50%;
            right: -30px; /* Adjust this to position the arrow correctly */
            transform: translateY(-50%);
            background-color: #333;
            color: white;
            border: none;
            padding: 10px;
            cursor: pointer;
            font-size: 20px;
            border-radius: 50%;
        }

        .toggle-arrow:hover {
            background-color: #444;
        }

        .toggle-arrow.open {
            transform: translateY(-50%) rotate(180deg); /* Rotate arrow when sidebar is open */
        }
    </style>
</head>
<body>
    <!-- Toggle button for the sidebar -->
    <button class="toggle-btn" onclick="toggleSidebar()">☰</button>

    <div class="sidebar" id="sidebar">
        <ul>
            <li><a href="#">Profile</a></li>
            <li><a href="#">Settings</a></li>
            <li><a href="{{ url_for('student.logout') }}">Logout</a></li>
        </ul>
        <button onclick="showStudentDetails()">Student Details</button>
        <button onclick="showAttendance()">Attendance</button>
    </div>
    <script>

        // Function to toggle sidebar
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const content = document.getElementById('content');
            sidebar.classList.toggle('active');
            content.classList.toggle('expanded');
        }

        function showStudentDetails() {
            document.getElementById("content").innerHTML = `

            <div class="content" id="content">
                <h1>Welcome, {{ student.name }}</h1>
                <p><strong>Email:</strong> {{ student.email }}</p>
                <p><strong>Roll Number:</strong> {{ student.roll_number }}</p>
                <p><strong>Enrollment Number:</strong> {{ student.enrollment_number }}</p>
                <p><strong>Year:</strong> {{ student.year }}</p>
                <p><strong>Semester:</strong> {{ student.semester }}</p>
                {% if student.photo %}
                <img src="{{ url_for('static', filename='uploads/' + student.photo) }}" alt="Profile Photo" style="width: 150px; height: 150px;">
                {% endif %}
            </div>
         `;
        }
        const studentRollNo = "{{ student.roll_number }}"; // Pass roll number from backend to template

        // Function to load attendance options
        function showAttendance() {
            document.getElementById("content").innerHTML = `
                <style>
                     body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        background-color: #fff;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        text-align: center;
                        width: 60%;
                    }
                    video {
                        width: 100%;
                        border-radius: 8px;
                        display: none;
                    }
                    button {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        margin: 10px;
                        font-size: 16px;
                    }
                    button:hover {
                        background-color: #45a049;
                    }
                    #statusMessage {
                        margin-top: 15px;
                        font-size: 18px;
                    }
                </style>
                <div class="container">
                <h2>Face Recognition Attendance</h2>
                <video id="cameraFeed" autoplay></video>
               <button id="recognizeBtn">Start Recognition</button>
                <button id="stopRecognitionBtn" style="display: none;">Stop Recognition</button>
                <p id="statusMessage"></p>
            </div>
                
            `;

            initializeAttendanceFunctions(studentRollNo);
        }

        // Initialize camera and attendance functions
        function initializeAttendanceFunctions(rollNo) {
            
            let recognitionStream = null;
            let recognitionInterval = null;


            document.getElementById("recognizeBtn").addEventListener("click", async () => {
                const video = document.getElementById("cameraFeed");
                video.style.display = "block";
                document.getElementById("stopRecognitionBtn").style.display = "block";
            
                try {
                    recognitionStream = await navigator.mediaDevices.getUserMedia({ video: true });
                    video.srcObject = recognitionStream;
            
                    recognitionInterval = setInterval(async () => {
                        const canvas = document.createElement("canvas");
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        canvas.getContext("2d").drawImage(video, 0, 0);
            
                        const photoData = canvas.toDataURL("image/jpeg");
            
                        try {
                            const response = await fetch('/student/recognize', {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({  rollNO: rollNo, photoData})
                            });
            
                            const result = await response.json();
                            document.getElementById("statusMessage").innerText = result.message;
            
                            if (result.message === "Attendance Recorded") {
                                // Stop the recognition
                                clearInterval(recognitionInterval);
                                video.style.display = "none";
                                recognitionStream.getTracks().forEach(track => track.stop());
                                document.getElementById("stopRecognitionBtn").style.display = "none";
            
                                alert("Attendance has been recorded.");
                            }
                        } catch (error) {
                            console.error("Error recognizing face:", error);
                        }
                    }, 1000);
                } catch (error) {
                    console.error("Error starting recognition:", error);
                    alert("Error starting recognition: " + error.message);
                }
            });
            
            document.getElementById("stopRecognitionBtn").addEventListener("click", () => {
                clearInterval(recognitionInterval);
                const video = document.getElementById("cameraFeed");
                video.style.display = "none";
                if (recognitionStream) recognitionStream.getTracks().forEach(track => track.stop());
                document.getElementById("statusMessage").innerText = "Face recognition stopped.";
                document.getElementById("stopRecognitionBtn").style.display = "none";
            });
            
            function stopVideoStream() {
                const video = document.getElementById("cameraFeed");
                video.style.display = "none";
                if (window.stream) {
                    window.stream.getTracks().forEach(track => track.stop());
                    window.stream = null;
                }
            }
            
            window.addEventListener("beforeunload", () => {
                if (window.stream) {
                    window.stream.getTracks().forEach(track => track.stop());
                }
            });
            
        }

        // Run the default view when the page loads
        showStudentDetails();
    </script>
</body>
</html>

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
base_user_folder = "modules/student/static/uploads/"

@student_bp.route('/recognize', methods=['POST'])
def recognize_face():
    try:
        data = request.get_json()
        photo_data = data.get('photoData')
        roll_no = data.get('rollNO')  # Using roll number from the request data

        if not photo_data or not roll_no:
            return jsonify({"message": "Photo data or Roll Number is missing"}), 400

        # Get the student record based on roll number and logged-in user email
        student = Student.query.filter_by(email=current_user.email, roll_number=roll_no).first()
        if not student:
            return jsonify({"message": "Student not found"}), 404

        # Check if the model exists for the student
        model_path = os.path.join(base_user_folder, roll_no, f"classifier_{roll_no}.yml")
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

        # Initialize a variable to track face recognition success
        face_recognized = False

        # Iterate over detected faces
        for (x, y, w, h) in faces:
            face = gray[y:y + h, x:x + w]
            label, confidence = face_recognizer.predict(face)

            print(f"Recognized label: {label}, Confidence: {confidence}")

            # Verify the label and confidence
            if confidence < 38 and label == int(roll_no):  # Directly compare with roll_no
                face_recognized = True
                break  # Stop once we find a match

        # Update attendance based on recognition result
        if face_recognized:
            student.attendance_status = "present"
            db.session.commit()
            return jsonify({"message": "Attendance Recorded"}), 200
        else:
            student.attendance_status = "absent"
            db.session.commit()
            return jsonify({"message": "Attendance Failed. Face not recognized."}), 400

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500

    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return jsonify({"message": f"Error: {str(e)}"}), 500
