# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models


class ToDo(models.Model):
    system = models.IntegerField()
    part = models.FloatField()
    entries = models.IntegerField()
    from_other_system = models.BooleanField()
    done = models.BooleanField(verbose_name='abgeschlossen')

    class Meta:
        verbose_name_plural = 'Todos'


class Product(models.Model):
    name = models.CharField(max_length=255)


class Item(models.Model):
    quantity = models.IntegerField(default=0)


class Order(models.Model):
    number = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, through=Item)

    # ====== above for evalutation in thesis, below for tests
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    plays_soccer = models.BooleanField(default=False)
    proof = models.FileField(null=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True)
    to_dos = models.ManyToManyField(ToDo, related_name='orders')
    mission = models.ForeignKey(ToDo, on_delete=models.CASCADE, related_name='commands', null=True)
    task = models.OneToOneField(ToDo, on_delete=models.CASCADE, related_name='order', null=True)

    class Meta:
        verbose_name = 'Auftrag'




