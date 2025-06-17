s# For any extra security utilities (e.g. email sending)
import sendgrid
from sendgrid.helpers.mail import Mail
from core.config import settings

def send_welcome_email(to_email: str):
    sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
    message = Mail(
        from_email=settings.FROM_EMAIL,
        to_emails=to_email,
        subject="Welcome to CF AutoBooks",
        html_content="<strong>Thanks for signing up!</strong>"
    )
    sg.send(message)
