# -*- coding: utf-8 -*-

from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from jinja2 import Environment, FileSystemLoader
import os
import smtplib
import sys
import zipfile
from crud.configCrud import get_storage_config
import logging
from collections import OrderedDict
from appConfig import base_config
import mimetypes
from email.mime.base import MIMEBase
from email import encoders

# 【关键步骤 1】手动添加 xlsx 的定义，防止系统库识别不出来
mimetypes.add_type('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx')
mimetypes.add_type('application/vnd.ms-excel', '.xls')


def get_images_id(image_paths=None):
    """
    获取图片的 MIME 对象列表并添加 Content-ID 头

    Args:
        image_paths (list[tuple]): 图片路径与图片 ID 的元组列表

    Returns:
        list: MIMEImage 对象列表
    """
    result = []
    if image_paths is None:
        image_paths = []  # 如果 image_paths 为空，初始化为空列表
    if len(image_paths) == 0:
        return result
    for image_path, image_id in image_paths:
        if not os.path.exists(image_path):
            continue
        with open(image_path, 'rb') as f:
            image_data = f.read()
        name = os.path.basename(image_path)
        mime_image = MIMEImage(image_data, name=name)
        mime_image.add_header('Content-ID', image_id)
        result.append(mime_image)
    return result


class EmailNotification:
    logger = logging.getLogger('app')

    def __init__(self, db, type='storage'):
        self.db = db
        self.config = get_storage_config(db=self.db)
        self.base_config = base_config
        # self.logger.error(self.base_config.get_info())
        if self.config:
            self.host = self.config.mail_host
            self.port = self.config.mail_port or 587
            self.sender = self.config.mail_user.replace('-', '.') if self.config.mail_user else None
            self.password = self.config.mail_password
            self.to = self.config.mail_to
        else:
            self.logger.error("Configuration cannot be loaded.")

    def send_email(self, subject, content, recipient=None, attachments=None, html=True, sender=None, password=None,
                   to=None, cc=None, cc_admin=True):
        if not self.config:
            self.logger.error("No configuration found.")
            return False
        message = self._create_message(subject, content, recipient, html, to, cc)
        if to is not None:
            recipient += to
        if cc is not None:
            recipient += cc
        recipient_list = self._process_recipients(recipient, cc_admin)
        if not message:
            return False
        if attachments:
            attachments = attachments.split(',') if isinstance(attachments, str) else attachments
            attachments = self.zip_attachments(attachments) if self._is_attachments_large(attachments, sys.getsizeof(
                message)) else attachments
            self._add_attachments_to_message(message, attachments)
        return self._send_message(recipient_list, message, sender, password)

    def send_image_mail(self, subject, content, recipient=None, image_paths=None):
        if not self.config:
            self.logger.error("No configuration found.")
            return False
        recipient_list = self._process_recipients(recipient)
        message = self._create_message(subject, content, recipient_list, html=True)
        if not message:
            return False
        mime_images = get_images_id(image_paths or [])
        for mime_image in mime_images:
            message.attach(mime_image)
        return self._send_message(recipient_list, message)

    def send_email_via_template(self, subject, template_name, recipient=None, data=None, attachments=None, sender=None,
                                password=None, to=None, cc=None, cc_admin=True):
        html_content = self.render_template(template_name, data)
        if recipient is None:
            recipient = []
        return self.send_email(subject=subject, content=html_content, recipient=recipient, attachments=attachments,
                               sender=sender, password=password, to=to, cc=cc, cc_admin=cc_admin)

    def send_image_via_template(self, subject, template_name, recipient=None, data=None, image_paths=None):
        if recipient is None:
            recipient = []
        html_content = self.render_template(template_name, data)
        return self.send_image_mail(subject, html_content, recipient, image_paths)

    def render_template(self, template_name, data=None):
        try:
            if data is None:
                self.logger.warning('Data for template rendering is None')
                return None

            template_dir = os.path.join(self.base_config.get('APP_ROOT_PATH'), 'utils', 'mailTools', 'template')
            j2loader = FileSystemLoader(template_dir)
            env = Environment(loader=j2loader)
            template_path = f"{template_name}.html"
            if not os.path.exists(os.path.join(template_dir, template_path)):
                self.logger.warning(f'Cannot find template: {os.path.join(template_dir, template_path)}')
                return None
            j2_template = env.get_template(template_path)
            return j2_template.render(data=data)
        except Exception as e:
            self.logger.error(f'Template rendering error: {e}')
            return None

    @staticmethod
    def zip_attachments(attachments):
        attach_dir = next((os.path.dirname(att) for att in attachments if os.path.isfile(att)), None)
        if not attach_dir:
            return None
        attach_zip = os.path.join(attach_dir, 'attachments.zip')
        with zipfile.ZipFile(attach_zip, 'w', zipfile.ZIP_DEFLATED) as f:
            for attachment in attachments:
                if os.path.isfile(attachment):
                    f.write(os.path.abspath(attachment), os.path.basename(attachment))
        return attach_zip

    @staticmethod
    def _is_attachments_large(attachments, message_size):
        if not attachments:
            return False
        max_size = 10 * 1024 * 1024  # 10MB
        total_size = sum(os.path.getsize(att) for att in attachments if os.path.isfile(att))
        return message_size + total_size >= max_size

    def _process_recipients(self, recipient, cc_admin=True):
        try:
            if isinstance(recipient, str):
                recipient = recipient.split(';')
            if not recipient:
                recipient = []
            # self.logger.info(f"{recipient} {cc_admin}")
            if self.to and cc_admin is True and self.base_config.get('MODEL') != 'dev':
                to_list = self.to.split(';') if ';' in self.to else self.to.split()
                recipient.extend(to_list)
            # Use OrderedDict to maintain order and remove duplicates
            return list(OrderedDict.fromkeys(recipient))
        except Exception as e:
            self.logger.error(f"error in process recipients: {recipient} ")
            return []

    def _create_message(self, subject, content, recipient_list, html=True, to=None, cc=None):
        message = MIMEMultipart('mixed')
        message['Subject'] = Header(subject, 'utf-8')
        if len(recipient_list) > 0 or to is not None:
            message['To'] = recipient_list[0] if to is None else ', '.join(list(set(to)))
        if len(recipient_list) > 1 or cc is not None:
            message['Cc'] = ', '.join(list(set(recipient_list[1:]))) if cc is None else ', '.join(list(set(cc)))

        message_text = MIMEText(content, 'html', 'utf-8') if html else MIMEText(content, 'plain', 'utf-8')
        message.attach(message_text)
        return message

    def _add_attachments_to_message(self, message, attachments):
        """Add attachments to email message"""
        if not attachments:
            return

        for filepath in attachments:
            try:
                if not os.path.isfile(filepath):
                    self.logger.error(f"Attachment file not found: {filepath}")
                    continue

                filename = os.path.basename(filepath)

                ctype, encoding = mimetypes.guess_type(filepath)

                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'

                maintype, subtype = ctype.split('/', 1)

                with open(filepath, 'rb') as f:
                    file_data = f.read()

                att = MIMEBase(maintype, subtype)
                att.set_payload(file_data)
                encoders.encode_base64(att)

                att.add_header('Content-Disposition', 'attachment', filename=filename)

                message.attach(att)
                self.logger.info(f"Attachment added: {filename} ({ctype})")

            except Exception as e:
                self.logger.error(f"Failed to add attachment {filepath}: {str(e)}")

    def _send_message(self, recipient_list, message, sender=None, password=None):
        sender = self.sender if sender is None else sender
        password = self.password if password is None else password
        try:
            recipient_emails = recipient_list if isinstance(recipient_list, list) else list(set(recipient_list))
            if len(recipient_emails) == 0:
                self.logger.warning(f"Please add one more recipient emails")
                return False
            with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(sender, password)
                # Send the email
                smtp.sendmail(sender, recipient_emails, message.as_string())
        except Exception as e:
            self.logger.error(f"Send Mail Error: {e}")
            self.logger.info(f"[host:{self.host}:{self.port}][user:{sender} {password}][recipients:{recipient_emails}]")
            return False
        return True
