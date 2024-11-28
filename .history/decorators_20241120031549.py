# # decorators.py
# from functools import wraps
# from flask import redirect, url_for, flash
# from flask_login import current_user

# # Decorator to restrict access to specific roles
# def role_required(role):
#     def decorator(func):
#         @wraps(func)
#         def decorated_function(*args, **kwargs):
#             if not current_user.is_authenticated or current_user.role != role:
#                 flash('Access denied: You do not have permission to view this page.', 'danger')
#                 return redirect(url_for('login'))  # Redirect to login page
#             return func(*args, **kwargs)
#         return decorated_function
#     return decorator
