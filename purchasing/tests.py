from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from django.utils import timezone

from inventory.models import Product, StockAdjustment
from people.models import Vendor
from .models import PurchaseBill, PurchaseReturn
from .serializers import PurchaseBillSerializer, PurchaseReturnSerializer


class PurchaseBillValidationTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(vendor_name="Vendor One", company_name="Vendor One")
        self.product = Product.objects.create(sku="SKU-001", name="Test Product")

    def test_serializer_requires_invoice_number_for_create(self):
        serializer = PurchaseBillSerializer(data={
            "vendor": self.vendor.id,
            "bill_date": "2026-04-08",
            "delivery_date": "2026-04-08",
            "sub_total": "100.00",
            "total_amount": "100.00",
            "due_date": timezone.now().isoformat(),
            "items_detail": [
                {
                    "product": self.product.id,
                    "quantity_ordered": 1,
                    "quantity_received": 1,
                    "unit_price": "100.00",
                }
            ],
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["invoice_number"][0], "This field is required.")

    def test_serializer_rejects_whitespace_invoice_number(self):
        serializer = PurchaseBillSerializer(data={
            "invoice_number": "   ",
            "vendor": self.vendor.id,
            "bill_date": "2026-04-08",
            "delivery_date": "2026-04-08",
            "sub_total": "100.00",
            "total_amount": "100.00",
            "due_date": timezone.now().isoformat(),
            "items_detail": [
                {
                    "product": self.product.id,
                    "quantity_ordered": 1,
                    "quantity_received": 1,
                    "unit_price": "100.00",
                }
            ],
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["invoice_number"][0], "This field may not be blank.")

    def test_model_save_rejects_blank_invoice_number(self):
        bill = PurchaseBill(
            bill_number="",
            invoice_number="   ",
            vendor=self.vendor,
            total_amount="100.00",
            due_date=timezone.now(),
        )

        with self.assertRaises(DjangoValidationError) as exc:
            bill.save()

        self.assertEqual(exc.exception.message_dict["invoice_number"][0], "Invoice number is required.")


class PurchaseReturnPayloadTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(vendor_name="Vendor Two", company_name="Vendor Two")
        self.product = Product.objects.create(sku="5082", name="JOHNNIE WALKER BLACK LABEL", stock=10)
        self.bill = PurchaseBill.objects.create(
            bill_number="8",
            invoice_number="INV-8",
            vendor=self.vendor,
            bill_date="2026-04-07",
            sub_total="174.54",
            total_amount="174.54",
            due_date=timezone.now(),
        )

    def test_purchase_return_serializer_accepts_payload_shape(self):
        serializer = PurchaseReturnSerializer(data={
            "vendor_id": str(self.vendor.id),
            "bill_id": str(self.bill.id),
            "return_bill_number": "8",
            "return_date": "2026-04-08",
            "bill_date": "2026-04-07",
            "due_date": "2026-05-08T00:00:00Z",
            "paid_status": "Paid",
            "note": "",
            "other_charges": 0,
            "total_returns": 6,
            "sub_total": 174.54,
            "total_payable": 174.54,
            "items": [
                {
                    "product_id": self.product.id,
                    "sku": "5082",
                    "description": "JOHNNIE WALKER BLACK LABEL",
                    "selected": False,
                    "quantity_received": 6,
                    "quantity_returned": 6,
                    "unit_price": 29.09,
                    "landing_cost": 29.09,
                    "amount": 174.54,
                }
            ],
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        purchase_return = serializer.save()
        response_data = PurchaseReturnSerializer(instance=purchase_return).data

        self.assertEqual(purchase_return.vendor_id, self.vendor.id)
        self.assertEqual(purchase_return.bill_id, self.bill.id)
        self.assertEqual(purchase_return.return_bill_number, "8")
        self.assertEqual(purchase_return.total_returns, 6)
        self.assertEqual(purchase_return.items.count(), 1)
        self.assertEqual(response_data["vendor_id"], self.vendor.id)
        self.assertEqual(len(response_data["items"]), 1)
        self.assertEqual(response_data["items"][0]["product_id"], self.product.id)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        adjustment = StockAdjustment.objects.get(product=self.product)
        self.assertEqual(adjustment.adjustment_type, "reduce")
        self.assertEqual(adjustment.quantity, 6)
        self.assertEqual(adjustment.reason, "Purchase Return 8")

    def test_purchase_return_model_auto_generates_return_bill_number(self):
        purchase_return = PurchaseReturn.objects.create(
            vendor=self.vendor,
            bill=self.bill,
            return_date="2026-04-08",
            total_returns=1,
            sub_total="29.09",
            total_payable="29.09",
        )

        self.assertEqual(purchase_return.return_bill_number, "1")

    def test_purchase_return_update_reconciles_stock_by_quantity_delta(self):
        serializer = PurchaseReturnSerializer(data={
            "vendor_id": str(self.vendor.id),
            "bill_id": str(self.bill.id),
            "return_bill_number": "9",
            "return_date": "2026-04-08",
            "paid_status": "Paid",
            "total_returns": 6,
            "sub_total": 174.54,
            "total_payable": 174.54,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity_received": 6,
                    "quantity_returned": 6,
                    "unit_price": 29.09,
                    "landing_cost": 29.09,
                    "amount": 174.54,
                }
            ],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        purchase_return = serializer.save()

        update_serializer = PurchaseReturnSerializer(
            purchase_return,
            data={
                "vendor_id": str(self.vendor.id),
                "bill_id": str(self.bill.id),
                "return_bill_number": "9",
                "return_date": "2026-04-08",
                "paid_status": "Paid",
                "total_returns": 4,
                "sub_total": 116.36,
                "total_payable": 116.36,
                "items": [
                    {
                        "product_id": self.product.id,
                        "quantity_received": 6,
                        "quantity_returned": 4,
                        "unit_price": 29.09,
                        "landing_cost": 29.09,
                        "amount": 116.36,
                    }
                ],
            },
        )

        self.assertTrue(update_serializer.is_valid(), update_serializer.errors)
        update_serializer.save()

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)
        self.assertEqual(StockAdjustment.objects.filter(product=self.product).count(), 2)
        latest_adjustment = StockAdjustment.objects.filter(product=self.product).order_by('-id').first()
        self.assertEqual(latest_adjustment.adjustment_type, "add")
        self.assertEqual(latest_adjustment.quantity, 2)

    def test_purchase_return_rejects_quantity_greater_than_available_stock(self):
        serializer = PurchaseReturnSerializer(data={
            "vendor_id": str(self.vendor.id),
            "bill_id": str(self.bill.id),
            "return_bill_number": "10",
            "return_date": "2026-04-08",
            "paid_status": "Paid",
            "total_returns": 11,
            "sub_total": 319.99,
            "total_payable": 319.99,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity_received": 11,
                    "quantity_returned": 11,
                    "unit_price": 29.09,
                    "landing_cost": 29.09,
                    "amount": 319.99,
                }
            ],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("items", serializer.errors)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_purchase_return_duplicate_return_bill_number_auto_generates_next_number(self):
        first_serializer = PurchaseReturnSerializer(data={
            "vendor_id": str(self.vendor.id),
            "bill_id": str(self.bill.id),
            "return_bill_number": "8",
            "return_date": "2026-04-08",
            "paid_status": "Paid",
            "total_returns": 2,
            "sub_total": 58.18,
            "total_payable": 58.18,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity_received": 2,
                    "quantity_returned": 2,
                    "unit_price": 29.09,
                    "landing_cost": 29.09,
                    "amount": 58.18,
                }
            ],
        })
        self.assertTrue(first_serializer.is_valid(), first_serializer.errors)
        first_purchase_return = first_serializer.save()

        second_serializer = PurchaseReturnSerializer(data={
            "vendor_id": str(self.vendor.id),
            "bill_id": str(self.bill.id),
            "return_bill_number": "8",
            "return_date": "2026-04-09",
            "paid_status": "Paid",
            "total_returns": 1,
            "sub_total": 29.09,
            "total_payable": 29.09,
            "items": [
                {
                    "product_id": self.product.id,
                    "quantity_received": 1,
                    "quantity_returned": 1,
                    "unit_price": 29.09,
                    "landing_cost": 29.09,
                    "amount": 29.09,
                }
            ],
        })
        self.assertTrue(second_serializer.is_valid(), second_serializer.errors)
        second_purchase_return = second_serializer.save()

        self.assertEqual(first_purchase_return.return_bill_number, "8")
        self.assertNotEqual(second_purchase_return.return_bill_number, "8")
        self.assertEqual(second_purchase_return.return_bill_number, "9")
