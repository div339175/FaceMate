from django.db import models
from student.models import Student
from teacher.models import Teacher
from django.utils import timezone

class AttendanceSession(models.Model):
    """ Represents a single attendance-taking event for a specific class. """
    STATUS_DRAFT = 'DRAFT'
    STATUS_REVIEW = 'REVIEW'
    STATUS_FINALIZED = 'FINALIZED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_REVIEW, 'In Review'),
        (STATUS_FINALIZED, 'Finalized'),
    ]

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    class_name = models.CharField(max_length=100)
    section = models.CharField(max_length=50)
    session_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_FINALIZED)
    finalized_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attendance for {self.class_name} - {self.section} on {self.session_date} ({self.status})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "class_name", "section", "session_date"],
                name="unique_teacher_class_session_date"
            )
        ]
        indexes = [
            models.Index(fields=["teacher", "session_date"]),
            models.Index(fields=["class_name", "section", "session_date"]),
            models.Index(fields=["status"]),
        ]

class AttendanceRecord(models.Model):
    """ Stores the attendance status for a single student in a session. """
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Absent', 'Absent')], default='Absent')

    def __str__(self):
        return f"{self.student.name} - {self.status}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "student"], name="one_attendance_record_per_student_session"),
        ]
        indexes = [models.Index(fields=["student", "status"])]
