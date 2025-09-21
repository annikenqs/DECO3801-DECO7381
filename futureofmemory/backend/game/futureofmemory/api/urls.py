from django.urls import path
from .views import ScenarioView, ChoicesView, OutcomeView

urlpatterns = [
    path("scenario/", ScenarioView.as_view(), name="scenario"),
    path("choices/", ChoicesView.as_view(), name="choices"),
    path("outcome/", OutcomeView.as_view(), name="outcome"),
    
]
