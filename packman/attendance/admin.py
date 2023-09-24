from django import forms
from django.contrib import admin

from ..calendars.models import Event
from .models import Attendance

# from django.utils.html import format_html, format_html_join
# from django.utils.translation import gettext_lazy as _


class AttendanceAdminForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = "__all__"


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    form = AttendanceAdminForm
    list_display = ["event", "start", "total", "adults", "cubs"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # limit choices on add screen to events not yet selected
        if db_field.name == "event" and str(request).find("/add/") > -1:
            kwargs["queryset"] = Event.objects.filter(attendance__event=None)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def start(self, obj):
        return (Event.objects.get(attendance=obj)).start

    def total(self, obj):
        return obj.members.count()

    def adults(self, obj):
        return obj.members.filter(scout=None).count()

    def cubs(self, obj):
        return obj.members.filter(adult=None).count()
