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
import filetype

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
    if not request.files:
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: missing uploaded"
            }
        }
        return jsonify(test2)

    filename = request.files['file'].filename
    print("filename:",filename.split('.')[-1])
    if not filename or not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: missing uploaded file name"
            }
        }
        return jsonify(test2)


    content = request.files['file'].read()

    #print("request: ", type(content))
    dateTimeObj = datetime.now()
    new_path = os.path.join(UPLOADS_PATH, dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")+filename)
    # if user does not select file, browser also
    # submit a empty part without filename
    if not content:
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: missing uploaded file"
            }
        }
        return jsonify(test2)

    if len(key) >= 44 or len(key) < 1:
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: invalid key length"
            }
        }
        return jsonify(test2)

    with open(new_path, "wb") as fh:
        fh.write(content)

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
                "message": "failed to upload image: failed to connect backend"
            }
        }
        return jsonify(test2)

    if response.status_code == 400 or response.status_code == 200:
        test2 = {'success': "true"}
        return jsonify(test2)
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
    if not key or len(key)>=44 or len(key)<1:
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to load image: invalid key"
            }
        }
        return jsonify(test2)


    try:
        res = requests.get('http://localhost:5001/get/'+key)
    except requests.exceptions.ConnectionError as err:
        print(err)
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: failed to connect backend"
            }
        }
        return jsonify(test2)
    dictFromServer = res.json()
    if res.status_code == 200 and dictFromServer:
        print("HERE")
        encoded_img_data = dictFromServer['content'].encode('ascii')
        
    elif res.status_code == 400:
        cnx = get_db()
        print("HERE!!!!")
        cursor = cnx.cursor()
        query = (''' SELECT path FROM `image` WHERE `key` = %s ''')
        try:
            cursor.execute(query,(key,))
            rows = cursor.fetchall()
            if len(rows) == 0:
                test2 = {
                    "success": "false",
                    "error": {
                        "code": 400,
                        "message": "failed to load image: "+ "image key does not exist",
                    }
                }
                return jsonify(test2)
            
            encoded_img_data = base64.b64encode(open(rows[0][0], "rb").read())            
        except mysql.connector.Error as err:
            test2 = {
                "success": "false",
                "error": {
                    "code": 400,
                    "message": "failed to load image:"+err.msg,
                }
            }
            return jsonify(test2)
    else:
        test2 = {
                "success": "false",
                "error": {
                    "code": 400,
                    "message": "failed to load image: failed to connect to memcache",
                }
            }
        return jsonify(test2)
    dictToSend = {'key': key, 'content': encoded_img_data.decode('utf-8')}

    try:
        res = requests.post('http://localhost:5001/put', json=dictToSend)
    except requests.exceptions.ConnectionError as err:
        print(err)
        test2 = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "failed to upload image: failed to connect backend"
            }
        }
        return jsonify(test2)

    if res.status_code == 400 or res.status_code == 200:
        test2 = {'success': "true", 'content': dictToSend['content']}
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
