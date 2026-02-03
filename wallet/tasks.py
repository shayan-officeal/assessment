"""
Celery tasks for the Wallet app.

This module contains background tasks triggered after successful transfers.
"""

import os
from datetime import datetime
from celery import shared_task
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_transaction_receipt(self, transaction_id: int) -> str:
    """
    Generate a PDF receipt for a transaction.
    
    This task is triggered asynchronously after a successful transfer.
    The receipt is saved to media/receipts/{transaction_id}_{timestamp}.pdf
    
    Args:
        transaction_id: The ID of the Transaction to generate a receipt for.
        
    Returns:
        The path to the generated receipt file.
    """
    # Import here to avoid circular imports
    from wallet.models import Transaction
    
    try:
        transaction = Transaction.objects.select_related(
            'sender', 'receiver'
        ).get(id=transaction_id)
    except Transaction.DoesNotExist:
        # Transaction was deleted before receipt generation
        return ''
    
    # Create receipts directory if it doesn't exist
    receipts_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"receipt_{transaction_id}_{timestamp}.pdf"
    filepath = os.path.join(receipts_dir, filename)
    relative_path = f"receipts/{filename}"
    
    # Create PDF receipt
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 1 * inch, "Transaction Receipt")
    
    # Horizontal line
    c.setLineWidth(2)
    c.line(1 * inch, height - 1.3 * inch, width - 1 * inch, height - 1.3 * inch)
    
    # Transaction details
    c.setFont("Helvetica", 12)
    y_position = height - 2 * inch
    line_height = 0.4 * inch
    
    details = [
        ("Transaction ID:", str(transaction.id)),
        ("Date & Time:", transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')),
        ("", ""),  # Spacer
        ("From:", f"{transaction.sender.username} (ID: {transaction.sender.id})"),
        ("To:", f"{transaction.receiver.username} (ID: {transaction.receiver.id})"),
        ("", ""),  # Spacer
        ("Amount:", f"${transaction.amount:,.2f}"),
    ]
    
    for label, value in details:
        if label:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1.5 * inch, y_position, label)
            c.setFont("Helvetica", 12)
            c.drawString(3.5 * inch, y_position, value)
        y_position -= line_height
    
    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(
        width / 2, 
        1 * inch, 
        "This is an automatically generated receipt. Please keep for your records."
    )
    
    # Save PDF
    c.save()
    
    # Update transaction with receipt path
    transaction.receipt_path = relative_path
    transaction.save(update_fields=['receipt_path'])
    
    return relative_path
