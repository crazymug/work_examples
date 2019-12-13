import time

from .ersmm import ersmm

class resource():
    '''class represents resources(engineers) and their available func and fields'''

    def __init__(self, eng_login):
        self.eng_login = eng_login
        self.booking = self.__get_booking(eng_login)
        self.cur_week_booking = self.__get_cur_week_booking(self.booking)
        self.workload = self.__calc_workload(self.cur_week_booking)
        self.phone = self.__get_phone_number(eng_login)

    def __get_booking(self, eng_login):
        '''get all booking info for specific engineer's id'''
        bking = ersmm.get_eng_booking_info(eng_login, None)
        return bking
    
    def __is_in_week_daterange(self, bk):
        '''NEED TO MOVE TO dateutils.py'''
        '''checks if booking entry in current week dateframe'''
        return not set(range(int(time.time()/60), 
                             int(time.time()/60) + 7*24*60)).isdisjoint(range(
                                                                              int(bk[7]/60), int(bk[8]/60)))
    
    def __get_cur_week_booking(self, booking):
        '''get current week booking info from given booking info'''
        #week_booking = ersmm.get_eng_booking_week(eng_login)
        week_booking = list(filter(self.__is_in_week_daterange, booking)) 
        return week_booking

    def __trunc_dateframes(self, cur_week_booking):
        '''NEED TO MOVE TO dateutils.py'''
        '''truncates start and end time in dateframes that partially belongs to current week dateframe'''
        res_timeline = []
        cur_time = int(time.time())

        for dateframe in cur_week_booking:
            if dateframe[7] < cur_time: 
                res_timeline.append((cur_time, dateframe[8]))
            elif dateframe[8] > (cur_time + 7*24*60*60): 
                res_timeline.append((dateframe[7], cur_time + 7*24*60*60))
            else: 
                res_timeline.append((dateframe[7], dateframe[8]))
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

    def __get_phone_number(self, eng_login):
        eng_info = ersmm.get_eng_info(eng_login)
        return eng_info[0][2]
