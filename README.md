# Atomic Wallet & Transaction System

A secure, thread-safe internal credit transfer system built with Django, Django REST Framework, PostgreSQL, Celery, and Redis.

## Features

- **Atomic Transactions**: All transfer operations are wrapped in database transactions with automatic rollback on failure
- **Thread-Safe Transfers**: Uses PostgreSQL's `SELECT FOR UPDATE` with consistent ordering to prevent race conditions and deadlocks
- **Audit Logging**: Every successful transfer creates an immutable transaction record
- **Async Receipt Generation**: PDF receipts are generated asynchronously via Celery
- **Decimal Precision**: All monetary values use `DecimalField` for accurate calculations

## Prerequisites

- Python 3.10+
- PostgreSQL 16+ (installed and running)
- Redis 3.0+ (installed and running)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Assessment
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update with your settings:

```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=assessment
DB_USER=postgres
DB_PASSWORD=your-password-here
DB_HOST=localhost
DB_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Create PostgreSQL Database

```bash
createdb -U postgres assessment
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 8. Start Redis (if not running as service)

```bash
redis-server
```

### 9. Start Celery Worker

```bash
celery -A Assessment worker --loglevel=info --pool=solo  # Windows
# or
celery -A Assessment worker --loglevel=info  # Linux/Mac
```

### 10. Start Django Server

```bash
python manage.py runserver
```

## API Endpoints

### Transfer Funds

```http
POST /api/wallet/transfer/
Content-Type: application/json
Authorization: Basic <credentials>

{
    "receiver_id": 2,
    "amount": "50.00"
}
```

**Response (Success):**
```json
{
    "message": "Transfer successful",
    "transaction_id": 1,
    "sender_balance": "50.00",
    "amount": "50.00",
    "receiver_id": 2
}
```

**Response (Error):**
```json
{
    "error": "Insufficient funds"
}
```

### Get Wallet Balance

```http
GET /api/wallet/balance/
Authorization: Basic <credentials>
```

**Response:**
```json
{
    "user_id": 1,
    "username": "john",
    "balance": "100.00"
}
```

### Deposit Funds (Testing Helper)

```http
POST /api/wallet/deposit/
Content-Type: application/json
Authorization: Basic <credentials>

{
    "amount": "100.00"
}
```

## Concurrency & Race Condition Handling

### The Problem

When two simultaneous requests attempt to transfer funds from the same wallet, a race condition can occur:

1. Request A reads balance: $100
2. Request B reads balance: $100
3. Request A transfers $100, writes balance: $0
4. Request B transfers $100, writes balance: $0 (or -$100!)

This is called **double-spending** and can result in data corruption.

### The Solution

This implementation uses two key PostgreSQL features:

#### 1. SELECT FOR UPDATE

```python
wallets = Wallet.objects.filter(
    user_id__in=wallet_user_ids
).select_for_update(nowait=False)
```

This acquires an exclusive row-level lock on the selected wallet rows. Any other transaction attempting to modify these rows will wait until the lock is released.

#### 2. Consistent Lock Ordering

```python
wallet_user_ids = sorted([sender.id, receiver.id])
```

To prevent deadlocks when two users transfer to each other simultaneously, wallets are always locked in a consistent order (by user ID). This ensures that:

- Transfer A→B locks wallets in order: min(A,B), max(A,B)
- Transfer B→A locks wallets in same order: min(A,B), max(A,B)

Without consistent ordering, deadlocks could occur when both transactions hold one lock and wait for the other.

#### 3. Atomic Transactions

```python
with transaction.atomic():
    # All database operations here
```

If any operation fails (including the transaction log creation), all changes are automatically rolled back.

## Testing

### Run All Tests

```bash
python manage.py test wallet
```

### Run Specific Test Suites

```bash
# Model tests
python manage.py test wallet.tests.test_models

# API tests
python manage.py test wallet.tests.test_views

# Concurrency tests (most important!)
python manage.py test wallet.tests.test_concurrency
```

### Key Concurrency Test

The `test_double_spending_prevented` test simulates the exact scenario from the assessment:

> If a user with $10 attempts two simultaneous $10 transfers, only one must succeed.

```python
def test_double_spending_prevented(self):
    """
    Test that double-spending is prevented.
    
    Scenario: A user with $100 balance attempts two simultaneous
    $100 transfers. Only one should succeed.
    """
    # Uses ThreadPoolExecutor to run concurrent transfers
    # Verifies exactly one succeeds and balance is $0, not negative
```

## Project Structure

```
Assessment/
├── Assessment/
│   ├── __init__.py       # Celery app import
│   ├── celery.py         # Celery configuration
│   ├── settings.py       # Django settings
│   ├── urls.py           # Main URL routing
│   └── wsgi.py
├── wallet/
│   ├── __init__.py
│   ├── admin.py          # Django admin configuration
│   ├── apps.py           # App configuration
│   ├── models.py         # Wallet & Transaction models
│   ├── serializers.py    # DRF serializers
│   ├── tasks.py          # Celery tasks (receipt generation)
│   ├── urls.py           # Wallet API URLs
│   ├── views.py          # API views (transfer logic)
│   └── tests/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_views.py
│       └── test_concurrency.py
├── media/
│   └── receipts/         # Generated PDF receipts
├── .env                  # Environment variables
├── .env.example          # Environment template
├── manage.py
├── requirements.txt
├── prompts.txt           # AI prompts used
└── README.md
```

## Technical Decisions

### Why PostgreSQL?

PostgreSQL provides robust row-level locking via `SELECT FOR UPDATE`, which is essential for preventing race conditions. SQLite's locking is database-level, not row-level, making it unsuitable for this use case.

### Why DecimalField?

Floating-point arithmetic can lead to rounding errors with currency:
```python
>>> 0.1 + 0.2
0.30000000000000004
```

`DecimalField` uses Python's `Decimal` type, which provides exact decimal representation.

### Why PROTECT on Foreign Keys?

Transaction records use `on_delete=models.PROTECT` to prevent accidental deletion of users who have transaction history. This maintains audit trail integrity.

## License

This project was created as a technical assessment.
