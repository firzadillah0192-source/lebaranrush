import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from rooms.models import Room

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically cleans up old and empty rooms'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Delete rooms older than this many hours',
        )
        parser.add_argument(
            '--empty-only',
            action='store_true',
            help='Only delete rooms with no players',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        threshold = timezone.now() - timedelta(hours=hours)

        # 1. Rooms older than threshold
        old_rooms = Room.objects.filter(created_at__lt=threshold)
        
        if options['empty_only']:
            old_rooms = old_rooms.filter(players__count=0)

        count, _ = old_rooms.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old rooms.'))
        
        # 2. Cleanup finished rooms older than 1 hour
        finished_threshold = timezone.now() - timedelta(hours=1)
        finished_rooms = Room.objects.filter(status='finished', created_at__lt=finished_threshold)
        f_count, _ = finished_rooms.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {f_count} finished rooms.'))
