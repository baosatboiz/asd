from rest_framework import serializers

from .models import Cart, CartItem, ClothingCartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = "__all__"


class ClothingCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothingCartItem
        fields = "__all__"


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    clothing_items = ClothingCartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = "__all__"
