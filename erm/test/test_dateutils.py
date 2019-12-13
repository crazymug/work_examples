from suir.modules.dateutils import dateutils
from datetime import datetime


def test_daterange_daily():
    d1 = datetime.strptime('2018-10-10T10:00','%Y-%m-%dT%H:%M')
    d2 = datetime.strptime('2018-10-12T16:00','%Y-%m-%dT%H:%M')

    assert [x for x in dateutils.daterange(d1, d2, 
                                           'daily')] == [('2018-10-10T10:00',
                                                          '2018-10-10T16:00'),
                                                         ('2018-10-11T10:00', 
                                                         '2018-10-11T16:00'), 
                                                         ('2018-10-12T10:00', 
                                                         '2018-10-12T16:00')]

def test_daterange_weekly():
    d1 = datetime.strptime('2018-10-10T10:00','%Y-%m-%dT%H:%M')
    d2 = datetime.strptime('2018-10-24T16:00','%Y-%m-%dT%H:%M')
    
    assert [x for x in dateutils.daterange(d1, d2, 
                                           'weekly')] == [('2018-10-10T10:00',
                                                           '2018-10-10T16:00'),
                                                          ('2018-10-17T10:00', 
                                                          '2018-10-17T16:00'), 
                                                          ('2018-10-24T10:00', 
                                                           '2018-10-24T16:00')]

def test_daterange_monthly():
    d1 = datetime.strptime('2018-10-10T10:00','%Y-%m-%dT%H:%M')
    d2 = datetime.strptime('2018-12-10T16:00','%Y-%m-%dT%H:%M')

    assert [x for x in dateutils.daterange(d1, d2, 
                                           'monthly')] == [('2018-10-10T10:00',
                                                            '2018-10-10T16:00'),
                                                           ('2018-11-10T10:00', 
                                                            '2018-11-10T16:00'), 
                                                           ('2018-12-10T10:00', 
                                                            '2018-12-10T16:00')]

def test_iso2unix():
    assert dateutils.iso2unix('2018-10-12T10:00') == 1539338400

def test_unix2iso():
    assert dateutils.unix2iso('1539338400') == '2018-10-12T10:00'

def test_unix2iso_ru():
    assert dateutils.unix2iso_ru('1539338400') == '12.10.2018 10:00'

def test_unix2iso_notime():
    assert dateutils.unix2iso('1539338400', 
                              time_info = False) == '2018-10-12'

def test_unix2iso_ru_notime():
    assert dateutils.unix2iso_ru('1539338400',
                                 time_info = False) == '12.10.2018'


def test_convert_booking_to_entries_percents():
    assert dateutils.convert_booking_to_entries('perc', 80, 6, 'daily',
                                        '2018-10-10', 
                                        '2018-10-12', 
                                        'Company1', 
                                        'SLA1') == [{'booking_type': 'perc',
           'company': 'Company1',
           'end_date': '2018-10-10T17:00',
           'hours': 6,
           'percent': 80,
           'repeat': 'daily',
           'sla': 'SLA1',
           'start_date': '2018-10-10T10:00'},
          {'booking_type': 'perc',
           'company': 'Company1',
           'end_date': '2018-10-11T17:00',
           'hours': 6,
           'percent': 80,
           'repeat': 'daily',
           'sla': 'SLA1',
           'start_date': '2018-10-11T10:00'},
          {'booking_type': 'perc',
           'company': 'Company1',
           'end_date': '2018-10-12T17:00',
           'hours': 6,
            'percent': 80,
            'repeat': 'daily',
           'sla': 'SLA1',
            'start_date': '2018-10-12T10:00'}]

    
def test_convert_booking_to_entries():
    assert dateutils.convert_booking_to_entries('hours', '', 6, 'daily', 
                                        '2018-10-10T10:00', 
                                        '2018-10-12T16:00', 
                                        'Company1', 
                                        'SLA1') == [{'booking_type': 'hours', 
                                                     'percent': '', 'hours': 6, 
                                                     'repeat': 'daily', 
                                                     'start_date': '2018-10-10T10:00', 
                                                     'end_date': '2018-10-10T16:00', 
                                                     'company': 'Company1', 
                                                     'sla': 'SLA1'},
                                                    {'booking_type': 'hours', 
                                                     'percent': '', 'hours': 6, 
                                                     'repeat': 'daily',
                                                     'start_date': '2018-10-11T10:00', 
                                                     'end_date': '2018-10-11T16:00', 
                                                     'company': 'Company1', 
                                                     'sla': 'SLA1'},
                                                    {'booking_type': 'hours', 
                                                     'percent': '', 'hours': 6, 
                                                     'repeat': 'daily',
                                                     'start_date': '2018-10-12T10:00', 
                                                     'end_date': '2018-10-12T16:00', 
                                                     'company': 'Company1', 
                                                     'sla': 'SLA1'}]

def test_convert_booking_to_entries_norepeat():
    assert dateutils.convert_booking_to_entries('hours', '', 6, 'no', 
                                                '2018-10-10T10:00', 
                                                '2018-10-12T16:00',
                                                'Company1', 
                                                'SLA1') == [{'booking_type': 'hours', 
                                                             'percent': '', 
                                                             'hours': 6, 
                                                             'repeat': 'no',
                                                             'start_date': '2018-10-10T10:00', 
                                                             'end_date': '2018-10-12T16:00',
                                                             'company': 'Company1', 
                                                             'sla': 'SLA1'}]

def test_replace_tmstps():
    bkinfo = (1, 'hours', 20, '20', 1, 5, 'проект 11', None, 
              1539770940, 1540065600)
    res_bk = (1, 'hours', 20, '20', 1, 5, 'проект 11', None, 
              '2018-10-17T10:09', '2018-10-20T20:00')
    assert dateutils.replace_tmstps(bkinfo) == list(res_bk)
