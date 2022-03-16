import random

from flask import render_template, url_for, request, g
from app import webapp, memcache, cache, totalRequest, totalMiss
from flask import json
from sys import getsizeof

from app.LRUCache import LRUCache
from threading import Timer
import mysql.connector
from app.config import db_config

import boto3
import socket
from botocore.exceptions import ClientError
from datetime import date
from datetime import datetime, timedelta

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
    for k in memcache.keys():
        size += getsizeof(k)
    for k in memcache.values():
        size += getsizeof(k)

    return size


# 5秒钟更新计时器
def ptimer(n):
    global x
    # print("total:", cnt2)
    # print("miss:", misscnt)
    # print("x is", x)
    totalRequest[x % 7] = cnt  # 目前设定为查看过去30s的统计数据 30/5+1
    totalMiss[x % 7] = miss
    x = x + 1

    ctx = webapp.app_context()
    ctx.push()
    cnx = get_db()

    cursor = cnx.cursor()

    query = "update statistics set request_num=%s, miss_num=%s, hit_num=%s, hit_rate=%s, miss_rate=%s," \
            "item_num=%s, item_size=%s limit 1;"
    # stat表字段还未写全

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


@webapp.route('/get', methods=['POST'])
def get():
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
    key = request.form.get('key')
    if rows[0][0] == '1':
        print("LRU")
        obj.getLRU(key)
    if rows[0][0] == '0':
        print("random")

    if key in memcache:
        value = memcache[key]
        size = getsizeof(memcache)
        ans = []
        ans.append(value)
        ans.append(size)
        response = webapp.response_class(
            response=json.dumps(ans),
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

    key = request.form.get('key')
    value = request.form.get('value')
    # print(getsizeof(key))
    # print(getsizeof(value))

    if rows[0][0] == '0':
        print("random")
        if key not in memcache:
            while cal() + getsizeof(key) + getsizeof(value) > int(rows[0][1]):
                randomReplace()
        else:
            for key0 in memcache:
                if key0 == key:
                    curSize = getsizeof(memcache[key0])
            while cal() + getsizeof(value) - curSize > int(rows[0][1]):
                randomReplace()
    if rows[0][0] == '1':
        print("LRU")
    obj.put(key, value)
    memcache[key] = value
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


@webapp.route('/invalidate', methods=['POST'])
def invalidate():
    key = request.form.get('key')
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


@webapp.route('/config', methods=['POST'])
def refreshConfiguration():
    cnx = get_db()
    cursor = cnx.cursor()
    policy = 0
    capacity = 300
    # query = "INSERT INTO `statistics ` (`total`, `miss`) VALUES (%s,%s);"
    query = "update config set policy=%s, capacity=%s limit 1;"
    # stat表字段还未写全
    cursor.execute(query, (policy, capacity))
    cnx.commit()
    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )
    return response


