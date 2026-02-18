from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0009_incoterm_and_move_incoterm_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="customer_rank",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="partner",
            name="supplier_rank",
            field=models.IntegerField(default=0),
        ),
    ]
