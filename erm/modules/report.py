from datetime import timedelta
from itertools import groupby

from flask import url_for
from openpyxl import Workbook 

from .dateutils import dateutils
from .backend import backend


#INDIVIDUAL WORK REPORT
def get_engineer_tasks_sorted_by_id(eng_login, start, end):
    tasks = backend.get_engineer_booking(eng_login, start, end)
    tasks = sorted(tasks, key = lambda item:int(item[0]))
    return tasks

def generate_report_from_tasks(tasks):
    report_from_tasks = []
    tasks_sla_sorted = sorted(tasks, key=lambda item:(item[10], item[11]))
    for sla, grp in groupby(tasks_sla_sorted, key=lambda item:(item[10], item[11])):
        tasks_grp = list(grp)
        hours = int(sum([task[15] for task in tasks_grp], timedelta()).total_seconds()/60/60)
        report_from_tasks.append([tasks_grp[0][10], hours, sla[1]])
    return report_from_tasks

def calc_work_hours(tasks):
    for task in tasks:
        task.append(str(timedelta(seconds=task[9] - task [8])))
        task.append(timedelta(seconds=task[9] - task [8]))
        task[8] = dateutils.unix2iso_ru(task[8])
        task[9] = dateutils.unix2iso_ru(task[9])
    return tasks

def mark_edited_entries_in_saved_report(saved_report, report_from_tasks):
    report = []
    for item_from_db in saved_report:
        if item_from_db not in report_from_tasks:
            report.append(item_from_db + ['edited'])
        elif item_from_db in report_from_tasks:
            report.append(item_from_db + ['not_edited'])
    return report

def get_new_report_entries(report_from_tasks, saved_report_without_util):    
    report = []
    for item_from_tasks in report_from_tasks:
        item_from_tasks_without_util = [item_from_tasks[0], item_from_tasks[2]]
        if item_from_tasks_without_util not in saved_report_without_util:
            report.append(item_from_tasks + ['new'])
            new_tasks_added = True
    return report

def concat_reports(saved_report, report_from_tasks):
    saved_report_without_util = [[item[0], item[2]] for item in saved_report]
    if saved_report == []:
        report = get_new_report_entries(report_from_tasks, []) 
    elif saved_report != []:
        report = mark_edited_entries_in_saved_report(saved_report, report_from_tasks)
        report = report + get_new_report_entries(report_from_tasks, saved_report_without_util)
    return report

def check_if_new_tasks_added(report):
    new_tasks_added = False
    for entry in report:
        if entry[3] == 'new':
            new_tasks_added = True
    return new_tasks_added

def get_hourslimits(config):
    hourslimits = [0] + [int(limit) for limit in config.split(',')]
    return hourslimits

def get_premade_workreport_entries(config, report):
    premade = set([entry.strip() for entry in config.split(',')])
    report_lst = set([entry[0] for entry in report])
    premade = premade - report_lst
    return premade

#CONSOLIDATED WORK REPORT
def get_report_with_full_names(raw_report):
    report_with_full_names = []
    for raw in raw_report:
        engineer = backend.get_eng_info(raw[0])
        if len(engineer) != 0:
            eng_name, eng_login = engineer[0][1], engineer[0][12]
        else:
            eng_name, eng_login = '', ''
        raw[0] = {'name': eng_name, 'login': eng_login}
        report_with_full_names.append(raw)
    return report_with_full_names

def get_utils_dict(report_with_full_names):
    utils_dict = {}
    for row in report_with_full_names:
        utils_dict[' '.join([row[0]['name'], row[0]['login'], row[1], row[2]])] = row[3]
    return utils_dict

def get_engineers_not_reported_workload(reported_engineers):
    not_reported_engineers = []
    eng_list = [(eng[1], eng[7], eng[11]) for eng in backend.get_engineers_list()]

    engineers_names_from_consreport = [x[0] for x in reported_engineers]
    for eng in eng_list:
        if eng[0] not in engineers_names_from_consreport and eng[2] == 'yes':
            not_reported_engineers.append(eng[1])
    return not_reported_engineers

def generate_excel_report_file(month, year, companies_sla, engineers, utils_dict, app_path):
    wb = Workbook()
    ws = wb.active
    ws.title = '_'.join(['отчет', str(month), str(year)])
    if len(engineers) > 0:
        for row_num, row in enumerate(ws.iter_rows(min_row = 1, 
                                                   max_row = len(companies_sla) + 1, 
                                                   max_col = len(engineers) + 1)):
            if row_num == 0:
                for column_num, cell in enumerate(row):
                    if column_num == 0:
                        cell.value = 'Заказчик/договор'
                    else:
                        cell.value = engineers[column_num - 1][0]
            else:
                for (column_num, cell), engineer in zip(enumerate(row), [(0,)] + engineers):
                    if column_num == 0:
                        cell.value = ' '.join(companies_sla[row_num - 1])
                    else:
                        try:
                            cell.value = utils_dict[engineer[0] + ' ' + engineer[1] + ' ' + companies_sla[row_num - 1][0] + ' ' + companies_sla[row_num -1][1]]
                        except Exception:
                            pass

    report_file_name = 'otchet_po_trudozatratam' + str(month) + '_' + str(year) + '.xlsx'
    wb.save(app_path + '/static/' + report_file_name)
    excel_file_path = url_for('static', filename = report_file_name)   
    return excel_file_path

def get_companies_sla(report_with_full_names):
    companies_sla = set([(row[1], row[2]) for row in report_with_full_names])
    companies_sla = sorted(list(companies_sla), key = lambda sla:sla[0], reverse = True)
    return companies_sla
