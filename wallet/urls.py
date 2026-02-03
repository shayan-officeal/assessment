"""
URL configuration for the Wallet app.
"""

from django.urls import path
from .views import (
    TransferView, 
    WalletBalanceView, 
    DepositView,
    TransactionHistoryView,
    UserListView,
)

app_name = 'wallet'

urlpatterns = [
    path('transfer/', TransferView.as_view(), name='transfer'),
    path('balance/', WalletBalanceView.as_view(), name='balance'),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('transactions/', TransactionHistoryView.as_view(), name='transactions'),
    path('users/', UserListView.as_view(), name='users'),
]
