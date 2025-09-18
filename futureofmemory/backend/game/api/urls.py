from django.urls import path
from .api import views

urlpatterns = [
    # path('', views.index, name='index'),
    # path('api/ping/', views.ping, name='ping'),

    path('api/select-faction/', views.select_faction),
    path('api/questions/', views.questions_for_player),
    path('api/answer/', views.submit_answer),
    path('api/answers/', views.my_answers),
]
