def getFiles(dir, extension):
    """Returns a list of file names in a given directory with a given file extension.

    Keyword arguments:
    dir -- directory to search
    extension -- file extension to look for

    """
    files = []
    for file in os.listdir(dir):
        if file.endswith(extension):
            files.append(os.path.join(dir, file))
    return files

def parseWD(dir):
    """Parse all .wd files in a given directory and return structured data.
    
    The content of the .wd files is written using the yaml markup language.
    Those file are to be written in a way that represents the structured data
    that is to be returned by the function.

    The data should take the form of a list of dictionaries, with the
    dictionaries taking the below form:
       
       {id: 'unique_id',
        type: 'webpage',
        url: 'http://www.etax.dor.ga.gov/inctax/efile/softwaredevelopers.aspx',
        mail: [address1@email.com, address2@email.com, ...],
        rule: ['regex1', 'regex2', ...]}

    For a complete list of the valid dictionary entries, refer to the
    template.wd file.

    """
    glob = [] 
    for file in getFiles(os.path.abspath(dir), '.wd'):
        try:
            fileDump = yaml.load(open(file, 'r'))
        except:
            log = open(LOGFILE, 'a')
            logString = date.today().strftime("%Y.%m.%d - Yaml error with file: ") + file + '\n'
            log.write(logString)
            log.close()
        else:
            for item in fileDump:
                glob.append(item)
        
    return glob

def prepHTML(htmlstring):
    """Removes all new line characters from a string."""
    stripedHTML = ''
    for line in htmlstring:
        stripedHTML += line.rstrip("\n")
    return stripedHTML

def filterHTML(htmlstring, relist):
    """Remove portion of html specified by each regular expression in a list."""
    for regex in relist:
        htmlstring = re.sub(regex, r'', htmlstring)
    return htmlstring

def formatHTML(htmlstring):
    """Puts each HTML tag on its own line."""
    return re.sub(r'(<)', r'\n\1', htmlstring)
  
def diffHTML(htmlstring1, htmlstring2):
    """Find the differences between to HTML strings, return a differ report."""
    diffreport = ''
    diff = difflib.Differ()
    result = list(diff.compare(htmlstring1.splitlines(1), htmlstring2.splitlines(1)))
    for line in result:
        if line[0] != ' ' and line[0] != '?':
            diffreport += line
    return diffreport

def wget(wPath, wURL, wArgs=[]):
    """ Uses wget command to download a webpage.  Returns file in string format"""

    wCmnd =[wPath]
    #Add options to the path
    wCmnd.extend(wArgs)
    wCmnd.append('--quiet')
    wCmnd.append('--output-document=-')
    wCmnd.append('--user-agent="IE 5.5"')
    #wCmnd.append('--no-check-certificate')
    wCmnd.append(wURL)
    return subprocess.Popen(wCmnd, stdout=subprocess.PIPE).communicate()[0]

def webpage(website, maillist):
    """Test if a web page has changed, if it has add the diff report to the appropriate e-mail list. 

        Keyword Arguments
        -- website: contains all info related to the web diffing / email notification process
           form     id:   unique name to identify the web page     
                    url:  url of the web page
                    auth: method of authentication if any (basic)
                    user: user name for authentication
                    pass: password for authentication

        -- maillist: contains all the info to notifing users of changes via email
           form    - emailadd1: id: id: 'website id1'
                                    url: 'url'
                                    diff: 'diffreport'
                   - emialadd2: id: id: 'website id2'
                                    url: 'url2'
                                    diff: 'diffreport2'

    """
    htmlfilename = LOGDIR + website['id'] + '.html'
    difffilename = LOGDIR + website['id'] + '.diff'
    logfilename = LOGDIR + website['id'] + '.' + \
                  time.strftime("%m.%d", time.localtime()) + \
                  '.html'

    #Collect options specified by user for wget
    wgetopts = []
    if website.has_key('wget'):
        wgetopts.extend(website['wget'])
    #Add basic authentication options to wget option list
    if website.has_key('user'):
        wgetopts.append('--user=' + str(website['user']))
    if website.has_key('pass'):
        wgetopts.append('--password=' + str(website['pass']))
    #Download web page, use authentication credentials if available
    newhtml = wget(WGETPATH, website['url'], wgetopts)

    #Make sure a webpage was downloaded
    if newhtml != '':
        #Remove the unwanted and dynamic portions of HTML file. 
        newhtml = prepHTML(newhtml)
        if website.has_key('rule'):
            newhtml = filterHTML(newhtml, website['rule'])
        newhtml = formatHTML(newhtml)  #Format for differ
        
        #Load baseline HTML file and diff with new HTML file
        if os.path.isfile(htmlfilename):
            oldhtml = open(htmlfilename, 'r').read()
            diffreport = diffHTML(oldhtml, newhtml)
            if diffreport:
                logfile = open(logfilename, 'w')
                logfile.write(newhtml)
                logfile.close()
                #Add diff report to any email list for the given webpage
                for email in website['mail']:
                    if email in maillist:
                        maillist[email][website['id']] = {'id': website['id'], \
                                                          'url': website['url'], \
                                                          'diff': diffreport}
                    else:
                        maillist[email] = {website['id']: {'id': website['id'], \
                                                           'url': website['url'], \
                                                           'diff': diffreport}}
                difffile = open(difffilename, 'w')
                difffile.write(diffreport)
                difffile.close()

        #Make the latest HTML file the baseline        
        htmlfile = open(htmlfilename, 'w')
        htmlfile.write(newhtml)
        htmlfile.close()
    else:
        log = open(LOGFILE, 'a')
        logString = date.today().strftime("%Y.%m.%d - webpage not downloaded ") + website['id'] + '\n'
        log.write(logString)
        log.close()

