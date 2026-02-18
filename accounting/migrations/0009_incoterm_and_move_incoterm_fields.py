import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0008_asset_assetdepreciationline"),
    ]

    operations = [
        migrations.CreateModel(
            name="Incoterm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=16, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "ga_incoterm",
                "ordering": ("code",),
            },
        ),
        migrations.AddField(
            model_name="move",
            name="incoterm",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="moves",
                to="accounting.incoterm",
            ),
        ),
        migrations.AddField(
            model_name="move",
            name="incoterm_location",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
