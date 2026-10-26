from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from django.utils import timezone

# --- 1. DYNAMIC REGISTRATION FORM LAYOUT ---
class RegistrationFormSection(models.Model):
    """
    Groups form fields together (e.g., 'Spouse Details', 'Children's Details').
    """
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text="Order in which this section appears on Web/Android")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class RegistrationFormField(models.Model):
    """
    Defines a dynamic field within a section.
    Allows each tenant to ask for custom questions (e.g., birth certificates, payroll numbers).
    """
    FIELD_TYPE_CHOICES = [
        ('TEXT', 'Short Text'),
        ('TEXTAREA', 'Long Text / Address'),
        ('NUMBER', 'Number'),
        ('DATE', 'Date'),
        ('SELECT', 'Dropdown Menu'),
        ('BOOLEAN', 'Yes/No Checkbox'),
        ('FILE', 'Document Upload (PDF/Image)'),
    ]

    section = models.ForeignKey(RegistrationFormSection, on_delete=models.CASCADE, related_name='fields')
    field_label = models.CharField(max_length=255, help_text="e.g., 'Employee Number', 'Date of Birth'")
    field_name_slug = models.SlugField(max_length=100, help_text="Unique database identifier for parsing, e.g., 'emp_no'")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    is_required = models.BooleanField(default=True)
    choices = models.TextField(blank=True, null=True, help_text="Comma-separated choices if field_type is 'SELECT'")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('section', 'field_name_slug')

    def __str__(self):
        return f"{self.field_label} ({self.get_field_type_display()})"


class LoanRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('repaid', 'Fully Repaid'),
    ]

    profile = models.ForeignKey('MemberProfile', on_delete=models.CASCADE, related_name='loans')
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    
    # Guarantors (Must be approved members with 6+ contributions)
    guarantor_1 = models.ForeignKey(
        'MemberProfile', on_delete=models.PROTECT, 
        related_name='guaranteed_loans_1', null=True, blank=True
    )
    guarantor_2 = models.ForeignKey(
        'MemberProfile', on_delete=models.PROTECT, 
        related_name='guaranteed_loans_2', null=True, blank=True
    )

    # National ID Documents
    id_front = models.ImageField(upload_to='loan_ids/front/', null=True, blank=True)
    id_back = models.ImageField(upload_to='loan_ids/back/', null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    date_applied = models.DateTimeField(auto_now_add=True)
    date_disbursed = models.DateTimeField(blank=True, null=True)
    date_reviewed = models.DateTimeField(blank=True, null=True)
    admin_remarks = models.TextField(blank=True, null=True)

    @property
    def current_balance(self):
        """Calculates balance with 30-day grace period and 5% monthly interest after."""
        if self.status != 'disbursed':
            return float(self.amount_requested)
            
        base_amount = float(self.amount_requested)
        if not self.date_disbursed:
            return base_amount
            
        now = timezone.now()
        delta = now - self.date_disbursed
        days_passed = delta.days
        
        # 30-day grace period: No interest added
        if days_passed <= 30:
            return base_amount
            
        # After 30 days, 5% interest per month overdue
        extra_days = days_passed - 30
        months_overdue = (extra_days // 30) + 1
        total_with_interest = base_amount * (1 + (0.05 * months_overdue))
        return round(total_with_interest, 2)

    @property
    def is_defaulted(self):
        """Checks if loan missed the November 1st annual deadline."""
        if self.status == 'repaid' or not self.date_disbursed:
            return False
            
        disbursed_year = self.date_disbursed.year
        nov_first = datetime.datetime(disbursed_year, 11, 1, tzinfo=timezone.get_current_timezone())
        
        return timezone.now() > nov_first and self.status != 'repaid'

    def __str__(self):
        return f"Loan KSh {self.amount_requested} - {self.profile.membership_no} ({self.status})"


# --- 2. FLEXIBLE MEMBER PROFILE & DATA ---
class MemberProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='welfare_profile')
    membership_no = models.CharField(max_length=50, unique=True, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    custom_responses = models.JSONField(default=dict, blank=True)
    uploaded_documents = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate membership number if not explicitly set
        if not self.membership_no:
            current_year = datetime.datetime.now().year
            prefix = f"MEM-{current_year}-"
            same_year_profiles = MemberProfile.objects.filter(membership_no__startswith=prefix)
            next_sequence = same_year_profiles.count() + 1

            while True:
                candidate_no = f"{prefix}{next_sequence:04d}"
                if not MemberProfile.objects.filter(membership_no=candidate_no).exists():
                    self.membership_no = candidate_no
                    break
                next_sequence += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.membership_no})"


