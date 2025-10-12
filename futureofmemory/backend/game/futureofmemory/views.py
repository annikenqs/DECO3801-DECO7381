from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = 'index-2075.html'


class LobbyView(TemplateView):
    template_name = 'lobby.html'


class Scenario1View(TemplateView):
    template_name = 'scenario1.html'


class GeneralScenarioView(TemplateView):
    template_name = 'GeneralScenario.html'
