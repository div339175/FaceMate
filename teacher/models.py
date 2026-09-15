from django.db import models
from django.contrib.auth.hashers import make_password


class Teacher(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    courses = models.CharField(max_length=255, blank=True, default="")
    photo = models.ImageField(upload_to='teacher_photos/', blank=True, null=True)
    class_teacher_for = models.CharField(max_length=100, default="Not Assigned")


    def __str__(self):
        return self.name

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
