from flask import Blueprint, jsonify,render_template,redirect,url_for
from models import Student  # Assuming you have a Student model
# from . import student_bp
from flask_login import login_required,current_user
student_bp = Blueprint('student', __name__, template_folder='templates')  # Ensure template_folder is correct

@student_bp.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))  # Redirect if not a student
    return render_template('student_dashboard.html')