from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

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
    semester = db.Column(db.String(50), nullable=False)
    photo = db.Column(db.String(150), nullable=True)
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # password = db.Column(db.String(120), nullable=False)
    # role = db.Column(db.String(50), nullable=False)



# from flask_sqlalchemy import SQLAlchemy
# from flask_login import UserMixin

# db = SQLAlchemy()

# class User(UserMixin, db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(db.String(100), unique=True, nullable=False)
#     password = db.Column(db.String(255), nullable=False)
#     role = db.Column(db.String(50), nullable=False)  # 'developer', 'student', or 'teacher'

#     def __repr__(self):
#         return f"<User {self.email}>"

# class Developer(User):
#     __tablename__ = 'developers'
#     # Additional fields specific to Developer can go here
#     def __repr__(self):
#         return f"<Developer {self.email}>"

# class Student(User):
#     __tablename__ = 'students'
#     roll_number = db.Column(db.String(20), nullable=False)
#     enrollment_number = db.Column(db.String(50), nullable=False)
#     year = db.Column(db.String(20), nullable=False)
#     semester = db.Column(db.String(20), nullable=False)
    
#     def __repr__(self):
#         return f"<Student {self.email}>"

# class Teacher(User):
#     __tablename__ = 'teachers'
#     course = db.Column(db.String(100), nullable=False)
    
#     def __repr__(self):
#         return f"<Teacher {self.email}>"
