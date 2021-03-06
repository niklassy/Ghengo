# Generated by Django 3.2.5 on 2021-10-07 07:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('order', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='ToDo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('system', models.IntegerField()),
                ('part', models.FloatField()),
                ('entries', models.IntegerField()),
                ('from_other_system', models.BooleanField()),
                ('done', models.BooleanField(verbose_name='abgeschlossen')),
            ],
            options={
                'verbose_name_plural': 'Todos',
            },
        ),
        migrations.AddField(
            model_name='order',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='order',
            name='description',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='number',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='order',
            name='owner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='order',
            name='plays_soccer',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='proof',
            field=models.FileField(null=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='order',
            name='mission',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='commands', to='order.todo'),
        ),
        migrations.AddField(
            model_name='order',
            name='products',
            field=models.ManyToManyField(to='order.Product'),
        ),
        migrations.AddField(
            model_name='order',
            name='task',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order', to='order.todo'),
        ),
        migrations.AddField(
            model_name='order',
            name='to_dos',
            field=models.ManyToManyField(related_name='orders', to='order.ToDo'),
        ),
    ]
