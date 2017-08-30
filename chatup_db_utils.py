import requests
import sqlite3
import feedparser

from contextlib import contextmanager
from functools import partial
from gmail_utils import gmail_login, fetch_contacts

CONTACT_DATA_URL = 'http://picasaweb.google.com/data/entry/api/user/{}?alt=json'
CHATUP_DB_NAME = 'chatup_db.db'
NUM_OF_PREDEFINED_SUBCATEGORIES = 3
EMPTY_AVATAR = "http://www.rammandir.ca/sites/default/files/default_images/defaul-avatar_0.jpg"

map_ideas_name = "Ideas"
rss_map_ynet = {'News': 'http://www.ynet.co.il/Integration/StoryRss3.xml',
                'Food': 'http://www.ynet.co.il/Integration/StoryRss975.xml',
                'Sport': 'http://www.ynet.co.il/Integration/StoryRss3.xml',
                'Culture': 'http://www.ynet.co.il/Integration/StoryRss538.xml',
                'Travel': 'http://www.ynet.co.il/Integration/StoryRss598.xml',
                'Lifesyle': 'http://www.ynet.co.il/Integration/StoryRss4104.xml'}

rss_map_walla = {'Quick_News': 'http://rss.walla.co.il/?w=/1/22/0/@rss.e',
                 'General News': 'http://rss.walla.co.il/?w=/1/0/12/@rss.e',
                 'Food': 'http://rss.walla.co.il/?w=/9/905/0/@rss.e',
                 'General Sport': 'http://rss.walla.co.il/?w=/3/0/12/@rss.el',
                 'Basketball': 'http://rss.walla.co.il/?w=/3/151/0/@rss.e',
                 'Soccer': 'http://rss.walla.co.il/?w=/3/156/0/@rss.e',
                 'Motors': 'http://rss.walla.co.il/?w=/31/0/12/@rss.e',
                 'Technology': 'http://rss.walla.co.il/?w=/6/0/12/@rss.e',
                 'Culture': 'http://rss.walla.co.il/?w=/4/0/12/@rss.e',
                 'Fashion': 'http://rss.walla.co.il/?w=/24/2121/0/@rss.e',
                 'Celebrities': 'http://rss.walla.co.il/?w=/22/0/12/@rss.e',
                 'Health': 'http://rss.walla.co.il/?w=/14/2500/0/@rss.e',
                 'Sexuality': 'http://rss.walla.co.il/?w=/139/1877/0/@rss.e',
                 'General Travel': 'http://rss.walla.co.il/?w=/14/2500/0/@rss.e',
                 'Jewish': 'http://rss.walla.co.il/?w=/138/0/12/@rss.e',
                 'Business': 'http://rss.walla.co.il/?w=/2/0/12/@rss.e',
                 'Home Design': 'http://rss.walla.co.il/?w=/35/3237/0/@rss.e'}


@contextmanager
def db_context(db_name):
    conn = sqlite3.connect(db_name)
    conn.text_factory = str

    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()

    finally:
        conn.close()


chatup_db_context = partial(db_context, db_name=CHATUP_DB_NAME)


############################ RSS

def get_walla_rss_by_subjet(subject, count):
    subject = rss_map_walla.get(subject)
    xml_sheet = feedparser.parse(subject)
    topic_list = []
    for topic in xml_sheet.entries:
        topic_list.append(topic['title'])
        # decrease by 1
        count -= 1
        if count == 0:
            break
    return topic_list


def get_topics_by_sub_category_name(sub_category_name, count):
    subjects = get_walla_rss_by_subjet(sub_category_name, count)
    topic_map = {map_ideas_name: subjects}
    return topic_map


############################ RSS


def get_user_image(email_address):
    email_address = email_address.lower()

    data = requests.get(CONTACT_DATA_URL.format(email_address))
    try:
        return data.json()["entry"]["gphoto$thumbnail"]['$t']

    except Exception:
        return EMPTY_AVATAR


def get_user_name(email_address):
    email_address = email_address.lower()
    email_address = email_address.replace("'", "")

    data = requests.get(CONTACT_DATA_URL.format(email_address))
    try:
        name = data.json()["entry"]["gphoto$nickname"]['$t']
        name = name.encode('utf-8')
        name = name.replace("'", "")
        assert not name.isdigit()

        return name
    except Exception:
        return email_address


def get_user_id_by_email(cursor, email_address):
    email_address = email_address.lower()

    query = cursor.execute("select id from users where email='{}'".format(email_address))
    result_list = query.fetchall()
    if len(result_list) == 0:
        return None

    else:
        user_id = result_list[0][0]

    return user_id


def add_user_and_get_new_user_id(cursor, email_address, password):
    email_address = email_address.lower()
    cursor.execute("insert into users (id, email, password) values (NULL, '{}', '{}')"
                   .format(email_address,
                           password))

    user_id = get_user_id_by_email(cursor, email_address)
    assert user_id is not None

    return user_id


def update_user_password(cursor, user_id, password):
    cursor.execute("update users set password='{}' where id={}".format(password, user_id))


def get_main_categories(cursor):
    query = cursor.execute("select distinct main_category_name from sub_categories")
    main_categories = [row[0] for row in query]

    return main_categories


def get_sub_categories_by_main_category(cursor, main_category):
    query = cursor.execute(
        "select id, sub_category_name, main_category_name \
        from sub_categories where main_category_name='{}' COLLATE NOCASE"
            .format(main_category))

    sub_categories = []
    for row in query:
        id, sub, main = row
        sub_categories.append({'id': id, 'name': sub, 'main_category_name': main})

    return sub_categories


