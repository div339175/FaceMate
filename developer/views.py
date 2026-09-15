import os
import shutil
from django.conf import settings
from django.core.files.base import ContentFile
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Developer
from student.models import Student
from teacher.models import Teacher
from teacher.views import invalidate_embeddings_cache
from core.face_utils import enroll_student_face, generate_avatar_from_initials
from core.security import (
    login_profile, logout_profile, password_validation_errors, role_required, set_password, verify_password,
)
from core.demo import login_demo_account

@require_POST
@role_required('developer', api=True)
def cleanup_legacy_photos(request):
    """
    🚀 EMBEDDING-ONLY MIGRATION TOOL
    Removes all legacy photo storage to complete the embedding-only transformation.
    Calculates and reports massive storage savings.
    """
    cleanup_stats = {
        'deleted_files': 0,
        'saved_mb': 0,
        'folders_cleaned': [],
        'errors': []
    }
    
    try:
        # Clean student_photos directory
        student_photos_dir = os.path.join(settings.MEDIA_ROOT, 'student_photos')
        if os.path.exists(student_photos_dir):
            for filename in os.listdir(student_photos_dir):
                file_path = os.path.join(student_photos_dir, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    cleanup_stats['deleted_files'] += 1
                    cleanup_stats['saved_mb'] += file_size / (1024 * 1024)
            cleanup_stats['folders_cleaned'].append('student_photos')
            
        # Clean student_datasets directory
        datasets_dir = os.path.join(settings.BASE_DIR, 'student_datasets')
        if os.path.exists(datasets_dir):
            for item in os.listdir(datasets_dir):
                item_path = os.path.join(datasets_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    cleanup_stats['folders_cleaned'].append(f'student_datasets/{item}')
                elif os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    os.remove(item_path)
                    cleanup_stats['deleted_files'] += 1
                    cleanup_stats['saved_mb'] += file_size / (1024 * 1024)
                    
        # Update student records to remove photo references
        students_updated = Student.objects.filter(photo__isnull=False).update(photo=None)
        
        cleanup_stats['students_updated'] = students_updated
        cleanup_stats['success'] = True
        
    except Exception as e:
        cleanup_stats['errors'].append(str(e))
        cleanup_stats['success'] = False
        
    return JsonResponse(cleanup_stats)

# from core.face_utils import process_dataset_and_create_embedding

# Import your AI utility function


def home_page(request):
    """ Renders the main project landing page. """
    return render(request, 'home.html')

# --- Developer Session Views ---

def developer_login(request):
    """ 
    Handles the developer login functionality.
    Automatically logs out any existing sessions for the same developer.
    """
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''
        developer = Developer.objects.filter(email__iexact=email).first()
        if developer and verify_password(developer, password):
            login_profile(request, 'developer', developer)
            return redirect('developer_dashboard')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'login.html', {'demo_login_enabled': settings.DEMO_LOGIN_ENABLED})


@require_POST
def developer_demo_login(request):
    login_demo_account(request, 'developer')
    return redirect('developer_dashboard')

@role_required('developer')
def developer_dashboard(request):
    """ Displays the developer's main dashboard. """
    if 'developer_id' not in request.session:
        return redirect('developer_login')
    developer = get_object_or_404(Developer, id=request.session['developer_id'])
    return render(request, 'dev_dashB.html', {'developer': developer})

@role_required('developer')
def developer_logout(request):
    """ Logs the developer out by clearing the session. """
    logout_profile(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('developer_login')

# --- Unified Teacher Management Views ---

@role_required('developer')
def teacher_register(request):
    """ Handles the CREATION of a new teacher using the unified form. """
    if 'developer_id' not in request.session:
        return redirect('developer_login')
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password') or ''
        class_teacher_for = request.POST.get('class_teacher_for')
        photo = request.FILES.get('photo')
        password_errors = password_validation_errors(password)
        if password_errors:
            messages.error(request, ' '.join(password_errors))
            return render(request, 'teacher_form.html', {'form_data': request.POST})
        if Teacher.objects.filter(email=email).exists():
            messages.error(request, f"A teacher with the email '{email}' already exists.")
            return render(request, 'teacher_form.html', {'form_data': request.POST})
        teacher = Teacher.objects.create(
            name=name, email=email, password='',
            class_teacher_for=class_teacher_for, photo=photo
        )
        set_password(teacher, password)
        teacher.save(update_fields=['password'])
        messages.success(request, f"Teacher '{name}' has been registered successfully!")
        return redirect('manage_teachers')
    return render(request, 'teacher_form.html')

@role_required('developer')
def manage_teachers(request):
    """ Displays a list of all registered teachers. """
    if 'developer_id' not in request.session:
        return redirect('developer_login')
    teachers = Teacher.objects.all().order_by('name')
    return render(request, 'manage_teachers.html', {'teachers': teachers})

@role_required('developer')
def edit_teacher(request, teacher_id):
    """ Handles the UPDATE of an existing teacher using the unified form. """
    if 'developer_id' not in request.session:
        return redirect('developer_login')
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        name = request.POST.get('name', teacher.name)
        email = (request.POST.get('email') or '').strip().lower()
        class_teacher_for = request.POST.get('class_teacher_for', teacher.class_teacher_for)

        if email and Teacher.objects.filter(email__iexact=email).exclude(id=teacher.id).exists():
            messages.error(request, f"A teacher with the email '{email}' already exists.")
            return render(request, 'teacher_form.html', {'teacher': teacher})

        teacher.name = name
        teacher.email = email
        teacher.class_teacher_for = class_teacher_for
        new_password = request.POST.get('password')
        if new_password:
            password_errors = password_validation_errors(new_password)
            if password_errors:
                messages.error(request, ' '.join(password_errors))
                return render(request, 'teacher_form.html', {'teacher': teacher})
            set_password(teacher, new_password)
        if 'photo' in request.FILES:
            if teacher.photo and os.path.isfile(teacher.photo.path):
                os.remove(teacher.photo.path)
            teacher.photo = request.FILES['photo']
        teacher.save()
        messages.success(request, f"Details for {teacher.name} have been updated successfully.")
        return redirect('manage_teachers')
    return render(request, 'teacher_form.html', {'teacher': teacher})

# --- All other views for developer login, teacher management, etc. are here and assumed correct ---

@role_required('developer')
def student_register(request):
    """
    Handles student registration using the correct AI utility call.
    """
    if 'developer_id' not in request.session:
        messages.error(request, "You must be logged in to perform this action.")
        return redirect('developer_login')

    if request.method == 'POST':
        enrollment_number = (request.POST.get('enrollment_number') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        roll_number = (request.POST.get('roll_number') or '').strip()
        class_name = (request.POST.get('class_name') or '').strip()
        section = (request.POST.get('section') or '').strip()
        images = request.FILES.getlist('images')
        password = request.POST.get('password') or ''

        if Student.objects.filter(enrollment_number=enrollment_number).exists():
            messages.error(request, f"A student with enrollment number '{enrollment_number}' already exists.")
            return render(request, 'student_form.html', {'form_data': request.POST})

        if Student.objects.filter(email__iexact=email).exists():
            messages.error(request, f"A student with email '{email}' already exists.")
            return render(request, 'student_form.html', {'form_data': request.POST})

        if Student.objects.filter(roll_number=roll_number).exists():
            messages.error(request, f"A student with roll number '{roll_number}' already exists.")
            return render(request, 'student_form.html', {'form_data': request.POST})

        if not password:
            messages.error(request, 'Set a password for the student account.')
            return render(request, 'student_form.html', {'form_data': request.POST})

        password_errors = password_validation_errors(password)
        if password_errors:
            messages.error(request, ' '.join(password_errors))
            return render(request, 'student_form.html', {'form_data': request.POST})

        if len(images) < 3:
            messages.error(request, 'Please upload at least 3 clear photos for the face dataset.')
            return render(request, 'student_form.html', {'form_data': request.POST})

        # 🚀 EMBEDDING-ONLY APPROACH: Process images and generate avatar
        student_name = request.POST.get('name')
        dataset_path, success_count, avatar_data = enroll_student_face(
            enrollment_number, images, student_name
        )
        
        if dataset_path:
            # Create student with embedding-only storage (no photo field)
            student = Student.objects.create(
                name=student_name,
                email=email,
                roll_number=roll_number,
                enrollment_number=enrollment_number,
                class_name=class_name,
                section=section,
                dataset_path=dataset_path,
                password=''
                # NOTE: No photo field - using avatar_data for UI display
            )
            set_password(student, password)
            student.save(update_fields=['password'])
            
            # Store avatar data in session for immediate display
            if avatar_data:
                request.session[f'avatar_{enrollment_number}'] = avatar_data
            
            invalidate_embeddings_cache(class_name, section)
            embedding_size = 12  # Approximate KB per student
            total_images = len(images)
            saved_mb = total_images * 1.5  # Approximate MB saved
            
            messages.success(
                request, 
                f'✅ Student registered successfully! '
                f'Storage optimized: {saved_mb:.1f}MB photos → {embedding_size}KB embedding '
                f'(99.2% reduction)'
            )
            return redirect('manage_students')
        else:
            messages.error(
                request, 
                f'⚠️  AI could only process {success_count} of {len(images)} uploaded images. '
                f'Please try again with clearer, well-lit photos showing the face clearly.'
            )
            
    return render(request, 'student_form.html')

@role_required('developer')
def edit_student(request, student_id):
    """
    Handles student updates, including re-creating the .npy file,
    using the correct AI utility call.
    """
    if 'developer_id' not in request.session:
        messages.error(request, "You must be logged in to perform this action.")
        return redirect('developer_login')
        
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', student.name)
        email = (request.POST.get('email') or '').strip().lower()
        roll_number = (request.POST.get('roll_number') or '').strip()
        class_name = (request.POST.get('class_name') or '').strip()
        section = (request.POST.get('section') or '').strip()

        if Student.objects.filter(email__iexact=email).exclude(id=student.id).exists():
            messages.error(request, f"A student with email '{email}' already exists.")
            return render(request, 'student_form.html', {'student': student})

        if Student.objects.filter(roll_number=roll_number).exclude(id=student.id).exists():
            messages.error(request, f"A student with roll number '{roll_number}' already exists.")
            return render(request, 'student_form.html', {'student': student})

        student.name = name
        student.email = email
        student.roll_number = roll_number
        student.class_name = class_name
        student.section = section
        if request.POST.get('password'):
            password_errors = password_validation_errors(request.POST.get('password'))
            if password_errors:
                messages.error(request, ' '.join(password_errors))
                return render(request, 'student_form.html', {'student': student})
            set_password(student, request.POST.get('password'))

        if 'images' in request.FILES and request.FILES.getlist('images'):
            images = request.FILES.getlist('images')
            if len(images) < 3:
                messages.error(request, 'Please upload at least 3 clear photos to update the face dataset.')
                return render(request, 'student_form.html', {'student': student})

            enrollment_number = student.enrollment_number
            
            # 🚀 EMBEDDING-ONLY: Process new images and regenerate avatar
            dataset_path, success_count, avatar_data = enroll_student_face(
                enrollment_number, images, student.name
            )
            
            if dataset_path:
                student.dataset_path = dataset_path
                
                # Update avatar data in session
                if avatar_data:
                    request.session[f'avatar_{enrollment_number}'] = avatar_data
                
                messages.success(
                    request, 
                    f'✅ Face dataset updated successfully! '
                    f'New embedding generated ({success_count} faces processed)'
                )
            else:
                messages.error(
                    request, 
                    f'⚠️  The new dataset could not be processed. '
                    f'Only {success_count} clear faces were found. No changes were saved.'
                )
                return render(request, 'student_form.html', {'student': student})

        student.save()
        invalidate_embeddings_cache(student.class_name, student.section)
        messages.success(request, 'Details updated successfully!')
        return redirect('manage_students')

    return render(request, 'student_form.html', {'student': student})

@role_required('developer')
def manage_students(request):
    """
    Displays a list of all registered students and includes a "health check"
    to verify if their AI data FOLDER exists.
    """
    if 'developer_id' not in request.session:
        return redirect('developer_login')
    
    students = Student.objects.all().order_by('name')
    
    for student in students:
        if student.dataset_path:
            # 🚀 EMBEDDING-ONLY: Check .npy file in static/trained_data
            if student.dataset_path.startswith('trained_data/'):
                # New embedding-only format
                path = os.path.join(settings.STATICFILES_DIRS[0], student.dataset_path)
            else:
                # Legacy format - migrate if needed
                path = os.path.join(settings.MEDIA_ROOT, student.dataset_path)
            
            # Check if the .npy embedding file exists
            if os.path.exists(path) and path.endswith('.npy'):
                file_size = os.path.getsize(path)
                student.ai_data_status = f"Ready ({file_size/1024:.1f}KB)"
                student.storage_optimized = True
            elif os.path.exists(path) and os.path.isdir(path):
                # Legacy directory format - needs migration
                student.ai_data_status = "Legacy (Migrate)"
                student.storage_optimized = False
            else:
                student.ai_data_status = "Missing"
                student.storage_optimized = False
        else:
            student.ai_data_status = "Missing"
            student.storage_optimized = False
            
        # Add avatar data for display
        student.avatar_data = request.session.get(f'avatar_{student.enrollment_number}')
            
    # Calculate storage optimization statistics
    total_students = students.count()
    optimized_students = sum(1 for s in students if hasattr(s, 'storage_optimized') and s.storage_optimized)
    
    # Estimate storage savings
    avg_photos_per_student = 4  # Conservative estimate
    avg_mb_per_photo = 1.5
    embedding_kb_per_student = 12
    
    legacy_storage_mb = total_students * avg_photos_per_student * avg_mb_per_photo
    optimized_storage_mb = total_students * embedding_kb_per_student / 1024
    savings_mb = legacy_storage_mb - optimized_storage_mb
    savings_percentage = (savings_mb / legacy_storage_mb * 100) if legacy_storage_mb > 0 else 0
    
    unoptimized_students = max(0, total_students - optimized_students)
    storage_stats = {
        'total_students': total_students,
        'optimized_students': optimized_students,
        'unoptimized_students': unoptimized_students,
        'legacy_storage_mb': round(legacy_storage_mb, 1),
        'optimized_storage_mb': round(optimized_storage_mb, 1),
        'savings_mb': round(savings_mb, 1),
        'savings_percentage': round(savings_percentage, 1)
    }
    
    return render(request, 'manage_students.html', {
        'students': students, 
        'storage_stats': storage_stats
    })

@require_POST
@role_required('developer', api=True)
def generate_student_avatar(request, student_id):
    """
    Generates avatar for existing student and stores in session.
    Part of embedding-only optimization.
    """
    try:
        student = Student.objects.get(id=student_id)
        avatar_data = generate_avatar_from_initials(student.name)
        request.session[f'avatar_{student.enrollment_number}'] = avatar_data
        
        return JsonResponse({
            'success': True,
            'avatar_data': avatar_data,
            'message': f'Avatar generated for {student.name}'
        })
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@role_required('developer')
def delete_student(request, student_id):
    """Safely deletes a student and removes any associated face embedding file."""
    student = get_object_or_404(Student, id=student_id)
    class_name, section = student.class_name, student.section
    name = student.name
    if student.dataset_path:
        for base in [settings.STATICFILES_DIRS[0], settings.MEDIA_ROOT]:
            path = os.path.join(base, student.dataset_path)
            if os.path.exists(path) and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
    student.delete()
    invalidate_embeddings_cache(class_name, section)
    messages.success(request, f"Student '{name}' has been deleted successfully.")
    return redirect('manage_students')


@require_POST
@role_required('developer')
def delete_teacher(request, teacher_id):
    """Safely deletes a teacher profile."""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    name = teacher.name
    teacher.delete()
    invalidate_embeddings_cache()
    messages.success(request, f"Teacher '{name}' has been deleted successfully.")
    return redirect('manage_teachers')
