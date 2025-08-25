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

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    tallas = models.CharField(max_length=100, help_text="Tallas separadas por comas, e.g., 'S,M,L'")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=50, choices=[('Hombre', 'Hombre'), ('Mujer', 'Mujer'), ('Accesorios', 'Accesorios')], default='Hombre')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre