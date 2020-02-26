from modules.backend import backend
from modules.integration import Remedy_HPD, Remedy_CHG, Jira, Sharepoint
import configparser
import sys


config = configparser.ConfigParser()
try:
    config.read(sys.argv[1])
except (IndexError, configparser.ParsingError):
    print('''Usage for manual syncing: sync.py <config file name>\n\n
    This utility sync ERSMM tasks info with outer systems. You must add this script to cron tasks.\n
    For ubuntu execute under root or other user with appropriate permissions following command:\n
        echo "30 * * * * * root python /var/ersmm/sync.py sync_example.cfg" >> /etc/crontab\n
        This will make sync run every half an hour.''')
else:

    sysTypes = {'Remedy_HPD': Remedy_HPD, 'Remedy_CHG': Remedy_CHG, 
                'JIRA': Jira, 'Sharepoint': Sharepoint}

    for system in config.sections():
        if system != 'General':
            url = config[system]['URL']
            user = config[system]['User']
            pswd = config[system]['Password']
            external_system = sysTypes[config[system]['Type']](url, user, pswd)

            print('\nSynchronizing with {0}...'.format(system))
            external_system.connect()
            entriesList = []
            for engineer in backend.get_engineers_list():
                entries = []
                if system == 'Remedy_HPD' and engineer[8] != None: 
                    entries = external_system.get_entries(engineer)
                elif system == 'Remedy_CHG' and engineer[8] != None: 
                    entries = external_system.get_entries(engineer)
                elif system == 'Jira' and engineer[9] != '' and engineer[9] != None: 
                    entries = external_system.get_entries(engineer)
                elif system == 'Sharepoint' and engineer[10] != '' and engineer[10] != None: 
                    entries = external_system.get_entries(engineer)

                if entries != []: 
                    entriesList = entriesList + entries

            preprocessed_entries = external_system.preprocess_entries(entriesList)
            print(preprocessed_entries)
            external_system.send_booking_to_backend(preprocessed_entries)
