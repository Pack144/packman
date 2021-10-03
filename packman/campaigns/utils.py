from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import Order


def get_cart_from_user(request, seller):
    order, created = Order.objects.get_or_create(
        seller=request.user.family
    )
    items = order.products.all()
    seller = order.seller
    cart = order.product_count
    return items, order, seller, cart


def build_cart(request):
    items, order, seller, cart = get_cart_from_user(request)
    return {"items": items, "order": order, "seller": seller, "cart": cart}


def email_receipt(order):
    site = Site.objects.get_current()

    context = {"site": site, "order": order}
    subject = render_to_string("campaigns/email/subject.txt", context).strip()
    plaintext = render_to_string("campaigns/email/message_body.txt", context)
    richtext = render_to_string("campaigns/email/message_body.html", context)

    msg = EmailMultiAlternatives(
        subject,
        plaintext,
        to=[order.customer.email],
        alternatives=[(richtext, "text/html")],
    )
    print("sending email")
    msg.send()
