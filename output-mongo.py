# -*- coding: utf-8 -*-

# MultiChain Feed Adapter (c) Coin Sciences Ltd
# All rights reserved under BSD 3-clause license


import cfg
#import pymysql
import pymongo
import datetime
import readconf
import multichain
import json
import utils
import feed


class AdapterOutput(cfg.BaseOutput):

    def initialize(self):
        
        self.ptr_name=self.config['pointer']
        self.stream_table_names = {}
        self.checked_tables = {}
        
        if not readconf.check_db_config(self.config):
            return False
            
        if readconf.is_missing(self.config,'port'):
            self.config['port']=27017
            
        if not self.check_pointer_table():
            utils.log_error("Couldn't create read pointers table")
            return False
              
        self.pointer = (0, 0)
        document=self.fetch_document("pointers",{"pointer":self.ptr_name})
        if document is not None:
            if "file" not in document or "pos" not in document:
                return False
            self.pointer = (document["file"], document["pos"])
            
        return True
   
        
    def write(self, records, ptr):
        
        if not self.begin_transaction():
            return False
            
        if not self.check_streammap_table():
            utils.log_error("Couldn't create stream mapping table")
            return False
                        
        for record in records:
            event=feed.parse_record(record)
            
            if not self.process_event(event):
                utils.log_error("Couldn't process event {code:02x} at ({file:4d}, {offset:08x})".format(code=record['code'],file=record['file'],offset=record['offset']))
                if event.table is None:
                    utils.log_error("Event record corrupted, ignored")
                else:
                    return False
                
        self.execute_upsert(
            "pointers",
            {"pointer":self.ptr_name},
            {"pointer":self.ptr_name},
            {"file":ptr[0],"pos":ptr[1]}
        )
        
        self.pointer=ptr
        
        return self.commit_transaction()
        
        
    def close(self):
        return True


    def create_pointer_table(self):
        return self.execute_create_collection("pointers",[{"fields":[("pointer",pymongo.ASCENDING)],"name":"pointers_idx","unique":True}])
   
            
    def create_streammap_table(self):
        return self.execute_create_collection("streams",[{"fields":[("stream",pymongo.ASCENDING)],"name":"streams_idx","unique":True}])
    
        
    def create_blocks_table(self):
        return self.execute_create_collection("blocks",[
            {"fields":[("hash",pymongo.ASCENDING)],"name":"blocks_hash_idx","unique":True},
            {"fields":[("height",pymongo.ASCENDING)],"name":"blocks_height_idx","unique":False}]
        )
       
            
    def create_stream_table(self,stream_name,table_name):
        return self.execute_create_collection(table_name,[
            {"fields":[("id",pymongo.ASCENDING)],"name":table_name+"_id_idx","unique":True},
            {"fields":[("keys",pymongo.ASCENDING)],"name":table_name+"_key_idx","unique":False},
            {"fields":[("publishers",pymongo.ASCENDING)],"name":table_name+"_pub_idx","unique":False},
            {"fields":[("blockheight",pymongo.ASCENDING),("blockpos",pymongo.ASCENDING)],"name":table_name+"_pos_idx","unique":False}]
        ) and self.execute_upsert(
            "streams",{"stream":stream_name},{"stream":stream_name},{"dbtable":table_name},False
        )
    
    
    def event_block_add(self,event):
        if not self.check_blocks_table(event):
            return False
        
        return self.execute_upsert(
            "blocks",
            {"hash":event.hash},
            {"hash":event.hash,"height":event.height},
            {"txcount":event.txcount,"confirmed":event.time,"miner":event.miner,"size":event.size}
        )
    
    
    def event_block_remove(self,event):
        if not self.check_blocks_table(event):
            return False
            
        return self.execute_delete(
            "blocks",
            {"hash":event.hash}
        )
    
        
    def event_stream_item_received(self,event):
        if not self.check_stream_table(event):
            return False
            
        return self.execute_upsert(
            event.table,
            {"id":event.id},
            {"id":event.id,"txid":event.txid,"vout":event.vout,"keys":event.keys,"publishers":event.publishers,"size":event.size,"format":event.format},
            {"flags":event.flags,"received":event.received,"binary_data":event.binary,"text_data":event.text,"json_data":event.json,"dataref":event.dataref}
        )
        

        
    def event_stream_item_confirmed(self,event):
        if not self.check_stream_table(event):
            return False
            
        return self.execute_upsert(
            event.table,
            {"id":event.id},
            {},
            {"blockhash":event.hash,"blockheight":event.height,"blockpos":event.offset,"confirmed":event.time,"dataref":event.dataref},
        )
        


    def event_stream_item_unconfirmed(self,event):
        if not self.check_stream_table(event):
            return False
            
        return self.execute_upsert(
            event.table,
            {"id":event.id},
            {},
            {},
            {"blockhash":None,"blockheight":None,"blockpos":None,"confirmed":None},
        )


    def event_stream_item_invalid(self,event):
        if not self.check_stream_table(event):
            return False
            
        return self.execute_delete(
            event.table,
            {"id":event.id},
        )


    def event_stream_offchain_available(self,event):
        if not self.check_stream_table(event):
            return False
            
        return self.execute_upsert(
            event.table,
            {"id":event.id},
            {},
            {"flags":event.flags,"received":event.received,"binary_data":event.binary,"text_data":event.text,"json_data":event.json,"dataref":event.dataref}
        )
        

    def event_stream_offchain_purged(self,event):
        if not self.check_stream_table(event):
            return False
            
        document=self.fetch_document(event.table,{"id":event.id})
        
        if document is None:
            utils.log_error("Item with this id not found")
            return False

        if "flags" not in document:
            utils.log_error("Annot finf flags field for purged document")
            return False
            
        return self.execute_upsert(
            event.table,
            {"id":event.id},
            {},
            {"flags": (document["flags"] & 254)},
            {"binary_data":None,"text_data":None,"json_data":None,"dataref":None},
        )
        

    def check_stream_table(self,event):
        
        if event.stream is None:
            return False
        
        stream_name=event.stream
        
        if stream_name not in self.stream_table_names:
            sanitized=self.sanitized_stream_name(stream_name)
            table_name=None
            
            document=self.fetch_document("streams",{"stream":stream_name})
            if document is not None:
                if "dbtable" not in document:
                    return False
                table_name=document["dbtable"]
                    
            if table_name is None:
                for ext in range(0,50):
                    try_name = sanitized
                    if ext > 0:
                        try_name += "_{ext:02d}".format(ext = ext)
                        
                    document=self.fetch_document("streams",{"dbtable":try_name})
                    if document is None:
                        table_name=try_name
                        break
                                    
            if table_name is None:
                utils.log_error("No available db table name found for stream " + stream_name)
                return False
                
            if not self.create_stream_table(stream_name,table_name):
                return False
                
            self.checked_tables[table_name]=True
            self.stream_table_names[stream_name]=table_name

        event.table=self.stream_table_names[stream_name]
        
        return True


    def check_pointer_table(self):
        if not 'pointers' in self.checked_tables:
            if not self.create_pointer_table():
                return False
            self.checked_tables['pointers']=True

        return True
    
    
    def check_streammap_table(self):
        if not 'streams' in self.checked_tables:
            if not self.create_streammap_table():
                return False
            self.checked_tables['streams']=True

        return True
    
    
    def check_blocks_table(self,event):
        if not 'blocks' in self.checked_tables:
            if not self.create_blocks_table():
                return False
            self.checked_tables['blocks']=True

        event.table='blocks'
        return True
         
        
    def process_event(self,event):
        if event.code == multichain.event_block_add_start:
            return self.event_block_add(event)
        elif event.code == multichain.event_block_remove_start:
            return self.event_block_remove(event)
        elif event.code == multichain.event_stream_item_received:
            return self.event_stream_item_received(event)
        elif event.code == multichain.event_stream_item_confirmed:
            return self.event_stream_item_confirmed(event)
        elif event.code == multichain.event_stream_item_unconfirmed:
            return self.event_stream_item_unconfirmed(event)
        elif event.code == multichain.event_stream_item_invalid:
            return self.event_stream_item_invalid(event)
        elif event.code == multichain.event_stream_offchain_available:
            return self.event_stream_offchain_available(event)
        elif event.code == multichain.event_stream_offchain_purged:
            return self.event_stream_offchain_purged(event)
            
        return True
 
 
    def connect(self):
        conn=pymongo.MongoClient("mongodb://"+self.config['host']+":"+str(self.config['port']),username=self.config['user'],password=self.config['password'],authSource=self.config['dbname'])
        return conn
    

    def getdb(self,conn):
        return conn[self.config['dbname']]
        
 
    def replace_sql_binaries(self,raw_sql):                
        toHex = lambda x:''.join(format(c, '02x') for c in x)
        params=()
        head=""
        tail=raw_sql[0]
        for param in raw_sql[1]:
            parts = tail.split("%s",1)
            head += parts[0]
            if isinstance(param, bytes):
                head += "UNHEX('" + toHex(param) + "')"
            else:
                head += "%s"
                params += (param,)
            tail = parts[1]
        return (head+tail,params)

        
    def execute_transaction(self,commands):
        
        result=True
        if len(commands) == 0:
            return result

        conn=None
        try:
            conn=self.connect()
            db=self.getdb(conn)
            
            for command in commands:
                if len(command) == 5:                                          # UPSERT
                    self.execute_update(db,command[0],command[1],command[2],command[3],command[4])
                elif len(command) == 2:                                        # DELETE 
                    coll=db[command[0]]
                    coll.delete_one(self.transform(command[1]))
                
        except pymongo.errors.PyMongoError as e:
            utils.log_error(str(e))
            result=False
            
        if conn is not None:
            conn.close()
        
            
        return result


    def execute_create_collection(self,collection,indexes):
        result=True
        conn=None
        try:
            conn=self.connect()
            db=self.getdb(conn)
            coll=db[collection]
            for index in indexes:
                coll.create_index(index['fields'],name=index['name'],unique=index['unique'])
        except pymongo.errors.PyMongoError as e:
            utils.log_error(str(e))
            result=False
        
        if conn is not None:
            conn.close()
            
        return result
    

    def transform(self,values):
        result={}
        for field in values:            
            if values[field] is not None:
                if field == "json_data":
                    result[field]=json.loads(values[field])                
                elif isinstance(values[field], datetime.datetime):
                    result[field]=datetime.datetime.timestamp(values[field])
                elif isinstance(values[field], bytes):
                    result[field]=utils.bytes_to_hex(values[field])
                else:                
                    result[field]=values[field]
                    
        return result
    
    
    def execute_update(self,db,collection,query,insert_values,update_values,delete_values):
        coll=db[collection]
        if len(insert_values) != 0:
            coll.update(self.transform(query),{"$set":self.transform(update_values),"$setOnInsert":self.transform(insert_values)},upsert=True)
        else:
            if len(delete_values) != 0:
                if len(update_values) != 0:
                    coll.update(self.transform(query),{"$set":self.transform(update_values),"$unset":delete_values},upsert=False)                        
                else:
                    coll.update(self.transform(query),{"$unset":delete_values},upsert=False)                                            
            else:            
                coll.update(self.transform(query),{"$set":self.transform(update_values)},upsert=False)                        


    def execute_upsert(self,collection,query,insert_values,update_values,delete_values={},transactional=True):
        if transactional:
            self.commands.append((collection,query,insert_values,update_values,delete_values))
            return True            
            
        result=True
        conn=None
        try:
            conn=self.connect()
            db=self.getdb(conn)
            self.execute_update(db,collection,query,insert_values,update_values,delete_values)
        except pymongo.errors.PyMongoError as e:
            utils.log_error(str(e))
            result=False
        
        if conn is not None:
            conn.close()
            
        return result


    def execute_delete(self,collection,query):
        self.commands.append((collection,query))
        return True

        
    def fetch_document(self,collection,query):
        result=None
        try:
            conn=self.connect()
            db=self.getdb(conn)
            coll=db[collection]
            result=coll.find_one(self.transform(query))
        except pymongo.errors.PyMongoError as e:
            utils.log_error(str(e))
        
        if conn is not None:
            conn.close()

        return result
        
    def begin_transaction(self):
        self.commands=[]
        return True


    def commit_transaction(self):
        result=self.execute_transaction(self.commands)
        self.commands=[]
        return result

        
    def abort_transaction(self):
        self.commands=[]
        return True


    def sanitized_stream_name(self,stream_name):
        if stream_name == 'blocks':
            return 'blocks_stream'
        if stream_name == 'streams':
            return 'streams_stream'
        if stream_name == 'pointers':
            return 'pointers_stream'
            
        sanitized="".join([ c if c.isalnum() else "_" for c in stream_name ])
        sanitized=sanitized.lower()
        if not sanitized[0].isalpha():
            sanitized = "ref_" + sanitized
        
        return sanitized[0:20]
    
