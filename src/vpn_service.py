#!/usr/bin/env python
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
from __future__ import absolute_import

import argparse
import logging

from gateway.settings import setup_global_arguments
from openmotics_cli import service

logger = logging.getLogger('openmotics')


@service('vpn_service')
def vpn_service(args):
    # type: (argparse.Namespace) -> None
    logger.info('Starting VPN service')

    from gateway.services.vpn import VPNService
    vpn_service = VPNService()
    vpn_service.start()


def main():
    # type: () -> None
    parser = argparse.ArgumentParser()
    setup_global_arguments(parser)
    args = parser.parse_args()
    vpn_service(args)


if __name__ == '__main__':
    main()
