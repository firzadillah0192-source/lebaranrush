import threading
import time
from .transitions import transition_to

def start_timer(room_code, seconds, next_state, state_data=None):
    """
    Start a background timer that transitions to a new state upon expiration.
    """
    def timer_callback():
        time.sleep(seconds)
        transition_to(room_code, next_state, state_data=state_data)
        
    thread = threading.Thread(target=timer_callback, daemon=True)
    thread.start()
    return thread
