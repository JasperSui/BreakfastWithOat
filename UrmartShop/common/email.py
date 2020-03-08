from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def SendEmailBySendGrid(sender_ac,  recipient, subject, content):

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