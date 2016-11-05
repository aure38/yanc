import cherrypy
from cherrypy.lib import auth_basic





USERS = {'jon': 'secret'}
def validate_password(realm, username, password):
    if username in USERS and USERS[username] == password:
       return True
    return False


class Root(object):
    @cherrypy.expose
    def index(self):
        return "Hello World!"



if __name__ == '__main__':
    server_config={
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 443,
#        'log.screen': False , 'log.access_file': '' , 'log.error_file': '',
        'engine.autoreload.on': False,  # Sinon le server se relance des qu'un fichier py est modifie...
        'server.ssl_module': 'pyopenssl',
        'server.ssl_certificate':'./cherry.crt',
        'server.ssl_certificate_key ':'./cherry.key',
    }
    cherrypy.config.update(server_config)

    app_conf = { '/protected/area': {
       'tools.auth_basic.on': True,
       'tools.auth_basic.realm': 'localhost',
       'tools.auth_basic.checkpassword': validate_password
        } }

    cherrypy.quickstart(Root(), '/', app_conf)

