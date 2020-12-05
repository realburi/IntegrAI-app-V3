#-*- coding:utf-8 -*-

from flask import Blueprint, render_template, request, jsonify, send_file, send_from_directory, current_app
from urllib3 import PoolManager
from config import Config_Object
from utils import DB_Handler, Device_Handler, Object_Handler, Value_Handler, ImageBankHandler
from utils import Detector_Handler, Status_Manager, Region_Repairer, Recognizor_Handler
from store_models import DETECT_DICT, RECOGNIZE_DICT
import os

ROUTER = Config_Object['router']
DB_PATH = Config_Object['db_path']
IMG_PATH = Config_Object['img_path']
INFO_PATH = Config_Object['info_path']
IoU_THRESH = Config_Object['iou_thresh']
# templates, static -d react iin js uud orj irne,    UI_PoolManager-> device, AI engine ruu access hiihiin tuld
IMG_Handler = ImageBankHandler(IMG_PATH)
#detect_config, db_handler, img_handler,

UI = Blueprint('UI', __name__, template_folder='./templates', static_folder='./static')
UI_PoolManager = PoolManager()
UI_DBHandler = DB_Handler(os.path.join(DB_PATH, 'master.db'))

UI_DTHandler = DB_Handler(os.path.join(DB_PATH, 'detected.db'))
UI_RNHandler = DB_Handler(os.path.join(DB_PATH, 'recognized.db'))
UI_SManager = Status_Manager(DB_PATH, IMG_PATH, max_db_storage=Config_Object['max_db_storage'], max_img_storage=Config_Object['max_img_storage'])
RR = Region_Repairer(UI_DTHandler, iou_thresh=IoU_THRESH, update_master=True)
REC_Handler = Recognizor_Handler(RECOGNIZE_DICT, rec_handler=UI_RNHandler, dev_handler=None, det_handler=UI_DTHandler, img_handler=IMG_Handler)
DET_Handler = Detector_Handler(DETECT_DICT, det_handler=UI_DTHandler, master_handler=UI_DBHandler, img_handler=IMG_Handler, hooked_taskque=REC_Handler, region_repairer=RR)

UI_DHandler = Device_Handler(IMG_PATH, UI_DBHandler, ROUTER, taskque=DET_Handler)
UI_OHandler = Object_Handler(UI_DBHandler)
UI_VHandler = Value_Handler(UI_RNHandler)
REC_Handler.dev_handler = UI_DHandler

@UI.route('/')
def index():
    return "index.html"#render_template('index.html')


#------Status--------
@UI.route('/status', methods=['GET'])
def status():
    # get status API
    #data = {'memory':50, 'memory_db':10, 'memory_img':60, 'cpu':12, 'gpu':70}
    data = UI_SManager.get_status()
    return jsonify(data)

@UI.route('/status/db/<db_name>', methods=['GET', 'DELETE'])
def db_status(db_name):
    if request.method == 'GET':
        dumped_db = UI_SManager.dump_db(db_name)
        return send_file(dumped_db)
    elif request.method == 'DELETE':
        if 'det' in db_name:
            UI_SManager.empty_db(UI_DTHandler)
        elif 'rec' in db_name:
            UI_SManager.empty_db(UI_RNHandler)
        print("Clear {}".format(db_name))
        return 'OK'

@UI.route('/status/imgs', methods=['GET', 'DELETE'])
def img_status():
    if request.method == 'GET':
        # zip img folder -> React-talaas arga zam oloh!
        zippedfile = UI_SManager.compress_imgs()
        return send_file(zippedfile)
    elif request.method == 'DELETE':
        # empty img folder
        UI_SManager.empty_imgs()
        return 'OK'

@UI.route('/status/upload/master', methods=['POST'])
def upload_master():
    # restore master.db and chmod 644
    data = {'updated':False}
    if len(request.files) > 0:
        master = request.files.to_dict()
        master_content = master['file']
        master_filename = master_content.filename
        # Saved By master.zip
        master_content.save(os.path.join('.', master_filename))
        UI_DBHandler.disconnect()
        data = UI_SManager.upload_master(master_filename)
        UI_DBHandler.reconnect()
    return jsonify(data)

#--------------------

