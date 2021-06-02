# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Auftrag'
