# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains the definitions for all classes related to the importer's API for
interacting with the Pulp server during a repo sync.
"""

from gettext import gettext as _
import logging
import os
import sys

from pulp.server.constants import LOCAL_STORAGE

# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions --------------------------------------------------------------

class RepoSyncConduitException(Exception):
    """
    General exception that wraps any server exception coming out of a conduit
    call.
    """
    pass

# -- classes -----------------------------------------------------------------

class RepoSyncConduit:
    """
    Used to communicate back into the Pulp server while an importer performs
    a repo sync. Instances of this class should *not* be cached between repo
    sync runs. Each sync will be issued its own conduit instance that is scoped
    to that sync alone.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize its sync process.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, repo_id, repo_association_manager, progress_callback=None):
        """
        @param repo_id: identifies the repo being synchronized
        @type  repo_id: str

        @param repo_association_manager: server manager instance for manipulating
                   repo to content unit associations
        @type  repo_association_manager: L{RepoUnitAssociationManager}

        @param progress_callback: used to update the server's knowledge of the
                   sync progress
        @type  progress_callback: ?
        """
        self.repo_id = repo_id

        self.__association_manager = repo_association_manager
        self.__progress_callback = progress_callback

    def __str__(self):
        return _('RepoSyncConduit for repository [%(r)s]') % {'r' : self.repo_id}

    # -- public ---------------------------------------------------------------

    def set_progress(self, current_step, total_steps, message):
        """
        Informs the server of the current state of the sync operation. The
        granularity of what a "step" is is dependent on how the importer
        implementation chooses to divide up the sync process.

        If the step data being set is invalid, this method will do nothing. No
        error will be thrown in the case of invalid step data.

        @param current_step: indicates where in the total process the sync is;
                             must be less than total_steps, greater than 0
        @type  current_step: int

        @param total_steps: indicates how much total work is needed; must be
                            greater than 0
        @type  total_steps: int

        @param message: message to make available to the user describing where
                        in the sync process the actual sync run is
        @type  message: str
        """

        # Validation
        if current_step < 1 or total_steps < 1 or current_step > total_steps:
            _LOG.warn('Invalid step data [current: %d, total: %d], set_progress aborting' % (current_step, total_steps))
            return

        # TODO: add hooks into tasking subsystem

        _LOG.info('Progress for repo [%s] sync: %s - %d/%d' % (self.repo_id, message, current_step, total_steps))

    def request_unit_filename(self, relative_path):
        """
        Requests the server translate the relative location of where a content
        unit should be stored into a full path on the local filesystem.

        @param relative_path: the path, as determined by the importer, where the
                              content unit should be stored
        @type  relative_path: str

        @return: absolute path where to store the unit
        @rtype:  str
        """

        # Ultimately Pulp may do something more fancy, but for now simply stuff
        # the relative path onto the local storage directory

        path = os.path.join(LOCAL_STORAGE, relative_path)
        return path

    def add_or_update_content_unit(self, type_id, unit_key, standard_unit_data, custom_unit_data):
        """
        Informs the server of a link between a content unit and the repo being
        syncced. This call does not distinguish between adding a new unit to
        the server v. updating an existing one; the server will resolve those
        distinctions. What this call does is ensure that a link exists between
        the repo being syncced and the given content unit.

        If the content unit already exists in the database (as determined by the
        pairing of type_id and unit_key), its metadata will be updated with the
        contents of standard_unit_data and custom_unit_data passed into this call.

        @param type_id: identifies the type of unit being added; this value must
                        be present in the server at the time of this call or an
                        error will be raised
        @type  type_id: str

        @param unit_key: key/value pairs uniquely identifying this unit from all
                         other units of the same type; the keys in here must
                         match the unique indexes defined in the type definition
        @type  unit_key: dict

        @param standard_unit_data: key/value pairs providing the required set of
                         metadata for describing a content unit
        @type  standard_unit_data: dict

        @param custom_unit_data: key/value pairs describing any type-specific
                         metadata for the content unit; no validation will be
                         performed on the data included here
        @type  custom_unit_data: dict
        """
        pass

    def associate_content_unit(self, type_id, unit_key):
        """
        Creates a relationship between the repo being synchronized and the
        content unit identified by the given key. The unit must have been
        previously added to the server through the add_or_update_content_unit
        call.

        @param type_id: identifies the type of content unit being associated
        @type  type_id: str

        @param unit_key: identifies the content unit itself
        @type  unit_key: dict
        """
        try:
            self.__association_manager.associate_unit_by_key(self.repo_id, type_id, unit_key)
        except:
            _LOG.exception(_('Content unit association failed'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def unassociate_content_unit(self, type_id, unit_key):
        """
        Unassociates the given content unit from the repo being syncced. The
        unit is not deleted from the server's database. If for some reason the
        content unit is not associated with the repo, this call has no effect.

        @param type_id: identifies the type of unit being associated
        @type  type_id: str

        @param unit_key: key/value pairs uniquely identifying this unit from all
                         other units of the same type; the keys in here must
                         match the unique indexes defined in the type definition
        @type  unit_key: dict
        """
        try:
            self.__association_manager.unassociate_unit_by_key(self.repo_id, type_id, unit_key)
        except:
            _LOG.exception(_('Content unit unassociation failed'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def get_unit_keys_for_repo(self, type_id=None):
        """
        Returns a list of keys for units associated with the repo being
        synchronized. This can be used to determine units that were once
        associated but were not present in the latest sync.

        @param type_id: optional; if specified, only keys for units of the  
        """
        try:
            self.__association_manager.unit_keys_for_repo(self.repo_id)
        except:
            raise RepoSyncConduitException(), None, sys.exc_info()[2]
