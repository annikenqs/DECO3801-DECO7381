# Create your models here.
# game/models.py

from django.db import models
from django.contrib.auth.models import User

# determines play mode
class PlayMode(models.Model):
    singleplayer = models.CharField(max_length=10)
    multiplayer = models.CharField(max_length=10)

# determines what faction the user can choose
class Faction(models.IntegerChoices):
    RIGHT = 0, 'right'
    RESPONSIBILITY = 1, 'responsibility'
    RESOURCE = 2, 'resource'

# determines the stats of the player
class Player(models.Model):
    from django.contrib.auth.models import User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player')
    faction = models.SmallIntegerField( # each faction has the choice they made (represented through an integer) and a default choice
        choices=Faction.choices,
        default=Faction.RIGHT,   
    )
    current_order = models.SmallIntegerField(default=0) 
    updated_at = models.DateTimeField(auto_now=True)

# what stuff goes into a question
class Question(models.Model):
    faction = models.SmallIntegerField(choices=Faction.choices) # what faction the player's in
    order = models.PositiveSmallIntegerField()   # 1..10
    text = models.TextField() # the requisite text content within the question itself
    option1 = models.CharField(max_length=255) # the options - a - c (or 1 to 3)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)

    class Meta:
        unique_together = ('faction', 'order')
        ordering = ['faction', 'order']

# what stuff goes into the answer
class Answer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='answers') # the player that made the answer
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers') # what question the answer was from
    choice = models.PositiveSmallIntegerField()  # 1~3
    answered_at = models.DateTimeField(auto_now_add=True) # when it was answered

    class Meta:
        unique_together = ('player', 'question')  

# start page: 'Singleplayer', 'Multiplayer', 'Settings'
# 'Singleplayer' => starting scenario (picking btwn rights etc) => scenario 1
# 'Multiplayer' => "Share this pin!" (for the host), generates new pin => stored in Firebase, "Enter the game pin!" (for other players)
# entering pin => click 'join game' => enter lobby
# game starts when host clicks 'start game'
# creating user sends this pin to their friends (somehow)
# 