# 查看size
@webapp.route('/mem', methods=['POST'])
def mem():
    # size = getsizeof(memcache)
    size = 0
    for k in memcache.keys():
        size += getsizeof(k)
    for k in memcache.values():
        size += getsizeof(k)
    response = webapp.response_class(
        response=json.dumps(size),
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


# @webapp.route('/cache', methods=['POST'])
def showCache():
    print("cache:", cache)
    print("memcache:", memcache)


'''
@webapp.route('/stat', methods=['POST'])
def stat():
    global x
    print("here x ", x)
    length = len(totalRequest)
    print("len", length)
    print("start", totalMiss.get(0))
    print(totalMiss.get(length - 1))
    if int(totalRequest.get(length - 1)) == 0:
        hitRate = 0
    elif length <= 7:
        hitRate = 1 - (int(totalMiss.get(length - 1)) / int(totalRequest.get(length - 1)))
    elif length > 7:
        hitRate = 1 - (int(totalMiss.get(x % 7)) - int(totalMiss.get(x % 7)) + 1) / (
                int(totalRequest.get(x % 7)) - int(totalRequest.get(x % 7)) + 1)
    tmp = []
    tmp.append(totalRequest)
    tmp.append(hitRate)
    response = webapp.response_class(
        response=json.dumps(tmp),
        status=200,
        mimetype='application/json'
    )

    return response
'''


@webapp.route('/stat', methods=['GET'])
def stat():
    tmp = []
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    print("host",hostname)
    ins_list = ec2.describe_instances()
    id_list=[]
    id = '0'
    for item in ins_list['Reservations']:
        if item['Instances'][0]["State"]['Name'] == 'running':
            print("ip: ",item['Instances'][0]['PrivateIpAddress'])
            id_list.append(item['Instances'][0]['InstanceId'])

    for ins in id_list:
        current_time = datetime.utcnow()
        req = cloudwatch.get_metric_statistics(
            Namespace='request',
            MetricName='req',
            Dimensions=[{
                'Name': 'instance-id',
                'Value': ins
            },
            ],
            StartTime=current_time - timedelta(seconds=120),
            EndTime=current_time,
            Period=60,
            Statistics=['Maximum','Minimum']
        )
        miss0 = cloudwatch.get_metric_statistics(
            Namespace='miss',
            MetricName='mis',
            Dimensions=[{
                'Name': 'instance-id',
                'Value': ins
            },
            ],
            StartTime=current_time - timedelta(seconds=120),
            EndTime=current_time,
            Period=60,
            Statistics=['Maximum','Minimum']
        )
        hit = cloudwatch.get_metric_statistics(
            Namespace='hit',
            MetricName='hit',
            Dimensions=[{
                'Name': 'instance-id',
                'Value': ins
            },
            ],
            StartTime=current_time - timedelta(seconds=120),
            EndTime=current_time,
            Period=60,
            Statistics=['Maximum','Minimum']
        )
        size = cloudwatch.get_metric_statistics(
            Namespace='size',
            MetricName='size',
            Dimensions=[{
                'Name': 'instance-id',
                'Value': ins
            },
            ],
            StartTime=current_time - timedelta(seconds=120),
            EndTime=current_time,
            Period=60,
            Statistics=['Maximum']
        )
        cache0 = cloudwatch.get_metric_statistics(
            Namespace='cache',
            MetricName='cache',
            Dimensions=[{
                'Name': 'instance-id',
                'Value': ins
            },
            ],
            StartTime=current_time - timedelta(seconds=120),
            EndTime=current_time,
            Period=60,
            Statistics=['Maximum']
        )


        tmp.append(ins)
        tmp.append(req['Datapoints'])
        tmp.append(miss0['Datapoints'])
        tmp.append(hit['Datapoints'])
        tmp.append(size['Datapoints'])
        tmp.append(cache0['Datapoints'])

        print(ins,": req miss  cache")
        for item in req['Datapoints']:
            # print(item['Timestamp'])
            print("req", item['Maximum']-item['Minimum'], item['Timestamp'])
        for item in miss0['Datapoints']:
            print("miss", item['Maximum']-item['Minimum'], item['Timestamp'])
        for item in hit['Datapoints']:
            print("miss", item['Maximum'] - item['Minimum'], item['Timestamp'])
        for item in cache0['Datapoints']:
            print("cache", item['Maximum'], item['Timestamp'])

        noreq = 0
        for item in req["Datapoints"]:
            if item['Maximum'] - item['Minimum'] == 0:
                print("9999", item['Maximum'], item['Minimum'])
                noreq = 1
        if noreq == 1:
            print("11111")
            cloudwatch.put_metric_data(
                Namespace="missrate",
                MetricData=[
                    {
                        'MetricName': 'mr',

                        'Value': 0,
                        'Dimensions': [
                            {
                                'Name': 'instance-id',
                                'Value': ins
                            },
                        ]
                    },
                ])
            cloudwatch.put_metric_data(
                Namespace="hitrate",
                MetricData=[
                    {
                        'MetricName': 'hr',

                        'Value': 0,
                        'Dimensions': [
                            {
                                'Name': 'instance-id',
                                'Value': ins
                            },
                        ]
                    },
                ])
            print(ins,"hr:0")
            print(ins,"mr:0")
        else:
            print("22222")
            reqNum = 1
            missNum = 0
            hitNum=0
            for item in req['Datapoints']:
                reqNum = item['Maximum'] - item['Minimum']
                print("req", item['Maximum'], item['Minimum'])
            for item in miss0['Datapoints']:
                missNum = item['Maximum'] - item['Minimum']
                print("missNum", item['Maximum'], item['Minimum'])
            hitNum = reqNum - missNum
            cloudwatch.put_metric_data(
                Namespace="missrate",
                MetricData=[
                    {
                        'MetricName': 'mr',

                        'Value': missNum / reqNum,
                        'Dimensions': [
                            {
                                'Name': 'instance-id',
                                'Value': ins
                            },
                        ]
                    },
                ])
            cloudwatch.put_metric_data(
                Namespace="hitrate",
                MetricData=[
                    {
                        'MetricName': 'hr',

                        'Value': hitNum / reqNum,
                        'Dimensions': [
                            {
                                'Name': 'instance-id',
                                'Value': ins
                            },
                        ]
                    },
                ])
            print(ins, "mr:",missNum / reqNum)
            print(ins, "hr:",hitNum / reqNum)
    # print(req['Datapoints']['Maximum'],miss0['Datapoints']['Maximum'],hit['Datapoints']['Maximum'],size['Datapoints']['Maximum'],
    # cache0['Datapoints']['Maximum'])

    response = webapp.response_class(
        response=json.dumps(tmp),
        status=200,
        mimetype='application/json'
    )

    return response


def put_metric(x):
    hostname = socket.gethostname()
    ins_list = ec2.describe_instances()
    id="0"
    ip_address = socket.gethostbyname(hostname)
    for item in ins_list['Reservations']:
        if item['Instances'][0]["State"]['Name']=='running':
            if item['Instances'][0]['PrivateIpAddress']==ip_address:
                id=item['Instances'][0]['InstanceId']

    length = len(totalRequest)
    item_size = cal()
    item_num = len(memcache)
    cloudwatch.put_metric_data(
        Namespace="request",
        MetricData=[
            {
                'MetricName': 'req',
                'Value': int(totalRequest.get(length - 1)),
                'Dimensions': [
                    {
                        'Name': 'instance-id',
                        'Value': id
                    },

                ]
            },
        ])
    cloudwatch.put_metric_data(
        Namespace="miss",
        MetricData=[
            {
                'MetricName': 'mis',
                'Value': int(totalMiss.get(length - 1)),
                'Dimensions': [
                    {
                        'Name': 'instance-id',
                        'Value': id
                    },
                ]
            },
        ])
    cloudwatch.put_metric_data(
        Namespace="hit",
        MetricData=[
            {
                'MetricName': 'hit',
                'Value': int(totalRequest.get(length - 1)) - int(totalMiss.get(length - 1)),
                'Dimensions': [
                    {
                        'Name': 'instance-id',
                        'Value': id
                    },
                ]
            },
        ])

    cloudwatch.put_metric_data(
        Namespace="size",
        MetricData=[
            {
                'MetricName': 'size',
                'Value': item_size,
                'Dimensions': [
                    {
                        'Name': 'instance-id',
                        'Value': id
                    },
                ]
            },
        ])
    cloudwatch.put_metric_data(
        Namespace="cache",
        MetricData=[
            {
                'MetricName': 'cache',
                'Value': item_num,
                'Dimensions': [
                    {
                        'Name': 'instance-id',
                        'Value': id
                    },
                ]
            },
        ])



def cal_rate():
    hostname = socket.gethostname()
    ins_list = ec2.describe_instances()
    id='0'
    for item in ins_list['Reservations']:
        if item['Instances'][0]['PrivateIpAddress'] == hostname:
            id = item['Instances'][0]['InstanceId']
    current_time = datetime.utcnow()
    req = cloudwatch.get_metric_statistics(
        Namespace='request',
        MetricName='req',
        Dimensions=[{
            'Name': 'instance-id',
            'Value': 'i-003929876cb9e189b'
        },
        ],
        StartTime=current_time - timedelta(seconds=60),
        EndTime=current_time,
        Period=60,
        Statistics=['Maximum', 'Minimum']
    )
    miss0 = cloudwatch.get_metric_statistics(
        Namespace='miss',
        MetricName='mis',
        Dimensions=[{
            'Name': 'instance-id',
            'Value': 'i-003929876cb9e189b'
        },
        ],
        StartTime=current_time - timedelta(seconds=60),
        EndTime=current_time,
        Period=60,
        Statistics=['Maximum', 'Minimum']
    )
    hit = cloudwatch.get_metric_statistics(
        Namespace='hit',
        MetricName='hit',
        Dimensions=[{
            'Name': 'instance-id',
            'Value': 'i-003929876cb9e189b'
        },
        ],
        StartTime=current_time - timedelta(seconds=60),
        EndTime=current_time,
        Period=60,
        Statistics=['Maximum', 'Minimum']
    )
    noreq = 0
    for item in req["Datapoints"]:
        if item['Maximum'] - item['Minimum'] == 0:
            noreq = 1
    if noreq == 1:
        cloudwatch.put_metric_data(
            Namespace="missrate",
            MetricData=[
                {
                    'MetricName': 'mr',
                    'Value': 0,
                    'Dimensions': [
                        {
                            'Name': 'instance-id',
                            'Value': id
                        },
                    ]
                },
            ])
        cloudwatch.put_metric_data(
            Namespace="hitrate",
            MetricData=[
                {
                    'MetricName': 'hr',
                    'Value': 0,
                    'Dimensions': [
                        {
                            'Name': 'instance-id',
                            'Value': id
                        },
                    ]
                },
            ])
    else:
        reqNum = 1
        missNum = 0
        for item in req['Datapoints']:
            reqNum = item['Maximum'] - item['Minimum']
        for item in miss0['Datapoints']:
            missNum = item['Maximum'] - item['Minimum']
        hitNum = reqNum - missNum
        cloudwatch.put_metric_data(
            Namespace="missrate",
            MetricData=[
                {
                    'MetricName': 'mr',

                    'Value': missNum / reqNum,
                    'Dimensions': [
                        {
                            'Name': 'instance-id',
                            'Value': id
                        },
                    ]
                },
            ])
        cloudwatch.put_metric_data(
            Namespace="hitrate",
            MetricData=[
                {
                    'MetricName': 'hr',

                    'Value': hitNum / reqNum,
                    'Dimensions': [
                        {
                            'Name': 'instance-id',
                            'Value': id
                        },
                    ]
                },
            ])


def ptimer_new(n):
    global x
    # print("total:", cnt2)
    # print("miss:", misscnt)
    # print("x is", x)
    totalRequest[x] = cnt  # 目前设定为查看过去30s的统计数据 30/5+1
    totalMiss[x] = miss
    # if x % 11 == 0:
    # cal_rate()
    x = x + 1

    put_metric(x)

    t = Timer(n, ptimer_new, (n,))
    t.start()


def rateStat():
    length = len(totalRequest)
    print("x and len", x, length)
    print("ttrq", totalRequest)
    if int(totalRequest.get(length - 1)) == 0:
        hitRate = 0
        missRate = 0
        totalCnt = 0
        missCnt = 0
        hitCnt = totalCnt - missCnt
    elif x <= 7:
        hitRate = 1 - (int(totalMiss.get(length - 1)) / int(totalRequest.get(length - 1)))
        missRate = 1 - hitRate
        totalCnt = int(totalRequest.get(length - 1))
        missCnt = int(totalMiss.get(length - 1))
        hitCnt = totalCnt - missCnt
    elif x > 7:
        if x % 7 - 1 < 0:
            idx = 6
        else:
            idx = x % 7 - 1
        totalCnt = int(totalRequest.get(idx)) - int(totalRequest.get(x % 7))
        if totalCnt == 0:
            hitRate = 0
            missRate = 0
            missCnt = 0
            hitCnt = 0
        else:
            hitRate = 1 - (int(totalMiss.get(idx)) - int(totalMiss.get(x % 7))) / (
                    int(totalRequest.get(idx)) - int(totalRequest.get(x % 7)))
            missRate = 1 - hitRate
            missCnt = int(totalMiss.get(idx)) - int(totalMiss.get(x % 7))
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

session = boto3.Session(aws_access_key_id='AKIARS5QSRZ3ZHBZ2M6K',
                                aws_secret_access_key='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',
                                region_name='us-east-1')
ec2 = session.client('ec2')
ec2_resource = session.resource('ec2')
cloudwatch = session.client('cloudwatch')
totalRequest[0] = 0
totalMiss[0] = 0
ptimer_new(5)
# ptimer(5)
