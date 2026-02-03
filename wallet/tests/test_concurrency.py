"""
Concurrency tests for the Wallet app.

These tests verify that the transfer endpoint correctly handles
race conditions and prevents double-spending.
"""

import time
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from wallet.models import Wallet, Transaction


class ConcurrencyTest(TransactionTestCase):
    """
    Test cases for concurrent transfer operations.
    
    Uses TransactionTestCase to ensure each test has proper
    transaction handling for concurrent operations.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test users
        self.sender = User.objects.create_user(
            username='sender',
            password='testpass123'
        )
        self.receiver1 = User.objects.create_user(
            username='receiver1',
            password='testpass123'
        )
        self.receiver2 = User.objects.create_user(
            username='receiver2',
            password='testpass123'
        )
        
        # Create wallets
        self.sender_wallet = Wallet.objects.create(
            user=self.sender,
            balance=Decimal('100.00')
        )
        Wallet.objects.create(user=self.receiver1, balance=Decimal('0.00'))
        Wallet.objects.create(user=self.receiver2, balance=Decimal('0.00'))
        
        self.transfer_url = reverse('wallet:transfer')
    
    def _make_transfer(self, username, password, receiver_id, amount):
        """
        Helper function to make a transfer request.
        
        Creates a new APIClient with fresh connection to simulate
        a separate request.
        """
        # Close the existing connection to get a fresh one
        connection.close()
        
        client = APIClient()
        
        # Login and get session
        login_success = client.login(username=username, password=password)
        if not login_success:
            return {'error': 'Login failed'}
        
        response = client.post(
            self.transfer_url,
            {'receiver_id': receiver_id, 'amount': str(amount)},
            format='json'
        )
        
        return {
            'status_code': response.status_code,
            'data': response.data if hasattr(response, 'data') else None
        }
    
    @patch('wallet.views.generate_transaction_receipt.delay')
    def test_double_spending_prevented(self, mock_task):
        """
        Test that double-spending is prevented.
        
        Scenario: A user with $100 balance attempts two simultaneous
        $100 transfers. Only one should succeed.
        
        This is the key test required by the assessment.
        """
        # Set sender balance to exactly $100
        self.sender_wallet.balance = Decimal('100.00')
        self.sender_wallet.save()
        
        results = []
        
        # Use ThreadPoolExecutor to simulate concurrent requests
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    self._make_transfer,
                    'sender', 'testpass123',
                    self.receiver1.id, Decimal('100.00')
                ),
                executor.submit(
                    self._make_transfer,
                    'sender', 'testpass123',
                    self.receiver2.id, Decimal('100.00')
                ),
            ]
            
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({'error': str(e)})
        
        # Count successful transfers
        success_count = sum(
            1 for r in results 
            if r.get('status_code') == status.HTTP_200_OK
        )
        
        # Exactly one transfer should succeed
        self.assertEqual(
            success_count, 1,
            f"Expected exactly 1 successful transfer, got {success_count}. Results: {results}"
        )
        
        # Verify sender balance is 0, not negative
        self.sender_wallet.refresh_from_db()
        self.assertEqual(
            self.sender_wallet.balance, 
            Decimal('0.00'),
            "Sender balance should be exactly 0.00 after one successful $100 transfer"
        )
        
        # Verify exactly one transaction was created
        transaction_count = Transaction.objects.count()
        self.assertEqual(
            transaction_count, 1,
            f"Expected exactly 1 transaction, got {transaction_count}"
        )
    
    @patch('wallet.views.generate_transaction_receipt.delay')
    def test_concurrent_transfers_from_same_user(self, mock_task):
        """
        Test concurrent transfers from the same user to different receivers.
        
        Scenario: A user with $100 attempts 5 concurrent $30 transfers.
        Only 3 should succeed (3 * $30 = $90 <= $100).
        """
        # Set sender balance
        self.sender_wallet.balance = Decimal('100.00')
        self.sender_wallet.save()
        
        # Create more receivers
        receivers = [self.receiver1, self.receiver2]
        for i in range(3, 6):
            receiver = User.objects.create_user(
                username=f'receiver{i}',
                password='testpass123'
            )
            Wallet.objects.create(user=receiver, balance=Decimal('0.00'))
            receivers.append(receiver)
        
        results = []
        
        # Use ThreadPoolExecutor for concurrent transfers
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    self._make_transfer,
                    'sender', 'testpass123',
                    receiver.id, Decimal('30.00')
                )
                for receiver in receivers
            ]
            
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({'error': str(e)})
        
        # Count successful transfers
        success_count = sum(
            1 for r in results 
            if r.get('status_code') == status.HTTP_200_OK
        )
        
        # At most 3 transfers should succeed (3 * $30 = $90 <= $100)
        self.assertLessEqual(
            success_count, 3,
            f"Expected at most 3 successful transfers, got {success_count}"
        )
        
        # Verify sender balance is non-negative
        self.sender_wallet.refresh_from_db()
        self.assertGreaterEqual(
            self.sender_wallet.balance, 
            Decimal('0.00'),
            "Sender balance should never be negative"
        )
        
        # Verify balance matches transaction count
        expected_remaining = Decimal('100.00') - (Decimal('30.00') * success_count)
        self.assertEqual(
            self.sender_wallet.balance,
            expected_remaining,
            f"Balance mismatch: expected {expected_remaining}, got {self.sender_wallet.balance}"
        )
    
    @patch('wallet.views.generate_transaction_receipt.delay')
    def test_no_deadlock_with_bidirectional_transfers(self, mock_task):
        """
        Test that bidirectional transfers don't cause deadlocks.
        
        Scenario: User A transfers to User B while User B transfers to User A.
        Both should eventually complete without deadlock.
        """
        # Give both users some balance
        self.sender_wallet.balance = Decimal('50.00')
        self.sender_wallet.save()
        
        receiver1_wallet = Wallet.objects.get(user=self.receiver1)
        receiver1_wallet.balance = Decimal('50.00')
        receiver1_wallet.save()
        
        results = []
        start_time = time.time()
        max_time = 10  # seconds - should complete well before this
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                # sender -> receiver1
                executor.submit(
                    self._make_transfer,
                    'sender', 'testpass123',
                    self.receiver1.id, Decimal('25.00')
                ),
                # receiver1 -> sender
                executor.submit(
                    self._make_transfer,
                    'receiver1', 'testpass123',
                    self.sender.id, Decimal('25.00')
                ),
            ]
            
            for future in as_completed(futures, timeout=max_time):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({'error': str(e)})
        
        elapsed_time = time.time() - start_time
        
        # Should complete quickly without deadlock
        self.assertLess(
            elapsed_time, max_time,
            f"Transfers took too long ({elapsed_time}s), possible deadlock"
        )
        
        # Both transfers should succeed
        success_count = sum(
            1 for r in results 
            if r.get('status_code') == status.HTTP_200_OK
        )
        self.assertEqual(
            success_count, 2,
            f"Expected 2 successful transfers, got {success_count}. Results: {results}"
        )
        
        # Balances should remain at $50 each (both transferred $25 to each other)
        self.sender_wallet.refresh_from_db()
        receiver1_wallet.refresh_from_db()
        
        self.assertEqual(
            self.sender_wallet.balance,
            Decimal('50.00'),
            "Sender balance should be $50 after bidirectional transfers"
        )
        self.assertEqual(
            receiver1_wallet.balance,
            Decimal('50.00'),
            "Receiver balance should be $50 after bidirectional transfers"
        )
