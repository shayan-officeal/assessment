"""
Management command to populate dummy data for testing.

Creates test users with wallets and sample transactions.
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from wallet.models import Wallet, Transaction


class Command(BaseCommand):
    help = 'Populate the database with dummy users, wallets, and transactions for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Transaction.objects.all().delete()
            Wallet.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))

        self.stdout.write('Creating dummy data...')

        # Create test users
        users_data = [
            {'username': 'alice', 'email': 'alice@example.com', 'password': 'password123', 'balance': '1000.00'},
            {'username': 'bob', 'email': 'bob@example.com', 'password': 'password123', 'balance': '500.00'},
            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'password123', 'balance': '750.00'},
            {'username': 'diana', 'email': 'diana@example.com', 'password': 'password123', 'balance': '250.00'},
            {'username': 'eve', 'email': 'eve@example.com', 'password': 'password123', 'balance': '100.00'},
        ]

        created_users = []
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={'email': user_data['email']}
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f"  Created user: {user.username}")
            else:
                self.stdout.write(f"  User exists: {user.username}")
            
            # Create or update wallet
            wallet, wallet_created = Wallet.objects.get_or_create(
                user=user,
                defaults={'balance': Decimal(user_data['balance'])}
            )
            
            if not wallet_created:
                wallet.balance = Decimal(user_data['balance'])
                wallet.save()
            
            created_users.append(user)
            self.stdout.write(f"    Wallet balance: ${user_data['balance']}")

        # Create some sample transactions
        self.stdout.write('\nCreating sample transactions...')
        
        sample_transactions = [
            {'sender': 'alice', 'receiver': 'bob', 'amount': '50.00'},
            {'sender': 'bob', 'receiver': 'charlie', 'amount': '25.00'},
            {'sender': 'charlie', 'receiver': 'diana', 'amount': '100.00'},
            {'sender': 'alice', 'receiver': 'eve', 'amount': '30.00'},
            {'sender': 'diana', 'receiver': 'alice', 'amount': '15.00'},
        ]

        for tx_data in sample_transactions:
            sender = User.objects.get(username=tx_data['sender'])
            receiver = User.objects.get(username=tx_data['receiver'])
            
            Transaction.objects.create(
                sender=sender,
                receiver=receiver,
                amount=Decimal(tx_data['amount'])
            )
            self.stdout.write(
                f"  {tx_data['sender']} -> {tx_data['receiver']}: ${tx_data['amount']}"
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Dummy data created successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write('Test Credentials (all use password: password123):')
        self.stdout.write('')
        self.stdout.write('  Username     Balance')
        self.stdout.write('  ---------    --------')
        for user_data in users_data:
            self.stdout.write(f"  {user_data['username']:<12} ${user_data['balance']}")
        self.stdout.write('')
