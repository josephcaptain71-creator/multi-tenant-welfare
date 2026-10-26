import pandas as pd
from django.contrib.auth.models import User
from django.db import transaction
from .models import MemberProfile

def import_members_from_file(file_object, file_name):
    """
    Reads an uploaded CSV or Excel file containing legacy members and creates 
    User and MemberProfile instances dynamically.
    
    Expected Columns:
    - email (required)
    - first_name (required)
    - last_name (required)
    - membership_no (optional - auto-generated if blank)
    - employee_number (optional)
    - national_id (optional)
    - contact_number (optional)
    - department (optional)
    - designation (optional)
    """
    # 1. Determine file type and parse using Pandas
    if file_name.endswith('.csv'):
        df = pd.read_csv(file_object)
    elif file_name.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file_object)
    else:
        raise ValueError("Unsupported file format. Please upload an Excel or CSV file.")

    # Standardize column header casings/spaces
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

    success_count = 0
    errors = []

    # 2. Bulk insert inside a transaction for safety
    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                email = str(row.get('email', '')).strip()
                first_name = str(row.get('first_name', '')).strip()
                last_name = str(row.get('last_name', '')).strip()

                if not email or not first_name:
                    errors.append(f"Row {index + 1}: Missing required fields (email and first_name).")
                    continue

                # Generate username from email prefix
                username = email.split('@')[0]

                # Create or fetch Django User
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'first_name': first_name,
                        'last_name': last_name,
                    }
                )
                if created:
                    user.set_unusable_password() # They can request password reset later
                    user.save()

                # Build the dynamic response schema dictionary from spreadsheet columns
                custom_responses = {
                    "emp_no": str(row.get('employee_number', '')).strip() if 'employee_number' in row else '',
                    "national_id": str(row.get('national_id', '')).strip() if 'national_id' in row else '',
                    "contact_no": str(row.get('contact_number', '')).strip() if 'contact_number' in row else '',
                    "department": str(row.get('department', '')).strip() if 'department' in row else '',
                    "designation": str(row.get('designation', '')).strip() if 'designation' in row else '',
                }

                # Save Profile (Auto-generators run automatically if membership_no is omitted)
                membership_no = str(row.get('membership_no', '')).strip() if 'membership_no' in row else ''
                
                profile, p_created = MemberProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'membership_no': membership_no if membership_no else None,
                        'is_approved': True,
                        'custom_responses': custom_responses
                    }
                )
                
                if p_created:
                    success_count += 1

            except Exception as e:
                errors.append(f"Row {index + 1}: Error - {str(e)}")

    return success_count, errors
