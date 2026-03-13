import sys
import os
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lebaranrush.settings')
django.setup()

from games.undercover.models import UndercoverWord

words = [
    ("Apple", "Orange"),
    ("Dog", "Wolf"),
    ("Tea", "Coffee"),
    ("Laptop", "Tablet"),
    ("Car", "Bus"),
    ("Doctor", "Nurse"),
    ("Pizza", "Burger"),
    ("Cat", "Tiger"),
    ("Football", "Basketball"),
    ("Rain", "Snow"),
]

for common, undercover in words:
    UndercoverWord.objects.get_or_create(
        word_common=common,
        word_undercover=undercover,
        defaults={'category': 'General'}
    )

print(f"Successfully seeded {len(words)} word pairs.")
