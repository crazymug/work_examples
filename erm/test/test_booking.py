import pytest
import unittest.mock as mock

from suir.modules.booking import *


def form_request():
    request = mock.Mock()
    request.form = {}
    request.form['type'] = 1
    request.form['perchours'] = 'hours'
    request.form['res_login'] = 't_testov'
    request.form['proj_id'] = 'Тестовая задача'
    request.form['repeat'] = 'weekly'
    request.form['company'] = 'Вектор-М'
    request.form['sla'] = 'ST024458-123'
    request.form['start_datetime'] = '10:20H08-01-2020'
    request.form['end_datetime'] = '15:30H07-01-2020'
    return request

def form_booking():
    booking = {}
    booking['booking_type'] = 1
    booking['percent'] = 'hours' 
    booking['hours'] = ''
    booking['resource_login'] = 't_testov'
    booking['project_id'] = 'Тестовая задача'
    booking['repeat'] = 'weekly'
    booking['company'] = 'Вектор-М'
    booking['sla'] = 'ST024458-123'
    booking['start_date'] = '10:20H08-01-2020'
    booking['end_date'] = '15:30H07-01-2020'
    return booking

def test_get_booking_info_from_request():
    request = form_request()
    booking = form_booking()
    assert booking == get_booking_info_from_request(request)


def get_config():
    config = {}
    config['sms_login'] = 'sms_login'
    config['sms_pwd'] = 'some_sms_pswd'
    config['sms_originator'] = 'COMPANY'
    return config

@mock.patch('suir.modules.booking.msg', autospec=True)
def test_send_task_added_messages_is_ok(msg):
    msg.send_sms.return_value = 'OK'
    config = get_config()
    assert send_task_added_messages('Задача 1', 'n_boss', 't_testov', config) == 'OK'


@mock.patch('suir.modules.booking.msg', autospec=True)
def test_send_task_added_messages_with_error(msg):
    msg.send_sms.return_value = 'ERROR'
    config = get_config()
    assert send_task_added_messages('Задача 1', 'n_boss', 't_testov', config) == 'ERROR'


def test_set_timeline_as_history():
    assert set_timeline_hist_or_act('0', '1539494939') == 'hist'
    assert set_timeline_hist_or_act('1321323434', '0') == 'hist'
    assert set_timeline_hist_or_act('1321323434', '1539494939') == 'hist'

def test_set_timeline_as_active():
    assert set_timeline_hist_or_act('0', '0') == 'act'

@mock.patch('suir.modules.booking.backend', autospec=True)
@mock.patch('suir.modules.booking.flash', autospec=True)
def test_adding_booking_entries(flash, backend):
    booking_entries = [form_booking() for x in range(0,10)] 
    backend.add_booking_entry.return_value = [], '200', ''
    assert add_booking_entries(booking_entries) == '200' 


def form_activities(eng_list_login_name):
    activities = []
    for eng_login_name in eng_list_login_name:
        activities.append({'id': 57795, 'descr': "test 5", 'company': "Beeline", 'sla': 'sla2',
                           'eng': eng_login_name['fullname']})
    return activities

def return_different_engineers_booking(eng_login, start_date, end_date):
    return [[57795, "hours", "", "", 1, 0,
             "test 5", "no", 1579514400, 1582196400, 
             "Beeline", "sla2", 0, eng_login]]

@mock.patch('suir.modules.booking.backend', autospec=True)
def test_get_booking_entries_short_description(backend):
    backend.get_engineer_booking.side_effect = return_different_engineers_booking

    eng_list_login_name = [{'login': 't_testov1', 'fullname': 'T. Testov I'}, 
                           {'login':'t_testov2', 'fullname': 'T. Testov II'}]

    activities = form_activities(eng_list_login_name)
    assert get_booking_entries_short_description(eng_list_login_name, 
                                            '2020-01-20T10:00', 
                                            '2020-02-20T11-00') == activities
