import os
import django
from decimal import Decimal

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django_tenants.utils import schema_context
from welfare.models import WelfareConfiguration

# Run inside the 'jabstir' tenant's namespace
with schema_context('jabstir'):
    config, created = WelfareConfiguration.objects.get_or_create(
        defaults={
            'monthly_contribution_total': Decimal('420.00'),
            'personal_savings_split': Decimal('200.00'),
            'main_welfare_split': Decimal('200.00'),
            'admin_cost_split': Decimal('20.00'),
            'loan_limit_multiplier': 5,
            'flat_interest_rate_percentage': Decimal('5.00'), # 5% flat rate
            'repayment_deadline_month': 10,                 # Must pay before October (10)
            'loan_issuance_start_month': 1,                 # Borrowing opens Jan (1)
            'loan_issuance_end_month': 7                    # Borrowing closes Jul (7)
        }
    )
    
    if created:
        print("Successfully created Jabstir's configuration rules in the database!")
    else:
        print("Jabstir's configuration rules already exist.")
