from flask import Blueprint, jsonify,render_template,redirect,url_for
from models import Teacher  # Assuming you have a Teacher model
# from . import teacher_bp
from flask_login import login_required,current_user
teacher_bp = Blueprint('teacher', __name__, template_folder='templates')  # Ensure template_folder is correct

@teacher_bp.route('/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('login'))  # Redirect if not a teacher
    return render_template('teacher_dashboard.html')