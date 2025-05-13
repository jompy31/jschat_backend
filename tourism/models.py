from django.db import models
from django.contrib.auth.models import User

class Amenity(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Property(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ('Casa', 'Casa'),
        ('Apartamento', 'Apartamento'),
        ('Granero', 'Granero'),
        ('Bed & breakfast', 'Bed & breakfast'),
        ('Barco', 'Barco'),
        ('Cabañas', 'Cabañas'),
        ('Casa rodante', 'Casa rodante'),
        ('Castillo', 'Castillo'),
        ('Cueva', 'Cueva'),
        ('Contenedores', 'Contenedores'),
        ('Casa cíclada', 'Casa cíclada'),
        ('Dammuso', 'Dammuso'),
        ('Domo', 'Domo'),
        ('Casa ecológica', 'Casa ecológica'),
        ('Granja', 'Granja'),
        ('Casa de huéspedes', 'Casa de huéspedes'),
        ('Hotel', 'Hotel'),
        ('Casa flotante', 'Casa flotante'),
        ('Kezhan', 'Kezhan'),
        ('Minsu', 'Minsu'),
        ('Riad', 'Riad'),
        ('Ryokan', 'Ryokan'),
        ('Casa de pastor', 'Casa de pastor'),
        ('Tienda de campo', 'Tienda de campo'),
        ('Minicasa', 'Minicasa'),
        ('Torre', 'Torre'),
        ('Casa del árbol', 'Casa del árbol'),
        ('Trullo', 'Trullo'),
        ('Molino de viento', 'Molino de viento'),
        ('Yurta', 'Yurta'),
    ]
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=500)
    country = models.CharField(max_length=100,null=True, blank=True) 
    province = models.CharField(max_length=100,null=True, blank=True)   
    canton = models.CharField(max_length=100,null=True, blank=True)  
    rating = models.IntegerField(null=True, blank=True)
    property_type = models.CharField(max_length=100, choices=PROPERTY_TYPE_CHOICES)
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    amenities = models.ManyToManyField(Amenity, blank=True)  # Relación de muchos a muchos
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    availability = models.BooleanField(default=True)
    pictures = models.ImageField(null=True, blank=True, upload_to="images/")
    
    def __str__(self):
        return self.title

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(null=True, blank=True, default="/propertyimages/", upload_to="propertyimages/")

    def __str__(self):
        return f"Image for {self.property.title}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
        ('No Show', 'No Show'),
        ('Refunded', 'Refunded'),
    ]

    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Booking for {self.property.title} by {self.guest.username}"

class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50)

    def __str__(self):
        return f"Payment of {self.amount} by {self.user.username}"

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_reviews')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.property.title} by {self.user.username}"
