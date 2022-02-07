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
    print(request)
    dictToSend = {key: key}
    res = requests.get('http://127.0.0.1:8000/api/search', data=dictToSend)

    dictFromServer = res.json()
    if dictFromServer['success']:
        #return redirect(url_for('main'))
        encoded_img_data = base64.b64encode(dictFromServer['content'])
        
    else:
        cnx = get_db()

        cursor = cnx.cursor()
        query = (''' SELECT path FROM `image` WHERE `key` = %s ''')
        try:
            cursor.execute(query,(key,))
            rows = cursor.fetchall() 

            print("rows", rows[0][0])
            im = Image.open(rows[0][0])
            data = io.BytesIO()
            im.save(data, "JPEG")
            encoded_img_data = base64.b64encode(data.getvalue())
            
            #return render_template("imagesearchresult.html", img_link = '/home/lllor/Documents/ece1779/a1/aws_files/code/app/static/images/upload/test.jpeg')
        except mysql.connector.Error as err:
            print(err)
            print("Error Code:", err.errno)
            print("SQLSTATE", err.sqlstate)
            print("Message", err.msg)
            render_template("imagesearchform.html")

    dictToSend = {key: key, content: encoded_img_data}
    res = requests.post('http://127.0.0.1:8000/api/add', data=dictToSend)

    return render_template("imagesearchresult.html", img_data=encoded_img_data.decode('utf-8'))