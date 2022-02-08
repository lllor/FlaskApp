
from flask import Flask

webapp = Flask(__name__)

from app import imagesearch
from app import imagekey
from app import fileupload
from app import memcacheconfig
from app import memcachestatistic
from app import testapi

from app import main

