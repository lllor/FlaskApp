import random

from flask import render_template, url_for, request, g
from app import webapp, memcache, cache, totalRequest, totalMiss
from flask import json
from sys import getsizeof
from flask import jsonify

from app.LRUCache import LRUCache
from threading import Timer
import mysql.connector
from app.config import db_config
import base64

obj = LRUCache(300)

cnt = 0
miss = 0
x = 0


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


@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# 计算size
def cal():
    size = 0
    # for k in memcache.keys():
    # size += getsizeof(k)
    for k in memcache.values():
        pic = base64.b64decode(k)
        size += getsizeof(pic) / 1024 / 1024

    return size


# 5秒钟更新计时器
def ptimer(n):
    global x
    # print("total:", cnt2)
    # print("miss:", misscnt)
    # print("x is", x)
    totalRequest[x % 121] = cnt  # 目前设定为查看过去30s的统计数据 30/5+1
    totalMiss[x % 121] = miss
    x = x + 1
    ctx = webapp.app_context()
    ctx.push()
    cnx = get_db()

    cursor = cnx.cursor()

    query = "update statistics set request_num=%s, miss_num=%s, hit_num=%s, hit_rate=%s, miss_rate=%s," \
            "item_num=%s, item_size=%s limit 1;"
    # stat表字段还未写全

    print("inside")

    item_size = cal()
    item_num = len(memcache)
    hitRate, missRate, totalCnt, hitCnt, missCnt = rateStat()
    cursor.execute(query, (totalCnt, missCnt, hitCnt, hitRate, missRate, item_num, item_size))
    cnx.commit()
    ctx.pop()

    t = Timer(n, ptimer, (n,))
    t.start()


@webapp.route('/')
def main():
    return render_template("main.html")


@webapp.route('/get/<key>', methods=['GET'])
def get(key):
    cnx = get_db()

    cursor = cnx.cursor()

    query = "select * from config;"

    cursor.execute(query)
    rows = cursor.fetchall()
    print(rows[0])
    cnx.commit()
    obj.setCapacity(int(rows[0][1]))
    if rows[0][0] == '0':
        while int(rows[0][1]) < cal():
            randomReplace()

    elif rows[0][0] == '1':

        while int(rows[0][1]) < cal():
            obj.deleteNode()

    global cnt, miss
    print("cache:", cache)
    print("memcache:", memcache)
    cnt += 1
    print("key:", key)
    # key = request.form.get('key')
    if rows[0][0] == '1':
        print("LRU")
        obj.getLRU(key)
    if rows[0][0] == '0':
        print("random")

    if key in memcache:
        value = memcache[key]
        response = webapp.response_class(
            response=json.dumps({'content': value}),
            status=200,
            mimetype='application/json'
        )
    else:
        miss += 1
        response = webapp.response_class(
            response=json.dumps("Unknown key"),
            status=400,
            mimetype='application/json'
        )

    return response


@webapp.route('/put', methods=['POST'])
def put():
    cnx = get_db()

    cursor = cnx.cursor()

    query = "select * from config;"

    cursor.execute(query)
    rows = cursor.fetchall()
    # print(rows[0])
    cnx.commit()
    obj.setCapacity(int(rows[0][1]))
    if rows[0][0] == '0':
        while int(rows[0][1]) < cal():
            randomReplace()

    elif rows[0][0] == '1':
        while int(rows[0][1]) < cal():
            obj.deleteNode()

    key = request.json['key']
    value = request.json['content']
    # print("============================data:",key)
    # print("============================data:",value)
    print("type of value", type(value))
    # print(getsizeof(key))
    # print(getsizeof(value))

    if rows[0][0] == '0':
        print("random")
        pic = base64.b64decode(value)
        if key not in memcache:
            while cal() + getsizeof(pic) / 1024 / 1024 > int(rows[0][1]):
                randomReplace()
        else:
            for key0 in memcache:
                if key0 == key:
                    curSize = getsizeof(memcache[key0]) / 1024 / 1024
            while cal() + getsizeof(pic) / 1024 / 1024 - curSize > int(rows[0][1]):
                randomReplace()
    if rows[0][0] == '1':
        print("LRU")
    obj.put(key, value)
    memcache[key] = value
    # print("latest", cal())
    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )

    return response


@webapp.route('/clear', methods=['POST'])
def clear():
    obj.clear()
    memcache.clear()
    cache.clear()

    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )

    return response


