# -*- coding: utf-8 -*-

# MultiChain Feed Adapter (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license


import cfg
import utils
import readconf

class AdapterOutput(cfg.BaseOutput):
    """ User defined output template class. """
 
    def initialize(self):
        """
            Class initialization.
            This class is implemented to do nothing except updating feed read pointer.
            Updating feed read pointer is required, otherwise adapter will try to
            send records to this class infinitely.
            Feed read pointer is stored in the file in this template.
    
            The following operations should be performed in this method:
            
            1. Check all required fields in .ini file are present
               Set default values if needed.
            2. Read feed read pointer.
            3. Make custom intitializations if necessary.
        """
    
        if not readconf.check_file_config(self.config):
            return False

        self.pointer=utils.read_file_ptr(self.config)
                        
        return True
 
        
    def write(self, records, ptr):
        """
            Writing feed data to this output.
            
            records - list of record objects:
            {
                'code'   : <event code> # see multichain.py for the list of events
                'length' : record length
                'data'   : record data
            }
            
            Use feed.parse_record(record) to parse the record. Ot returns list of fields:
            {
                'code'   : <field code> # see multichain.py for the list of fields and field types
                'length' : field length
                'value'  : field value
                    bytes for binary fields
                    string for other types
                'intvalue' : integer field value for integer and timestamp fields
            }
                       
            ptr - feed read pointer - tuple ( file id, offset in file )
            
            See dump.py for example.
        """
# Process records here
        
        self.pointer=ptr
        
        return utils.write_file_ptr(self.config,ptr)
        
        
    def close(self):
        """ Close this object. """
        return True
