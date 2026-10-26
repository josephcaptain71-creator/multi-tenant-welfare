import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django_tenants.utils import schema_context
from welfare.models import WelfareConfiguration

def calculate_monthly_interest(balance, months_elapsed, config):
    """
    Applies the interest rate to the outstanding balance ONLY after 
    the configured grace period has passed.
    """
    if months_elapsed <= config.grace_period_months:
        return Decimal('0.00')
    
    rate_decimal = config.flat_interest_rate_percentage / Decimal('100.00')
    return (balance * rate_decimal).quantize(Decimal('0.01'))

with schema_context('jabstir'):
    print("--- Testing Dynamic Monthly Interest on Balance (After Grace Period) ---")
    
    # Fetch the configuration from the database
    config, _ = WelfareConfiguration.objects.get_or_create(
        defaults={
            'flat_interest_rate_percentage': Decimal('5.00'),
            'grace_period_months': 1
        }
    )
    
    principal = Decimal('10000.00')
    print(f"Loan Principal: Ksh {principal}")
    print(f"Configuration: {config.flat_interest_rate_percentage}% interest after {config.grace_period_months} month(s) grace period.\n")
    
    # --- Month 1 (Within Grace Period) ---
    m1_interest = calculate_monthly_interest(principal, months_elapsed=1, config=config)
    print(f"Month 1 (Grace): Balance: Ksh {principal} | Interest Accrued: Ksh {m1_interest}")
    
    # --- Month 2 (Grace Period Over) ---
    m2_interest = calculate_monthly_interest(principal, months_elapsed=2, config=config)
    print(f"Month 2 (Active): Balance: Ksh {principal} | Interest Accrued (5%): Ksh {m2_interest}")
    
    # Simulate payment of Ksh 4,000 total (Ksh 500 covers interest, Ksh 3,500 covers principal)
    payment = Decimal('4000.00')
    remaining_principal = principal - (payment - m2_interest)
    print(f"--- Member pays Ksh {payment} (Ksh {m2_interest} interest + Ksh {payment - m2_interest} principal) ---")
    print(f"New Outstanding Principal: Ksh {remaining_principal}\n")
    
    # --- Month 3 (Interest runs on outstanding balance) ---
    m3_interest = calculate_monthly_interest(remaining_principal, months_elapsed=3, config=config)
    print(f"Month 3 (Active): Balance: Ksh {remaining_principal} | Interest Accrued (5% on balance): Ksh {m3_interest}")
    
    assert m1_interest == Decimal('0.00'), "Month 1 should have 0 interest (grace period)"
    assert m2_interest == Decimal('500.00'), "Month 2 interest should be Ksh 500"
    assert m3_interest == Decimal('325.00'), "Month 3 interest should be 5% of remaining balance (Ksh 325.00)"
    
    print("\n--- Correct Dynamic Interest Calculations Verified Successfully! ---")
