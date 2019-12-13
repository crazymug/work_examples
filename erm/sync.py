from modules.ersmm import ersmm
from modules.integration import Remedy, Jira, Sharepoint
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

    sysTypes = {'Remedy': Remedy, 'JIRA': Jira, 'Sharepoint': Sharepoint}

    for system in config.sections():
        if system != 'General':
            url = config[system]['URL']
            user = config[system]['User']
            pswd = config[system]['Password']
            r = sysTypes[config[system]['Type']](url, user, pswd)

            print('Synchronizing with {0}...'.format(system))
            client, header = r.connect()
            entriesList = []
            for eng in ersmm.get_engineers_list():
                if system == 'Remedy' and eng[8] != None: 
                    entry = r.getEntry(client, header, eng)
                    if entry != None: entriesList = entriesList + entry
                if system == 'Jira' and eng[9] != '' and eng[9] != None: 
                    entries = r.getEntries(eng)
                    if entries != None: entriesList = entriesList + entries
                if system == 'Sharepoint' and eng[10] != '' and eng[10] != None: 
                    entries = r.getEntries(eng)
                    if entries != None: entriesList = entriesList + entries
            prepEntries = r.preprocessEntries(entriesList)
            print(prepEntries)
            r.updateBooking(prepEntries)
