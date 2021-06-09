# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Auftrag'


class ToDo(models.Model):
    system = models.CharField(max_length=255)
    from_other_system = models.BooleanField()
