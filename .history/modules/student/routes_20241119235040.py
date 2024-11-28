from flask import Blueprint, render_template
from flask_login import login_required, current_user

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))  # Redirect if not a student
    return render_template('student_dashboard.html')
