"""Local-only demo accounts used to showcase the full FaceMate workflow."""

from django.conf import settings
from django.http import Http404

from core.security import login_profile, set_password
from developer.models import Developer
from student.models import Student
from teacher.models import Teacher


DEMO_PASSWORD = "demo-access-only"


def login_demo_account(request, role):
    """Create a predictable local demo account when enabled, then sign in."""
    if not settings.DEMO_LOGIN_ENABLED:
        raise Http404("Demo login is disabled.")

    if role == "developer":
        profile, _ = Developer.objects.get_or_create(
            email="demo.admin@facemate.local",
            defaults={"name": "Demo Administrator", "password": ""},
        )
    elif role == "teacher":
        profile, _ = Teacher.objects.get_or_create(
            email="demo.teacher@facemate.local",
            defaults={
                "name": "Demo Teacher",
                "password": "",
                "class_teacher_for": "10-A",
                "courses": "Demonstration Course",
            },
        )
    elif role == "student":
        profile, _ = Student.objects.get_or_create(
            email="demo.student@facemate.local",
            defaults={
                "name": "Demo Student",
                "password": "",
                "roll_number": "DEMO-001",
                "enrollment_number": "DEMO-ENROLL-001",
                "class_name": "10",
                "section": "A",
            },
        )
    else:
        raise Http404("Unknown demo role.")

    # The password is not displayed or needed for the one-click route. Hash it
    # nevertheless so a demo account never creates a plain-text password row.
    if not profile.password:
        set_password(profile, DEMO_PASSWORD)
        profile.save(update_fields=["password"])

    login_profile(request, role, profile)
    return profile
