"""
Unit tests for Wallet app models.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from wallet.models import Wallet, Transaction


class WalletModelTest(TestCase):
    """Test cases for the Wallet model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_wallet_creation(self):
        """Test that a wallet can be created for a user."""
        wallet = Wallet.objects.create(user=self.user)
        
        self.assertEqual(wallet.user, self.user)
        self.assertEqual(wallet.balance, Decimal('0.00'))
        self.assertIsNotNone(wallet.created_at)
        self.assertIsNotNone(wallet.updated_at)
    
    def test_wallet_default_balance(self):
        """Test that wallet default balance is 0.00."""
        wallet = Wallet.objects.create(user=self.user)
        self.assertEqual(wallet.balance, Decimal('0.00'))
    
    def test_wallet_balance_precision(self):
        """Test that wallet balance maintains decimal precision."""
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('1234.56'))
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('1234.56'))
    
    def test_wallet_one_to_one_constraint(self):
        """Test that a user can only have one wallet."""
        Wallet.objects.create(user=self.user)
        
        with self.assertRaises(IntegrityError):
            Wallet.objects.create(user=self.user)
    
    def test_wallet_str_representation(self):
        """Test wallet string representation."""
        wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.50'))
        self.assertIn('testuser', str(wallet))
        self.assertIn('100.50', str(wallet))
    
    def test_wallet_balance_cannot_be_negative_via_validator(self):
        """Test that wallet balance validator prevents negative values."""
        wallet = Wallet(user=self.user, balance=Decimal('-10.00'))
        with self.assertRaises(ValidationError):
            wallet.full_clean()


class TransactionModelTest(TestCase):
    """Test cases for the Transaction model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sender = User.objects.create_user(
            username='sender',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            password='testpass123'
        )
    
    def test_transaction_creation(self):
        """Test that a transaction can be created."""
        transaction = Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('50.00')
        )
        
        self.assertEqual(transaction.sender, self.sender)
        self.assertEqual(transaction.receiver, self.receiver)
        self.assertEqual(transaction.amount, Decimal('50.00'))
        self.assertIsNotNone(transaction.timestamp)
        self.assertEqual(transaction.receipt_path, '')
    
    def test_transaction_amount_precision(self):
        """Test that transaction amount maintains decimal precision."""
        transaction = Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('123.45')
        )
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal('123.45'))
    
    def test_transaction_str_representation(self):
        """Test transaction string representation."""
        transaction = Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('50.00')
        )
        str_repr = str(transaction)
        self.assertIn('sender', str_repr)
        self.assertIn('receiver', str_repr)
        self.assertIn('50.00', str_repr)
    
    def test_transaction_ordering(self):
        """Test that transactions are ordered by timestamp descending."""
        t1 = Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('10.00')
        )
        t2 = Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('20.00')
        )
        
        transactions = list(Transaction.objects.all())
        self.assertEqual(transactions[0], t2)  # Most recent first
        self.assertEqual(transactions[1], t1)
    
    def test_transaction_protect_sender_deletion(self):
        """Test that deleting sender is prevented by PROTECT."""
        Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('50.00')
        )
        
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.sender.delete()
    
    def test_transaction_protect_receiver_deletion(self):
        """Test that deleting receiver is prevented by PROTECT."""
        Transaction.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal('50.00')
        )
        
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.receiver.delete()
