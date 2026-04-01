from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0003_adpayment_bookmark_fakenewsreport'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReadingHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(auto_now=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='news.article')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reading_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-read_at'],
                'unique_together': {('user', 'article')},
            },
        ),
    ]
