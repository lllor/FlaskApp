from flask import Flask
from flask import request, jsonify
from app import webapp
from app.config import UPLOAD_FOLDER
from datetime import datetime
import imghdr
from os.path import join, dirname, realpath
from flask import g
from werkzeug.utils import secure_filename
from app import webapp
import sys
import tempfile
import os
import mysql.connector
from app.config import db_config
from app.config import UPLOAD_FOLDER
import requests
from base64 import b64encode, b64decode
from PIL import Image
import base64
import io
from werkzeug.datastructures import ImmutableMultiDict

UPLOADS_PATH = join(dirname(realpath(__file__)), UPLOAD_FOLDER)
test1 = {'hello':'world'}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOADS_PATH = join(dirname(realpath(__file__)), UPLOAD_FOLDER)
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'], 
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'],
                                   autocommit=True)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@webapp.route('/api/health', methods=['GET'])
def api_health():
    return jsonify(test1)

@webapp.route('/api/upload', methods=['POST'])
def api_upload():
    key = request.form.get('key') 
    content = request.files['file'].read()

    print("request: ", type(content))
    dateTimeObj = datetime.now()

    # if user does not select file, browser also
    # submit a empty part without filename
    if not content:
        print('Missing file', file=sys.stderr)

    filename = request.files['file'].filename
    new_path = os.path.join(UPLOADS_PATH, dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")+filename)
    image = Image.open(io.BytesIO(content))
    image.save(new_path)

    cnx = get_db()

    cursor = cnx.cursor()
    

    query = (''' INSERT INTO `image` (`key`, `path`) VALUES (%s,%s); ''')

    
    try:
        cursor.execute(query,(key,new_path))
        cnx.commit()
        print("Success insert row into image", file=sys.stdout)
    except mysql.connector.Error as err:
        print(err)
        print("Error Code:", err.errno)
        print("SQLSTATE", err.sqlstate)
        print("Message", err.msg)
        print(type(err.errno))
        if err.errno == 1062:
            print("here")
            query = ('''UPDATE `image` SET `path`=%s where `key`=%s;''')
            cursor.execute(query,(new_path,key))
            cnx.commit()
            
        else:
            os.remove(new_path)
            test2 = {
                "success": "false",
                "error": {
                    "code": 400,
                    "message": "failed to upload image: unable to upload image to database"
                }
            }
            return jsonify(test2)


    #TODO disable the key in memcache
    #invalidateKey(key)  to drop a specific key
    try:
        response = requests.post('http://localhost:5001/invalidate/'+key)
    except requests.exceptions.ConnectionError as err:
        print(err)
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: "+ err.message
            }
        }
        return jsonify(test2)

    if response.status_code == 400 or response.status_code == 200:
        test2 = {'success': "true"}
        return jsonify(test2)
    else:
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: unable to invalid the key"
            }
        }
        return jsonify(test2)

    

@webapp.route('/api/list_key', methods=['POST'])
def api_list_key():
    cnx = get_db()

    cursor = cnx.cursor()

    
    query = (" SELECT * FROM image ")
    cursor.execute(query, multi=True)

    rows = cursor.fetchall()
    keys = []
    for row in rows:
        keys.append(row[0])
    test2 = {'success': "true", "keys": keys}
    return jsonify(test2)

@webapp.route('/api/key/<key>', methods=['POST'])
def api_search(key):
    res = requests.get('http://192.168.40.128:5001/get/'+key)

    dictFromServer = res.json()
    if res.status_code == 200:
        encoded_img_data = dictFromServer['content'].encode('ascii')
        
    elif res.status_code == 400:
        cnx = get_db()
        cursor = cnx.cursor()
        query = (''' SELECT path FROM `image` WHERE `key` = %s ''')
        try:
            cursor.execute(query,(key,))
            rows = cursor.fetchall() 
            print("rows", rows[0][0])
            im = Image.open(rows[0][0])
            data = io.BytesIO()
            im.save(data, rows[0][0].split(".")[-1])
            encoded_img_data = base64.b64encode(data.getvalue())
        except mysql.connector.Error as err:
            test2 = {
                "success": "false",
                "error": {
                    "code": 400,
                    "message": "failed to load image: unable to read the image"
                }
            }
            return jsonify(test2)

    dictToSend = {'key': key, 'content': encoded_img_data}
    res = requests.post('http://192.168.40.128:5001/put', json=dictToSend)

    if res.status_code == 400 or res.status_code == 200:
        test2 = {'success': "true", 'content': encoded_img_data.decode("utf-8")}
        return jsonify(test2)
    else:
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to load image: unable to save the image to memcache"
            }
        }
        return jsonify(test2)