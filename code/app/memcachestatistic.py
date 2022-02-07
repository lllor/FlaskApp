from flask import render_template, redirect, url_for, request, g
from werkzeug.utils import secure_filename
from os.path import join, dirname, realpath
from app import webapp
import sys
import tempfile
import os
import mysql.connector
from app.config import db_config

def connect_to_database():
    return mysql.connector.connect(user=db_config['user'], 
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'])

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@webapp.route('/memcache/stat',methods=['GET'])
#Return file upload form
def memcache_statistic():
    cnx = get_db()

    cursor = cnx.cursor()

    query = (" SELECT * FROM statistics ")
    cursor.execute(query, multi=True)

    rows = cursor.fetchall() 

    return render_template("memcachestatistic.html", row=rows[0])