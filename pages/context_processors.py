from django.db.models import Q

from .models import DynamicPage, Content


def navbar_items(request):
    pages = {'navbar_public_navs': [], 'navbar_private_navs': []}
    for page in DynamicPage.objects.filter(include_in_nav=True):
        if page.content_set.filter(Q(visibility=Content.PUBLIC) | Q(visibility=Content.ANONYMOUS)):
            page['navbar_public_navs'].append(page)
        else:
            pages['navbar_private_navs'].append(page)

    return pages
