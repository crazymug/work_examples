import time
from datetime import datetime, timedelta
import calendar
import json
import http.client
import urllib.parse
import logging
import configparser
from os import environ, urandom
from itertools import groupby
from functools import wraps

from flask import Flask, render_template, g, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
import psycopg2
from openpyxl import Workbook 

from .modules.dateutils import dateutils as du
from .modules.resource import resource
from .modules.message import message as msg
from .modules.user import User

'''Initialization'''
app = Flask(__name__, template_folder='templates_ru')

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
        app.logger.error('Error reading application configuration file ' +
conf_file_name)
        exit() #need testing
    app.config['sms_login'] = config['General']['SMS_login']
    app.config['sms_pwd'] = config['General']['SMS_pwd']
    app.config['sms_originator'] = config['General']['SMS_originator']
    app.config['db_name'] = config['General']['DB_name']
    app.config['db_user'] = config['General']['DB_user']
    app.config['db_pass'] = config['General']['DB_pass']
    app.config['db_host'] = config['General']['DB_host']

    app.config['hourslimit'] = config['General']['Hours_limit']
    app.config['premade'] = config['General']['Standard_ent']


read_app_config(environ['SUIR_CFG'])


def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(dbname = app.config['db_name'],
                user = app.config['db_user'], 
                password = app.config['db_pass'], 
                host = app.config['db_host'])
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.commit()
        db.close()

login_manager = LoginManager()
login_manager.init_app(app)
app.secret_key = urandom(16)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def user_group_required(user_group = []):
    '''User group checking decorator'''
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if (current_user.user_group not in user_group) and user_group != []:
                return login_manager.unauthorized()
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


'''Application web-interface's main routes'''
@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    user = User(request.form['login'], request.form['pass'])
    if user.is_authenticated:
        active = login_user(user)
        if active:
            flash('Вы вошли в трекер задач', 'info')
            return redirect(url_for('search'))
        else:
            flash('Пользователь отмечен как не активный.' 
                    'Обратитесь к администратору', 'error')
            return redirect(url_for('login_page'))
    else:
        flash('Неверный логин или пароль', 'error')
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из трекера задач','info')
    return redirect(url_for('login_page'))

@app.route('/search')
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'focus-manager', 
                                   'engineer', 'manager'])
def search():
    return render_template('search.html', startpage = True, 
                           username = current_user.fullname, 
                           toolset = current_user.toolset_actions)

@app.route('/search_result', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'focus-manager', 
                                   'engineer', 'manager'])
def search_result():
    if request.method == 'POST':
        search_string = request.form['search_string']
    elif request.method == 'GET': 
        search_string = request.args.get('search_string')

    if len(search_string) == 0:
        search_string = '%%'
    
    conn = http.client.HTTPConnection('127.0.0.1', 8000)
    conn.request('GET', 
                 '/rest/search/{0}'.format(urllib.parse.quote(search_string)))
    answ = conn.getresponse()
    res = json.loads(answ.read())
    conn.close()

    res_list = {}
    for r in res:
        res_list[r[12]] = resource(r[12]).workload
    
    res = sorted(res, key = lambda res_el: res_list[res_el[12]]) #engineers sorted by workload

    return render_template('search_result.html', result = res, 
                           res_wl = res_list, 
                           username = current_user.fullname, 
                           toolset = current_user.toolset_actions)

@app.route('/book_engineer/<string:eng_login>/<string:start>/<string:end>', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'focus-manager', 
                                   'engineer', 'manager'])
