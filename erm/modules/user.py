import hashlib
import http 
import json

from .toolset import Toolset

class User():
    def __init__(self, login, pswd):
        self.login = login
        self.pswd = pswd

    @property
    def is_authenticated(self):
        '''compare pswd hash from db with pswd hash from request'''
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET', '/rest/check_credentials/{0}/{1}'.format(self.login,
                                                                    self.pswd))
        answ = conn.getresponse()
     
        #pswd_list[0] -> password hash, pswd_list[1] -> password salt
        is_auth = json.loads(answ.read())

        if is_auth == True:
            self.toolset_actions = Toolset(self.user_group, 
                                           self.fullname, self.login).actions
            self.id = ' '.join((self.login, self.pswd))
            return True
        else:
            return False

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def fullname(self):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET', '/rest/get_fullname/{0}'.format(self.login))
        answ = conn.getresponse()
        fullname = json.loads(answ.read())
        return fullname

    @property
    def user_group(self):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET', '/rest/get_user_group/{0}'.format(self.login))
        answ = conn.getresponse()
        user_group = json.loads(answ.read())
        return user_group 

    def get_id(self):
        if self.is_authenticated:
            return self.id
        else:
            return None
    
    @staticmethod
    def get(user_id):
        return User(user_id.split()[0], user_id.split()[1])
