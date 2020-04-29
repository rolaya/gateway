# Copyright (C) 2020 OpenMotics BV
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
This module contains ORM sync logic
"""

from __future__ import absolute_import
import logging

from ioc import Inject, INJECTED
from gateway.hal.master_event import MasterEvent
from gateway.hal.master_controller import MasterController
from gateway.models import Output, Input, Sensor

logger = logging.getLogger("openmotics")


class ORMSyncer(object):

    @staticmethod
    def handle_master_event(master_event):  # type: (MasterEvent) -> None
        if master_event.type == MasterEvent.Types.EEPROM_CHANGE:
            ORMSyncer.sync()

    @staticmethod
    @Inject
    def sync(master_controller=INJECTED):  # type: (MasterController) -> None
        """
        Synchronizes the Master state with the ORM and thus only happens for data where
        the master is source of truth. For example, the amount of physical outputs connected
        """
        logger.info('Sync ORM with Master/Core reality')

        for orm_model, name, filter_ in [(Output, 'output', lambda o: True),
                                         (Input, 'input', lambda i: i.module_type in ['i', 'I']),
                                         (Sensor, 'sensor', lambda s: True)]:
            logger.info('* {0}s'.format(orm_model.__name__))
            ids = []
            for dto in getattr(master_controller, 'load_{0}s'.format(name))():
                if not filter_(dto):
                    continue
                id_ = dto.id
                ids.append(id_)
                orm_model.get_or_create(number=id_)  # type: ignore
            orm_model.delete().where(orm_model.number.not_in(ids)).execute()  # type: ignore

        logger.info('Sync ORM completed')
