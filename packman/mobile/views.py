from django.views.generic import TemplateView

from packman.membership.mixins import ActiveMemberOrContributorTest


class AppShellView(ActiveMemberOrContributorTest, TemplateView):
    """Serves the Pack Directory PWA shell. Everything past this point is static JS."""

    template_name = "mobile/index.html"


class ServiceWorkerView(TemplateView):
    template_name = "mobile/sw.js"
    content_type = "application/javascript"

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        response["Cache-Control"] = "no-cache"
        return response


class WebManifestView(TemplateView):
    template_name = "mobile/manifest.webmanifest"
    content_type = "application/manifest+json"
