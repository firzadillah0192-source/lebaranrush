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
def process_manual_boxes(manual_config):
    """
    Convert a list of types from the host into full box objects.
    manual_config: List of dicts e.g. [{"type": "snack"}, {"type": "zonk"}, {"type": "custom", "reward": "Car"}]
    """
    boxes = []
    label_map = {
        'snack': '🍿 SNACK REWARD',
        'zonk': '💥 ZONK! (ELIMINATED)',
        'steal': '🕵️ STEAL POINTS',
        'shield': '🛡️ SHIELD (SAFE)',
        'swap': '🔄 SWAP POINTS',
        'double': '✖️ DOUBLE POINTS',
        'jackpot': '🎡 JACKPOT SPINS',
        'custom': '🎁'
    }

    for i, item in enumerate(manual_config):
        itype = item.get('type')
        reward = {}
        
        if itype == 'custom':
            # Support "prize" type as per user request if necessary, but keep structure
            name = item.get('reward', 'SPECIAL PRIZE')
            reward = {'type': 'prize', 'name': name, 'label': f"🎁 {name}"}
        elif itype == 'snack':
            name = item.get('reward', '').strip()
            label = f"🍿 {name}" if name else label_map['snack']
            reward = {'type': 'snack', 'amount': 1, 'label': label, 'name': name}
        elif itype == 'zonk':
            reward = {'type': 'zonk', 'amount': 0, 'label': label_map['zonk']}
        elif itype == 'jackpot':
            reward = {'type': 'special', 'item': 'jackpot_spin', 'label': label_map['jackpot']}
        else:
            # Direct mapping for steal, swap, double, shield
            reward = {'type': 'special', 'item': itype, 'label': label_map.get(itype, itype.upper())}

        boxes.append({
            'id': i,
            'reward': reward,
            'player_id': None,
            'player_name': None,
            'revealed': False
        })
    
    return boxes
