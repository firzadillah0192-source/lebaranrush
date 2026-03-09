from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import GuestSpinToken
from django.utils import timezone
from .logic import get_random_reward

def guest_spin_page(request, token):
    guest_token = get_object_or_404(GuestSpinToken, token=token, is_used=False)
    return render(request, 'spinwheel/guest_spin.html', {'token': guest_token})

def process_guest_spin(request, token):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
        
    guest_token = get_object_or_404(GuestSpinToken, token=token, is_used=False)
    name = request.POST.get('name', 'Anonymous Guest')
    
    # Mark token as used
    guest_token.is_used = True
    guest_token.guest_name = name
    guest_token.used_at = timezone.now()
    guest_token.save()
    
    # Generate reward
    reward = get_random_reward(is_guest=True)
    
    # Broadcast to host via WebSocket if needed, or just return result
    # For now, we return it to the guest screen which should then notify the host via socket if they are connected
    # Actually, the host doesn't listen to guest's individual sockets unless they join the same room group
    
    return JsonResponse({
        'success': True,
        'reward': reward,
        'room_code': guest_token.room.code
    })
