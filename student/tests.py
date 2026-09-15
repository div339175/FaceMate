from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from student.models import Student
from teacher.models import Teacher
from attendance.models import AttendanceSession, AttendanceRecord
from core.security import set_password


class StudentViewsTests(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            name="Teacher",
            email="teacher@example.com",
            password="",
            class_teacher_for="10-A",
        )
        self.student1 = Student.objects.create(
            name="Student One",
            email="student1@example.com",
            password="",
            roll_number="1",
            enrollment_number="EN001",
            class_name="10",
            section="A",
        )
        set_password(self.student1, "student1-pass")
        self.student1.save(update_fields=["password"])

        self.student2 = Student.objects.create(
            name="Student Two",
            email="student2@example.com",
            password="",
            roll_number="2",
            enrollment_number="EN002",
            class_name="10",
            section="A",
        )

    def login_as_student1(self):
        session = self.client.session
        session["student_id"] = self.student1.pk
        session["profile_role"] = "student"
        session.save()

    def test_student_profile_duplicate_email_rejected(self):
        self.login_as_student1()
        response = self.client.post(
            reverse("student_profile"),
            {
                "email": "student2@example.com",  # Duplicate of student2
                "phone_number": "1234567890",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already registered")
        self.student1.refresh_from_db()
        self.assertEqual(self.student1.email, "student1@example.com")

    def test_student_attendance_history_renders_present_status(self):
        self.login_as_student1()
        session = AttendanceSession.objects.create(
            teacher=self.teacher, class_name="10", section="A", session_date=timezone.localdate()
        )
        record = AttendanceRecord.objects.create(session=session, student=self.student1, status="Present")

        response = self.client.get(reverse("student_attendance_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Present")

