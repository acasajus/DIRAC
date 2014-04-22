
import random
import time
import threading
import thread
from hashlib import md5

from DIRAC.Core.Utilities.ReturnValues import S_ERROR, S_OK
from DIRAC.Core.Utilities.DIRACSingleton import DIRACSingleton
from DIRAC.Core.Utilities.ThreadSafe import WORM

class LockRing( object ):
  __metaclass__ = DIRACSingleton

  def __init__( self ):
    random.seed()
    self.__locks = {}
    self.__events = {}
    self.__enableGSIWORM = True
    self.__gsiWORM = False

  def __genName( self, container ):
    name = md5( str( time.time() + random.random() ) ).hexdigest()
    retries = 10
    while name in container and retries:
      name = md5( str( time.time() + random.random() ) ).hexdigest()
      retries -= 1
    return name

  def getLock( self, lockName = "", recursive = False ):
    if not lockName:
      lockName = self.__genName( self.__locks )
    try:
      return self.__locks[ lockName ]
    except KeyError:
      if recursive:
        self.__locks[ lockName ] = threading.RLock()
      else:
        self.__locks[ lockName ] = threading.Lock()
    return self.__locks[ lockName ]

  def gsiAction( self, funcToCall ):
    if self.__enableGSIWORM:
      if not self.__gsiWORM:
        self.__gsiWORM = WORM( 1000 )
      return self.__gsiWORM.read( funcToCall )
    else:
      return funcToCall

  def _gsiPause( self, funcToCall ):
    if self.__enableGSIWORM:
      if not self.__gsiWORM:
        self.__gsiWORM = WORM( 1000 )
      return self.__gsiWORM.write( funcToCall )
    else:
      return funcToCall

  def getEvent( self, evName = "" ):
    if not evName:
      evName = self.__genName( self.__events )
    try:
      return self.__events[ evName ]
    except KeyError:
      self.__events[ evName ] = threading.Event()
    return self.__events[ evName ]

  def acquire( self, lockName ):
    try:
      self.__locks[ lockName ].acquire()
    except ValueError:
      return S_ERROR( "No lock named %s" % lockName )
    return S_OK()

  def release( self, lockName ):
    try:
      self.__locks[ lockName ].release()
    except ValueError:
      return S_ERROR( "No lock named %s" % lockName )
    return S_OK()

  def _openAll( self ):
    """
    WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
    DO NOT USE EXCEPT IN JUST SPAWNED NEW CHILD PROCESSES!!!!!!!!
    NEVER IN THE PARENT PROCESS!!!!!!
    WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
    """
    for lockName in self.__locks.keys():
      try:
        self.__locks[ lockName ].release()
      except ( RuntimeError, thread.error, KeyError ):
        pass

  def _setAllEvents( self ):
    """
    WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
    DO NOT USE EXCEPT IN JUST SPAWNED NEW CHILD PROCESSES!!!!!!!!
    NEVER IN THE PARENT PROCESS!!!!!!
    WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
    """
    for evName in self.__events.keys():
      try:
        self.__events[ evName ].set()
      except KeyError:
        pass

gLockRing = LockRing()

if __name__ == "__main__":
  lr = LockRing()
  lock = lr.getLock( "test1" )
  print "ACQUIRING LOCK", lock
  lock.acquire()
  print "IS THE SAME LOCK? ", lock == lr.getLock( "test1" )
  print "OPENING ALL LOCKS"
  lr._openAll()
  print "REACQUIRING LOCK", lock
  lr.acquire( "test1" )
  print "RELEASING LOCK"
  lr.release( "test1" )
  print "IS SINGLETON", lr == LockRing()
  ev = lr.getEvent( "POT" )
  ev.set()
  lr._setAllEvents()
  print "ALL OK"


