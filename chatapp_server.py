from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)


@app.route('/')
def root():
    return "Welcome To ChatApp"


@app.route('/users/<int:userid>')
def user(userid):
    user = get_user_info_by_id(userid)

    return jsonify(user)


@app.route('/users/<int:user_id>/contacts/<int:contact_id>')
def contact(user_id, contact_id):
    contact = get_contact(user_id, contact_id)

    return jsonify(contact)


def get_user_info_by_id(user_id):
    return {'user_id': user_id, 'name': "Bar"}


def get_contact(user_id, contact_id):
    return {'contact_id': contact_id, 'user_id': user_id, 'name': "Shabi"}
