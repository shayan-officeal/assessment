"""
API tests for the Wallet app views.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from wallet.models import Wallet, Transaction


class TransferViewTest(TestCase):
    """Test cases for the TransferView API endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        
        # Create test users
        self.sender = User.objects.create_user(
            username='sender',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            password='testpass123'
        )
        
        # Create wallets with initial balances
        self.sender_wallet = Wallet.objects.create(
            user=self.sender,
            balance=Decimal('100.00')
        )
        self.receiver_wallet = Wallet.objects.create(
            user=self.receiver,
            balance=Decimal('50.00')
        )
        
        # URL for transfer endpoint
        self.transfer_url = reverse('wallet:transfer')
    
    @patch('wallet.views.generate_transaction_receipt.delay')
    def test_successful_transfer(self, mock_task):
        """Test a successful transfer between two users."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.receiver.id, 'amount': '25.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Transfer successful')
        self.assertEqual(Decimal(str(response.data['amount'])), Decimal('25.00'))
        
        # Verify balances updated
        self.sender_wallet.refresh_from_db()
        self.receiver_wallet.refresh_from_db()
        
        self.assertEqual(self.sender_wallet.balance, Decimal('75.00'))
        self.assertEqual(self.receiver_wallet.balance, Decimal('75.00'))
        
        # Verify transaction created
        self.assertEqual(Transaction.objects.count(), 1)
        transaction = Transaction.objects.first()
        self.assertEqual(transaction.sender, self.sender)
        self.assertEqual(transaction.receiver, self.receiver)
        self.assertEqual(transaction.amount, Decimal('25.00'))
        
        # Verify Celery task was triggered
        mock_task.assert_called_once_with(transaction.id)
    
    def test_transfer_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.receiver.id, 'amount': '25.00'},
            format='json'
        )
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    @patch('wallet.views.generate_transaction_receipt.delay')
    def test_transfer_insufficient_funds(self, mock_task):
        """Test transfer fails with insufficient funds."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.receiver.id, 'amount': '150.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient funds', response.data['error'])
        
        # Verify balances unchanged
        self.sender_wallet.refresh_from_db()
        self.receiver_wallet.refresh_from_db()
        
        self.assertEqual(self.sender_wallet.balance, Decimal('100.00'))
        self.assertEqual(self.receiver_wallet.balance, Decimal('50.00'))
        
        # Verify no transaction created
        self.assertEqual(Transaction.objects.count(), 0)
        
        # Verify Celery task was not triggered
        mock_task.assert_not_called()
    
    def test_transfer_to_self(self):
        """Test that self-transfer is rejected."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.sender.id, 'amount': '25.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot transfer to yourself', response.data['error'])
    
    def test_transfer_to_invalid_user(self):
        """Test transfer to non-existent user is rejected."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': 99999, 'amount': '25.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Receiver not found', response.data['error'])
    
    def test_transfer_negative_amount(self):
        """Test that negative amounts are rejected."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.receiver.id, 'amount': '-25.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_transfer_zero_amount(self):
        """Test that zero amount is rejected."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.receiver.id, 'amount': '0.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_transfer_missing_receiver_id(self):
        """Test that missing receiver_id is rejected."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'amount': '25.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_transfer_missing_amount(self):
        """Test that missing amount is rejected."""
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': self.receiver.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('wallet.views.generate_transaction_receipt.delay')
    def test_transfer_creates_receiver_wallet_if_not_exists(self, mock_task):
        """Test that a wallet is created for receiver if they don't have one."""
        # Create a new user without a wallet
        new_receiver = User.objects.create_user(
            username='newreceiver',
            password='testpass123'
        )
        self.assertFalse(Wallet.objects.filter(user=new_receiver).exists())
        
        self.client.force_authenticate(user=self.sender)
        
        response = self.client.post(
            self.transfer_url,
            {'receiver_id': new_receiver.id, 'amount': '25.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify wallet was created
        self.assertTrue(Wallet.objects.filter(user=new_receiver).exists())
        receiver_wallet = Wallet.objects.get(user=new_receiver)
        self.assertEqual(receiver_wallet.balance, Decimal('25.00'))


class WalletBalanceViewTest(TestCase):
    """Test cases for the WalletBalanceView API endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal('100.00')
        )
        self.balance_url = reverse('wallet:balance')
    
    def test_get_balance_authenticated(self):
        """Test getting balance for authenticated user."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.balance_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_id'], self.user.id)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(Decimal(str(response.data['balance'])), Decimal('100.00'))
    
    def test_get_balance_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = self.client.get(self.balance_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_get_balance_creates_wallet_if_not_exists(self):
        """Test that a wallet is created if user doesn't have one."""
        new_user = User.objects.create_user(
            username='newuser',
            password='testpass123'
        )
        self.assertFalse(Wallet.objects.filter(user=new_user).exists())
        
        self.client.force_authenticate(user=new_user)
        response = self.client.get(self.balance_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Wallet.objects.filter(user=new_user).exists())
        self.assertEqual(Decimal(str(response.data['balance'])), Decimal('0.00'))


class DepositViewTest(TestCase):
    """Test cases for the DepositView API endpoint."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal('100.00')
        )
        self.deposit_url = reverse('wallet:deposit')
    
    def test_successful_deposit(self):
        """Test a successful deposit."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            self.deposit_url,
            {'amount': '50.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Deposit successful')
        
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('150.00'))
    
    def test_deposit_unauthenticated(self):
        """Test that unauthenticated requests are rejected."""
        response = self.client.post(
            self.deposit_url,
            {'amount': '50.00'},
            format='json'
        )
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_deposit_negative_amount(self):
        """Test that negative deposits are rejected."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            self.deposit_url,
            {'amount': '-50.00'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_deposit_missing_amount(self):
        """Test that missing amount is rejected."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            self.deposit_url,
            {},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
