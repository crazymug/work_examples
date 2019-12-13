from datetime import date, datetime
import json
import http.client
import urllib.parse
import time

import sqlite3

from .dateutils import dateutils as du

class ersmm:
    '''class represents ersmm application'''
    @staticmethod
    def get_engineers_list():
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng_list')
        answ = conn.getresponse()
        if answ.status != 404:
            eng_list = json.loads(answ.read())
        else: eng_list = []
        conn.close()
        return eng_list

    @staticmethod
    def get_eng_booking_week(eng_login):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng_booking_interval/{0}/{1}/{2}'.format(eng_login, du.unix2iso(int(time.time()), False), du.unix2iso(int(time.time()) + 604800, False)))
        answ = conn.getresponse()
        if answ.status != 404:
            a = answ.read()
            bookinfo = json.loads(a)
        else: bookinfo = []
        conn.close()
        return bookinfo

    @staticmethod
    def get_eng_booking_info(eng_login, prj_id):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        if prj_id != None:
            prj_id_encoded = urllib.parse.quote(prj_id)
            conn.request('GET','/'.join(['/rest/eng_booking', eng_login, prj_id_encoded]))
        elif prj_id == None:
            conn.request('GET','/'.join(['/rest/eng_booking', eng_login, '0']))
        answ = conn.getresponse()
        if answ.status != 404:
            a = answ.read()
            bookinfo = json.loads(a)
        else: bookinfo = []
        conn.close()
        return bookinfo

    @staticmethod
    def get_eng_info(eng_login):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng/' + eng_login)
        answ = conn.getresponse()
        if answ.status != 404: 
            enginfo = json.loads(answ.read())
        else: enginfo = []
        conn.close()
        return enginfo

    @staticmethod
    def insert_into_booking_table(prj_id, eng_login, company, sla):
        '''insert entry about incident into booking table based on list from SOAP-answer'''
        params = urllib.parse.urlencode({'type': 0, 'perchours': 0, 'res_login': eng_login, 'prj_id': prj_id, 
            'repeat': 0, 'start_datetime': 0, 'end_datetime': 0, 'company': company,
            'sla': sla})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('POST','/rest/eng_booking/' + eng_login + '/0', params, headers)
        answ = conn.getresponse()
        print(answ.read())
        conn.close()
        return None

    @staticmethod
    def update_booking_table(prj_id, assignee, sla):
        '''update entry about incident based on list from SOAP-answer'''
        try:
            params = urllib.parse.urlencode({'prj_id': prj_id, 
                                             'res_login': assignee,
                                             'sla': sla})
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
            conn = http.client.HTTPConnection('127.0.0.1', 8000)
            conn.request('PATCH','/rest/eng_booking/' + assignee + '/0', params, headers)
            answ = conn.getresponse()
            print(answ.read())
            conn.close()
        except Exception as e:
            print(e)
            return None

