import http.client
import urllib.parse
import base64
import json
import requests
import re

from requests_ntlm import HttpNtlmAuth
import zeep
from zeep import xsd, Client
from zeep.transports import Transport

from .ersmm import ersmm

class externalSystem():
    '''Abstract class all new integration types must be added as subclasses inherited from externalSystem'''
    def __init__(self, url, usr, pswd):
        self.url = url
        self.usr = usr
        self.pswd = pswd

    def connect(self):
        return True, True

    def getEntries():
        raise NotImplementedError 

    def preprocessEntries():
        raise NotImplementedError 

    @staticmethod
    def updateBooking(entriesList):
        '''1. check if booking entry with same prj_id exists 2. if entry exists -> update db 3. if no -> insert into db'''

        for prj_id, assignee, company, sla in entriesList:
            bookinfo = ersmm.get_eng_booking_info(assignee, prj_id)
            if bookinfo == []:
                ersmm.insert_into_booking_table(prj_id, assignee, company, sla)
            else:
                ersmm.update_booking_table(prj_id, assignee, sla)
        else:
            return True
        return False

class Basecamp(externalSystem):

    def getEntries(self, eng):
        return True

    def preprocessEntries(self, res):
        return True

class Sharepoint(externalSystem):

    def getEntries(self, eng):
        '''get entries from Sharepoint using SOAP and NTLM auth'''
        session = requests.Session()
        session.auth = HttpNtlmAuth(self.usr,self.pswd)
        r = session.get(self.url)
        client = Client(self.url, transport=Transport(session=session))
        resp = client.service.GetListItems(listName = '{AF9DFDD5-6EEB-44BA-B908-4E42A5221CD7}', viewName = '{2D63DFF6-F930-46AC-AD53-3E5688A1FD39}', rowLimit = 3000)
        
        res = []
        for row in resp[0].getchildren():
            if eng[10] == row.get(key = 'ows_sl_WFSAssignedTo') and row.get(key = 'ows_sl_WFSStatus') == 'Выполнение':
                res.append({'key': row.get(key = 'ows_ID'), 'summary': row.get(key = 'ows_Title'), 'assignee': row.get(key = 'ows_sl_WFSAssignedTo'), 'status': row.get(key = 'ows_sl_WFSStatus'), 
                    'priority': row.get(key = 'ows_sl_WFSPriority'), 'eng_id': eng[12]})
        return res

    def preprocessEntries(self, res):
        prep_res = []
        for entry in res:
            prj_id = entry['key'] + ' ' + entry['summary']
            assignee = entry['eng_id']
            prep_res.append((prj_id, assignee, 'Стэп Лоджик', 'none'))
        return prep_res


class Jira(externalSystem):
    
    def getEntries(self, eng):
        '''get entries from JIRA using rest api and HTTP basic auth'''
        jql_expr = 'resolution = Unresolved AND status in (Open, "In Progress", Reopened) AND assignee = {0}'.format(eng[9])
        params = urllib.parse.urlencode({'jql': jql_expr})
        b64usrpass = base64.b64encode(bytes(self.usr + ":" + self.pswd, "ascii"))
        headers = {"Authorization": "Basic " + b64usrpass.decode("ascii"), "Connection": b"keep-alive", "Accept-Encoding": b"gzip, deflate"}

        conn = http.client.HTTPConnection(self.url, 8080)
        conn.request('GET', url = '/rest/api/latest/search?{0}'.format(params), headers = headers)
        answ = conn.getresponse()
        res = json.loads(answ.read().decode('utf-8'))['issues']
        conn.close()
        for entry in res:
            entry['eng_id'] = eng[12]
        return res
        
    def preprocessEntries(self, res):
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

        return client, header_value
    
    @staticmethod
    def getEntry(client, header_value, eng):
        '''get incidents/issues/requests list from external system for particular engineer (eng variable)'''
        with client.settings(strict=False):
            #get incidents with Status < 4, where 4 is id of "Resolved" status
            try:
                res = client.service.HelpDesk_QueryList_Service(Qualification ="'Assignee Login ID'=\"" + eng[8] + "\" AND 'Status' < 4", 
                                                                maxLimit=2, startRecord="", _soapheaders=[header_value])
                for entry in res:
                    entry['eng_id'] = eng[12]
            except Exception as e:
                print(e)
                return None
        return res
    
    @staticmethod
    def preprocessEntries(res):
        prep_res = []
        for entry in res:
            prj_id = entry['Incident_Number'] + ' ' + entry['Summary']
            assignee = entry['eng_id']
            company = entry['Company']
            sla = entry['SLA']
            prep_res.append((prj_id, assignee, company, sla))
        return prep_res
