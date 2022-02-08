from flask import Flask
from flask import request, jsonify
from app import webapp

test1 = {'hello':'world'}

@webapp.route('/api/health', methods=['GET'])
def api_health():
    return jsonify(test1)

@webapp.route('/api/upload', methods=['POST'])
def api_upload():
    key = request.form['key'] 
    content = request.form['key']
    print("data", data)
    test2 = {'success': True}
    return jsonify(test2)

@webapp.route('/api/list_key', methods=['POST'])
def api_list_key():
    test2 = {'success': True}
    return jsonify(test2)

@webapp.route('/api/key/<key_value>', methods=['POST'])
def api_search():
    test2 = {'success': False}
    return jsonify(test2)