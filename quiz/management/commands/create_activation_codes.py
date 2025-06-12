import uuid
from django.core.management.base import BaseCommand, CommandError
from quiz.models import PackageActivationCode, Packages


class Command(BaseCommand):
    help = 'Create activation codes for given package IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            'count',
            type=int,
            help='Number of codes to create for each package and for all combined'
        )
        parser.add_argument(
            'pkg_ids',
            nargs='+',
            type=str,
            help='List of package UUIDs'
        )

    def handle(self, *args, **options):
        count = options['count']
        pkg_ids = options['pkg_ids']
        pkgs = []

        if count <= 0:
            raise CommandError("Count must be a positive integer.")

        # Validate and fetch packages
        for pkg_id in pkg_ids:
            try:
                pkg = Packages.objects.get(id=pkg_id)
                pkgs.append(pkg)
            except Packages.DoesNotExist:
                raise CommandError(f'❌ Package with ID {pkg_id} does not exist.')

        # Create <count> codes for the combination of all packages
        for _ in range(count):
            code = PackageActivationCode.objects.create()
            code.pkgs.set(pkgs)

        self.stdout.write(self.style.SUCCESS('✅ Successfully created activation codes.'))
