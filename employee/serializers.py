from rest_framework import serializers
from .models import (
    Company, JobCategory, ExperienceLevel, Skill, Benefit, JobTag, 
    JobPosting, JobApplication, JobAlert
)
from django.contrib.auth.models import User
from api.serializers import UserSerializer
import random

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__' 
    def create(self, validated_data):
        # Asignar el usuario autenticado al campo 'user' del modelo Company
        user = self.context['request'].user  # Obtiene el usuario autenticado de la solicitud
        validated_data['user'] = user  # Agrega el usuario a los datos validados
        return super().create(validated_data)

class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ['id', 'name', 'description']

class ExperienceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperienceLevel
        fields = ['id', 'level']

    def validate_level(self, value):
        # Check if an ExperienceLevel with this level already exists
        if ExperienceLevel.objects.filter(level=value).exists():
            raise serializers.ValidationError(f"An ExperienceLevel with level '{value}' already exists.")
        return value

    def create(self, validated_data):
        # Use get_or_create to ensure no duplicates are created
        experience_level, created = ExperienceLevel.objects.get_or_create(
            level=validated_data['level']
        )
        return experience_level

# Serializador para el modelo de Skill
class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'description']

class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benefit
        fields = ['id', 'name', 'description']

class JobTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobTag
        fields = ['id', 'name']

class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = '__all__' 

class JobApplicationSerializer(serializers.ModelSerializer):
    applicant = UserSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'cover_letter', 'notes', 'status', 'applicant', 'resume']

    def validate_applicant(self, value):
        print(f"Validando applicant: {value}")
        try:
            user = User.objects.get(email=value)
            print(f"Usuario encontrado: {user.email}")
            return user.email
        except User.DoesNotExist:
            print("Usuario no encontrado.")
            raise serializers.ValidationError("Este correo electrónico no está registrado.")

    def validate_resume(self, value):
        if not value:
            raise serializers.ValidationError("El archivo de currículum es obligatorio.")
        if not hasattr(value, 'name') or not hasattr(value, 'size'):
            raise serializers.ValidationError("El archivo proporcionado no es válido.")
        return value

    def create(self, validated_data):
        print(f"Datos validados recibidos para crear: {validated_data}")
        applicant_email = validated_data.pop('applicant')
        applicant = User.objects.get(email=applicant_email)
        job_application = JobApplication.objects.create(applicant=applicant, **validated_data)
        print(f"JobApplication creada: {job_application}")
        return job_application




class JobAlertSerializer(serializers.ModelSerializer):
    user = serializers.EmailField()

    class Meta:
        model = JobAlert
        fields = ['id','user', 'keywords', 'categories', 'experience_level', 'skills_required']

    def validate_user(self, value):
        # Verifica si el correo electrónico existe en la base de datos
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Este correo electrónico no está registrado.")
        
        return user  # Devuelve la instancia de usuario encontrada

    def create(self, validated_data):
        # Extrae categorías y habilidades de los datos validados
        categories_data = validated_data.pop('categories', [])
        skills_required_data = validated_data.pop('skills_required', [])

        # Crea el objeto JobAlert sin relaciones de muchos a muchos
        job_alert = JobAlert.objects.create(user=validated_data.pop('user'), **validated_data)

        # Asigna las categorías y habilidades requeridas
        job_alert.categories.set(categories_data)  # Asigna las categorías
        job_alert.skills_required.set(skills_required_data)  # Asigna las habilidades requeridas

        return job_alert