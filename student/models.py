from django.db import models
from django.contrib.auth.hashers import make_password

class Student(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, default="")
    roll_number = models.CharField(max_length=50, unique=True)
    enrollment_number = models.CharField(max_length=50, unique=True)
    class_name = models.CharField(max_length=50, default="Not Assigned") 
    section = models.CharField(max_length=50, default="A")
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    
    # This is the correct field for storing the path to the dataset folder.
    # The old 'embedding_path' has been removed.
    dataset_path = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.enrollment_number})"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
