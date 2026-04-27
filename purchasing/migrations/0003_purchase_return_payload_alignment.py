import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchasing', '0002_purchasebill_invoice_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='purchasereturn',
            old_name='return_number',
            new_name='return_bill_number',
        ),
        migrations.RenameField(
            model_name='purchasereturn',
            old_name='reason',
            new_name='note',
        ),
        migrations.RenameField(
            model_name='purchasereturn',
            old_name='total_amount',
            new_name='total_payable',
        ),
        migrations.AlterField(
            model_name='purchasereturn',
            name='return_bill_number',
            field=models.CharField(blank=True, default='', max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='purchasereturn',
            name='note',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='purchasereturn',
            name='total_payable',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='bill',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='returns', to='purchasing.purchasebill'),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='bill_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='due_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='other_charges',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='paid_status',
            field=models.CharField(choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid'), ('Partial', 'Partial')], default='Unpaid', max_length=20),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='return_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='sub_total',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
        migrations.AddField(
            model_name='purchasereturn',
            name='total_returns',
            field=models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.RemoveField(
            model_name='purchasereturn',
            name='status',
        ),
        migrations.CreateModel(
            name='PurchaseReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sku', models.CharField(blank=True, default='', max_length=100)),
                ('description', models.TextField(blank=True, default='')),
                ('selected', models.BooleanField(default=True)),
                ('quantity_received', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('quantity_returned', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('unit_price', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('landing_cost', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.product')),
                ('purchase_return', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='purchasing.purchasereturn')),
            ],
        ),
    ]
