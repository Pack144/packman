from django import forms

from .models import Customer, Order, OrderItem


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("name", "address", "city", "state", "zipcode", "phone_number", "email")


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("seller", "donation", "notes", "date_paid", "date_delivered")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["seller"].queryset = Order.seller.field.related_model.objects.active().filter(
            family=self.request.user.family,
        )


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ("product", "quantity")


OrderItemFormSet = forms.inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=0, min_num=1)
