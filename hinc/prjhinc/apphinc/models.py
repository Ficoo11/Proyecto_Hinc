from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=[('Admin', 'Admin'), ('Usuario', 'Usuario')], default='Usuario')
    estado = models.CharField(max_length=20, choices=[('Habilitado', 'Habilitado'), ('Inhabilitado', 'Inhabilitado')], default='Habilitado')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'usuario'