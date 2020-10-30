from .models import DynamicPage


def populate_navbar(request):
    navbar = {'navbar_links': []}
    for page in DynamicPage.objects.filter(include_in_nav=True):
        if page.content_blocks.visible(user=request.user):
            navbar['navbar_links'].append(page)
    return navbar
