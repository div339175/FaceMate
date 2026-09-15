from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from teacher.models import Teacher
from student.models import Student
from attendance.models import AttendanceSession, AttendanceRecord
from teacher.views import invalidate_embeddings_cache, EMBEDDINGS_CACHE
from core.security import set_password


class TeacherViewsTests(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            name="Test Teacher",
            email="teacher@example.com",
            password="",
            class_teacher_for="10-A",
        )
        set_password(self.teacher, "teacher-pass")
        self.teacher.save(update_fields=["password"])

        self.student1 = Student.objects.create(
            name="Alice",
            email="alice@example.com",
            password="",
            roll_number="1",
            enrollment_number="EN001",
            class_name="10",
            section="A",
        )
        self.student2 = Student.objects.create(
            name="Bob",
            email="bob@example.com",
            password="",
            roll_number="2",
            enrollment_number="EN002",
            class_name="10",
            section="A",
        )

    def login_as_teacher(self):
        session = self.client.session
        session["teacher_id"] = self.teacher.pk
        session["profile_role"] = "teacher"
        session.save()

    def test_attendance_report_calculates_stats_correctly(self):
        self.login_as_teacher()
        d1 = timezone.localdate()
        d2 = d1 - timezone.timedelta(days=1)

        s1 = AttendanceSession.objects.create(teacher=self.teacher, class_name="10", section="A", session_date=d1)
        s2 = AttendanceSession.objects.create(teacher=self.teacher, class_name="10", section="A", session_date=d2)

        AttendanceRecord.objects.create(session=s1, student=self.student1, status="Present")
        AttendanceRecord.objects.create(session=s2, student=self.student1, status="Present")
        AttendanceRecord.objects.create(session=s1, student=self.student2, status="Present")
        AttendanceRecord.objects.create(session=s2, student=self.student2, status="Absent")

        response = self.client.get(
            reverse("attendance_report"),
            {"class_name": "10", "section": "A", "report_type": "weekly"},
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["total_sessions"], 2)
        self.assertEqual(response.context["avg_attendance"], 75.0)

        student_stats = response.context["student_stats"]
        self.assertEqual(len(student_stats), 2)

        alice_stat = next(s for s in student_stats if s["student"].pk == self.student1.pk)
        self.assertEqual(alice_stat["present"], 2)
        self.assertEqual(alice_stat["percentage"], 100.0)

        bob_stat = next(s for s in student_stats if s["student"].pk == self.student2.pk)
        self.assertEqual(bob_stat["present"], 1)
        self.assertEqual(bob_stat["percentage"], 50.0)

    def test_teacher_add_student_duplicate_roll_number_rejected(self):
        self.login_as_teacher()
        response = self.client.post(
            reverse("add_student"),
            {
                "name": "New Student",
                "email": "newstudent@example.com",
                "password": "pass",
                "roll_number": "1",  # Duplicate roll number
                "enrollment_number": "EN999",
                "class_name": "10",
                "section": "A",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(Student.objects.filter(email="newstudent@example.com").exists())

    def test_embeddings_cache_invalidation(self):
        cache_key = ("10", "A")
        EMBEDDINGS_CACHE[cache_key] = {"data": [1, 2, 3]}
        self.assertIn(cache_key, EMBEDDINGS_CACHE)

        invalidate_embeddings_cache("10", "A")
        self.assertNotIn(cache_key, EMBEDDINGS_CACHE)

    def test_multi_class_assigned_teacher_can_manage_classes(self):
        from core.security import assigned_classes, teacher_can_manage_class
        self.teacher.class_teacher_for = "10-A, 10-B"
        self.teacher.save()

        classes = assigned_classes(self.teacher)
        self.assertEqual(classes, [("10", "A"), ("10", "B")])
        self.assertTrue(teacher_can_manage_class(self.teacher, "10", "A"))
        self.assertTrue(teacher_can_manage_class(self.teacher, "10", "B"))
        self.assertFalse(teacher_can_manage_class(self.teacher, "11", "A"))

    def test_all_class_assigned_teacher_can_manage_any_class(self):
        from core.security import teacher_can_manage_class
        self.teacher.class_teacher_for = "All"
        self.teacher.save()

        self.assertTrue(teacher_can_manage_class(self.teacher, "9", "B"))
        self.assertTrue(teacher_can_manage_class(self.teacher, "12", "A"))

    def test_select_attendance_class_returns_multi_classes(self):
        self.teacher.class_teacher_for = "10-A, 11-B"
        self.teacher.save()
        self.login_as_teacher()

        response = self.client.get(reverse("select_attendance_class"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("10", response.context["classes"])
        self.assertIn("11", response.context["classes"])

    def test_save_attendance_returns_detail_and_export_urls(self):
        self.login_as_teacher()
        payload = {"class_name": "10", "section": "A", "student_EN001": "Present"}
        response = self.client.post(reverse("save_attendance"), payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("session_id", data)
        self.assertIn("detail_url", data)
        self.assertIn("export_url", data)
        self.assertIn("redirect_url", data)
        self.assertEqual(data["redirect_url"], data["detail_url"])

    def test_export_attendance_report_csv(self):
        self.login_as_teacher()
        session = AttendanceSession.objects.create(
            teacher=self.teacher, class_name="10", section="A", session_date=timezone.localdate()
        )
        AttendanceRecord.objects.create(session=session, student=self.student1, status="Present")

        response = self.client.get(
            reverse("export_attendance_report"),
            {"class_name": "10", "section": "A", "report_type": "daily"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("Roll Number", content)
        self.assertIn(self.student1.name, content)
        self.assertIn("100.0%", content)

    def test_teacher_idor_rejection_on_attendance_detail(self):
        """Teacher cannot view session detail of an unassigned class."""
        other_teacher = Teacher.objects.create(
            name="Other Teacher",
            email="otherteacher@example.com",
            password="pass",
            class_teacher_for="9-B",
        )
        unauthorized_session = AttendanceSession.objects.create(
            teacher=other_teacher, class_name="9", section="B", session_date=timezone.localdate()
        )
        self.login_as_teacher()
        response = self.client.get(reverse("attendance_detail", args=[unauthorized_session.id]))
        self.assertRedirects(response, reverse("teacher_dashboard"))

    def test_teacher_idor_rejection_on_export_attendance(self):
        """Teacher cannot export session CSV of an unassigned class."""
        other_teacher = Teacher.objects.create(
            name="Other Teacher",
            email="otherteacher2@example.com",
            password="pass",
            class_teacher_for="9-B",
        )
        unauthorized_session = AttendanceSession.objects.create(
            teacher=other_teacher, class_name="9", section="B", session_date=timezone.localdate()
        )
        self.login_as_teacher()
        response = self.client.get(reverse("export_attendance", args=[unauthorized_session.id]))
        self.assertEqual(response.status_code, 403)

    def test_toggle_attendance_view_endpoint(self):
        """Authorized teacher can toggle student status via AJAX."""
        self.login_as_teacher()
        session = AttendanceSession.objects.create(
            teacher=self.teacher, class_name="10", section="A", session_date=timezone.localdate()
        )
        record = AttendanceRecord.objects.create(session=session, student=self.student1, status="Present")

        response = self.client.post(reverse("toggle_attendance", args=[record.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["new_status"], "Absent")

    def test_case_insensitive_class_management(self):
        from core.security import teacher_can_manage_class
        self.teacher.class_teacher_for = "10-A, 11-B"
        self.teacher.save()

        self.assertTrue(teacher_can_manage_class(self.teacher, "10", "a"))
        self.assertTrue(teacher_can_manage_class(self.teacher, " 10 ", " A "))
        self.assertTrue(teacher_can_manage_class(self.teacher, "11", "b"))
        self.assertFalse(teacher_can_manage_class(self.teacher, "12", "c"))

    def test_save_attendance_case_insensitive_payload(self):
        self.login_as_teacher()
        payload = {"class_name": " 10 ", "section": " a ", "student_EN001": "Present"}
        response = self.client.post(reverse("save_attendance"), payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["present_count"], 1)

    def test_recognize_faces_in_frame_drops_when_locked(self):
        from core.face_utils import recognize_faces_in_frame, _RECOGNITION_LOCK
        import numpy as np

        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # Acquire lock to simulate concurrent frame
        _RECOGNITION_LOCK.acquire()
        try:
            result = recognize_faces_in_frame(dummy_frame, {"EN001": [1, 2, 3]})
            self.assertEqual(result, {"recognized": [], "newly_present": []})
        finally:
            _RECOGNITION_LOCK.release()
