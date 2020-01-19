from django.utils import timezone
from django.views.generic import DetailView, TemplateView, UpdateView

from pack_calendar.models import Event

from .models import StaticPage, DynamicPage


class AboutPageView(TemplateView):
    template_name = 'pages/about_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            context['page_content'] = StaticPage.objects.get(page=StaticPage.ABOUT)
        except StaticPage.DoesNotExist:
            context['page_content'] = None

        return context


class HomePageView(TemplateView):
    template_name = 'pages/home_page.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        context['event_list'] = Event.objects.filter(start__lte=timezone.now() + timezone.timedelta(weeks=1))\
            .filter(start__gte=timezone.now() - timezone.timedelta(hours=8))\
            .order_by('start')
        try:
            context['page_content'] = StaticPage.objects.get(page=StaticPage.HOME)
        except StaticPage.DoesNotExist:
            context['page_content'] = None
        return context


class HistoryPageView(TemplateView):
    template_name = 'pages/history_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['page_content'] = StaticPage.objects.get(page=StaticPage.HISTORY)
        except StaticPage.DoesNotExist:
            context['page_content'] = None
        return context


class DynamicPageView(DetailView):
    model = DynamicPage
    context_object_name = 'page_content'


class DynamicPageUpdateView(UpdateView):
    model = DynamicPage
    context_object_name = 'page_content'
    fields = '__all__'
