from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    """
    Represents an independent welfare organization (e.g., Jabstir Welfare Group).
    Creating a record here automatically instructs PostgreSQL to spawn a new isolated schema.
    """
    name = models.CharField(max_length=100)
    created_on = models.DateField(auto_now_add=True)

    # When True, creating a client instance dynamically provisions the Postgres schema
    auto_create_schema = True

    def __str__(self):
        return f"{self.name} (Schema: {self.schema_name})"


class Domain(DomainMixin):
    """
    Maps the tenant to a subdomain (e.g., 'jabstir.localhost' or 'magharibi.localhost')
    so the router middleware directs traffic to the correct schema.
    """
    pass