def book(eng_login, start, end):
    act_hist = 'hist'

    if request.method == 'GET':
        app.logger.info(' '.join(('GET on /book_engineer:', 
                                  request.headers.get('User-agent'),
                                  current_user.fullname)))

        #resource_login = request.args.get('res_login')
        if eng_login == None:
            return redirect('/')

        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        #start = request.args.get('diag_start_datetime') or '0'
        #end = request.args.get('diag_end_datetime') or '0'

        if start == '0' and end == '0': act_hist = 'act'
        
        conn.request('GET','/rest/eng_booking_interval/' + eng_login + '/' + start + '/' + end)
        answ = conn.getresponse()
        binfo = json.loads(answ.read())
        

        #replace all unix timestamps with ISO 8601
        bookinfo = list(map(du.replace_tmstps, binfo))

        # get constrains from vacations table 
        # form resulting dict
        cur = get_db().cursor()
        cur.execute('select full_name from resources where suir_id=%s', (eng_login, ))
        fullname = cur.fetchall()[0][0]

        return render_template('book_engineer.html', res_login=eng_login, 
                               bkinfo=bookinfo, flname = fullname, 
                               act_or_hist = act_hist, 
                               username = current_user.fullname,
                               start = start, end = end, 
                               toolset = current_user.toolset_actions,
                               diag_start_datetime = 0,
                               diag_end_datetime = 0)

    if request.method == 'POST':
        app.logger.info(' '.join(('POST on /book_engineer:', 
                                  request.headers.get('User-agent'),
                                  current_user.fullname)))
        booking_type = request.form['type']
        percent = request.form['perchours']
        hours = "" #request.form.get('perchours')
        active = 1
        resource_login = request.form['res_login']
        project_id = request.form['proj_id']
        repeat = request.form['repeat']
        company = request.form['company']
        sla = request.form['sla']

        #convert datetime ISO 8601 to unix timestamp
        start_date = request.form['start_datetime']
        end_date = request.form['end_datetime']

        username = ''.join((' : ', current_user.fullname)) 

        booking_entries = du.convert_booking_to_entries(booking_type, percent, hours, repeat, start_date, end_date, company, sla)
        
        conn = get_db()
        for e in booking_entries:
            try:
                conn.cursor().execute('insert into booking values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (e['booking_type'], e['percent'], e['hours'], 1, 0, project_id + username, e['repeat'], du.iso2unix(e['start_date']), du.iso2unix(e['end_date']), e['company'], e['sla'], 0, resource_login)) 
            except Exception as e:
                flash('Проблема записи в базу данных. Обратитесь к администратору', 'error')

        #send message to resource and his/her org.units head
        msg_send_status = msg.send_sms('Вам назначена задача на http://st-erm: ' + project_id + ' :' + username, resource_login, app.config['sms_login'], app.config['sms_pwd'], app.config['sms_originator'])
        app.logger.info(msg_send_status)
        if msg_send_status[0] == 'ERROR': 
            app.logger.error(' '.join(('Error sending SMS', msg_send_status[1], current_user.fullname)))
            flash('Не удалось отправить SMS инженеру. Обратитесь к администратору', 'error')
        #msg_send_status = msg.send_sms_to_head('Инженеру назначена задача на http://st-erm: ' + project_id, resource_login, conf_dict['sms_login'], conf_dict['sms_pwd'])
        #if msg_send_status == 'ERROR': app.logger.error('Error sending SMS')

        flash('Задача успешно добавлена', 'info')
        return redirect(url_for('book', eng_login = resource_login, start = 0, end = 0))
      
@app.route('/add_engineer', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def add_eng():
    if request.method == 'GET':
        return render_template('engineer_crud.html', action = "add_engineer",
                               username = current_user.fullname, 
                               toolset = current_user.toolset_actions)
    if request.method == 'POST':
        cur = get_db().cursor()
        fullname = request.form['fullname']
        phone = request.form['phone']
        tags = request.form['tags']
        skills = request.form['skills']
        org_unit = request.form['org_unit']
        eng_type = request.form['type']
        email = request.form['email']
        rem_id = request.form['rem_id']
        jira_id = request.form['jira_id']
        suir_id = request.form['suir_id']
        util = request.form['util']

        cur.execute('insert into resources values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                    (fullname, phone, tags, skills, org_unit, eng_type, email, 
                     rem_id, jira_id, '', util, suir_id))

        flash('Инженер добавлен в систему', 'info')
        return render_template('engineer_crud.html', action = "add_engineer", 
                               username = current_user.fullname, 
                               toolset = current_user.toolset_actions)

@app.route('/edit_engineer/<string:eng_login>', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def edit_eng(eng_login):
    if request.method == 'GET':
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng/' + eng_login)
        answ = conn.getresponse()
        eng_info = json.loads(answ.read())
        conn.close()
        return render_template('engineer_crud.html', action = "edit_engineer",
                               eng_inf = eng_info[0], 
                               username = current_user.fullname, 
                               toolset = current_user.toolset_actions)

    if request.method == 'POST':
        cur = get_db().cursor()
        eng_login = request.form['suir_id']
        fullname = request.form['fullname']
        phone = request.form['phone']
        tags = request.form['tags']
        skills = request.form['skills']
        org_unit = request.form['org_unit']
        eng_type = request.form['type']
        email = request.form['email']
        rem_id = request.form['rem_id']
        jira_id = request.form['jira_id']
        sharepoint_id = request.form['sharepoint_id']
        suir_id = request.form['suir_id']
        util = request.form['util']
        langs = request.form['langs']

        cur.execute('update resources set full_name = %s, phone = %s, tags = %s, skills = %s, org_unit_id = %s, type = %s, e_mail = %s, rem_id = %s, jira_id = %s, sharepoint_id = %s, suir_id = %s, utilized = %s, langs = %s where suir_id=%s', (fullname, phone, tags, skills, org_unit, eng_type, email, rem_id, jira_id, sharepoint_id, suir_id, util, langs, eng_login))
        
        flash('Данные об инженере отредактированы', 'info')
        return redirect(url_for('edit_eng', eng_login = eng_login))


@app.route('/delete_engineer/<string:eng_login>', methods=['GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def delete_eng(eng_login):
    conn = http.client.HTTPConnection('127.0.0.1', 8000)
    conn.request('DELETE','/rest/eng/' + eng_login)
    answ = conn.getresponse()
    flash('Инженер с ID {0} удален'.format(eng_login), 'info')
    conn.close()
    return redirect(url_for('search'))


@app.route('/work_report/<int:month>/<int:year>/<string:eng_login>', methods=['GET', 'POST'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'engineer', 'manager'])
def work_report(month, year, eng_login):
    conn = http.client.HTTPConnection('127.0.0.1', 8000)
    conn.request('GET', '/rest/get_fullname/{0}'.format(eng_login))
    answ = conn.getresponse()
    fullname = json.loads(answ.read())

    if request.method == 'GET':
        #check if user exists in DB
        #show different month-year reports as buttons in table - in one row
        #try to get report data
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/workrep/' + eng_login + '/' + str(month) + '/' + str(year))
        answ = conn.getresponse()
        report_from_db = json.loads(answ.read())
        if report_from_db: flash('Загружен ранее сохраненный отчет', 'info')
        #get users tasks from prev month, put them into Table 1
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        start = datetime(year, month, 1).strftime("%Y-%m-%d")
        end = datetime(year, month, calendar.monthrange(year, month)[1], hour = 23, minute = 59).strftime('%Y-%m-%dT%H:%M')

        conn.request('GET','/rest/eng_booking_interval/' + eng_login + '/' + start + '/' + end)
        answ = conn.getresponse()
        tasks = json.loads(answ.read())
        tasks = sorted(tasks, key = lambda item:int(item[0]))
        
        #calc work hours for each task
        for task in tasks:
            task.append(str(timedelta(seconds=task[9] - task [8])))
            task.append(timedelta(seconds=task[9] - task [8]))
            #convert dates in tasks list to iso format
            task[8] = du.unix2iso_ru(task[8])
            task[9] = du.unix2iso_ru(task[9])
            
        #calc or recalc work report
        report_from_tasks = []
        tasks_sla_sorted = sorted(tasks, key=lambda item:(item[10], item[11]))
        for sla, grp in groupby(tasks_sla_sorted, key=lambda item:(item[10], item[11])):
            tasks_grp = list(grp)
            hours = int(sum([task[15] for task in tasks_grp], timedelta()).total_seconds()/60/60)
            report_from_tasks.append([tasks_grp[0][10], hours, sla[1]])
        
        #form report, mark edited and newly created items          
        report = []
        new_tasks_exists = False
        report_from_db_without_util = [[item[0], item[2]] for item in report_from_db]
        if report_from_db == []:
            report = report_from_tasks
        elif report_from_db != []:
            
            for item_from_db in report_from_db:
                if item_from_db not in report_from_tasks:
                    report.append(item_from_db + ['edited'])
                elif item_from_db in report_from_tasks:
                    report.append(item_from_db + ['not_edited'])
            
            for item_from_tasks in report_from_tasks:
                item_from_tasks_without_util = [item_from_tasks[0], item_from_tasks[2]]
                if item_from_tasks_without_util not in report_from_db_without_util:
                    report.append(item_from_tasks + ['new'])
                    new_tasks_exists = True

        if new_tasks_exists:
            flash('Отчет необходимо обновить и сохранить, т.к. были добавлены новые задачи. \nЕсли ранее были введены трудозатраты равные нулю - проигнорируйте данное сообщение', 'error')


        hourslimit = [0] + [int(limit) for limit in app.config['hourslimit'].split(',')]
        premade = set([ent.strip() for ent in app.config['premade'].split(',')])
        report_lst = set([item[0] for item in report_from_db])
        pre = premade - report_lst

        return render_template('work_report.html', tasks = tasks, 
                               report = sorted(report, reverse = True), 
                               premade = pre, hourslimit = hourslimit[month], 
                               username = fullname, eng_login = eng_login, 
                               toolset = current_user.toolset_actions,
                               month = month, year = year)

    if request.method == 'POST':
        params = urllib.parse.urlencode(request.form.to_dict())
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('POST','/rest/workrep/' + eng_login + '/' + str(month) + '/' + str(year), body = params, headers = headers)
        answ = conn.getresponse()
        if json.loads(answ.read()) == 'OK':
            flash('Отчет за прошедший месяц сохранен', 'info')
        else:
            flash('Ошибка сохранения отчета: обратитесь к администратору', 'error')
        
        return redirect(url_for('work_report', 
                                month = month, year = year, 
                                eng_login = eng_login))

@app.route('/cons_work_report/<int:month>/<int:year>', methods=['GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'manager'])
def cons_work_report(month, year):
    conn = http.client.HTTPConnection('127.0.0.1', 8000)
    conn.request('GET','/rest/consworkrep/' + str(month) + '/' + str(year))
    answ = conn.getresponse()
    json_answ = answ.read()
    engineers = json.loads(json_answ)[0]
    companies_sla = json.loads(json_answ)[1]
    utils_dict = json.loads(json_answ)[2]
     

    #form list of engineers that does not saved report
    conn = http.client.HTTPConnection('127.0.0.1', 8000)
    conn.request('GET','/rest/eng_list')
    answ = conn.getresponse()
    eng_list = [(eng[1], eng[7], eng[11]) for eng in json.loads(answ.read())]
    no_rep_list = []

    app.logger.info(engineers)
    engineers_names_from_consreport = [x[0] for x in engineers]
    app.logger.info(eng_list)
    for eng in eng_list:
        if eng[0] not in engineers_names_from_consreport and eng[2] == 'yes':
            no_rep_list.append(eng[1])
    
    #generate excel file
    wb = Workbook()
    ws = wb.active
    ws.title = '_'.join(['отчет', str(month), str(year)])
    if len(engineers) > 0:
        for row_num, row in enumerate(ws.iter_rows(min_row = 1, max_row = len(companies_sla) + 1, max_col = len(engineers) + 1)):
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
    wb.save(app.root_path + '/static/' + report_file_name)
    excel_file_path = url_for('static', filename = report_file_name)

    return render_template('cons_work_report.html', no_rep_list = no_rep_list, 
                           excel_file_path = excel_file_path, month = month, 
                           year = year, engineers = engineers, 
                           companies_sla = companies_sla, 
                           utils_dict = utils_dict, 
                           username = current_user.fullname, 
                           toolset = current_user.toolset_actions)

@app.route('/activities', methods = ['GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'manager'])
def get_activities():
    #get engineers list
    conn = http.client.HTTPConnection('127.0.0.1', 8000)
    conn.request('GET','/rest/eng_list')
    answ = conn.getresponse()
    eng_list = [(eng[12], eng[1]) for eng in json.loads(answ.read())]

    #calc time interval
    start_date = du.unix2iso(int(time.time()) - 604800, time_info = False)
    end_date = du.unix2iso(int(time.time()), time_info = False)

    activities = []

    for eng in eng_list:
        #get activities for previous week for particular engineer
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/eng_booking_interval/{0}/{1}/{2}'.format(eng[0], start_date, end_date))
        answ = conn.getresponse()
        eng_activities = [{'id':act[0], 'descr': act[6], 'company': act[10], 'sla': act[11], 'eng': eng[1]} for act in json.loads(answ.read())]
        if eng_activities:
            for act in eng_activities:
                activities.append(act)

    return render_template('activities.html', activities = activities, 
                           username = current_user.fullname, 
                           toolset = current_user.toolset_actions)

@app.route('/user_crud', methods = ['GET', 'POST'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def user_crud():
    if request.method == 'GET':
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        conn.request('GET','/rest/users')
        answ = conn.getresponse()
        users = json.loads(answ.read())
        return render_template('user_crud.html', username = current_user.fullname, 
                               toolset = current_user.toolset_actions,
                               users = users)
    elif request.method == 'POST':
        conn = http.client.HTTPConnection('127.0.0.1', 8000)
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        params = urllib.parse.urlencode(request.form.to_dict())
        conn.request('POST','/rest/users', body = params, headers = headers)
        answ = conn.getresponse()
        success = json.loads(answ.read())
        if success != 'PROBLEM':
            flash(''.join(('Пользователь добавлен в систему, пароль: ', success))
                  , 'info')
        else:
            flash('Ошибка добавления пользователя, обратитесь к разработчику',
                  'error')
        return redirect(url_for("user_crud"))
