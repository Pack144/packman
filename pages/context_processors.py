from .models import Page


def populate_navbar(request):
    navbar = {'navbar_links': []}
    for page in Page.objects.filter(include_in_nav=True):
        if page.content_blocks.visible(user=request.user):
            navbar['navbar_links'].append(page)
    return navbar
