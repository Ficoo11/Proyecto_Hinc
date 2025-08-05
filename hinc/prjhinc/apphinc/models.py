from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=[('usuario', 'Usuario'), ('administrador', 'Administrador')], default='usuario')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email