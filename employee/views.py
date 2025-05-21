from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError
from .models import (
    Company, JobCategory, JobPosting, JobApplication, 
    JobAlert, ExperienceLevel, Skill, Benefit, JobTag
)
from .serializers import (
    CompanySerializer, JobCategorySerializer, 
    JobPostingSerializer, JobApplicationSerializer, 
    JobAlertSerializer, ExperienceLevelSerializer, SkillSerializer, 
    BenefitSerializer, JobTagSerializer
)
from django.contrib.auth.models import User
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from rest_framework.permissions import AllowAny

# Vistas relacionadas con Company
class CompanyListView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [AllowAny]

class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

# Vistas relacionadas con JobCategory
class JobCategoryListView(generics.ListCreateAPIView):
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [AllowAny]

class JobCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [IsAuthenticated]


# Vistas relacionadas con JobPosting
class JobPostingListView(generics.ListCreateAPIView):
    queryset = JobPosting.objects.all().order_by('-posted_date')
    serializer_class = JobPostingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        return self.filter_jobs_for_user(user, queryset)

    def post(self, request, *args, **kwargs):
        # Imprimir datos recibidos
        print("Datos recibidos:", request.data)
        
        # Crear el serializer con los datos recibidos
        serializer = JobPostingSerializer(data=request.data)
        
        # Validar los datos
        if serializer.is_valid():
            # Guardar la instancia
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Imprimir errores de validación
        print("Errores de validación:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def filter_jobs_for_user(self, user, queryset):
        user_profile = self.get_user_profile_data(user)
        job_titles = [job.title for job in queryset]

        if not job_titles:
            return queryset  # Retorna todos los trabajos si no hay títulos

        user_preferences = [user_profile['job_interests']]
        vectorizer = TfidfVectorizer(stop_words='english')
        
        try:
            job_vectors = vectorizer.fit_transform(job_titles)
            user_vector = vectorizer.transform(user_preferences)
        except ValueError as e:
            # Manejar el error si el vocabulario está vacío
            print(f"Error de vectorización: {e}")
            return queryset

        cosine_similarities = cosine_similarity(user_vector, job_vectors).flatten()
        recommended_jobs_indices = cosine_similarities.argsort()[::-1]
        recommended_jobs = [queryset[int(i)] for i in recommended_jobs_indices]

        return recommended_jobs

    def get_user_profile_data(self, user):
        return {
            'job_interests': 'Software Development, Data Science',
            'preferred_location': 'Remote',
            'experience_level': 'Mid-level'
        }


class JobPostingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer

# Vistas relacionadas con JobApplication
class JobApplicationCreateView(generics.CreateAPIView):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer

    def post(self, request, *args, **kwargs):
        print("Datos recibidos:", request.data)  # Imprime los datos del cliente
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            print(f"Error durante la creación: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JobApplicationListView(generics.ListAPIView):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(applicant=self.request.user)
    
class JobApplicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]    

class JobAlertCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        print("Datos recibidos:", request.data)  # Imprimir los datos recibidos
        
        # Crear un serializer con los datos recibidos
        serializer = JobAlertSerializer(data=request.data)

        # Validar y guardar los datos
        if serializer.is_valid():
            serializer.save(user=request.user)  # Guardar con el usuario actual
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        print("Errores de validación:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class JobAlertDetailView(APIView):

    def delete(self, request, pk, *args, **kwargs):
        try:
            jobAlert = JobAlert.objects.get(pk=pk)
            jobAlert.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)  # No content para indicar que la eliminación fue exitosa
        except JobAlert.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    


class JobAlertListView(generics.ListAPIView):
    queryset = JobAlert.objects.all()
    serializer_class = JobAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

# Vistas con Machine Learning para Job Alerts
class JobAlertAIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        profile_data = self.get_user_profile_data(user)

        recommended_jobs = self.get_recommended_jobs(profile_data)

        serializer = JobPostingSerializer(recommended_jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_recommended_jobs(self, profile_data):
        queryset = JobPosting.objects.filter(is_active=True)

        job_titles = [job.title for job in queryset]
        user_preferences = [profile_data['job_interests']]

        vectorizer = TfidfVectorizer(stop_words='english')
        job_vectors = vectorizer.fit_transform(job_titles)
        user_vector = vectorizer.transform(user_preferences)

        cosine_similarities = cosine_similarity(user_vector, job_vectors).flatten()
        recommended_jobs_indices = cosine_similarities.argsort()[::-1]
        recommended_jobs = [queryset[i] for i in recommended_jobs_indices[:5]]

        return recommended_jobs

    def get_user_profile_data(self, user):
        return {
            'job_interests': 'Software Development, Data Science',
            'preferred_location': 'Remote',
            'experience_level': 'Mid-level'
        }

class UserJobAlertsListView(ListAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return JobAlert.objects.filter(user=user)

# Vistas relacionadas con ExperienceLevel
class ExperienceLevelListView(generics.ListCreateAPIView):
    queryset = ExperienceLevel.objects.all()
    serializer_class = ExperienceLevelSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        print("Datos recibidos del frontend:", request.data)  # Log received data
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Errores de validación:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExperienceLevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExperienceLevel.objects.all()
    serializer_class = ExperienceLevelSerializer
    

# Vistas relacionadas con Skill
class SkillListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        skills = Skill.objects.all()
        serializer = SkillSerializer(skills, many=True)
        return Response(serializer.data)
    def post(self, request, *args, **kwargs):
        # Imprimir datos recibidos
        print("Datos recibidos:", request.data)

        # Usar el serializer para validar y guardar los datos
        serializer = SkillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    

class SkillDetailView(APIView):
    def get(self, request, pk):
        try:
            skill = Skill.objects.get(pk=pk)
            serializer = SkillSerializer(skill)
            return Response(serializer.data)
        except Skill.DoesNotExist:
            return Response({'error': 'Skill not found'}, status=404)
        
    def delete(self, request, pk, *args, **kwargs):
        try:
            skill = Skill.objects.get(pk=pk)
            skill.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)  # No content para indicar que la eliminación fue exitosa
        except Skill.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    

# Vistas relacionadas con Benefit
class BenefitListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        benefits = Benefit.objects.all()
        serializer = BenefitSerializer(benefits, many=True)
        return Response(serializer.data)
    def post(self, request, *args, **kwargs):
        # Imprimir datos recibidos
        print("Datos recibidos:", request.data)

        # Usar el serializer para validar y guardar los datos
        serializer = BenefitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BenefitDetailView(APIView):
    def get(self, request, pk):
        try:
            benefit = Benefit.objects.get(pk=pk)
            serializer = BenefitSerializer(benefit)
            return Response(serializer.data)
        except Benefit.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    def delete(self, request, pk, *args, **kwargs):
        try:
            benefit = Benefit.objects.get(pk=pk)
            benefit.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)  # No content para indicar que la eliminación fue exitosa
        except Benefit.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

# Vistas relacionadas con JobTag
class JobTagListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        job_tags = JobTag.objects.all()
        serializer = JobTagSerializer(job_tags, many=True)
        return Response(serializer.data)
    def post(self, request, *args, **kwargs):
        # Imprimir datos recibidos
        print("Datos recibidos:", request.data)

        # Usar el serializer para validar y guardar los datos
        serializer = JobTagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class JobTagDetailView(APIView):
    def get(self, request, pk):
        try:
            job_tag = JobTag.objects.get(pk=pk)
            serializer = JobTagSerializer(job_tag)
            return Response(serializer.data)
        except JobTag.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    def delete(self, request, pk, *args, **kwargs):
        try:
            job_tag = JobTag.objects.get(pk=pk)
            job_tag.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)  # No content para indicar que la eliminación fue exitosa
        except JobTag.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
