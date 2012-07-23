# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
Contains package (RPM) management section and commands.
"""

import time
from gettext import gettext as _
from command import PollingCommand
from pulp.client.extensions.extensions import PulpCliSection
from pulp.bindings.exceptions import NotFoundException

TYPE_ID = 'rpm'

class PackageSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(
            self,
            'package',
            _('package installation management'))
        for Command in (Install, Update, Uninstall):
            command = Command(context)
            command.create_option(
                '--id',
                _('identifies the consumer'),
                required=True)
            command.create_flag(
                '--no-commit',
                _('transaction not committed'))
            command.create_flag(
                '--reboot',
                _('reboot after successful transaction'))
            self.add_command(command)


class Install(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'install',
            _('install packages'),
            self.run)
        self.create_option(
            '--name',
            _('package name; may repeat for multiple packages'),
            required=True,
            allow_multiple=True,
            aliases=['-n'])
        self.create_flag(
            '--import-keys',
            _('import GPG keys as needed'))
        self.context = context

    def run(self, **kwargs):
        id = kwargs['id']
        apply = (not kwargs['no-commit'])
        importkeys = kwargs['import-keys']
        reboot = kwargs['reboot']
        units = []
        options = dict(
            apply=apply,
            importkeys=importkeys,
            reboot=reboot,)
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.install(id, units, options)

    def install(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.install(id, units=units, options=options)
            task = response.response_body
            msg = _('Install task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Install failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Install Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        filter = ['name', 'version', 'arch', 'repoid']
        resolved = details['resolved']
        if resolved:
            prompt.render_title('Installed')
            prompt.render_document_list(
                resolved,
                order=filter,
                filters=filter)
        else:
            msg = 'Packages already installed'
            prompt.render_success_message(_(msg))
        deps = details['deps']
        if deps:
            prompt.render_title('Installed for dependency')
            prompt.render_document_list(
                deps,
                order=filter,
                filters=filter)


class Update(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'update',
            _('update (installed) packages'),
            self.run)
        self.create_option(
            '--name',
            _('package name; may repeat for multiple packages'),
            required=False,
            allow_multiple=True,
            aliases=['-n'])
        self.create_flag(
            '--import-keys',
            _('import GPG keys as needed'))
        self.create_flag(
            '--all',
            _('update all packages'),
            aliases=['-a'])
        self.context = context

    def run(self, **kwargs):
        id = kwargs['id']
        all = kwargs['all']
        names = kwargs['name']
        apply = (not kwargs['no-commit'])
        importkeys = kwargs['import-keys']
        reboot = kwargs['reboot']
        units = []
        options = dict(
            all=all,
            apply=apply,
            importkeys=importkeys,
            reboot=reboot,)
        if all: # ALL
            unit = dict(type_id=TYPE_ID, unit_key=None)
            self.update(id, [unit], options)
            return
        if names is None:
            names = []
        for name in names:
            unit_key = dict(name=name)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.update(id, units, options)

    def update(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        if not units:
            msg = 'No packages specified'
            prompt.render_failure_message(_(msg))
            return
        try:
            response = server.consumer_content.update(id, units=units, options=options)
            task = response.response_body
            msg = _('Update task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Install failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Install Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        filter = ['name', 'version', 'arch', 'repoid']
        resolved = details['resolved']
        if resolved:
            prompt.render_title('Updated')
            prompt.render_document_list(
                resolved,
                order=filter,
                filters=filter)
        else:
            msg = 'No updates needed'
            prompt.render_success_message(_(msg))
        deps = details['deps']
        if deps:
            prompt.render_title('Installed for dependency')
            prompt.render_document_list(
                deps,
                order=filter,
                filters=filter)


class Uninstall(PollingCommand):

    def __init__(self, context):
        PollingCommand.__init__(
            self,
            'uninstall',
            _('uninstall packages'),
            self.run)
        self.create_option(
            '--name',
            _('package name; may repeat for multiple packages'),
            required=True,
            allow_multiple=True,
            aliases=['-n'])
        self.context = context

    def run(self, **kwargs):
        id = kwargs['id']
        apply = (not kwargs['no-commit'])
        reboot = kwargs['reboot']
        units = []
        options = dict(
            apply=apply,
            reboot=reboot,)
        for name in kwargs['name']:
            unit_key = dict(name=name)
            unit = dict(type_id=TYPE_ID, unit_key=unit_key)
            units.append(unit)
        self.uninstall(id, units, options)

    def uninstall(self, id, units, options):
        prompt = self.context.prompt
        server = self.context.server
        try:
            response = server.consumer_content.uninstall(id, units=units, options=options)
            task = response.response_body
            msg = _('Uninstall task created with id [%s]') % task.task_id
            prompt.render_success_message(msg)
            response = server.tasks.get_task(task.task_id)
            task = response.response_body
            if self.rejected(task):
                return
            if self.postponed(task):
                return
            self.process(id, task)
        except NotFoundException:
            msg = _('Consumer [%s] not found') % id
            prompt.write(msg, tag='not-found')

    def succeeded(self, id, task):
        prompt = self.context.prompt
        # reported as failed
        if not task.result['status']:
            msg = 'Install Failed'
            details = task.result['details'][TYPE_ID]['details']
            prompt.render_failure_message(_(msg))
            prompt.render_failure_message(details['message'])
            return
        msg = 'Install Succeeded'
        prompt.render_success_message(_(msg))
        # reported as succeeded
        details = task.result['details'][TYPE_ID]['details']
        filter = ['name', 'version', 'arch', 'repoid']
        resolved = details['resolved']
        if resolved:
            prompt.render_title('Uninstalled')
            prompt.render_document_list(
                resolved,
                order=filter,
                filters=filter)
        else:
            msg = 'No matching packages found to uninstall'
            prompt.render_success_message(_(msg))
        deps = details['deps']
        if deps:
            prompt.render_title('Uninstalled for dependency')
            prompt.render_document_list(
                deps,
                order=filter,
                filters=filter)
