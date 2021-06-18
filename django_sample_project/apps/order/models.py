# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models


class ToDo(models.Model):
    system = models.IntegerField()
    entries = models.IntegerField()
    from_other_system = models.BooleanField()
    done = models.BooleanField(verbose_name='abgeschlossen')


class Order(models.Model):
    plays_soccer = models.BooleanField()
    name = models.CharField(max_length=255)
    to_dos = models.ManyToManyField(ToDo, related_name='orders')
    mission = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='commands')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.OneToOneField(ToDo, on_delete=models.CASCADE, related_name='order')

    class Meta:
        verbose_name = 'Auftrag'
