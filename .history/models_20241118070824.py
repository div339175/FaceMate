from extensions import db
from flask_login import UserMixin

# Base User Model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Use hashed passwords in production
    role = db.Column(db.String(50), nullable=False)  # Role can be 'student', 'teacher', or 'developer'

    # Relationships for Student and Teacher profiles if needed
    student_profile = db.relationship('Student', backref='user', uselist=False)
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False)

    def __repr__(self):
        return f"<User {self.email}, Role: {self.role}>"

# Student Model
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Link to User table
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), nullable=False)
    enrollment_number = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    photo = db.Column(db.String(200), nullable=True)  # Store path to photo

    def __repr__(self):
        return f"<Student {self.name}>"

# Teacher Model
class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Link to User table
    name = db.Column(db.String(100), nullable=False)
    course = db.Column(db.String(100), nullable=False)
    photo = db.Column(db.String(200), nullable=True)  # Store path to photo

    def __repr__(self):
        return f"<Teacher {self.name}>"
