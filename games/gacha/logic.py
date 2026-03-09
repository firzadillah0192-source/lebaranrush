import random

def generate_gacha_boxes_v2(box_count, zonk_count, special_items):
    """
    Generate boxes based on host configuration.
    """
    boxes = []
    
    # 1. Add Special Items
    for item in special_items:
        if len(boxes) >= box_count: break
        label_map = {
            'steal': '🕵️ STEAL POINTS',
            'shield': '🛡️ SHIELD (NO ZONK)',
            'swap': '🔄 SWAP POINTS',
            'double': '✖️ DOUBLE POINTS',
            'jackpot_spin': '🎢 10 SPINS JACKPOT'
        }
        boxes.append({
            'id': len(boxes),
            'reward': {'type': 'special', 'item': item, 'label': label_map.get(item, item.replace('_', ' ').upper())},
            'player_id': None, 'player_name': None, 'revealed': False
        })

    # 2. Add Zonks
    for _ in range(zonk_count):
        if len(boxes) >= box_count: break
        boxes.append({
            'id': len(boxes),
            'reward': {'type': 'zonk', 'amount': 0, 'label': '💥 ZONK! (0 PKT)'},
            'player_id': None, 'player_name': None, 'revealed': False
        })

    # 3. Fill the rest with Points and Spins
    while len(boxes) < box_count:
        if random.random() < 0.2:
            amount = random.randint(1, 3)
            reward = {'type': 'spins', 'amount': amount, 'label': f'🎡 {amount} Spins'}
        else:
            amount = random.choice([5, 10, 15, 20])
            reward = {'type': 'points', 'amount': amount, 'label': f'🪙 {amount} Points'}
            
        boxes.append({
            'id': len(boxes),
            'reward': reward,
            'player_id': None, 'player_name': None, 'revealed': False
        })
        
    random.shuffle(boxes)
    return boxes