@webapp.route('/invalidate/<key>', methods=['POST'])
def invalidate(key):
    # key = request.form.get('key')
    print("key: ", key)
    if key in memcache:
        obj.findNode(key)
        memcache.pop(key)
        cache.pop(key)
        response = webapp.response_class(
            response=json.dumps("OK"),
            status=200,
            mimetype='application/json'
        )

    else:
        response = webapp.response_class(
            response=json.dumps("not found"),
            status=400,
            mimetype='application/json'
        )
    return response


@webapp.route('/config/<policy>/<capacity>', methods=['POST'])
def refreshConfiguration(policy=3, capacity=-1):
    cnx = get_db()
    cursor = cnx.cursor()
    policy = int(policy)
    capacity = int(capacity)
    if policy == 3 and capacity == -1:
        query = "select * from statistics;"
        cursor.execute(query)
        row = cursor.fetchone()
        request_num = row[0]
        hit_num = row[4]
        miss_num = row[3]
        hit_rate = row[6]
        miss_rate = row[5]
        item_num = row[2]
        item_size = row[1]
        response = webapp.response_class(
            response=json.dumps({'request_num': request_num, 'item_size': item_size, 'item_num': item_num,
                                 'miss_num': miss_num, 'hit_num': hit_num, 'miss_rate': miss_rate,
                                 'hit_rate': hit_rate}),
            status=200,
            mimetype='application/json'
        )
    else:
        # cnx = get_db()
        # cursor = cnx.cursor()
        # policy = 0
        # capacity = 300

        query = "update config set policy=%s, capacity=%s limit 1;"

        cursor.execute(query, (policy, capacity))
        cnx.commit()

        obj.setCapacity(int(capacity))
        if policy == '0':
            while int(capacity) < cal():
                randomReplace()

        elif policy == '1':
            while int(capacity) < cal():
                obj.deleteNode()

        response = webapp.response_class(
            response=json.dumps("ok"),
            status=200,
            mimetype='application/json'
        )

    return response


def randomReplace():
    rep = random.sample(memcache.keys(), 1)
    print(rep)
    obj.findNode(rep[0])
    memcache.pop(rep[0])
    cache.pop(rep[0])


def rateStat():
    length = len(totalRequest)
    print("x and len", x, length)
    # print("ttrq", totalRequest)
    if int(totalRequest.get(length - 1)) == 0:
        hitRate = 0
        missRate = 0
        totalCnt = 0
        missCnt = 0
        hitCnt = totalCnt - missCnt
    elif x <= 121:
        hitRate = 1 - (int(totalMiss.get(length - 1)) / int(totalRequest.get(length - 1)))
        missRate = 1 - hitRate
        totalCnt = int(totalRequest.get(length - 1))
        missCnt = int(totalMiss.get(length - 1))
        hitCnt = totalCnt - missCnt
    elif x > 121:
        if x % 121 - 1 < 0:
            idx = 6
        else:
            idx = x % 121 - 1
        totalCnt = int(totalRequest.get(idx)) - int(totalRequest.get(x % 121))
        if totalCnt == 0:
            hitRate = 0
            missRate = 0
            missCnt = 0
            hitCnt = 0
        else:
            hitRate = 1 - (int(totalMiss.get(idx)) - int(totalMiss.get(x % 121))) / (
                    int(totalRequest.get(idx)) - int(totalRequest.get(x % 121)))
            missRate = 1 - hitRate
            missCnt = int(totalMiss.get(idx)) - int(totalMiss.get(x % 121))
            hitCnt = totalCnt - missCnt
    else:
        hitRate = 0
        missRate = 1 - hitRate
        totalCnt = 0
        missCnt = 0
        hitCnt = totalCnt - missCnt
    # missRate = 1 - hitRate
    # hitCnt = totalCnt - missCnt
    print("stat, hitRate, missRate, totalCnt, hitCnt, missCnt", hitRate, missRate, totalCnt, hitCnt, missCnt)
    return hitRate, missRate, totalCnt, hitCnt, missCnt


@webapp.route('/changeSize', methods=['GET'])
def changeSize():
    cnx = get_db()

    cursor = cnx.cursor()

    query = "select * from config;"

    cursor.execute(query)
    rows = cursor.fetchall()
    print(rows[0])
    cnx.commit()
    obj.setCapacity(int(rows[0][1]))
    if rows[0][0] == '0':
        while int(rows[0][1]) < cal():
            randomReplace()

    elif rows[0][0] == '1':

        while int(rows[0][1]) < cal():
            obj.deleteNode()

    response = webapp.response_class(
        response=json.dumps("ok"),
        status=200,
        mimetype='application/json'
    )

    return response


ptimer(5)
