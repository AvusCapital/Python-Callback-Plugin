# (C) 2012, Michael DeHaan, <michael.dehaan@gmail.com>

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import json
import tarfile
from yaml import safe_load
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders
from multiprocessing import  Pipe
# NOTE: in Ansible 1.2 or later general logging is available without
# this plugin, just set ANSIBLE_LOG_PATH as an environment variable
# or log_path in the DEFAULTS section of your ansible configuration
# file.  This callback is an example of per hosts logging for those
# that want it.

TIME_FORMAT="Date: %b %d %Y %H:%M:%S"
CURRENT_TIME =  time.strftime('%Y-%m-%d-%H%M', time.localtime())
delimiter=''.join(['*' for s in xrange(80)])
MSG_FORMAT="\nStatus: %(category)s \nHOST: %(host)s\nDebug: %(data)s\n"+delimiter+"\n"
LOG_PATH = os.path.join("logs", "debug.log")
DEFAULT_LOG='logs/ansible.log'
send_message, recieve_message = Pipe()


if not os.path.exists("logs"):
    os.makedirs("logs")


def log(host, category, data):
    if type(data) == dict:
        if 'verbose_override' in data:
            # avoid logging extraneous data from facts
            data = 'omitted'
        else:
            data = data.copy()
            invocation = data.pop('invocation', None)
            data = json.dumps(data)
            if invocation is not None:
                data = json.dumps(invocation) + " => %s " % data
    path = os.path.join("logs", "debug.log")
    fd = open(path, "a")
    fd.write(MSG_FORMAT % dict(category=category, host=host, data=data))
    fd.close()


def rename_log(log_name=None):
    logfile = "logs/{0}.log".format(log_name)
    os.rename("logs/debug.log",logfile)
    tar = tarfile.open("logs/{0}-{1}.tar.gz".format(log_name, CURRENT_TIME), "w:gz")
    tar.add(logfile)
    tar.add(DEFAULT_LOG)
    tar.close()
    os.remove(logfile)
    os.remove(DEFAULT_LOG)


def log_task_name(name=None):
    now = time.strftime(TIME_FORMAT, time.localtime())
    path = LOG_PATH
    fd = open(path, "a")
    fd.write('%(now)s\nTASK: %(name)s' % dict(now=now, name=name))
    fd.close()


def log_statistics(statistics):
    with open(LOG_PATH, "a") as fd:
        fd.write("\nStatistics:\n{0}".format(statistics))


def mail(subject='Ansible error mail', smtp_server=None, sender=None, to=None, cc=None, bcc=None, body=None, log_name=None):
    if not body:
        body = subject
    print "SMTP: %s\nTO: %s\nFROM: %s\n" % (smtp_server, to, sender)
    smtp = smtplib.SMTP(smtp_server)
    msg = MIMEMultipart()
    # The main body is just another attachment
    body += '<p>Please check the attached log for more detailes!</p><p>Kind regards,<br></p>'
    body += '<p><img width="300" src="http://ecx.images-amazon.com/images/I/41WxqVwqawL._SX342_.jpg" alt="Rambo Logo" /><p>'
    msg.attach(MIMEText(body,'html'))
    filename = "logs/{0}-{1}.tar.gz".format(log_name, CURRENT_TIME)
    attachment = open(filename,'rb')
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    attachment.close()
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
    msg.attach(part)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    msg['cc'] = cc
    addresses = to.split(',')
    if cc:
        addresses += cc.split(',')
    if bcc:
        addresses += bcc.split(',')

    smtp.sendmail(sender, addresses, msg.as_string())

    smtp.quit()

