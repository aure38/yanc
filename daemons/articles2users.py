import logging
import os,sys,time,hashlib
from pathlib import Path
from datetime import datetime
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

    liste_users = ['aure']
    for usr in liste_users :
        myops.rdb_get_lock()
        answer = r.table('users').get(usr).pluck('feeds').run(myops.rdb)
        feedsid4user = answer['feeds']
        myops.rdb_release()

        for fid in feedsid4user :
            liste_articles = list()
            myops.rdb_get_lock()
            curseur = r.table('articles').filter({'feed_id' : fid}).run(myops.rdb)
            for article in curseur :
                liste_articles.append(article)

            for artic in liste_articles :
                # TODO : Analyse de l'article avec les filtres
                tmpSort = '1000' + artic['ts_published'].strftime('%y%m%d%H%M')
                do_insert = False
                if not r.table('articles_users').get(artic['id']).run(myops.rdb) :
                    do_insert = True
                elif not r.table('articles_users').get(artic['id']).has_fields(usr).run(myops.rdb) :
                    do_insert = True
                if do_insert :
                    reponse = r.table('articles_users').insert({'id':artic['id'], 'ts_published':artic['ts_published'], usr : {'status':0, 'score':0, 'sorting':tmpSort, 'tags':['tag1', 'tag2']}}, conflict='update').run(myops.rdb)
                    print("%s - %s - %d new inserted" % (usr, fid, reponse['inserted']))
            myops.rdb_release()