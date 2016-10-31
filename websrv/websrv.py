import logging
import cherrypy
import os,sys
from pathlib import Path
from datetime import timedelta
from aclib.ops4app import ops4app
from aclib.sourceparsing import acfeed
import rethinkdb as r
from aclib.func4strings import Func4strings as f4s

class ServYanc(object):
    def __init__(self):
        self.myops = ops4app.get_instance('./yanc.cfg.toml')
        self.myusers = list()

    def checkUser(self, username=''):
        # TODO : ajouter un compteur de temps pour faire un reload en cas d'ajout de user dans la base
        if len(self.myusers) == 0 :
            if self.myops.rdb_get_lock() is not None :
                self.myusers = list(r.table('users')['id'].run(self.myops.rdb))
                self.myops.rdb_release()
                logging.info('Checking users')

        if username in self.myusers :
            return True
        else :
            return False

    # ------- Recup de la liste globale des articles
    @cherrypy.expose()
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def getlstartic(self, _="", usrun="", nbdays="5"):
        retourObj = list()
        try :
            p_days  = int(nbdays)
        except:
            p_days = 5
        try :
            p_user = usrun[:20]
            # TODO : faire un test sur les users
        except :
            p_user = ""

        if self.myops.rdb_get_lock() is not None and len(p_user) > 1 :
            # -- Recup date max pour faire historique base sur la datemax des articles du user
            DateMax  = r.table('articles_users').has_fields(p_user)['ts_published'].max().run(self.myops.rdb)
            DateLimite = DateMax - timedelta(days=int(p_days))

            # -- query avec joint
            curseur = r.table('articles_users').has_fields(p_user).filter(lambda row : (row["ts_published"].ge(DateLimite) & row[p_user]['status'].ge(0)))
            curseur = curseur.inner_join(r.table('articles'), lambda rowA,rowB: rowB['id'].eq(rowA['id'])).zip()
            curseur = curseur.map(lambda doc: {'id':doc['id'], 'score':doc[p_user]['score'], 'tags':doc[p_user]['tags'], 'ts_published':doc['ts_published'].to_iso8601(),
                                              'title': doc['title'], 'content':doc['content'], 'url_article':doc['url_article'], 'links_audio':doc['links_audio'], 'links_images':doc['links_images'], 'links_video':doc['links_video'],
                                              'sorting': doc[p_user]['sorting']})
            res = curseur.limit(50).order_by(r.desc('sorting')).run(self.myops.rdb)
            self.myops.rdb_release()
            for doc2 in res :
                itm = dict()
                itm['id']        = doc2['id']
                itm['score']     = doc2['score']
                itm['tags']      = doc2['tags']
                itm['date']      = doc2['ts_published'][5:10]+' '+doc2['ts_published'][11:16]
                itm['title']     = doc2['title'] if len(doc2['title']) < 100 else doc2['title'][:100] + "..."
                itm['content']   = doc2['content'] if len(doc2['content']) < 400 else doc2['title'][:400] + "..."
                itm['url']       = doc2['url_article']
                itm['image']     = '/images/favicon.gif'
                if len(doc2['links_images']) > 0 :
                    itm['image'] = doc2['links_images'][0]
                itm['url_media'] = ''
                if len(doc2['links_video']) > 0 :
                    itm['url_media'] = doc2['links_video'][0]
                elif len(doc2['links_audio']) > 0 :
                    itm['url_media'] = doc2['links_audio'][0]
                retourObj.append(itm)
        return retourObj

    # ------- Recup stats user
    @cherrypy.expose()
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def getusrstt(self, _="", usrun=""):
        retourObj = dict()
        try :
            p_user = usrun[:20]
            # TODO : faire un test sur les users
        except :
            p_user = ""

        if self.myops.rdb_get_lock() is not None and len(p_user) > 1 :
            retourObj['nbarticles'] = r.table('articles_users').has_fields(p_user).filter(lambda row : row[p_user]['status'].ge(0)).count().run(self.myops.rdb)
            self.myops.rdb_release()
        return retourObj

    # ------- DEL article for user
    @cherrypy.expose()
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def dartic(self, _="", usrun="", artid=""):
        try :
            p_id  = artid[:200]
        except:
            p_id = ""
        try :
            p_user = usrun[:20]
            # TODO : faire un test sur les users
        except :
            p_user = ""

        if p_user != "" and p_id != "" :
            if self.myops.rdb_get_lock() is not None :
                # -- query avec joint
                r.table('articles_users').get(p_id).update({p_user: r.row[p_user].merge({'status':-666})}).run(self.myops.rdb)
                self.myops.rdb_release()
        return { 'answer' : "ok"}

    # ------- Feed check
    @cherrypy.expose()
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def feedcheck1(self, _="", usrun="", feedurl="") :
        retour = dict()
        if self.checkUser(usrun[:30]) :
            cherrypy.session['usrun'] = usrun[:30]

        if len(cherrypy.session.get('usrun', default="")) < 2 :
            retour['status']  = "error"
            retour['message'] = "User session"
        else :
            newfeedurl = acfeed.url_normalize(feedurl)
            newfeedid = acfeed.calculateFeedId(newfeedurl)
            if len(newfeedid) < 10 :
                retour['status']  = "error"
                retour['message'] = "Error in URL format"
            else :
                if self.myops.rdb_get_lock() is None :
                    retour['status']  = "error"
                    retour['message'] = "Error while connecting to DB"
                else :
                    feed_exist = r.table('feeds').get(newfeedid).run(self.myops.rdb)
                    self.myops.rdb_release()
                    if feed_exist :
                        # TODO : Gerer quand le feed est deja dans la DB
                        retour['status']  = "okdb"
                        retour['next']  = "indb"
                        retour['feedobj'] = feed_exist
                    else :
                        try :
                            jsonfeed = acfeed.parsefeed(httpurl=newfeedurl, feedid=newfeedid)
                            if jsonfeed['status'] == 'ok' :
                                retour['status']  = 'oknew'
                                retour['feedobj'] = jsonfeed['feed']
                            else :
                                retour['status'] = 'error'
                                retour['message']  = jsonfeed['message']
                        except Exception as e :
                            retour['status'] = 'error'
                            retour['message'] = str(e)
                            logging.error("Exception URL %s | %s " % (newfeedurl, str(e)))
        return retour

    # ------- Feed insert
    @cherrypy.expose()
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def abonn2feed(self, _="", usrun="", feedid="", feedurl="", feedname="", feeddescription="", image_url="") :
        retour = dict()
        retour['status'] = retour['message'] = ""
        if self.checkUser(usrun[:30]) :
            cherrypy.session['usrun'] = usrun[:30]

        if len(cherrypy.session.get('usrun', default="")) < 2 :
            retour['status']  = "error"
            retour['message'] = "User session"
        else :
            newfeedurl = acfeed.url_normalize(feedurl)
            newfeedid = acfeed.calculateFeedId(newfeedurl)
            if newfeedid != feedid :
                retour['status']  = "error"
                retour['message'] = "mismatch in feed url and id"
            elif self.myops.rdb_get_lock() is None :
                retour['status']  = "error"
                retour['message'] = "Error while connecting to DB for check"
            else :
                feed_exist = r.table('feeds').get(newfeedid).run(self.myops.rdb)
                self.myops.rdb_release()
                if not feed_exist :
                    # --- Ajout du feed dans la DB
                    if self.myops.rdb_get_lock() is None :
                        retour['status']  = "error"
                        retour['message'] = "Error while connecting to DB for insert"
                    else :
                        new_feed = dict()
                        new_feed['id'] = newfeedid
                        new_feed['url']  = newfeedurl
                        new_feed['name'] = f4s.cleanLangueFr(feedname)[:50]
                        new_feed['description'] = f4s.cleanLangueFr(feeddescription)[:100]
                        new_feed['image_url_online'] = image_url[:400]
                        # new_feed['headers'] = dict()
                        # new_feed['headers']['url']  = newfeedurl
                        # new_feed['headers']['name'] = f4s.cleanLangueFr(feedname)[:50]
                        # new_feed['headers']['description'] = f4s.cleanLangueFr(feeddescription)[:100]
                        # new_feed['headers']['image_url_online'] = image_url[:400]
                        rdbans = r.table('feeds').insert(new_feed, conflict="error", return_changes=False).run(self.myops.rdb)
                        self.myops.rdb_release()
                        logging.info("Feed insertion : %d | %s" % (rdbans['inserted'], str(rdbans)))
                        retour['message'] = "Feed inserted - "

                # --- Ajout de l'abonnement pour le user
                if self.myops.rdb_get_lock() is None :
                    retour['status']  = "error"
                    retour['message'] = "Error while connecting to DB for subscription"
                else :
                    r.table('users').get(cherrypy.session['usrun']).update({'feeds': r.branch(r.row['feeds'].contains(newfeedid), r.row['feeds'], r.row['feeds'].append(newfeedid))}).run(self.myops.rdb)
                    self.myops.rdb_release()
                    retour['status']   = "ok"
                    retour['message'] += "Subscription done to " + newfeedid

        return retour



    # @cherrypy.expose()
    # @cherrypy.tools.json_in()
    # @cherrypy.tools.json_out()
    # def feedcheck2(self, _="", usrun=""):
    #     retour = dict()
    #     if self.checkUser(usrun[:30]) :
    #         cherrypy.session['usrun'] = usrun[:30]
    #
    #     if len(cherrypy.session.get('usrun', default="")) < 2 :
    #         retour['status']  = "error"
    #         retour['message'] = "User session"
    #     elif len(cherrypy.session.get('newfeed_content', default='')) > 0 :
    #         try :
    #             jsonfeed = acfeed.parsefeed(httpcontent=cherrypy.session.get('newfeed_content', default=''), feedid=cherrypy.session.get('newfeed_id', default=''))
    #             retour['status']  = 'ok'
    #             retour['feedobj'] = jsonfeed
    #         except Exception as e :
    #             logging.error("Exception parsing %s " % str(e))
    #             retour['status']  = "error"
    #             retour['message'] = "Parsing error %s" % str(e)
    #
    #     return retour

