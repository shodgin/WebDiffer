#!/usr/bin/env python

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
import os

def sendmessage(fro, to, subject, text, server="localhost", mode="normal", password="", files=[]):
    assert type(files)==list
    msg = MIMEMultipart()
    msg['From'] = fro
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(text))
    for file in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(file,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
        msg.attach(part)

    if mode == 'tls':
        mailServer = smtplib.SMTP(server, 587)
        mailServer.ehlo()
        mailServer.starttls()
        mailServer.ehlo()
        mailServer.login(fro, password)
    else:
        mailServer = smtplib.SMTP(server)
    

    mailServer.sendmail(fro, to, msg.as_string())
    # Should be mailServer.quit(), but that crashes...
    mailServer.close()

if __name__ == '__main__':
    import sys
    attachlist = []
    if not sys.argv[4:]:
        print "Usage: %s from to subject text server mode password attachments" % sys.argv[0]
    else:
        for arg in sys.argv[8:]:
            attachlist.append(arg)   
        sendmessage(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], attachlist)
        print "E-mail Sent"