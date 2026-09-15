from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from attendance.models import AttendanceRecord, AttendanceSession
from core.security import set_password, verify_password
from student.models import Student
from teacher.models import Teacher


class FaceMateSecurityAndAttendanceTests(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            name="Class Teacher",
            email="teacher@example.com",
            password="",
            class_teacher_for="10-A",
        )
        set_password(self.teacher, "safe-password")
        self.teacher.save(update_fields=["password"])

        self.student = Student.objects.create(
            name="Student One",
            email="student@example.com",
            password="",
            roll_number="1",
            enrollment_number="EN001",
            class_name="10",
            section="A",
        )
        set_password(self.student, "student-password")
        self.student.save(update_fields=["password"])

        self.other_student = Student.objects.create(
            name="Student Two",
            email="other@example.com",
            password="",
            roll_number="2",
            enrollment_number="EN002",
            class_name="11",
            section="A",
        )

    def login_as_teacher(self):
        session = self.client.session
        session["teacher_id"] = self.teacher.pk
        session["profile_role"] = "teacher"
        session.save()

    def login_as_student(self):
        session = self.client.session
        session["student_id"] = self.student.pk
        session["profile_role"] = "student"
        session.save()

    def test_legacy_plaintext_password_is_upgraded_after_successful_login(self):
        self.student.password = "legacy-password"
        self.student.save(update_fields=["password"])

        self.assertTrue(verify_password(self.student, "legacy-password"))
        self.student.refresh_from_db()
        self.assertNotEqual(self.student.password, "legacy-password")
        self.assertTrue(verify_password(self.student, "legacy-password"))

    def test_teacher_login_uses_hashed_password_and_rotates_to_role_session(self):
        response = self.client.post(
            reverse("teacher_login"), {"email": self.teacher.email, "password": "safe-password"}
        )

        self.assertRedirects(response, reverse("teacher_dashboard"))
        self.assertEqual(self.client.session["teacher_id"], self.teacher.pk)
        self.assertEqual(self.client.session["profile_role"], "teacher")

    @override_settings(DEMO_LOGIN_ENABLED=True)
    def test_demo_login_creates_a_local_teacher_account(self):
        response = self.client.post(reverse("teacher_demo_login"))

        self.assertRedirects(response, reverse("teacher_dashboard"))
        self.assertEqual(self.client.session["profile_role"], "teacher")
        self.assertTrue(Teacher.objects.filter(email="demo.teacher@facemate.local").exists())

    def test_student_dashboard_counts_capitalized_status_values(self):
        session = AttendanceSession.objects.create(
            teacher=self.teacher, class_name="10", section="A", session_date=timezone.localdate()
        )
        AttendanceRecord.objects.create(session=session, student=self.student, status="Present")
        self.login_as_student()

        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.context["present_count"], 1)
        self.assertEqual(response.context["absent_count"], 0)
        self.assertEqual(response.context["attendance_percentage"], 100.0)

    def test_recognition_endpoint_requires_a_teacher_session(self):
        response = self.client.post(reverse("recognize_frame"), {"image_data": "invalid"})
        self.assertEqual(response.status_code, 401)

    def test_teacher_cannot_open_another_class_attendance_roster(self):
        self.login_as_teacher()
        response = self.client.get(reverse("live_attendance"), {"class_name": "11", "section": "A"})
        self.assertRedirects(response, reverse("select_attendance_class"))

    def test_saving_the_same_roster_updates_instead_of_creating_duplicate_records(self):
        self.login_as_teacher()
        payload = {"class_name": "10", "section": "A", "student_EN001": "Present"}

        first_response = self.client.post(reverse("save_attendance"), payload)
        second_response = self.client.post(
            reverse("save_attendance"), {**payload, "student_EN001": "Absent"}
        )

        self.assertTrue(first_response.json()["success"])
        self.assertTrue(second_response.json()["success"])
        self.assertEqual(AttendanceSession.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.count(), 1)
        self.assertEqual(AttendanceRecord.objects.get().status, "Absent")

    def test_database_prevents_duplicate_records_within_one_session(self):
        session = AttendanceSession.objects.create(
            teacher=self.teacher, class_name="10", section="A", session_date=timezone.localdate()
        )
        AttendanceRecord.objects.create(session=session, student=self.student, status="Present")

        with self.assertRaises(IntegrityError):
            AttendanceRecord.objects.create(session=session, student=self.student, status="Absent")

    def test_custom_404_template(self):
        """Non-existent URL renders the custom 404 page."""
        response = self.client.get("/non-existent-page-url-xyz-123/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_custom_403_view(self):
        """Direct call to permission_denied handler renders 403.html."""
        from django.test import RequestFactory
        from core.views import permission_denied
        factory = RequestFactory()
        request = factory.get("/teacher/attendance/detail/999/")
        response = permission_denied(request, Exception("Access Denied"))
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied", response.content.decode())

    def test_custom_400_view(self):
        """Direct call to bad_request handler renders 400.html."""
        from django.test import RequestFactory
        from core.views import bad_request
        factory = RequestFactory()
        request = factory.get("/bad-request/")
        response = bad_request(request, Exception("Malformed payload"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Malformed payload", response.content.decode())

    def test_custom_500_view(self):
        """Direct call to server_error handler renders 500.html."""
        from django.test import RequestFactory
        from core.views import server_error
        factory = RequestFactory()
        request = factory.get("/server-error/")
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Something Went Wrong", response.content.decode())

    def test_face_recognition_graceful_fallback(self):
        """Face recognition returns clean empty dict when given empty embeddings or on exception."""
        from core.face_utils import recognize_faces_in_frame
        import numpy as np

        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # 1. Empty embeddings dictionary
        result = recognize_faces_in_frame(dummy_frame, {})
        self.assertEqual(result, {"recognized": [], "newly_present": []})

        # 2. Corrupted embeddings dictionary
        result2 = recognize_faces_in_frame(dummy_frame, {"EN001": [1.0, 2.0]})
        self.assertIn("recognized", result2)
        self.assertIsInstance(result2["recognized"], list)

