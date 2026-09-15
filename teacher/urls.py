from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.teacher_login, name='teacher_login'),
    path('demo-login/', views.teacher_demo_login, name='teacher_demo_login'),
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('logout/', views.teacher_logout, name='teacher_logout'),
    path('attendance/select-class/', views.select_attendance_class, name='select_attendance_class'),
    
    # This URL displays the live camera feed and the student roster.
    path('attendance/live/', views.live_attendance, name='live_attendance'),
    
    # This URL handles the final submission of the attendance data.
    path('attendance/save/', views.save_attendance, name='save_attendance'),
    path('attendance/recognize/', views.recognize_frame, name='recognize_frame'),
    
    # Attendance History & Reports
    path('attendance/history/', views.attendance_history, name='attendance_history'),
    path('attendance/history/<int:session_id>/', views.attendance_detail, name='attendance_detail'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),
    path('attendance/report/export/', views.export_attendance_report, name='export_attendance_report'),
    path('attendance/export/<int:session_id>/', views.export_attendance, name='export_attendance'),
    path('attendance/toggle/<int:record_id>/', views.toggle_attendance, name='toggle_attendance'),
    
    # Student Management
    path('students/', views.view_students, name='view_students'),
    path('student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/<int:student_id>/edit/', views.edit_student, name='edit_student'),
]
