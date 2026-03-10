from rest_framework import serializers

from .models import CommentRate


class CommentRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentRate
        fields = "__all__"
