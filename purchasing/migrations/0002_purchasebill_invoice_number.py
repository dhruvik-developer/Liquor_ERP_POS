from django.db import migrations, models


def copy_bill_number_to_invoice_number(apps, schema_editor):
    PurchaseBill = apps.get_model('purchasing', 'PurchaseBill')
    for bill in PurchaseBill.objects.filter(invoice_number__isnull=True):
        bill.invoice_number = bill.bill_number
        bill.save(update_fields=['invoice_number'])


class Migration(migrations.Migration):

    dependencies = [
        ('purchasing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasebill',
            name='invoice_number',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RunPython(copy_bill_number_to_invoice_number, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='purchasebill',
            name='invoice_number',
            field=models.CharField(max_length=100),
        ),
    ]
