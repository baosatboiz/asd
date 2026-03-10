from django.db import models


class Recommendation(models.Model):
    customer_id = models.IntegerField()
    recommended_book_id = models.IntegerField()
    score = models.FloatField(default=0.0)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommend Book {self.recommended_book_id} to Customer {self.customer_id}"
