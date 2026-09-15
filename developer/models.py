from django.db import models
from django.contrib.auth.hashers import make_password

class Developer(models.Model):
    """
    Represents the developer/administrator of the system.
    """
    name = models.CharField(max_length=120)
    email = models.CharField(max_length=120, unique=True)
    password = models.CharField(max_length=128)


    def __str__(self):
        return self.name

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
    
