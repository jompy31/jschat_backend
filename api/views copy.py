from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import TodoSerializer, TodoToggleCompleteSerializer, UserSerializer, LeadSerializer, CommentSerializer, EmailSerializer, ResetPasswordSerializer
from .models import Lead, Comment
from todo.models import Todo
from django.db import IntegrityError
from django.contrib.auth.models import User
from .models import UserProfile
from rest_framework.parsers import JSONParser
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.generics import ListCreateAPIView
from django.http import Http404
from rest_framework import status
from rest_framework.generics import get_object_or_404
from django.core.mail import send_mail, EmailMessage
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.views import APIView
from django.contrib.auth.hashers import check_password
from rest_framework.exceptions import NotFound
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny 


class EmailAPIView(APIView):
    def get(self, request):
        serializer = EmailSerializer()
        return Response(serializer.data)

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        if serializer.is_valid():
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            from_email = serializer.validated_data['from_email']
            recipient_list = [email.strip() for email in serializer.validated_data['recipient_list'].split(',')]
            attachments = request.FILES.getlist('attachments')  # Obtener la lista de adjuntos

            # Enviar el correo a cada destinatario en recipient_list
            for recipient in recipient_list:
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=from_email,
                    to=[recipient],  # Pasar una lista con el destinatario actual solamente
                )

                for attachment in attachments:
                    email.attach(attachment.name, attachment.read(), attachment.content_type)

                email.send()

            return Response('Correos enviados correctamente', status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentListCreate(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lead_id = self.kwargs['pk']
        return Comment.objects.filter(lead_id=lead_id).order_by('-timestamp')

    def perform_create(self, serializer):
        lead_id = self.kwargs['pk']
        lead = Lead.objects.get(id=lead_id)
        serializer.save(lead=lead, user=self.request.user)

class CommentRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        lead_id = self.kwargs['pk']
        comment_id = self.kwargs['comment_pk']
        queryset = Comment.objects.filter(lead_id=lead_id)
        obj = get_object_or_404(queryset, pk=comment_id)
        self.check_object_permissions(self.request, obj)
        return obj

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class LeadCreate(generics.ListCreateAPIView):
    serializer_class = LeadSerializer
    queryset = Lead.objects.all()

class LeadRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LeadSerializer
    queryset = Lead.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        comment = request.data.get('comment')
        user = request.user

        if comment:
            comment_data = {
                'lead': instance,
                'user': user,
                'comment': comment,
            }
            comment_serializer = CommentSerializer(instance.last_comment, data=comment_data)
            comment_serializer.is_valid(raise_exception=True)
            comment_serializer.save()

        instance.save()

        return super().update(request, *args, **kwargs)

class UserList(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.all()

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

class UserDelete(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
class UserDetail(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Actualizar el campo staff_status si se proporciona en los datos de solicitud
        staff_status = request.data.get('staff_status')
        if staff_status is not None:
            user_profile = instance.userprofile
            allowed_choices = [choice[0] for choice in UserProfile._meta.get_field('staff_status').choices]
            if staff_status not in allowed_choices:
                return Response({'error': 'Invalid staff status.'}, status=400)
            user_profile.staff_status = staff_status
            user_profile.save()
        
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
class UserUpdate(generics.UpdateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()


class TodoList(generics.ListAPIView):
    serializer_class = TodoSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # return Todo.objects.filter(user=user).order_by('-created')
        return Todo.objects.order_by('-created')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TodoListCreate(generics.ListCreateAPIView):
    serializer_class = TodoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Todo.objects.order_by('-created')

    def perform_create(self, serializer):
        created = self.request.data.get('created', timezone.now())  # Obtener la hora recibida o usar la hora actual si no se proporciona
        serializer.save(user=self.request.user, created=created)



class TodoRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TodoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Todo.objects.filter(user=user)

    def perform_update(self, serializer):
        serializer.validated_data['created'] = self.request.data.get('created')
        serializer.save()


class TodoToggleComplete(generics.UpdateAPIView):
    serializer_class = TodoToggleCompleteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Todo.objects.filter(user=user)

    def perform_update(self, serializer):
        serializer.instance.completed = not serializer.instance.completed
        serializer.save()


@csrf_exempt
def signup(request):
    if request.method == 'POST':
        try:
            data = JSONParser().parse(request)
            first_name = data['first_name']
            last_name = data['last_name']
            email = data['email']
            password = data['password']
            staff_status = data.get('staff_status', 'customer')
            company = data.get('company')

            user = User.objects.create_user(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password
            )

            # Set staff status
            user_profile = UserProfile.objects.create(user=user, staff_status=staff_status, company=company)
            user_profile.save()

            token = Token.objects.create(user=user)

            return JsonResponse({'token': str(token)}, status=201)
        except IntegrityError:
            return JsonResponse(
                {'error': 'username taken. choose another username'},
                status=400)

@csrf_exempt
def login(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        user = authenticate(
            request,
            username=data['username'],
            password=data['password']
        )
        if user is None:
            return JsonResponse(
                {'error': 'unable to login. check username and password'},
                status=400)
        else:
            try:
                token = Token.objects.get(user=user)
            except:
                token = Token.objects.create(user=user)
            return JsonResponse({'token': str(token)}, status=201)
            
class ResetPasswordAPIView(APIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                user_profile = user.userprofile

                # Check if a token already exists for the user
                try:
                    reset_token = Token.objects.get(user=user)
                except Token.DoesNotExist:
                    # If a token does not exist, create a new one
                    reset_token = Token.objects.create(user=user)

                # Update the token's value (optional, only if you want to reset the token)
                # reset_token.key = Token.generate_key()
                # reset_token.save()

                current_site = get_current_site(request)
                reset_url = reverse('reset_password_user', kwargs={'reset_token': reset_token.key})
                reset_password_url = f"http://{current_site.domain}{reset_url}"
                frontend_reset_url = f"http://localhost:3000/reset_password_user/{reset_token.key}/"

                # Obtener los datos del usuario para el correo electrónico
                data = {
                    'Nombre': user.first_name,
                    'Apellido': user.last_name, 
                    'Correo Electrónico': user.email,
                    'Compañía': user_profile.company,
                    'Estado de Personal': user_profile.staff_status,
                    'Reset URL': reset_password_url,
                }

                # Crear la tabla con los datos del usuario
                table_data = "\n".join([f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in data.items()])
                table_html = f"<table><tbody>{table_data}</tbody></table>"

                # Envía el correo electrónico con los datos del usuario en una tabla
                subject = 'Reset Password'
                message = f"Hello!\n\nHere are the user data:\n{table_html}\n\nPlease click on the following link to reset your password:\n{frontend_reset_url}\n\nTDM will be happy to help you, please contact us by http://localhost:3000/contact"
                # message = f"Hello!\n\nHere are the user data:\n{table_html}\n\nPlease click on the following link to reset your password:\n{reset_password_url}\n\nTDM will be happy to help you, please contact us by http://localhost:3000/contact"
                from_email = 'consultas@iriquiqui.com'
                recipient_list = [email]

                send_mail(subject, '', from_email, recipient_list, html_message=message)

                return Response('Mail sent successfully', status=status.HTTP_200_OK)
            except User.DoesNotExist:
                raise NotFound("User with the provided email not found.")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ResetPasswordUser(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    allowed_methods = ['GET', 'PUT'] 
    permission_classes = [AllowAny]

    def get_object(self):
        reset_token = self.kwargs['reset_token']
        try:
            user = Token.objects.get(key=reset_token).user
            return user
        except Token.DoesNotExist:
            raise NotFound("Invalid reset token.")

    def put(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Update the user's password
        new_password = request.data.get('password')
        if new_password is not None:
            user.set_password(new_password)
            user.save()

        # Actualizar cualquier otro campo adicional si es necesario
        user_profile = user.userprofile
        staff_status = request.data.get('staff_status')
        if staff_status is not None:
            user_profile.staff_status = staff_status
            user_profile.save()

        serializer.save()

        return Response(serializer.data)