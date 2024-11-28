from flask import Blueprint, render_template,redirect,url_for
from flask_login import login_required, current_user

developer_bp = Blueprint('developer', __name__)

@developer_bp.route('/dashboard')
@login_required
def developer_dashboard():
    if current_user.role != 'developer':
        return redirect(url_for('home'))  # Redirect if not a developer
    return render_template('developer_dashboard.html')
