import random

REWARDS_PLAYER = [
    {'id': 'small_snack', 'label': 'Small Snack', 'type': 'item', 'weight': 30},
    {'id': 'big_snack', 'label': 'Big Snack!', 'type': 'item', 'weight': 10},
    {'id': 'bonus_5', 'label': '5 Points', 'type': 'points', 'value': 5, 'weight': 20},
    {'id': 'bonus_10', 'label': '10 Points', 'type': 'points', 'value': 10, 'weight': 10},
    {'id': 'swap', 'label': 'Swap Reward', 'type': 'action', 'weight': 5},
    {'id': 'steal', 'label': 'Steal Reward', 'type': 'action', 'weight': 5},
    {'id': 'zonk', 'label': 'ZONK!', 'type': 'zonk', 'weight': 20},
]

REWARDS_GUEST = [
    {'id': 'small_snack', 'label': 'Small Snack', 'type': 'item', 'weight': 40},
    {'id': 'big_snack', 'label': 'Big Snack!', 'type': 'item', 'weight': 15},
    {'id': 'bonus_5', 'label': '5 Points', 'type': 'points', 'value': 5, 'weight': 15},
    {'id': 'zonk', 'label': 'ZONK!', 'type': 'zonk', 'weight': 30},
]

def get_random_reward(is_guest=False):
    rewards = REWARDS_GUEST if is_guest else REWARDS_PLAYER
    choices = []
    weights = []
    for r in rewards:
        choices.append(r)
        weights.append(r['weight'])
    
    return random.choices(choices, weights=weights, k=1)[0]
