from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from decimal import Decimal

class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=[('Admin', 'Admin'), ('Usuario', 'Usuario')], default='Usuario')
    estado = models.CharField(max_length=20, choices=[('Habilitado', 'Habilitado'), ('Inhabilitado', 'Inhabilitado')], default='Habilitado')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'usuario'

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='categorias/', blank=True, null=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    tallas = models.CharField(max_length=100, help_text="Tallas separadas por comas, e.g., 'S,M,L'")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    descripcion = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    stock = models.IntegerField(default=0)
    descuento = models.IntegerField(
        choices=[(i, f"{i}%") for i in range(0, 101, 5)],
        default=0
    )
    estado = models.CharField(
        max_length=20,
        choices=[('Habilitado', 'Habilitado'), ('Inhabilitado', 'Inhabilitado'), ('Agotado', 'Agotado')],
        default='Habilitado'
    )
    is_destacado = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    def precio_con_descuento(self):
        return self.precio * Decimal(1 - self.descuento / 100)

class Carrito(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carrito')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

    def obtener_total(self):
        return sum(item.obtener_total() for item in self.items.all())

    def obtener_cantidad_total(self):
        return sum(item.cantidad for item in self.items.all())

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    agregado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    def obtener_total(self):
        return self.producto.precio * self.cantidad

    class Meta:
        unique_together = ('carrito', 'producto')