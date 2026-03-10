from django.db import models


class CommentRate(models.Model):
    book_id = models.IntegerField()
    customer_id = models.IntegerField()
    comment = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rate {self.rating} for Book {self.book_id}"
