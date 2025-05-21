from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Lead, Comment, WorkExperience, Skill
from django.core.mail import EmailMessage
from django.contrib import messages

# Define la clase UserProfileInline
class UserProfileInline(admin.StackedInline):
    model = UserProfile

# Define la clase CustomUserAdmin que hereda de UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0

class LeadAdmin(admin.ModelAdmin):
    inlines = [CommentInline]
    list_display = ['id', 'name', 'email', 'priority', 'status']
    
    # Custom admin action to send emails
    actions = ['send_test_email']

    def send_test_email(self, request, queryset):
        recipient_list = [lead.email for lead in queryset if lead.email]
        if not recipient_list:
            self.message_user(request, "No valid email addresses found for the selected leads.", level=messages.ERROR)
            return

        subject = "Test Email from ABCupon Admin"
        message = "This is a test email sent from the ABCupon admin panel."
        from_email = "soporte@abcupon.com"

        try:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list,
            )
            email.send()
            self.message_user(request, f"Test email sent successfully to {len(recipient_list)} recipient(s).", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error sending email: {str(e)}", level=messages.ERROR)
            # Log the error to the console and debug.log
            print(f"Email sending failed: {str(e)}")
            import logging
            logger = logging.getLogger('django')
            logger.error(f"Email sending failed: {str(e)}", exc_info=True)

# Desregistra el administrador predeterminado de User y registra CustomUserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Lead, LeadAdmin)
admin.site.register(WorkExperience)
admin.site.register(Skill)