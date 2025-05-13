from django.contrib import admin
from .models import Company, JobAlert, JobApplication, JobCategory,JobPosting, ExperienceLevel, Skill, Benefit, JobTag

class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'logo', 'website', 'contact_email', 'created_at')

class JobAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'keywords', 'created_at')

class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'applicant', 'application_date', 'status')
    list_filter = ('job', 'application_date', 'status')

class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')


class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'company', 'category', 
        'employment_type', 'experience_level', 
        'posted_date', 'is_active'
    )
    list_filter = ('company', 'category', 'employment_type', 'experience_level', 'is_active')
    search_fields = ('title', 'company__name')

class ExperienceLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'level')
    search_fields = ('level',)

class SkillAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

class BenefitAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

class JobTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

admin.site.register(Company, CompanyAdmin)
admin.site.register(JobAlert, JobAlertAdmin)
admin.site.register(JobApplication, JobApplicationAdmin)
admin.site.register(JobCategory, JobCategoryAdmin)
admin.site.register(JobPosting, JobPostingAdmin)
admin.site.register(ExperienceLevel, ExperienceLevelAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Benefit, BenefitAdmin)
admin.site.register(JobTag, JobTagAdmin)
