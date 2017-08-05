import re
import email
import imaplib

from bs4 import BeautifulSoup


def login(email_address, password):
    gmail_object = imaplib.IMAP4_SSL("imap.gmail.com")
    gmail_object.login(email_address, password)
    return gmail_object


def logout(gmail_object):
    return gmail_object.logout()


def get_inbox_email_ids(gmail_object, inbox_name="INBOX"):
    gmail_object.select(inbox_name)
    resp, items = gmail_object.search(None, "ALL")
    items = items[0].split()
    return items


def get_email_text(gmail_object, email_id):
    resp, data = gmail_object.fetch(email_id, "(RFC822)")
    email_body = data[0][1]
    mail = email.message_from_string(email_body)

    # email_html = ""
    # for part in mail.walk():
    #    # Skip attachments
    #    if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
    #        continue

    #    email_html += part.get_payload(decode=True)

    resp, data = gmail_object.fetch(email_id, '(BODY[1])')
    html_body = data[0][1]

    return mail["From"], mail["Subject"], strip_from_html(html_body)


def strip_from_html(email_html):
    soup = BeautifulSoup(email_html, 'html.parser')
    return soup.get_text()


def get_contacts(gmail_object, email_address, count=10, inbox_name="INBOX"):
    gmail_object.select(inbox_name)
    contacts_list = []
    result, data = gmail_object.search(None, 'ALL')
    ids = data[0]
    id_list = ids.split()

    for i in id_list:
        typ, data = gmail_object.fetch(i, '(RFC822)')

        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_string(response_part[1])
                sender = msg['from'].split()[-1]
                address = re.sub(r'[<>]', '', sender)

        if not re.search(r'' + re.escape(email_address), address) and not address in contacts_list:
            contacts_list.append(address)

            if len(contacts_list) == count:
                return set(contacts_list)


# @idoShabi, continue from http://www.christianpeccei.com/textmining/ for text mining
