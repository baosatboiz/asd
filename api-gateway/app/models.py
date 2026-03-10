from django.db import models


class GatewayLog(models.Model):
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method} {self.endpoint} -> {self.status_code}"
