from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from decimal import Decimal

class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=[('Admin', 'Admin'), ('Usuario', 'Usuario')], default='Usuario')
    estado = models.CharField(max_length=20, choices=[('Habilitado', 'Habilitado'), ('Inhabilitado', 'Inhabilitado')], default='Habilitado')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NUEVOS CAMPOS PARA EL PERFIL
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    documento = models.CharField(max_length=20, blank=True, null=True)
    genero = models.CharField(max_length=10, choices=[
        ('M', 'Masculino'), 
        ('F', 'Femenino'), 
        ('O', 'Otro')
    ], blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    telefono_personal = models.CharField(max_length=15, blank=True, null=True)
    
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
    
    def actualizar_stock_general(self):
        total_stock = sum(stock.stock for stock in self.stocktalla_set.all())
        self.stock = total_stock
        if total_stock == 0:
            self.estado = 'Agotado'
        elif self.estado == 'Agotado' and total_stock > 0:
            self.estado = 'Habilitado'
        self.save()
    
    def obtener_stock_por_talla(self, talla):
        try:
            stock_talla = self.stocktalla_set.get(talla=talla)
            return stock_talla.stock
        except StockTalla.DoesNotExist:
            return 0
    
    def tiene_stock_bajo(self):
        return self.stocktalla_set.filter(stock__lte=10).exists()
    
    def get_tallas_con_stock_bajo(self):
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
    stock_inicial = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('producto', 'talla')
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.talla}: {self.stock}"
    
    def save(self, *args, **kwargs):
        if self.pk is None and self.stock_inicial == 0 and self.stock > 0:
            self.stock_inicial = self.stock
        elif self.stock_inicial == 0 and self.stock > 0:
            self.stock_inicial = self.stock
        super().save(*args, **kwargs)
    
    def obtener_porcentaje_stock(self):
        if self.stock_inicial == 0:
            return 0
        return (self.stock / self.stock_inicial) * 100
    
    def obtener_estado_stock(self):
        porcentaje = self.obtener_porcentaje_stock()
        if porcentaje == 0:
            return 'agotado', 'Agotado', 'red'
        elif porcentaje <= 10:
            return 'critico', 'Crítico (≤10%)', 'red'
        elif porcentaje <= 25:
            return 'bajo', 'Bajo (≤25%)', 'orange'
        elif porcentaje <= 50:
            return 'medio', 'Medio (≤50%)', 'yellow'
        else:
            return 'normal', 'Normal (>50%)', 'green'

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

class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    
    METODOS_PAGO = [
        ('tarjeta', 'Tarjeta de Crédito/Débito'),
        ('paypal', 'PayPal'),
        ('transferencia', 'Transferencia Bancaria'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pedidos')
    numero_pedido = models.CharField(max_length=20, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO, default='pendiente')
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='tarjeta')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    nombre_completo = models.CharField(max_length=200, default="Admin")
    email = models.EmailField(default="Admin@gmail.com")
    direccion_envio = models.TextField(default="Dirección no especificada")
    ciudad = models.CharField(max_length=100, default="Ciudad no especificada")
    telefono = models.CharField(max_length=20, default="0000000000")
    
    numero_tarjeta = models.CharField(max_length=20, blank=True, null=True)
    fecha_expiracion = models.CharField(max_length=10, blank=True, null=True)
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.usuario.username}"
    
    def generar_numero_pedido(self):
        import random
        import string
        return 'PED' + ''.join(random.choices(string.digits, k=7))
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            self.numero_pedido = self.generar_numero_pedido()
        super().save(*args, **kwargs)
    
    def obtener_estado_color(self):
        colores = {
            'pendiente': 'yellow',
            'confirmado': 'blue',
            'procesando': 'orange',
            'enviado': 'purple',
            'entregado': 'green',
            'cancelado': 'red',
        }
        return colores.get(self.estado, 'gray')
    
    def es_reciente(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.creado_en >= timezone.now() - timedelta(days=1)

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    talla = models.CharField(max_length=10)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} ({self.talla}) - Pedido {self.pedido.numero_pedido}"
    
    def obtener_total(self):
        return self.precio * self.cantidad