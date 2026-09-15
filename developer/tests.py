from django.test import TestCase
from django.urls import reverse
from developer.models import Developer
from teacher.models import Teacher
from student.models import Student
from core.security import set_password


class DeveloperViewsTests(TestCase):
    def setUp(self):
        self.developer = Developer.objects.create(
            name="Super Developer",
            email="dev@example.com",
            password="",
        )
        set_password(self.developer, "dev-pass")
        self.developer.save(update_fields=["password"])

        self.teacher = Teacher.objects.create(
            name="Teacher One",
            email="teacher1@example.com",
            password="",
            class_teacher_for="10-A",
        )
        set_password(self.teacher, "teacher-pass")
        self.teacher.save(update_fields=["password"])

        self.student = Student.objects.create(
            name="Student One",
            email="student1@example.com",
            password="",
            roll_number="101",
            enrollment_number="EN101",
            class_name="10",
            section="A",
        )
        set_password(self.student, "student-pass")
        self.student.save(update_fields=["password"])

    def login_as_developer(self):
        session = self.client.session
        session["developer_id"] = self.developer.pk
        session["profile_role"] = "developer"
        session.save()

    def test_manage_students_renders_unoptimized_students(self):
        self.login_as_developer()
        response = self.client.get(reverse("manage_students"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("storage_stats", response.context)
        self.assertIn("unoptimized_students", response.context["storage_stats"])
        self.assertEqual(response.context["storage_stats"]["unoptimized_students"], 1)

    def test_delete_student_by_developer(self):
        self.login_as_developer()
        response = self.client.post(reverse("dev_delete_student", args=[self.student.pk]))
        self.assertRedirects(response, reverse("manage_students"))
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())

    def test_delete_teacher_by_developer(self):
        self.login_as_developer()
        response = self.client.post(reverse("delete_teacher", args=[self.teacher.pk]))
        self.assertRedirects(response, reverse("manage_teachers"))
        self.assertFalse(Teacher.objects.filter(pk=self.teacher.pk).exists())

    def test_delete_student_requires_developer(self):
        response = self.client.post(reverse("dev_delete_student", args=[self.student.pk]))
        self.assertRedirects(response, reverse("developer_login"))
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

    def test_student_register_duplicate_roll_number_rejected(self):
        self.login_as_developer()
        response = self.client.post(
            reverse("student_register"),
            {
                "name": "Duplicate Roll",
                "email": "unique@example.com",
                "password": "pass",
                "roll_number": "101",  # Same as self.student
                "enrollment_number": "EN999",
                "class_name": "10",
                "section": "A",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(Student.objects.filter(email="unique@example.com").exists())

    def test_edit_teacher_duplicate_email_rejected(self):
        other_teacher = Teacher.objects.create(
            name="Teacher Two",
            email="teacher2@example.com",
            password="",
            class_teacher_for="9-B",
        )
        self.login_as_developer()
        response = self.client.post(
            reverse("edit_teacher", args=[other_teacher.pk]),
            {
                "name": "Teacher Two Updated",
                "email": "teacher1@example.com",  # Duplicate of self.teacher
                "class_teacher_for": "9-B",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        other_teacher.refresh_from_db()
        self.assertEqual(other_teacher.email, "teacher2@example.com")

