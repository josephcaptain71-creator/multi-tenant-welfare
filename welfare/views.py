import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views import View

# REST API Imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import (
    MemberProfile,
    RegistrationFormField,
    RegistrationFormSection,
    Contribution,
    Announcement,
    LoanRequest
)

# ============================================
# 1. API Endpoints (Mobile / Headless Frontends)
# ============================================

class RegistrationFormSchemaAPIView(APIView):
    """
    API endpoint that returns the dynamic registration form schema grouped by section
    along with field definitions.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        sections = RegistrationFormSection.objects.all().order_by('order').prefetch_related('fields')
        schema = []

        for section in sections:
            section_data = {
                "section_id": section.id,
                "title": section.title,
                "description": section.description,
                "order": section.order,
                "fields": []
            }
            for field in section.fields.all():
                section_data["fields"].append({
                    "field_id": field.id,
                    "field_label": field.field_label,
                    "field_name_slug": field.field_name_slug,
                    "field_type": field.field_type,
                    "is_required": field.is_required,
                    "options": field.options
                })
            schema.append(section_data)

        return Response(schema, status=status.HTTP_200_OK)


class RegisterWelfareMemberAPIView(APIView):
    """
    REST API endpoint for submitting a new member registration.
    """
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        full_name = data.get('full_name', '').strip()

        if not username or not password or not email or not full_name:
            return Response(
                {"error": "Username, Email, Full Name, and Password are required fields."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != confirm_password:
            return Response(
                {"error": "Passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": f"Username '{username}' is already taken."},
                status=status.HTTP_400_BAD_REQUEST
            )

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        base_fields = ['username', 'email', 'password', 'confirm_password', 'full_name']
        custom_responses = {}

        db_fields = {field.field_name_slug: field for field in RegistrationFormField.objects.all()}

        for key, value in data.items():
            if key not in base_fields:
                field_obj = db_fields.get(key)
                if field_obj:
                    if field_obj.is_required and not value:
                        return Response(
                            {"error": f"The field '{field_obj.field_label}' is required."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    custom_responses[key] = value

        for slug, field_obj in db_fields.items():
            if field_obj.is_required and slug not in custom_responses:
                return Response(
                    {"error": f"The field '{field_obj.field_label}' is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        profile = MemberProfile.objects.create(
            user=user,
            membership_no=f"MEM-{uuid.uuid4().hex[:6].upper()}",
            is_approved=False,
            custom_responses=custom_responses
        )

        return Response(
            {
                "message": "Registration successful!",
                "membership_no": profile.membership_no,
                "status": "Pending approval"
            },
            status=status.HTTP_201_CREATED
        )


# ============================================
# 2. Interactive Frontend Wizard Views
# ============================================

class TenantRegistrationView(View):
    """
    Renders and processes the dynamic multi-step registration form HTML wizard.
    Supports file uploads directly into tenant storage.
    """
    def get(self, request, *args, **kwargs):
        sections = RegistrationFormSection.objects.prefetch_related('fields').order_by('order')
        context = {
            'sections': sections,
        }
        return render(request, 'welfare/register.html', context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        full_name = request.POST.get('full_name', '').strip()

        if not username or not email or not full_name or not password:
            messages.error(request, "Username, Email, Full Name, and Password are required.")
            return redirect(request.path)

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect(request.path)

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return redirect(request.path)

        db_fields = RegistrationFormField.objects.all()
        custom_responses = {}

        for field_obj in db_fields:
            field_slug = field_obj.field_name_slug

            if field_obj.field_type == 'FILE':
                uploaded_file = request.FILES.get(field_slug)
                if field_obj.is_required and not uploaded_file:
                    messages.error(request, f"The file '{field_obj.field_label}' is required.")
                    return redirect(request.path)
                if uploaded_file:
                    file_path = default_storage.save(f"member_uploads/{uploaded_file.name}", uploaded_file)
                    custom_responses[field_slug] = file_path
            else:
                value = request.POST.get(field_slug, '').strip()
                if field_obj.is_required and not value:
                    messages.error(request, f"The field '{field_obj.field_label}' is required.")
                    return redirect(request.path)
                if value:
                    custom_responses[field_slug] = value

        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        profile = MemberProfile.objects.create(
            user=user,
            membership_no=f"MEM-{uuid.uuid4().hex[:6].upper()}",
            is_approved=False,
            custom_responses=custom_responses
        )

        messages.success(request, f"Registration successful! Reference ID: {profile.membership_no}. Pending approval.")
        return redirect('registration_success')


# ============================================
# 3. Administrative Dashboard View
# ============================================

@method_decorator(staff_member_required(login_url='/login/'), name='dispatch')
class AdminApprovalDashboardView(View):
    """
    Renders administrative dashboard listing pending member applications
    along with their dynamic custom responses.
    """
    login_url = '/login/'

    def get(self, request, *args, **kwargs):
        pending_profiles = MemberProfile.objects.filter(is_approved=False).select_related('user')
        context = {
            'pending_profiles': pending_profiles,
        }
        return render(request, 'welfare/admin_dashboard.html', context)


@method_decorator(staff_member_required(login_url='/login/'), name='dispatch')
class ApproveMemberView(View):
    """
    Handles the activation action of a pending member.
    """
    def post(self, request, pk, *args, **kwargs):
        try:
            profile = MemberProfile.objects.get(pk=pk)
            profile.is_approved = True
            profile.save()
            messages.success(request, f"Member {profile.user.get_full_name()} ({profile.membership_no}) has been approved successfully!")
        except MemberProfile.DoesNotExist:
            messages.error(request, "Member profile not found.")

        return redirect('admin_approval_dashboard')

import csv
import io
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

@staff_member_required
def bulk_upload_contributions(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('admin:index')

        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string)
        next(reader) # Skip header row: membership_no, amount, month_for, receipt_no

        success_count = 0
        for row in reader:
            if len(row) < 4:
                continue
            membership_no, amount, month_for, receipt_no = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            
            try:
                profile = MemberProfile.objects.get(membership_no=membership_no)
                Contribution.objects.get_or_create(
                    receipt_no=receipt_no,
                    defaults={
                        'profile': profile,
                        'amount': Decimal(amount),
                        'month_for': month_for,
                        'contribution_type': 'REGULAR',
                        'recorded_by': request.user
                    }
                )
                success_count += 1
            except MemberProfile.DoesNotExist:
                continue

        messages.success(request, f"Successfully imported {success_count} contributions from CSV roster!")
        return redirect('admin:index')
    
    return render(request, 'welfare/admin_bulk_upload.html')

# ============================================
# 4. Member Portal Dashboard View
# ==========================================
class MemberPortalDashboardView(LoginRequiredMixin, View):
    login_url = '/login/'

    def get(self, request, *args, **kwargs):
        try:
            profile = MemberProfile.objects.get(user=request.user)
        except MemberProfile.DoesNotExist:
            profile = None

        contributions = None
        total_contributions = 0
        announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')
        loans = None

        savings_count = 0
        max_loan_limit = 0
        is_eligible_for_loan = False
        eligible_guarantors = []

        if profile and profile.is_approved:
            contributions = Contribution.objects.filter(profile=profile).order_by('-date_paid')
            savings_count = contributions.count()
            total_contributions = contributions.aggregate(Sum('amount'))['amount__sum'] or 0
            loans = LoanRequest.objects.filter(profile=profile).order_by('-date_applied')

            # Rule: Must have saved 6 times and at least KSh 1,200
            if savings_count >= 6 and total_contributions >= 1200:
                is_eligible_for_loan = True
                max_loan_limit = float(total_contributions) * 5

            # Eligible guarantors (Approved members excluding self)
            eligible_guarantors = MemberProfile.objects.filter(
                is_approved=True
            ).exclude(id=profile.id)

        context = {
            'profile': profile,
            'contributions': contributions,
            'total_contributions': total_contributions,
            'announcements': announcements,
            'loans': loans,
            'savings_count': savings_count,
            'is_eligible_for_loan': is_eligible_for_loan,
            'max_loan_limit': max_loan_limit,
            'eligible_guarantors': eligible_guarantors,
        }
        return render(request, 'welfare/member_dashboard.html', context)

    def post(self, request, *args, **kwargs):
        try:
            profile = MemberProfile.objects.get(user=request.user)
        except MemberProfile.DoesNotExist:
            messages.error(request, "Profile not found.")
            return redirect('member_portal')

        action = request.POST.get('action')

        if action == 'update_profile':
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name).strip()
            user.last_name = request.POST.get('last_name', user.last_name).strip()
            user.email = request.POST.get('email', user.email).strip()
            user.save()
            messages.success(request, "Your profile has been updated successfully!")

        elif action == 'apply_loan':
            # Check if member has any defaulted loans
            active_loans = LoanRequest.objects.filter(profile=profile, status='disbursed').all()
            for l in active_loans:
                if l.is_defaulted:
                    messages.error(request, "Loan Denied: You have a defaulted loan past the Nov 1st deadline and are banned from borrowing.")
                    return redirect('member_portal')

            contributions = Contribution.objects.filter(profile=profile)
            savings_count = contributions.count()
            total_contributions = contributions.aggregate(Sum('amount'))['amount__sum'] or 0

            if savings_count < 6 or total_contributions < 1200:
                messages.error(request, "Ineligible: You must have saved at least 6 times and minimum KSh 1,200 to apply for a loan.")
                return redirect('member_portal')

            amount = float(request.POST.get('amount_requested', 0))
            max_limit = float(total_contributions) * 5

            if amount > max_limit:
                messages.error(request, f"Loan amount exceeds your maximum limit of KSh {max_limit:,.2f} (5x your total savings).")
                return redirect('member_portal')

            guarantor_1_id = request.POST.get('guarantor_1')
            guarantor_2_id = request.POST.get('guarantor_2')
            reason = request.POST.get('reason')
            id_front = request.FILES.get('id_front')
            id_back = request.FILES.get('id_back')

            if not guarantor_1_id or not guarantor_2_id or guarantor_1_id == guarantor_2_id:
                messages.error(request, "Please select 2 different eligible guarantors.")
                return redirect('member_portal')

            if not id_front or not id_back:
                messages.error(request, "Please upload both Front and Back photos of your National ID.")
                return redirect('member_portal')

            LoanRequest.objects.create(
                profile=profile,
                amount_requested=amount,
                reason=reason,
                guarantor_1_id=guarantor_1_id,
                guarantor_2_id=guarantor_2_id,
                id_front=id_front,
                id_back=id_back,
                status='pending'
            )
            messages.success(request, "Loan application submitted successfully with guarantors and ID documentation!")

        return redirect('member_portal')

from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class DownloadReceiptPDFView(LoginRequiredMixin, View):
    """
    Generates and downloads a printable PDF receipt for a specific contribution.
    """
    login_url = '/login/'

    def get(self, request, receipt_no, *args, **kwargs):
        try:
            profile = MemberProfile.objects.get(user=request.user)
            contribution = Contribution.objects.get(profile=profile, receipt_no=receipt_no)
        except (MemberProfile.DoesNotExist, Contribution.DoesNotExist):
            messages.error(request, "Contribution receipt not found.")
            return redirect('member_portal')

        # Create PDF in memory
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Header
        p.setFont("Helvetica-Bold", 18)
        p.drawString(100, 750, "WELFARE CONTRIBUTION RECEIPT")
        p.setStrokeColorRGB(0.2, 0.4, 0.8)
        p.line(100, 740, 500, 740)

        # Body Details
        p.setFont("Helvetica", 12)
        p.drawString(100, 700, f"Receipt No: {contribution.receipt_no}")
        p.drawString(100, 680, f"Member Name: {profile.user.get_full_name()}")
        p.drawString(100, 660, f"Member ID: {profile.membership_no}")
        p.drawString(100, 640, f"Period / Month: {contribution.month_for}")
        p.drawString(100, 620, f"Amount Paid: KSh {contribution.amount}")
        p.drawString(100, 600, f"Date Paid: {contribution.date_paid.strftime('%b %d, %Y')}")

        # Footer
        p.setFont("Helvetica-Oblique", 10)
        p.drawString(100, 550, "Thank you for your timely contribution towards the welfare fund.")
        p.drawString(100, 535, "This is an official system-generated receipt.")

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Receipt_{contribution.receipt_no}.pdf"'
        return response
# ============================================
# 5. Year-End Interest Calculation & Distribution Engine
# ============================================
def process_year_end_interest(year, decision, admin_user, remarks=""):
    # 1. Calculate total interest pool for the target year
    loans = LoanRequest.objects.filter(date_disbursed__year=year)
    total_pool = Decimal('0.00')
    
    for loan in loans:
        balance = Decimal(str(loan.current_balance))
        principal = loan.amount_requested
        if balance > principal:
            total_pool += (balance - principal)

    approved_members = MemberProfile.objects.filter(is_approved=True)
    member_count = approved_members.count()

    amount_per_member = Decimal('0.00')
    if member_count > 0 and total_pool > 0:
        amount_per_member = (total_pool / member_count).quantize(Decimal('0.01'))

    # 2. Record Distribution Rule
    distribution, created = AnnualInterestDistribution.objects.update_or_create(
        year=year,
        defaults={
            'total_interest_pool': total_pool,
            'decision': decision,
            'amount_per_member': amount_per_member,
            'remarks': remarks,
            'processed_by': admin_user
        }
    )

    # 3. If decision is DIVIDEND, credit each member's savings ledger automatically
    if decision == 'DIVIDEND' and amount_per_member > 0:
        for member in approved_members:
            receipt_no = f"DIV-{year}-{member.membership_no}"
            Contribution.objects.get_or_create(
                receipt_no=receipt_no,
                defaults={
                    'profile': member,
                    'amount': amount_per_member,
                    'month_for': f"Annual Dividend {year}",
                    'contribution_type': 'INTEREST_DIVIDEND',
                    'recorded_by': admin_user
                }
            )
    return distribution
