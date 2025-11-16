import os
import logging
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template, TemplateNotFound
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To

from app.core.config import settings
from app.utils.events import event_bus
import asyncio

async def handle_email_send_requested(data):
    try:
        await EmailService._send_email_via_sendgrid(
            data["to_email"],
            data["subject"],
            data["template_name"],
            data["template_context"]
        )
    except Exception as e:
        logging.error(f"Failed to send email to {data['to_email']}: {e}")

event_bus.subscribe("email_send_requested", handle_email_send_requested)

class EmailService:
    _template_env = None

    @classmethod
    def _get_template_env(cls):
        """
        Initialize Jinja2 template environment with inheritance support
        """
        if cls._template_env is None:
            # Find templates directory
            template_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                'templates'
            )

            cls._template_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html']),
                enable_async=False
            )
        return cls._template_env

    @classmethod
    def render_template(cls, template_name: str, context: dict) -> str:
        """
        Render an email template

        :param template_name: Name of the template file
        :param context: Dictionary of template variables
        :return: Rendered HTML template
        """
        try:
            # Add default context variables
            default_context = {
                'company_name': 'Your Company',
                'current_year': datetime.now().year,
                **context
            }

            template_env = cls._get_template_env()
            template = template_env.get_template(template_name)
            return template.render(**default_context)
        except Exception as e:
            logging.error(f"Error rendering email template {template_name}: {e}")
            raise


    @classmethod
    async def send_email(
        cls,
        to_email: str,
        subject: str,
        template_name: str,
        template_context: dict,
    ):
        await event_bus.publish("email_send_requested", {
            "to_email": to_email,
            "subject": subject,
            "template_name": template_name,
            "template_context": template_context,
            "timestamp": datetime.utcnow().isoformat()
        })

    @classmethod
    async def _send_email_via_sendgrid(
        cls,
        to_email: str,
        subject: str,
        template_name: str,
        template_context: dict,
    ):
        try:
            html_content = cls.render_template(template_name, template_context)

            from_email = (
                f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
                if hasattr(settings, 'EMAILS_FROM_NAME')
                else settings.EMAILS_FROM_EMAIL
            )

            message = Mail(
                from_email=from_email,
                to_emails=To(to_email),
                subject=subject,
                html_content=html_content
            )

            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sendgrid_client.send(message)

            if response.status_code not in [200, 201, 202]:
                logging.error(f"SendGrid error: {response.status_code} - {response.body}")
                raise Exception(f"SendGrid API error: {response.status_code}")

            logging.info(f"Email sent successfully to {to_email} via SendGrid")

        except Exception as e:
            logging.error(f"SendGrid email error: {e}")
            raise
