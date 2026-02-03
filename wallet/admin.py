"""
Admin configuration for the Wallet app.
"""

from django.contrib import admin
from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin configuration for Wallet model."""
    
    list_display = ('id', 'user', 'balance', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin configuration for Transaction model."""
    
    list_display = ('id', 'sender', 'receiver', 'amount', 'timestamp', 'receipt_path')
    list_filter = ('timestamp',)
    search_fields = ('sender__username', 'receiver__username')
    readonly_fields = ('sender', 'receiver', 'amount', 'timestamp', 'receipt_path')
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        """Transactions should only be created through the API."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Transactions are immutable."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Transactions cannot be deleted."""
        return False
