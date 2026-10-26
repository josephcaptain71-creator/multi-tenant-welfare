from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from welfare.models import RegistrationFormSection, RegistrationFormField, WelfareGroupSettings
from decimal import Decimal

class Command(BaseCommand):
    help = "Seeds the customized Jabstir Welfare Registration form fields inside its schema"

    def handle(self, *args, **options):
        # Using 'jabstir' as the tenant schema name as observed in the migrations output
        schema_name = 'jabstir' 
        
        self.stdout.write(f"Switching to schema context: '{schema_name}'...")
        
        with schema_context(schema_name):
            # 1. Setup Base financial configurations
            WelfareGroupSettings.objects.get_or_create(
                currency="Kshs",
                monthly_contribution_amount=Decimal('420.00'),
                savings_allocation=Decimal('200.00'),
                welfare_allocation=Decimal('200.00'),
                admin_allocation=Decimal('20.00')
            )
            
            # 2. Section: Member Details
            sec_member, _ = RegistrationFormSection.objects.get_or_create(title="Member's Details", order=1)
            RegistrationFormField.objects.get_or_create(
                section=sec_member, field_label="Employee Number", 
                field_name_slug="emp_no", field_type="TEXT", is_required=True, order=1
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_member, field_label="National ID No.", 
                field_name_slug="national_id", field_type="TEXT", is_required=True, order=2
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_member, field_label="Contact Number", 
                field_name_slug="contact_no", field_type="TEXT", is_required=True, order=3
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_member, field_label="Department", 
                field_name_slug="department", field_type="TEXT", is_required=True, order=4
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_member, field_label="Designation", 
                field_name_slug="designation", field_type="TEXT", is_required=True, order=5
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_member, field_label="Marital Status", 
                field_name_slug="marital_status", field_type="SELECT", 
                choices="Single, Married, Divorced, Widowed", is_required=True, order=6
            )

            # 3. Section: Spouse's Details
            sec_spouse, _ = RegistrationFormSection.objects.get_or_create(title="Spouse's Details", order=2)
            RegistrationFormField.objects.get_or_create(
                section=sec_spouse, field_label="Spouse Full Name", 
                field_name_slug="spouse_name", field_type="TEXT", is_required=False, order=1
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_spouse, field_label="Spouse ID No", 
                field_name_slug="spouse_id", field_type="TEXT", is_required=False, order=2
            )
            RegistrationFormField.objects.get_or_create(
                section=sec_spouse, field_label="Spouse Phone Number", 
                field_name_slug="spouse_phone", field_type="TEXT", is_required=False, order=3
            )

            # 4. Section: Salary Deduction Authority
            sec_deduction, _ = RegistrationFormSection.objects.get_or_create(title="Deduction Authority", order=3)
            RegistrationFormField.objects.get_or_create(
                section=sec_deduction, field_label="Authorize Salary Deduction?", 
                field_name_slug="salary_deduction_authorized", field_type="BOOLEAN", is_required=True, order=1
            )

            self.stdout.write(self.style.SUCCESS("Successfully seeded the customized Jabstir registration form template!"))
