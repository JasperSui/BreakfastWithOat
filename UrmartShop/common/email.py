from email.mime.text import MIMEText
import smtplib

def SendEmailByGmail(sender_ac, sender_pw, recipient, subject, content):

    msg = MIMEText(content, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender_ac
    msg['To'] = recipient

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(sender_ac, sender_pw)
    server.send_message(msg)
    server.quit()
    
    return True