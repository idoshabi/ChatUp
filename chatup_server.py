from flask import Flask, jsonify, request
from contextlib import contextmanager
from functools import partial
from gmail_utils import login, fetch_contacts
import requests
import sqlite3

app = Flask(__name__)
CONTACT_DATA_URL = 'http://picasaweb.google.com/data/entry/api/user/{}?alt=json'
CHATUP_DB_NAME = 'chatup_db.db'
NUM_OF_PREDEFINED_SUBCATEGORIES = 3
EMPTY_AVATAR = "http://www.rammandir.ca/sites/default/files/default_images/defaul-avatar_0.jpg"
CONTACTS_COUNT = 10


@contextmanager
def db_context(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()

    finally:
        conn.close()


chatup_db_context = partial(db_context, db_name=CHATUP_DB_NAME)


@app.route('/')
def root():
    return "Welcome To ChatApp"


@app.route('/login', methods=['POST'])
def login():
    try:
        password = request.form['gmail_password']
        email = request.form['gmail_address'].lower()
        login(email, password)

        with chatup_db_context() as cursor:
            user_id = get_user_id_by_email(cursor, email)
            if user_id is None:
                user_id = add_user_and_get_new_user_id(cursor, email, password)

            else:
                update_user_password(cursor, user_id, password)

    except Exception:
        user_id = None

    return_dict = {'gmail_password': None,
                   'gmail_address': None,
                   'user_id': user_id}

    return jsonify(return_dict)


@app.route('/main_catergories', methods=['GET'])
def main_categories():
    with chatup_db_context() as cursor:
        main_categories = get_main_categories(cursor)

    return_dict = {'categories': main_categories}

    return jsonify(return_dict)


@app.route('/main_catergories/<string:main_category>/sub_catergories', methods=['GET'])
def sub_categories(main_category):
    with chatup_db_context() as cursor:
        sub_categories = get_sub_categories_by_main_category(cursor, main_category)

    return_dict = {'sub_categories': sub_categories}

    return jsonify(return_dict)


@app.route('/sub_catergories/<int:sub_category_id>/topics', methods=['GET'])
def sub_category_topics(sub_category_id):
    with chatup_db_context() as cursor:
        sub_category_name = get_first_field_value_by_id(cursor,
                                                        table_name="sub_catergories",
                                                        field_name="sub_category_name",
                                                        entry_id=sub_category_id)

    topics = get_topics_by_sub_category_name(sub_category_name, count=30)

    return_dict = {'ideas': topics}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/favorite_sub_categories', methods=['GET'])
def favorites_sub_categories(user_id):
    with chatup_db_context() as cursor:
        sub_categories = get_user_favorites_subcategories(cursor,
                                                          user_id)

    return_dict = {'favourite_categories': sub_categories}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/favorite_sub_categories', methods=['POST'])
def add_user_favorite_sub_category(user_id):
    sub_category_id = request.form['sub_category_id']
    sub_category_id = int(sub_category_id)

    with chatup_db_context() as cursor:
        add_sub_category_to_user_favorites(cursor, user_id, sub_category_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/favorite_sub_categories', methods=['POST'])
def remove_user_favorites_sub_category(user_id):
    sub_category_id = int(request.form['sub_category_id'])

    with chatup_db_context() as cursor:
        remove_sub_category_from_user_favorites(cursor, user_id, sub_category_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/favorite_sub_categories', methods=['POST'])
def switch_user_favorites_sub_categories(user_id):
    old_sub_category_id = int(request.form['old_sub_category_id'])
    new_sub_category_id = int(request.form['new_sub_category_id'])

    with chatup_db_context() as cursor:
        switch_user_favorites_sub_categories(cursor,
                                             user_id,
                                             old_sub_category_id,
                                             new_sub_category_id)

    return_dict = {}
    return jsonify(return_dict)


# fetches CONTACTS_COUNT contacts from emails. this can take a while, and should be preformed as
# little as possible, perhaps for backend internal use only
@app.route('/users/<int:user_id>/contacts', methods=['POST'])
def contacts_fetch(user_id):
    with chatup_db_context() as cursor:
        email = get_first_field_value_by_id(cursor,
                                            entry_id=user_id,
                                            table_name='users',
                                            field_name='email')
        password = get_first_field_value_by_id(cursor,
                                               entry_id=user_id,
                                               table_name='users',
                                               field_name='password')
    fetch_and_insert_contacts_to_db(email, password, CONTACTS_COUNT)

    return_dict = {}
    return jsonify(return_dict)


# Should only be called after contacts_fetch call
@app.route('/users/<int:user_id>/contacts', methods=['GET'])
def get_contacts(user_id):
    with chatup_db_context() as cursor:
        contacts = get_contacts_from_db(cursor, user_id)

    return_dict = {"contacts": contacts}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/set_favorite', methods=['POST'])
def set_contact_favorite(user_id):
    contact_id = request.form['contact_id']
    contact_id = int(contact_id)

    with chatup_db_context() as cursor:
        add_contact_to_favorites(cursor, contact_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/switch_favorites', methods=['POST'])
def switch_favorites(user_id):
    contact_id_to_remove = request.form['contact_id_to_remove']
    contact_id_to_remove = int(contact_id_to_remove)
    contact_id_to_add = request.form['contact_id_to_add']
    contact_id_to_add = int(contact_id_to_add)

    with chatup_db_context() as cursor:
        add_contact_to_favorites(cursor, contact_id_to_add)
        remove_contact_from_favorites(cursor, contact_id_to_remove)

    return_dict = {}
    return jsonify(return_dict)


# ToDo: RSS
def get_topics_by_sub_category_name(sub_category_name, count):
    # sub_category_name = sub_category_name.lower()
    # But its better to make sure it ignores case
    raise NotImplemented()


def get_user_image(email_address):
    email_address = email_address.lower()

    data = requests.get(CONTACT_DATA_URL.format(email_address))
    try:
        return data.json()["entry"]["gphoto$thumbnail"]['$t']

    except Exception:
        return EMPTY_AVATAR


def get_user_name(email_address):
    email_address = email_address.lower()

    data = requests.get(CONTACT_DATA_URL.format(email_address))
    try:
        name = data.json()["entry"]["gphoto$nickname"]['$t']
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


def fetch_and_insert_contacts_to_db(email_address, password, count):
    gmail_object = login(email_address, password)
    contacts = fetch_contacts(gmail_object, email_address, count=count)

    for contact_email in contacts:
        with chatup_db_context() as cursor:
            user_id = get_user_id_by_email(cursor, email_address)
            image_src = get_user_image(contact_email)
            name = get_user_name(contact_email)
            cursor.execute(
                "insert or ignore into contacts \
                (id, user_id, contact_email, image_src, name, is_favorite) \
                values (NULL, {}, '{}', '{}', '{}', 0)".format(user_id,
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
