from django.db import migrations


SAMPLE_PRODUCTS = [
    {
        "name": "Wireless Headphones",
        "description": "Black over-ear headphones with padded ear cups for everyday listening.",
        "price": "1499.00",
        "image_path": "store/images/wireless-headphones.jpg",
        "is_available": True,
    },
    {
        "name": "Classic Smartwatch",
        "description": "A classic round smartwatch with a clean white band.",
        "price": "2299.00",
        "image_path": "store/images/classic-smartwatch.jpg",
        "is_available": True,
    },
    {
        "name": "Everyday Backpack",
        "description": "A dark navy backpack for carrying daily essentials.",
        "price": "999.00",
        "image_path": "store/images/everyday-backpack.jpg",
        "is_available": True,
    },
]


def add_sample_products(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    for product in SAMPLE_PRODUCTS:
        Product.objects.get_or_create(name=product["name"], defaults=product)


class Migration(migrations.Migration):
    dependencies = [("store", "0001_initial")]

    operations = [
        migrations.RunPython(add_sample_products, migrations.RunPython.noop),
    ]