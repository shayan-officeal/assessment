"""
DRF Serializers for the Wallet app.
"""

from decimal import Decimal
from rest_framework import serializers


class TransferSerializer(serializers.Serializer):
    """
    Serializer for the transfer endpoint.
    
    Validates:
    - receiver_id: must be a valid integer
    - amount: must be a positive decimal with max 2 decimal places
    """
    
    receiver_id = serializers.IntegerField(
        help_text='ID of the user to transfer funds to'
    )
    amount = serializers.DecimalField(
        max_digits=19,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text='Amount to transfer (must be > 0)'
    )


class TransferResponseSerializer(serializers.Serializer):
    """Serializer for successful transfer response."""
    
    message = serializers.CharField()
    transaction_id = serializers.IntegerField()
    sender_balance = serializers.DecimalField(max_digits=19, decimal_places=2)
    amount = serializers.DecimalField(max_digits=19, decimal_places=2)
    receiver_id = serializers.IntegerField()


class WalletSerializer(serializers.Serializer):
    """Serializer for wallet balance response."""
    
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    balance = serializers.DecimalField(max_digits=19, decimal_places=2)


class ErrorSerializer(serializers.Serializer):
    """Serializer for error responses."""
    
    error = serializers.CharField()
