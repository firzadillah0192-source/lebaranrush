from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from core.models import ChatbotSetting, HelpContact, HelpOption, SiteVisit
from rooms.models import Room


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_dashboard(request):
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        room = get_object_or_404(Room, id=room_id)
        room.delete()
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

    context = {
        'total_rooms': Room.objects.count(),
        'active_rooms': Room.objects.filter(status='playing').count(),
        'waiting_rooms': Room.objects.filter(status='waiting').count(),
        'total_hits': total_hits,
        'hits_today': hits_today,
        'unique_visitors_24h': unique_visitors_24h,
        'unique_ips_7d': unique_ips_7d,
        'rooms': rooms,
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
