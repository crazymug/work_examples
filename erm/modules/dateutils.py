import unittest
from datetime import datetime
from datetime import timedelta
import calendar

class dateutils():
    '''date and time functions usefull for processing timelines'''
    
    @staticmethod
    def iso2unix(dt):
        '''accepts UTC time, returns unix timestamp as int'''
        try:
            timestamp = int((datetime.strptime(dt, "%Y-%m-%dT%H:%M") - datetime(1970,1,1)).total_seconds())
        except ValueError:
            timestamp = int((datetime.strptime(dt, "%Y-%m-%d") - datetime(1970,1,1)).total_seconds())
        except Exception:
            return None
        return timestamp
    
    @staticmethod
    def unix2iso_ru(timestamp, time_info = True):
        '''accepts unix timestamp, returns UTC time in ISO 8601 format'''
        if time_info == True:
            dt = datetime.utcfromtimestamp(int(timestamp)).strftime('%d.%m.%Y %H:%M')
        elif time_info == False:
            dt = datetime.utcfromtimestamp(int(timestamp)).strftime('%d.%m.%Y')
        return dt
    
    @staticmethod
    def unix2iso(timestamp, time_info = True):
        '''accepts unix timestamp, returns UTC time in ISO 8601 format'''
        if time_info == True:
            dt = datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%dT%H:%M')
        elif time_info == False:
            dt = datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
        return dt
        
    @staticmethod
    def daterange(d1, d2, repeat):
        '''date range generator with respect to repeatance type in repeat var (daily, weekly, monthly)
        daily repeat generates list of tuples of days with same timeframes
        weekly repeat generates list of tuples of days every week on specific weekday (e.g. every monday)
        monthly repeat generates list of tuples of days every month on specific day of month
        (e.g. every 10th day of every month)'''

        if d2 > d1:
           day_start = d1
           work_timeframe = d2.time().hour - d1.time().hour
           day_end = d1 + timedelta(hours=work_timeframe)

           while day_end <= d2:
               yield (datetime.strftime(day_start, '%Y-%m-%dT%H:%M'), 
                      datetime.strftime(day_end, '%Y-%m-%dT%H:%M'))
               if repeat == 'daily':
                   day_start = day_start + timedelta(days=1)
                   day_end = day_end + timedelta(days=1)
               elif repeat == 'weekly':
                   day_start = day_start + timedelta(days=7)
                   day_end = day_end + timedelta(days=7)
               elif repeat == 'monthly':
                   _month_days = calendar.monthrange(day_start.year, 
                                                     day_start.month)[1] 
                   day_start = day_start + timedelta(days=_month_days)
                   day_end = day_end + timedelta(days=_month_days)
 

    @staticmethod
    def convert_booking_to_entries(booking_type, percent, hours, 
                                   repeat, start_date, end_date, company, sla):
        '''prepare booking info entries for inserting into booking db table, return list if dicts var
        start_date and end_date is datetime.datetime instances

        if booking_type is percent - start date frame from begining of work day (AM time in workday_start var)
        for weekly repeatance - choose weekday as start_date's weekday
        for monthly repeatance - choose month day as start_date's month day
        
        function uses datetime and calendar standard modules
        '''
        
        if percent == '':
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
            end_date_obj =  datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
        elif int(percent) > 0:
            start_date_obj = datetime.strptime(start_date, 
                                               '%Y-%m-%d') + timedelta(hours = 10)
            task_duration = timedelta(hours = (9 * (int(percent)/100) + 10))
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') + task_duration

 
        booking_entries = []
        
        

        if repeat != 'no':
            for (d_s, d_e) in dateutils.daterange(start_date_obj, 
                                                  end_date_obj, repeat):
                booking_entries.append({'booking_type': booking_type, 
                                        'percent': percent, 'hours': hours, 
                                        'repeat': repeat, 'start_date': d_s, 
                                        'end_date': d_e, 'company': company, 
                                        'sla': sla})
        elif repeat == 'no':
            booking_entries.append({'booking_type': booking_type, 
                                    'percent': percent, 'hours': hours, 
                                    'repeat': repeat,
                                    'start_date': datetime.strftime(start_date_obj, 
                                                                    '%Y-%m-%dT%H:%M'),
                                    'end_date': datetime.strftime(end_date_obj, 
                                                                  '%Y-%m-%dT%H:%M'), 
                                    'company': company, 'sla': sla})

        return booking_entries

    @staticmethod
    def replace_tmstps(bk):
        '''replaces all unix timestamps with ISO 8601 in select from booking table (from app db)'''

        bk_updated = list(bk)
        bk_updated[8] = dateutils.unix2iso(bk[8])
        bk_updated[9] = dateutils.unix2iso(bk[9])
        return bk_updated
