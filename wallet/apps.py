"""
Wallet app configuration.
"""

from django.apps import AppConfig


class WalletConfig(AppConfig):
    """Configuration for the Wallet app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wallet'
    verbose_name = 'Wallet & Transactions'
