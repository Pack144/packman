from django.conf import settings


def settings_context(_request):
    """Make project settings available to templates under the settings context"""
    return {"settings": settings}
