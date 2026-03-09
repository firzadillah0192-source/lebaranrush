import random

def generate_gacha_boxes(player_count):
    """
    Generate a list of boxes with hidden rewards.
    Each box is a dict: {'id': int, 'reward': dict, 'player_id': None}
    """
    # Define reward pool
    # 60% Points (5-20)
    # 30% Spins (1-3)
    # 10% Jackpot (50 points or 5 spins)
    
    box_count = max(player_count + 2, 8) # At least 8 boxes or players+2
    boxes = []
    
    for i in range(box_count):
        r = random.random()
        if r < 0.10:
            # Jackpot
            if random.random() < 0.5:
                reward = {'type': 'points', 'amount': 50, 'label': '💰 JACKPOT 50 PTS'}
            else:
                reward = {'type': 'spins', 'amount': 5, 'label': '🎡 JACKPOT 5 SPINS'}
        elif r < 0.40:
            # Spins
            amount = random.randint(1, 3)
            reward = {'type': 'spins', 'amount': amount, 'label': f'🎡 {amount} Spins'}
        else:
            # Points
            amount = random.choice([5, 10, 15, 20])
            reward = {'type': 'points', 'amount': amount, 'label': f'🪙 {amount} Points'}
            
        boxes.append({
            'id': i,
            'reward': reward,
            'player_id': None,
            'player_name': None,
            'revealed': False
        })
        
    random.shuffle(boxes)
    return boxes
