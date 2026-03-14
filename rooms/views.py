import qrcode
import base64
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Room
from players.models import Player

def index(request):
    return render(request, 'rooms/index.html')

def join_index(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').upper().strip()
        if room_code:
            return redirect('join_room', room_code=room_code)
    return render(request, 'rooms/join_index.html')

def create_room(request):
    if not request.session.session_key:
        request.session.create()
    
    # Create the room
    room = Room.objects.create(host_session=request.session.session_key)
    return redirect('host_dashboard', room_code=room.code)

def host_dashboard(request, room_code):
    room = get_object_or_404(Room, code=room_code)
    
    # Generate QR Code
    join_url = request.build_absolute_uri(reverse('join_room', args=[room.code]))
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(join_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    context = {
        'room': room,
        'qr_code': f"data:image/png;base64,{qr_base64}",
        'join_url': join_url,
    }
    return render(request, 'rooms/host_dashboard.html', context)

def join_room(request, room_code):
    room = get_object_or_404(Room, code=room_code)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            if not request.session.session_key:
                request.session.create()
            
            session_id = request.session.session_key
            # Check if player already exists in this room with this session
            player, created = Player.objects.get_or_create(
                room=room,
                session_id=session_id,
                defaults={'name': name}
            )
            return redirect('player_lobby', room_code=room.code)
            
    return render(request, 'rooms/join.html', {'room': room})

def player_lobby(request, room_code):
    room = get_object_or_404(Room, code=room_code)
    if not request.session.session_key:
        return redirect('join_room', room_code=room.code)
        
    session_id = request.session.session_key
    try:
        player = Player.objects.get(room=room, session_id=session_id)
    except Player.DoesNotExist:
        return redirect('join_room', room_code=room.code)
        
    return render(request, 'rooms/player_lobby.html', {'room': room, 'player': player})
