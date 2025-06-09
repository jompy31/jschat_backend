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
    applicant_email = serializers.EmailField(write_only=True, required=False)
    job = serializers.PrimaryKeyRelatedField(queryset=JobPosting.objects.all(), required=False)  # Hacer job opcional

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'cover_letter', 'notes', 'status', 'applicant', 'applicant_email', 'resume']

    def validate_resume(self, value):
        if not value:
            raise serializers.ValidationError("El archivo de currículum es obligatorio.")
        if not hasattr(value, 'name') or not hasattr(value, 'size'):
            raise serializers.ValidationError("El archivo proporcionado no es válido.")
        return value

    def validate(self, data):
        # Solo validar job si se proporciona en los datos
        job = data.get('job')
        if job and not JobPosting.objects.filter(id=job.id).exists():
            raise serializers.ValidationError("El trabajo especificado no existe.")
        return data

    def create(self, validated_data):
        print(f"Datos validados recibidos para crear: {validated_data}")
        applicant_email = validated_data.pop('applicant_email', None)
        request = self.context.get('request')
        
        if applicant_email:
            try:
                applicant = User.objects.get(email=applicant_email)
            except User.DoesNotExist:
                raise serializers.ValidationError("Este correo electrónico no está registrado.")
        else:
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError("Se requiere autenticación para crear una solicitud de empleo.")
            applicant = request.user

        job_application = JobApplication.objects.create(
            applicant=applicant,
            **validated_data
        )
        print(f"JobApplication creada: {job_application}")
        return job_application

    def update(self, instance, validated_data):
        print(f"Datos validados recibidos para actualizar: {validated_data}")
        request = self.context.get('request')
        applicant_email = validated_data.pop('applicant_email', None)

        # Validar que el usuario autenticado sea el propietario de la JobApplication
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Se requiere autenticación para actualizar una solicitud de empleo.")
        if instance.applicant != request.user:
            raise serializers.ValidationError(
                f"Acceso denegado: {request.user.email} no es el solicitante de {instance}"
            )

        # Opcional: Si se proporciona applicant_email, validar que coincida con el usuario autenticado
        if applicant_email:
            try:
                applicant = User.objects.get(email=applicant_email)
                if applicant != request.user:
                    raise serializers.ValidationError(
                        "El correo electrónico proporcionado no coincide con el usuario autenticado."
                    )
            except User.DoesNotExist:
                raise serializers.ValidationError("Este correo electrónico no está registrado.")

        # No permitir modificar applicant ni job (si no se desea)
        validated_data.pop('applicant', None)
        validated_data.pop('job', None)

        # Actualizar los campos permitidos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        print(f"JobApplication actualizada: {instance}")
        return instance



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