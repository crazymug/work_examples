import http.client
import urllib.parse

import xml.etree.ElementTree as ET

from .resource import resource

class message():
    '''class implements messaging subsystem'''

    @staticmethod
    def send_sms(mes_text, eng_login, login, pwd, originator, phone = None):
        '''send sms through smstraffic.ru
        returns OK or ERROR string'''
        
        if eng_login != 0:
            eng = resource(eng_login)
            phone = eng.phone

        params = urllib.parse.urlencode({'login': login, 'password': pwd, 
                                         'phones': phone,'message': mes_text, 
                                         'rus': '5', 'originator': originator})
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn = http.client.HTTPConnection('api.smstraffic.ru', 80)
        conn.request('POST','/multi.php', params, headers)
        answ = conn.getresponse()
        
        try:
            root = ET.fromstring(answ.read())
            conn.close()
            return (root[0].text, ' '.join((root[1].text, root[2].text)))
        except Exception as e:
            conn.close()
            print(e)
            return ("ERROR", e)
