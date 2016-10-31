import time,hashlib
from datetime import datetime
import dateutil.parser
from pytz import timezone
from aclib.func4strings import Func4strings as f4s
import socket,feedparser



class acfeed :
    def __init__(self):
        super().__init__()

    # ----- Normalisation de l'url et creation du ID
    @staticmethod
    def url_normalize(urlfeed=''):
        retour = ''
        purl = urlfeed[:400].lower()
        if purl.startswith('http') and len(purl) > 6 :
            retour = purl
        return retour

    @staticmethod
    def calculateFeedId(normalizedurl=''):
        retour = ''
        if len(normalizedurl) > 1 :
            retour = hashlib.sha1(normalizedurl.encode('utf-8')).hexdigest()
        return retour

    @staticmethod
    def _parseheaders(feedobj):
        headers = dict()
        #headers['encoding']  = f4s.cleanLangueFr(str(feedobj.get('encoding')) or '')
        #headers['url']       = f4s.cleanLangueFr(str(feedobj.get('href')) or '')
        #headers['lang']      = f4s.cleanLangueFr(str(feedobj['feed'].get('language')) or '')
        #headers['author']    = f4s.cleanLangueFr(str(feedobj['feed'].get('author')) or '')
        headers['name']      = f4s.cleanLangueFr(str(feedobj['feed'].get('title')) or  'Not specified')
        headers['description']  = f4s.cleanLangueFr(str(feedobj.get('subtitle')) or 'Not specified')
        headers['image_url_online'] = ''
        if 'href' in (feedobj['feed'].get('image') or dict()) :
            headers['image_url_online'] = str(feedobj['feed'].get('image').get('href'))
        return headers

    # Renvoie la date de l'article au format string ISO
    @staticmethod
    def _parsearticle_date(feedarticle):
        tmpDate = None
        # Au mieux : la date parsee par la librairie RSS. mais des soucis quand la date est en francais detaille...
        if 'published_parsed' in feedarticle and feedarticle['published_parsed'] is not None :
            tmpDate = feedarticle['published_parsed']
        # ou Autre champ possible la date parsee par la librairie RSS. mais des soucis quand la date est en francais detaille...
        elif 'updated_parsed' in feedarticle and feedarticle['updated_parsed'] is not None :
            tmpDate = feedarticle['updated_parsed']
        # ou Recuperation du champ texte et interpretation
        elif 'published' in feedarticle and feedarticle['published'] is not None and feedarticle['published'] != '':
            try:
                # https://docs.python.org/3/library/datetime.html?highlight=datetime#strftime-strptime-behavior
                # Pour marianne : 'Mercredi, 14 Janvier, 2015 - 10:00'
                tmpDateStr = f4s.cleanOnlyLetterDigit(feedarticle['published']).lower()
                tmpDateStr = f4s.strMultiReplace([('lundi','monday'), ('mardi','tuesday'), ('mercredi','wednesday'), ('jeudi','thursday'), ('vendredi','friday'), ('samedi','saturday'), ('dimanche','sunday')], tmpDateStr)
                tmpDateStr = f4s.strMultiReplace([('janvier','january'), ('fevrier','february'), ('mars','marchy'), ('avril','april'), ('mai','may'), ('juin','june'), ('juillet','july'),('aout','august'), ('septembre','september'), ('octobre','october'), ('novembre','november'), ('decembre','december')], tmpDateStr)
                tmpDatetime = datetime.strptime(tmpDateStr, '%A, %d %B, %Y - %H:%M')
                tmpDate = tmpDatetime.timetuple()  # passage au format n-uple
            except:
                tmpDate = None
        # Test final
        if tmpDate is None :
            tmpDate = time.gmtime()

        localtz = timezone('Europe/Paris') # On localize la date comme etant en France. Le decalage d'ete ne semble pas pris en compte par contre, juste la timezone
        date_finale = localtz.localize(datetime.fromtimestamp(time.mktime(tmpDate))).isoformat()
        #date_finale_RDB = r.iso8601(date_finale) # creation d'un object serialiable rethinkDB pour ce datetime
        return date_finale

    # Renvoie le texte de l'article : format francais, longueur non limitee
    @staticmethod
    def _parsearticle_contenu(feedarticle):
        tmpSummary = f4s.cleanLangueFr(str(feedarticle.get('summary')) or '')
        if tmpSummary == '' :
            if 'content' in feedarticle :
                for med_item in feedarticle['content']:
                    if med_item.has_key('value') and med_item.has_key('type'):
                        if med_item['type'] in ['text/html', 'text/plain'] :
                            tmpSummary = med_item['value']
        return f4s.cleanLangueFr(tmpSummary)

    # Calcule l'id de l'article
    @staticmethod
    def _parsearticle_calcule_id(champs_traites):
        uniq_id_str = champs_traites['url_article']
        if len(champs_traites['links_audio']) > 0 :
            uniq_id_str += champs_traites['links_audio'][0]
        elif len(champs_traites['links_video']) > 0 :
            uniq_id_str += champs_traites['links_video'][0]
        the_id = hashlib.sha1(str(uniq_id_str).encode('utf-8')).hexdigest()
        return the_id

    @staticmethod
    def parsearticles(feedobj, feedid, feed_img_url=''):
        articles = list()
        for artic in (feedobj.get('entries') or dict()) :
            articc = dict()
            articc['feed_id']       = feedid
            articc['title']         = f4s.cleanLangueFr(str(artic.get('title')) or 'Not specified' )
            articc['author']        = f4s.cleanLangueFr(str(artic.get('author')) or '')
            articc['url_article']   = f4s.cleanLangueFr(str(artic.get('link')) or '')
            articc['ts_published']  = acfeed._parsearticle_date(artic)
            articc['content']       = acfeed._parsearticle_contenu(artic)[:500]

            articc['title_stz']     = f4s.cleanOnlyLetterDigit(articc['title']).lower()
            articc['content_stz']   = f4s.cleanOnlyLetterDigit(articc['content']).lower()

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
            if len(articc['links_images']) == 0 and len(feed_img_url) > 0 :
                articc['links_images'].append(feed_img_url)

            # -- Gestion des tags
            articc['tags'] = list()
            if 'tags' in artic :
                for tag_item in artic['tags']:
                    if tag_item.has_key('term'):
                        if len(str(tag_item['term'])) > 1 :
                            articc['tags'].append(f4s.cleanMax(str(tag_item['term'])))
            articc['tags'] = list(set(articc['tags']))

            # -- Calcul de l'identifiant unique
            articc['id'] = acfeed._parsearticle_calcule_id(articc)

            # -- Ajout de l'article dans la liste : SI MOINS DE N JOURS pour n'ajouter que des news recentes
            if len(articc['url_article']) > 5 :
                if (datetime.now(tz=timezone('Europe/Paris')) - dateutil.parser.parse(articc['ts_published'])).days < 5 :
                    articles.append(articc)

        return articles

    # --------- Retour de { status:'ok' , message: '' , feed : { 'header': ... , 'articles' : [] }
    @staticmethod
    def parsefeed(httpurl='', feedid='') :
        retour = dict()
        retour['feed']    = dict()
        retour['status']  = "error"
        retour['message'] = ""

        # -- Load and Parse - http://pythonhosted.org//feedparser/
        socket.setdefaulttimeout(30)
        feedr = feedparser.parse(httpurl)
        if f4s.cleanLangueFr(str(feedr.get('status')) or '') != '200' :
            retour['status']  = "error"
            retour['message'] = 'bad status from feedparser ' + str(feedr.get('status'))
        else :
            retour['status'] = "ok"

            # -- Headers
            retour['feed']['id']             = feedid
            retour['feed']['headers']        = acfeed._parseheaders(feedr)
            retour['feed']['headers']['url'] = httpurl

            # -- Articles
            retour['feed']['articles'] = acfeed.parsearticles(feedobj=feedr, feedid=feedid, feed_img_url='')

        return retour
