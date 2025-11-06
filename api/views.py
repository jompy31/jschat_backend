# backend\api\views.py
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models.functions import TruncMonth
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Avg, Max, F, ExpressionWrapper, FloatField, Value, Subquery, OuterRef, DecimalField
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail, EmailMessage
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, Count, Avg
from .models import UserProfile, PointsConfig ,Customer, Order, OrderItem, OrderEvent, Promotion, CustomerPoints, ProductionQueue, Invoice, Payment, EVENT_TYPE_CHOICES, ProductType
from .serializers import (
    UserSerializer, CustomerSerializer, OrderSerializer, OrderEventSerializer,
    PromotionSerializer, CustomerPointsSerializer, ProductionQueueSerializer,
    ResetPasswordSerializer, EmailSerializer, InvoiceSerializer, PaymentSerializer, DashboardOrderSummarySerializer,
    DashboardProductionDaySerializer,
    DashboardProductPerformanceSerializer,
    DashboardCustomerMetricsSerializer,
    DashboardMetricsSerializer, PointsConfigSerializer
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
import requests
import io
import logging
import re
import json
import uuid
from rest_framework import serializers
from collections import defaultdict
from decimal import Decimal
from datetime import date, timedelta
from django.utils.timezone import now

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
def json_safe_dump(obj):
    def default(o):
        return str(o)
    try:
        return json.dumps(obj, default=default, indent=2)
    except Exception as e:
        return f"Error dumping: {str(e)} - {str(obj)}"

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
        logger.info("=== INICIO OrderViewSet.create() ===")
        raw_data = {
            k: ["<binary>" if hasattr(val, 'read') else val for val in vals]
            for k, vals in request.data.lists()
        }
        logger.info(f"FormData:\n{json.dumps(raw_data, indent=2)}")
        logger.info(f"Files: { {k: v.name for k, v in request.FILES.items()} }")

        try:
            # Parsear ítems
            item_dict = defaultdict(dict)
            item_files = {}
            for key in list(request.data.keys()):
                if key.startswith('items['):
                    match = re.match(r'items\[(\d+)\]\.(.+)', key)
                    if match:
                        idx = int(match.group(1))
                        field = match.group(2)
                        value = request.data[key]
                        if field == 'design_file' and key in request.FILES:
                            item_files[idx] = request.FILES[key]
                            continue
                        item_dict[idx][field] = value

            # Parsear uniform_detail
            uniform_dict = {}
            player_dict = defaultdict(dict)
            uniform_files = {}
            for key in list(request.data.keys()):
                if key.startswith('uniform_detail.'):
                    parts = key.split('.', 1)
                    if len(parts) != 2:
                        continue
                    field_path = parts[1]
                    if field_path.startswith('players['):
                        match = re.match(r'players\[(\d+)\]\.(.+)', field_path)
                        if match:
                            idx = int(match.group(1))
                            field = match.group(2)
                            player_dict[idx][field] = request.data[key]
                    else:
                        uniform_dict[field_path] = request.data[key]
                        if key in request.FILES:
                            uniform_files[field_path] = request.FILES[key]

            items = []
            for idx in sorted(item_dict.keys()):
                item = item_dict[idx]
                if 'quantity' in item:
                    item['quantity'] = int(item['quantity'])
                if 'product' in item and item['product']:
                    item['product'] = int(item['product'])
                if 'product_type' in item and item['product_type']:
                    item['product_type'] = int(item['product_type'])
                items.append(item)

            uniform_detail_data = {}
            for field, value in uniform_dict.items():
                if value == '' or value == ['']:
                    uniform_detail_data[field] = None
                else:
                    try:
                        uniform_detail_data[field] = int(value[0]) if isinstance(value, list) else int(value)
                    except (ValueError, TypeError):
                        uniform_detail_data[field] = value[0] if isinstance(value, list) else value
            for field, file in uniform_files.items():
                uniform_detail_data[field] = file
            if player_dict:
                players = []
                for idx in sorted(player_dict.keys()):
                    player = player_dict[idx]
                    if 'number' in player:
                        try:
                            player['number'] = int(player['number'])
                        except (ValueError, TypeError):
                            player['number'] = 0
                    players.append(player)
                uniform_detail_data['players'] = players

            # Datos principales
            data = {}
            top_level_keys = ['customer_id', 'order_type', 'status', 'order_date', 'delivery_date', 'use_points']
            for key in top_level_keys:
                if key in request.data:
                    value = request.data[key]
                    if isinstance(value, list):
                        value = value[0]
                    data[key] = value

            if 'use_points' in data:
                data['use_points'] = str(data['use_points']).lower() == 'true'
            if data.get('order_date') == '':
                data['order_date'] = None
            if data.get('delivery_date') == '':
                data['delivery_date'] = None

            # Contexto
            context = self.get_serializer_context()
            context['parsed_items'] = items
            context['item_files'] = item_files
            context['uniform_detail_data'] = uniform_detail_data if uniform_detail_data else None

            serializer = self.get_serializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            order = serializer.instance
            logger.info(f"ORDEN CREADA: {order.order_number} | ÍTEMS: {order.items.count()} | TOTAL: {order.total_amount}")
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            logger.error(f"Error en create(): {str(e)}", exc_info=True)
            return Response({"detail": str(e)}, status=500)

    def update(self, request, *args, **kwargs):
        logger.info(f"PATCH/PUT /api/orders/{kwargs.get('pk')} raw FormData")
        raw_data = {k: ["<binary>" if hasattr(val, 'read') else val for val in vals] for k, vals in request.data.lists()}
        logger.info(f"FormData:\n{json.dumps(raw_data, indent=2)}")

        data = request.data.copy()
        try:
            # Parsear ítems
            item_dict = defaultdict(dict)
            for k in list(data.keys()):
                if k.startswith('items.'):
                    parts = k.split('.')
                    if len(parts) == 3:
                        _, idx_str, field = parts
                        try:
                            idx = int(idx_str)
                            item_dict[idx][field] = data.pop(k)[0]
                        except (ValueError, TypeError, IndexError):
                            logger.error(f"Invalid item key format: {k}")
                            return Response({"detail": f"Invalid item key format: {k}"}, status=400)

            items = [item_dict[i] for i in sorted(item_dict.keys())] if item_dict else None
            item_files = {}
            for index, item in enumerate(items or []):
                file_key = f"items.{index}.design_file"
                if file_key in request.FILES:
                    item['design_file'] = request.FILES[file_key]
                    item_files[index] = request.FILES[file_key]
                for field, target_type in [('id', int), ('product', int), ('product_type', int), ('quantity', int)]:
                    if field in item and isinstance(item[field], str):
                        try:
                            item[field] = target_type(item[field]) if item[field] and item[field] != 'null' else None
                        except (ValueError, TypeError):
                            logger.error(f"Invalid {field} in item {index}: {item[field]}")
                            return Response({"items": f"Invalid {field} in item {index}"}, status=400)

            # Parsear uniform_detail
            ud_dict = {}
            player_dict = defaultdict(dict)
            for k in list(data.keys()):
                if k.startswith('uniform_detail.'):
                    parts = k.split('.')
                    if len(parts) == 2:
                        _, field = parts
                        ud_dict[field] = data.pop(k)[0]
                    elif len(parts) == 4 and parts[1] == 'players':
                        _, _, idx_str, field = parts
                        try:
                            idx = int(idx_str)
                            player_dict[idx][field] = data.pop(k)[0]
                        except (ValueError, TypeError, IndexError):
                            logger.error(f"Invalid player key format: {k}")
                            return Response({"detail": f"Invalid player key format: {k}"}, status=400)

            uniform_detail = ud_dict if ud_dict else None
            if player_dict:
                uniform_detail = uniform_detail or {}
                uniform_detail['players'] = [player_dict[i] for i in sorted(player_dict.keys())]
            if uniform_detail:
                for field in ['shirt_quantity', 'pants_quantity', 'polo_quantity', 'bag_quantity']:
                    if field in uniform_detail and isinstance(uniform_detail[field], str):
                        try:
                            uniform_detail[field] = int(uniform_detail[field])
                        except (ValueError, TypeError):
                            logger.error(f"Invalid {field} in uniform_detail: {uniform_detail[field]}")
                            return Response({"uniform_detail": f"Invalid {field}"}, status=400)
                for field in ['player_uniform_photo', 'goalkeeper_uniform_photo', 'neck_photo', 'pants_photo']:
                    file_key = f"uniform_detail.{field}"
                    if file_key in request.FILES:
                        uniform_detail[field] = request.FILES[file_key]

            if 'use_points' in data:
                data['use_points'] = data['use_points'].lower() == 'true'
            if 'delivery_date' in data and data['delivery_date'] == '':
                data['delivery_date'] = None
            if 'order_date' in data and data['order_date'] == '':
                data['order_date'] = None

            context = self.get_serializer_context()
            context['parsed_items'] = items
            context['item_files'] = item_files
            context['uniform_detail_data'] = uniform_detail if uniform_detail else None

            instance = self.get_object()
            serializer = self.get_serializer(instance, data=data, partial=True, context=context)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            logger.info(f"Order updated successfully: {serializer.data['order_number']}")
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error en update(): {str(e)}")
            return Response({"detail": str(e)}, status=400)
        
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
        logger.debug(f"POST /api/orders/{pk}/add_event/ - Raw request data: {request.data}, Files: { {k: v.name for k, v in request.FILES.items()} }")
        order = self.get_object()
        event_type = request.data.get('event_type')
        document = request.FILES.get('document')
        amount = request.data.get('amount', '0')

        # Log received data
        logger.info(f"Received event data: order_id={pk}, event_type={event_type}, amount={amount}, document={document.name if document else None}")

        # Validate event_type
        valid_event_types = [choice[0] for choice in EVENT_TYPE_CHOICES]
        if event_type not in valid_event_types:
            logger.error(f"Invalid event_type: {event_type}. Valid types: {valid_event_types}")
            return Response({'error': f'Tipo de evento inválido. Opciones válidas: {valid_event_types}'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate amount for non-payment events
        try:
            amount = Decimal(amount)
            if event_type != 'payment' and amount != 0:
                logger.error(f"Invalid amount {amount} for event_type {event_type}. Amount must be 0 for non-payment events.")
                return Response({'error': 'El monto solo es válido para eventos de tipo "payment".'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            logger.error(f"Invalid amount format: {amount}")
            return Response({'error': 'Formato de monto inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        # Log before creating event
        logger.debug(f"Creating OrderEvent for order {order.order_number} with event_type={event_type}, amount={amount}")

        # Create the event
        event = OrderEvent.objects.create(
            order=order,
            event_type=event_type,
            user=request.user,
            document=document,
            amount=amount
        )

        # Log successful creation
        logger.info(f"Event created successfully: id={event.id}, order={order.order_number}, event_type={event.event_type}, amount={event.amount}")

        # Send notifications
        send_mail(
            subject=f'Evento en pedido {order.order_number}: {dict(EVENT_TYPE_CHOICES)[event_type]}',
            message=f'El pedido {order.order_number} ha sido {dict(EVENT_TYPE_CHOICES)[event_type].lower()} por {request.user.username}.',
            from_email='soporte@dirlux.com',
            recipient_list=[order.customer.email] if order.customer.email else []
        )
        self.send_whatsapp_notification(
            order,
            f"Evento en pedido {order.order_number}: {dict(EVENT_TYPE_CHOICES)[event_type]}. "
            f"Aprobar: http://localhost:3000/approve/{order.id}"
        )

        logger.info(f"Notifications sent for event {event.id} in order {order.order_number}")
        return Response({
            'message': 'Evento registrado correctamente',
            'event_id': event.id,
            'event_type': event_type,
            'order_number': order.order_number,
            'amount': str(event.amount)
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put'], url_path='events/(?P<event_id>[^/.]+)')
    def update_event(self, request, pk=None, event_id=None):
        try:
            order = self.get_object()
            event = OrderEvent.objects.get(id=event_id, order=order)
            serializer = OrderEventSerializer(event, data=request.data, partial=True)
            
            if serializer.is_valid():
                logger.info(f"Validation passed for event_type={request.data.get('event_type')}, amount={request.data.get('amount', 0.00)}")
                serializer.save()
                logger.info(f"OrderEvent updated: id={event.id}, order={order.order_number}, event_type={event.event_type}")
                return Response(serializer.data)
            else:
                logger.error(f"Serializer errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except OrderEvent.DoesNotExist:
            logger.error(f"OrderEvent {event_id} not found for order {pk}")
            return Response({"detail": "Evento no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_payment(self, request, pk=None):
        logger.debug(f"POST /api/orders/{pk}/add_payment/ - Raw request data: {request.data}, Files: { {k: v.name for k, v in request.FILES.items()} }")
        order = self.get_object()
        amount = request.data.get('amount')
        document = request.FILES.get('document')

        # Log received data
        logger.info(f"Received payment data: order_id={pk}, amount={amount}, document={document.name if document else None}")

        # Validate amount
        try:
            amount = Decimal(amount)
            if amount <= 0:
                logger.error(f"Invalid amount: {amount}. Amount must be greater than 0.")
                return Response({"error": "El monto debe ser mayor a 0"}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            logger.error(f"Invalid amount format: {amount}")
            return Response({"error": "Monto inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # Log before creating event
        logger.debug(f"Creating payment event for order {order.order_number} with amount={amount}")

        # Create the payment event
        event = OrderEvent.objects.create(
            order=order,
            event_type='payment',
            user=request.user,
            amount=amount,
            document=document
        )

        # Log successful creation
        logger.info(f"Payment event created: id={event.id}, order={order.order_number}, amount={event.amount}")

        # Refresh the order to ensure computed fields are updated
        order.refresh_from_db()

        # Send notifications
        send_mail(
            subject=f'Nuevo pago en pedido {order.order_number}',
            message=f'Se ha registrado un pago de {amount} para el pedido {order.order_number} por {request.user.username}.',
            from_email='soporte@dirlux.com',
            recipient_list=[order.customer.email] if order.customer.email else []
        )
        self.send_whatsapp_notification(
            order,
            f"Nuevo pago de {amount} registrado para el pedido {order.order_number}. "
            f"Aprobar: http://localhost:3000/approve/{order.id}"
        )

        logger.info(f"Notifications sent for payment event {event.id} in order {order.order_number}")
        return Response({
            "message": "Pago registrado",
            "paid_amount": str(order.paid_amount),
            "percentage": order.payment_percentage
        }, status=status.HTTP_201_CREATED)

class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer

    def create(self, request, *args, **kwargs):
        logger.debug(f"PromotionViewSet.create() - Raw request data: {json_safe_dump(request.data)}")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        logger.debug(f"PromotionViewSet.update() - Raw request data: {json_safe_dump(request.data)}")
        return super().update(request, *args, **kwargs)

class CustomerPointsViewSet(viewsets.ModelViewSet):
    queryset = CustomerPoints.objects.all()
    serializer_class = CustomerPointsSerializer
    permission_classes = [IsAdminOrSales]

class PointsConfigViewSet(viewsets.ModelViewSet):
    queryset = PointsConfig.objects.all()
    serializer_class = PointsConfigSerializer
    permission_classes = [IsAdminOrSales]  # Solo admin/ventas configuran

# === ACCIÓN PARA ESTABLECER POR DEFECTO (con ID - detail=True) ===
    @action(detail=True, methods=['post'], url_path='set_default')
    def set_default_with_id(self, request, pk=None):
        """
        Establece UNA config específica como predeterminada.
        URL: /api/points-config/{id}/set_default/
        """
        try:
            config = self.get_object()  # Obtiene por pk
            # Desactivar todas las demás
            PointsConfig.objects.filter(is_default=True).exclude(pk=pk).update(is_default=False)
            # Activar la seleccionada
            config.is_default = True
            config.save()
            
            serializer = self.get_serializer(config)
            logger.info(f"Config {config.name} (ID {pk}) establecida como predeterminada")
            return Response({
                'message': f'Configuración "{config.name}" ahora es la predeterminada',
                'data': serializer.data
            })
        except PointsConfig.DoesNotExist:
            return Response({'error': 'Configuración no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error set_default: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # === ACCIÓN PARA ESTABLECER POR DEFECTO (sin ID - detail=False) ===
    @action(detail=False, methods=['post'], url_path='set-default')
    def set_default(self, request):
        """
        Establece UNA config por ID en body como predeterminada.
        URL: /api/points-config/set-default/
        Body: { "id": 2 }
        """
        config_id = request.data.get('id')
        if not config_id:
            return Response({'error': 'ID requerido en el body'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            config = PointsConfig.objects.get(pk=config_id)
            # Desactivar todas las demás
            PointsConfig.objects.filter(is_default=True).exclude(pk=config_id).update(is_default=False)
            # Activar la seleccionada
            config.is_default = True
            config.save()
            
            serializer = PointsConfigSerializer(config)
            logger.info(f"Config {config.name} (ID {config_id}) establecida como predeterminada")
            return Response({
                'message': f'Configuración "{config.name}" ahora es la predeterminada',
                'data': serializer.data
            })
        except PointsConfig.DoesNotExist:
            return Response({'error': 'ID de configuración no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error set_default: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # NUEVA ACCIÓN: set_active (para activar/desactivar configs)
    @action(detail=True, methods=['post'], url_path='set_active')
    def set_active(self, request, pk=None):
        """
        Activa la configuración especificada y desactiva todas las demás.
        Si está activa, la desactiva.
        """
        try:
            config = self.get_object()  # Obtiene la config por pk
            current_active = config.is_active

            if current_active:
                # Desactivar solo esta
                config.is_active = False
                config.save()
                return Response({
                    'message': f'Configuración "{config.name}" desactivada correctamente.',
                    'is_active': False
                })
            else:
                # Desactivar todas las demás y activar esta
                PointsConfig.objects.filter(is_active=True).update(is_active=False)
                config.is_active = True
                config.save()
                return Response({
                    'message': f'Configuración "{config.name}" activada. Las demás se desactivaron.',
                    'is_active': True
                })
        except PointsConfig.DoesNotExist:
            return Response({'error': 'Configuración no encontrada'}, status=404)
        except Exception as e:
            logger.error(f"Error en set_active para config {pk}: {str(e)}")
            return Response({'error': 'Error interno al cambiar estado'}, status=500)

    # === ACCIÓN PARA OTORGAR PUNTOS MANUALES (bonus) ===
    @action(detail=False, methods=['post'], url_path='award-manual')
    def award_manual(self, request):
        """
        Otorga puntos manuales a un cliente.
        URL: /api/points-config/award-manual/
        Body: { "customer": "uuid", "points": 100, "reason": "Bono fidelidad" }
        """
        customer_id = request.data.get('customer')
        points = int(request.data.get('points', 0))
        reason = request.data.get('reason', 'Asignación manual')
        
        if points == 0:
            return Response({'error': 'Los puntos deben ser mayores a 0'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            customer = Customer.objects.get(id=customer_id)
            # Crear el registro de puntos
            point_entry = CustomerPoints.objects.create(
                customer=customer,
                points=points,
                reason=reason,
                config=None  # Manual, sin config
            )
            
            # Recalcular total de puntos del cliente (opcional)
            total_points = CustomerPoints.objects.filter(customer=customer).aggregate(Sum('points'))['points__sum'] or 0
            
            logger.info(f"{points} puntos asignados manualmente a {customer.name} (ID {customer_id})")
            return Response({
                'message': 'Puntos asignados correctamente',
                'entry_id': point_entry.id,
                'total_points': total_points,
                'customer_name': customer.name
            }, status=status.HTTP_201_CREATED)
        except Customer.DoesNotExist:
            return Response({'error': 'Cliente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error award_manual: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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
    def get(self, request, *args, **kwargs):
        logger.info("ProductionQueueDashboardAPIView llamado")
        # Use timezone-aware datetimes
        end_date = timezone.make_aware(timezone.datetime.combine(date.today(), timezone.datetime.min.time()))
        start_date = timezone.make_aware(timezone.datetime.combine(date.today().replace(year=date.today().year - 4), timezone.datetime.min.time()))
        
        # Optimización de consultas con select_related y prefetch_related
        orders = Order.objects.filter(
            order_date__gte=start_date,
            order_date__lte=end_date
        ).select_related('customer', 'created_by').prefetch_related('items', 'events', 'payments', 'productionqueue')
        
        production_queues = ProductionQueue.objects.filter(
            delivery_date__gte=start_date,
            delivery_date__lte=end_date
        ).select_related('order')
        
        # Time Metrics
        total_orders = orders.count()
        
        # Average Design Days
        design_days = orders.filter(events__event_type='design_approved').annotate(
            design_time=ExpressionWrapper(
                F('events__timestamp') - F('order_date'),
                output_field=None  # Let database handle as interval
            )
        ).aggregate(avg_design=Avg('design_time'))
        
        # Average Production Days
        production_days = orders.filter(
            events__event_type='delivered'
        ).annotate(
            design_approved_time=Subquery(
                OrderEvent.objects.filter(
                    order=OuterRef('pk'),
                    event_type='design_approved'
                ).values('timestamp')[:1]
            ),
            production_time=ExpressionWrapper(
                F('events__timestamp') - F('design_approved_time'),
                output_field=None
            )
        ).aggregate(avg_production=Avg('production_time'))
        
        # Average Delivery Time
        delivery_time = orders.filter(events__event_type='delivered').annotate(
            delivery_time=ExpressionWrapper(
                F('events__timestamp') - F('order_date'),
                output_field=None
            )
        ).aggregate(avg_delivery=Avg('delivery_time'))
        
        # On-Time Delivery Rate
        on_time_deliveries = orders.filter(
            events__event_type='delivered',
            events__timestamp__lte=F('delivery_date')
        ).count()
        on_time_delivery_rate = (on_time_deliveries / total_orders * 100) if total_orders > 0 else 0
        
        # Delayed Orders
        delayed_orders = orders.filter(
            events__event_type='delivered',
            events__timestamp__gt=F('delivery_date')
        )
        delayed_count = delayed_orders.count()
        delayed_avg = delayed_orders.annotate(
            delay=ExpressionWrapper(
                F('events__timestamp') - F('delivery_date'),
                output_field=None
            )
        ).aggregate(avg_delay=Avg('delay'))
        
        # Customer Insights
        customer_insights = Customer.objects.filter(
            orders__order_date__gte=start_date,
            orders__order_date__lte=end_date
        ).annotate(
            total_orders=Count('orders'),
            total_spent=Sum(ExpressionWrapper(
                F('orders__items__quantity') * F('orders__items__unit_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )),
            last_order_date=Max('orders__order_date'),
            points=Sum('orders__items__quantity')
        ).order_by('-total_spent')[:10]
        
        customer_insights_data = [
            {
                'customer_id': str(customer.id),
                'customer_name': customer.name,
                'total_orders': customer.total_orders,
                'total_spent': float(customer.total_spent or 0),
                'last_order_date': customer.last_order_date.isoformat() if customer.last_order_date else None,
                'points': customer.points or 0,
                'retention_rate': 100.0 if customer.orders.filter(order_date__gte=end_date - timedelta(days=365)).exists() else 0.0,
                'avg_order_value': float(customer.total_spent / customer.total_orders) if customer.total_orders > 0 else 0.0
            } for customer in customer_insights
        ]
        
        # Financial Metrics
        total_revenue = OrderItem.objects.filter(
            order__order_date__gte=start_date,
            order__order_date__lte=end_date
        ).annotate(
            item_revenue=ExpressionWrapper(
                F('quantity') * F('unit_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ).aggregate(total=Sum('item_revenue'))['total'] or 0.0
        
        total_payments = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0.0
        
        total_owed = float(total_revenue - total_payments)
        
        monthly_revenue_qs = OrderItem.objects.filter(
            order__order_date__gte=start_date,
            order__order_date__lte=end_date
        ).annotate(
            month=TruncMonth('order__order_date'),
            item_revenue=ExpressionWrapper(
                F('quantity') * F('unit_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ).values('month').annotate(
            quantity=Sum('quantity'),
            revenue=Sum('item_revenue')
        ).order_by('month')
        
        monthly_payments = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date
        ).annotate(
            month=TruncMonth('payment_date')
        ).values('month').annotate(
            payments=Sum('amount')
        ).order_by('month')
        
        monthly_dict = {item['month']: {'revenue': item['revenue'], 'quantity': item['quantity'], 'payments': 0} for item in monthly_revenue_qs}
        for payment in monthly_payments:
            if payment['month'] in monthly_dict:
                monthly_dict[payment['month']]['payments'] = payment['payments'] or 0
            else:
                monthly_dict[payment['month']] = {'revenue': 0, 'quantity': 0, 'payments': payment['payments'] or 0}
        
        monthly_revenue = [
            {
                'month': month.strftime('%Y-%m'),
                'revenue': float(data['revenue']),
                'payments': float(data['payments']),
                'owed': float(data['revenue'] - data['payments'])
            } for month, data in sorted(monthly_dict.items(), key=lambda x: x[0])
        ]
        
        # Sales Metrics
        orders_by_status = orders.values('status').annotate(count=Count('id'))
        orders_by_type = orders.values('order_type').annotate(count=Count('id'))
        
        monthly_orders = orders.annotate(
            month=TruncMonth('order_date')
        ).values('month', 'order_type').annotate(
            total=Count('id')
        ).order_by('month')
        
        monthly_orders_dict = {}
        for item in monthly_orders:
            month = item['month'].strftime('%Y-%m')
            if month not in monthly_orders_dict:
                monthly_orders_dict[month] = {'total': 0}
            monthly_orders_dict[month][item['order_type']] = item['total']
            monthly_orders_dict[month]['total'] += item['total']
        
        monthly_orders_data = [
            {
                'month': month,
                'total': data['total'],
                **{k: v for k, v in data.items() if k != 'total'}
            } for month, data in sorted(monthly_orders_dict.items())
        ]
        
        top_products = ProductType.objects.filter(
            orderitem__order__order_date__gte=start_date,
            orderitem__order__order_date__lte=end_date
        ).annotate(
            total_quantity=Sum('orderitem__quantity'),
            total_revenue=Sum(ExpressionWrapper(
                F('orderitem__quantity') * F('orderitem__unit_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ))
        ).order_by('-total_revenue')[:10]
        
        top_products_data = [
            {
                'product_type_id': product.id,
                'product_type_name': product.name,
                'total_quantity': product.total_quantity or 0,
                'total_revenue': float(product.total_revenue or 0),
                'avg_unit_price': float(product.total_revenue / product.total_quantity) if product.total_quantity > 0 else 0.0
            } for product in top_products
        ]
        
        product_performance = ProductType.objects.filter(
            orderitem__order__order_date__gte=start_date,
            orderitem__order__order_date__lte=end_date
        ).annotate(
            total_quantity=Sum('orderitem__quantity'),
            total_revenue=Sum(ExpressionWrapper(
                F('orderitem__quantity') * F('orderitem__unit_price'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ))
        ).annotate(
            demand_vs_capacity=ExpressionWrapper(
                F('total_quantity') / (F('daily_production_capacity') * Value(Decimal((end_date - start_date).days), output_field=DecimalField(max_digits=12, decimal_places=2))),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
        
        product_performance_data = [
            {
                'product_type_name': product.name,
                'demand_vs_capacity': float(product.demand_vs_capacity * 100) if product.demand_vs_capacity else 0.0,
                'monthly_sales': [
                    {
                        'month': item['month'].strftime('%Y-%m'),
                        'quantity': item['quantity'],
                        'revenue': float(item['revenue'])
                    } for item in OrderItem.objects.filter(
                        product_type=product,
                        order__order_date__gte=start_date,
                        order__order_date__lte=end_date
                    ).annotate(
                        month=TruncMonth('order__order_date'),
                        revenue=ExpressionWrapper(
                            F('quantity') * F('unit_price'),
                            output_field=DecimalField(max_digits=12, decimal_places=2)
                        )
                    ).values('month').annotate(
                        quantity=Sum('quantity'),
                        revenue=Sum('revenue')
                    ).order_by('month')
                ]
            } for product in product_performance
        ]
        
        # Production Metrics
        total_queues = production_queues.count()
        queues_by_type = production_queues.values('queue_type').annotate(count=Count('id'))
        
        capacity_utilization = 0
        if ProductType.objects.exists():
            total_capacity = ProductType.objects.aggregate(
                total=Sum(F('daily_production_capacity') * Value(Decimal((end_date - start_date).days), output_field=DecimalField(max_digits=12, decimal_places=2)))
            )['total'] or Decimal('1.0')
            total_produced = OrderItem.objects.filter(
                order__order_date__gte=start_date,
                order__order_date__lte=end_date,
                order__status='completed'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            capacity_utilization = float(total_produced / total_capacity * 100) if total_capacity > 0 else 0
        
        production_load = []
        for day in range(30):
            current_date = end_date - timedelta(days=day)
            daily_load = ProductionQueue.objects.filter(
                delivery_date=current_date
            ).aggregate(total=Sum('order__items__quantity'))['total'] or 0
            total_capacity = ProductType.objects.aggregate(total=Sum('daily_production_capacity'))['total'] or Decimal('1.0')
            load_percent = float(daily_load / total_capacity * 100) if total_capacity > 0 else 0
            production_load.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'load_percent': float(load_percent),
                'orders': ProductionQueue.objects.filter(delivery_date=current_date).count()
            })
        
        alerts = []
        for day in range(1, 31):
            future_date = end_date + timedelta(days=day)
            daily_load = ProductionQueue.objects.filter(
                delivery_date=future_date
            ).aggregate(total=Sum('order__items__quantity'))['total'] or 0
            total_capacity = ProductType.objects.aggregate(total=Sum('daily_production_capacity'))['total'] or Decimal('1.0')
            load_percent = float(daily_load / total_capacity * 100) if total_capacity > 0 else 0
            if load_percent > 90:
                alerts.append({
                    'date': future_date.strftime('%Y-%m-%d'),
                    'level': 'warning',
                    'message': f'Capacidad al {load_percent:.1f}% el {future_date.strftime("%Y-%m-%d")}'
                })
        
        # Delivery Metrics
        total_deliveries = orders.filter(events__event_type='delivered').count()
        overdue_orders = orders.filter(
            delivery_date__lt=end_date,
            status__in=['pending', 'in_progress']
        ).count()
        
        monthly_deliveries = orders.filter(
            events__event_type='delivered'
        ).annotate(
            month=TruncMonth('events__timestamp'),
            delivered_timestamp=Subquery(
                OrderEvent.objects.filter(
                    order=OuterRef('pk'),
                    event_type='delivered'
                ).values('timestamp')[:1]
            )
        ).values('month').annotate(
            total=Count('id'),
            on_time=Count('id', filter=Q(delivered_timestamp__lte=F('delivery_date'))),
            delayed=Count('id', filter=Q(delivered_timestamp__gt=F('delivery_date')))
        ).order_by('month')
        
        monthly_deliveries_data = [
            {
                'month': item['month'].strftime('%Y-%m'),
                'total': item['total'],
                'on_time': item['on_time'],
                'delayed': item['delayed']
            } for item in monthly_deliveries
        ]
        
        # Payment Details
        payment_details = [
            {
                'payment_id': payment.id,
                'order_number': payment.order.order_number,
                'amount': float(payment.amount),
                'payment_date': payment.payment_date.isoformat(),
                'payment_type': payment.payment_type,
                'reference_document': payment.reference_document.url if payment.reference_document else None
            } for payment in Payment.objects.filter(
                payment_date__gte=start_date,
                payment_date__lte=end_date
            ).select_related('order')
        ]
        
        # Annotate orders with total_amount and paid_amount using distinct names
        owed_orders = orders.annotate(
            annotated_total_amount=Subquery(
                OrderItem.objects.filter(
                    order=OuterRef('pk')
                ).annotate(
                    item_total=ExpressionWrapper(
                        F('quantity') * F('unit_price'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ).values('order').annotate(
                    total=Sum('item_total')
                ).values('total')[:1],
                output_field=DecimalField(max_digits=12, decimal_places=2, default=0)
            ),
            annotated_paid_amount=Subquery(
                Payment.objects.filter(
                    order=OuterRef('pk')
                ).values('order').annotate(
                    total=Sum('amount')
                ).values('total')[:1],
                output_field=DecimalField(max_digits=12, decimal_places=2, default=0)
            )
        ).filter(annotated_total_amount__gt=F('annotated_paid_amount'))
        
        owed_details = [
            {
                'owed_id': order.id,
                'order_number': order.order_number,
                'amount_owed': float(order.annotated_total_amount - order.annotated_paid_amount),
                'due_date': order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else None
            } for order in owed_orders
        ]
        
        payment_details.extend(owed_details)
        
        # Customer Metrics
        total_customers = Customer.objects.count()
        new_customers = Customer.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        active_customers = Customer.objects.filter(
            orders__order_date__gte=end_date - timedelta(days=365)
        ).distinct().count()
        churn_rate = float((total_customers - active_customers) / total_customers * 100) if total_customers > 0 else 0
        
        customer_acquisition = Customer.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            new=Count('id')
        ).order_by('month')
        
        customer_acquisition_data = [
            {'month': item['month'].strftime('%Y-%m'), 'new': item['new']}
            for item in customer_acquisition
        ]
        
        customer_segmentation = {
            'vip': Customer.objects.filter(
                orders__items__order__order_date__gte=start_date,
                orders__items__order__order_date__lte=end_date
            ).annotate(
                total_spent=Sum(ExpressionWrapper(
                    F('orders__items__quantity') * F('orders__items__unit_price'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ))
            ).filter(total_spent__gte=5000).count(),
            'regular': Customer.objects.filter(
                orders__items__order__order_date__gte=start_date,
                orders__items__order__order_date__lte=end_date
            ).annotate(
                total_spent=Sum(ExpressionWrapper(
                    F('orders__items__quantity') * F('orders__items__unit_price'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ))
            ).filter(total_spent__gte=1000, total_spent__lt=5000).count(),
            'low': Customer.objects.filter(
                orders__items__order__order_date__gte=start_date,
                orders__items__order__order_date__lte=end_date
            ).annotate(
                total_spent=Sum(ExpressionWrapper(
                    F('orders__items__quantity') * F('orders__items__unit_price'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ))
            ).filter(total_spent__lt=1000).count()
        }
        
        response_data = {
            'generated_at': timezone.now().isoformat(),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'time_metrics': {
                'avg_design_days': float(design_days['avg_design'].total_seconds() / 86400) if design_days['avg_design'] else 0.0,
                'avg_production_days': float(production_days['avg_production'].total_seconds() / 86400) if production_days['avg_production'] else 0.0,
                'total_orders_processed': total_orders,
                'avg_delivery_time_days': float(delivery_time['avg_delivery'].total_seconds() / 86400) if delivery_time['avg_delivery'] else 0.0,
                'on_time_delivery_rate': float(on_time_delivery_rate),
                'delayed_orders_count': delayed_count,
                'avg_delay_days': float(delayed_avg['avg_delay'].total_seconds() / 86400) if delayed_avg['avg_delay'] else 0.0
            },
            'customer_insights': customer_insights_data,
            'financial_metrics': {
                'total_revenue': float(total_revenue),
                'total_payments_received': float(total_payments),
                'total_owed': float(total_owed),
                'total_profit': 0.0,  # Placeholder
                'monthly_revenue': monthly_revenue,
                'cash_flow_summary': {
                    'positive_months': len([m for m in monthly_revenue if m['revenue'] > m['payments']]),
                    'negative_months': len([m for m in monthly_revenue if m['revenue'] < m['payments']]),
                    'avg_monthly_revenue': float(total_revenue / Decimal((end_date - start_date).days / 30)) if (end_date - start_date).days > 0 else 0.0
                }
            },
            'sales_metrics': {
                'total_orders': total_orders,
                'orders_by_status': {item['status']: item['count'] for item in orders_by_status},
                'orders_by_type': {item['order_type']: item['count'] for item in orders_by_type},
                'monthly_orders': monthly_orders_data,
                'top_products': top_products_data,
                'product_performance': product_performance_data
            },
            'production_metrics': {
                'total_production_queues': total_queues,
                'queues_by_type': {item['queue_type']: item['count'] for item in queues_by_type},
                'capacity_utilization': float(capacity_utilization),
                'production_load_by_day': production_load,
                'alerts': alerts,
                'production_efficiency': 94.5,  # Placeholder
                'bottlenecks': {
                    'design': float(design_days['avg_design'].total_seconds() / 86400) if design_days['avg_design'] else 0.0,
                    'production': float(production_days['avg_production'].total_seconds() / 86400) if production_days['avg_production'] else 0.0
                }
            },
            'delivery_metrics': {
                'total_deliveries': total_deliveries,
                'on_time_deliveries': on_time_deliveries,
                'delayed_deliveries': delayed_count,
                'overdue_orders': overdue_orders,
                'monthly_deliveries': monthly_deliveries_data
            },
            'payment_details': payment_details,
            'customer_metrics': {
                'total_customers': total_customers,
                'new_customers': new_customers,
                'active_customers': active_customers,
                'churn_rate': float(churn_rate),
                'customer_acquisition': customer_acquisition_data,
                'customer_segmentation': customer_segmentation
            },
            'overall_kpis': {
                'net_promoter_score': 85,  # Placeholder
                'customer_satisfaction': 4.5,  # Placeholder
                'employee_performance': {}  # Placeholder
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

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
        today = date.today()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        # === 1. ÓRDENES Y ESTADOS ===
        total_orders = Order.objects.count()
        active_orders = Order.objects.filter(status__in=['pending', 'in_progress', 'design_pending', 'design_confirmed']).count()
        completed_today = Order.objects.filter(status='completed', updated_at__date=today).count()
        overdue_orders = Order.objects.filter(
            delivery_date__lt=today,
            status__in=['in_progress', 'design_pending', 'design_confirmed']
        ).count()

        # === 2. FINANZAS ===
        total_revenue = Order.objects.filter(status='completed').aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        paid_amount = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        pending_amount = total_revenue - paid_amount
        collection_rate = round((paid_amount / total_revenue) * 100, 2) if total_revenue > 0 else 0

        # === 3. TIEMPOS CLAVE ===
        # Tiempo promedio de aprobación de diseño
        design_approved = Order.objects.filter(
            design_confirmation_date__isnull=False,
            order_date__isnull=False
        ).annotate(
            design_time=ExpressionWrapper(
                F('design_confirmation_date') - F('order_date'),
                output_field=DurationField()
            )
        ).aggregate(avg=Avg('design_time'))['avg']
        avg_design_days = round(design_approved.days + design_approved.seconds / 86400, 1) if design_approved else 0

        # Tiempo promedio de producción (desde diseño aprobado hasta entrega)
        delivered_orders = Order.objects.filter(
            status='completed',
            delivery_date__isnull=False,
            design_confirmation_date__isnull=False
        ).annotate(
            production_time=ExpressionWrapper(
                F('delivery_date') - F('design_confirmation_date'),
                output_field=DurationField()
            )
        ).aggregate(avg=Avg('production_time'))['avg']
        avg_production_days = round(delivered_orders.days + delivered_orders.seconds / 86400, 1) if delivered_orders else 0

        # === 4. PRODUCCIÓN HOY ===
        today_queue = ProductionQueue.objects.filter(delivery_date=today)
        today_load = today_queue.aggregate(total=Sum('order__items__quantity'))['total'] or 0
        daily_capacity = ProductType.objects.aggregate(cap=Sum('daily_production_capacity'))['cap'] or 1
        production_load_today = round((today_load / daily_capacity) * 100, 2)

        # === 5. PUNTOS Y CLIENTES TOP ===
        top_customers = Customer.objects.annotate(
            total_spent=Sum('orders__total_amount'),
            total_points=Sum('customerpoints__points')
        ).filter(total_spent__gt=0).order_by('-total_spent')[:5]

        customers_data = [
            {
                "name": c.name,
                "total_spent": float(c.total_spent or 0),
                "points": c.total_points or 0,
                "orders": c.orders.count()
            } for c in top_customers
        ]

        # === 6. PRODUCTOS MÁS VENDIDOS ===
        top_products = OrderItem.objects.values(
            'product__name', 'product_type__name'
        ).annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField()))
        ).order_by('-total_revenue')[:5]

        products_data = [
            {
                "name": item['product__name'] or item['product_type__name'],
                "quantity": item['total_qty'],
                "revenue": float(item['total_revenue'])
            } for item in top_products
        ]

        # === 7. ALERTAS ===
        alerts = []
        if overdue_orders > 0:
            alerts.append({"type": "warning", "message": f"{overdue_orders} pedidos atrasados"})
        if production_load_today > 90:
            alerts.append({"type": "danger", "message": f"Producción hoy al {production_load_today}% de capacidad"})

        # === 8. RESUMEN DE ÓRDENES POR TIPO ===
        order_types = dict(Order.objects.values('order_type').annotate(count=Count('id')))
        order_types_display = {
            k: f"{v} {dict(ORDER_TYPE_CHOICES).get(k, k).capitalize()}" 
            for k, v in order_types.items()
        }

        # === 9. DINERO PENDIENTE POR CLIENTE ===
        pending_by_customer = Customer.objects.annotate(
            total_owed=Sum('orders__total_amount') - Sum('orders__payments__amount')
        ).filter(total_owed__gt=0).order_by('-total_owed')[:5]

        pending_customers = [
            {
                "name": c.name,
                "owed": float(c.total_owed or 0)
            } for c in pending_by_customer
        ]

        # === RESPUESTA FINAL ===
        data = {
            "summary": {
                "total_orders": total_orders,
                "active_orders": active_orders,
                "completed_today": completed_today,
                "overdue_orders": overdue_orders,
                "total_revenue": float(total_revenue),
                "paid_amount": float(paid_amount),
                "pending_amount": float(pending_amount),
                "collection_rate": collection_rate,
            },
            "time_metrics": {
                "avg_design_days": avg_design_days,
                "avg_production_days": avg_production_days,
                "avg_delivery_days": avg_design_days + avg_production_days,
            },
            "production": {
                "today_load_percent": production_load_today,
                "daily_capacity": int(daily_capacity),
                "today_items": int(today_load),
            },
            "order_types": order_types_display,
            "top_customers": customers_data,
            "top_products": products_data,
            "pending_payments": pending_customers,
            "alerts": alerts,
            "generated_at": timezone.now().isoformat()
        }

        logger.info(f"Dashboard data generado exitosamente para {request.user}")
        return Response(data, status=status.HTTP_200_OK)

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
    
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = user.userprofile
        if profile.staff_status == 'administrator':
            return Payment.objects.all()
        elif profile.staff_status == 'sales':
            return Payment.objects.filter(order__customer__user=user)
        return Payment.objects.filter(order__created_by=user)
    def update(self, request, *args, **kwargs):
        logger.info(f"PUT /api/payments/{kwargs.get('pk')}/ - Raw request data: { {k: ['<binary>' if hasattr(v, 'read') else v for v in (request.data.getlist(k) if isinstance(request.data.get(k), list) else [request.data.get(k)])] for k in request.data} }")
        logger.info(f"Files: { {k: v.name for k, v in request.FILES.items()} }")
        
        try:
            payment = self.get_object()
            logger.debug(f"Updating payment ID {payment.id} for order {payment.order.order_number}")
            
            serializer = self.get_serializer(payment, data=request.data, partial=True)
            if serializer.is_valid():
                logger.info(f"Validation passed for payment ID {payment.id} with data: {json.dumps(serializer.validated_data, default=str)}")
                serializer.save()
                
                # Send notifications
                order = payment.order
                send_mail(
                    subject=f'Pago actualizado en pedido {order.order_number}',
                    message=f'El pago de {payment.amount} para el pedido {order.order_number} ha sido actualizado por {request.user.username}.',
                    from_email='soporte@dirlux.com',
                    recipient_list=[order.customer.email] if order.customer.email else []
                )
                self.send_whatsapp_notification(
                    order,
                    f"Pago de {payment.amount} actualizado para el pedido {order.order_number}. "
                    f"Aprobar: http://localhost:3000/approve/{order.id}"
                )
                logger.info(f"Payment ID {payment.id} updated successfully for order {order.order_number}")
                return Response({
                    "message": "Pago actualizado correctamente",
                    "paid_amount": str(order.paid_amount),
                    "percentage": order.payment_percentage
                })
            else:
                logger.error(f"Validation failed for payment ID {payment.id}: {serializer.errors}")
                return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Payment.DoesNotExist:
            logger.error(f"Payment ID {kwargs.get('pk')} not found")
            return Response({"error": "Pago no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating payment ID {kwargs.get('pk')}: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                logger.error(f"Error sending WhatsApp for order {order.order_number}: {e}")