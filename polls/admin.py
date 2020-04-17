from django.contrib import admin

from .models import Choice, Question


class ChoiceInline(admin.TabularInline):
    model = Choice
    readonly_fields = ['count_votes', ]
    extra = 0


class QuestionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['question_text', 'description', 'is_anonymous']}),
        ('Date information', {'fields': ['poll_opens', 'poll_closes']}),
    ]
    inlines = [ChoiceInline]
    list_display = ('question_text', 'count_choices', 'count_total_votes', 'poll_opens', 'poll_closes', 'was_published_recently')
    list_filter = ['poll_opens', 'poll_closes']
    search_fields = ['question_text']


admin.site.register(Question, QuestionAdmin)
