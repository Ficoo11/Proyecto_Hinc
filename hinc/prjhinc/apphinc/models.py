from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from decimal import Decimal
# Define los modelos de la base de datos para la tienda en línea, gestionando usuarios, categorías, productos y carritos de compra. Incluye un modelo personalizado de usuario (CustomUser) con roles y estados, un modelo para categorías (Categoria) con nombre, descripción e imagen, un modelo para productos (Producto) con detalles como precio, tallas y descuentos, y modelos para carritos (Carrito) e ítems de carrito (ItemCarrito) que manejan las compras de los usuarios. Los modelos usan relaciones (ForeignKey, OneToOneField) para conectar datos y métodos personalizados para cálculos como precios con descuento y totales del carrito, soportando la lógica del sistema de comercio electrónico.
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
    stock = models.IntegerField(default=0)  # Stock general (calculado)
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
    
    def actualizar_stock_general(self):
        """Actualiza el stock general basado en el stock por tallas"""
        total_stock = sum(stock.stock for stock in self.stocktalla_set.all())
        self.stock = total_stock
        # Actualizar estado basado en stock
        if total_stock == 0:
            self.estado = 'Agotado'
        elif self.estado == 'Agotado' and total_stock > 0:
            self.estado = 'Habilitado'
        self.save()
    
    def obtener_stock_por_talla(self, talla):
        """Obtiene el stock para una talla específica"""
        try:
            stock_talla = self.stocktalla_set.get(talla=talla)
            return stock_talla.stock
        except StockTalla.DoesNotExist:
            return 0
    
    def tiene_stock_bajo(self):
        """Verifica si alguna talla tiene stock bajo (<= 10)"""
        return self.stocktalla_set.filter(stock__lte=10).exists()
    
    def get_tallas_con_stock_bajo(self):
        """Obtiene las tallas con stock bajo"""
        return self.stocktalla_set.filter(stock__lte=10)

class StockTalla(models.Model):
    TALLAS_CHOICES = [
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    talla = models.CharField(max_length=10, choices=TALLAS_CHOICES)
    stock = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('producto', 'talla')
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.talla}: {self.stock}"

class Carrito(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carrito')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Carrito de {self.usuario.username}"
    
    def obtener_total(self):
        total = sum(float(item.obtener_total()) for item in self.items.all())
        return total

    def obtener_cantidad_total(self):
        return sum(int(item.cantidad) for item in self.items.all())

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    talla = models.CharField(max_length=10, choices=StockTalla.TALLAS_CHOICES)
    agregado_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} ({self.talla})"
    
    def obtener_total(self):
        return float(self.producto.precio) * int(self.cantidad)
    
    class Meta:
        unique_together = ('carrito', 'producto', 'talla')