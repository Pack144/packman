from django import forms

from packman.membership.models import Scout

from .models import Customer, Order, OrderItem, PrizeSelection


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = (
            "name",
            "email",
            "phone_number",
            "address",
            "city",
            "state",
            "zipcode",
            "latitude",
            "longitude",
            "gps_accuracy",
        )
        widgets = {
            "name": forms.TextInput(attrs={"autocapitalize": "words"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "gps_accuracy": forms.HiddenInput(),
        }


class SimpleCustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("name", "phone_number", "email")


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("donation", "notes", "seller", "date_paid", "date_delivered")
        widgets = {
            "donation": forms.NumberInput(attrs={"min": 0, "step": 5}),
            "seller": forms.RadioSelect(),
            "date_paid": forms.HiddenInput(),
            "date_delivered": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        try:
            self.request = kwargs.pop("request")
            active_scouts = Order.seller.field.related_model.objects.active().filter(family=self.request.user.family)

            super().__init__(*args, **kwargs)

            self.fields["seller"].queryset = active_scouts
            if active_scouts.count() == 1:
                self.fields["seller"].widget = forms.HiddenInput()
                self.initial["seller"] = active_scouts.first()

        except KeyError:
            super().__init__(*args, **kwargs)


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ("product", "quantity")


OrderItemFormSet = forms.inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=0)


class PrizeSelectionForm(forms.ModelForm):
    class Meta:
        model = PrizeSelection
        fields = ("campaign", "cub", "prize", "quantity")


PrizeSelectionFormSet = forms.inlineformset_factory(Scout, PrizeSelection, form=PrizeSelectionForm, extra=0)
