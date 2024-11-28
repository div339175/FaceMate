from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Define db instance
db = SQLAlchemy()

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
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    enrollment_number = db.Column(db.String(50), unique=True, nullable=False)
    year = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(150), nullable=True)
    # Remove batch_id from here (since it's linked to the course)
    batch = db.Column(db.String(150), nullable=True)

      # Relationship to StudentCourse
    courses = db.relationship('StudentCourse', backref='student', lazy=True)



class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # Course name
    code = db.Column(db.String(50), unique=True, nullable=False)  # Course code, e.g., "CS101"

    
# Association Table for Many-to-Many relationship between Student and Course
class StudentCourse(db.Model):
    __tablename__ = 'student_course'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Ensure autoincrement is set
    roll_number = db.Column(db.String(50), db.ForeignKey('student.roll_number'), nullable=False)
    course_name = db.Column(db.String(120), nullable=False)
    course_code = db.Column(db.String(50), nullable=False)


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    course = db.Column(db.String(120), nullable=False)
    photo = db.Column(db.String(150), nullable=True)
    # Explicitly specify foreign keys for the relationship
    sessions = db.relationship(
        'AttendanceSession',
        backref='teacher',
        lazy=True,
        foreign_keys='AttendanceSession.teacher_id'
    )

class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Unique session ID
    session_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique session identifier
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)  # Link to Teacher
    batch_id = db.Column(db.String(50), nullable=False)  # Batch ID as string
    course_id = db.Column(db.String(120), nullable=False)  # Course identifier
    start_time = db.Column(db.DateTime, nullable=False)  # Session start time
    end_time = db.Column(db.DateTime, nullable=False)  # Session end time
    active = db.Column(db.Boolean, default=True)  # Active session status

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_session.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)
    batch = db.Column(db.String(50), nullable=False)  # Store batch_id in attendance record
    status = db.Column(db.String(10), nullable=False)  # Attendance status: Present/Absent
    timestamp = db.Column(db.DateTime, default=datetime.now)
