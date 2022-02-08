from flask import render_template, redirect, url_for, request, g
from werkzeug.utils import secure_filename
from os.path import join, dirname, realpath
from app import webapp
import sys
import tempfile
import os
import mysql.connector
from app.config import db_config
from app.config import UPLOAD_FOLDER
from datetime import datetime
import requests

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

@webapp.route('/upoad/form',methods=['GET'])
#Return file upload form
def upload_form():
    return render_template("fileupload.html")

@webapp.route('/upload',methods=['POST'])
#Return file upload form
def upload_image():

    key = request.form.get("file_key")
    dateTimeObj = datetime.now()

    # check if the post request has the file part
    if 'uploadedimage' not in request.files:
        print("Missing uploaded file", file=sys.stderr)

    new_file = request.files['uploadedimage']

    # if user does not select file, browser also
    # submit a empty part without filename
    if new_file.filename == '':
        print('Missing file name', file=sys.stderr)

    if new_file and allowed_file(new_file.filename):
        filename = secure_filename(new_file.filename)
        new_path = os.path.join(UPLOADS_PATH, dateTimeObj.strftime("%d-%b-%Y (%H:%M:%S.%f)")+filename)
        new_file.save(new_path)
    else:
        return render_template("errorpage.html", msg="invalid file name")

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
        os.remove(new_path)
        return render_template("errorpage.html", msg=err.msg)

    #TODO disable the key in memcache
    #invalidateKey(key)  to drop a specific key
    dictToSend = {key: 'key'}
    res = requests.post('http://127.0.0.1:8000/api/dropkey', data=dictToSend)

    dictFromServer = res.json()
    if dictFromServer['success']:
        return redirect(url_for('main'))
    else:
        return redirect(url_for('upload_form'))
