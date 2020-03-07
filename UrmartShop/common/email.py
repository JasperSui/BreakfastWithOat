from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def SendEmailByGmail(sender_ac,  recipient, subject, content):

    message = Mail(
        from_email=sender_ac,
        to_emails=recipient,
        subject=subject,
        html_content=content
    )

    try:
        sg = SendGridAPIClient('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')

        response = sg.send(message)

        if (response.status_code == 202):

            return True
        
        else:

            return False
    
    except Exception as e:

        print(e.message)