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
crashmail.py [-p processname] [-a] [-o string] [-m mail_address]
             [-s sendmail] URL

Options:

-p -- specify a supervisor process_name.  Send mail when this process
      transitions to the EXITED state unexpectedly. If this process is
      part of a group, it can be specified using the
      'group_name:process_name' syntax.

-a -- Send mail when any child of the supervisord transitions
      unexpectedly to the EXITED state unexpectedly.  Overrides any -p
      parameters passed in the same crashmail process invocation.

-o -- Specify a parameter used as a prefix in the mail subject header.

-s -- the sendmail command to use to send email
      (e.g. "/usr/sbin/sendmail -t -i").  Must be a command which accepts
      header and message data on stdin and sends mail.  Default is
      "/usr/sbin/sendmail -t -i".

-m -- specify an email address.  The script will send mail to this
      address when crashmail detects a process crash.  If no email
      address is specified, email will not be sent.

The -p option may be specified more than once, allowing for
specification of multiple processes.  Specifying -a overrides any
selection of -p.

A sample invocation:

crashmail.py -p program1 -p group1:program2 -m dev@example.com

"""

import getopt
import os
import sys

from supervisor import childutils


def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)


class CrashMail:

    def __init__(self, programs, sendmail, mailsvr):

        self.programs = programs
        # self.any = any
        # self.email = email
        self.sendmail = sendmail
        # self.optionalheader = optionalheader
        self.mailsvr = mailsvr
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

            msg = ('Process %(processname)s in group %(groupname)s exited '
                   'unexpectedly (pid %(pid)s) from state %(from_state)s' %
                   pheaders)

            # subject = ' %s crashed at %s' % (pheaders['processname'],
            #                                  childutils.get_asctime())
            # if self.optionalheader:
            #     subject = self.optionalheader + ':' + subject

            self.stderr.write('unexpected exit, mailing\n')
            self.stderr.flush()

            self.mail(self.email, msg)

            childutils.listener.ok(self.stdout)
            if test:
                break

    def mail(self, msg):
        body = msg

        # pass string to command
        with os.popen(self.sendmail, 'w') as m:
            m.write(body)
        self.stderr.write('Mailed:\n\n%s' % body)
        self.mailed = body


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
    mailsvr = None


    for option, value in opts:
        if option in ('-h', '--help'):
            usage(exitstatus=0)

        if option in ('-S', '--smtp'):
            programs.append(r'-S ' + value)

        if option in ('-f', '--from'):
            programs.append('-r ' + value)

        if option in ('-s', '--subject'):
            programs.append('-s ' + value)

         # target mail address
        if option in ('-m', '--email'):
            programs.append(value)


    sendmail = sendmail + ''.join(programs)
    print sendmail

    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('crashmail must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    prog = CrashMail(programs, sendmail, mailsvr)
    prog.runforever()


if __name__ == '__main__':
    main()
