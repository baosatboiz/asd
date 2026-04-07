from django.db import models


class ClothingItem(models.Model):
    SIZE_CHOICES = [
        ("XS", "XS"),
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("XXL", "XXL"),
    ]

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=180)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, default="M")
    color = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    category_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.size})"
