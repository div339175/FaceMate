from flask import Blueprint, render_template, request, redirect, url_for, flash
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
            return redirect(url_for('student.developer_dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('login.html')

@student_bp.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('home'))
    return render_template('student_dashboard.html')
