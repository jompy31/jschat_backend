from django.urls import path
from .views import (
    CompanyListView, CompanyDetailView, JobCategoryListView, JobCategoryDetailView, 
    JobPostingListView, JobPostingDetailView, 
    JobApplicationCreateView, JobApplicationListView, JobApplicationDetailView,
    JobAlertCreateView, JobAlertListView,  JobAlertDetailView, JobAlertAIView, UserJobAlertsListView,
    ExperienceLevelListView, ExperienceLevelDetailView, 
    SkillListView, SkillDetailView,
    BenefitListView, BenefitDetailView,
    JobTagListView, JobTagDetailView
)

urlpatterns = [
    # Rutas para empresas (Company)
    path('companies/', CompanyListView.as_view(), name='company-list'),
    path('companies/<int:pk>/', CompanyDetailView.as_view(), name='company-detail'),

    # Rutas para categorías de trabajo (JobCategory)
    path('job-categories/', JobCategoryListView.as_view(), name='job-category-list'),
    path('job-categories/<int:pk>/', JobCategoryDetailView.as_view(), name='job-category-detail'),

    # Rutas para las publicaciones de empleo (JobPosting)
    path('jobs/', JobPostingListView.as_view(), name='job-posting-list'),
    path('jobs/<int:pk>/', JobPostingDetailView.as_view(), name='job-posting-detail'),

    # Rutas para aplicar a trabajos (JobApplication)
    path('jobs/<int:job_id>/apply/', JobApplicationCreateView.as_view(), name='job-application-create'),
    path('applications/', JobApplicationListView.as_view(), name='job-application-list'),
    path('jobs/<int:job_id>/apply/<int:pk>/', JobApplicationDetailView.as_view(), name='job-application-detail'),

    # Rutas para alertas de empleo (JobAlert)
    path('job-alerts/', JobAlertListView.as_view(), name='job-alert-list'),
    path('job-alerts/create/', JobAlertCreateView.as_view(), name='job-alert-create'),
    path('job-alerts/<int:pk>/', JobAlertDetailView.as_view(), name='job-alert-list'),

    # Ruta personalizada para generar Job Alerts utilizando inteligencia artificial
    path('job-alerts/ai/', JobAlertAIView.as_view(), name='job-alert-ai'),

    # Ruta para que el usuario vea sus alertas personalizadas
    path('user/<int:user_id>/job-alerts/', UserJobAlertsListView.as_view(), name='user-job-alerts'),

    # Rutas para niveles de experiencia (ExperienceLevel)
    path('experience-levels/', ExperienceLevelListView.as_view(), name='experience-level-list'),
    path('experience-levels/<int:pk>/', ExperienceLevelDetailView.as_view(), name='experience-level-detail'),

    # Rutas para habilidades (Skill)
    path('skills/', SkillListView.as_view(), name='skill-list'),
    path('skills/<int:pk>/', SkillDetailView.as_view(), name='skill-detail'),

    # Rutas para beneficios (Benefit)
    path('benefits/', BenefitListView.as_view(), name='benefit-list'),
    path('benefits/<int:pk>/', BenefitDetailView.as_view(), name='benefit-detail'),

    # Rutas para etiquetas de trabajo (JobTag)
    path('job-tags/', JobTagListView.as_view(), name='job-tag-list'),
    path('job-tags/<int:pk>/', JobTagDetailView.as_view(), name='job-tag-detail'),
]
