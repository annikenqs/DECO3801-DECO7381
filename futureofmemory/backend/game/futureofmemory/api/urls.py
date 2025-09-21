from django.urls import path
# from ..api import views
from .views import ScenarioView, ChoicesView, OutcomeView

urlpatterns = [
    path("scenario/", ScenarioView.as_view(), name="scenario"),
    path("choices/", ChoicesView.as_view(), name="choices"),
    path("outcome/", OutcomeView.as_view(), name="outcome"),
    
    # path('', views.index, name='index'),
    # path('api/ping/', views.ping, name='ping'),
    # path('api/select-faction/', views.select_faction),
    # path('api/questions/', views.questions_for_player),
    # path('api/answer/', views.submit_answer),
    # path('api/answers/', views.my_answers),
]
