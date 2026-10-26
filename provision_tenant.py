import os
import django

# Initialize the Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from customers.models import Client, Domain

def provision_jabstir():
    print("--- Starting Tenant Provisioning ---")
    
    # 1. Create the tenant client (This triggers Postgres to create the 'jabstir' schema)
    tenant, created = Client.objects.get_or_create(
        schema_name='jabstir',
        name='Jabstir Welfare Group'
    )
    
    if created:
        print(f"Created tenant: {tenant.name} with schema: {tenant.schema_name}")
    else:
        print(f"Tenant '{tenant.name}' already exists.")

    # 2. Bind the local routing domain (e.g., jabstir.localhost)
    domain, domain_created = Domain.objects.get_or_create(
        domain='jabstir.localhost',
        tenant=tenant,
        is_primary=True
    )
    
    if domain_created:
        print(f"Bound domain '{domain.domain}' to {tenant.name}.")
    else:
        print(f"Domain '{domain.domain}' is already registered.")
        
    print("--- Provisioning Complete! ---")

if __name__ == "__main__":
    provision_jabstir()
