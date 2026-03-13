
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lebaranrush.settings')
django.setup()

from games.undercover.models import UndercoverWord

word_pairs = [
    ("Apple", "Orange", "Fruit"),
    ("Laptop", "Tablet", "Tech"),
    ("Coffee", "Tea", "Drink"),
    ("Football", "Basketball", "Sport"),
    ("Bicycle", "Motorcycle", "Vehicle"),
    ("Cat", "Tiger", "Animal"),
    ("Moon", "Sun", "Space"),
    ("Piano", "Guitar", "Instrument"),
    ("Water", "Ice", "Nature"),
    ("Mountain", "Hill", "Geography"),
]

for common, undercover, category in word_pairs:
    UndercoverWord.objects.get_or_create(
        word_common=common,
        word_undercover=undercover,
        category=category,
        is_active=True
    )

print(f"Seeded {len(word_pairs)} Undercover word pairs.")
