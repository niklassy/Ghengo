# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class ToDo(models.Model):
    system = models.IntegerField()
    entries = models.IntegerField()
    from_other_system = models.BooleanField()


class Order(models.Model):
    name = models.CharField(max_length=255)
    to_dos = models.ManyToManyField(ToDo, related_name='orders')

    class Meta:
        verbose_name = 'Auftrag'
