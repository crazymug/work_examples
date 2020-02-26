from datetime import datetime
import calendar
import logging
import configparser
from os import environ, urandom

from functools import wraps

from flask import Flask, render_template, g, request, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user, current_user

from .modules.backend import backend
from .modules.resource import resource
from .modules.dateutils import dateutils
from .modules.user import User
from .modules.search import *
from .modules.booking import *
from .modules.report import *
from .modules.exceptions import MessagingError


'''Initialization'''
app = Flask(__name__, template_folder='templates_ru')

app.add_template_filter(dateutils.iso2unix, name='iso2unix')
app.add_template_filter(dateutils.unix2iso_ru, name='unix2iso_ru')

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
    app.config['backend_ip'] = '127.0.0.1'
    app.config['backend_port'] = '8000'

read_app_config(environ['SUIR_CFG'])

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

@app.route('/search_result', methods=['POST'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'focus-manager', 
                                   'engineer', 'manager'])
def search_result():
    search_string = form_search_string(request)
    logins = backend.search_logins(app.config['backend_ip'], 
                              app.config['backend_port'], search_string)
    resources = resource.get_resources_sorted_by_workload(logins)
    return render_template('search_result.html', resources = resources, 
                           username = current_user.fullname, 
                           toolset = current_user.toolset_actions)

@app.route('/book_engineer/<string:eng_login>/<string:start>/<string:end>', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'focus-manager', 
                                   'engineer', 'manager'])
