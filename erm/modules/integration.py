import http.client
import urllib.parse
import base64
import json
import requests
import re
from datetime import datetime, timedelta, date

from requests_ntlm import HttpNtlmAuth
import zeep
from zeep import xsd, Client
from zeep.transports import Transport

from .backend import backend
from .dateutils import dateutils
from .exceptions import ERMError, NoDataError


class externalSystem():
    '''all new integration types must be 
       added as subclasses inherited from externalSystem'''
    def __init__(self, url, usr, pswd):
        self.url = url
        self.usr = usr
        self.pswd = pswd
        self.connection = None

    def connect(self):
        return True

    def get_raw_entries(engineer):
        raise NotImplementedError 
 
    def add_engineer_login_to_raw_entries(self, response, engineer):
        raise NotImplementedError 

    def get_entries(self, engineer):
        response = self.get_raw_entries(engineer)
        result = self.add_engineer_login_to_raw_entries(response, engineer)
        return result

    def preprocess_entries():
        raise NotImplementedError 

    def __get_start_and_end_date_for_entry(self):
        start_date = str(date.today()) + 'T' + str(datetime.today().hour) + ':' + ('0' if datetime.today().minute < 10 else '') + str(datetime.today().minute)

        one_hour_delta = timedelta(hours = 1)
        end_datetime = datetime.today() + one_hour_delta
        end_date = str(end_datetime.date()) + 'T' + str(end_datetime.hour) + ':' + str(end_datetime.minute)
        return start_date, end_date

    def send_booking_to_backend(self, entriesList):
        '''1. check if booking entry with same prj_id exists 
           2. if entry exists -> update db 3. if no -> insert into db'''
        for prj_id, assignee, company, sla in entriesList:
            try:
                backend.update_booking(prj_id, assignee, sla)
                print('Updating entries')
            except NoDataError:
                start_date, end_date = self.__get_start_and_end_date_for_entry()
                print('Creating entries')
                backend.add_booking_entry(booking_type = 'hours', percent = None, 
                                                         hours = 1, repeat = 0, start_date=start_date, 
                                                         end_date=end_date, company = company, 
                                                         sla = sla, project_id = prj_id, 
                                                         resource_login = assignee)
        return '200'


class Sharepoint(externalSystem):
    def get_raw_entries(self, eng):
        '''get entries from Sharepoint using SOAP and NTLM auth'''
        session = requests.Session()
        session.auth = HttpNtlmAuth(self.usr,self.pswd)
        r = session.get(self.url)
        client = Client(self.url, transport=Transport(session=session))
        response = client.service.GetListItems(listName = '{AF9DFDD5-6EEB-44BA-B908-4E42A5221CD7}', 
                                               viewName = '{2D63DFF6-F930-46AC-AD53-3E5688A1FD39}',
                                               rowLimit = 3000)
        return response

    def add_engineer_login_to_raw_entries(self, response, engineer):
        result = []
        for row in response[0].getchildren():
            if engineer[10] == row.get(key = 'ows_sl_WFSAssignedTo') and row.get(key = 'ows_sl_WFSStatus') == 'Выполнение':
                result.append({'key': row.get(key = 'ows_ID'), 
                            'summary': row.get(key = 'ows_Title'), 
                            'assignee': row.get(key = 'ows_sl_WFSAssignedTo'), 
                            'status': row.get(key = 'ows_sl_WFSStatus'), 
                            'priority': row.get(key = 'ows_sl_WFSPriority'), 
                            'eng_id': engineer[12]})
        return result

    def preprocess_entries(self, raw_entries):
        preproced_entries = []
        for entry in raw_entries:
            prj_id = entry['key'] + ' ' + entry['summary']
            assignee = entry['eng_id']
            preproced_entries.append((prj_id, assignee, 'Стэп Лоджик', 'none'))
        return preproced_entries


class Jira(externalSystem):
    def get_raw_entries(self, engineer):
        '''get entries from JIRA using rest api and HTTP basic auth'''
        jql_expr = 'resolution = Unresolved AND status in (Open, "In Progress", Reopened) AND assignee = {0}'.format(engineer[9])
        params = urllib.parse.urlencode({'jql': jql_expr})
        b64usrpass = base64.b64encode(bytes(self.usr + ":" + self.pswd, "ascii"))
        headers = {"Authorization": "Basic " + b64usrpass.decode("ascii"), 
                   "Connection": b"keep-alive", 
                   "Accept-Encoding": b"gzip, deflate"}
        conn = http.client.HTTPConnection(self.url, 8080)
        conn.request('GET', url = '/rest/api/latest/search?{0}'.format(params), headers = headers)
        answ = conn.getresponse()
        response = json.loads(answ.read().decode('utf-8'))['issues']
        conn.close()
        return response

    def add_engineer_login_to_raw_entries(self, response, engineer):
        for entry in response:
            entry['eng_id'] = engineer[12]
        return response
       
    def preprocess_entries(self, res):
        prep_res = []
        for entry in res:
            prj_id = entry['key'] + ' ' + entry['fields']['summary']
            assignee = entry['eng_id']
            prep_res.append((prj_id, assignee, 'Стэп Лоджик', re.sub(r'-[0-9]+', '', entry['key'])))
        return prep_res


class Remedy(externalSystem):
    def connect(self):
        # typical WSDL URL http://<midtier_server>/arsys/WSDL/public/<servername>/HPD_IncidentInterface_WS
        client = zeep.Client(wsdl=self.url)
        
        header = xsd.Element(
                'AuthenticationInfo',
                xsd.ComplexType([
                    xsd.Element(
                        'userName', 
                        xsd.String()),
                    xsd.Element(
                        'password',
                        xsd.String()),
                    ])
                )
        
        header_value = header(userName = self.usr, password = self.pswd)

        self.connection = (client, header_value)
        return True

    def add_engineer_login_to_raw_entries(self, response, engineer):
        for entry in response:
            entry['eng_id'] = engineer[12]
        return response
    
    def preprocess_entries(self, res):
        prep_res = []
        for entry in res:
            prj_id = entry['Incident_Number'] + ' ' + entry['Summary']
            assignee = entry['eng_id']
            company = entry['Company']
            sla = entry['SLA']
            prep_res.append((prj_id, assignee, company, sla))
        return prep_res


class Remedy_HPD(Remedy):
    def get_raw_entries(self, engineer):
        '''get incidents list from external system for particular engineer (eng variable)'''
        client, header_value = self.connection
        with client.settings(strict=False):
            #get incidents with Status < 4, where 4 is id of "Resolved" status
            try:
                result = client.service.HelpDesk_QueryList_Service(Qualification ="'Assignee Login ID'=\"" + engineer[8] + "\" AND 'Status' < 4", 
                    maxLimit=2, startRecord="", _soapheaders=[header_value])
            except zeep.exceptions.Fault as error:
                result = []
                print(error) 
        return result


class Remedy_CHG(Remedy):
    def get_raw_entries(self, engineer):
        '''get changes list from external system for particular engineer (eng variable)'''
        client, header_value = self.connection
        with client.settings(strict=False):
            try:
                result = client.service.Change_QueryList_Service(Qualification ="'CAB Manager ( Change Co-ord )'=\"" + engineer[8] + "\" AND 'Change Request Status' < 9", 
                                                            maxLimit=2, startRecord="", _soapheaders=[header_value])
            except zeep.exceptions.Fault as error:
                result = []
                print(error) 
        return result
