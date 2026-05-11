from django.core.management.base import BaseCommand
from chainsight.models import SavedPath
from chainsight.services.path_service import generate_summary_path


class Command(BaseCommand):
    help = 'Regenerate summary_path for all SavedPath (run after GDS rerun).'

    def handle(self, *args, **options):
        count = 0
        for path in SavedPath.objects.all():
            new_summary = generate_summary_path(path.path_nodes)
            if new_summary != path.summary_path:
                path.summary_path = new_summary
                path.save(update_fields=['summary_path', 'updated_at'])
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Regenerated {count} summary_paths.'))