class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Urgent Warning'),
        ('success', 'Good News / Update'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='info')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# --- 3. CONTROLS, POLICIES & CONTRIBUTIONS ---
class WelfareGroupSettings(models.Model):
    """
    Stores group-specific rules to run the system autonomously per tenant.
    """
    currency = models.CharField(max_length=10, default="KES")
    
    # Financial Splits
    monthly_contribution_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('420.00'))
    savings_allocation = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('200.00'))
    welfare_allocation = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('200.00'))
    admin_allocation = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('20.00'))

    # Dynamic Lending & Interest Settings
    INTEREST_TYPE_CHOICES = [
        ('REDUCING_MONTHLY', 'Monthly Reducing Balance (e.g., Jabstir 5%)'),
        ('FLAT_PRINCIPAL', 'Flat Rate on Original Principal'),
        ('TIERED_CONSTITUTIONAL', 'Tiered Constitutional Grace System'),
    ]
    interest_calculation_type = models.CharField(
        max_length=30, 
        choices=INTEREST_TYPE_CHOICES, 
        default='REDUCING_MONTHLY'
    )
    interest_rate_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('5.00'), 
        help_text="e.g. 5.00 for 5%"
    )

    # Rules
    loan_limit_multiplier_of_savings = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('5.00'))
    emergency_loan_max_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('10000.00'))
    lending_start_month = models.PositiveIntegerField(default=1) # January
    lending_end_month = models.PositiveIntegerField(default=7)   # July

    def __str__(self):
        return f"Operational Parameters ({self.interest_calculation_type} - {self.interest_rate_percent}%)"


class Contribution(models.Model):
    profile = models.ForeignKey('MemberProfile', on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month_for = models.CharField(max_length=50)  # e.g., "October 2026"
    date_paid = models.DateTimeField(auto_now_add=True)
    receipt_no = models.CharField(max_length=50, unique=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.profile.membership_no} - {self.amount} ({self.month_for})"

class AnnualInterestDistribution(models.Model):
    DISTRIBUTION_CHOICES = [
        ('DIVIDEND', 'Distribute Equally to Members'),
        ('RETAINED_EVENT', 'Retain for Group Event / Trip'),
    ]

    year = models.PositiveIntegerField(unique=True)
    total_interest_pool = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    decision = models.CharField(max_length=20, choices=DISTRIBUTION_CHOICES)
    amount_per_member = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    remarks = models.TextField(blank=True, null=True, help_text="e.g., Allocated for 2026 Annual Member Trip")
    processed_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.year} Interest Pool (KSh {self.total_interest_pool}) - {self.get_decision_display()}"


# Update your existing Contribution model to include contribution_type:
class Contribution(models.Model):
    TYPE_CHOICES = [
        ('REGULAR', 'Regular Monthly Savings'),
        ('INTEREST_DIVIDEND', 'Year-End Interest Share Bonus'),
    ]

    profile = models.ForeignKey('MemberProfile', on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    month_for = models.CharField(max_length=50)  # e.g., "October 2026"
    date_paid = models.DateTimeField(auto_now_add=True)
    receipt_no = models.CharField(max_length=50, unique=True)
    contribution_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='REGULAR')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.profile.membership_no} - {self.amount} ({self.month_for})"
