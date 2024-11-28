from flask import Blueprint, render_template
from flask_login import login_required, current_user

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('login'))  # Redirect if not a teacher
    return render_template('teacher_dashboard.html')
