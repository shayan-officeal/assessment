"""
API Views for the Wallet app.

This module contains the transfer endpoint with atomic, thread-safe operations.
"""

from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Wallet, Transaction
from .serializers import TransferSerializer, TransferResponseSerializer, WalletSerializer
from .tasks import generate_transaction_receipt


class TransferView(APIView):
    """
    POST /api/wallet/transfer/
    
    Transfer funds from the authenticated user's wallet to another user's wallet.
    
    This endpoint implements:
    - Atomic transactions: All database changes are rolled back on failure
    - Thread-safety: Uses SELECT FOR UPDATE with consistent ordering to prevent
      race conditions and deadlocks
    - Validation: Checks for sufficient funds, valid receiver, and prevents
      self-transfers
    
    Request body:
        - receiver_id (int): ID of the user to transfer funds to
        - amount (decimal): Amount to transfer (must be > 0)
    
    Returns:
        - 200: Transfer successful
        - 400: Validation error (insufficient funds, invalid receiver, etc.)
        - 401: Authentication required
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle transfer request."""
        # Validate input
        serializer = TransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        receiver_id = serializer.validated_data['receiver_id']
        amount = Decimal(str(serializer.validated_data['amount']))
        sender = request.user
        
        # Prevent self-transfer
        if receiver_id == sender.id:
            return Response(
                {'error': 'Cannot transfer to yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate receiver exists
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Receiver not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure receiver has a wallet (create if not exists)
        Wallet.objects.get_or_create(user=receiver)
        
        # Ensure sender has a wallet (create if not exists)
        Wallet.objects.get_or_create(user=sender)
        
        try:
            # Execute atomic transfer with row-level locking
            transaction_record = self._execute_transfer(sender, receiver, amount)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger async receipt generation
        generate_transaction_receipt.delay(transaction_record.id)
        
        # Refresh sender wallet to get updated balance
        sender_wallet = Wallet.objects.get(user=sender)
        
        # Return success response
        response_data = {
            'message': 'Transfer successful',
            'transaction_id': transaction_record.id,
            'sender_balance': sender_wallet.balance,
            'amount': amount,
            'receiver_id': receiver_id,
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _execute_transfer(
        self, 
        sender: User, 
        receiver: User, 
        amount: Decimal
    ) -> Transaction:
        """
        Execute the transfer with atomic transaction and row-level locking.
        
        Uses SELECT FOR UPDATE with consistent ordering (by user ID) to:
        1. Prevent race conditions (double-spending)
        2. Avoid deadlocks when two users transfer to each other simultaneously
        
        Args:
            sender: The user sending funds
            receiver: The user receiving funds
            amount: The amount to transfer
            
        Returns:
            The created Transaction record
            
        Raises:
            ValueError: If sender has insufficient funds
        """
        with transaction.atomic():
            # Order wallet IDs consistently to prevent deadlocks
            # Always lock the lower ID first
            wallet_user_ids = sorted([sender.id, receiver.id])
            
            # Lock both wallets with SELECT FOR UPDATE
            # nowait=False means wait for lock if another transaction holds it
            wallets = list(
                Wallet.objects.filter(
                    user_id__in=wallet_user_ids
                ).select_for_update(nowait=False).order_by('user_id')
            )
            
            # Map wallets by user_id
            wallet_map = {w.user_id: w for w in wallets}
            sender_wallet = wallet_map[sender.id]
            receiver_wallet = wallet_map[receiver.id]
            
            # Check sufficient funds
            if sender_wallet.balance < amount:
                raise ValueError('Insufficient funds')
            
            # Perform the transfer
            sender_wallet.balance -= amount
            receiver_wallet.balance += amount
            
            # Save both wallets
            sender_wallet.save(update_fields=['balance', 'updated_at'])
            receiver_wallet.save(update_fields=['balance', 'updated_at'])
            
            # Create audit log
            transaction_record = Transaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=amount
            )
            
            return transaction_record


class WalletBalanceView(APIView):
    """
    GET /api/wallet/balance/
    
    Get the current balance of the authenticated user's wallet.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return the user's wallet balance."""
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        return Response({
            'user_id': request.user.id,
            'username': request.user.username,
            'balance': wallet.balance,
        })


class DepositView(APIView):
    """
    POST /api/wallet/deposit/
    
    Deposit funds into the authenticated user's wallet.
    This is a helper endpoint for testing purposes.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle deposit request."""
        amount = request.data.get('amount')
        
        if amount is None:
            return Response(
                {'error': 'Amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount <= 0:
            return Response(
                {'error': 'Amount must be positive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            wallet, created = Wallet.objects.select_for_update().get_or_create(
                user=request.user
            )
            wallet.balance += amount
            wallet.save(update_fields=['balance', 'updated_at'])
        
        return Response({
            'message': 'Deposit successful',
            'balance': wallet.balance,
        })


class TransactionHistoryView(APIView):
    """
    GET /api/wallet/transactions/
    
    Get the transaction history for the authenticated user.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return the user's transaction history."""
        user = request.user
        
        # Get transactions where user is sender or receiver
        sent = Transaction.objects.filter(sender=user).select_related('receiver')
        received = Transaction.objects.filter(receiver=user).select_related('sender')
        
        # Combine and format
        transactions = []
        
        for tx in sent:
            transactions.append({
                'id': tx.id,
                'type': 'sent',
                'counterparty': tx.receiver.username,
                'counterparty_id': tx.receiver.id,
                'amount': str(tx.amount),
                'timestamp': tx.timestamp.isoformat(),
                'receipt_path': tx.receipt_path,
            })
        
        for tx in received:
            transactions.append({
                'id': tx.id,
                'type': 'received',
                'counterparty': tx.sender.username,
                'counterparty_id': tx.sender.id,
                'amount': str(tx.amount),
                'timestamp': tx.timestamp.isoformat(),
                'receipt_path': tx.receipt_path,
            })
        
        # Sort by timestamp descending
        transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return Response({
            'transactions': transactions,
            'count': len(transactions),
        })


class UserListView(APIView):
    """
    GET /api/wallet/users/
    
    Get a list of all users (for transfer dropdown).
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return list of users excluding current user."""
        users = User.objects.exclude(id=request.user.id).values('id', 'username')
        
        return Response({
            'users': list(users),
        })

