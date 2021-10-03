# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models


class Order(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    number = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Auftrag'
