from django.db import models


class Manager(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
