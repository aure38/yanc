import logging
import os,sys,time,hashlib
from pathlib import Path
from datetime import timedelta
from pytz import timezone
from aclib.func4strings import Func4strings as f4s
from aclib.ops4app import ops4app
import feedparser
import rethinkdb as r

if __name__ == '__main__':
    # --- Logs Definition  logging.Logger.manager.loggerDict.keys()
    Level_of_logs = level =logging.INFO
    logging.addLevelName(logging.DEBUG-2, 'DEBUG_DETAILS') # Logging, arguments pour fichier : filename='example.log', filemode='w'
    logging.basicConfig(level=Level_of_logs, datefmt="%m-%d %H:%M:%S", format="P%(process)d|T%(thread)d|%(name)s|%(levelname)s|%(asctime)s | %(message)s")  # %(thread)d %(funcName)s L%(lineno)d

    # -- PATH
    if 'daemons' in Path.cwd().parts[-1] :
        os.chdir("..")
    elif 'github' in Path.cwd().parts[-1] :
        os.chdir("./yanc")
    sys.path.append('./')
    logging.info("Starting from %s" % str(os.getcwd()))

    myops = ops4app.get_instance('./yanc.cfg.toml')
    if not myops :
        logging.critical('Problem with config file or DB')
        exit()

    myops.rdb_get_lock()
    DateMax  = r.table('articles')['ts_published'].max().run(myops.rdb)
    DateLimite = DateMax - timedelta(days=int(10))
    curseur = r.table('articles').filter(lambda row : (row["ts_published"].lt(DateLimite))).count().run(myops.rdb)
    print(curseur)
    curseur = r.table('articles_users').filter(lambda row : (row["ts_published"].lt(DateLimite))).count().run(myops.rdb)
    print(curseur)
    myops.rdb_release()


