from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.fields import BLANK_CHOICE_DASH
from django.core.exceptions import ValidationError
from django.db import IntegrityError

class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='shipping_products')
    name = models.CharField(max_length=200,null=True,blank=True)
    image = models.ImageField(null=True,blank = True,default = "/images/",upload_to="images/")
    subproduct = models.CharField(max_length=200,null=True,blank=True)
    category = models.CharField(max_length=200,null=True,blank=True)
    subcategory = models.TextField(max_length=4000, null=True, blank=True)
    subsubcategory = models.TextField(max_length=4000, null=True, blank=True)
    description = models.TextField(null=True,blank=True)
    rating = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    numReviews = models.IntegerField(null=True, blank=True, default=0, editable=True)
    price = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    countInStock = models.IntegerField(null=True,blank=True,default=0)
    createdAt = models.DateTimeField(auto_now_add=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    province = models.CharField(max_length=50, blank=True, null=True)
    canton = models.CharField(max_length=50, blank=True, null=True)
    _id = models.AutoField(primary_key=True)

    def __str__(self):
        return f"{self.name} | {self.subproduct} | {str(self.price)}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    image = models.ImageField(null=True, blank=True, default="/images/", upload_to="images/")
    comment = models.TextField(null=True, blank=True)
    _id = models.AutoField(primary_key=True, editable=False)

    def __str__(self):
        return str(self.name)

class Review(models.Model):
    product = models.ForeignKey(Product,on_delete=models.SET_NULL,null=True)
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    name = models.CharField(max_length=200,null=True,blank=True)
    image = models.ImageField(null=True,blank = True,default = "/images/",upload_to="images/")
    rating =  models.IntegerField(null=True,blank=True,default=0)
    comment = models.TextField(null=True,blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    _id =  models.AutoField(primary_key=True,editable=False)

    def __str__(self):
        return str(self.rating)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    paymentMethod = models.CharField(max_length=200,null=True,blank=True)
    taxPrice = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    shippingPrice = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    totalPrice = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    isPaid = models.BooleanField(default=False)
    paidAt = models.DateTimeField(auto_now_add=False,null=True, blank=True)
    isDeliver = models.BooleanField(default=False)
    deliveredAt = models.DateTimeField(auto_now_add=False,null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    _id =  models.AutoField(primary_key=True,editable=False)
    product = models.ManyToManyField(Product)
    shipping_address = models.OneToOneField('ShippingAddress', on_delete=models.SET_NULL, null=True, related_name='order_shipping_address')

    def __str__(self):
        return str(self.createdAt)


class OrderItem(models.Model):
    product = models.ForeignKey(Product,on_delete=models.SET_NULL,null=True)
    order  = models.ForeignKey(Order,on_delete=models.SET_NULL,null=True)
    name = models.CharField(max_length=200,null=True,blank=True)
    qty = models.IntegerField(null=True,blank=True,default=0)
    price = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    _id =  models.AutoField(primary_key=True,editable=False)

    def __str__(self):
        return str(self.name)



class ShippingAddress(models.Model):
    order = models.OneToOneField(Order,on_delete=models.CASCADE,null=True,blank=True)
    address = models.CharField(max_length=200,null=True,blank=True)
    city  = models.CharField(max_length=200,null=True,blank=True)
    postalCode = models.CharField(max_length=200,null=True,blank=True)
    country = models.CharField(max_length=200,null=True,blank=True)
    shippingPrice = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True)
    _id = models.AutoField(primary_key=True, default=1,editable=False)

    def __str__(self):
        return str(self.address)

class Form(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='user_forms')
    name = models.CharField(max_length=200)
    product = models.ManyToManyField(Product, related_name='forms',null=True,blank=True) # Un producto puede tener un formulario asociado
    created_at = models.DateTimeField(auto_now_add=True)
    _id = models.AutoField(primary_key=True)

    def __str__(self):
        return self.name

class FormField(models.Model):
    FORM_FIELD_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('select', 'Select'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio'),
        # Añadir más tipos de campo si es necesario
    ]

    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=200)  # Etiqueta de la pregunta/campo
    field_type = models.CharField(max_length=50, choices=FORM_FIELD_TYPES)
    required = models.BooleanField(default=True)
    _id = models.AutoField(primary_key=True)
    def __str__(self):
        return self.label
    
class FormResponse(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='responses')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='product_responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Usuario que completó el formulario
    submitted_at = models.DateTimeField(auto_now_add=True)
    form_field = models.ForeignKey(FormField, on_delete=models.CASCADE, default='producto_generico', null=True, blank=True)
    value = models.TextField(null=True, blank=True)  # Almacenar la respuesta dada por el usuario
    _id = models.AutoField(primary_key=True)

    class Meta:
        unique_together = ('form', 'product', 'user', 'form_field')  # Define la restricción de unicidad

    def __str__(self):
        return f'Respuesta al Formulario: {self.form.name} del Producto: {self.product.name}'

    def save(self, *args, **kwargs):
        try:
            # Verificar si ya existe una respuesta con los mismos datos
            if not FormResponse.objects.filter(form=self.form, product=self.product, user=self.user, form_field=self.form_field).exists():
                super().save(*args, **kwargs)  # Solo guardar si no existe un registro duplicado
            else:
                print("Ya existe una respuesta con los mismos datos. Se omitió el guardado.")
        except IntegrityError:
            print("Error de integridad, se omitió el guardado.")

# Señal para asignar automáticamente el producto a un formulario si la subsubcategoría coincide con el nombre del formulario
@receiver(post_save, sender=Product)
def assign_product_to_form(sender, instance, created, **kwargs):
    if created and instance.subsubcategory:
        # Buscar si hay algún formulario con el nombre igual a la subsubcategoría del producto
        forms = Form.objects.filter(name=instance.subsubcategory)
        if forms.exists():
            for form in forms:
                form.product.add(instance)  # Añadir el producto al formulario correspondiente
                form.save()

    # Si se crea un formulario cuyo nombre coincide con una subsubcategoría existente de un producto
@receiver(post_save, sender=Form)
def assign_form_to_existing_products(sender, instance, created, **kwargs):
    if created:
        # Buscar productos con subsubcategoría igual al nombre del formulario recién creado
        products = Product.objects.filter(subsubcategory=instance.name)
        if products.exists():
            for product in products:
                instance.product.add(product)  # Añadir los productos coincidentes al formulario recién creado
                instance.save()