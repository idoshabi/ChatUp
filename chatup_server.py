from flask import Flask, jsonify, request
from contextlib import contextmanager
from functools import partial
from gmail_utils import login
import requests
import sqlite3

app = Flask(__name__)
CONTACT_DATA_URL = 'http://picasaweb.google.com/data/entry/api/user/{}?alt=json'
CHATUP_DB_NAME = 'chatup_db.db'


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


@app.route('/users/<int:user_id>/contacts/<int:contact_id>')
def contact(user_id, contact_id):
    contact = get_contact(user_id, contact_id)

    return jsonify(contact)


# ToDo: RSS
def get_topics_by_sub_category_name(sub_category_name, count):
    raise NotImplemented()


def get_contact(user_id, contact_id):
    raise NotImplemented()


def get_user_image(email_address):
    data = requests.get(CONTACT_DATA_URL.format(email_address))
    return data.json()["entry"]["gphoto$thumbnail"]['$t']


def get_user_name(email_address):
    data = requests.get(CONTACT_DATA_URL.format(email_address))
    return data.json()["entry"]["gphoto$nickname"]['$t']


def get_user_id_by_email(cursor, email):
    query = cursor.execute("select * from users where email='{}'".format(email))
    result_list = query.fetchall()
    if len(result_list) == 0:
        return None

    else:
        user_id, _, _ = result_list[0]

    return user_id


def add_user_and_get_new_user_id(cursor, email, password):
    cursor.execute("insert into users (id, email, password) values (NULL, '{}', '{}')"
                   .format(email,
                           password))

    user_id = get_user_id_by_email(cursor, email)
    assert user_id is not None

    return user_id


def update_user_password(cursor, user_id, password):
    cursor.execute("update users set password='{}' where id={}".format(password, user_id))


def get_main_categories(cursor):
    query = cursor.execute("select distinct  main_category_name from sub_categories")
    main_categories = [row[0] for row in query]

    return main_categories


def get_sub_categories_by_main_category(cursor, main_category):
    query = cursor.execute(
        "select * from sub_categories where main_category_name='{}' COLLATE NOCASE"
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


"""
do("insert into users (id, email, password) values (NULL, 'bsasson@infinidat.com', 'Bar2565121024')")
do("insert into sub_categories (id, sub_category_name, main_category_name) values (NULL, 'Football', 'Sport')")
do("insert into favorite_sub_categories (id, user_id, sub_category_id) values (NULL, 1, 2)")

do("create table users (id integer primary key autoincrement, email text unique, password text)")
do("create table sub_categories (id integer primary key autoincrement, sub_category_name text unique, main_category_name text)")
do("create table favorite_sub_categories (id integer primary key autoincrement, user_id integer, sub_category_id integer)")
"""
