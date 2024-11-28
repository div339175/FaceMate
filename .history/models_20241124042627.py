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
    attendance_status = db.Column(db.String(10), nullable=True) 

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    course= db.Column(db.String(120), nullable=False)
    photo = db.Column(db.String(150), nullable=True)

# New AttendanceSession model
class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(50), nullable=False)  # References batch info in the Student model
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Enum('Active', 'Closed', name='session_status'), default='Active')

    # Relationships
    records = db.relationship('AttendanceRecord', backref='session', lazy=True)

# New AttendanceRecord model
class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
        roll_number = db.Column(db.String(50), unique=True,nullable=False)

    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    status = db.Column(db.Enum('Present', 'Absent', name='attendance_status'), nullable=False)
    recognized_time = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    student = db.relationship('Student', backref='attendance_records')