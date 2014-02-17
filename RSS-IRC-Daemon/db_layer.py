#Database abstration layer

import shelve
from threading import Thread
import time

class MyDataBaseLayer(Thread):
    def __init__(self,vars_dict,db_fn):
        Thread.__init__(self)
        self.datb = shelve.open(db_fn)
        if(self.datb.has_key("qwe")):
            self.data = self.datb["qwe"]
            print "Database Layer: loading data from db."
            print "Database Layer: loaded data:"+repr(self.data)
        else:
            self.data = vars_dict.copy()
            print "Database Layer: Database is empty, so i will initialize new keys with data provided from init."
            print "Database Layer: Initial data: "+repr(self.data)
        self.RUNFLAG = 1
        self.fn = db_fn
        
    def run(self):
        while (self.RUNFLAG == 1):
            self.datb["qwe"] = self.data 
            print "Database Layer: syncing db"
            time.sleep(10)
        
    def stop(self):
        self.RUNFLAG = 0
        print "Database Layer: Stopping database enumerator..."
        self.datb.close()
        print "Database Layer: Database close."
        
    def kill(self):
        self.RUNFLAG = 0
        print "Database Layer: Stopping database enumerator..."
        self.datb.close()
        print "Database Layer: Database close."
        
    def getdata(self):
        print "Database Layer: getdata()"
        return self.data
    
    def setdata(self,ddd):
        print "Database Layer: setdata()"
        self.data = ddd
        pass