#------devices--------
@UI.route('/devices', methods=['GET', 'POST'])
def devices_function():
    if request.method == 'GET':
        # get all devices
        #datas = [{'deviceID':'161', 'class':1}, {'deviceID':'162', 'class':0}]
        #datas = UI_DBHandler.get('devices', columns=['deviceID', 'class'])
        datas = UI_DHandler.get_devices()
        return jsonify(datas)
    else:
        data = request.json
        data = data['data']
        # save device
        print("deviceID: {} | New Device Registered".format(data['deviceID']))
        devices = UI_DHandler.register_device(data)
        return jsonify(devices)

@UI.route('/devices/<deviceID>', methods=['GET', 'PUT', 'DELETE'])
def device_function(deviceID):
    if request.method == 'GET':
        # get data
        data = UI_DHandler.get_device(deviceID, det_handler=UI_DTHandler)
        return jsonify(data)
    elif request.method == 'PUT':
        data = request.json
        # update device
        print(data)
        res = UI_DHandler.set_device(deviceID, data)
        return jsonify(res)
    elif request.method == 'DELETE':
        # delete device
        res = UI_DHandler.delete_device(deviceID)
        return jsonify(res)

@UI.route('/captures/<deviceID>')
def captures(deviceID):
    # send latest device image
    print("deviceID:{} | GET IMAGE".format(deviceID))
    if deviceID != 'undefined':
        imgfile = IMG_Handler.get_latest(deviceID)#os.path.join(os.path.join(IMG_PATH, deviceID+'.jpg'))
        if imgfile is not None:
            return send_file(imgfile)
    return 'OK'


@UI.route('/capture', methods=['POST'])
def capture():
    data = request.json
    deviceID = data['deviceID']
    # Take Photo
    # Detect
    UI_DHandler.access_device(deviceID)
    data = UI_DHandler.get_device(deviceID, det_handler=UI_DTHandler)
    return jsonify(data)
#--------------------

#------objects--------
@UI.route('/objects', methods=['GET', 'POST'])
def objects_function():
    if request.method == 'GET':
        # get all objects
        #datas = [{'objectID':'1611', 'class':1}, {'objectID':'1621', 'class':0}]
        datas = UI_DBHandler.get('objects', columns=['objectID', 'class', 'name'])
        return jsonify(datas)
    else:
        datas = request.json
        print("POST OBJECT:", datas)
        object_class = datas['class']
        deviceID = datas['deviceID']
        if len(datas["position"]) > 0:
            objectID = UI_OHandler.register_object(object_class, deviceID, datas)
            return objectID
        return "OK"

@UI.route('/objects/recover', methods=['POST'])
def set_object_position():
    data = request.json
    objectID = data['objectID']
    position = data['position']
    res = UI_OHandler.recover_position(objectID, position)
    return jsonify(res)

@UI.route('/objects/recognition', methods=['POST'])
def objects_recognition():
    datas = request.json
    print("POST RECOGNITION:", datas)
    deviceID = datas['deviceID']
    object_class = datas['class']
    res = UI_OHandler.update_objects(object_class, deviceID, datas['position'])
    # TODO: Run recognizor engine
    return jsonify(res)

@UI.route('/objects/<objectID>', methods=['GET', 'PUT', 'DELETE'])
def object_function(objectID):
    if request.method == 'GET':
        data = UI_OHandler.get_object(objectID, UI_DTHandler)
        return jsonify(data)
    elif request.method == 'PUT':
        data = request.json
        # update object
        res = UI_OHandler.set_object(objectID, data)
        return jsonify(res)
    elif request.method == 'DELETE':
        # delete object
        res = UI_OHandler.delete_object(objectID, rec_handler=UI_RNHandler)
        return jsonify(res)

@UI.route('/value', methods=['POST'])
def send_values():
    data = request.json
    print(data)
    objectID = data['objectID']
    date1 = data['date1']
    date2 = data['date2']
    datas = UI_VHandler.get_values(objectID, date1, date2)
    #datas = [{'date':'2020-11-05 23:34:13', 'result':{'value':1234}}, {'date':'2020-11-05 23:35:16', 'result':{'value':1287}}]
    return jsonify(datas)

@UI.route('/value/<valueID>', methods=['PUT', 'DELETE'])
def value_function(valueID):
    if request.method == 'PUT':
        data = request.json
        res = UI_VHandler.set_value(valueID, data)
        return jsonify(res)
    else:
        res = UI_VHandler.delete_value(valueID)
        return jsonify(res)

#--------------------

#------infos---------
@UI.route('/infos/<filename>')
def send_infos(filename):
    filepath = os.path.join(INFO_PATH, filename)
    return send_file(filepath)
#--------------------


#----- Engine -------
