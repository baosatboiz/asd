from rest_framework import serializers

from .models import GatewayLog


class GatewayLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayLog
        fields = "__all__"
