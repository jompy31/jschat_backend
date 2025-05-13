from django.db import models
from django.db import IntegrityError
from django.contrib.auth.models import User
import os
import re

class Characteristic(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name

class Product(models.Model):
    file = models.FileField(upload_to='products/')
    file1 = models.FileField(upload_to='products/')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    name_url = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    characteristics = models.ManyToManyField(Characteristic, blank=True)
    # subproducts = models.ManyToManyField(SubProduct, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Mantener name_url en blanco
        if not self.name_url:
            self.name_url = ''

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.file1:
            if os.path.isfile(self.file1.path):
                os.remove(self.file1.path)
        super().delete(*args, **kwargs)

class TeamMember(models.Model):
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255, blank=True, null=True)
    photo = models.ImageField(upload_to='team_members/', blank=True, null=True)

    def __str__(self):
        return self.name

class BusinessHour(models.Model):
    DAY_CHOICES = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miércoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sábado', 'Sábado'),
        ('domingo', 'Domingo'),
    ]
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.get_day_display()}: {self.start_time} - {self.end_time}"

class Coupon(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)  # Changed to nullable
    code = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='coupons/', blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True, default=None)
    discount = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True, default=None)

    def __str__(self):
        return f"Coupon: {self.description[:30]}..."

class SubProduct(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    addressmap = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='subproducts/', blank=True)
    url = models.URLField(blank=True)
    products = models.ManyToManyField('Product', related_name='subproducts', blank=True)
    subcategory = models.TextField(max_length=400, null=True, blank=True)
    subsubcategory = models.TextField(max_length=400, null=True, blank=True)
    product_names = models.TextField(blank=True)  # New variable to store product names
    description = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    province = models.CharField(max_length=50, blank=True, null=True)
    canton = models.CharField(max_length=50, blank=True, null=True)
    distrito = models.CharField(max_length=50, blank=True, null=True)
    constitucion = models.DateField(blank=True, null=True)
    contact_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    comercial_activity = models.CharField(max_length=100, blank=True, null=True, default='')
    pay_method = models.CharField(max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='distributor_logos/', null=True, blank=True)
    file = models.FileField(upload_to='distributor_logos/', null=True, blank=True)

    # New fields
    business_hours = models.ManyToManyField(BusinessHour, related_name='subproducts', blank=True)
    team_members = models.ManyToManyField(TeamMember, related_name='subproducts', blank=True)
    certified = models.BooleanField(default=False)
    coupons = models.ManyToManyField(Coupon, related_name='subproducts', blank=True)

    def __str__(self):
        return self.name

    def add_product_name(self, product_name):
        if not self.product_names:
            self.product_names = product_name
        else:
            product_names_list = self.product_names.split(',')
            if product_name not in product_names_list:
                product_names_list.append(product_name)
                self.product_names = ','.join(product_names_list)

    def remove_product_name(self, product_name):
        if self.product_names:
            product_names_list = self.product_names.split(',')
            if product_name in product_names_list:
                product_names_list.remove(product_name)
                self.product_names = ','.join(product_names_list)

    def __str__(self):
        # Modificar para incluir los detalles de los team members y business hours
        team_members_str = ', '.join([f"{member.name} ({member.position})" for member in self.team_members.all()])
        business_hours_str = ', '.join([f"{business_hour.get_day_display()}: {business_hour.start_time} - {business_hour.end_time}" for business_hour in self.business_hours.all()])
        
        return f"{self.name} - Team: [{team_members_str}] - Hours: [{business_hours_str}]"

    def get_team_members_details(self):
        return ", ".join([f"{member.name} ({member.position})" for member in self.team_members.all()])
    
    def get_business_hours_details(self):
        return ", ".join([f"{business_hour.get_day_display()}: {business_hour.start_time} - {business_hour.end_time}" for business_hour in self.business_hours.all()])
                
class Service(models.Model):
    code = models.CharField(max_length=7, unique=True, default='AB00000')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True, default=None)
    duration = models.CharField(max_length=100, null=True, blank=True)
    subproduct = models.ForeignKey('SubProduct', on_delete=models.CASCADE, null=True, blank=True, default=None)

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'products_service_service'

    def save(self, *args, **kwargs):
        if not self.code:
            self.generate_unique_code()

        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            # Handle the unique constraint violation by generating a new code
            self.generate_unique_code()
            super().save(*args, **kwargs)

    def generate_unique_code(self):
        existing_codes = Service.objects.values_list('code', flat=True)
        code_number = 1

        while True:
            new_code = f'AB{code_number:05d}'
            if new_code not in existing_codes:
                self.code = new_code
                break
            code_number += 1



class Combo(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=7, null=True, default='AB00000')
    name = models.CharField(max_length=255)
    description = models.TextField()
    services = models.ManyToManyField('Service', blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    subproduct = models.ForeignKey('SubProduct', on_delete=models.CASCADE, null=True, blank=True, default=None)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.generate_unique_code()

        super().save(*args, **kwargs)

    def generate_unique_code(self):
        existing_codes = Combo.objects.values_list('code', flat=True)
        code_number = 1

        while True:
            new_code = f'C{code_number:05d}'
            if new_code not in existing_codes:
                self.code = new_code
                break
            code_number += 1
