from rest_framework import serializers
from django.contrib.auth.models import User
from todo.models import Todo
from .models import UserProfile, Lead, Comment, WorkExperience, Skill

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = ['id','user', 'job_title', 'company_name', 'start_date', 'end_date', 'responsibilities']
    
    def create(self, validated_data):
        # Suponiendo que el usuario está en el contexto
        user = self.context['request'].user  # Obtener el usuario actual
        validated_data['user'] = user  # Asignar el usuario al nuevo Skill
        return WorkExperience.objects.create(**validated_data)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'user', 'name']  # Cambiado de 'user_profile' a 'user'
    
    def create(self, validated_data):
        # Suponiendo que el usuario está en el contexto
        user = self.context['request'].user  # Obtener el usuario actual
        validated_data['user'] = user  # Asignar el usuario al nuevo Skill
        return Skill.objects.create(**validated_data)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=1000)
    from_email = serializers.EmailField()
    recipient_list = serializers.CharField()  # Esto lo mantienes como una cadena
    attachments = serializers.ListField(child=serializers.FileField(), required=False)  # Esto es para archivos

    # Método para limpiar recipient_list y convertirlo en lista
    def validate_recipient_list(self, value):
        return [email.strip() for email in value.split(',')]

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Comment
        fields = ['id', 'user', 'comment', 'timestamp']

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'
    
    def create(self, validated_data):
        # Remove created_by from validated_data if it exists
        created_by = self.context['request'].user
        validated_data.pop('created_by', None)
        
        # Create the Lead instance
        lead = Lead.objects.create(created_by=created_by, **validated_data)
        return lead


class TodoSerializer(serializers.ModelSerializer):
    created = serializers.ReadOnlyField()
    completed = serializers.ReadOnlyField()
    
    class Meta:
        model = Todo
        fields = ['id', 'title', 'memo', 'created', 'completed']

class TodoToggleCompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Todo
        fields = ['id']  # why need to show id?
        read_only_fields = ['title', 'memo', 'created', 'completed']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    staff_status = serializers.CharField(source='userprofile.staff_status')
    company = serializers.CharField(source='userprofile.company', allow_blank=True, required=False)
    phone_number = serializers.CharField(source='userprofile.phone_number', allow_blank=True, required=False)
    address = serializers.CharField(source='userprofile.address', allow_blank=True, required=False)
    profile_picture = serializers.ImageField(source='userprofile.profile_picture', required=False)
    bio = serializers.CharField(source='userprofile.bio', allow_blank=True, required=False)
    date_of_birth = serializers.DateField(source='userprofile.date_of_birth', allow_null=True, required=False)
    country = serializers.CharField(source='userprofile.country', allow_null=True, required=False)
    openwork = serializers.BooleanField(source='userprofile.openwork', required=False, default=False)

    # Nuevos campos
    id_number = serializers.CharField(source='userprofile.id_number', allow_blank=True, required=False)
    id_type = serializers.CharField(source='userprofile.id_type', allow_blank=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'password', 'first_name', 'last_name', 'email', 'staff_status', 'country', 'company', 
                  'phone_number', 'address', 'profile_picture', 'bio', 'date_of_birth', 'openwork', 
                  'id_number', 'id_type']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
        )
        user_profile_data = validated_data.get('userprofile', {})

        # Crear el perfil de usuario con los campos id_number y id_type
        user_profile = UserProfile.objects.create(
            user=user,
            staff_status=user_profile_data.get('staff_status', 'customer'),
            openwork=user_profile_data.get('openwork', False),
            id_number=user_profile_data.get('id_number', ''),
            id_type=user_profile_data.get('id_type', '')
        )
        return user

    def update(self, instance, validated_data):
        # Actualizar los campos del usuario
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)

        # Actualizar el perfil de usuario
        user_profile = instance.userprofile

        # Actualizar el staff_status
        staff_status = validated_data.get('staff_status', user_profile.staff_status)
        allowed_choices = [choice[0] for choice in UserProfile._meta.get_field('staff_status').choices]
        if staff_status not in allowed_choices:
            raise serializers.ValidationError('Invalid staff status.')
        user_profile.staff_status = staff_status

        # Actualizar otros campos del perfil de usuario
        user_profile.company = validated_data.get('userprofile', {}).get('company', user_profile.company)
        user_profile.phone_number = validated_data.get('userprofile', {}).get('phone_number', user_profile.phone_number)
        user_profile.address = validated_data.get('userprofile', {}).get('address', user_profile.address)
        user_profile.bio = validated_data.get('userprofile', {}).get('bio', user_profile.bio)
        user_profile.date_of_birth = validated_data.get('userprofile', {}).get('date_of_birth', user_profile.date_of_birth)
        user_profile.openwork = validated_data.get('userprofile', {}).get('openwork', user_profile.openwork)

        # Actualizar los campos id_number y id_type
        user_profile.id_number = validated_data.get('userprofile', {}).get('id_number', user_profile.id_number)
        user_profile.id_type = validated_data.get('userprofile', {}).get('id_type', user_profile.id_type)

        # Actualizar la imagen de perfil si se proporciona
        profile_picture = validated_data.get('userprofile', {}).get('profile_picture', None)
        if profile_picture:
            user_profile.profile_picture = profile_picture

        user_profile.save()

        # Actualizar la contraseña si se proporciona
        password = validated_data.get('password', None)
        if password:
            instance.set_password(password)  # Utilizar set_password para el hash de la contraseña

        instance.save()
        return instance
