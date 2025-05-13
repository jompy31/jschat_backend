from rest_framework import generics
from .models import File, NewsPost, Distributor, Design, Service
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import FileSerializer, NewsPostSerializer, DistributorSerializer, DesignSerializer, ServiceSerializer
from rest_framework import status

class FileListCreate(generics.ListCreateAPIView):
    serializer_class = FileSerializer
    queryset = File.objects.all()

    def perform_create(self, serializer):
        file = self.request.data.get('file')
        name = self.request.data.get('name')
        if file and name:
            serializer.save(user=self.request.user, file=file, name=name)
        else:
            serializer.save(user=self.request.user)
            
class FileDestroy(generics.DestroyAPIView):
    queryset = File.objects.all()
    serializer_class = FileSerializer

class FileRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = File.objects.all()
    serializer_class = FileSerializer

class NewsPostListCreate(generics.ListCreateAPIView):
    queryset = NewsPost.objects.all()
    serializer_class = NewsPostSerializer

    def perform_create(self, serializer):
        # Solo se establecen los campos requeridos
        serializer.save()
        
    def post(self, request, *args, **kwargs):
        print("Datos recibidos:", request.data)  # Imprime los datos del cliente
        try:
            return super().post(request, *args, **kwargs)
        except Exception as e:
            print(f"Error durante la creación: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class NewsPostRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = NewsPost.objects.all()
    serializer_class = NewsPostSerializer

    def perform_update(self, serializer):
        serializer.save()

class DistributorListCreate(generics.ListCreateAPIView):
    queryset = Distributor.objects.all()
    serializer_class = DistributorSerializer
    def perform_create(self, serializer):
        serializer.save()
    def create(self, request, *args, **kwargs):
        logo = request.data.get('logo', None)
        name = request.data.get('name', None)
        # Add other fields as needed for duplicate checking
        # Check if a distributor with the same name already exists (case-insensitive)
        existing_distributor = Distributor.objects.filter(name__iexact=name).first()
        if existing_distributor:
            serializer = self.get_serializer(existing_distributor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # If no duplicate found, proceed with the creation
        data_copy = request.data.copy()
        data_copy.pop('logo', None)
        serializer = self.get_serializer(data=data_copy)
        serializer.is_valid(raise_exception=True)
        distributor = serializer.save()
        # Save the logo if provided
        if logo:
            distributor.logo = logo
            distributor.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class DistributorRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Distributor.objects.all()
    serializer_class = DistributorSerializer
class DistributorServicesList(APIView):
    def get(self, request, distributor_id):
        try:
            services = Service.objects.filter(distributor_id=distributor_id)
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Service.DoesNotExist:
            return Response({"message": "Services not found for the distributor"}, status=status.HTTP_404_NOT_FOUND)
class ServiceDeleteView(APIView):
    def delete(self, request, distributor_id, service_id):
        try:
            service = Service.objects.get(id=service_id, distributor_id=distributor_id)
            service.delete()
            return Response({"message": "Service deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        
class DistributorServicesList(APIView):
    def get(self, request, distributor_id):
        try:
            services = Service.objects.filter(distributor_id=distributor_id)
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Service.DoesNotExist:
            return Response({"message": "Services not found for the distributor"}, status=status.HTTP_404_NOT_FOUND)
    def post(self, request, distributor_id):
        print(request.data)
        try:
            distributor = Distributor.objects.get(id=distributor_id)
        except Distributor.DoesNotExist:
            return Response({"message": "Distributor not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(distributor=distributor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DesignListCreate(generics.ListCreateAPIView):
    queryset = Design.objects.all()
    serializer_class = DesignSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class DesignRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Design.objects.all()
    serializer_class = DesignSerializer