def get_first_field_value_by_id(cursor, table_name, field_name, entry_id):
    query = cursor.execute("select {} from {} where id={}".format(field_name, table_name, entry_id))
    result_list = query.fetchall()
    if len(result_list) == 0:
        return None

    return result_list[0][0]


def get_user_favorites_subcategories(cursor, user_id):
    query = cursor.execute("select distinct s.id, s.sub_category_name, s.main_category_name \
    from favorite_sub_categories f INNER JOIN sub_categories s \
    on f.sub_category_id = s.id \
    where f.user_id={}".format(user_id))

    sub_categories = []
    for row in query:
        id, sub, main = row
        sub_categories.append({'id': id, 'name': sub, 'main_category_name': main})

    return sub_categories


def add_sub_category_to_user_favorites(cursor, user_id, sub_category_id):
    cursor.execute("insert into favorite_sub_categories (id, user_id, sub_category_id) \
    values (NULL, {}, {})".format(user_id, sub_category_id))


def remove_sub_category_from_user_favorites(cursor, user_id, sub_category_id):
    cursor.execute("delete from favorite_sub_categories where user_id={} and sub_category_id={}"
                   .format(user_id, sub_category_id))


def switch_sub_category_user_favorites(cursor, user_id, old_sub_category_id, new_sub_category_id):
    cursor.execute("update favorite_sub_categories set sub_category_id={} \
    where user_id={} and sub_category_id={}"
                   .format(new_sub_category_id, user_id, old_sub_category_id))


def get_predefined_recommended_sub_categories(cursor):
    query = cursor.execute("select s.id, s.sub_category_name, s.main_category_name \
    from predefined_recommended_sub_categories p INNER JOIN sub_categories s \
    on p.sub_category_id = s.id")

    sub_categories = []
    for row in query:
        id, sub, main = row
        sub_categories.append({'id': id, 'name': sub, 'main_category_name': main})
        if len(sub_categories) == NUM_OF_PREDEFINED_SUBCATEGORIES:
            return sub_categories

    return sub_categories


def get_contacts_from_db(cursor, user_id, only_favorites=False):
    query = "select id, name, image_src from contacts where user_id={}".format(user_id)
    if only_favorites:
        query += " and is_favorite > 0"

    query = cursor.execute(query)

    contacts = []
    for row in query:
        id, name, image_src = row
        contacts.append({'id': id, 'name': name, 'image_src': image_src})

    return contacts


def add_contact_to_favorites(cursor, contact_id):
    cursor.execute("update contacts set is_favorite={} where id={}".format(1, contact_id))


def remove_contact_from_favorites(cursor, contact_id):
    cursor.execute("update contacts set is_favorite={} where id={}".format(0, contact_id))


def get_credentials(user_id):
    with chatup_db_context() as cursor:
        email = get_first_field_value_by_id(cursor,
                                            entry_id=user_id,
                                            table_name='users',
                                            field_name='email')
        password = get_first_field_value_by_id(cursor,
                                               entry_id=user_id,
                                               table_name='users',
                                               field_name='password')
    return email, password


def get_gmail_object(user_id):
    email, password = get_credentials(user_id)

    return gmail_login(email, password)


def assert_contacts_belong_to_user(user_id, contacts_ids):
    for contact_id in contacts_ids:
        with chatup_db_context() as cursor:
            user_id_from_contact = get_first_field_value_by_id(cursor,
                                                               table_name='contacts',
                                                               field_name='user_id',
                                                               entry_id=contact_id)
            assert user_id == user_id_from_contact


def fetch_and_insert_contacts_to_db(user_id, count):
    email, password = get_credentials(user_id)
    gmail_object = gmail_login(email, password)

    contacts = fetch_contacts(gmail_object, email, count=count)

    for contact_email in contacts:
        with chatup_db_context() as cursor:
            user_id = get_user_id_by_email(cursor, email)
            image_src = get_user_image(contact_email)
            name = get_user_name(contact_email)
            cursor.execute(
                "insert or ignore into contacts \
                (id, user_id, contact_email, image_src, name, is_favorite) \
                values (NULL, ?, ?, ?, ?, 0)", (user_id,
                                                contact_email,
                                                image_src,
                                                name))


"""
do("insert into users (id, email, password) values (NULL, 'bsasson@infinidat.com', 'Bar2565121024')")
do("insert into sub_categories (id, sub_category_name, main_category_name) values (NULL, 'Football', 'Sport')")
do("insert into favorite_sub_categories (id, user_id, sub_category_id) values (NULL, 1, 2)")
do("insert into predefined_recommended_sub_categories (id, sub_category_id) values (NULL, 1)")


do("create table users (id integer primary key autoincrement, email text unique, password text)")
do("create table contacts (id integer primary key autoincrement, user_id integer, contact_email text, image_src text, name text, is_favorite integer, unique (user_id, contact_email) on conflict replace)")
do("create table sub_categories (id integer primary key autoincrement, sub_category_name text unique, main_category_name text)")
do("create table favorite_sub_categories (id integer primary key autoincrement, user_id integer, sub_category_id integer)")
do("create table predefined_recommended_sub_categories (id integer primary key autoincrement, sub_category_id integer)")
"""

"""
unitests:
def do(func, *args, **kwargs):
    with chatup_db_context() as cursor:
        f = func(cursor, *args, **kwargs)
        print f

do(get_sub_categories_by_main_category, main_category="sport")
do(get_user_favorites_subcategories, user_id=1)
do(get_predefined_recommended_sub_categories)
do(get_contacts_from_db, user_id=1, only_favorites=False)
do(get_contacts_from_db, user_id=1, only_favorites=True)

"""
