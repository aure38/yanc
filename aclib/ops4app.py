# coding: utf8
import rethinkdb as r
import logging
import time
from pathlib import Path
import threading
import pytoml

class ops4app :
    # --- Do not use directly
    def __init__(self, toml_file_str='') :
        # -- Init des champs
        self._my_cfgFP      = None
        self._my_config     = dict()
        self._my_rdb        = None
        self._my_rdb_lock   = threading.Lock()
        self._my_rdb_IP     = '127.0.0.1'   # See BELOW
        self._my_rdb_port   = 28015         # See BELOW
        self._my_rdb_base   = 'test'        # See BELOW
        self._isOK          = False

        # -- Parsing de la conf
        try:
            fp  = Path(toml_file_str)
            fo  = fp.open(mode='r', encoding='utf-8', errors='backslashreplace')
            cfg = pytoml.load(fo)
            self._my_cfgFP    = fp
            self._my_config   = cfg
            self._my_rdb_IP   = (cfg.get('ops4app') or dict()).get('rdb.ip') or '127.0.0.1'
            self._my_rdb_port = (cfg.get('ops4app') or dict()).get('rdb.port') or '28015'
            self._my_rdb_base = (cfg.get('ops4app') or dict()).get('rdb.base') or 'test'
        except Exception as e:
            logging.error("Error reading config file %s | %s" % (str(toml_file_str), str(e)))

        # -- Init de la conn a RDB
        if self.rdb is not None:
            self._isOK = True

    # --- Creation of instance from config TOML file : return None in case of error or the instance if config file & DB connexion are OK.
    @staticmethod
    def get_instance(toml_file_str='') :
        the_instance = ops4app(toml_file_str)
        if the_instance.isOK() :
            return the_instance
        else :
            return None

    def isOK(self):
        return self._isOK

    # --- Config as a dict
    @property
    def cfg(self):
        return self._my_config
    @cfg.setter
    def cfg(self, p):
        pass  # on ne fait rien en ecriture
    @cfg.deleter
    def cfg(self):
        self._my_config.clear()

    # --- RDB multithread / multi instances : on take et on release (avec attente dans le take si besoin)
    def rdb_get_lock(self):
        if self.rdb is not None :
            self._my_rdb_lock.acquire(blocking=True,timeout=60)
        return self.rdb
    def rdb_release(self):
        self._my_rdb_lock.release()

    # --- RDB monothread : 1 instance par thread, PERSISTANCE DE LA CONNEXION DONC pas possible d'avoir connexion en thread safe Acces a la DB en get / set / delete
    @property
    def rdb(self):
        if self._my_rdb is None :
            nb_reconnect = 3
            while nb_reconnect > 0 :
                try :
                    self._my_rdb = r.connect(host=self._my_rdb_IP, port=self._my_rdb_port, db=self._my_rdb_base, auth_key="", timeout=10)
                    self._my_rdb.use(self._my_rdb_base)
                    nb_reconnect = 0
                    self._isOK = True
                except Exception as e :
                    logging.error("Echec connexion a RDB : %s" % str(e))
                    self._my_rdb = None
                    self._isOK = False
                    nb_reconnect -= 1
                    if nb_reconnect > 0 :
                        logging.error("Sleep avant reconnexion RDB")
                        time.sleep(20)
        return self._my_rdb
    @rdb.setter  # Acces a la db en set : dans tous les cas, on referme la connexion et on met None -> appel du delete
    def rdb(self, p):
        # with self._my_rdb_MT_lock :
        logging.warning("Tentative d'affecter une valeur au pointeur RDB : %s" % type(p))
        del self.rdb  # logging.log(logging.DEBUG-2, "Deconnexion de la DB via assignement=%s" % str(type(p)) )
    @rdb.deleter  # On referme la connexion a la db
    def rdb(self):
        # with self._my_rdb_MT_lock :
        if self._my_rdb is not None :
            try :
                self._my_rdb.close()
            except Exception as e :
                logging.warning("Erreur durant deconnexion RDB : %s" % str(e))
            self._my_rdb = None
