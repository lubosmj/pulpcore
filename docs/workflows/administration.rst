Administration
==============

Administrators are responsible for managing content. While manipulating the content, a small
mistake may have undesired consequences. This section contains instructions which enable
superusers to effectively administer the system.

Signing Content
---------------
The users who consume content through Pulp shall not be endangered by common security threats.
Because of that, there is a feature which helps administrators to manage signing scripts. These
scripts can be used afterwards by plugin writers in order to sign and protect the content
from being forged.

The following procedure should be considered for administrators:

    1. A signing script with a certain input and output format is created::

        #!/usr/bin/python3

        import os, subprocess, sys

        repo_id = os.environ.get("GPG_REPOSITORY_NAME", "")
        key_id = "my-devel-key" if repo_id.endswith("-devel") else "my-key"

        fname = sys.argv[1]

        cmd = ["/usr/bin/gpg", "--homedir", "/var/lib/pulp/gpg-home",
               "--detach-sign", "--default-key", key_id, "--armor",
               "--output", fname + ".asc", fname]

        sys.exit(subprocess.call(cmd))

    2. A path to the script and a meaningful name describing the script's purpose is created in a
       database leveraging the django-admin shell_plus utility::

        from pulpcore.app.models.content import SigningService

        SigningService.objects.create(
            name="sign-metadata",
            script="/var/lib/pulp/scripts/sign-metadata.sh"
        )

Plugin writers utilize signing scripts.
