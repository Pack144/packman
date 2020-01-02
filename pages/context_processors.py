from .models import DynamicPage


def navbar_items(request):
    pages = {'navbar_items': []}
    for page in DynamicPage.objects.filter(include_in_nav=True):
        pages['navbar_items'].append(page)
    return pages
