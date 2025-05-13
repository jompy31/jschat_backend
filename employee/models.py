from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Modelo para las empresas o contratistas
class Company(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField()
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    established_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies', null=True, blank=True)

    def __str__(self):
        return self.name

# Modelo para las categorías de trabajos (Ej: IT, Marketing, Finanzas)
class JobCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# Modelo para los niveles de experiencia
class ExperienceLevel(models.Model):
    level = models.CharField(max_length=50, choices=[
        ('Entry-level', 'Entry-level'),
        ('Mid-level', 'Mid-level'),
        ('Senior-level', 'Senior-level'),
        ('Director', 'Director'),
        ('Executive', 'Executive')
    ])

    def __str__(self):
        return self.level

# Modelo para las habilidades requeridas (Ej: Python, Marketing Digital)
class Skill(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# Modelo para los beneficios del trabajo (Ej: Seguro médico, home office)
class Benefit(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

# Modelo para las etiquetas de empleo (Ej: Urgente, Contratación Inmediata)
class JobTag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

# Modelo principal para los puestos de trabajo
class JobPosting(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True)
    city = models.CharField(max_length=100)  # Nueva ubicación
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, null=True)  # Estado o región opcional
    modality = models.CharField(max_length=50, choices=[  # Campo de modalidad
        ('Presencial', 'Presencial'),
        ('Remoto', 'Remoto'),
        ('Híbrido', 'Híbrido')
    ])
    employment_type = models.CharField(max_length=50, choices=[
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Contract', 'Contract'),
        ('Temporary', 'Temporary'),
        ('Freelance', 'Freelance')
    ])
    experience_level = models.ForeignKey(ExperienceLevel, on_delete=models.SET_NULL, null=True)
    salary_range = models.CharField(max_length=100, blank=True, null=True)
    skills_required = models.ManyToManyField(Skill, blank=True)
    benefits = models.ManyToManyField(Benefit, blank=True)
    tags = models.ManyToManyField(JobTag, blank=True)
    posted_date = models.DateField(auto_now_add=True)
    application_deadline = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    how_to_apply = models.TextField()
    views_count = models.IntegerField(default=0)
    applicants_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} at {self.company.name}"

    def increment_views(self):
        self.views_count += 1
        self.save()

    def increment_applicants(self):
        self.applicants_count += 1
        self.save()

# Modelo para aplicaciones de trabajo
class JobApplication(models.Model):
    id = models.AutoField(primary_key=True)
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    resume = models.FileField(upload_to='resumes/')
    cover_letter = models.TextField(blank=True, null=True)
    application_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed'),
        ('Interview', 'Interview'),
        ('Offer', 'Offer'),
        ('Hired', 'Hired'),
        ('Rejected', 'Rejected')
    ], default='Pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.applicant.username} - {self.job.title}"

# Modelo para alertas de trabajo
class JobAlert(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_alerts')
    keywords = models.CharField(max_length=255)
    categories = models.ManyToManyField(JobCategory, blank=True)
    experience_level = models.ForeignKey(ExperienceLevel, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    skills_required = models.ManyToManyField(Skill, blank=True)
    
    def __str__(self):
        return f"Alert for {self.user.username} - {self.keywords}"
