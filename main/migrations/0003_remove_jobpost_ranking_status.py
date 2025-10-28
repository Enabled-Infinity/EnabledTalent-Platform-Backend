# Generated manually to remove ranking_status field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_jobpost_ranking_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jobpost',
            name='ranking_status',
        ),
    ]
