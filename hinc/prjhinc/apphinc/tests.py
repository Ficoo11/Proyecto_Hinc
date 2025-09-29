import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import CustomUser, Categoria, Producto, Carrito, ItemCarrito
from .forms import CustomUserCreationForm, LoginForm, ProductoForm, CategoriaForm, InventoryForm
from decimal import Decimal

class ProjectTests(TestCase):
    def setUp(self):
        # Configura el entorno inicial para todas las pruebas, creando un cliente HTTP, usuarios, una categoría y un producto.
        self.client = Client()
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'role': 'Usuario',
            'estado': 'Habilitado'
        }
        self.admin_data = {
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'adminpassword123',
            'role': 'Admin',
            'estado': 'Habilitado'
        }
        self.user = CustomUser.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password'],
            role=self.user_data['role'],
            estado=self.user_data['estado']
        )
        self.admin = CustomUser.objects.create_user(
            username=self.admin_data['username'],
            email=self.admin_data['email'],
            password=self.admin_data['password'],
            role=self.admin_data['role'],
            estado=self.admin_data['estado']
        )
        self.categoria = Categoria.objects.create(
            nombre='Test Categoria',
            descripcion='Descripcion de prueba'
        )
        self.producto = Producto.objects.create(
            nombre='Test Producto',
            precio=Decimal('100.00'),
            tallas='S,M,L',
            descripcion='Descripcion de producto',
            categoria=self.categoria,
            stock=10,
            descuento=10,
            estado='Habilitado',
            is_destacado=True
        )

    def test_index_view(self):
        # Prueba la vista 'index' que muestra la página principal.
        # Verifica que la vista responda con un código 200, use el template 'index2.html',
        # y contenga los contextos 'productos_destacados', 'categorias' y 'ofertas' con hasta 4 elementos cada uno.
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index2.html')
        self.assertIn('productos_destacados', response.context)
        self.assertIn('categorias', response.context)
        self.assertIn('ofertas', response.context)
        self.assertTrue(response.context['productos_destacados'].count() <= 4)
        self.assertTrue(response.context['ofertas'].count() <= 4)

    def test_register_view_success(self):
        # Prueba la vista 'register' para el registro de un nuevo usuario.
        # Envía datos válidos a través de POST y verifica que redirija a la página de login,
        # que el usuario se cree correctamente en la base de datos, y que los datos (email y contraseña) sean correctos.
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'role': 'Usuario',
            'estado': 'Habilitado'
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(CustomUser.objects.filter(username='newuser').exists())
        new_user = CustomUser.objects.get(username='newuser')
        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertTrue(new_user.check_password('newpassword123'))

    def test_login_view_success(self):
        # Prueba la vista 'login' para el inicio de sesión de un usuario.
        # Envía credenciales válidas a través de POST y verifica que redirija a la página principal,
        # que el usuario esté autenticado en la sesión, y que el ID del usuario en la sesión sea correcto.
        response = self.client.post(reverse('login'), {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.assertRedirects(response, reverse('index'))
        self.assertTrue('_auth_user_id' in self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.id)

    def test_logout_view(self):
        # Prueba la vista 'logout' para cerrar la sesión de un usuario.
        # Inicia sesión, accede a la vista de logout, y verifica que redirija a la página principal
        # y que el usuario ya no esté autenticado en la sesión.
        self.client.login(email=self.user.email, password=self.user_data['password'])
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('index'))
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_paneladmin_view_as_admin(self):
        # Prueba la vista 'paneladmin' para usuarios con rol 'Admin'.
        # Inicia sesión como admin, accede al panel de administración, y verifica que responda con un código 200,
        # use el template 'paneladmin.html', y contenga los contextos 'users', 'productos' y 'categorias' con datos.
        self.client.login(email=self.admin.email, password=self.admin_data['password'])
        response = self.client.get(reverse('paneladmin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'paneladmin.html')
        self.assertIn('users', response.context)
        self.assertIn('productos', response.context)
        self.assertIn('categorias', response.context)
        self.assertTrue(response.context['users'].count() >= 2)
        self.assertTrue(response.context['productos'].count() >= 1)
        self.assertTrue(response.context['categorias'].count() >= 1)

    def test_add_to_cart(self):
        # Prueba la vista 'agregar_al_carrito' para añadir un producto al carrito de un usuario autenticado.
        # Inicia sesión, envía un JSON con el ID del producto y cantidad vía POST, y verifica que la respuesta sea exitosa (200),
        # que el carrito se cree con un item, y que el item tenga la cantidad y producto correctos.
        self.client.login(email=self.user.email, password=self.user_data['password'])
        data = {'producto_id': self.producto.id, 'cantidad': 2}
        response = self.client.post(
            reverse('agregar_al_carrito'),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])
        carrito = Carrito.objects.get(usuario=self.user)
        self.assertEqual(carrito.items.count(), 1)
        item = carrito.items.first()
        self.assertEqual(item.cantidad, 2)
        self.assertEqual(item.producto.id, self.producto.id)

    def test_categorias_view_as_admin(self):
        # Prueba la vista 'categorias' para usuarios con rol 'Admin'.
        # Inicia sesión como admin, accede a la vista de categorías, y verifica que responda con un código 200,
        # use el template 'PAcategorias.html', contenga los contextos 'categorias' y 'form',
        # y que 'action' y 'categoria' sean None para una solicitud GET predeterminada.
        self.client.login(email=self.admin.email, password=self.admin_data['password'])
        response = self.client.get(reverse('categorias'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'PAcategorias.html')
        self.assertIn('categorias', response.context)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['categorias'].count() >= 1)
        self.assertIsNone(response.context['action'])
        self.assertIsNone(response.context['categoria'])

    def test_producto_form_validation(self):
        # Prueba la validación del formulario 'ProductoForm' para crear un producto.
        # Crea un formulario con datos válidos, verifica que sea válido, guarda el producto,
        # y comprueba que los campos (tallas, nombre, precio, stock, descuento) se guarden correctamente.
        form_data = {
            'nombre': 'Nuevo Producto',
            'precio': '50.00',
            'tallas': ['S', 'M'],
            'descripcion': 'Descripcion de prueba',
            'categoria': self.categoria.id,
            'stock': 5,
            'descuento': 5,
            'estado': 'Habilitado',
            'is_destacado': False
        }
        form = ProductoForm(data=form_data)
        self.assertTrue(form.is_valid())
        producto = form.save()
        self.assertEqual(producto.tallas, 'S,M')
        self.assertEqual(producto.nombre, 'Nuevo Producto')
        self.assertEqual(producto.precio, Decimal('50.00'))
        self.assertEqual(producto.stock, 5)
        self.assertEqual(producto.descuento, 5)