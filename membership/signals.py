from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, Member, Parent, Scout


@receiver(post_save, sender=Account)
def create_or_update_account_profile(sender, instance, created, **kwargs):
    if created:
        Parent.objects.create(account=instance)
    instance.profile.save()

@receiver(post_save, sender=Member)
def update_parent_status(sender, )