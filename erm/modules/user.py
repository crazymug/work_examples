import hashlib
import http 
import json

from .toolset import Toolset
from .backend import backend


class User():
    def __init__(self, login, pswd):
        self.login = login
        self.pswd = pswd

    @property
    def is_authenticated(self):
        '''compare pswd hash from db with pswd hash from request'''
        is_auth = backend.check_credentials(self.login, self.pswd)
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
        user_info = backend.get_user(self.login)
        fullname = user_info['name']
        return fullname

    @property
    def user_group(self):
        user_group = backend.get_user_group(self.login)
        return user_group 

    def get_id(self):
        if self.is_authenticated:
            return self.id
        else:
            return None
    
    @staticmethod
    def get(user_id):
        return User(user_id.split()[0], user_id.split()[1])
