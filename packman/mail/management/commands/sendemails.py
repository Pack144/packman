from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from packman.mail.models import Message


class Command(BaseCommand):
    help = _("Sends all Messages with a status of 'QUEUED'")

    def handle(self, *args, **options):
        messages = Message.objects.filter(status=Message.Status.QUEUED)
        success_count = 0
        for message in messages:
            message.status = Message.Status.SENDING
            message.save(update_fields=("status",))
            try:
                message.send()
                success_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(_("An unexpected error occurred: %s") % e))

        self.stdout.write(self.style.SUCCESS(_("Successfully sent %d email messages") % success_count))
