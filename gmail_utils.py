import re
import email
import imaplib
import textrank

from bs4 import BeautifulSoup

FORBIDDEN_SUBJECT_STRINGS = ["=?UTF-8"]
STOP_WORDS = ['@', ' Re ', 'Re:', 'Fwd', ' |', '|', ' |, |']
KEYWORDS_COUNT = 15
SUBJECTS_COUNT = 35
CONTACTS_COUNT = 30


def gmail_login(email_address, password):
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


def get_inbox_email_ids_by_sender(gmail_object, sender_email, inbox_name="INBOX"):
    gmail_object.select(inbox_name)
    resp, items = gmail_object.search(None, '(FROM "{}")'.format(sender_email))
    items = items[
        0].split()  # I think it will be good to shuffle here, or to reverse the array so that the more recent email will pop up first

    return items


def get_email_subject_by_id(gmail_object, email_id):
    resp, data = gmail_object.fetch(email_id, '(BODY[HEADER.FIELDS (SUBJECT FROM)])')
    email_body = data[0][1]
    mail = email.message_from_string(email_body)

    return mail["Subject"]


def strip_key_phrases(key_phrases_set):
    for phrase in key_phrases_set:
        key_phrases_set.discard(phrase)
        key_phrases_set.add(phrase.strip())

    return key_phrases_set


def remove_duplicate_while_preserving_order(elements):
    seen = set()
    seen_add = seen.add
    return [x for x in elements if not (x in seen or seen_add(x))]


def get_email_keywords_by_sender(gmail_object, sender_email, count=KEYWORDS_COUNT):
    subjects = get_email_subjects_list_by_sender(gmail_object, sender_email, SUBJECTS_COUNT)
    keywords = []
    for subject in subjects:
        key_phrases = textrank.extract_key_phrases(subject)
        key_phrases = strip_key_phrases(key_phrases)
        subject_keywords = ', '.join(key_phrases)
        if len(subject_keywords) > 0:
            keywords.append(subject_keywords)

            for chopped_phrase in key_phrases:
                keywords.append(chopped_phrase)

        unique_keywords = remove_duplicate_while_preserving_order(keywords)
        if len(unique_keywords) == count:
            return unique_keywords

    return remove_duplicate_while_preserving_order(keywords)


def clean_subject(subject):
    for stop_word in STOP_WORDS:
        subject = subject.replace(stop_word, "")
        subject = subject.strip()

    return subject


def matching_keywords(filter_keywords, subject):
    if filter_keywords is None:
        return True
    else:
        keyword_list = re.findall(r"[\w']+", filter_keywords)
        return all(re.search(keyword, subject, re.IGNORECASE) for keyword in keyword_list)


def get_email_subjects_list_by_sender(gmail_object, sender_email, count, filter_keywords=None):
    email_ids = get_inbox_email_ids_by_sender(gmail_object, sender_email)
    subjects = []
    for email_id in email_ids:
        subject = get_email_subject_by_id(gmail_object, email_id)
        if not any(extension in subject for extension in FORBIDDEN_SUBJECT_STRINGS) and \
                matching_keywords(filter_keywords, subject):
            subject = clean_subject(subject)
            if subject.strip():
                subjects.append(subject)

        if len(subjects) == count:
            return remove_duplicate_while_preserving_order(subjects)

    return remove_duplicate_while_preserving_order(subjects)


def get_email_text(gmail_object, email_id):
    resp, data = gmail_object.fetch(email_id, "(RFC822)")
    email_body = data[0][1]
    mail = email.message_from_string(email_body)

    resp, data = gmail_object.fetch(email_id, '(BODY[1])')
    html_body = data[0][1]

    return mail["From"], mail["Subject"], strip_from_html(html_body)


def strip_from_html(email_html):
    soup = BeautifulSoup(email_html, 'html.parser')
    return soup.get_text()


def fetch_contacts(gmail_object, email_address, count=CONTACTS_COUNT, inbox_name="INBOX"):
    gmail_object.select(inbox_name)
    contacts_list = []
    result, data = gmail_object.search(None, 'ALL')
    ids = data[0]
    id_list = ids.split()  # I think it will be good to shuffle here, or to reverse the array so that the more recent email will pop up first
    id_list.reverse()
    skipped = []

    for i in id_list:
        if i in skipped:
            continue

        try:
            typ, data = gmail_object.fetch(i, '(RFC822)')

            for response_part in data:
                if isinstance(response_part, tuple):
                    import email
                    msg = email.message_from_string(response_part[1])
                    sender = msg['from'].split()[-1]
                    address = re.sub(r'[<>]', '', sender)

            if not re.search(r'' + re.escape(email_address), address) and not address in contacts_list:
                contacts_list.append(address)
                skipped.extend(get_inbox_email_ids_by_sender(gmail_object, address))

                if len(contacts_list) == count:
                    return contacts_list

        except Exception:
            continue