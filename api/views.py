# backend\api\views.py
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail, EmailMessage
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, Count, Avg
from .models import UserProfile, Customer, Order, OrderEvent, Promotion, CustomerPoints, ProductionQueue, Invoice, Payment
from .serializers import (
    UserSerializer, CustomerSerializer, OrderSerializer, OrderEventSerializer,
    PromotionSerializer, CustomerPointsSerializer, ProductionQueueSerializer,
    ResetPasswordSerializer, EmailSerializer, InvoiceSerializer, PaymentSerializer
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
import requests
import io
import logging
import json
import uuid
from rest_framework import serializers
from collections import defaultdict

# Configure logging with file output
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

class IsAdminOrSalesOrDesign(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            logger.warning("Unauthenticated user attempted access")
            return False
        profile = UserProfile.objects.filter(user=request.user).first()
        logger.debug(f"User: {request.user}, Profile: {profile}, staff_status: {profile.staff_status if profile else None}")
        return profile and profile.staff_status in ['administrator', 'sales', 'design']

class IsAdminOrSales(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            logger.warning("Unauthenticated user attempted access")
            return False
        profile = UserProfile.objects.filter(user=request.user).first()
        logger.debug(f"User: {request.user}, Profile: {profile}, staff_status: {profile.staff_status if profile else None}")
        return profile and profile.staff_status in ['administrator', 'sales']

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        logger.debug(f"User {self.request.user} accessing UserViewSet.get_queryset")
        if self.request.user.userprofile.staff_status == 'administrator':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def update(self, request, *args, **kwargs):
        logger.debug(f"User {request.user} updating user with data: {request.data}")
        data = request.data.get('data', request.data)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        logger.info(f"User {instance.id} updated successfully")
        return Response(serializer.data)

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        logger.debug(f"User {self.request.user} accessing CustomerViewSet.get_queryset")
        if self.request.user.userprofile.staff_status in ['administrator', 'sales']:
            return Customer.objects.all()
        return Customer.objects.filter(user=self.request.user)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        logger.debug(f"User {user} accessing OrderViewSet.get_queryset")
        try:
            user_profile = user.userprofile
        except UserProfile.DoesNotExist:
            logger.error(f"User {user.username} has no UserProfile")
            return Order.objects.none()
        if user_profile.staff_status == 'administrator':
            return Order.objects.all()
        elif user_profile.staff_status == 'sales':
            return Order.objects.all()
        elif user_profile.staff_status == 'design':
            return Order.objects.filter(status__in=['design_pending', 'design_confirmed'])
        else:
            return Order.objects.filter(customer__user=user)

    def create(self, request, *args, **kwargs):
        # Log raw FormData as received
        raw_data = {k: ["<binary>" if hasattr(val, 'read') or isinstance(val, (bytes, bytearray)) else val for val in vals] for k, vals in request.data.lists()}
        logger.info(f"POST /api/orders/ raw FormData (keys and values):\n{json.dumps(raw_data, indent=2)}\nFiles:\n{json.dumps({k: v.name for k, v in request.FILES.items()}, indent=2)}")

        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        files = request.FILES

        try:
            # Extract: Parse items
            items = data.get('items')
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                    logger.debug(f"Transformed items:\n{json.dumps(items, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse items JSON: {str(e)}")
                    return Response(
                        {
                            "detail": "Invalid JSON format in items field.",
                            "error": str(e),
                            "request_data": raw_data
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif isinstance(items, list):
                logger.debug(f"Items already a list:\n{json.dumps(items, indent=2)}")
            else:
                logger.debug("No items provided in request, setting to empty list")
                items = []
            data['items'] = items

            # Extract: Parse uniform_detail
            uniform_detail = data.get('uniform_detail')
            if isinstance(uniform_detail, str):
                try:
                    uniform_detail = json.loads(uniform_detail)
                    logger.debug(f"Transformed uniform_detail:\n{json.dumps(uniform_detail, indent=2)}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse uniform_detail JSON: {str(e)}")
                    return Response(
                        {
                            "detail": "Invalid JSON format in uniform_detail field.",
                            "error": str(e),
                            "request_data": raw_data
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif uniform_detail is None or uniform_detail == '':
                uniform_detail = None
                logger.debug("No uniform_detail provided in request")
            else:
                logger.debug(f"uniform_detail already a dict:\n{json.dumps(uniform_detail, indent=2)}")
            data['uniform_detail'] = uniform_detail

            # Transform: Convert empty string date fields to None
            if 'payment_50_date' in data and data['payment_50_date'] == '':
                data['payment_50_date'] = None
                logger.debug("Converted payment_50_date to None")
            if 'design_confirmation_date' in data and data['design_confirmation_date'] == '':
                data['design_confirmation_date'] = None
                logger.debug("Converted design_confirmation_date to None")

            # Transform: Attach uniform_detail files
            if uniform_detail:
                for field in ['player_uniform_photo', 'goalkeeper_uniform_photo', 'neck_photo', 'pants_photo']:
                    file_key = f"uniform_detail.{field}"
                    if file_key in files:
                        uniform_detail[field] = files[file_key]
                        logger.debug(f"Added {file_key} to uniform_detail: {files[file_key].name}")

            # Transform: Process items
            for index, item in enumerate(data['items']):
                file_key = f"items[{index}].design_file"
                if file_key in files:
                    item['design_file'] = files[file_key]
                    logger.debug(f"Added design_file to item {index}: {files[file_key].name}")

                # Convert string fields to appropriate types
                if isinstance(item.get('product'), str):
                    try:
                        item['product'] = int(item['product']) if item['product'] and item['product'] != 'null' else None
                    except (ValueError, TypeError):
                        logger.error(f"Invalid product ID in item {index}: {item.get('product')}")
                        return Response(
                            {"items": f"Invalid product ID in item {index}", "request_data": raw_data},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if isinstance(item.get('product_type'), str):
                    try:
                        item['product_type'] = int(item['product_type']) if item['product_type'] and item['product_type'] != 'null' else None
                    except (ValueError, TypeError):
                        logger.error(f"Invalid product_type ID in item {index}: {item.get('product_type')}")
                        return Response(
                            {"items": f"Invalid product_type ID in item {index}", "request_data": raw_data},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if isinstance(item.get('quantity'), str):
                    try:
                        item['quantity'] = int(item['quantity'])
                    except (ValueError, TypeError):
                        logger.error(f"Invalid quantity in item {index}: {item.get('quantity')}")
                        return Response(
                            {"items": f"Invalid quantity in item {index}", "request_data": raw_data},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if isinstance(item.get('unit_price'), str):
                    try:
                        item['unit_price'] = float(item['unit_price'])
                    except (ValueError, TypeError):
                        logger.error(f"Invalid unit_price in item {index}: {item.get('unit_price')}")
                        return Response(
                            {"items": f"Invalid unit_price in item {index}", "request_data": raw_data},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if 'id' in item and isinstance(item['id'], str):
                    try:
                        item['id'] = int(item['id']) if item['id'] and item['id'] != 'null' else None
                    except (ValueError, TypeError):
                        logger.error(f"Invalid id in item {index}: {item.get('id')}")
                        return Response(
                            {"items": f"Invalid id in item {index}", "request_data": raw_data},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            # Transform: Convert customer_id and use_points
            if isinstance(data.get('customer_id'), str):
                try:
                    uuid.UUID(data['customer_id'])
                except (ValueError, TypeError):
                    logger.error(f"Invalid customer_id: {data.get('customer_id')}")
                    return Response(
                        {"customer_id": "Must be a valid UUID", "request_data": raw_data},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            if isinstance(data.get('use_points'), str):
                data['use_points'] = data['use_points'].lower() == 'true'
                logger.debug(f"Converted use_points to: {data['use_points']}")

            # Log transformed data before serialization
            logger.info(f"Transformed data for serialization:\n{json.dumps(data, indent=2, default=str)}")

            # Load: Pass transformed data to serializer
            serializer = self.get_serializer(data=data, context={'request': request})
            try:
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                logger.info(f"Order created successfully: {serializer.data['order_number']}")
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            except serializers.ValidationError as e:
                logger.error(f"Validation error in POST /api/orders/: {e.detail}")
                return Response(
                    {
                        "detail": "Invalid data provided. Please check the required fields.",
                        "errors": e.detail,
                        "request_data": raw_data,
                        "transformed_data": data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Unexpected error in POST /api/orders/: {str(e)}")
                return Response(
                    {
                        "detail": f"Unexpected error: {str(e)}",
                        "errors": serializer.errors if hasattr(serializer, 'errors') else {},
                        "request_data": raw_data,
                        "transformed_data": data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Error during data transformation: {str(e)}")
            return Response(
                {"detail": f"Data transformation failed: {str(e)}", "request_data": raw_data},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        order = serializer.save(created_by=self.request.user)
        logger.debug(f"Created order: {order.order_number} for customer: {order.customer.name}")
        send_mail(
            subject=f'Nuevo pedido creado: {order.order_number}',
            message=f'Se ha creado un nuevo pedido {order.order_number} para el cliente {order.customer.name}.',
            from_email='soporte@dirlux.com',
            recipient_list=[order.customer.email] if order.customer.email else []
        )
        self.send_whatsapp_notification(
            order,
            f"Nuevo pedido {order.order_number} creado. Aprobar: http://localhost:3000/approve/{order.id}"
        )

    # backend\api\views.py
    def update(self, request, *args, **kwargs):
        # Log raw FormData as received with detailed formatting
        raw_data = {k: ["<binary>" if hasattr(val, 'read') or isinstance(val, (bytes, bytearray)) else val for val in vals] for k, vals in request.data.lists()}
        logger.info(f"PATCH/PUT /api/orders/{kwargs.get('pk')} raw FormData (keys and values):\n{json.dumps(raw_data, indent=2)}\nFiles:\n{json.dumps({k: v.name for k, v in request.FILES.items()}, indent=2)}")

        data = request.data.copy()

        try:
            # Parse flat form data into nested structures
            # Parse items
            item_dict = defaultdict(dict)
            for k in list(data.keys()):
                if k.startswith('items.'):
                    parts = k.split('.')
                    if len(parts) == 3:
                        _, idx_str, field = parts
                        try:
                            idx = int(idx_str)
                            item_dict[idx][field] = data.pop(k)[0]  # Take first value from list
                        except (ValueError, TypeError, IndexError):
                            logger.error(f"Invalid item key format: {k}")
                            return Response(
                                {"detail": f"Invalid item key format: {k}", "request_data": raw_data},
                                status=status.HTTP_400_BAD_REQUEST
                            )
            items = [item_dict[i] for i in sorted(item_dict.keys())] if item_dict else None
            if items:
                logger.info(f"Parsed items from flat form: {json.dumps(items, indent=2)}")
                data['items'] = items
            else:
                logger.info("No items provided in request, will preserve existing items")
                data['items'] = None

            # Parse uniform_detail and players
            ud_dict = {}
            player_dict = defaultdict(dict)
            for k in list(data.keys()):
                if k.startswith('uniform_detail.'):
                    parts = k.split('.')
                    if len(parts) == 2:
                        _, field = parts
                        ud_dict[field] = data.pop(k)[0]  # Take first value from list
                    elif len(parts) == 4 and parts[1] == 'players':
                        _, _, idx_str, field = parts
                        try:
                            idx = int(idx_str)
                            player_dict[idx][field] = data.pop(k)[0]  # Take first value from list
                        except (ValueError, TypeError, IndexError):
                            logger.error(f"Invalid player key format: {k}")
                            return Response(
                                {"detail": f"Invalid player key format: {k}", "request_data": raw_data},
                                status=status.HTTP_400_BAD_REQUEST
                            )
            uniform_detail = ud_dict if ud_dict else None
            if player_dict:
                uniform_detail = uniform_detail or {}
                uniform_detail['players'] = [player_dict[i] for i in sorted(player_dict.keys())]
            if uniform_detail:
                logger.info(f"Parsed uniform_detail from flat form: {json.dumps(uniform_detail, indent=2)}")
                data['uniform_detail'] = uniform_detail
            else:
                logger.info("No uniform_detail provided in request, will preserve existing uniform_detail")
                data['uniform_detail'] = None

            # Transform: Handle files for items
            if 'items' in data and isinstance(data['items'], list):
                for index, item in enumerate(data['items']):
                    file_key = f"items.{index}.design_file"
                    if file_key in request.FILES:
                        item['design_file'] = request.FILES[file_key]
                        logger.debug(f"Added design_file to item {index}: {request.FILES[file_key].name}")

                    # Convert string fields to appropriate types
                    for field, target_type in [
                        ('id', int), ('product', int), ('product_type', int),
                        ('quantity', int), ('unit_price', float)
                    ]:
                        if field in item and isinstance(item[field], str):
                            try:
                                item[field] = target_type(item[field]) if item[field] and item[field] != 'null' else None
                            except (ValueError, TypeError):
                                logger.error(f"Invalid {field} in item {index}: {item[field]}")
                                return Response(
                                    {"items": f"Invalid {field} in item {index}", "request_data": raw_data},
                                    status=status.HTTP_400_BAD_REQUEST
                                )

            # Transform: Handle files for uniform_detail
            if 'uniform_detail' in data and data['uniform_detail']:
                for field in ['player_uniform_photo', 'goalkeeper_uniform_photo', 'neck_photo', 'pants_photo']:
                    file_key = f"uniform_detail.{field}"
                    if file_key in request.FILES:
                        data['uniform_detail'][field] = request.FILES[file_key]
                        logger.debug(f"Added {file_key} to uniform_detail: {request.FILES[file_key].name}")
                    elif field in data['uniform_detail'] and data['uniform_detail'][field]:
                        # Preserve existing file if provided as URL or not changed
                        logger.debug(f"Preserving existing {field} in uniform_detail: {data['uniform_detail'][field]}")
                
                # Convert uniform_detail fields to appropriate types
                for field in ['shirt_quantity', 'pants_quantity', 'polo_quantity', 'bag_quantity']:
                    if field in data['uniform_detail'] and isinstance(data['uniform_detail'][field], str):
                        try:
                            data['uniform_detail'][field] = int(data['uniform_detail'][field])
                        except (ValueError, TypeError):
                            logger.error(f"Invalid {field} in uniform_detail: {data['uniform_detail'][field]}")
                            return Response(
                                {"uniform_detail": f"Invalid {field}", "request_data": raw_data},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                
                # Convert player fields
                if 'players' in data['uniform_detail']:
                    for index, player in enumerate(data['uniform_detail']['players']):
                        for field, target_type in [
                            ('id', int), ('number', int)
                        ]:
                            if field in player and isinstance(player[field], str):
                                try:
                                    player[field] = target_type(player[field]) if player[field] and player[field] != 'null' else None
                                except (ValueError, TypeError):
                                    logger.error(f"Invalid {field} in player {index}: {player[field]}")
                                    return Response(
                                        {"uniform_detail.players": f"Invalid {field} in player {index}", "request_data": raw_data},
                                        status=status.HTTP_400_BAD_REQUEST
                                    )

            # Transform: Convert top-level fields
            if 'payment_50_date' in data and data['payment_50_date'] == '':
                data['payment_50_date'] = None
                logger.debug("Converted payment_50_date to None")
            if 'design_confirmation_date' in data and data['design_confirmation_date'] == '':
                data['design_confirmation_date'] = None
                logger.debug("Converted design_confirmation_date to None")
            if isinstance(data.get('customer_id'), str):
                try:
                    uuid.UUID(data['customer_id'])
                except (ValueError, TypeError):
                    logger.error(f"Invalid customer_id: {data.get('customer_id')}")
                    return Response(
                        {"customer_id": "Must be a valid UUID", "request_data": raw_data},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            if isinstance(data.get('use_points'), str):
                data['use_points'] = data['use_points'].lower() == 'true'
                logger.debug(f"Converted use_points to: {data['use_points']}")

            # Log transformed data before serialization
            logger.info(f"Transformed data for serialization:\n{json.dumps(data, indent=2, default=str)}")

            # Load: Pass transformed data to serializer
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True, context={'request': request})
            try:
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                logger.info(f"Order updated successfully: {serializer.data['order_number']}")
                return Response(serializer.data)
            except serializers.ValidationError as e:
                logger.error(f"Validation error in PATCH/PUT /api/orders/{kwargs.get('pk')}: {e.detail}")
                return Response(
                    {
                        "detail": "Validation error",
                        "errors": e.detail,
                        "request_data": raw_data,
                        "transformed_data": data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Unexpected error in PATCH/PUT /api/orders/{kwargs.get('pk')}: {str(e)}")
                return Response(
                    {
                        "detail": f"Unexpected error: {str(e)}",
                        "errors": serializer.errors if hasattr(serializer, 'errors') else {},
                        "request_data": raw_data,
                        "transformed_data": data
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Error during data transformation: {str(e)}")
            return Response(
                {
                    "detail": f"Data transformation failed: {str(e)}",
                    "request_data": raw_data
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_update(self, serializer):
        order = serializer.save()
        if 'status' in serializer.validated_data:
            send_mail(
                subject=f'Actualización de estado del pedido {order.order_number}',
                message=f'El estado del pedido {order.order_number} ha cambiado a {order.get_status_display()}.',
                from_email='soporte@dirlux.com',
                recipient_list=[order.customer.email] if order.customer.email else []
            )
            self.send_whatsapp_notification(
                order,
                f"El estado del pedido {order.order_number} ha cambiado a {order.get_status_display()}. "
                f"Aprobar: http://localhost:3000/approve/{order.id}"
            )

    def send_whatsapp_notification(self, order, message):
        whatsapp_api_url = "https://api.whatsapp.com/send"
        phone_number = order.customer.phone_number
        if phone_number:
            try:
                requests.post(whatsapp_api_url, json={
                    'phone': phone_number,
                    'message': message
                })
                logger.debug(f"WhatsApp notification sent for order {order.order_number}")
            except Exception as e:
                logger.error(f"Error enviando WhatsApp for order {order.order_number}: {e}")

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_event(self, request, pk=None):
        logger.debug(f"POST /api/orders/{pk}/add_event/ request data: {request.data}")
        order = self.get_object()
        event_type = request.data.get('event_type')
        document = request.FILES.get('document')
        if event_type not in dict(OrderEvent.EVENT_TYPES):
            logger.error(f"Invalid event_type: {event_type}")
            return Response({'error': 'Tipo de evento inválido'}, status=status.HTTP_400_BAD_REQUEST)

        OrderEvent.objects.create(
            order=order,
            event_type=event_type,
            user=request.user,
            document=document
        )

        send_mail(
            subject=f'Evento en pedido {order.order_number}: {dict(OrderEvent.EVENT_TYPES)[event_type]}',
            message=f'El pedido {order.order_number} ha sido {dict(OrderEvent.EVENT_TYPES)[event_type].lower()} por {request.user.username}.',
            from_email='soporte@dirlux.com',
            recipient_list=[order.customer.email] if order.customer.email else []
        )
        self.send_whatsapp_notification(
            order,
            f"Evento en pedido {order.order_number}: {dict(OrderEvent.EVENT_TYPES)[event_type]}. "
            f"Aprobar: http://localhost:3000/approve/{order.id}"
        )

        logger.info(f"Event {event_type} added to order {order.order_number}")
        return Response({'message': 'Evento registrado correctamente'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put'], permission_classes=[permissions.IsAuthenticated])
    def update_event(self, request, pk=None, event_id=None):
        logger.debug(f"PUT /api/orders/{pk}/events/{event_id}/ request data: {request.data}")
        try:
            order = self.get_object()
            event = OrderEvent.objects.get(id=event_id, order=order)
        except OrderEvent.DoesNotExist:
            logger.error(f"Event {event_id} not found for order {pk}")
            return Response({'error': 'Evento no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        user_profile = request.user.userprofile
        if user_profile.staff_status not in ['administrator', 'sales', 'design']:
            logger.error(f"User {request.user.username} not authorized to update events")
            return Response({'error': 'No tienes permisos para editar eventos.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = OrderEventSerializer(event, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            send_mail(
                subject=f'Evento actualizado en pedido {order.order_number}: {dict(OrderEvent.EVENT_TYPES)[event.event_type]}',
                message=f'El evento {dict(OrderEvent.EVENT_TYPES)[event.event_type]} del pedido {order.order_number} ha sido actualizado por {request.user.username}.',
                from_email='soporte@dirlux.com',
                recipient_list=[order.customer.email] if order.customer.email else []
            )
            self.send_whatsapp_notification(
                order,
                f"Evento actualizado en pedido {order.order_number}: {dict(OrderEvent.EVENT_TYPES)[event.event_type]}. "
                f"Aprobar: http://localhost:3000/approve/{order.id}"
            )
            logger.info(f"Event {event_id} updated for order {order.order_number}")
            return Response(serializer.data)
        logger.error(f"Validation error in updating event {event_id}: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def delete_event(self, request, pk=None, event_id=None):
        logger.debug(f"DELETE /api/orders/{pk}/events/{event_id}/")
        try:
            order = self.get_object()
            event = OrderEvent.objects.get(id=event_id, order=order)
        except OrderEvent.DoesNotExist:
            logger.error(f"Event {event_id} not found for order {pk}")
            return Response({'error': 'Evento no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        user_profile = request.user.userprofile
        if user_profile.staff_status not in ['administrator', 'sales', 'design']:
            logger.error(f"User {request.user.username} not authorized to delete events")
            return Response({'error': 'No tienes permisos para eliminar eventos.'}, status=status.HTTP_403_FORBIDDEN)

        event_type_display = dict(OrderEvent.EVENT_TYPES)[event.event_type]
        event.delete()
        send_mail(
            subject=f'Evento eliminado en pedido {order.order_number}: {event_type_display}',
            message=f'El evento {event_type_display} del pedido {order.order_number} ha sido eliminado por {request.user.username}.',
            from_email='soporte@dirlux.com',
            recipient_list=[order.customer.email] if order.customer.email else []
        )
        self.send_whatsapp_notification(
            order,
            f"Evento eliminado en pedido {order.order_number}: {event_type_display}. "
            f"Aprobar: http://localhost:3000/approve/{order.id}"
        )
        logger.info(f"Event {event_id} deleted from order {order.order_number}")
        return Response({'message': 'Evento eliminado correctamente'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def generate_invoice_pdf(self, request, pk=None):
        logger.debug(f"GET /api/orders/{pk}/generate_invoice_pdf/ by user {request.user}")
        order = self.get_object()
        if not order.invoice:
            logger.error(f"No invoice associated with order {order.order_number}")
            return Response({'error': 'No hay factura asociada'}, status=status.HTTP_400_BAD_REQUEST)
        invoice = order.invoice
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        text_color = colors.red if invoice.is_urgent else colors.black
        elements.append(Paragraph(f"Factura {invoice.invoice_number}", styles['Title']))
        elements.append(Spacer(1, 12))
        customer_data = [
            ['Cliente:', order.customer.name],
            ['Cédula:', order.customer.id_number],
            ['Dirección:', order.customer.address or 'N/A'],
            ['Correo:', order.customer.email or 'N/A'],
            ['Teléfono:', order.customer.phone_number or 'N/A']
        ]
        customer_table = Table(customer_data)
        customer_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 12))
        items_data = [['Producto', 'Cantidad', 'Precio Unitario', 'Total']]
        for item in order.items.all():
            product_name = item.product.name if item.product else item.product_type.name
            items_data.append([product_name, item.quantity, f"{item.unit_price:.2f}", f"{item.quantity * item.unit_price:.2f}"])
        items_table = Table(items_data)
        items_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey)
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 12))
        total_data = [
            ['Subtotal:', f"{invoice.total_amount - invoice.tax:.2f}"],
            ['IVA (13%):', f"{invoice.tax:.2f}"],
            ['Total:', f"{invoice.total_amount:.2f}"]
        ]
        total_table = Table(total_data)
        total_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(total_table)
        elements.append(Spacer(1, 12))
        signature_data = [
            ['Firma:', invoice.signature_field or '____________________'],
            ['Revisado:', invoice.reviewed_date or '____________________'],
            ['Empacado:', invoice.packed_date or '____________________'],
            ['Entregado:', invoice.delivered_date or '____________________']
        ]
        signature_table = Table(signature_data)
        signature_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(signature_table)
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        logger.info(f"Invoice PDF generated for order {order.order_number}")
        return Response(response)

    def list(self, request, *args, **kwargs):
        logger.debug(f"User {request.user} listing orders")
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in list orders: {str(e)}")
            return Response([], status=status.HTTP_200_OK)

class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAdminOrSalesOrDesign]

class CustomerPointsViewSet(viewsets.ModelViewSet):
    queryset = CustomerPoints.objects.all()
    serializer_class = CustomerPointsSerializer
    permission_classes = [IsAdminOrSales]

class ProductionQueueViewSet(viewsets.ModelViewSet):
    queryset = ProductionQueue.objects.all()
    serializer_class = ProductionQueueSerializer
    permission_classes = [IsAdminOrSalesOrDesign]

    def get_queryset(self):
        queue_type = self.request.query_params.get('queue_type')
        logger.debug(f"ProductionQueueViewSet.get_queryset with queue_type: {queue_type}")
        if queue_type:
            return ProductionQueue.objects.filter(queue_type=queue_type).order_by('delivery_date')
        return ProductionQueue.objects.all().order_by('delivery_date')

    def perform_create(self, serializer):
        logger.debug(f"Creating production queue with data: {serializer.validated_data}")
        order = serializer.validated_data['order']
        delivery_date = serializer.validated_data['delivery_date']
        product_type_quantities = {}
        for item in order.items.all():
            product_type = item.product_type or item.product.product_type
            product_type_id = product_type.id
            product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + item.quantity
        for product_type_id, requested_quantity in product_type_quantities.items():
            product_type = ProductType.objects.get(id=product_type_id)
            existing_queues = ProductionQueue.objects.filter(
                delivery_date=delivery_date,
                order__items__product_type=product_type
            ).exclude(order=order).distinct()
            existing_quantity = sum(
                item.quantity for queue in existing_queues
                for item in queue.order.items.filter(product_type=product_type)
            )
            total_quantity = existing_quantity + requested_quantity
            if total_quantity > product_type.daily_production_capacity:
                raise serializers.ValidationError(
                    f"La cantidad solicitada ({total_quantity}) para {product_type.name} excede la capacidad diaria de producción ({product_type.daily_production_capacity}) para la fecha {delivery_date}."
                )
        serializer.save(queue_type=order.order_type)
        logger.info(f"Production queue created for order {order.order_number}")

class ProductionQueueDashboardAPIView(APIView):
    permission_classes = [IsAdminOrSalesOrDesign]

    def get(self, request):
        logger.debug(f"ProductionQueueDashboardAPIView.get with query params: {request.query_params}")
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        queue_type = request.query_params.get('queue_type')
        status = request.query_params.get('status')

        queryset = ProductionQueue.objects.all()
        if start_date:
            queryset = queryset.filter(delivery_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(delivery_date__lte=end_date)
        if queue_type:
            queryset = queryset.filter(queue_type=queue_type)
        if status:
            queryset = queryset.filter(order__status=status)

        serializer = ProductionQueueSerializer(queryset, many=True)
        response_data = {
            'queues': serializer.data,
            'total_orders': queryset.count(),
            'by_status': {
                'pending': queryset.filter(order__status='pending').count(),
                'in_progress': queryset.filter(order__status='in_progress').count(),
                'design_pending': queryset.filter(order__status='design_pending').count(),
                'design_confirmed': queryset.filter(order__status='design_confirmed').count(),
                'completed': queryset.filter(order__status='completed').count(),
            }
        }
        logger.info(f"Production queue dashboard data retrieved: {response_data}")
        return Response(response_data)

class InactiveOrdersAPIView(APIView):
    permission_classes = [IsAdminOrSales]

    def get(self, request):
        logger.debug(f"InactiveOrdersAPIView.get with query params: {request.query_params}")
        inactivity_days = int(request.query_params.get('days', 3))
        threshold_date = timezone.now() - timedelta(days=inactivity_days)
        inactive_orders = Order.objects.filter(
            updated_at__lt=threshold_date,
            status__in=['pending', 'design_pending']
        )
        for order in inactive_orders:
            send_mail(
                subject=f'Pedido inactivo: {order.order_number}',
                message=f'El pedido {order.order_number} no ha tenido movimiento en {inactivity_days} días. '
                        f'Por favor, revisa su estado.',
                from_email='soporte@dirlux.com',
                recipient_list=[order.customer.email] if order.customer.email else []
            )
            order_view = OrderViewSet()
            order_view.send_whatsapp_notification(
                order,
                f"Pedido {order.order_number} inactivo por {inactivity_days} días. "
                f"Revisar: http://localhost:3000/orders/{order.id}"
            )
        logger.info(f"Notifications sent for {inactive_orders.count()} inactive orders")
        return Response({'message': f'Notificaciones enviadas para {inactive_orders.count()} pedidos inactivos.'})

class DashboardAPIView(APIView):
    permission_classes = [IsAdminOrSales]

    def get(self, request):
        logger.debug(f"User {request.user} accessing DashboardAPIView")
        total_sales = Invoice.objects.filter(order__status='completed').aggregate(
            total=Sum('total_amount')
        )['total'] or 0.0
        orders_with_response = Order.objects.filter(
            order_date__isnull=False,
            design_confirmation_date__isnull=False
        )
        avg_response_time = orders_with_response.aggregate(
            avg_response=Avg(
                models.ExpressionWrapper(
                    models.F('design_confirmation_date') - models.F('order_date'),
                    output_field=models.DurationField()
                )
            )
        )['avg_response'] or timedelta(0)
        avg_response_days = avg_response_time.days + avg_response_time.seconds / (24 * 3600)
        status_distribution = Order.objects.values('status').annotate(count=Count('id'))
        metrics = {
            'total_sales': float(total_sales),
            'average_response_time_days': float(avg_response_days),
            'status_distribution': [
                {'status': item['status'], 'count': item['count']}
                for item in status_distribution
            ]
        }
        logger.debug(f"Dashboard metrics: {metrics}")
        return Response(metrics)

class SignupAPIView(APIView):
    def post(self, request):
        logger.debug(f"Signup request data: {request.data}")
        try:
            data = request.data
            first_name = data['first_name']
            last_name = data['last_name']
            email = data['email']
            password = data['password']
            staff_status = data.get('staff_status', 'customer')
            phone_number = data.get('phone_number', '')
            address = data.get('address', '')
            if User.objects.filter(email=email).exists():
                logger.error(f"Email {email} already registered")
                return Response({'error': 'El correo electrónico ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.create_user(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password
            )
            UserProfile.objects.create(
                user=user,
                staff_status=staff_status,
                phone_number=phone_number,
                address=address
            )
            token = Token.objects.create(user=user)
            logger.info(f"User {email} signed up successfully")
            return Response({'token': str(token)}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error in signup: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    def post(self, request):
        logger.debug(f"Login request data: {request.data}")
        data = request.data
        user = authenticate(
            request,
            username=data['username'],
            password=data['password']
        )
        if user is None:
            logger.error(f"Login failed for username {data['username']}")
            return Response(
                {'error': 'No se pudo iniciar sesión. Verifique usuario y contraseña.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            token, _ = Token.objects.get_or_create(user=user)
            logger.info(f"User {user.username} logged in successfully")
            return Response({'token': str(token)}, status=status.HTTP_200_OK)

class ResetPasswordAPIView(APIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        logger.debug(f"Reset password request data: {request.data}")
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                token, _ = Token.objects.get_or_create(user=user)
                current_site = get_current_site(request)
                reset_url = reverse('reset_password_user', kwargs={'reset_token': token.key})
                reset_password_url = f"https://{current_site.domain}{reset_url}"
                send_mail(
                    subject='Restablecer contraseña',
                    message=f"Haga clic en el siguiente enlace para restablecer su contraseña:\n{reset_password_url}",
                    from_email='soporte@dirlux.com',
                    recipient_list=[email]
                )
                logger.info(f"Password reset email sent to {email}")
                return Response('Correo enviado exitosamente.', status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.error(f"User with email {email} not found")
                return Response({'error': 'Usuario con el correo proporcionado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        logger.error(f"Reset password validation error: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordUser(APIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self, reset_token):
        try:
            return Token.objects.get(key=reset_token).user
        except Token.DoesNotExist:
            logger.error(f"Invalid reset token: {reset_token}")
            return None

    def post(self, request, reset_token):
        logger.debug(f"Reset password user request data: {request.data}, token: {reset_token}")
        user = self.get_object(reset_token)
        if not user:
            return Response({'error': 'Token de restablecimiento inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Password reset for user {user.username}")
            return Response({'message': 'Contraseña actualizada correctamente.'}, status=status.HTTP_200_OK)
        logger.error(f"Password reset validation error: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailAPIView(APIView):
    def post(self, request):
        logger.debug(f"Email request data: {request.data}")
        serializer = EmailSerializer(data=request.data)
        if serializer.is_valid():
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            from_email = serializer.validated_data['from_email']
            recipient_list = serializer.validated_data['recipient_list']
            try:
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=from_email,
                    to=recipient_list
                )
                email.send()
                logger.info(f"Email sent to {recipient_list}")
                return Response({'message': 'Correo enviado exitosamente.'}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error sending email: {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        logger.error(f"Email validation error: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)