from django.db import models
from django.contrib.auth.models import AbstractUser
from stocks.models import Stock

# Create your models here.

class User(AbstractUser):
    """
    커스텀 유저 모델
    user_name, nick_name, favorite_stock 포함하고 있음. 
    """

    user_name= models.CharField(max_length=20, default="", blank=True, null=True,)
    nick_name= models.CharField(max_length=20, default="", blank=True, null=True,)
    favorite_stock=models.ManyToManyField(Stock, max_length=100, default="", blank=True,)

    def __str__(self):
        return self.username
