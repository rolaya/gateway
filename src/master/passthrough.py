'''
The passthrough module contains the PassthroughService. This service uses the GatewayApi
to communicate with the master. 

Created on Sep 24, 2012

@author: fryckbos
'''
import logging
LOGGER = logging.getLogger("openmotics")

import threading
from master_communicator import InMaintenanceModeException
from master_command import printable

class PassthroughService:
    """ The Passthrough service creates two threads: one for reading from and one for writing
    to the master.
    """
    
    def __init__(self, master_communicator, passthrough_serial, verbose=False):
        self.__master_communicator = master_communicator
        self.__passthrough_serial = passthrough_serial
        self.__verbose = verbose
        
        self.__stopped = False
        self.__reader_thread = None
        self.__writer_thread = None
    
    def start(self):
        """ Start the Passthrough service, this launches the two threads. """
        self.__reader_thread = threading.Thread(target=self.__reader)
        self.__reader_thread.setName("Passthrough reader thread")
        self.__reader_thread.daemon = True
        self.__reader_thread.start()
        
        self.__writer_thread = threading.Thread(target=self.__writer)
        self.__writer_thread.setName("Passthrough writer thread")
        self.__writer_thread.daemon = True
        self.__writer_thread.start()
        

    def __reader(self):
        """ Reads from the master and writes to the passthrough serial. """
        while not self.__stopped:
            data = self.__master_communicator.get_passthrough_data()
            if data and len(data) > 0:
                if self.__verbose:
                    LOGGER.info("Data for passthrough: %s" % printable(data))
                self.__passthrough_serial.write(data)
    
    def __writer(self):
        """ Reads from the passthrough serial and writes to the master. """
        while not self.__stopped:
            data = self.__passthrough_serial.read(1)
            if data and len(data) > 0:
                num_bytes = self.__passthrough_serial.inWaiting()
                if num_bytes > 0:
                    data += self.__passthrough_serial.read(num_bytes)
                try:
                    if self.__verbose:
                        LOGGER.info("Data from passthrough: %s" % printable(data))
                    self.__master_communicator.send_passthrough_data(data)
                except InMaintenanceModeException:
                    LOGGER.info("Dropped passthrough communication in maintenance mode.")
    
    def stop(self):
        """ Stop the Passthrough service. """
        self.__stopped = True
