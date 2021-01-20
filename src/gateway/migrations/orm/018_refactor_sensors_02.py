# Copyright (C) 2021 OpenMotics BV
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

from peewee import (
    Model, Database, SqliteDatabase,
    AutoField, CharField, IntegerField,
    ForeignKeyField, FloatField
)
from peewee_migrate import Migrator
import constants

if False:  # MYPY
    from typing import Dict, Any


def migrate(migrator, database, fake=False, **kwargs):
    # type: (Migrator, Database, bool, Dict[Any, Any]) -> None

    class BaseModel(Model):
        class Meta:
            database = SqliteDatabase(constants.get_gateway_database_file(),
                                      pragmas={'foreign_keys': 1})

    class Floor(BaseModel):
        id = AutoField()
        number = IntegerField(unique=True)
        name = CharField(null=True)

    class Room(BaseModel):
        id = AutoField()
        number = IntegerField(unique=True)
        name = CharField(null=True)
        floor = ForeignKeyField(Floor, null=True, on_delete='SET NULL', backref='rooms')

    class Plugin(BaseModel):
        id = AutoField()
        name = CharField(unique=True)
        version = CharField()

    class Sensor(BaseModel):
        id = AutoField()
        number = IntegerField(unique=True)
        room = ForeignKeyField(Room, null=True, on_delete='SET NULL', backref='sensors')
        type = CharField(null=True)
        source = CharField(null=True)
        plugin = ForeignKeyField(Plugin, null=True, on_delete='CASCADE')
        external_id = CharField(null=True)
        name = CharField(null=True)
        offset = FloatField(null=True)

    # Basic data migration
    for sensor in Sensor.select():
        external_id = str(sensor.number)
        sensor.external_id = external_id
        sensor.type = 'temperature'
        sensor.source = 'master'
        sensor.offset = 0
        sensor.save()
        Sensor.create(external_id=external_id,
                      number=sensor.number + 100,
                      type='humidity',
                      source='master',
                      room=sensor.room,
                      offset=0)
        Sensor.create(external_id=external_id,
                      number=sensor.number + 200,
                      type='brightness',
                      source='master',
                      room=sensor.room,
                      offset=0)

    # Further schema migrations
    migrator.add_not_null(Sensor, *['type', 'source', 'external_id', 'offset'])
    migrator.drop_columns(Sensor, *['number'])
    migrator.add_index(Sensor, *['source', 'plugin_id', 'external_id'], unique=True)


def rollback(migrator, database, fake=False, **kwargs):
    # type: (Migrator, Database, bool, Dict[Any, Any]) -> None
    pass
