from flask import Blueprint

developer_bp = Blueprint('developer', __name__, template_folder='templates')

from . import routes  # Import routes for the student module
