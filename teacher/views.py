import os
import base64
import numpy as np
import cv2
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Teacher
from student.models import Student
from attendance.models import AttendanceSession, AttendanceRecord
from core.face_utils import recognize_faces_in_frame, enroll_student_face
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.db import IntegrityError, transaction
from django.core.exceptions import PermissionDenied, ValidationError
import csv
import logging
import json

from core.security import (
    assigned_class,
    assigned_classes,
    login_profile,
    logout_profile,
    role_required,
    set_password,
    password_validation_errors,
    teacher_can_manage_class,
    teacher_can_manage_student,
    verify_password,
)
from core.demo import login_demo_account
from attendance.services import finalize_attendance, toggle_student_status, export_session_csv_buffer

logger = logging.getLogger(__name__)

EMBEDDINGS_CACHE = {}

def invalidate_embeddings_cache(class_name=None, section=None):
    """Invalidate memory cache when students are created, updated, or removed."""
    if class_name and section:
        EMBEDDINGS_CACHE.pop(f"{class_name}_{section}", None)
        EMBEDDINGS_CACHE.pop((class_name, section), None)
    else:
        EMBEDDINGS_CACHE.clear()

def teacher_login(request):
    """
    Handles the teacher login functionality.
    Automatically logs out any existing sessions for the same teacher.
    """
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''
        teacher = Teacher.objects.filter(email__iexact=email).first()
        if teacher and verify_password(teacher, password):
            login_profile(request, 'teacher', teacher)
            return redirect('teacher_dashboard')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'teacher_login.html', {'demo_login_enabled': settings.DEMO_LOGIN_ENABLED})


@require_POST
def teacher_demo_login(request):
    login_demo_account(request, 'teacher')
    return redirect('teacher_dashboard')

