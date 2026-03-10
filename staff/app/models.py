from django.db import models


class Staff(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"
