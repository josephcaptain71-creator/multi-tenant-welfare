# Multi-Tenant Welfare Management System

A robust Django-based web application designed to handle multi-tenant welfare groups, member savings, automated loan eligibility, bulk contribution uploads, and year-end interest distributions.

## Key Features
- **Multi-Tenant Architecture**: Schema or group-level data isolation for different welfare groups.
- **Bulk Contribution Upload**: CSV upload engine for seamless batch recording of member contributions.
- **Automated Loan Engine**: Real-time eligibility evaluation (6+ contributions and minimum savings threshold) with dynamic loan multipliers (5x savings limit).
- **Guarantor & Verification Support**: Member loan applications with guarantor selection and National ID document uploads.
- **Year-End Interest Engine**: Calculate annual accrued loan interest and distribute as dividends or retain for group welfare events.
- **Member Portal**: Intuitive dashboard displaying savings, receipts, dividend history, and printable PDF statements.

## Tech Stack
- **Backend**: Python 3.12, Django 6.0
- **Database**: SQLite (Development) / PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript (Django Templates)

## Setup & Running
1. Clone the repository:
   \`\`\`bash
   git clone https://github.com/josephcaptain71-creator/multi-tenant-welfare.git
   cd multi-tenant-welfare
   \`\`\`
2. Activate virtual environment and install requirements:
   \`\`\`bash
   source venv/bin/activate
   pip install -r requirements.txt
   \`\`\`
3. Run migrations and start server:
   \`\`\`bash
   python manage.py migrate
   python manage.py runserver 0.0.0.0:8000
   \`\`\`
