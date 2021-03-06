# Copyright (C) 2018 OpenMotics BV
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
PulseCounter BLL
"""
from __future__ import absolute_import
import logging
import time
from peewee import fn, DoesNotExist, JOIN
from ioc import Injectable, Inject, INJECTED, Singleton
from serial_utils import CommunicationTimedOutException
from gateway.base_controller import BaseController
from gateway.dto import PulseCounterDTO
from gateway.models import PulseCounter, Room
from gateway.mappers import PulseCounterMapper

if False:  # MYPY
    from typing import List, Tuple, Dict, Optional

logger = logging.getLogger("openmotics")


@Injectable.named('pulse_counter_controller')
@Singleton
class PulseCounterController(BaseController):

    @Inject
    def __init__(self, master_controller=INJECTED):
        super(PulseCounterController, self).__init__(master_controller)
        self._counts = {}  # type: Dict[int, int]

    def _sync_orm(self):
        if self._sync_running:
            logger.info('ORM sync (PulseCounter): Already running')
            return False
        self._sync_running = True

        start = time.time()
        logger.info('ORM sync (PulseCounter)')

        try:
            for pulse_counter_dto in self._master_controller.load_pulse_counters():
                pulse_counter_id = pulse_counter_dto.id
                pulse_counter = PulseCounter.get_or_none(number=pulse_counter_id)
                if pulse_counter is None:
                    pulse_counter = PulseCounter(number=pulse_counter_id,
                                                 name='PulseCounter {0}'.format(pulse_counter_id),
                                                 source='master',
                                                 persistent=False)
                    pulse_counter.save()
            duration = time.time() - start
            logger.info('ORM sync (PulseCounter): completed after {0:.1f}s'.format(duration))
        except CommunicationTimedOutException as ex:
            logger.error('ORM sync (PulseCounter): Failed: {0}'.format(ex))
        except Exception:
            logger.exception('ORM sync (PulseCounter): Failed')
        finally:
            self._sync_running = False

        return True

    def load_pulse_counter(self, pulse_counter_id):  # type: (int) -> PulseCounterDTO
        pulse_counter = PulseCounter.select(PulseCounter, Room) \
                                    .join_from(PulseCounter, Room, join_type=JOIN.LEFT_OUTER) \
                                    .where(PulseCounter.number == pulse_counter_id) \
                                    .get()  # type: PulseCounter  # TODO: Load dict
        if pulse_counter.source == 'master':
            pulse_counter_dto = self._master_controller.load_pulse_counter(pulse_counter_id=pulse_counter_id)
            pulse_counter_dto.room = pulse_counter.room.number if pulse_counter.room is not None else None
        else:
            pulse_counter_dto = PulseCounterMapper.orm_to_dto(pulse_counter)
        return pulse_counter_dto

    def load_pulse_counters(self):  # type: () -> List[PulseCounterDTO]
        pulse_counter_dtos = []
        for pulse_counter in list(PulseCounter.select(PulseCounter, Room)
                                              .join_from(PulseCounter, Room, join_type=JOIN.LEFT_OUTER)):  # TODO: Load dicts
            if pulse_counter.source == 'master':
                pulse_counter_dto = self._master_controller.load_pulse_counter(pulse_counter_id=pulse_counter.number)
                pulse_counter_dto.room = pulse_counter.room.number if pulse_counter.room is not None else None
                pulse_counter_dto.name = pulse_counter.name  # Use longer ORM name
            else:
                pulse_counter_dto = PulseCounterMapper.orm_to_dto(pulse_counter)
            pulse_counter_dtos.append(pulse_counter_dto)
        return pulse_counter_dtos

    def save_pulse_counters(self, pulse_counters):  # type: (List[Tuple[PulseCounterDTO, List[str]]]) -> None
        pulse_counters_to_save = []
        for pulse_counter_dto, fields in pulse_counters:
            pulse_counter = PulseCounter.get_or_none(number=pulse_counter_dto.id)  # type: PulseCounter
            if pulse_counter is None:
                raise DoesNotExist('A PulseCounter with id {0} could not be found'.format(pulse_counter_dto.id))
            if pulse_counter.source == 'master':
                # Only master pulse counters will be passed to the MasterController batch save
                pulse_counters_to_save.append((pulse_counter_dto, fields))
                if 'name' in fields:
                    pulse_counter.name = pulse_counter_dto.name
            elif pulse_counter.source == 'gateway':
                pulse_counter = PulseCounterMapper.dto_to_orm(pulse_counter_dto, fields)
            else:
                logger.warning('Trying to save a PulseCounter with unknown source {0}'.format(pulse_counter.source))
                continue
            if 'room' in fields:
                if pulse_counter_dto.room is None:
                    pulse_counter.room = None
                elif 0 <= pulse_counter_dto.room <= 100:
                    pulse_counter.room, _ = Room.get_or_create(number=pulse_counter_dto.room)
            pulse_counter.save()
        self._master_controller.save_pulse_counters(pulse_counters_to_save)

    def set_amount_of_pulse_counters(self, amount):  # type: (int) -> int
        _ = self
        # This does not make a lot of sense in an ORM driven implementation, but is for legacy purposes.
        # The legacy implementation heavily depends on the number (legacy id) and the fact that there should be no
        # gaps between them. If there are gaps, legacy upstream code will most likely break.
        # TODO: Fix legacy implementation once the upstream can manage this better

        amount_of_master_pulse_counters = PulseCounter.select().where(PulseCounter.source == 'master').count()
        if amount < amount_of_master_pulse_counters:
            raise ValueError('Amount should be >= {0}'.format(amount_of_master_pulse_counters))

        # Assume amount is 27:
        # - This means n master driven PulseCounters
        # - This means 27-n gateway driven PulseCounters
        # The `number` field will contain 0-(n-1) (zero-based counting), this means that any
        # number above or equal to the amount can be removed (>= n)

        PulseCounter.delete().where(PulseCounter.number >= amount).execute()
        for number in range(amount_of_master_pulse_counters, amount):
            pulse_counter = PulseCounter.get_or_none(number=number)
            if pulse_counter is None:
                pulse_counter = PulseCounter(number=number,
                                             name='PulseCounter {0}'.format(number),
                                             source='gateway',
                                             persistent=False)
                pulse_counter.save()
        return amount

    def get_amount_of_pulse_counters(self):  # type: () -> int
        _ = self
        return PulseCounter.select(fn.Max(PulseCounter.number)).scalar() + 1

    def set_value(self, pulse_counter_id, value):  # type: (int, int) -> int
        pulse_counter = PulseCounter.get(number=pulse_counter_id)
        if pulse_counter.source == 'master':
            raise ValueError('Cannot set pulse counter value for a Master controlled PulseCounter')
        self._counts[pulse_counter_id] = value
        return value

    def get_values(self):  # type: () -> Dict[int, Optional[int]]
        pulse_counter_values = {}  # type: Dict[int, Optional[int]]
        pulse_counter_values.update(self._master_controller.get_pulse_counter_values())
        for pulse_counter in PulseCounter.select().where(PulseCounter.source == 'gateway'):
            pulse_counter_values[pulse_counter.number] = self._counts.get(pulse_counter.number)
        return pulse_counter_values

    def get_persistence(self):  # type: () -> Dict[int, bool]
        _ = self
        return {pulse_counter.number: pulse_counter.persistent for pulse_counter
                in PulseCounter.select()}
