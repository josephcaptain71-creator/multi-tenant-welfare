from decimal import Decimal
from .models import LoanLedgerEntry, WelfareGroupSettings

def calculate_next_ledger_row(loan, current_month_str, amount_paid_now, interest_paid_now):
    """
    Calculates a dynamic ledger card row based on the active tenant's settings.
    """
    # 1. Fetch active settings for the tenant
    settings = WelfareGroupSettings.objects.first()
    interest_rate = settings.interest_rate_percent / Decimal('100.00')  # e.g., 5.00 -> 0.05
    calc_type = settings.interest_calculation_type

    # 2. Pull prior history from the ledger
    last_entry = loan.ledger_entries.last()
    
    if not last_entry:
        prev_loan_balance = loan.amount_borrowed
        prev_interest_balance = Decimal('0.00')
    else:
        prev_loan_balance = last_entry.loan_balance
        prev_interest_balance = last_entry.interest_balance

    # 3. Deduct current payments
    new_loan_balance = max(Decimal('0.00'), prev_loan_balance - Decimal(amount_paid_now))
    remaining_interest_balance = max(Decimal('0.00'), prev_interest_balance - Decimal(interest_paid_now))

    # 4. Apply Interest based on the tenant's chosen strategy
    new_interest_on_balance = Decimal('0.00')
    interest_accumulated_this_month = Decimal('0.00')

    if calc_type == 'REDUCING_MONTHLY':
        # --- JABSTIR'S SPECIFIC RULE ---
        # 5% charged monthly on the remaining outstanding loan balance
        new_interest_on_balance = new_loan_balance * interest_rate

    elif calc_type == 'FLAT_PRINCIPAL':
        # Standard Flat rate of 5% on original amount borrowed
        interest_accumulated_this_month = loan.amount_borrowed * interest_rate

    elif calc_type == 'TIERED_CONSTITUTIONAL':
        # Tiered months based on duration
        months_elapsed = loan.ledger_entries.count() + 1
        if months_elapsed == 1:
            interest_accumulated_this_month = loan.amount_borrowed * Decimal('0.05')
        elif months_elapsed == 2:
            interest_accumulated_this_month = loan.amount_borrowed * Decimal('0.10')
        elif months_elapsed == 3:
            interest_accumulated_this_month = loan.amount_borrowed * Decimal('0.15')
        else:
            new_interest_on_balance = new_loan_balance * Decimal('0.15')

    # Total interest balance outstanding
    total_interest_balance = remaining_interest_balance + interest_accumulated_this_month + new_interest_on_balance

    return {
        "loan_id": loan.id,
        "month": current_month_str,
        "amount_paid": Decimal(amount_paid_now),
        "loan_balance": new_loan_balance,
        "interest_accumulated": interest_accumulated_this_month,
        "interest_paid": Decimal(interest_paid_now),
        "interest_balance": total_interest_balance,
        "new_interest_on_balance": new_interest_on_balance
    }
