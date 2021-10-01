from .models import Order, Family

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
    return {"items": items, "order": order, "seller": seller, "cart": cart }
