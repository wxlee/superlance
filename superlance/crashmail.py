#!/usr/bin/env python -u
##############################################################################
#
# Copyright (c) 2007 Agendaless Consulting and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the BSD-like license at
# http://www.repoze.org/LICENSE.txt.  A copy of the license should accompany
# this distribution.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL
# EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND
# FITNESS FOR A PARTICULAR PURPOSE
#
##############################################################################

# A event listener meant to be subscribed to PROCESS_STATE_CHANGE
# events.  It will send mail when processes that are children of
# supervisord transition unexpectedly to the EXITED state.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:crashmail]
# command =
#     /usr/bin/crashmail
#         -o hostname -a -m notify-on-crash@domain.com
#         -s '/usr/sbin/sendmail -t -i -f crash-notifier@domain.com'
# events=PROCESS_STATE
#
# Sendmail is used explicitly here so that we can specify the 'from' address.

doc = """\
crashmail.py [-f sent_from] [-m sent_to] [-h help] 
             [-S set_smtp_server] [-s subject]

Options:
-f -- set the mail from address 
-S -- set smtp server
-s -- set mail subject
-m -- set target mail address

A sample invocation:
crashmail -f "crash@xxx.com" -s "NodeCrash" -S smtp=x.x.x.x:25 -m target@xxx.com

"""

import getopt
import os
import sys

from supervisor import childutils


def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)


class CrashMail:

    def __init__(self, sendmail):

        # self.programs = programs
        self.sendmail = sendmail
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def runforever(self, test=False):
        while 1:
            # we explicitly use self.stdin, self.stdout, and self.stderr
            # instead of sys.* so we can unit test this code
            headers, payload = childutils.listener.wait(
                self.stdin, self.stdout)

            if not headers['eventname'] == 'PROCESS_STATE_EXITED':
                # do nothing with non-TICK events
                childutils.listener.ok(self.stdout)
                if test:
                    self.stderr.write('non-exited event\n')
                    self.stderr.flush()
                    break
                continue

            pheaders, pdata = childutils.eventdata(payload+'\n')

            if int(pheaders['expected']):
                childutils.listener.ok(self.stdout)
                if test:
                    self.stderr.write('expected exit\n')
                    self.stderr.flush()
                    break
                continue

            msg = ('Process %(processname)s exited '
                   'unexpectedly (pid %(pid)s) from state %(from_state)s' %
                   pheaders)

            self.stderr.write('unexpected exit, mailing\n')
            self.stderr.flush()
            self.mail(msg)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def mail(self, msg):
        body = msg

        # pass string to command
        with os.popen(self.sendmail, 'w') as m:
            m.write(body)
        self.stderr.write('Mailed:\n\n%s' % body)


def main(argv=sys.argv):
    short_args = "S:hf:s:m:"
    long_args = [
        "smtp=",
        "help",
        "from=",
        "subject=",
        "mail="
    ]

    arguments = argv[1:]
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        usage()

    programs = []
    sendmail = '/usr/bin/mailx '

    for option, value in opts:
        if option in ('-h', '--help'):
            usage(exitstatus=0)

        if option in ('-S', '--smtp'):
            programs.append(' -S ' + value)

        if option in ('-f', '--from'):
            programs.append(' -r ' + value)

        if option in ('-s', '--subject'):
            programs.append(' -s ' + value)

         # target mail address
        if option in ('-m', '--email'):
            programs.append(' ' + value)


    sendmail = sendmail + ''.join(programs)

    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('crashmail must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = CrashMail(sendmail)
    prog.runforever()


if __name__ == '__main__':
    main()
