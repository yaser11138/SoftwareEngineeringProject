# Generated by Django 4.2.7 on 2023-11-21 06:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notification", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="notification",
            old_name="content_id",
            new_name="object_id",
        ),
    ]
