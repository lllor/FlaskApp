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

key = 1

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

@webapp.route('/config/form',methods=['GET'])
#Return file upload form
def show_memcache_config_form():
    cnx = get_db()

    cursor = cnx.cursor()

    
    query = (" SELECT * FROM config ")

    try:
        cursor.execute(query, multi=True)
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        return render_template("errorpage.html", msg=err.msg)

    if len(rows) == 0:
        return render_template("errorpage.html", msg="failed to read config information")
            
    check = rows[0][0] == 0
    print(rows[0])
    if check:
        policy = "Random Replacement"
    else:
        policy = "Least Recently Used"
    key = rows[0][0]
    return render_template("memcacheconfig.html", data=rows[0], check = check, policy=policy)

@webapp.route('/config/update', methods=['POST'])
def config_memcache():

    if request.form.get('policy-select') == "Random Replacement":
        new_policy = 0
    else:
        new_policy = 1
    new_capacity = request.form.get('capacity')

    print(new_capacity,new_policy)

    cnx = get_db()

    cursor = cnx.cursor()

    query = (''' UPDATE `config` SET `capacity`= %s, `policy`=%s limit 1''')

    
    try:
        cursor.execute(query,(new_capacity,new_policy))
        cnx.commit()
        print("Success insert row into config", file=sys.stdout)
    except mysql.connector.Error as err:
        print(err)
        print("Error Code:", err.errno)
        print("SQLSTATE", err.sqlstate)
        print("Message", err.msg)
        return render_template("errorpage.html", msg=err.msg)

    try:
        response = requests.post('http://localhost:5001/config/'+str(new_policy)+'/'+str(new_capacity))
    except requests.exceptions.ConnectionError as err:
        return render_template("errorpage.html", msg="failed to connect to memcache")
        


    if response.status_code == 400 or response.status_code == 200:
        return redirect(url_for('main'))
    else:
        return render_template("errorpage.html", msg="failed to save to memcache")

@webapp.route('/config/clear',methods=['POST'])
def clear_memcache():
    try:
        res = requests.post('http://localhost:5001/clear')
    except requests.exceptions.ConnectionError as err:
        return render_template("errorpage.html", msg="failed to connect to memcache")
    return redirect(url_for('main'))

