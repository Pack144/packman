from .models import Page


def populate_navbar(request):
    navbar = {'navbar_links': []}
    for page in Page.objects.get_visible_content(user=request.user).filter(include_in_nav=True):
        if page.content_blocks.count():
            navbar['navbar_links'].append(page)
    return navbar
