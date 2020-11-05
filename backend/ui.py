#-*- coding:utf-8 -*-

from flask import Blueprint, render_template, request, jsonify, send_file
from urllib3 import PoolManager
from api import *
import os

# templates, static -d react iin js uud orj irne,    UI_PoolManager-> device, AI engine ruu access hiihiin tuld
UI = Blueprint('UI', __name__, template_folder='./templates', static_folder='./static')
UI_PoolManager = PoolManager()

@UI.route('/')
def index():
    return "index.html"#render_template('index.html')


#------status--------
@UI.route('/status', methods=['GET'])
def status():
    # get status API
    data = {'memory':50, 'memory_db':10, 'memory_img':60, 'cpu':12, 'gpu':70}
    return jsonify(data)

@UI.route('/status/db', methods=['POST', 'DELETE'])
def db_status():
    if request.method == 'POST':
        # dump DB
        db_file = ''
        return send_file(db_file)
    elif request.method == 'DELETE':
        # empty db
        return 'OK'

@UI.route('/status/img', methods=['POST', 'DELETE'])
def img_status():
    if request.method == 'POST':
        # zip img folder
        db_file = ''
        return send_file(db_file)
    elif request.method == 'DELETE':
        # empty img folder
        return 'OK'
#--------------------

#------devices--------
@UI.route('/devices', methods=['GET', 'POST'])
def devices_function():
    if request.method == 'GET':
        # get all devices
        datas = [{'deviceID':'161', 'class':1}, {'deviceID':'162', 'class':0}]
        return jsonify(datas)
    else:
        data = request.json
        # save device
        return 'OK'

@UI.route('/devices/<deviceID>', methods=['GET', 'PUT', 'DELETE'])
def device_function(deviceID):
    if request.method == 'GET':
        # get data
        data = {'deviceID':'161', 'class':1}
        return jsonify(data)
    elif request == 'PUT':
        data = request.json
        # update device
        return 'OK'
    elif request == 'DELETE':
        # delete device
        return 'OK'

@UI.route('/capture/<deviceID>')
def capture():
    # send latest device image
    imgfile = ''
    return send_file(imgfile)

#--------------------

#------objects--------
@UI.route('/objects', methods=['GET', 'POST'])
def objects_function():
    if request.method == 'GET':
        # get all objects
        datas = [{'objectID':'1611', 'class':1}, {'objectID':'1621', 'class':0}]
        return jsonify(datas)
    else:
        data = request.json
        # save object
        return 'OK'

@UI.route('/objects/<objectID>', methods=['GET', 'PUT', 'DELETE'])
def object_function(objectID):
    if request.method == 'GET':
        # get data
        data = {'objectID':'1611', 'class':1}
        return jsonify(data)
    elif request == 'PUT':
        data = request.json
        # update object
        return 'OK'
    elif request == 'DELETE':
        # delete object
        return 'OK'

@UI.route('/value', methods=['POST'])
def send_values():
    data = request.json
    objectID = data['objectID']
    date1 = data['date1']
    date2 = data['date2']
    datas = [{'date':'2020-11-05 23:34:13', 'result':{'value':1234}}, {'date':'2020-11-05 23:35:16', 'result':{'value':1287}}]
    return jsonify(datas)

#--------------------

#------infos---------
@UI.route('/infos')
def send_infos():
    filename = ''
    return send_file(filename)

#--------------------