if __name__ == '__main__':
    # --- Logs Definition  logging.Logger.manager.loggerDict.keys()
    Level_of_logs = level =logging.INFO
    logging.addLevelName(logging.DEBUG-2, 'DEBUG_DETAILS') # Logging, arguments pour fichier : filename='example.log', filemode='w'
    logging.basicConfig(level=Level_of_logs, datefmt="%m-%d %H:%M:%S", format="P%(process)d|T%(thread)d|%(name)s|%(levelname)s|%(asctime)s | %(message)s")  # %(thread)d %(funcName)s L%(lineno)d
    logging.getLogger("requests").setLevel(logging.WARNING) # On desactive les logs pour la librairie requests

    # -- PATH
    if 'websrv' in Path.cwd().parts[-1] :
        os.chdir("..")
    elif 'github' in Path.cwd().parts[-1] :
        os.chdir("./yanc")
    sys.path.append('./')
    logging.info("Starting from %s" % str(os.getcwd()))

    # -------- CherryPy et web statique
    # ops = Ops4app(appli_uname='websrv.static')
    cherrypy.config.update({'server.socket_port': 80, 'server.socket_host': '0.0.0.0',
                            'log.screen': False , 'log.access_file': '' , 'log.error_file': '',
                            'engine.autoreload.on': False  # Sinon le server se relance des qu'un fichier py est modifie...
                            })

    # -------- SERVER ROOT --------
    config_root= { '/' :            { 'tools.staticdir.on'  : True, 'tools.staticdir.index' : "index.html", 'tools.staticdir.dir' : Path().cwd().joinpath("websrv").joinpath("wstatic").as_posix(), 'tools.sessions.on' : True } }
    cherrypy.tree.mount(ServYanc(), "/", config_root)


    # --- Loglevel pour CherryPy : a faire une fois les serveurs mounted et avant le start
    for log_mgt in logging.Logger.manager.loggerDict.keys() :
        if "cherrypy.access" in log_mgt :
            logging.getLogger(log_mgt).setLevel(logging.WARNING)

    # -------- Lancement --------
    cherrypy.engine.start()
    cherrypy.engine.block()

