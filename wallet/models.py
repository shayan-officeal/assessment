"""
Data models for the Wallet app.

This module contains:
- Wallet: User balance storage with decimal precision
- Transaction: Audit log for all transfers
"""

from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Wallet(models.Model):
    """
    Wallet model linked to a User that maintains a balance.
    
    Uses DecimalField for accurate currency representation.
    Balance constraint: must be >= 0.00
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet',
        help_text='The user who owns this wallet'
    )
    balance = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Current wallet balance (must be >= 0.00)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the wallet was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='When the wallet was last updated'
    )

    class Meta:
        """Wallet model metadata."""
        
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
        indexes = [
            models.Index(fields=['user'], name='wallet_user_idx'),
        ]

    def __str__(self) -> str:
        """Return string representation of the wallet."""
        return f"Wallet({self.user.username}: ${self.balance})"


class Transaction(models.Model):
    """
    Transaction model to record audit log of all transfers.
    
    Every successful transfer creates a Transaction record
    that cannot be modified or deleted (PROTECT).
    """
    
    sender = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sent_transactions',
        help_text='User who sent the funds'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='received_transactions',
        help_text='User who received the funds'
    )
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Amount transferred'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the transaction occurred'
    )
    receipt_path = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='Path to the generated receipt file'
    )

    class Meta:
        """Transaction model metadata."""
        
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sender', 'timestamp'], name='tx_sender_time_idx'),
            models.Index(fields=['receiver', 'timestamp'], name='tx_receiver_time_idx'),
            models.Index(fields=['timestamp'], name='tx_timestamp_idx'),
        ]

    def __str__(self) -> str:
        """Return string representation of the transaction."""
        return (
            f"Transaction #{self.id}: "
            f"{self.sender.username} -> {self.receiver.username} "
            f"${self.amount} @ {self.timestamp}"
        )
