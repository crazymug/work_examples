from flask import flash

from .backend import backend
from .message import message as msg
from .exceptions import MessagingError


def get_booking_info_from_request(request):
    booking = {}
    booking['booking_type'] = request.form['type']
    booking['percent'] = request.form['perchours']
    booking['hours'] = ""
    booking['resource_login'] = request.form['res_login']
    booking['project_id'] = request.form['proj_id']
    booking['repeat'] = request.form['repeat']
    booking['company'] = request.form['company']
    booking['sla'] = request.form['sla']
    booking['start_date'] = request.form['start_datetime']
    booking['end_date'] = request.form['end_datetime']
    return booking

def send_task_added_messages(project_id, username, resource_login, config):
    msg_send_status = msg.send_sms('Вам назначена задача на http://st-erm: ' + project_id + ' :' + username, 
                                   resource_login, 
                                   config['sms_login'], config['sms_pwd'], config['sms_originator'])
    #app.logger.info(msg_send_status)
    #msg_send_status = msg.send_sms_to_head('Инженеру назначена задача на http://st-erm: ' + project_id, 
    #                                       resource_login, conf_dict['sms_login'], conf_dict['sms_pwd'])
    if msg_send_status[0] == 'ERROR':
        raise MessagingError(msg_send_status[1])
    return msg_send_status

def set_timeline_hist_or_act(start, end):
    if (start == '0') and (end == '0'):
        act_hist = 'act'
    else:
        act_hist = 'hist'
    return act_hist

def add_booking_entries(booking_entries):
    for entry in booking_entries:
        data = backend.add_booking_entry(**entry)
    if data == []:
        flash('Задача успешно добавлена', 'info')
    return data

def get_booking_entries_short_description(eng_list_login_name, start_date, end_date):
    activities_short_description = []

    for eng in eng_list_login_name:
        activities = backend.get_engineer_booking(eng['login'], start_date, end_date)
        eng_activities = [{'id':act[0], 'descr': act[6], 'company': act[10], 'sla': act[11], 
                           'eng': eng['fullname']} for act in activities]
        if eng_activities:
            for act in eng_activities:
                activities_short_description.append(act)
    return activities_short_description
