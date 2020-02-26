import json
import http.client
import urllib.parse
import time

from .dateutils import dateutils 
from .exceptions import DBError, NoDataError

from flask import flash


class backend:
    '''class represents erm backend(rest)'''
    def add_error_processing(func):
        def func_with_msg(*args, **kwargs):
            try:
                data, status, data_name = func(*args, **kwargs)
                if status == 503:
                    raise DBError 
                if status == 404:
                    raise NoDataError(data_name)
                return json.loads(data)
            except ConnectionError:
                flash('Backend не доступен, обратитесь к администратору системы', 'error')
                return []
            except DBError:
                flash('БД не доступна, обратитесь к администратору системы', 'error')
                return []
            except NoDataError as error:
                try:
                    flash('Нет данных по '+error.data_name, 'warning')
                except RuntimeError:
                    raise NoDataError(error.data_name)  
                return []
        return func_with_msg

    @staticmethod
    @add_error_processing
    def search_logins(backend_ip, backend_port, search_string):
        conn = http.client.HTTPConnection(backend_ip, backend_port)
        conn.request('GET', 
                     '/rest/search/{0}'.format(urllib.parse.quote(search_string)))
        answ = conn.getresponse()
        logins = answ.read()
        conn.close()
        return logins, answ.status, 'поисковому запросу'


    @staticmethod
    @add_error_processing
    def get_engineers_list():
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng_list')
        answ = conn.getresponse()
        eng_list = answ.read()
        conn.close()
        return eng_list, answ.status, 'инженерам'

    @staticmethod
    @add_error_processing
    def get_eng_booking_week(eng_login):
        ONE_WEEK_SECONDS = 604800
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET',
                     '/rest/eng_booking_interval/{0}/{1}/{2}'.format(eng_login, 
                                                                     dateutils.unix2iso(int(time.time())), 
                                                                     dateutils.unix2iso(int(time.time()) + ONE_WEEK_SECONDS)))
        answ = conn.getresponse()
        bookinfo = answ.read()
        conn.close()
        return bookinfo, answ.status, 'загрузке инженера {0} на текущую неделю'.format(eng_login)
    
    @staticmethod
    @add_error_processing
    def get_engineer_booking(eng_login, start, end):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng_booking_interval/' + eng_login + '/' + start + '/' + end)
        answ = conn.getresponse()
        booking_entries = answ.read()
        return booking_entries, answ.status, 'загрузке инженера {0} в заданный период времени'.format(eng_login)

    @staticmethod
    @add_error_processing
    def get_eng_booking_info(eng_login, prj_id):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        if prj_id != None:
            prj_id_encoded = urllib.parse.quote(prj_id)
            conn.request('GET','/'.join(['/rest/eng_booking', eng_login, prj_id_encoded]))
        elif prj_id == None:
            conn.request('GET','/'.join(['/rest/eng_booking', eng_login, '0']))
        answ = conn.getresponse()
        bookinfo = answ.read()
        conn.close()
        return bookinfo, answ.status, 'загрузке инженера {0}'.format(eng_login) 

    @staticmethod
    @add_error_processing
    def add_booking_entry(booking_type, percent, hours, 
                    repeat, start_date, end_date, company, sla,
                    project_id, resource_login):
        '''insert entry about incident into booking table based on list from SOAP-answer'''
        params = urllib.parse.urlencode({'booking_type': booking_type, 
            'percent': percent, 'hours': hours, 'res_login': resource_login, 'project_id': project_id, 
            'repeat': repeat, 'start_datetime': start_date, 'end_datetime': end_date, 
            'company': company,
            'sla': sla})
        headers = {"Content-type": "application/x-www-form-urlencoded", 
                   "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('POST','/rest/eng_booking/' + resource_login + '/0', params, headers)
        answ = conn.getresponse()
        conn.close()
        return json.dumps([]), answ.status, ''

    @staticmethod
    @add_error_processing
    def update_booking(prj_id, assignee, sla):
        '''update entry about incident based on list from SOAP-answer'''
        params = urllib.parse.urlencode({'prj_id': prj_id, 
                                         'res_login': assignee,
                                         'sla': sla})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('PATCH','/rest/eng_booking/' + assignee + '/0', params, headers)
        answ = conn.getresponse()
        conn.close()
        return json.dumps([]), answ.status, ''

    @staticmethod
    @add_error_processing
    def get_eng_info(eng_login):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng/' + eng_login)
        answ = conn.getresponse()
        enginfo = answ.read()
        conn.close()
        return enginfo, answ.status, 'профилю инженера {0}'.format(eng_login)

    @staticmethod
    @add_error_processing
    def add_engineer(fullname, phone, tags, skills, 
                     org_unit, eng_type, email, 
                     rem_id, jira_id, util, suir_id, 
                     sharepoint_id, langs):
        params = urllib.parse.urlencode({'fullname': fullname, 'phone': phone, 'tags': tags, 
                                         'skills': skills, 'org_unit': org_unit, 
                                         'type': eng_type, 'email': email, 'rem_id': rem_id, 
                                         'jira_id': jira_id, 'sharepoint_id': sharepoint_id,
                                         'util': util, 'suir_id': suir_id, 'langs': langs})
        headers = {"Content-type": "application/x-www-form-urlencoded", 
                   "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('POST','/rest/eng/'+suir_id, params, headers)
        answ = conn.getresponse()
        print(answ.read())
        conn.close()
        return json.dumps([]), answ.status, ''

    @staticmethod
    @add_error_processing
    def update_engineer(fullname, phone, tags, skills, 
                        org_unit, eng_type, email, 
                        rem_id, jira_id, util, suir_id, 
                        sharepoint_id, langs):
        params = urllib.parse.urlencode({'fullname': fullname, 'phone': phone, 'tags': tags, 
                                         'skills': skills, 'org_unit': org_unit, 
                                         'type': eng_type, 'email': email, 'rem_id': rem_id, 
                                         'jira_id': jira_id, 'sharepoint_id': sharepoint_id,
                                         'util': util, 'suir_id': suir_id, 'langs': langs})
        headers = {"Content-type": "application/x-www-form-urlencoded", 
                   "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('PATCH','/rest/eng/'+suir_id, params, headers)
        answ = conn.getresponse()
        print(answ.read())
        conn.close()
        return json.dumps([]), answ.status, ''

    @staticmethod
    @add_error_processing
    def delete_engineer(eng_login):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('DELETE','/rest/eng/' + eng_login)
        answ = conn.getresponse()
        conn.close()
        return json.dumps([]), answ.status, ''

    @staticmethod
    @add_error_processing
    def get_workreport(eng_login, month, year):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/workrep/' + eng_login + '/' + str(month) + '/' + str(year))
        answ = conn.getresponse()
        report_from_db = answ.read()
        return report_from_db, answ.status, 'ежемесячному отчету. Отчет необходимо заполнить и сохранить'

    @staticmethod
    @add_error_processing
    def save_workreport(request, eng_login, month, year):
        params = urllib.parse.urlencode(request.form.to_dict())
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('POST','/rest/workrep/' + eng_login + '/' + str(month) + '/' + str(year), body = params, headers = headers)
        answ = conn.getresponse()
        return json.dumps([]), answ.status, ''

    @staticmethod
    @add_error_processing
    def get_all_workreports(month, year):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/consworkrep/' + str(month) + '/' + str(year))
        answ = conn.getresponse()
        all_workreports = answ.read()
        return all_workreports, answ.status, 'ежемесячным отчетам'

    @staticmethod
    @add_error_processing 
    def get_user(login):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/user/' + login)
        answ = conn.getresponse()
        users = answ.read()
        return users, answ.status, 'пользователю {0}'.format(login)

    @staticmethod
    @add_error_processing 
    def get_users():
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/users')
        answ = conn.getresponse()
        users = answ.read()
        return users, answ.status, 'пользователям'

    @staticmethod
    @add_error_processing 
    def add_user(request):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        params = urllib.parse.urlencode(request.form.to_dict())
        conn.request('POST','/rest/users', body = params, headers = headers)
        answ = conn.getresponse()
        success = answ.read()
        return success, answ.status, ''

    @staticmethod
    @add_error_processing
    def check_credentials(login, pswd):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET', '/rest/check_credentials/{0}/{1}'.format(login, pswd))
        answ = conn.getresponse()
     
        #pswd_list[0] -> password hash, pswd_list[1] -> password salt
        is_auth = answ.read()
        return is_auth, answ.status, ''

    @staticmethod
    @add_error_processing
    def get_user_group(login):
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET', '/rest/get_user_group/{0}'.format(login))
        answ = conn.getresponse()
        user_group = answ.read()
        return user_group, answ.status, ''
