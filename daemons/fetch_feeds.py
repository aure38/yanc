import logging
import os,sys
from pathlib import Path
from aclib.ops4app import ops4app
import feedparser
import rethinkdb as r
from aclib.sourceparsing import acfeed

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

    # liste_feeds = [ 'http://www.courrierinternational.com/feed/all/rss.xml', 'http://podcast.bfmbusiness.com/channel78/BFMchannel78.xml' ]
    myops.rdb_get_lock()
    liste_feeds = r.table('feeds').pluck('id', 'name', 'url', 'image_url_online').run(myops.rdb)
    myops.rdb_release()

    # -- Parsing des feeds
    for ifeed in liste_feeds :
        feedr = feedparser.parse(ifeed['url'])
        articles = acfeed.parsearticles(feedobj=feedr, feedid=ifeed['id'], feed_img_url=ifeed['image_url_online'])

        # On passe la date au format RDB
        for artic in articles :
            artic['ts_published']  = r.iso8601(artic['ts_published'])

        # -- Insert items in DB
        if len(articles) > 0 :
            myops.rdb_get_lock()
            reponse = r.table('articles').insert(articles, conflict="error", return_changes=False).run(myops.rdb)
            print("%s - %d new inserted" % (ifeed['name'], reponse['inserted']))
            myops.rdb_release()
