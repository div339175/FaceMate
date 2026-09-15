from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.developer_login, name='developer_login'),
    path('demo-login/', views.developer_demo_login, name='developer_demo_login'),
    path('dashboard/', views.developer_dashboard, name='developer_dashboard'),
    path('logout/', views.developer_logout, name='developer_logout'),
    
    # URLs for Teacher Management (from previous steps)
    path('teachers/register/', views.teacher_register, name='teacher_register'),
    path('teachers/manage/', views.manage_teachers, name='manage_teachers'),
    path('teachers/edit/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),

    # URLs for Student Management (from previous steps)
    path('students/register/', views.student_register, name='student_register'),
    path('students/manage/', views.manage_students, name='manage_students'),
    # Use a unique name to avoid clashing with teacher.edit_student
    path('students/edit/<int:student_id>/', views.edit_student, name='dev_edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='dev_delete_student'),
    
    # 🚀 EMBEDDING-ONLY OPTIMIZATION URLs
    path('cleanup-photos/', views.cleanup_legacy_photos, name='cleanup_legacy_photos'),
    path('generate-avatar/<int:student_id>/', views.generate_student_avatar, name='generate_student_avatar'),
]