@role_required('teacher')
def teacher_dashboard(request):
    """
    Displays the teacher's dashboard.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.warning(request, 'Your session has expired or you logged in from another device. Please log in again.')
        return redirect('teacher_login')
    try:
        teacher = Teacher.objects.get(id=teacher_id)
        context = {'teacher': teacher}
        return render(request, 'teacher_dash.html', context)
    except Teacher.DoesNotExist:
        request.session.flush()
        messages.error(request, 'Account not found. Please log in again.')
        return redirect('teacher_login')

@role_required('teacher')
def teacher_logout(request):
    """
    Logs the teacher out by clearing the session.
    """
    logout_profile(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('teacher_login')

@role_required('teacher')
def select_attendance_class(request):
    """ Displays a page for the teacher to select which class to take attendance for. """
    if 'teacher_id' not in request.session:
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=request.session['teacher_id'])
    classes_assigned = assigned_classes(teacher)
    if not classes_assigned:
        messages.error(request, 'No class is assigned to your account. Please contact an administrator.')
        return redirect('teacher_dashboard')
    
    class_sections_map = {}
    if ("All", "All") in classes_assigned:
        # Teacher has access to all active classes and sections with students
        student_pairs = Student.objects.values_list('class_name', 'section').distinct()
        if student_pairs.exists():
            for c, s in student_pairs:
                if c and s:
                    class_sections_map.setdefault(c, []).append(s)
        else:
            class_sections_map = {'10': ['A'], '9': ['B']}
    else:
        for c, s in classes_assigned:
            if c and s:
                class_sections_map.setdefault(c, []).append(s)

    # Sort classes and their sections
    for c in class_sections_map:
        class_sections_map[c] = sorted(list(set(class_sections_map[c])))
    available_classes = sorted(list(class_sections_map.keys()))
    
    context = {
        'classes': available_classes,
        'sections': class_sections_map.get(available_classes[0], []) if available_classes else [],
        'class_sections_json': json.dumps(class_sections_map),
    }
    return render(request, 'select_attendance_class.html', context)

@role_required('teacher')
def live_attendance(request):
    """ Displays the main attendance page with the camera feed and class roster. """
    if 'teacher_id' not in request.session:
        return redirect('teacher_login')
        
    class_name = (request.GET.get('class_name') or '').strip()
    section = (request.GET.get('section') or '').strip()
    
    if not class_name or not section:
        messages.error(request, 'You must select a class and section to proceed.')
        return redirect('select_attendance_class')
    
    teacher = get_object_or_404(Teacher, id=request.session['teacher_id'])
    if not teacher_can_manage_class(teacher, class_name, section):
        messages.error(request, 'You can take attendance only for your assigned class.')
        return redirect('select_attendance_class')

    # Fetch all students belonging to the selected class and section
    students = Student.objects.filter(class_name__iexact=class_name, section__iexact=section).order_by('name')
    canonical_class = students.first().class_name if students.exists() else class_name
    canonical_section = students.first().section if students.exists() else section

    context = {
        'students': students,
        'class_name': canonical_class,
        'section': canonical_section
    }
    return render(request, 'live_attendance.html', context)

@require_POST
@role_required('teacher', api=True)
def recognize_frame(request):
    """
    Receives a camera frame, loads the necessary AI data, calls the AI utility,
    and returns the recognized student IDs.
    """
    try:
        image_data = request.POST.get('image_data')
        class_name = (request.POST.get('class_name') or '').strip()
        section = (request.POST.get('section') or '').strip()
        teacher = get_object_or_404(Teacher, id=request.session['teacher_id'])
        if not teacher_can_manage_class(teacher, class_name, section):
            return JsonResponse({'error': 'You are not assigned to this class'}, status=403)
        if not image_data or len(image_data) > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            return JsonResponse({'error': 'Invalid or oversized image data'}, status=400)
            
        # Load student AI data for the class, using a cache for speed
        cache_key = f"{class_name.upper()}_{section.upper()}"
        if cache_key not in EMBEDDINGS_CACHE:
            all_students = Student.objects.filter(class_name__iexact=class_name, section__iexact=section)
            student_embeddings = {}
            for student in all_students:
                if student.dataset_path:
                    path = os.path.join(settings.STATICFILES_DIRS[0], student.dataset_path)
                    if not os.path.exists(path):
                        path = os.path.join(settings.MEDIA_ROOT, student.dataset_path)
                    if os.path.exists(path) and os.path.isfile(path) and path.endswith('.npy'):
                        student_embeddings[student.enrollment_number] = np.load(path, allow_pickle=False)
            EMBEDDINGS_CACHE[cache_key] = student_embeddings
            
        try:
            # Decode the Base64 image sent from the browser's camera
            header, encoded = image_data.split(",", 1)
            decoded_image = base64.b64decode(encoded, validate=True)
            image_array = np.frombuffer(decoded_image, np.uint8)
            frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid image data'}, status=400)

        recognized_ids = recognize_faces_in_frame(frame, EMBEDDINGS_CACHE.get(cache_key, {}))
        return JsonResponse({'recognized_ids': recognized_ids})
    except (ConnectionResetError, BrokenPipeError):
        logger.info("Client disconnected during frame recognition")
        return HttpResponse(status=204)
    except Exception as e:
        logger.warning("Error during frame recognition: %s", e)
        return JsonResponse({'recognized_ids': {'recognized': [], 'newly_present': []}}, status=200)

@require_POST
@role_required('teacher', api=True)
def save_attendance(request):
    """ Handles the submission of the finalized attendance roster. """
    teacher = get_object_or_404(Teacher, id=request.session['teacher_id'])
    class_name = (request.POST.get('class_name') or '').strip()
    section = (request.POST.get('section') or '').strip()
    notes = request.POST.get('notes')
    wants_html = request.POST.get('format') == 'html'

    if not class_name or not section:
        if wants_html:
            messages.error(request, 'Class and section are required.')
            return redirect('select_attendance_class')
        return JsonResponse({'success': False, 'message': 'Class and section are required.'}, status=400)

    if not teacher_can_manage_class(teacher, class_name, section):
        if wants_html:
            messages.error(request, 'You are not assigned to this class.')
            return redirect('select_attendance_class')
        return JsonResponse({'success': False, 'message': 'You are not assigned to this class.'}, status=403)

    students = Student.objects.filter(class_name__iexact=class_name, section__iexact=section)
    if not students.exists():
        if wants_html:
            messages.error(request, 'No students are enrolled in this class.')
            return redirect('select_attendance_class')
        return JsonResponse({'success': False, 'message': 'No students are enrolled in this class.'}, status=400)

    student_statuses = {}
    for student in students:
        status_val = request.POST.get(f'student_{student.enrollment_number}', 'Absent')
        student_statuses[student.enrollment_number] = 'Present' if status_val == 'Present' else 'Absent'

    try:
        result = finalize_attendance(
            teacher=teacher,
            class_name=class_name,
            section=section,
            student_statuses=student_statuses,
            notes=notes
        )
        session_id = result['session_id']
        detail_url = reverse('attendance_detail', args=[session_id])
        export_url = reverse('export_attendance', args=[session_id])

        if wants_html:
            messages.success(request, result['message'])
            return redirect('attendance_detail', session_id=session_id)

        return JsonResponse({
            'success': True,
            'message': result['message'],
            'session_id': session_id,
            'present_count': result['present_count'],
            'absent_count': result['absent_count'],
            'total_count': result['total_count'],
            'detail_url': detail_url,
            'export_url': export_url,
            'redirect_url': detail_url,
        })
    except PermissionDenied as e:
        if wants_html:
            messages.error(request, str(e))
            return redirect('select_attendance_class')
        return JsonResponse({'success': False, 'message': str(e)}, status=403)
    except ValidationError as e:
        if wants_html:
            messages.error(request, str(e))
            return redirect('select_attendance_class')
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        logger.exception("Error finalizing attendance: %s", e)
        if wants_html:
            messages.error(request, 'Failed to save attendance. Please try again.')
            return redirect('select_attendance_class')
        return JsonResponse({'success': False, 'message': 'Failed to save attendance. Please try again.'}, status=500)


# ==================== ATTENDANCE HISTORY & REPORTS ====================

@role_required('teacher')
def attendance_history(request):
    """
    Displays attendance history for all sessions taken by the teacher.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in to view attendance history.')
        return redirect('teacher_login')
    
    try:
        teacher = Teacher.objects.get(id=teacher_id)
        
        # Get filter parameters
        class_filter = request.GET.get('class_name', '')
        section_filter = request.GET.get('section', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        # Base query
        sessions = AttendanceSession.objects.filter(teacher=teacher).order_by('-session_date', '-created_at')
        
        # Apply filters
        if class_filter:
            sessions = sessions.filter(class_name=class_filter)
        if section_filter:
            sessions = sessions.filter(section=section_filter)
        if date_from:
            sessions = sessions.filter(session_date__gte=date_from)
        if date_to:
            sessions = sessions.filter(session_date__lte=date_to)
        
        # Get unique classes and sections for filter dropdowns
        all_sessions = AttendanceSession.objects.filter(teacher=teacher)
        classes = all_sessions.values_list('class_name', flat=True).distinct()
        sections = all_sessions.values_list('section', flat=True).distinct()
        
        # Annotate with present/absent counts
        sessions_with_stats = []
        for session in sessions:
            records = AttendanceRecord.objects.filter(session=session)
            total = records.count()
            present = records.filter(status='Present').count()
            absent = total - present
            percentage = (present / total * 100) if total > 0 else 0
            
            sessions_with_stats.append({
                'session': session,
                'total': total,
                'present': present,
                'absent': absent,
                'percentage': round(percentage, 1)
            })
        
        context = {
            'teacher': teacher,
            'sessions': sessions_with_stats,
            'classes': classes,
            'sections': sections,
            'class_filter': class_filter,
            'section_filter': section_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, 'attendance_history.html', context)
    except Teacher.DoesNotExist:
        request.session.flush()
        messages.error(request, 'Account not found. Please log in again.')
        return redirect('teacher_login')


@role_required('teacher')
def attendance_detail(request, session_id):
    """
    Shows detailed attendance for a specific session.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in.')
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    session = get_object_or_404(AttendanceSession, id=session_id)
    if session.teacher != teacher and not teacher_can_manage_class(teacher, session.class_name, session.section):
        messages.error(request, 'You do not have permission to view attendance for this class.')
        return redirect('teacher_dashboard')

    records = AttendanceRecord.objects.filter(session=session).select_related('student').order_by('student__name')
    
    # Calculate statistics
    total = records.count()
    present = records.filter(status='Present').count()
    absent = total - present
    percentage = (present / total * 100) if total > 0 else 0
    
    context = {
        'session': session,
        'records': records,
        'total': total,
        'present': present,
        'absent': absent,
        'percentage': round(percentage, 1)
    }
    return render(request, 'attendance_detail.html', context)


@role_required('teacher')
def attendance_report(request):
    """
    Generate comprehensive attendance reports with various filters.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in.')
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    assignment = assigned_class(teacher)
    
    # Get filter parameters (support both report_type and legacy type)
    report_type = request.GET.get('report_type') or request.GET.get('type') or 'daily'
    class_name = request.GET.get('class_name', '')
    section = request.GET.get('section', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Default to teacher's assigned class if not specified
    if assignment:
        teacher_class, teacher_sec = assignment
        if not class_name:
            class_name = teacher_class
        if not section:
            section = teacher_sec

    # Calculate date range based on report type
    today = timezone.localdate()
    if report_type == 'daily':
        date_from = today.strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif report_type == 'weekly':
        date_from = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif report_type == 'monthly':
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    
    # Query sessions for this teacher
    sessions = AttendanceSession.objects.filter(teacher=teacher)
    if class_name:
        sessions = sessions.filter(class_name__iexact=class_name)
    if section:
        sessions = sessions.filter(section__iexact=section)
    if date_from:
        sessions = sessions.filter(session_date__gte=date_from)
    if date_to:
        sessions = sessions.filter(session_date__lte=date_to)
    
    # Calculate student-wise statistics
    student_stats = []
    target_class = class_name or (sessions.first().class_name if sessions.exists() else "")
    target_section = section or (sessions.first().section if sessions.exists() else "")
    
    students = Student.objects.none()
    if target_class and target_section:
        students = Student.objects.filter(class_name__iexact=target_class, section__iexact=target_section).order_by('roll_number')
    elif target_class:
        students = Student.objects.filter(class_name__iexact=target_class).order_by('roll_number')
    
    total_present_across = 0
    total_records_across = 0

    for student in students:
        records = AttendanceRecord.objects.filter(session__in=sessions, student=student)
        total_days = records.count()
        present_days = records.filter(status='Present').count()
        absent_days = total_days - present_days
        percentage = round((present_days / total_days * 100), 1) if total_days > 0 else 0

        total_present_across += present_days
        total_records_across += total_days
        
        student_stats.append({
            'student': student,
            'total_days': total_days,
            'present': present_days,
            'absent': absent_days,
            'percentage': percentage
        })

    total_sessions = sessions.count()
    avg_attendance = round((total_present_across / total_records_across * 100), 1) if total_records_across > 0 else 0

    all_sessions = AttendanceSession.objects.filter(teacher=teacher)
    classes = list(all_sessions.values_list('class_name', flat=True).distinct())
    sections = list(all_sessions.values_list('section', flat=True).distinct())
    if assignment:
        if assignment[0] not in classes:
            classes.append(assignment[0])
        if assignment[1] not in sections:
            sections.append(assignment[1])
    
    context = {
        'teacher': teacher,
        'student_stats': student_stats,
        'student_data': student_stats,
        'total_sessions': total_sessions,
        'avg_attendance': avg_attendance,
        'sessions': sessions,
        'report_type': report_type,
        'class_name': class_name,
        'class_filter': class_name,
        'section': section,
        'section_filter': section,
        'date_from': date_from,
        'date_to': date_to,
        'classes': classes,
        'sections': sections,
    }
    return render(request, 'attendance_report.html', context)


@role_required('teacher')
def export_attendance_report(request):
    """
    Export the filtered aggregated attendance report as a CSV.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        return HttpResponse("Unauthorized", status=401)
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    report_type = request.GET.get('report_type') or request.GET.get('type') or 'daily'
    class_name = request.GET.get('class_name', '')
    section = request.GET.get('section', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    today = timezone.localdate()
    if report_type == 'daily':
        date_from = today.strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif report_type == 'weekly':
        date_from = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    elif report_type == 'monthly':
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    
    sessions = AttendanceSession.objects.filter(teacher=teacher)
    if class_name:
        sessions = sessions.filter(class_name__iexact=class_name)
    if section:
        sessions = sessions.filter(section__iexact=section)
    if date_from:
        sessions = sessions.filter(session_date__gte=date_from)
    if date_to:
        sessions = sessions.filter(session_date__lte=date_to)
        
    if class_name and section:
        students = Student.objects.filter(class_name__iexact=class_name, section__iexact=section).order_by('roll_number')
    elif class_name:
        students = Student.objects.filter(class_name__iexact=class_name).order_by('roll_number')
    elif sessions.exists():
        target_classes = sessions.values_list('class_name', flat=True).distinct()
        students = Student.objects.filter(class_name__in=target_classes).order_by('class_name', 'roll_number')
    else:
        students = Student.objects.all().order_by('class_name', 'roll_number')
    
    response = HttpResponse(content_type='text/csv')
    filename = f"attendance_report_{report_type}_{today.strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['Roll Number', 'Enrollment Number', 'Student Name', 'Class', 'Section', 'Total Days', 'Present', 'Absent', 'Attendance %', 'Status'])
    
    for student in students:
        records = AttendanceRecord.objects.filter(session__in=sessions, student=student)
        total_days = records.count()
        present_days = records.filter(status='Present').count()
        absent_days = total_days - present_days
        pct = round((present_days / total_days * 100), 1) if total_days > 0 else 0
        status_label = 'Good' if pct >= 75 else ('Average' if pct >= 60 else 'Poor')
        
        writer.writerow([
            student.roll_number,
            student.enrollment_number,
            student.name,
            student.class_name,
            student.section,
            total_days,
            present_days,
            absent_days,
            f"{pct}%",
            status_label
        ])
    return response


@role_required('teacher')
def export_attendance(request, session_id):
    """
    Export attendance data as CSV.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        return HttpResponse("Unauthorized", status=401)
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    session = get_object_or_404(AttendanceSession, id=session_id)
    if session.teacher != teacher and not teacher_can_manage_class(teacher, session.class_name, session.section):
        return HttpResponse("Forbidden: You cannot export attendance for this class.", status=403)
    
    csv_data = export_session_csv_buffer(session)
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{session.class_name}_{session.section}_{session.session_date}.csv"'
    return response


# ==================== STUDENT MANAGEMENT ====================

@role_required('teacher')
def view_students(request):
    """
    View all students in teacher's assigned class(es).
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in.')
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    class_teacher_for = teacher.class_teacher_for
    classes_assigned = assigned_classes(teacher)
    
    class_filter = request.GET.get('class_name', '').strip()
    section_filter = request.GET.get('section', '').strip()
    search_query = request.GET.get('search', '').strip()
    
    if ("All", "All") in classes_assigned:
        students = Student.objects.all()
        available_classes = sorted(list(Student.objects.values_list('class_name', flat=True).distinct()))
    elif classes_assigned:
        q = Q()
        for c, s in classes_assigned:
            q |= Q(class_name__iexact=c, section__iexact=s)
        students = Student.objects.filter(q)
        available_classes = sorted(list(set(c for c, s in classes_assigned)))
    else:
        students = Student.objects.none()
        available_classes = []
    
    if class_filter:
        students = students.filter(class_name__iexact=class_filter)
    if section_filter:
        students = students.filter(section__iexact=section_filter)
    
    # Apply search
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(roll_number__icontains=search_query) |
            Q(enrollment_number__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    students = students.order_by('class_name', 'section', 'roll_number')
    
    context = {
        'teacher': teacher,
        'students': students,
        'class_teacher_for': class_teacher_for,
        'search_query': search_query,
        'class_filter': class_filter,
        'section_filter': section_filter,
        'classes': available_classes,
    }
    return render(request, 'view_students.html', context)


@role_required('teacher')
def student_detail(request, student_id):
    """
    View detailed information about a specific student including attendance history.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in.')
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    student = get_object_or_404(Student, id=student_id)
    if not teacher_can_manage_student(teacher, student):
        messages.error(request, 'You can view only students in your assigned class.')
        return redirect('view_students')
    
    # Get attendance records for this student
    attendance_records = AttendanceRecord.objects.filter(
        student=student
    ).select_related('session').order_by('-session__session_date')
    
    # Calculate statistics
    total_records = attendance_records.count()
    present_count = attendance_records.filter(status='Present').count()
    absent_count = total_records - present_count
    attendance_percentage = (present_count / total_records * 100) if total_records > 0 else 0
    
    # Get recent attendance (last 30 records)
    recent_records = attendance_records[:30]
    
    context = {
        'teacher': teacher,
        'student': student,
        'attendance_records': recent_records,
        'total_days': total_records,
        'present_days': present_count,
        'absent_days': absent_count,
        'attendance_percentage': round(attendance_percentage, 1),
    }
    return render(request, 'student_detail.html', context)

@require_POST
@role_required('teacher', api=True)
def toggle_attendance(request, record_id):
    """
    Toggle attendance status between Present and Absent
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
    try:
        teacher = Teacher.objects.get(id=teacher_id)
        result = toggle_student_status(teacher, record_id)
        status_code = result.pop('status_code', 200)
        return JsonResponse(result, status=status_code)
    except Teacher.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Teacher not found'}, status=404)
    except Exception as e:
        logger.exception("Error in toggle_attendance: %s", e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@role_required('teacher')
def add_student(request):
    """
    Allow teachers to add new students to their class.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in.')
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    classes_assigned = assigned_classes(teacher)
    if not classes_assigned:
        messages.error(request, 'No class is assigned to your account.')
        return redirect('view_students')
    
    if ("All", "All") in classes_assigned:
        default_class, default_section = "10", "A"
    else:
        default_class, default_section = classes_assigned[0]
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password') or ''
        roll_number = request.POST.get('roll_number')
        enrollment_number = request.POST.get('enrollment_number')
        post_class = (request.POST.get('class_name') or '').strip()
        post_section = (request.POST.get('section') or '').strip()
        
        if post_class and post_section and teacher_can_manage_class(teacher, post_class, post_section):
            class_name, section = post_class, post_section
        else:
            class_name, section = default_class, default_section

        photo = request.FILES.get('photo')
        images = request.FILES.getlist('images')
        
        # Validation
        if Student.objects.filter(enrollment_number=enrollment_number).exists():
            messages.error(request, f"A student with enrollment number '{enrollment_number}' already exists.")
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'form_data': request.POST, 'default_class': class_name, 'default_section': section})
        
        if Student.objects.filter(email=email).exists():
            messages.error(request, f"A student with email '{email}' already exists.")
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'form_data': request.POST, 'default_class': class_name, 'default_section': section})

        if Student.objects.filter(roll_number=roll_number).exists():
            messages.error(request, f"A student with roll number '{roll_number}' already exists.")
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'form_data': request.POST, 'default_class': class_name, 'default_section': section})

        if not password:
            messages.error(request, 'Set a password for the student account.')
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'form_data': request.POST, 'default_class': class_name, 'default_section': section})

        password_errors = password_validation_errors(password)
        if password_errors:
            messages.error(request, ' '.join(password_errors))
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'form_data': request.POST, 'default_class': class_name, 'default_section': section})
        
        if len(images) < 3:
            messages.error(request, 'Please upload at least 3 clear photos for the face dataset.')
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'form_data': request.POST, 'default_class': class_name, 'default_section': section})
        
        # Create student
        student = Student.objects.create(
            name=name,
            email=email,
            password='',
            roll_number=roll_number,
            enrollment_number=enrollment_number,
            class_name=class_name,
            section=section,
            photo=photo
        )
        
        set_password(student, password)
        student.save(update_fields=['password'])

        # Process face dataset with embedding-only approach
        try:
            dataset_path, count, avatar_data = enroll_student_face(enrollment_number, images, name)
            if dataset_path:
                student.dataset_path = dataset_path
                student.save()
                
                # Store avatar data in session for immediate display
                if avatar_data:
                    request.session[f'avatar_{enrollment_number}'] = avatar_data
                
                embedding_size = 12  # Approximate KB per student
                saved_mb = len(images) * 1.5  # Approximate MB saved
                
                messages.success(
                    request, 
                    f'✅ Student {name} registered successfully with AI face recognition! '
                    f'({count} photos processed, {saved_mb:.1f}MB → {embedding_size}KB)'
                )
            else:
                student.save()
                messages.warning(request, f'⚠️ Student registered but face recognition training failed. Only {count} clear faces found (need 3+).')
        except Exception as e:
            student.save()
            messages.warning(request, f'⚠️ Student registered but face recognition setup failed: {str(e)}')
        
        invalidate_embeddings_cache(class_name, section)
        return redirect('view_students')
    
    # Pre-fill class and section from teacher's assigned class
    class_teacher_for = teacher.class_teacher_for
    default_class = ""
    default_section = ""
    if class_teacher_for and class_teacher_for != "Not Assigned" and '-' in class_teacher_for:
        default_class, default_section = class_teacher_for.split('-', 1)
    
    context = {
        'teacher': teacher,
        'default_class': default_class,
        'default_section': default_section,
    }
    return render(request, 'teacher_student_form.html', context)


