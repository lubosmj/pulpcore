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

    1. A signing script with a certain input and output format is created, for example::

        #!/usr/bin/env bash

        FILE_PATH=$1
        SIGNATURE_PATH="$1.asc"
        PUBLIC_KEY_PATH="public.key"

        ADMIN_ID="27B3E8915B0C58FB"
        PASSWORD="password"

        # Export a public key
        gpg --armor --export admin@example.com > $PUBLIC_KEY_PATH

        # Create a detached signature for the file
        gpg --quiet --batch --pinentry-mode loopback --yes --passphrase \
            $PASSWORD --homedir ~/.gnupg/ --detach-sign --default-key $ADMIN_ID \
            --armor --output $SIGNATURE_PATH $FILE_PATH

        STATUS=$?
        if [ $STATUS -eq 0 ]; then
            echo {\"file\": \"$FILE_PATH\", \"signature\": \"$SIGNATURE_PATH\", \
                \"key\": \"$PUBLIC_KEY_PATH\"}
        else
            exit $STATUS
        fi

    2. A path to the script and a meaningful name describing the script's purpose is created in a
       database leveraging the django-admin shell_plus utility::

        from pulpcore.app.models.content import SigningService

        SigningService.objects.create(
            name="sign-metadata",
            script="/var/lib/pulp/scripts/sign-metadata.sh"
        )

Plugin writers may sign content by leveraging the given script. Then, a user can verify the content
with an associated public key provided by an administrator. Both document and the signature are
required to verify the signature::

        gpg --import /var/lib/pulp/gpg-home/public.key
        gpg --verify filename.asc filename
