from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff_status = models.CharField(
        max_length=20,
        choices=(
            ('customer', 'Customer'),
            ('user', 'User'),
            ('administrator', 'Administrator'),
            ('sales', 'Sales'),
            ('design', 'Design'),
            ('supervisor', 'Supervisor'),
            ('human_resources', 'Human Resources'),
            ('reporter', 'Reporter'),
            ('owner', 'Owner'),
        ),
        default='customer'
    )
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=50, unique=True)  # Asegurarse de que los valores sean únicos
    company = models.CharField(max_length=255, blank=True, null=True)  # Cambiar TextField por CharField
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)  # Cambiar a CharField
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.CharField(max_length=500, blank=True, null=True)  # Cambiar a CharField
    date_of_birth = models.DateField(blank=True, null=True)
    openwork = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class WorkExperience(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)  # Puede ser nulo si la experiencia está activa
    responsibilities = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"
    
class Skill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)  # Usar null=True
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user', 'name')  # Evitar duplicados por nombre de habilidad para el mismo usuario

    def __str__(self):
        return self.name
    
class Lead(models.Model):
    # Campos requeridos del cliente
    name = models.CharField(max_length=200)  # Nombre de la empresa
    email = models.EmailField()  # Correo electrónico de la empresa
    description = models.TextField()  # Descripción de la empresa
    number = models.CharField(max_length=20, blank=True, null=True)  # Número de contacto
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads_created', default=None)  # Usuario que crea el lead
    
    # Campos adicionales (opcional)
    comments = models.ManyToManyField(User, through='Comment', related_name='lead_comments', blank=True)  # Comentarios sobre el lead
    commercial_activity = models.CharField(max_length=200, blank=True, null=True)  # Actividad comercial de la empresa
    priority = models.CharField(
        max_length=10,
        choices=(
            ('bajo', 'Bajo'),
            ('medio', 'Medio'),
            ('alto', 'Alto'),
        ),
        blank=True, null=True
    )  # Prioridad del lead
    status = models.CharField(
        max_length=10,
        choices=(
            ('nuevo', 'Nuevo'),
            ('contactado', 'Contactado'),
            ('ganado', 'Ganado'),
        ),
        default='nuevo', blank=True, null=True
    )  # Estado del lead
    company_address = models.CharField(max_length=200, blank=True, null=True)  # Dirección de la empresa

    # Información relacionada con la marca y marketing
    brand_category = models.CharField(max_length=200, blank=True, null=True)  # Categoría de la marca
    brand_description = models.TextField(blank=True, null=True)  # Descripción de la marca
    brand_differentiation = models.TextField(blank=True, null=True)  # Diferenciación de la marca
    brand_necessity = models.TextField(blank=True, null=True)  # Necesidad que satisface la marca
    brand_perception_keywords = models.CharField(max_length=200, blank=True, null=True)  # Palabras clave de la marca
    brand_personality = models.CharField(max_length=200, blank=True, null=True)  # Personalidad de la marca
    brand_slogan_or_motto = models.CharField(max_length=200, blank=True, null=True)  # Eslogan de la marca
    brand_style_preference = models.CharField(max_length=200, blank=True, null=True)  # Preferencia de estilo visual
    brand_values = models.TextField(blank=True, null=True)  # Valores de la marca
    brand_virtues = models.TextField(blank=True, null=True)  # Virtudes de la marca
    business_experience_duration = models.CharField(max_length=200, blank=True, null=True)  # Años de experiencia comercial
    business_type = models.CharField(max_length=200, blank=True, null=True)  # Tipo de negocio de la empresa
    colors = models.CharField(max_length=200, blank=True, null=True)  # Colores asociados a la marca
    commercial_information_details = models.TextField(blank=True, null=True)  # Detalles adicionales sobre la empresa
    company_logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)  # Logo de la empresa
    company_name = models.CharField(max_length=200, blank=True, null=True)  # Nombre completo de la empresa
    company_website_or_social_media = models.URLField(blank=True, null=True)  # Sitio web o redes sociales de la empresa

    # Información de contacto del responsable
    contact_person_name = models.CharField(max_length=200, blank=True, null=True)  # Nombre de la persona de contacto
    contact_person_phone = models.CharField(max_length=20, blank=True, null=True)  # Teléfono de la persona de contacto
    contact_person_position = models.CharField(max_length=200, blank=True, null=True)  # Puesto de la persona de contacto
    contact_reason = models.TextField(blank=True, null=True)  # Razón por la que se contacta al cliente
    current_business_goals = models.TextField(blank=True, null=True)  # Metas comerciales actuales
    main_competitors = models.TextField(blank=True, null=True)  # Competidores principales
    opening_hours_location_maps = models.CharField(max_length=200, blank=True, null=True)  # Horarios y ubicación en Google Maps
    payment_information = models.TextField(blank=True, null=True)  # Información adicional sobre métodos de pago
    payment_method = models.CharField(max_length=100, blank=True, null=True)  # Métodos de pago disponibles

    # Segmentación del público objetivo
    target_age_range = models.CharField(max_length=200, blank=True, null=True)  # Rango de edad objetivo
    target_gender = models.CharField(max_length=100, blank=True, null=True)  # Género objetivo
    target_interests = models.TextField(blank=True, null=True)  # Intereses del público objetivo
    target_lifecycle_stage = models.CharField(max_length=50, blank=True, null=True)  # Etapa del ciclo de vida del público
    target_socioeconomic_level = models.CharField(max_length=200, blank=True, null=True)  # Nivel socioeconómico objetivo

    def __str__(self):
        return self.name

class Comment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_comments')
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment {self.id} for Lead {self.lead.name}"
    
    
