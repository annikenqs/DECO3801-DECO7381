from django.db import models

# Create your models here.

class UserDetail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    decision = models.CharField(max_length=50)

class Decision(models.Model):
    number_of_users = models.IntegerField()
    description = models.TextField(max_length=500)

class Consequences(models.Model):
    decision_made = models.CharField(max_length=50)

class Timeline(models.Model):
    year = models.IntegerField()
    details = models.TextField(max_length=10000)

