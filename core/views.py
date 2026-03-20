from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from core.models import ChatbotSetting, HelpContact, HelpOption, SiteVisit, SupportTicket, SupportMessage
from players.models import Player
from rooms.models import Room


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_room':
            room_id = request.POST.get('room_id')
            room = get_object_or_404(Room, id=room_id)
            room.delete()
        elif action == 'cleanup_rooms':
            # Cleanup: older than 24h OR finished older than 1h
            threshold_24h = timezone.now() - timedelta(hours=24)
            threshold_1h = timezone.now() - timedelta(hours=1)
            Room.objects.filter(created_at__lt=threshold_24h).delete()
            Room.objects.filter(status='finished', created_at__lt=threshold_1h).delete()
        
        # Help Management
        elif action == 'save_chatbot_setting':
            setting_id = request.POST.get('id')
            greeting = request.POST.get('greeting')
            bubble_label = request.POST.get('bubble_label')
            is_active = request.POST.get('is_active') == 'on'
            
            if setting_id:
                ChatbotSetting.objects.filter(id=setting_id).update(
                    greeting=greeting, bubble_label=bubble_label, is_active=is_active
                )
            else:
                ChatbotSetting.objects.create(
                    greeting=greeting, bubble_label=bubble_label, is_active=is_active
                )
                
        elif action == 'delete_help_option':
            opt_id = request.POST.get('id')
            HelpOption.objects.filter(id=opt_id).delete()
            
        elif action == 'save_help_option':
            opt_id = request.POST.get('id')
            title = request.POST.get('title')
            answer = request.POST.get('answer')
            sort_order = request.POST.get('sort_order', 0)
            
            if opt_id:
                HelpOption.objects.filter(id=opt_id).update(
                    title=title, answer=answer, sort_order=sort_order
                )
            else:
                HelpOption.objects.create(title=title, answer=answer, sort_order=sort_order)
                
        elif action == 'delete_help_contact':
            contact_id = request.POST.get('id')
            HelpContact.objects.filter(id=contact_id).delete()
            
        elif action == 'save_help_contact':
            contact_id = request.POST.get('id')
            name = request.POST.get('name')
            c_type = request.POST.get('type')
            value = request.POST.get('value')
            
            if contact_id:
                HelpContact.objects.filter(id=contact_id).update(
                    name=name, contact_type=c_type, contact_value=value
                )
            else:
                HelpContact.objects.create(name=name, contact_type=c_type, contact_value=value)
        
        elif action == 'reply_ticket_admin':
            ticket_id = request.POST.get('ticket_id')
            message = request.POST.get('message')
            status = request.POST.get('status')
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            if message:
                SupportMessage.objects.create(ticket=ticket, sender_type='admin', message=message)
            if status:
                ticket.status = status
                ticket.save()

        return redirect('admin_dashboard')

    now = timezone.now()
    today = now.date()
    start_of_today = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    week_ago = now - timedelta(days=7)

    total_hits = SiteVisit.objects.count()
    hits_today = SiteVisit.objects.filter(visited_at__gte=start_of_today).count()
    unique_visitors_24h = SiteVisit.objects.filter(visited_at__gte=now - timedelta(hours=24)).values('session_key').distinct().count()
    unique_ips_7d = SiteVisit.objects.filter(visited_at__gte=week_ago).exclude(ip_address__isnull=True).values('ip_address').distinct().count()

    rooms = Room.objects.annotate(
        player_count=Count('players', distinct=True),
        active_session_count=Count('sessions', distinct=True),
    ).order_by('-created_at')[:50]

    players = Player.objects.select_related('room').order_by('-id')[:20]
    
    # Tickets for admin
    tickets = SupportTicket.objects.all().prefetch_related('messages')

    context = {
        'total_rooms': Room.objects.count(),
        'active_rooms': Room.objects.filter(status='playing').count(),
        'waiting_rooms': Room.objects.filter(status='waiting').count(),
        'total_players': Player.objects.count(),
        'total_hits': total_hits,
        'hits_today': hits_today,
        'unique_visitors_24h': unique_visitors_24h,
        'unique_ips_7d': unique_ips_7d,
        'rooms': rooms,
        'latest_players': players,
        # Help data for custom UI
        'chatbot_setting': ChatbotSetting.objects.first(),
        'help_options': HelpOption.objects.all(),
        'help_contacts': HelpContact.objects.all(),
        'tickets': tickets,
    }
    return render(request, 'core/admin_dashboard.html', context)


@require_GET
def helpbot_data(request):
    setting = ChatbotSetting.objects.filter(is_active=True).order_by('-updated_at').first()
    options = HelpOption.objects.filter(is_active=True).order_by('sort_order', 'title')
    contacts = HelpContact.objects.filter(is_active=True).order_by('name')

    payload = {
        'bubble_label': setting.bubble_label if setting else 'Butuh bantuan?',
        'greeting': setting.greeting if setting else 'Halo! Ada yang bisa kami bantu?',
        'options': [
            {'id': option.id, 'title': option.title, 'answer': option.answer}
            for option in options
        ],
        'contacts': [
            {
                'name': contact.name,
                'type': contact.contact_type,
                'value': contact.contact_value,
            }
            for contact in contacts
        ],
    }
    return JsonResponse(payload)


@require_http_methods(["POST"])
def create_ticket(request):
    if not request.session.session_key:
        request.session.create()
    
    phone = request.POST.get('phone')
    description = request.POST.get('description')
    attachment = request.FILES.get('attachment')
    
    ticket = SupportTicket.objects.create(
        session_key=request.session.session_key,
        phone=phone,
        description=description
    )
    
    # Initial message
    SupportMessage.objects.create(
        ticket=ticket,
        sender_type='user',
        message=description,
        attachment=attachment
    )
    
    return JsonResponse({'status': 'ok', 'ticket_id': ticket.id})


@require_GET
def my_tickets(request):
    if not request.session.session_key:
        return JsonResponse({'tickets': []})
    
    tickets = SupportTicket.objects.filter(session_key=request.session.session_key).order_by('-created_at')
    data = []
    for t in tickets:
        data.append({
            'id': t.id,
            'status': t.status,
            'created_at': t.created_at.isoformat(),
            'last_message': t.messages.last().message if t.messages.exists() else ''
        })
    return JsonResponse({'tickets': data})


@require_GET
def ticket_messages(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    # Security: check session key
    if ticket.session_key != request.session.session_key and not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    messages = ticket.messages.all()
    data = []
    for m in messages:
        data.append({
            'sender': m.sender_type,
            'message': m.message,
            'created_at': m.created_at.isoformat(),
            'attachment': m.attachment.url if m.attachment else None
        })
    return JsonResponse({'status': ticket.status, 'messages': data})


@require_http_methods(["POST"])
def reply_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    if ticket.session_key != request.session.session_key and not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    message = request.POST.get('message')
    attachment = request.FILES.get('attachment')
    
    if message or attachment:
        SupportMessage.objects.create(
            ticket=ticket,
            sender_type='admin' if request.user.is_staff else 'user',
            message=message,
            attachment=attachment
        )
        ticket.updated_at = timezone.now()
        ticket.save()
        
    return JsonResponse({'status': 'ok'})
