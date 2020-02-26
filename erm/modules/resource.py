import unittest
import time

from .backend import backend

class resource():
    '''class represents resource(engineer) and their available func and fields'''

    def __init__(self, eng_login):
        self.eng_login = eng_login
        self.cur_week_booking = backend.get_eng_booking_week(eng_login)  
        self.workload = self.__calc_workload(self.cur_week_booking)
        self.__set_info()

    def __lt__(self, other):
        return self.workload < other.workload

    def __set_info(self):
        eng_info = backend.get_eng_info(self.eng_login)
        if len(eng_info) != 0:
            self.full_name = eng_info[0][1]
            self.phone = eng_info[0][2]
            self.tags = eng_info[0][3]
            self.skills = eng_info[0][4]
            self.org_unit_id = eng_info[0][5]
            self.type = eng_info[0][6]
            self.e_mail = eng_info[0][7]
            self.rem_id = eng_info[0][8]
            self.jira_id = eng_info[0][9]
            self.sharepoint_id = eng_info[0][10]
            self.utilized = eng_info[0][11]
            self.langs = eng_info[0][13]
        else:
            self.full_name = ''

    def __trunc_dateframes(self, cur_week_booking):
        '''NEED TO MOVE TO dateutils.py'''
        '''truncates start and end time in dateframes that partially belongs to current week dateframe'''
        res_timeline = []
        cur_time = int(time.time())

        for dateframe in cur_week_booking:
            if dateframe[8] < cur_time: 
                res_timeline.append((cur_time, dateframe[8]))
            elif dateframe[9] > (cur_time + 7*24*60*60): 
                res_timeline.append((dateframe[8], cur_time + 7*24*60*60))
            else: 
                res_timeline.append((dateframe[8], dateframe[9]))
        return res_timeline

    def __calc_workload(self, cur_week_booking):
        '''calculates workload for specific engineer.
        Workload is calculated as percent of engineers next week planned
        workload.
        Workload % = (busy timeline dateframes/overall timeline dateframe)*100%
        Busy dateframes is calculated with accounting tasks overlays'''
        res_timeline = []
        preproc_timeline = self.__trunc_dateframes(cur_week_booking)
        
        timeline = [set(range(int(x[0]/60), int(x[1]/60))) for x in preproc_timeline] 

        for dateframe in timeline:
            for n_dateframe in timeline:
                if dateframe < n_dateframe:
                    break
            else:
                res_timeline.append(dateframe)

        busy_timeline = 0
        for dateset in res_timeline:
            busy_timeline += len(dateset)
        
        if busy_timeline > (7*24*60): busy_timeline = 7*24*60

        workload = int((busy_timeline / (7*24*60)) * 100)
        return workload

    @staticmethod
    def get_resources_sorted_by_workload(logins):
        resources = []
        for login in logins:
            resources.append(resource(login[0]))
        resources_sorted_by_workload = sorted(resources)
        return resources_sorted_by_workload

    @staticmethod
    def get_engineer_info_from_request(request):
        engineer = {}
        engineer['fullname'] = request.form['fullname']
        engineer['phone'] = request.form['phone']
        engineer['tags'] = request.form['tags']
        engineer['skills'] = request.form['skills']
        engineer['org_unit'] = request.form['org_unit']
        engineer['eng_type'] = request.form['type']
        engineer['email'] = request.form['email']
        engineer['rem_id'] = request.form['rem_id']
        engineer['jira_id'] = request.form['jira_id']
        engineer['suir_id'] = request.form['suir_id']
        engineer['util'] = request.form['util']
        engineer['langs'] = request.form['langs']
        engineer['sharepoint_id'] = request.form['sharepoint_id']
        return engineer 
