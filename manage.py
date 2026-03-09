#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lebaranrush.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    if 'runserver' in sys.argv:
        from get_ip import get_local_ip
        local_ip = get_local_ip()
        print("\n" + "="*50)
        print("  🌙 LEBARAN RUSH SERVER STARTED")
        print("="*50)
        print(f"  Host Dashboard: http://localhost:8000/host")
        print(f"  Players Join:   http://{local_ip}:8000")
        print("="*50)
        print("  Note: All players must be on the same Wi-Fi!\n")

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
