import csv
import io
from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from .models import (
    RegistrationFormSection,
    RegistrationFormField,
    MemberProfile,
    WelfareGroupSettings,
    Contribution,
    Announcement,
    LoanRequest,
    AnnualInterestDistribution
)
from .importers import import_members_from_file

# Form to handle spreadsheet file uploads
class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label="Select Excel or CSV member list")


# Inline to allow admins to manage fields directly inside a Form Section
class RegistrationFormFieldInline(admin.TabularInline):
    model = RegistrationFormField
    extra = 1
    prepopulated_fields = {"field_name_slug": ("field_label",)}


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'is_active', 'created_at')
    list_filter = ('is_active', 'priority')
    search_fields = ('title', 'content')

    def log_addition(self, request, object, message):
        pass

    def log_change(self, request, object, message):
        pass

    def log_deletion(self, request, object, object_repr):
        pass


@admin.register(RegistrationFormSection)
class RegistrationFormSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
    inlines = [RegistrationFormFieldInline]


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ('profile', 'amount_requested', 'status', 'date_applied')
    list_filter = ('status', 'date_applied')
    search_fields = ('profile__membership_no', 'reason')

    def log_addition(self, request, object, message):
        pass

    def log_change(self, request, object, message):
        pass

    def log_deletion(self, request, object, object_repr):
        pass


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'amount', 'month_for', 'contribution_type', 'receipt_no', 'date_paid')
    search_fields = ('profile__membership_no', 'receipt_no', 'month_for')
    list_filter = ('contribution_type', 'date_paid')

    # Prevent tenant schema content_type mismatch when writing admin log entries
    def log_addition(self, request, object, message):
        pass

    def log_change(self, request, object, message):
        pass

    def log_deletion(self, request, object, object_repr):
        pass

    # Custom URLs for Bulk CSV Contribution Upload and Year-End Interest Processing
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/', self.admin_site.admin_view(self.bulk_upload_view), name='welfare_contribution_bulk_upload'),
            path('process-year-end/', self.admin_site.admin_view(self.year_end_processing_view), name='welfare_year_end_processing'),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        if request.method == 'POST' and request.FILES.get('csv_file'):
            csv_file = request.FILES['csv_file']
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a valid CSV file.')
                return redirect('admin:welfare_contribution_changelist')

            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.reader(io_string)
            next(reader, None)  # Skip header row

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

            messages.success(request, f"Successfully imported {success_count} contributions from CSV!")
            return redirect('admin:welfare_contribution_changelist')

        context = dict(
            self.admin_site.each_context(request),
            title="Bulk Upload Contributions (CSV)"
        )
        return render(request, 'welfare/admin_bulk_upload.html', context)

    def year_end_processing_view(self, request):
        if request.method == 'POST':
            year = int(request.POST.get('year', 2026))
            decision = request.POST.get('decision')
            remarks = request.POST.get('remarks', '')

            # 1. Calculate Interest Pool
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

            # 2. Save Rule
            AnnualInterestDistribution.objects.update_or_create(
                year=year,
                defaults={
                    'total_interest_pool': total_pool,
                    'decision': decision,
                    'amount_per_member': amount_per_member,
                    'remarks': remarks,
                    'processed_by': request.user
                }
            )

            # 3. Distribute if DIVIDEND chosen
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
                            'recorded_by': request.user
                        }
                    )
            messages.success(request, f"Year-end interest successfully processed for {year}!")
            return redirect('admin:welfare_contribution_changelist')

        context = dict(
            self.admin_site.each_context(request),
            title="Year-End Interest Distribution Engine"
        )
        return render(request, 'welfare/admin_year_end.html', context)


@admin.register(RegistrationFormField)
class RegistrationFormFieldAdmin(admin.ModelAdmin):
    list_display = ('field_label', 'field_name_slug', 'field_type', 'is_required', 'section', 'order')
    list_filter = ('field_type', 'is_required', 'section')
    search_fields = ('field_label', 'field_name_slug')


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('membership_no', 'user', 'is_approved', 'get_joined_date')
    list_filter = ('is_approved', 'user__date_joined')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'membership_no')
    change_list_template = "admin/memberprofile_changelist.html"

    def get_joined_date(self, obj):
        return obj.user.date_joined
    get_joined_date.short_description = 'Joined Date'
    get_joined_date.admin_order_field = 'user__date_joined'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel), name='import_excel'),
        ]
        return custom_urls + urls

    def import_excel(self, request):
        if request.method == "POST":
            form = ExcelUploadForm(request.POST, request.FILES)
            if form.is_valid():
                uploaded_file = request.FILES['excel_file']
                try:
                    success_count, errors = import_members_from_file(
                        uploaded_file, 
                        uploaded_file.name
                    )

                    if success_count > 0:
                        self.message_user(
                            request, 
                            f"Successfully imported {success_count} members!", 
                            level=messages.SUCCESS
                        )
                    if errors:
                        for err in errors:
                            self.message_user(request, err, level=messages.WARNING)

                    return redirect("..")
                except Exception as e:
                    self.message_user(request, f"Failure executing upload: {str(e)}", level=messages.ERROR)
                    return redirect("..")
        else:
            form = ExcelUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "title": "Bulk Upload Member List"
        }
        return render(request, "admin/excel_upload_form.html", context)


@admin.register(WelfareGroupSettings)
class WelfareGroupSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'currency', 
        'monthly_contribution_amount', 
        'savings_allocation', 
        'welfare_allocation',
    )


@admin.register(AnnualInterestDistribution)
class AnnualInterestDistributionAdmin(admin.ModelAdmin):
    list_display = ('year', 'total_interest_pool', 'decision', 'amount_per_member', 'processed_at')
    list_filter = ('decision', 'year')
