"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    https://docs.pulpproject.org/pulpcore/plugins/plugin-writer/index.html
"""

from django.db import models
from pulpcore.app.util import get_domain_pk
from pulpcore.plugin.models import (
    AutoAddObjPermsMixin,
    BaseModel,
    Distribution,
    EncryptedTextField,
)


class UpstreamPulp(BaseModel, AutoAddObjPermsMixin):
    name = models.TextField(db_index=True)
    pulp_domain = models.ForeignKey("Domain", default=get_domain_pk, on_delete=models.PROTECT)

    base_url = models.TextField()
    api_root = models.TextField(default="pulp")
    domain = models.TextField(null=True)

    ca_cert = models.TextField(null=True)
    client_cert = models.TextField(null=True)
    client_key = EncryptedTextField(null=True)
    tls_validation = models.BooleanField(default=True)

    username = EncryptedTextField(null=True)
    password = EncryptedTextField(null=True)

    pulp_label_select = models.TextField(null=True)

    last_updated_timestamps = models.ManyToManyField(Distribution, through="LastUpdatedRecord")

    class Meta:
        unique_together = ("name", "pulp_domain")
        permissions = [
            ("replicate_upstreampulp", "Can start a replication task"),
            ("manage_roles_upstreampulp", "Can manage roles on upstream pulps"),
        ]


class LastUpdatedRecord(BaseModel):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE)
    upstream_pulp = models.ForeignKey(UpstreamPulp, on_delete=models.CASCADE)
    content_last_updated = models.DateTimeField(null=True)
    last_replication = models.DateTimeField()

    class Meta:
        unique_together = ("distribution", "upstream_pulp")
