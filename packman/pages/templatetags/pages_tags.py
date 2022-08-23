from django import template

register = template.Library()


@register.simple_tag
def get_elided_page_range(page_obj, on_each_side=3, on_ends=2):
    """
    Return a 1-based range of pages with some values elided.

    If the page range is larger than a given size, the whole range is not
    provided and a compact form is returned instead, e.g. for a paginator
    with 50 pages, if page 43 were the current page, the output, with the
    default arguments, would be:

        1, 2, …, 40, 41, 42, 43, 44, 45, 46, …, 49, 50.

    https://docs.djangoproject.com/en/3.2/ref/paginator/#django.core.paginator.Paginator.get_elided_page_range
    """
    paginator = page_obj.paginator
    number = page_obj.number
    return paginator.get_elided_page_range(number=number, on_each_side=on_each_side, on_ends=on_ends)


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Returns the URL-encoded querystring for the current page,
    updating the params with the key/value pairs passed to the tag.

    E.g: given the querystring ?foo=1&bar=2
    {% query_transform bar=3 %} outputs ?foo=1&bar=3
    {% query_transform foo='baz' %} outputs ?foo=baz&bar=2
    {% query_transform foo='one' bar='two' baz=99 %} outputs ?foo=one&bar=two&baz=99

    A RequestContext is required for access to the current querystring.
    """
    query = context["request"].GET.copy()
    for k, v in kwargs.items():
        if v:
            query[k] = v
    return query.urlencode()
