from flask import Flask, jsonify, request

from chatup_db_utils import *

from gmail_utils import gmail_login, get_email_keywords_by_sender, get_email_subjects_list_by_sender

app = Flask(__name__)
CONTACTS_COUNT = 30
TOPICS_COUNT = 30


@app.route('/')
def root():
    return "Welcome To ChatUp Rest API"


@app.route('/login', methods=['POST'])
def login():
    try:
        password = request.form['gmail_password']
        email = request.form['gmail_address'].lower()
        gmail_login(email, password)

        with chatup_db_context() as cursor:
            user_id = get_user_id_by_email(cursor, email)
            if user_id is None:
                user_id = add_user_and_get_new_user_id(cursor, email, password)

            else:
                update_user_password(cursor, user_id, password)

    except Exception as e:
        user_id = -1

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
                                                        table_name="sub_categories",
                                                        field_name="sub_category_name",
                                                        entry_id=sub_category_id)

    topics = get_topics_by_sub_category_name(sub_category_name, count=30)

    return_dict = {'ideas': topics}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/favourite_sub_categories', methods=['GET'])
def favorites_sub_categories(user_id):
    with chatup_db_context() as cursor:
        sub_categories = get_user_favorites_subcategories(cursor,
                                                          user_id)

    return_dict = {'favourite_categories': sub_categories}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/add_favourite_sub_category', methods=['POST'])
def add_user_favorite_sub_category(user_id):
    sub_category_id = request.form['sub_category_id']
    sub_category_id = int(sub_category_id)

    with chatup_db_context() as cursor:
        add_sub_category_to_user_favorites(cursor, user_id, sub_category_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/remove_favourite_sub_category', methods=['POST'])
def remove_user_favorites_sub_category(user_id):
    sub_category_id = int(request.form['sub_category_id'])

    with chatup_db_context() as cursor:
        remove_sub_category_from_user_favorites(cursor, user_id, sub_category_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/switch_favourite_sub_categories', methods=['POST'])
def switch_user_favorites_sub_categories(user_id):
    old_sub_category_id = int(request.form['old_sub_category_id'])
    new_sub_category_id = int(request.form['new_sub_category_id'])

    with chatup_db_context() as cursor:
        switch_sub_category_user_favorites(cursor,
                                           user_id,
                                           old_sub_category_id,
                                           new_sub_category_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/predefined_sub_categories', methods=['GET'])
def predefined_sub_categories():
    with chatup_db_context() as cursor:
        sub_categories = get_predefined_recommended_sub_categories(cursor)

    return_dict = {'recommended': sub_categories}
    return jsonify(return_dict)


# fetches CONTACTS_COUNT contacts from emails. this can take a while, and should be preformed as
# little as possible, perhaps for backend internal use only
@app.route('/users/<int:user_id>/contacts', methods=['POST'])
def contacts_fetch(user_id):
    fetch_and_insert_contacts_to_db(user_id, CONTACTS_COUNT)

    return_dict = {}
    return jsonify(return_dict)


# Should only be called after contacts_fetch call
@app.route('/users/<int:user_id>/contacts', methods=['GET'])
def get_contacts(user_id):
    with chatup_db_context() as cursor:
        contacts = get_contacts_from_db(cursor, user_id)

    return_dict = {"contacts": contacts}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/favourite', methods=['GET'])
def get_favorite_contacts(user_id):
    with chatup_db_context() as cursor:
        contacts = get_contacts_from_db(cursor, user_id, only_favorites=True)

    return_dict = {"favourite_contacts": contacts}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/set_favourite', methods=['POST'])
def set_contact_favorite(user_id):
    contact_id = request.form['contact_id']
    contact_id = int(contact_id)
    assert_contacts_belong_to_user(user_id, [contact_id])

    with chatup_db_context() as cursor:
        add_contact_to_favorites(cursor, contact_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/switch_favourites', methods=['POST'])
def switch_favorite_contacts(user_id):
    old_contact_id = request.form['old_contact_id']
    old_contact_id = int(old_contact_id)
    new_contact_id = request.form['new_contact_id']
    new_contact_id = int(new_contact_id)

    assert_contacts_belong_to_user(user_id, [old_contact_id, new_contact_id])

    with chatup_db_context() as cursor:
        add_contact_to_favorites(cursor, new_contact_id)
        remove_contact_from_favorites(cursor, old_contact_id)

    return_dict = {}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/<int:contact_id>/keywords', methods=['GET'])
def get_contact_keywords(user_id, contact_id):
    with chatup_db_context() as cursor:
        contact_email = get_first_field_value_by_id(cursor,
                                                    table_name='contacts',
                                                    field_name='contact_email',
                                                    entry_id=contact_id)

    gmail_object = get_gmail_object(user_id)

    keywords_list = get_email_keywords_by_sender(gmail_object, contact_email)

    return_dict = {'keywords': keywords_list}
    return jsonify(return_dict)


@app.route('/users/<int:user_id>/contacts/<int:contact_id>/topics', methods=['POST'])
def get_contact_topics_by_keyword(user_id, contact_id):
    keyword = request.form['keyword']
    with chatup_db_context() as cursor:
        contact_email = get_first_field_value_by_id(cursor,
                                                    table_name='contacts',
                                                    field_name='contact_email',
                                                    entry_id=contact_id)
    gmail_object = get_gmail_object(user_id)

    subjects = get_email_subjects_list_by_sender(gmail_object=gmail_object,
                                                 count=TOPICS_COUNT,
                                                 sender_email=contact_email,
                                                 filter_keywords=keyword)

    return_dict = {'ideas': subjects}
    return jsonify(return_dict)
