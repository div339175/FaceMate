from django.urls import path
from . import views

urlpatterns = [
    # Student authentication (registration disabled for security)
    path('login/', views.student_login, name='student_login'),
    path('demo-login/', views.student_demo_login, name='student_demo_login'),
    path('logout/', views.student_logout, name='student_logout'),
    
    # Student dashboard and features
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('attendance/', views.student_attendance_history, name='student_attendance_history'),
    path('profile/', views.student_profile, name='student_profile'),
]