def book(eng_login, start, end):
    if request.method == 'GET':
        act_hist = set_timeline_hist_or_act(start, end)

        app.logger.info(' '.join(('GET on /book_engineer:', 
                                  request.headers.get('User-agent'),
                                  current_user.fullname)))

        engineer = resource(eng_login)
        if start == '0' and end == '0':
            bookinfo = engineer.cur_week_booking
        else:
            bookinfo = backend.get_engineer_booking(eng_login, start, end)
       
        bookinfo_ = list(map(dateutils.replace_timestamps, bookinfo))

        return render_template('book_engineer.html', eng_login = eng_login, 
                               bkinfo = bookinfo_, fullname = engineer.full_name, 
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
        booking = get_booking_info_from_request(request)
        booking_entries = dateutils.convert_booking_to_entries(**booking)

        add_booking_entries(booking_entries)

        try:
            if current_user.login != booking['resource_login']:
                send_task_added_messages(booking['project_id'], 
                                         current_user.fullname, 
                                         booking['resource_login'], 
                                         app.config)
        except MessagingError as msg_error:
            app.logger.error(' '.join(('Error sending SMS', msg_error.error_data, current_user.fullname)))
            flash('Не удалось отправить SMS инженеру. Обратитесь к администратору', 'error')

        return redirect(url_for('book', eng_login = eng_login , start = 0, end = 0))

@app.route('/add_engineer', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def add_eng():
    if request.method == 'GET':
        return render_template('engineer_crud.html', action = "add_engineer",
                               username = current_user.fullname, 
                               toolset = current_user.toolset_actions)
    if request.method == 'POST':
        engineer = resource.get_engineer_info_from_request(request)
        backend.add_engineer(**engineer)
        flash('Инженер добавлен в систему', 'info')
        return render_template('engineer_crud.html', action = "add_engineer", 
                               username = current_user.fullname, 
                               toolset = current_user.toolset_actions)

@app.route('/edit_engineer/<string:eng_login>', methods=['POST', 'GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def edit_eng(eng_login):
    if request.method == 'GET':
        eng_info = backend.get_eng_info(eng_login)
        return render_template('engineer_crud.html', action = "edit_engineer",
                               eng_inf = eng_info[0], 
                               username = current_user.fullname, 
                               toolset = current_user.toolset_actions)

    if request.method == 'POST':
        engineer = resource.get_engineer_info_from_request(request)
        backend.update_engineer(**engineer)
        flash('Данные об инженере отредактированы', 'info')
        return redirect(url_for('edit_eng', eng_login = eng_login))

@app.route('/delete_engineer/<string:eng_login>', methods=['GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def delete_eng(eng_login):
    backend.delete_engineer(eng_login)
    flash('Инженер с ID {0} удален'.format(eng_login), 'info')
    return redirect(url_for('search'))


@app.route('/work_report/<int:month>/<int:year>/<string:eng_login>', methods=['GET', 'POST'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'engineer', 'manager'])
def work_report(month, year, eng_login):
    eng_info = backend.get_eng_info(eng_login)
    if len(eng_info) != 0:
        fullname = eng_info[0][1]
    else:
        return render_template('work_report.html', tasks = [], 
                               report = [], 
                               premade = [], 
                               hourslimit = 0, 
                               username = '', eng_login = eng_login, 
                               toolset=current_user.toolset_actions,
                               month=month, year=year)

    if request.method == 'GET':
        saved_report = backend.get_workreport(eng_login, month, year)
        if saved_report:
            flash('Загружен ранее сохраненный отчет', 'info')

        start = datetime(year, month, 1, 
                         hour = 00, minute = 00).strftime('%Y-%m-%dT%H:%M')
        end = datetime(year, month, calendar.monthrange(year, month)[1], 
                       hour = 23, minute = 59).strftime('%Y-%m-%dT%H:%M')

        tasks = get_engineer_tasks_sorted_by_id(eng_login, start, end)
        tasks_with_workhours = calc_work_hours(tasks)
        new_tasks_report = generate_report_from_tasks(tasks_with_workhours)

        report = concat_reports(saved_report, new_tasks_report)
        new_tasks_added = check_if_new_tasks_added(report)
        if new_tasks_added:
            flash('Отчет необходимо обновить и сохранить, т.к. были добавлены новые задачи. \n \
                    Если ранее были введены трудозатраты равные нулю - \
                    проигнорируйте данное сообщение', 'error')

        hourslimits = get_hourslimits(app.config['hourslimit'])  
        premade_report_entries = get_premade_workreport_entries(app.config['premade'], saved_report)

        return render_template('work_report.html', tasks = tasks, 
                               report = sorted(report, reverse = True), 
                               premade = premade_report_entries, 
                               hourslimit = hourslimits[month], 
                               username = fullname, eng_login = eng_login, 
                               toolset=current_user.toolset_actions,
                               month=month, year=year)

    if request.method == 'POST':
        backend.save_workreport(request, eng_login, month, year)
        flash('Отчет за прошедший месяц сохранен', 'info')
        return redirect(url_for('work_report', 
                                month = month, year = year, 
                                eng_login = eng_login))

@app.route('/cons_work_report/<int:month>/<int:year>', methods=['GET'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin', 'manager'])
def cons_work_report(month, year):
    all_workreports = backend.get_all_workreports(month, year)

    report_with_full_names = get_report_with_full_names(all_workreports)
    
    #group raws by company/item column and columns by resource_logins/real names
    #make utils dict, dict key is engineer + ' ' + company + ' ' + sla string 
    utils_dict = get_utils_dict(report_with_full_names)

    engineers = set([(row[0]['name'], row[0]['login']) for row in report_with_full_names])

    companies_sla = get_companies_sla(report_with_full_names)

    excel_file_path = generate_excel_report_file(month, year, 
                                                 companies_sla, list(engineers), utils_dict, app.root_path)

    not_reported_engineers = get_engineers_not_reported_workload(engineers)
    return render_template('cons_work_report.html', 
                           no_rep_list = not_reported_engineers, 
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
    eng_list = backend.get_engineers_list()
    eng_list_login_name = [{'login': eng[12], 'fullname':eng[1]} for eng in eng_list]

    start_date, end_date = dateutils.get_last_week_time_interval()

    activities_short_description = get_booking_entries_short_description(eng_list_login_name, 
                                                                    start_date, end_date)

    return render_template('activities.html', activities = activities_short_description, 
                           username = current_user.fullname, 
                           toolset = current_user.toolset_actions)

@app.route('/user_crud', methods = ['GET', 'POST'])
@login_required
@user_group_required(user_group = ['super-admin', 'admin'])
def user_crud():
    if request.method == 'GET':
        users = backend.get_users()
        return render_template('user_crud.html', username = current_user.fullname, 
                               toolset = current_user.toolset_actions,
                               users = users)
    elif request.method == 'POST':
        success = backend.add_user(request)
        if success != 'PROBLEM':
            flash(''.join(('Пользователь добавлен в систему, пароль: ', success)), 'info')
        else:
            flash('Ошибка добавления пользователя, обратитесь к разработчику',
                  'error')
        return redirect(url_for("user_crud"))
