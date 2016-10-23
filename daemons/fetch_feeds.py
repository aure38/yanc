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

    # liste_feeds = [ 'http://www.courrierinternational.com/feed/all/rss.xml', 'http://podcast.bfmbusiness.com/channel78/BFMchannel78.xml' ]
    myops.rdb_get_lock()
    liste_feeds = r.table('feeds').pluck('id', 'name', 'url').run(myops.rdb)
    myops.rdb_release()

    # -- Parsing des feeds
    for ifeed in liste_feeds :
        id_feed   = ifeed['id']
        url_feed  = ifeed['url']
        name_feed = ifeed['name']

        articles = list()
        feedr = feedparser.parse(url_feed)

        # -- Parse feed headers
        feedc = dict()
        ## Check the headers : http://pythonhosted.org//feedparser/
        feedc['status']    = f4s.cleanLangueFr(str(feedr.get('status')) or '')
        feedc['encoding']  = f4s.cleanLangueFr(str(feedr.get('encoding')) or '')
        feedc['url']       = f4s.cleanLangueFr(str(feedr.get('href')) or '')
        feedc['lang']      = f4s.cleanLangueFr(str(feedr['feed'].get('language')) or '')
        feedc['author']    = f4s.cleanLangueFr(str(feedr['feed'].get('author')) or '')
        feedc['title']     = f4s.cleanLangueFr(str(feedr['feed'].get('title')) or  '')
        feedc['subtitle']  = f4s.cleanLangueFr(str(feedr.get('subtitle')) or '')
        feedc['image_url'] = ''
        if 'href' in (feedr['feed'].get('image') or dict()) :
            feedc['image_url'] = str(feedr['feed'].get('image').get('href'))

        # -- Parse each article
        for artic in (feedr.get('entries') or dict()) :
            articc = dict()
            articc['feed_id'] = id_feed
            articc['title']  = f4s.cleanLangueFr(str(artic.get('title')) or feedc['title'] )
            articc['author']  = f4s.cleanLangueFr(str(artic.get('author')) or feedc['author'])
            articc['url_article']  = f4s.cleanLangueFr(str(artic.get('link')) or '')

            # -- Gestion de la date de l'article
            date_generee = False
            tmpDate = None
            # Au mieux : la date parsee par la librairie RSS. mais des soucis quand la date est en francais detaille...
            if 'published_parsed' in artic and artic['published_parsed'] is not None :
                tmpDate = artic['published_parsed']
            # ou Autre champ possible la date parsee par la librairie RSS. mais des soucis quand la date est en francais detaille...
            elif 'updated_parsed' in artic and artic['updated_parsed'] is not None :
                tmpDate = artic['updated_parsed']
            # ou Recuperation du champ texte et interpretation
            elif 'published' in artic and artic['published'] is not None and artic['published'] != '':
                try:
                    # https://docs.python.org/3/library/datetime.html?highlight=datetime#strftime-strptime-behavior
                    # Pour marianne : 'Mercredi, 14 Janvier, 2015 - 10:00'
                    tmpDateStr = f4s.cleanOnlyLetterDigit(artic['published']).lower()
                    tmpDateStr = f4s.strMultiReplace([('lundi','monday'), ('mardi','tuesday'), ('mercredi','wednesday'), ('jeudi','thursday'), ('vendredi','friday'), ('samedi','saturday'), ('dimanche','sunday')], tmpDateStr)
                    tmpDateStr = f4s.strMultiReplace([('janvier','january'), ('fevrier','february'), ('mars','marchy'), ('avril','april'), ('mai','may'), ('juin','june'), ('juillet','july'),('aout','august'), ('septembre','september'), ('octobre','october'), ('novembre','november'), ('decembre','december')], tmpDateStr)
                    tmpDatetime = datetime.strptime(tmpDateStr, '%A, %d %B, %Y - %H:%M')
                    tmpDate = tmpDatetime.timetuple()  # passage au format n-uple
                except:
                    tmpDate = None
            # Test final
            if tmpDate is None :
                tmpDate = time.gmtime()
                date_generee = True

            localtz = timezone('Europe/Paris')                                       # On localize la date comme etant en France. Le decalage d'ete ne semble pas pris en compte par contre, juste la timezone
            articc['ts_published'] = r.iso8601(localtz.localize(datetime.fromtimestamp(time.mktime(tmpDate))).isoformat()) # creation d'un object serialiable rethinkDB pour ce datetime

            # articc['date']  = time.strftime('%Y/%m/%d %H:%M:%S', tmpDate)  # time.strftime('%H:%M:%S %d/%m/%Y',tmpDate)
            # articc['date_NUMDATE']  = time.mktime(tmpDate)

            # -- Gestion du contenu
            tmpSummary = f4s.cleanLangueFr(str(artic.get('summary')) or '')
            tmpContent = ''
            if 'content' in artic :
                for med_item in artic['content']:
                    if med_item.has_key('value') and med_item.has_key('type'):
                        if med_item['type'] in ['text/html', 'text/plain'] :
                            tmpContent = med_item['value']

            if tmpSummary == '' :   articc['summary'] = f4s.cleanLangueFr(tmpContent)
            else :                  articc['summary'] = f4s.cleanLangueFr(tmpSummary)
            if len(articc['summary']) < 2 :
                articc['summary'] = articc['title']

            # -- Liens
            articc['links_images'] = list()
            articc['links_audio'] = list()
            articc['links_video'] = list()
            if artic.has_key('links') :
                for med_item in artic['links']:
                    if med_item.has_key('href') and med_item.has_key('type'):
                        if 'image' in str(med_item['type']) :
                            articc['links_images'].append(str(med_item['href']))
                        elif 'audio' in str(med_item['type']) :
                            articc['links_audio'].append(str(med_item['href']))
                        elif 'video' in str(med_item['type']) :
                            articc['links_video'].append(str(med_item['href']))
            articc['links_images'] = list(set(articc['links_images']))
            articc['links_audio'] = list(set(articc['links_audio']))
            articc['links_video'] = list(set(articc['links_video']))
            if len(articc['links_images']) == 0 and len(feedc['image_url']) > 0 :
                articc['links_images'].append(str(feedc['image_url']))

            # -- Gestion des tags
            articc['tags'] = list()
            if 'tags' in artic :
                for tag_item in artic['tags']:
                    if tag_item.has_key('term'):
                        if len(str(tag_item['term'])) > 1 :
                            articc['tags'].append(f4s.cleanMax(str(tag_item['term'])))
            articc['tags'] = list(set(articc['tags']))

            # -- Calcul de l'identifiant unique
            uniq_id_str = articc['url_article']
            if len(articc['links_audio']) > 0 :
                uniq_id_str += articc['links_audio'][0]
            elif len(articc['links_video']) > 0 :
                uniq_id_str += articc['links_video'][0]
            articc['id'] = hashlib.sha1(str(uniq_id_str).encode('utf-8')).hexdigest()

            # -- Ajout de l'article dans la liste : SI MOINS DE N JOURS pour n'ajouter que des news recentes
            if (datetime.utcnow() - datetime.fromtimestamp(time.mktime(tmpDate))).days < 5 :
                articles.append(articc)

        # -- Insert items in DB
        if len(articles) > 0 :
            myops.rdb_get_lock()
            reponse = r.table('articles').insert(articles, conflict="error", return_changes=False).run(myops.rdb)
            print("%s - %d new inserted" % (name_feed, reponse['inserted']))
            myops.rdb_release()

