from datetime import date, timedelta

class Toolset():
    '''construct toolset for user, with respect to user's group'''
     
    def __init__(self, usergroup: str, fullname: str, eng_login: str):
        login_page = ('Войти', 'login', {})
        logout = ('Выйти', 'logout', {})
        user_crud = ('Управление учетными записями', 'user_crud', {})
        engineer_crud = ('Добавить профиль инженера', 'add_eng', {})


        #from 15th of current month till 15th of next month set current month id

        if date.today().day >= 15:
            current_month = date.today().month
            current_year = date.today().year
        elif date.today().day < 15:
            current_month = date.today().month - 1
            prev_month_date = date.today() - timedelta(days = 30)

            if date.today().year != prev_month_date.year:
                current_year = date.today().year - 1
            else:
                current_year = date.today().year

        monthly_report = ('Ежемесячный отчет по трудозатратам', 
                          'work_report', 
                          {'month': current_month, 'year': current_year, 
                           'eng_login': eng_login})
        
        monthly_report2 = ('Отчеты по трудозатратам (ист. данные)', 
                           'work_report', {})

        cons_work_report = ('Консолидированный отчет по трудозатратам', 
                                'cons_work_report', {'month': current_month, 'year': current_year})

        fullname = (fullname, 'book', {'eng_login': eng_login,
                                                'start': '0', 'end': '0'})

        tasks_log = ('Лог задач', 'get_activities', {})

        settings = {'engineer': (monthly_report, fullname, logout),
                    'focus-manager': (logout,),
                    'manager': (cons_work_report, tasks_log, logout),
                    'admin': (monthly_report, user_crud, engineer_crud, 
                              fullname, logout),
                    'super-admin': (monthly_report, cons_work_report, 
                                    tasks_log, user_crud, engineer_crud, 
                                    fullname, logout)}  

        self.actions = settings[usergroup]
