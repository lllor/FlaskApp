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
from base64 import b64encode
from PIL import Image
import base64
import io
import time

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

@webapp.route('/search/form',methods=['GET'])
#Return image search form
def image_search_form():
    return render_template("imagesearchform.html")

@webapp.route('/search/result',methods=['POST'])
#Return image search form
def search_image():
    key = request.form.get("file_key")
    dictToSend = {key: key}
    if len(key)<1 or len(key)>=44:
        return render_template("errorpage.html", msg="invalid key, the length of a key has to between 1 char and 44 char")

    try:
        res = requests.get('http://localhost:5001/get/'+key)
    except requests.exceptions.ConnectionError as err:
        return render_template("errorpage.html", msg="failed to connect to memcache")


    dictFromServer = res.json()
    if res.status_code == 200 and dictFromServer:
        encoded_img_data = dictFromServer['content'].encode('ascii')
        
    elif res.status_code == 400:
        cnx = get_db()
        cursor = cnx.cursor()
        query = (''' SELECT path FROM `image` WHERE `key` = %s ''')
        try:
            cursor.execute(query,(key,))
            rows = cursor.fetchall() 
            if len(rows) == 0:
                return render_template("errorpage.html", msg="image key does not exist")
            
            print(rows[0][0].split(".")[-1])
            encoded_img_data = base64.b64encode(open(rows[0][0], "rb").read())
            """
            if image_type == "gif":
                im = Image.open(rows[0][0])
                data = io.BytesIO()
                image_type = rows[0][0].split(".")[-1]
                im.save(data, image_type)
                encoded_img_data = base64.b64encode(data.getvalue())
            else:
            """
            
        except mysql.connector.Error as err:
            print(err)
            print("Error Code:", err.errno)
            print("SQLSTATE", err.sqlstate)
            print("Message", err.msg)
            return render_template("errorpage.html", msg=err.msg)


    dictToSend = {'key': key, 'content': encoded_img_data.decode('utf-8')}
    try:
        res = requests.post('http://localhost:5001/put', json=dictToSend)
    except requests.exceptions.ConnectionError as err:
        return render_template("errorpage.html", msg="failed to connect to memcache")

    if res.status_code == 400 or res.status_code == 200:
        time.sleep(1)
        return render_template("imagesearchresult.html", img_data=encoded_img_data.decode('utf-8'))
    else:
        return render_template("errorpage.html", msg="failed to save to memcache")

    
