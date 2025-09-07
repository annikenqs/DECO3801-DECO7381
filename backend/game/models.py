# Create your models here.
# game/models.py

from django.db import models
from django.contrib.auth.models import User

class Faction(models.IntegerChoices):
    RIGHT = 0, 'right'
    RESPONSIBILITY = 1, 'responsibility'
    RESOURCE = 2, 'resource'

class Player(models.Model):
    from django.contrib.auth.models import User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player')
    faction = models.SmallIntegerField(
        choices=Faction.choices,
        default=Faction.RIGHT,   
    )
    current_order = models.SmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

class Question(models.Model):
    faction = models.SmallIntegerField(choices=Faction.choices)
    order = models.PositiveSmallIntegerField()   # 1..10
    text = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)

    class Meta:
        unique_together = ('faction', 'order')
        ordering = ['faction', 'order']


class Answer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    choice = models.PositiveSmallIntegerField()  # 1~4
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('player', 'question')  