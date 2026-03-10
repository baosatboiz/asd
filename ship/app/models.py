from django.db import models


class Shipment(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
    ]

    order_id = models.IntegerField()
    customer_id = models.IntegerField()
    address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shipment #{self.id} for Order {self.order_id}"
