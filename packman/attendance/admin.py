from django import forms
from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from .models import Attendance
from ..calendars.models import Event

# admin.site.register(Attendance)

class AttendanceAdminForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = "__all__"

    # event = forms.ModelMultipleChoiceField(queryset=None)

    # def __init__(self, *args, **kwargs):
    #     super(AttendanceAdminForm, self).__init__(*args, **kwargs)
    #     if self.data is None:
    #         self.fields['event'].queryset = Attendance.objects.exclude(event__in=Event.objects.all())

    # def clean_first_name(self):
    #     if self.cleaned_data["first_name"] == "Spike":
    #         raise forms.ValidationError("No Vampires")

    #     return self.cleaned_data["first_name"]
    # def get_form(self, request, obj=None, **kwargs):
    #     super().get_form(request, obj, **defaults)
    #     if obj is None:
    #         self.fields['event'].queryset = Attendance.objects.exclude(event__in=Event.objects.all())
         

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    form = AttendanceAdminForm
    # search_fields = ["event__name"]
    list_display = ["event","start","total"]
    
    def start(self, obj):
        return (Event.objects.get(attendance=obj)).start
    
    def total(self, obj):
        return obj.member.count()

    # def add_view(self, request, extra_content=None):
        # self.exclude = ('', 'mname')
        # print(self)
        # limit_choices_to = At/tendance.objects.exclude(event__in=Event.objects.all())
        # request['event'].queryset = Attendance.objects.exclude(event__in=Event.objects.all())
        # return super(AttendanceAdmin, self).add_view(request)