@role_required('teacher')
def edit_student(request, student_id):
    """
    Allow teachers to edit student information in their class.
    """
    teacher_id = request.session.get('teacher_id')
    if not teacher_id:
        messages.error(request, 'You must be logged in.')
        return redirect('teacher_login')
    
    teacher = get_object_or_404(Teacher, id=teacher_id)
    student = get_object_or_404(Student, id=student_id)
    if not teacher_can_manage_student(teacher, student):
        messages.error(request, 'You can edit only students in your assigned class.')
        return redirect('view_students')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        roll_number = request.POST.get('roll_number')
        enrollment_number = request.POST.get('enrollment_number')
        
        # Uniqueness checks
        if Student.objects.filter(enrollment_number=enrollment_number).exclude(id=student.id).exists():
            messages.error(request, f"A student with enrollment number '{enrollment_number}' already exists.")
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'student': student, 'is_edit': True})

        if Student.objects.filter(email=email).exclude(id=student.id).exists():
            messages.error(request, f"A student with email '{email}' already exists.")
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'student': student, 'is_edit': True})

        if Student.objects.filter(roll_number=roll_number).exclude(id=student.id).exists():
            messages.error(request, f"A student with roll number '{roll_number}' already exists.")
            return render(request, 'teacher_student_form.html', {'teacher': teacher, 'student': student, 'is_edit': True})

        student.name = name
        student.email = email
        student.roll_number = roll_number
        student.enrollment_number = enrollment_number
        # Class placement is controlled by the teacher assignment, not form data.
        student.class_name, student.section = assigned_class(teacher)
        
        if request.POST.get('password'):
            password_errors = password_validation_errors(request.POST.get('password'))
            if password_errors:
                messages.error(request, ' '.join(password_errors))
                return render(request, 'teacher_student_form.html', {'teacher': teacher, 'student': student, 'is_edit': True})
            set_password(student, request.POST.get('password'))
        
        if request.FILES.get('photo'):
            student.photo = request.FILES.get('photo')
        
        images = request.FILES.getlist('images')
        if images and len(images) >= 3:
            try:
                dataset_path, count, avatar_data = enroll_student_face(student.enrollment_number, images, student.name)
                if dataset_path:
                    student.dataset_path = dataset_path
                    
                    # Update avatar data in session
                    if avatar_data:
                        request.session[f'avatar_{student.enrollment_number}'] = avatar_data
                    
                    embedding_size = 12  # Approximate KB per student
                    saved_mb = len(images) * 1.5  # Approximate MB saved
                    
                    messages.success(
                        request, 
                        f'✅ Student {student.name} updated successfully with new face data! '
                        f'({count} photos processed, {saved_mb:.1f}MB → {embedding_size}KB)'
                    )
                else:
                    messages.warning(request, f'⚠️ Student updated but face recognition training failed. Only {count} clear faces found (need 3+).')
            except Exception as e:
                messages.warning(request, f'⚠️ Student updated but face recognition update failed: {str(e)}')
        
        student.save()
        invalidate_embeddings_cache(student.class_name, student.section)
        messages.success(request, f'Student {student.name} updated successfully!')
        return redirect('view_students')
    
    context = {
        'teacher': teacher,
        'student': student,
        'is_edit': True,
        'default_class': '',
        'default_section': '',
    }
    return render(request, 'teacher_student_form.html', context)
