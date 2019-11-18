from django.utils import timezone
from django.views.generic import DetailView, TemplateView, UpdateView

from .models import StaticPage, DynamicPage


class AboutPageView(TemplateView):
    template_name = 'pages/about_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['page_content'] = StaticPage.objects.filter(page='ABOUT').filter(
                published_on__lte=timezone.now()).latest()
        except StaticPage.DoesNotExist:
            context['page_content'] = None
        return context


class HomePageView(TemplateView):
    template_name = 'pages/home_page.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        try:
            context['page_content'] = StaticPage.objects.filter(page='HOME').filter(
                published_on__lte=timezone.now()).latest()
        except StaticPage.DoesNotExist:
            context['page_content'] = None
        return context


class HistoryPageView(TemplateView):
    template_name = 'pages/history_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['page_content'] = StaticPage.objects.filter(page='HISTORY').filter(
                published_on__lte=timezone.now()).latest()
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
