from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError

from teacher.models import Teacher
from student.models import Student
from attendance.models import AttendanceSession, AttendanceRecord
from attendance.services import finalize_attendance, toggle_student_status, export_session_csv_buffer


class AttendanceServiceTests(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            name="Teacher One",
            email="teacher1@example.com",
            mobile_number="1111111111",
            courses="Math",
            class_teacher_for="10-A, 10-B",
            password="hashed",
        )
        self.other_teacher = Teacher.objects.create(
            name="Teacher Two",
            email="teacher2@example.com",
            mobile_number="2222222222",
            courses="Science",
            class_teacher_for="9-A",
            password="hashed",
        )
        self.student1 = Student.objects.create(
            name="Alice",
            email="alice@example.com",
            roll_number="01",
            enrollment_number="EN001",
            class_name="10",
            section="A",
            password="hashed",
        )
        self.student2 = Student.objects.create(
            name="Bob",
            email="bob@example.com",
            roll_number="02",
            enrollment_number="EN002",
            class_name="10",
            section="A",
            password="hashed",
        )

    def test_atomic_finalize_attendance(self):
        """Finalizing attendance atomically creates session and records with FINALIZED status."""
        result = finalize_attendance(
            teacher=self.teacher,
            class_name="10",
            section="A",
            student_statuses={"EN001": "Present", "EN002": "Absent"},
            notes="Morning session",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["present_count"], 1)
        self.assertEqual(result["absent_count"], 1)
        self.assertEqual(result["total_count"], 2)

        session = AttendanceSession.objects.get(id=result["session_id"])
        self.assertEqual(session.status, AttendanceSession.STATUS_FINALIZED)
        self.assertIsNotNone(session.finalized_at)
        self.assertEqual(session.notes, "Morning session")

        r1 = AttendanceRecord.objects.get(session=session, student=self.student1)
        self.assertEqual(r1.status, "Present")
        r2 = AttendanceRecord.objects.get(session=session, student=self.student2)
        self.assertEqual(r2.status, "Absent")

    def test_idempotent_finalize_attendance(self):
        """Re-saving attendance updates the existing session without creating duplicates."""
        date = timezone.localdate()
        result1 = finalize_attendance(
            teacher=self.teacher,
            class_name="10",
            section="A",
            student_statuses={"EN001": "Present", "EN002": "Absent"},
            session_date=date,
        )
        self.assertEqual(result1["present_count"], 1)

        # Update and re-finalize
        result2 = finalize_attendance(
            teacher=self.teacher,
            class_name="10",
            section="A",
            student_statuses={"EN001": "Present", "EN002": "Present"},
            session_date=date,
        )
        self.assertEqual(result2["present_count"], 2)
        self.assertEqual(result1["session_id"], result2["session_id"])

        # Check total sessions count remains exactly 1
        sessions_count = AttendanceSession.objects.filter(
            teacher=self.teacher, class_name="10", section="A", session_date=date
        ).count()
        self.assertEqual(sessions_count, 1)

        # Check records count remains exactly 2
        records_count = AttendanceRecord.objects.filter(session_id=result1["session_id"]).count()
        self.assertEqual(records_count, 2)

    def test_teacher_unauthorized_finalize(self):
        """A teacher cannot finalize attendance for a class they do not manage."""
        with self.assertRaises(PermissionDenied):
            finalize_attendance(
                teacher=self.other_teacher,
                class_name="10",
                section="A",
                student_statuses={"EN001": "Present"},
            )

    def test_unique_constraint_enforced_at_db_level(self):
        """Database rejects inserting two AttendanceSessions for same teacher/class/section/date."""
        date = timezone.localdate()
        AttendanceSession.objects.create(
            teacher=self.teacher,
            class_name="10",
            section="A",
            session_date=date,
            status=AttendanceSession.STATUS_FINALIZED,
        )
        with self.assertRaises(IntegrityError):
            AttendanceSession.objects.create(
                teacher=self.teacher,
                class_name="10",
                section="A",
                session_date=date,
                status=AttendanceSession.STATUS_FINALIZED,
            )

    def test_toggle_student_status_service(self):
        """Testing toggling status and IDOR rejection."""
        result = finalize_attendance(
            teacher=self.teacher,
            class_name="10",
            section="A",
            student_statuses={"EN001": "Present"},
        )
        record = AttendanceRecord.objects.get(session_id=result["session_id"], student=self.student1)
        self.assertEqual(record.status, "Present")

        # Toggle to Absent by authorized teacher
        toggle_res = toggle_student_status(self.teacher, record.id)
        self.assertTrue(toggle_res["success"])
        self.assertEqual(toggle_res["new_status"], "Absent")

        # Attempt toggle by unauthorized teacher
        unauth_res = toggle_student_status(self.other_teacher, record.id)
        self.assertFalse(unauth_res["success"])
        self.assertEqual(unauth_res["status_code"], 403)

    def test_export_session_csv_buffer(self):
        """Verify CSV export contains proper headers and student data."""
        result = finalize_attendance(
            teacher=self.teacher,
            class_name="10",
            section="A",
            student_statuses={"EN001": "Present", "EN002": "Absent"},
        )
        session = AttendanceSession.objects.get(id=result["session_id"])
        csv_text = export_session_csv_buffer(session)

        self.assertIn("Roll Number,Enrollment Number,Student Name,Class,Section,Status,Date", csv_text)
        self.assertIn("Alice", csv_text)
        self.assertIn("EN001", csv_text)
        self.assertIn("Present", csv_text)
        self.assertIn("Bob", csv_text)
        self.assertIn("Absent", csv_text)
