from flask import render_template, redirect, url_for, request, g
from werkzeug.utils import secure_filename
from os.path import join, dirname, realpath
from app import webapp
import sys
import tempfile
import os
import mysql.connector
from app.config import db_config

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
    cursor.execute(query, multi=True)

    rows = cursor.fetchall() 

    check = rows[0][2] == 'Random Replacement'
    print("rows",rows[0],check)
    key = rows[0][0]
    return render_template("memcacheconfig.html", data=rows[0], check = check)

@webapp.route('/', methods=['POST'])
def config_memcache():
    new_policy = request.form.get('policy-select')
    new_capacity = request.form.get('capacity')

    cnx = get_db()

    cursor = cnx.cursor()

    query = (''' UPDATE `config` SET `capacity`= %s, `policy`=%s where id=%s; ''')

    
    try:
        cursor.execute(query,(new_capacity,new_policy,key))
        cnx.commit()
        print("Success insert row into config", file=sys.stdout)
    except mysql.connector.Error as err:
        print(err)
        print("Error Code:", err.errno)
        print("SQLSTATE", err.sqlstate)
        print("Message", err.msg)
        return render_template("errorpage.html", msg=err.msg)

    #TODO notify memcache to refresh
    
    return render_template("main.html")