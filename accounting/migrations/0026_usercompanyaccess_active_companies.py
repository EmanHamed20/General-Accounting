from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0025_merge_0024_merge_20260223_0834_0024_usercompanyaccess"),
    ]

    operations = [
        migrations.AddField(
            model_name="usercompanyaccess",
            name="active_companies",
            field=models.ManyToManyField(blank=True, related_name="active_for_users", to="accounting.company"),
        ),
    ]
