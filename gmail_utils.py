import email, getpass, imaplib, os
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

    #email_html = ""
    #for part in mail.walk():
    #    # Skip attachments
    #    if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
    #        continue

    #    email_html += part.get_payload(decode=True)


    (rCode, data) = gmail_object.fetch(email_id, '(BODY[1])')
    html_body  = data[0][1]


    return mail["From"],  mail["Subject"], strip_from_html(html_body)

def strip_from_html(email_html):
    soup = BeautifulSoup(email_html, 'html.parser')
    return soup.get_text()



# @idoShabi, continue from http://www.christianpeccei.com/textmining/ for text mining