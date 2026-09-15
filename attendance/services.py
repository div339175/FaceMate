import csv
import io
import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError

from .models import AttendanceSession, AttendanceRecord
from student.models import Student
from core.security import teacher_can_manage_class

logger = logging.getLogger(__name__)


def get_or_create_session(teacher, class_name, section, session_date=None, status=AttendanceSession.STATUS_FINALIZED):
    """
    Retrieves an existing session for the given teacher, class, section, and date,
    or creates a new one.
    """
    if session_date is None:
        session_date = timezone.localdate()

    session, created = AttendanceSession.objects.get_or_create(
        teacher=teacher,
        class_name=class_name,
        section=section,
        session_date=session_date,
        defaults={'status': status}
    )
    return session, created


def finalize_attendance(teacher, class_name, section, student_statuses, notes=None, session_date=None):
    """
    Atomically creates or updates an AttendanceSession and all associated
    AttendanceRecord entries.
    
    Args:
        teacher: Teacher model instance
        class_name: str, class name (e.g. '10')
        section: str, section name (e.g. 'A')
        student_statuses: dict mapping enrollment_number (or str ID) -> 'Present' / 'Absent'
        notes: optional str
        session_date: optional date, defaults to today
    
    Returns:
        dict with keys: 'success', 'session_id', 'present_count', 'absent_count', 'total_count', 'message'
    """
    clean_class = str(class_name).strip()
    clean_section = str(section).strip()

    if not teacher_can_manage_class(teacher, clean_class, clean_section):
        logger.warning(
            "Teacher %s denied authorization to finalize attendance for %s-%s",
            teacher.email, clean_class, clean_section
        )
        raise PermissionDenied("You are not assigned to manage this class.")

    students = Student.objects.filter(class_name__iexact=clean_class, section__iexact=clean_section)
    if not students.exists():
        raise ValidationError(f"No enrolled students found for class {clean_class}-{clean_section}.")

    first_student = students.first()
    canonical_class = first_student.class_name
    canonical_section = first_student.section

    if session_date is None:
        session_date = timezone.localdate()

    with transaction.atomic():
        session, _ = AttendanceSession.objects.get_or_create(
            teacher=teacher,
            class_name=canonical_class,
            section=canonical_section,
            session_date=session_date,
            defaults={'status': AttendanceSession.STATUS_FINALIZED}
        )

        present_count = 0
        absent_count = 0

        for student in students:
            status_val = student_statuses.get(student.enrollment_number, 'Absent')
            status = 'Present' if status_val == 'Present' else 'Absent'

            AttendanceRecord.objects.update_or_create(
                session=session,
                student=student,
                defaults={'status': status}
            )

            if status == 'Present':
                present_count += 1
            else:
                absent_count += 1

        session.status = AttendanceSession.STATUS_FINALIZED
        session.finalized_at = timezone.now()
        if notes:
            session.notes = notes
        session.save(update_fields=['status', 'finalized_at', 'notes'])

    logger.info(
        "Attendance finalized: session %s, teacher %s, class %s-%s, date %s. Present: %d, Absent: %d",
        session.id, teacher.email, class_name, section, session_date, present_count, absent_count
    )

    return {
        'success': True,
        'session_id': session.id,
        'session': session,
        'present_count': present_count,
        'absent_count': absent_count,
        'total_count': students.count(),
        'message': f"Attendance saved successfully! {present_count}/{students.count()} students present.",
    }


def toggle_student_status(teacher, record_id):
    """
    Toggles a student's attendance status in a session, verifying authorization.
    """
    try:
        record = AttendanceRecord.objects.select_related('session', 'session__teacher').get(id=record_id)
    except AttendanceRecord.DoesNotExist:
        return {'success': False, 'error': 'Attendance record not found', 'status_code': 404}

    session = record.session
    if session.teacher != teacher and not teacher_can_manage_class(teacher, session.class_name, session.section):
        logger.warning(
            "Unauthorized toggle attempt on record %s by teacher %s",
            record_id, teacher.email
        )
        return {'success': False, 'error': 'Unauthorized access', 'status_code': 403}

    record.status = 'Absent' if record.status == 'Present' else 'Present'
    record.save(update_fields=['status'])

    logger.info(
        "Attendance record %s toggled to %s by teacher %s",
        record_id, record.status, teacher.email
    )

    return {
        'success': True,
        'new_status': record.status,
        'is_present': record.status == 'Present',
        'status_code': 200,
    }


def export_session_csv_buffer(session):
    """
    Generates a CSV string buffer for a single session's attendance records.
    """
    records = AttendanceRecord.objects.filter(session=session).select_related('student').order_by('student__roll_number')

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Roll Number', 'Enrollment Number', 'Student Name', 'Class', 'Section', 'Status', 'Date'])

    for record in records:
        writer.writerow([
            record.student.roll_number,
            record.student.enrollment_number,
            record.student.name,
            session.class_name,
            session.section,
            record.status,
            session.session_date.strftime('%Y-%m-%d'),
        ])

    return buffer.getvalue()
