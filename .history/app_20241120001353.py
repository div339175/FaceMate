from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, current_user
from models import db, User  # Assuming you have a User model with fields: email, password, role
from flask_login import login_required


# Initialize the extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Load the user by their ID from the database

@app.route('/')
def home():
    return render_template('home.html')

# Route for login
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  # You should use hashed passwords in production
            login_user(user)

            # Redirect user based on their role
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'developer':
                return redirect(url_for('developer_dashboard'))

        flash('Invalid email or password', 'danger')

    return render_template('login.html', role=role)

# Routes for student, teacher, and developer dashboards (add logic to each route as needed)
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('home'))
    return render_template('student_dashboard.html')

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('home'))
    return render_template('teacher_dashboard.html')

@app.route('/developer/dashboard')
@login_required
def developer_dashboard():
    if current_user.role != 'developer':
        return redirect(url_for('home'))
    return render_template('developer_dashboard.html')

# Function to create tables automatically when app starts
def create_tables():
    with app.app_context():
        db.create_all()  # This will create all tables defined in the models

if __name__ == '__main__':
    create_tables()  # Call the function to create tables before running the app
    app.run(debug=True)
