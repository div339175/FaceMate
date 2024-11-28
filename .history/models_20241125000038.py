from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
# Define db instance
db = SQLAlchemy()  # Define db without app passed in directly here

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Developer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    roll_number = db.Column(db.String(50), unique=True,nullable=False)
    enrollment_number = db.Column(db.String(50),unique=True, nullable=False)
    year = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(150), nullable=True)
    # attendance_status = db.Column(db.String(10), nullable=True) 
    course = db.Column(db.String(150), nullable=True)
    course = db.Column(db.String(150), nullable=True)


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    course= db.Column(db.String(120), nullable=False)
    photo = db.Column(db.String(150), nullable=True)
     # Relationship to AttendanceSession
    sessions = db.relationship('AttendanceSession', backref='teacher', lazy=True)
    
class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique session ID
    session_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique identifier for the session
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)  # Link to the teacher
    course_id = db.Column(db.String(120), nullable=False)  # Course for the session
    start_time = db.Column(db.DateTime, nullable=False)  # Session start time
    end_time = db.Column(db.DateTime, nullable=False)  # Session end time
    active = db.Column(db.Boolean, default=True)  # Whether the session is active

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_session.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    batch = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

