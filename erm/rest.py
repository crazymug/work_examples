import json
import logging
import configparser
from os import environ, urandom
import hashlib
import secrets
import time
from datetime import date, datetime, timedelta
import pickle
import re

import psycopg2
from flask import Flask, g, request, flash, abort

from .modules.dateutils import dateutils as dateutils
from .modules.message import message as msg

'''ERM application REST interface'''

'''Initialization'''
app = Flask(__name__) 
app.secret_key = urandom(16)

# two options for logging: through Flask dev logger or Gunicorn built-in
if __name__ != '__main__':
    gunicorn_error_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers.extend(gunicorn_error_logger.handlers)
    app.logger.setLevel(logging.INFO)
else:
    app.logger.addHandler(logging.FileHandler('erss.log'))

def read_app_config(conf_file_name):
    '''read and return application configuration dictionary'''
    config = configparser.ConfigParser()
    try:
        config.read(conf_file_name)
    except configparser.ParsingError:
        app.logger.error(''.join(('Error reading application configuration file ',
                                  conf_file_name)))
        exit() #need testing
    app.config['sms_login'] = config['General']['SMS_login']
    app.config['sms_pwd'] = config['General']['SMS_pwd']
    app.config['db_name'] = config['General']['DB_name']
    app.config['db_user'] = config['General']['DB_user']
    app.config['db_pass'] = config['General']['DB_pass']
    app.config['db_host'] = config['General']['DB_host']


read_app_config(environ['SUIR_CFG'])

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(dbname = app.config['db_name'], 
                                user = app.config['db_user'], password = app.config['db_pass'], 
                                host = app.config['db_host'])
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.commit()
        db.close()

