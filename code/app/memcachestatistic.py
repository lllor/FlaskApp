from flask import render_template, redirect, url_for, request, g
from werkzeug.utils import secure_filename
from os.path import join, dirname, realpath
from app import webapp
import sys
import tempfile
import os
import mysql.connector
from app.config import db_config
import requests

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
    try:
        response = requests.post('http://localhost:5001/config/3/-1')
    except requests.exceptions.ConnectionError as err:
        return render_template("errorpage.html", msg="failed to connect to memcache")

    if not response.status_code == 200:
        return render_template("errorpage.html", msg="failed to read memcache statistics")
    
    cnx = get_db()

    cursor = cnx.cursor()

    query = (" SELECT * FROM statistics ")
    
    try:
        cursor.execute(query, multi=True)
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template("errorpage.html", msg=err.msg)
    

    while not response.json():
        print("loading ...")

    #print(response.json())
    #return redirect(url_for('main'))
    return render_template("memcachestatistic.html", data=response.json())
