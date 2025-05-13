from django.urls import path, include
from . import views
from .views import (
    WorkExperienceListCreateView,
    WorkExperienceRetrieveUpdateDestroyView,
    SkillListCreateView,
    SkillRetrieveUpdateDestroyView,
)


urlpatterns = [
    path('todos/', views.TodoListCreate.as_view()),
    path('todos/<int:pk>', views.TodoRetrieveUpdateDestroy.as_view()),
    path('todos/<int:pk>/complete', views.TodoToggleComplete.as_view()),
    path('signup/', views.signup),
    path('login/', views.login),
    path('reset_password/', views.ResetPasswordAPIView.as_view(), name='reset_password'),
    path('reset_password_user/<str:reset_token>/', views.ResetPasswordUser.as_view(), name='reset_password_user'),
    path('users/', views.UserList.as_view()), 
    path('users/<int:pk>/', views.UserDetail.as_view()),
    path('users/<int:pk>/update/', views.UserUpdate.as_view()),
    path('users/<int:pk>/delete/', views.UserDelete.as_view()),
    path('leads/', views.LeadCreate.as_view()),
    path('leads/<int:pk>/', views.LeadRetrieveUpdateDestroy.as_view()),
    path('leads/<int:pk>/comments/', views.CommentListCreate.as_view()),
    path('leads/comments/<int:pk>/', views.CommentRetrieveUpdateDestroy.as_view()),
    path('leads/comments/<int:pk>/<int:comment_pk>/', views.CommentRetrieveUpdateDestroy.as_view()),
    path('blog/', include('blog.urls')),

     # WorkExperience URLs
    path('work-experience/', WorkExperienceListCreateView.as_view(), name='work-experience-list-create'),
    path('work-experience/<int:pk>/', WorkExperienceRetrieveUpdateDestroyView.as_view(), name='work-experience-detail'),

    # Skill URLs
    path('skills/', SkillListCreateView.as_view(), name='skill-list-create'),
    path('skills/<int:pk>/', SkillRetrieveUpdateDestroyView.as_view(), name='skill-detail'),
]