class CallbackModule(object):
    """
    logs playbook results, per host, in /var/log/ansible/hosts
    """
    def __init__(self):
        self.stats = {}
        self.current = None
        self.start = time.time()
        self.filename = None
        self.task_name = None
        with open('group_vars/all', 'r') as stream:
            self.group_vars = safe_load(stream)
        self.smtp_server = None
        self.generated_statistics = False
        self.email_errors = []
        # These will be populated in playbook_on_play_start
        self.env = None
        self.brand = None
        self.sub_brand = None

    def playbook_on_play_start(self, pattern):
        self.playbook  = self.play.playbook
        self.brand     = self.playbook.extra_vars.get('brand', "Undefined")
        self.env       = self.playbook.extra_vars.get('env', 'Undefined')
        self.sub_brand = self.playbook.extra_vars.get('subBrand', "Undefined")
        self.filename = "{0}_{1}_{2}".format(self.env,
                                             self.brand,
                                             self.sub_brand)
        env = self.playbook.extra_vars['env']
        if env in self.group_vars['smtp_servers']:
            self.smtp_server = self.group_vars['smtp_servers'][env]
        else:
            self.smtp_server = self.group_vars['smtp_servers']['default']

    def on_any(self, *args, **kwargs):
        pass

    def runner_on_failed(self, host, res, ignore_errors=False):
        if ignore_errors:
            return
        log(host, 'FAILED', res)
        subject = 'Failed: %s ' % self.task_name
        body = '<p>An error occurred for host <b>' + host + ':</b></p> '
        body += '<p><font color="red"><p><b>Failed task name: [ </b>' + self.task_name + ' ]</p></font>'

        if 'stdout' in res.keys() and res['stdout']:
            subject += res['stdout'].strip('\r\n').split('\n')[-1]
            body += '<font color="red"><br><i>' + res['stdout'] + '</font></i></p>'
        if 'stderr' in res.keys() and res['stderr']:
            subject += res['stderr'].strip('\r\n').split('\n')[-1]
            body += '<font color="red"><br><i>' + res['stderr'] + '</font></i></p>'
        if 'msg' in res.keys() and res['msg']:
            subject += res['msg'].strip('\r\n').split('\n')[0]
            body += '<font color="red"><br><i>' + res['msg'] + '</font></i></p>'
        body += 'A complete dump of the error:' + str(res)

        send_message.send({'body': body, 'subject': subject})

    def runner_on_ok(self, host, res):
        log(host, 'OK', res)

    def runner_on_skipped(self, host, item=None):
        log(host, 'SKIPPED', '...')

    def runner_on_unreachable(self, host, res):
        log(host, 'UNREACHABLE', res)
        if isinstance(res, basestring):
            subject = 'Unreachable: %s' % res.strip('\r\n').split('\n')[-1]
            body = '<p>An error occurred for host <b>' + host + '</b> \n<font color="red"><br><i>' + res +'</font>'
        else:
            subject = 'Unreachable: %s' % res['msg'].strip('\r\n').split('\n')[0]
            body = '<p>An error occurred for host <b>' + host + '</b>:<font color="red"><br><i>' + \
                   res['msg'] +'</font>' + '</p>A complete dump of the error:' + str(res)

        send_message.send({'body': body, 'subject': subject})

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        log(host, 'ASYNC_FAILED', res)

    def playbook_on_start(self):
        pass

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        log(host, 'IMPORTED', imported_file)

    def playbook_on_not_import_for_host(self, host, missing_file):
        log(host, 'NOTIMPORTED', missing_file)

    def playbook_on_task_start(self, name, is_conditional):
        """
        Logs the start of each task
        """
        self.task_name = name
        log_task_name(name)
        if self.current is not None:
            # Record the running time of the last executed task
            self.stats[self.current] = time.time() - self.stats[self.current]

        # Record the start time of the current task
        self.current = name
        self.stats[self.current] = time.time()

    def playbook_on_stats(self, stats):
        """
        Prints the timings.
        """
        self.generate_statistics()
        while recieve_message.poll():
            error_message = recieve_message.recv()
            cc_address = None
            if self.env in ['production', 'staging']:
                cc_address = self.group_vars['error_email_cc_address']
            mail(subject=error_message['subject'], smtp_server=self.smtp_server, body=error_message['body'],
                 sender=self.group_vars['email_from_address'], to=self.group_vars['error_email_to_address'],
                 cc=cc_address, log_name=self.filename)

    def generate_statistics(self):
        if self.generated_statistics:
            return
        statistics = ''
        log_task_name('FINISHED')

        # Record the timing of the very last task
        if self.current is not None:
            self.stats[self.current] = time.time() - self.stats[self.current]

        # Sort the tasks by their running time
        results = sorted(
            self.stats.items(),
            key=lambda value: value[1],
            reverse=True,
        )

        # Just keep the top 100
        results = results[:100]

        # Print the timings
        for name, elapsed in results:
            statistics +=(
                "{0:-<70}{1:->9}".format(
                    '{0} '.format(name),
                    ' {0:.02f}s\n'.format(elapsed),
                )
            )

        # Get Total time
        total_elapsed = time.time() - self.start

        # Print the total time in seconds
        statistics +=(
            "{0:-<70}{1:->9}".format(
                '{0} '.format("Total"),
                ' {0:.02f}s\n'.format(total_elapsed),
            )
        )

        # new line
        statistics +="\n"

        # Print the total time - fromat HH:MM:SS
        statistics +=(
            "{0:-<70}{1:->9}".format(
                '{0} '.format(" >> TOTAL TIME: <<< "),
                ' {0}\n'.format(time.strftime('%H:%M:%S', time.gmtime(total_elapsed))),
            )
        )
        log_statistics(statistics)
        self.generated_statistics = True
        rename_log(log_name=self.filename)

