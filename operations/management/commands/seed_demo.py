from django.core.management.base import BaseCommand
from operations.models import Product, Order, ApprovalRequest
from decimal import Decimal

class Command(BaseCommand):
    help = "Create sample products and demo orders (safe to run more than once)"
    def handle(self, *args, **options):
        products = [
            ("Radiant Glow Serum","SKN-001","Skincare","A lightweight serum for a fresh, hydrated glow.",Decimal("799.00"),24,5,Decimal("4.8")),
            ("Velvet Matte Lipstick","LIP-002","Lipsticks","Comfortable matte color for everyday wear.",Decimal("499.00"),18,5,Decimal("4.6")),
            ("Cloud Nine Hair Mask","HAIR-003","Haircare","A nourishing weekly hair-care treatment.",Decimal("649.00"),3,5,Decimal("4.7")),
            ("Midnight Bloom Eau de Parfum","FRA-004","Fragrance","A warm floral fragrance for evening wear.",Decimal("1299.00"),12,4,Decimal("4.9")),
            ("Precision Eye Palette","EYE-005","Eye Makeup","Blendable neutral shades for day-to-night looks.",Decimal("899.00"),2,5,Decimal("4.5")),
            ("Soft Touch Nail Polish","NAIL-006","Nails","A glossy, quick-drying nail color.",Decimal("249.00"),40,8,Decimal("4.4")),
        ]
        for name,sku,cat,desc,price,stock,reorder,rating in products:
            Product.objects.update_or_create(sku=sku,defaults={"name":name,"category":cat,"description":desc,"price":price,"stock":stock,"reorder_level":reorder,"rating":rating,"active":True})
        self.stdout.write(self.style.SUCCESS("Demo catalog seeded. Run again safely whenever needed."))