def makemessage(info):
    """Returns the message body to be sent with an e-mail notification"""
    message = "The following webpages have changed\n"
    for page in info:
        message += info[page]['id'] + '   ' + info[page]['url'] + '\n' 
    return message

def adminreport(adminEmail, mailDump):
    """ Sends a summary report to the admin"""
    attachments = []
    reportMessage = ""
    reportTitle = "Webdiffer Summary Report"
    for email in mailDump:
        reportMessage += makemessage(mailDump[email]).replace(
            "The following webpages have changed", email) + '\n'
        for page in mailDump[email]:
            attachments.append(LOGDIR + page + '.diff')
    try:
        sendemail.sendmessage(SENDER, adminEmail, reportTitle, reportMessage, 
                              SERVER, ACCOUNTTYPE, PASSWORD, attachments)
    except:
        log = open(LOGFILE, 'a')
        logString = date.today().strftime("%Y.%m.%d - failed to send summary report to admin")
        log.write(logString)
        log.close()
        dumpFileName = LOGDIR + date.today().strftime("%Y.%m.%d-SummaryReport")
        dumpFile = open(dumpFileName, 'w')            
        dumpFile.write(yaml.dump(mailque[email])) 
        dumpFile.close()

import sys
import os
import re
import time
import getopt 
import string 
import difflib 
import subprocess
from datetime import date

import yaml
import sendemail

#setup globals
data = []
mailque = {}
testmode = None
reportmode = 1

if sys.platform == 'win32':
    WGETPATH = '.\\wget.exe'
else:
    WGETPATH = 'wget' 

CONFILE = os.path.expanduser('~/.wdrc')
HOMEDIR = '.'
DATADIR = 'data'
LOGDIR =  'log'
LOGFILE = './webdiffer.log'
TITLE = 'Changes Found!'
SENDER = 'address@gmail.com'
PASSWORD = 'password'
SERVER = 'smtp.gmail.com'
ACCOUNTTYPE = 'tls'
ADMINADDRESS = ['adim@gmail.com']

#Overwrite globals with values from webdiffer.cfg
if not os.path.isfile(CONFILE):
    CONFILE = './webdiffer.cfg'

if os.path.isfile(CONFILE):
    settings = yaml.load(open(CONFILE, 'r'))
    if settings.has_key('HOMEDIR'):
        HOMEDIR = os.path.expanduser(settings['HOMEDIR'])
    if settings.has_key('DATADIR'):
        DATADIR = os.path.expanduser(settings['DATADIR'])
    if settings.has_key('LOGDIR'):
        LOGDIR = os.path.expanduser(settings['LOGDIR'])
    if settings.has_key('TITLE'):
        TITLE = settings['TITLE']
    if settings.has_key('SENDER'):
        SENDER = settings['SENDER']
    if settings.has_key('PASSWORD'):
        PASSWORD = settings['PASSWORD']
    if settings.has_key('SERVER'):
        SERVER = settings['SERVER']
    if settings.has_key('ACCOUNTTYPE'):
        ACCOUNTTYPE = settings['ACCOUNTTYPE']
    if settings.has_key('WGETPATH'):
        WGETPATH = settings['WGETPATH']
    if settings.has_key('LOGFILE'):
        LOGFILE = os.path.expanduser(settings['LOGFILE'])
    if settings.has_key('ADMINADDRESS'):
        ADMINADDRESS = settings['ADMINADDRESS']


#Parse command line arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "htr", ["help", "test", "report"])
except getopt.GetpptError:
    pass
else:
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print "Please refer to the documentation of usage."
            system.exit
        elif opt in ("-t", "--test"):
            testmode = 1
        elif opt in ("-r", "--report"):
            reportmode = 1
        
#Parse data files
data = parseWD(DATADIR) 

#Process each item
for item in data:
    if item['type'].lower() == 'webpage':
        webpage(item, mailque)
    elif item['type'].lower() == 'pdf':
        pass
    else: 
        pass

#Send out emails
for email in mailque:
    message = makemessage(mailque[email])
    attachments = []
    for page in mailque[email]:
        attachments.append(LOGDIR + page + '.diff')
 
    if testmode == 1:
        print email
        print message + "\n"
    else:
        try:
            sendemail.sendmessage(SENDER, email, TITLE, message, SERVER, ACCOUNTTYPE, PASSWORD, attachments)
        except:
            log = open(LOGFILE, 'a')
            logString = date.today().strftime("%Y.%m.%d - failed to send email to: ") + email.replace("@", "AT").replace(".", "DOT") + '\n'
            log.write(logString)
            log.close()
            dumpFileName = LOGDIR + date.today().strftime("%Y.%m.%d-") + email.replace("@", "AT").replace(".", "DOT")
            dumpFile = open(dumpFileName, 'w')            
            dumpFile.write(yaml.dump(mailque[email])) 
            dumpFile.close()

if reportmode == 1:
    for email in ADMINADDRESS:
        adminreport(email, mailque)
 
if testmode == 1:
    raw_input("Press any key to exit")
