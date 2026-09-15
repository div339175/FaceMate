"""Small, shared authentication and authorization helpers for FaceMate.

The project has three profile models rather than a single custom user model.
These helpers keep that legacy structure while using Django's password hashing
and rotating session identifiers on login.
"""

from functools import wraps
import secrets

from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect


ROLE_SESSION_KEYS = {
    "developer": "developer_id",
    "teacher": "teacher_id",
    "student": "student_id",
}


def set_password(profile, raw_password):
    """Hash and store a profile password using Django's configured hasher."""
    profile.password = make_password(raw_password)


def password_validation_errors(raw_password):
    """Return Django password-policy messages without storing a weak password."""
    try:
        validate_password(raw_password)
    except ValidationError as exc:
        return exc.messages
    return []


def verify_password(profile, raw_password):
    """Verify a password and transparently upgrade a legacy plain-text value.

    Existing demo databases can continue to be used once; a successful legacy
    login immediately replaces the stored value with a secure Django hash.
    """
    try:
        identify_hasher(profile.password)
        return check_password(raw_password, profile.password)
    except ValueError:
        valid = secrets.compare_digest(profile.password, raw_password)
        if valid:
            set_password(profile, raw_password)
            profile.save(update_fields=["password"])
        return valid


def login_profile(request, role, profile):
    """Create a fresh session for a successfully authenticated profile."""
    # flush() discards the anonymous session and causes Django to issue a new
    # identifier, preventing session fixation across the login boundary.
    request.session.flush()
    request.session[ROLE_SESSION_KEYS[role]] = profile.pk
    request.session["profile_role"] = role
    request.session.set_expiry(60 * 60 * 8)


def logout_profile(request):
    request.session.flush()


def role_required(role, *, api=False):
    """Require the role-specific session key before allowing a view."""
    session_key = ROLE_SESSION_KEYS[role]

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.session.get("profile_role") != role or not request.session.get(session_key):
                if api:
                    from django.http import JsonResponse
                    return JsonResponse({"error": "Authentication required"}, status=401)
                return redirect(f"{role}_login")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def assigned_classes(teacher):
    """
    Return list of (class_name, section) tuples assigned to the teacher.
    Supports:
      - Single: "10-A"
      - Multiple comma-separated: "10-A, 10-B, 11-A"
      - Wildcard / All: "All" or "*"
    """
    assignment = (getattr(teacher, "class_teacher_for", "") or "").strip()
    if not assignment or assignment.lower() in {"not assigned", "none"}:
        return []
    if assignment.lower() in {"all", "*"}:
        return [("All", "All")]

    classes = []
    for part in assignment.split(","):
        cleaned = part.strip()
        if "-" in cleaned:
            c, s = (p.strip() for p in cleaned.split("-", 1))
            if c and s:
                classes.append((c, s))
        elif " " in cleaned:
            parts = cleaned.split()
            if len(parts) >= 2:
                if parts[0].lower() == "class" and len(parts) >= 3:
                    classes.append((parts[1].strip(), parts[2].strip()))
                else:
                    classes.append((parts[0].strip(), parts[1].strip()))
    return classes


def assigned_class(teacher):
    """Return the primary assigned (class, section), or None when unassigned."""
    classes = assigned_classes(teacher)
    if not classes:
        return None
    return classes[0]


def teacher_can_manage_class(teacher, class_name, section):
    classes = assigned_classes(teacher)
    if not classes:
        return False
    if ("All", "All") in classes:
        return True
    target_c = str(class_name).strip().upper()
    target_s = str(section).strip().upper()
    return any(c.strip().upper() == target_c and s.strip().upper() == target_s for c, s in classes)


def teacher_can_manage_student(teacher, student):
    return teacher_can_manage_class(teacher, student.class_name, student.section)
