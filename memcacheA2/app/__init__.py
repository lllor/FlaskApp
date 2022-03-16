from flask import Flask

# from app import LRUCache

global memcache
global cache
global cnt1
global totalRequest
global totalMiss

webapp = Flask(__name__)
memcache = {}
cache = {}
cnt1=1
totalRequest={}
totalMiss={}
from app import main