def add_db_connection_error_msg(func):
    def func_with_msg(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            app.logger.error('DB operational error, check DB engine status, or connection to DB')
            return abort(503) 
    return func_with_msg

@app.route('/rest/consworkrep/<int:month>/<int:year>', methods = ['GET'])
def consworkrep(month, year):
    cur = get_db().cursor()
    cur.execute('select resource_login, company, project_ids, util_hours from workrep where month = %s and year = %s', (month, year))
    all_reports = cur.fetchall()

    if len(all_reports) == 0:
        abort(404)

    return json.dumps(all_reports)

@app.route('/rest/workrep/<string:login>/<int:month>/<int:year>', methods = ['GET', 'POST'])
def workrep(login, month, year):
    if request.method == 'GET':
        cur = get_db().cursor()
        cur.execute('select company, util_hours, project_ids from workrep where resource_login = %s and month = %s and year = %s', (login, month, year))
        rep = cur.fetchall()
        if len(rep) == 0:
            abort(404)
        return json.dumps(rep)

    elif request.method == 'POST':
        report = request.form.to_dict()
        cur = get_db().cursor()
        while report:
            util_hours = report.popitem()
            sla = report.popitem()
            item = report.popitem()
            if int(util_hours[1]) > 0:
                cur.execute('insert into workrep values(%s, %s, %s, %s, %s, %s, %s) on conflict(resource_login, company, project_ids, month, year) do update set util_hours=%s', (1, item[1], sla[1], util_hours[1], month, year, login, util_hours[1]))
        return json.dumps('OK')


@app.route('/rest/eng_booking_interval/<string:eng_login>/<string:start>/<string:end>', methods=['GET'])
def eng_booking_interval(start = None, end = None, eng_login = None):
    ONE_WEEK_SECONDS = 604800

    if start != '0':
        req_start_date = dateutils.iso2unix(start)
    else:
        req_start_date = 0

    if end != '0':
        req_end_date = dateutils.iso2unix(end)
    else:
        req_end_date = 10000000000000
    
    if start == '0' and end == '0':
        req_start_date = int(time.time())
        req_end_date = req_start_date + ONE_WEEK_SECONDS 
    
    cur = get_db().cursor() 
    
    cur.execute('select oid, * from booking where ' 
                'resource_login=%(eng_login)s and '
                '((start_date >=%(req_start_date)s and end_date <= %(req_end_date)s) or '
                '(start_date < %(req_start_date)s and '
                'end_date >= %(req_start_date)s and end_date < %(req_end_date)s) or '
                '(end_date > %(req_end_date)s and '
                'start_date > %(req_start_date)s and start_date <= %(req_end_date)s) or '
                '(start_date < %(req_start_date)s and end_date > %(req_end_date)s))', 
                 {'eng_login': eng_login, 'req_start_date': req_start_date,
                     'req_end_date': req_end_date})

    res = cur.fetchall()
    if len(res) == 0:
        abort(404)
    return json.dumps(res)


@app.route('/rest/eng_booking/<string:eng_login>/<string:prj_id>', methods=['POST', 'GET', 'DELETE', 'PATCH'])
def eng_booking(eng_login, prj_id):
    cur = get_db().cursor()
    if request.method == 'GET':
        if prj_id  == '0':
            cur.execute('select * from booking where resource_login = %s and active = 1', (eng_login,))
        elif prj_id != '0':
            cur.execute('select * from booking where resource_login = %s and project_id like %s and active = 1', (eng_login, '%' + prj_id + '%'))
        res = cur.fetchall()
        if len(res) == 0: 
            abort(404)
        return json.dumps(res)

    elif request.method == 'POST':
        booking_type = request.form['booking_type'] 
        percent = request.form['percent']
        hours = request.form['hours']
        active = 1
        resource_login = request.form['res_login'] 
        project_id = request.form['project_id']
        repeat = request.form['repeat'] 
        company = request.form['company']
        start_date = dateutils.iso2unix(request.form['start_datetime'])
        end_date = dateutils.iso2unix(request.form['end_datetime'])
        sla = request.form['sla'] 
        cur.execute('insert into booking values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (booking_type, percent, hours, active, 0, project_id, repeat, start_date, end_date, company, sla, 0, resource_login))
        return json.dumps('Booked engineer')

    elif request.method == 'PATCH':
        project_id = request.form['prj_id']
        assignee = request.form['res_login']
        sla = request.form['sla']
        one_hour_delta = timedelta(hours = 1)
        end_datetime = datetime.today() + one_hour_delta
        end_date = dateutils.iso2unix(str(end_datetime.date()) + 'T' + str(end_datetime.hour) + ':' + str(end_datetime.minute))
        cur.execute('update booking set end_date=\''+ str(end_date) +'\', sla=%s where project_id like %s', (sla, project_id + '%', ))
        if cur.statusmessage == 'UPDATE 0':
            abort(404)
        return json.dumps('Updated booking for engineer')

    elif request.method == 'DELETE':
        cur.execute('delete from booking where resource_login = %s', (eng_login, ))
        return json.dumps('Deleted engineer booking') 


@app.route('/rest/spec_booking/<int:booking_id>', methods=['DELETE'])
def spec_booking(booking_id):
    return json.dumps('Deleted booking info with id = {0}'.format(booking_id))

@app.route('/rest/eng/<string:eng_login>', methods = ['GET', 'POST', 'PATCH', 'DELETE'])
@add_db_connection_error_msg
def operate_on_engineer_data(eng_login):
    cur = get_db().cursor()

    if request.method == 'GET':
        cur.execute('select oid, * from resources where suir_id = %s', (eng_login,))
        res = cur.fetchall()
        if len(res) == 0: 
            abort(404)
        return json.dumps(res)

    elif request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        tags = request.form['tags']
        skills = request.form['skills']
        org_unit = request.form['org_unit']
        eng_type = request.form['type']
        email = request.form['email']
        rem_id = request.form['rem_id']
        jira_id = request.form['jira_id']
        util = request.form['util']
        suir_id = request.form['suir_id']
        sharepoint_id = request.form['sharepoint_id']
        langs = request.form['langs']

        cur.execute('insert into resources values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                    (fullname, phone, tags, skills, org_unit, eng_type, email, 
                     rem_id, jira_id, sharepoint_id, util, suir_id, langs))
        return json.dumps('Added new engineer')


    elif request.method == 'DELETE':
        cur.execute('delete from resources where suir_id = %s', (eng_login, ))
        app.logger.info('Deleted engineer with suir_id = {0}'.format(eng_login))

    elif request.method == 'PATCH':
        fullname = request.form['fullname']
        phone = request.form['phone']
        tags = request.form['tags']
        skills = request.form['skills']
        org_unit = request.form['org_unit']
        eng_type = request.form['type']
        email = request.form['email']
        rem_id = request.form['rem_id']
        jira_id = request.form['jira_id']
        util = request.form['util']
        suir_id = request.form['suir_id']
        sharepoint_id = request.form['sharepoint_id']
        langs = request.form['langs']

        cur.execute('update resources set full_name = %s, phone = %s, tags = %s, skills = %s, org_unit_id = %s, type = %s, e_mail = %s, rem_id = %s, jira_id = %s, sharepoint_id = %s, suir_id = %s, utilized = %s, langs = %s where suir_id=%s', (fullname, phone, tags, skills, org_unit, eng_type, email, rem_id, jira_id, sharepoint_id, suir_id, util, langs, eng_login)) 
        return json.dumps('Updated record')


@app.route('/rest/eng_list', methods = ['GET'])
def eng_list():
    cur = get_db().cursor()
    if request.method == 'GET':
        cur.execute('select oid, * from resources')
        res = cur.fetchall()
        if len(res) == 0: 
            abort(404)
        return json.dumps(res)
 
@app.route('/rest/search/<string:search_string>', methods = ['GET'])
def search_rest(search_string):
    cur = get_db().cursor()
    res = []
    for search_word in search_string.split():
        search_word_like = '%' + search_word + '%'

        cur.execute('select suir_id from resources where skills ilike %s', (search_word_like, ))
        res_skills = cur.fetchall()
        cur.execute('select suir_id from resources where tags ilike %s', (search_word_like, ))
        res_tags = cur.fetchall()
        cur.execute('select suir_id from resources where org_unit_id ilike %s', (search_word_like, ))
        res_org_unit = cur.fetchall()
        cur.execute('select suir_id from resources where full_name ilike %s', (search_word_like, ))
        res_full_name = cur.fetchall()
        
        res = res + res_skills + res_tags + res_full_name + res_org_unit

        res = list(set(res))
    if len(res) == 0:
        abort(404)
    return json.dumps(res)

@app.route('/rest/get_eng_login/<string:fullname>', methods = ['GET'])
def get_eng_login(fullname):
    cur = get_db().cursor()
    res = []
    cur.execute('select oid, * from resources where full_name = %s', (fullname, ))
    res = cur.fetchall()
    return json.dumps(res)


@app.route('/rest/gentags', methods = ['POST'])
def gen_tags():
    '''Generate tags for given text on predefined tags dictionary basis''' 
    with open('tags_dict.pickle', 'rb') as tags_dict_file:
        words = pickle.load(tags_dict_file)

    tags = []
    prep_text_rw = re.sub('[^A-Za-z]+', ' ', request.form['texttotag'].lower())

    for word in prep_text_rw.split():
        if word in words:
            if words[word] > 3: 
                tags.append(word)
                if len(tags) == 10: break
    
    res_tags = set(sorted(tags, key=lambda x:x[0]))
    
    return json.dumps(list(res_tags))

@app.route('/rest/check_credentials/<string:login>/<string:pswd>', 
           methods = ['GET'])
def check_credentials(login, pswd):
    cur = get_db().cursor()
    cur.execute('select pswd_hash, salt from users where login = %s',
                (login, ))
    res = cur.fetchall()
    if res:
        pswd_hash = res[0][0]
        salt = res[0][1]
    else:
        return json.dumps(False)

    hsh =  bytes(''.join((pswd, salt)), 'UTF-8')
    given_pswd_hash = hashlib.sha256(hsh).hexdigest()
    if given_pswd_hash == pswd_hash:
        cur.execute('update users set last_logged_in=%s where login=%s',
                    (int(time.time()), login))
        return json.dumps(True)
    else:
        return json.dumps(False)

@app.route('/rest/get_user_group/<string:login>', methods = ['GET'])
def get_user_group(login):
    cur = get_db().cursor()
    cur.execute('select user_group from users where login = %s', (login, ))
    user_group = cur.fetchall()[0][0]
    return json.dumps(user_group)

@app.route('/rest/get_user_oid/<string:login>', methods = ['GET'])
def get_user_oid(login):
    cur = get_db().cursor()
    cur.execute('select oid from users where login = %s', (login, ))
    oid = cur.fetchall()[0][0]
    return json.dumps(oid)

@app.route('/rest/user/<string:login>', methods = ['GET'])
def user(login):
    if request.method == 'GET':
        cur = get_db().cursor()
        cur.execute('select * from users where login = %s', (login,))
        user = cur.fetchall()[0]
        user_proc = {}
        user_proc['name'] = user[0]
        user_proc['login'] = user[1]
        user_proc['active'] = user[4]
        user_proc['last_logged_in'] = dateutils.unix2iso_ru(user[5])
        user_proc['created'] = dateutils.unix2iso_ru(user[6])
        user_proc['modified'] = dateutils.unix2iso_ru(user[7])
        user_proc['user_group'] = user[8]
        user_proc['phone'] = user[9]
        return json.dumps(user_proc)

@app.route('/rest/users', methods = ['GET', 'POST', 'PATCH'])
def users():
    if request.method == 'GET':
        cur = get_db().cursor()
        cur.execute('select * from users')
        users = cur.fetchall()
        users_proc = []
        user_proc = {}
        for user in users:
            user_proc['name'] = user[0]
            user_proc['login'] = user[1]
            user_proc['active'] = user[4]
            user_proc['last_logged_in'] = dateutils.unix2iso_ru(user[5])
            user_proc['created'] = dateutils.unix2iso_ru(user[6])
            user_proc['modified'] = dateutils.unix2iso_ru(user[7])
            user_proc['user_group'] = user[8]
            user_proc['phone'] = user[9]
            users_proc.append(user_proc)
            user_proc = {}
        return json.dumps(users_proc)

    elif request.method == 'POST':
        cur = get_db().cursor()
        pswd = secrets.token_hex(4)
        salt = secrets.token_hex(32)
        pswd_hash = hashlib.sha256(bytes(''.join((pswd, salt)), 
                                         'UTF-8')).hexdigest()

        cur.execute('insert into users values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                    (request.form['username'], request.form['login'], 
                     pswd_hash, salt, 1, 0, 
                     int(time.time()), 0, request.form['user_group'], 
                     request.form['phone']))

        msg_send_status = msg.send_sms(' '.join(('Вам создана учетная запись', 
                                                 'на http://st-erm ', 
                                                 request.form['login'],
                                                 pswd)), 
                                       0, app.config['sms_login'], 
                                       app.config['sms_pwd'],
                                       request.form['phone'])
        if msg_send_status == 'ERROR': 
            app.logger.error('Error sending SMS')
            flash('Не удалось отправить SMS пользователю. Обратитесь к разработчику', 'error')
        return json.dumps(pswd)
    elif request.method == 'PATCH':
        return json.dumps('OK')

@app.route('/rest/update_pswd/<string:login>', methods = ['GET'])
def update_pswd(login):
    pswd = secrets.token_hex(4)
    salt = secrets.token_hex(32)
    pswd_hash = hashlib.sha256(bytes(''.join((pswd, salt)), 
                                     'UTF-8')).hexdigest()
    
    cur = get_db().cursor()
    cur.execute('update users set pswd_hash=%s, salt=%s where login=%s',
                (pswd_hash, salt, login))

    return json.dumps(pswd)
