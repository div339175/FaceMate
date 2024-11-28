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

     # Many-to-many relationship with courses
    courses = db.relationship(
        'Course',
        secondary='student_course',
        back_populates='students',  # Use back_populates instead of backref
        lazy='dynamic'
    )

    enrolled_courses = db.relationship(
        'Course',
        secondary='student_course',
        backref='enrolled_students',
        lazy='dynamic',
        overlaps="courses,students"
    )
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)  # Course name
    code = db.Column(db.String(50), unique=True, nullable=False)  # Course code, e.g., "CS101"

      # Relationships with students
    students = db.relationship(
        'Student',
        secondary='student_course',
        backref='enrolled_courses',
        lazy='dynamic',
        overlaps="enrolled_students"
    )

    enrolled_students = db.relationship(
        'Student',
        secondary='student_course',
        backref='courses',
        lazy='dynamic',
        overlaps="students,courses"
    )
# Association Table for Many-to-Many relationship between Student and Course
class StudentCourse(db.Model):
    __tablename__ = 'student_course'
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)


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
    batch_id = db.Column(db.String(50), nullable=False)  # Store batch_id in attendance record
    status = db.Column(db.String(10), nullable=False)  # Attendance status: Present/Absent
    timestamp = db.Column(db.DateTime, default=datetime.now)
