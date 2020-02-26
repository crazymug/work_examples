import unittest.mock as mock

import pytest

from suir.modules.integration import externalSystem, Jira, Remedy_CHG, Remedy_HPD
from suir.modules.exceptions import NoDataError

def get_external_system_instance(system_class):
    usr = 't_testov'
    pswd = '123'
    url = 'http://test'
    system_instance = system_class(usr, pswd, url)
    return system_instance

@mock.patch('suir.modules.integration.externalSystem.connect')
@mock.patch('suir.modules.integration.Remedy.connect')
@mock.patch('suir.modules.integration.Remedy_HPD.get_raw_entries')
@mock.patch('suir.modules.integration.Remedy_CHG.get_raw_entries')
@mock.patch('suir.modules.integration.Jira.get_raw_entries')
def get_entries_from_system(system_instance, engineer, 
                            jira_get_raw_entries,
                            remedy_chg_get_raw_entries,
                            remedy_hpd_get_raw_entries, 
                            remedy_connect,
                            connect):
    remedy_connect.return_value = True
    connect.return_value = True
    jira_get_raw_entries.return_value =  [{'fields': 
                                               {'assignee': {'active': True,
                                                             'displayName': 'T.Testov',
                                                             'emailAddress': 't_testov@test.com',
                                                             'name': 't_testov'},
                                               'created': '2019-02-11T17:05:12.000+0400',
                                               'description': 'Task description',
                                               'project': {'key': 'SERVICEML',
                                                           'name': 'Автоклассификатор заявок (активно)'},
                                     'summary': 'Task description'},
                                     'id': '14714',
                                     'key': 'SERVICEML-5'},
                            {'fields': 
                                       {'assignee': {'active': True,
                                                     'displayName': 'T.Testov',
                                                     'emailAddress': 't_testov@test.com',
                                                     'name': 't_testov'},
                                       'created': '2019-02-11T12:10:32.000+0400',
                                       'description': 'Task description',
                                       'project': {'key': 'ERM',
                                                   'name': 'Трекер задач (активно)'},
                             'summary': 'Task description'},
                             'id': '13582',
                             'key': 'ERM-73'}]
   
    remedy_chg_get_raw_entries.return_value = []
    remedy_hpd_get_raw_entries.return_value = []

    if system_instance.connect() == True:
        entries = system_instance.get_entries(engineer)
    else:
        entries = []
    return entries




@pytest.mark.parametrize('system_class', [Jira, Remedy_HPD, Remedy_CHG])
def test_connecting_to_external_system(system_class):
    external_system = get_external_system_instance(system_class) 
    assert external_system.connect() == True

@pytest.mark.parametrize('system_class, expected_entries', [[Jira, [1, 2, 3]], 
                                                            [Remedy_HPD, [1, 2, 3]],
                                                            [Remedy_HPD, [1, 2, 3]]])
def test_connecting_and_getting_entries_from_external_system(system_class, expected_entries):
    engineer = [57790,  'Умаров Герман Шавкатович',
               '9851799623', 'web php javascript bmc remedy linux',
               'test', '1522-6 Отдел автоматизации ИТ процессов',
               'Начальник отдела',
               'umarov.german@gmail.com',
               'german', 'g_umarov', '', 'yes', 't_testov', 'Английский']

    external_system = get_external_system_instance(system_class)
    entries = get_entries_from_system(external_system, engineer)
    assert entries == expected_entries

@pytest.mark.parametrize('system_class, expected_preproced_entries', [[Jira, 
                                                                       [('SERVICEML-5 Task description', 
                                                                         't_testov', 
                                                                         'Стэп Лоджик', 
                                                                         'SERVICEML'), 
                                                                         ('ERM-73 Task description', 
                                                                          't_testov', 'Стэп Лоджик', 
                                                                          'ERM')]], 
                                                                     [Remedy_HPD, [1, 2, 3]],
                                                                     [Remedy_CHG, [1, 2, 3]]])
def test_external_system_entries_preprocessing(system_class, expected_preproced_entries):
    engineer = [57790,  'Умаров Герман Шавкатович',
               '9851799623', 'web php javascript bmc remedy linux',
               'test', '1522-6 Отдел автоматизации ИТ процессов',
               'Начальник отдела',
               'umarov.german@gmail.com',
               'german', 'g_umarov', '', 'yes', 't_testov', 'Английский']

    external_system = get_external_system_instance(system_class)
    entries = get_entries_from_system(external_system, engineer)
    preprocessed_entries = external_system.preprocess_entries(entries)
    assert preprocessed_entries == expected_preproced_entries 


@mock.patch('suir.modules.backend.backend.update_booking')
@pytest.mark.parametrize('system_class', [Jira, Remedy_HPD, Remedy_CHG])
def test_sending_external_system_tasks_to_backend_for_booking_update(update_booking, system_class):
    update_booking.return_value = '200'

    engineer = [57790,  'Умаров Герман Шавкатович',
               '9851799623', 'web php javascript bmc remedy linux',
               'test', '1522-6 Отдел автоматизации ИТ процессов',
               'Начальник отдела',
               'umarov.german@gmail.com',
               'german', 'g_umarov', '', 'yes', 't_testov', 'Английский']

    external_system = get_external_system_instance(system_class)

    entries = get_entries_from_system(external_system, engineer)
    preprocessed_entries = external_system.preprocess_entries(entries)
    status = external_system.send_booking_to_backend(preprocessed_entries)
    assert status == '200'

@mock.patch('suir.modules.backend.backend.add_booking_entry')
@mock.patch('suir.modules.backend.backend.update_booking')
@pytest.mark.parametrize('system_class', [Jira, Remedy_HPD, Remedy_CHG])
def test_sending_external_system_tasks_to_backend_for_booking_create(update_booking,
                                                                     add_booking_entry, 
                                                                     system_class):
    add_booking_entry.return_value = '200'
    update_booking.side_effect = NoDataError('по задачам')
    
    engineer = [57790,  'Умаров Герман Шавкатович',
               '9851799623', 'web php javascript bmc remedy linux',
               'test', '1522-6 Отдел автоматизации ИТ процессов',
               'Начальник отдела',
               'umarov.german@gmail.com',
               'german', 'g_umarov', '', 'yes', 't_testov', 'Английский']

    external_system = get_external_system_instance(system_class)

    entries = get_entries_from_system(external_system, engineer)
    preprocessed_entries = external_system.preprocess_entries(entries)
    status = external_system.send_booking_to_backend(preprocessed_entries)
    assert status == '200'
