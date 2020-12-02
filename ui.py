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
IoU_THRESH = Config_Object['iou_thresh']
# templates, static -d react iin js uud orj irne,    UI_PoolManager-> device, AI engine ruu access hiihiin tuld
IMG_Handler = ImageBankHandler(IMG_PATH)
#detect_config, db_handler, img_handler,

UI = Blueprint('UI', __name__, template_folder='./templates', static_folder='./static')
UI_PoolManager = PoolManager()
UI_DBHandler = DB_Handler(os.path.join(DB_PATH, 'master.db'))

UI_DTHandler = DB_Handler(os.path.join(DB_PATH, 'detected.db'))
UI_RNHandler = DB_Handler(os.path.join(DB_PATH, 'recognized.db'))
UI_SManager = Status_Manager(DB_PATH, IMG_PATH, 128000)
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
    print("OK!")
    return jsonify(data)

@UI.route('/status/db/<filename>', methods=['GET', 'POST', 'DELETE'])
def db_status(filename):
    if request.method == 'POST' or request.method == 'GET':
        # dump? DB
        db_file = filename
        db_path = os.path.join(DB_PATH, db_file)
        return send_file(db_path)
    elif request.method == 'DELETE':
        # empty db
        return 'OK'

@UI.route('/status/imgs', methods=['GET', 'POST', 'DELETE'])
def img_status():
    if request.method == 'POST' or request.method == 'GET':
        # zip img folder -> React-talaas arga zam oloh!
        compressed_imgs = UI_SManager.compress_imgs()
        return send_file(compressed_imgs, attachment_filename='images.zip', as_attachment=True)
    elif request.method == 'DELETE':
        # empty img folder
        return 'OK'

@UI.route('/status/upload/master', methods=['POST'])
def upload_master():
    # restore master.db and chmod 644
    return 'OK'

@UI.route('/status/upload/recognition', methods=['POST'])
def upload_recognition():
    # restore recognized.db and chmod 644
    return 'Ok'
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
    elif request == 'PUT':
        data = request.json
        # update device
        UI_DHandler.set_device(data)
        return 'OK'
    elif request == 'DELETE':
        # delete device
        UI_DHandler.delete_device(deviceID)
        return 'OK'

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
            UI_OHandler.register_object(object_class, deviceID, datas)
        # save object -> objectID:None -> have to register
        #objects = UI_DBHandler.get('objects', {'deviceID':deviceID})
        return 'OK'

@UI.route('/objects/recognition', methods=['POST'])
def objects_recognition():
    datas = request.json
    print("POST RECOGNITION:", datas)
    deviceID = datas['deviceID']
    object_class = datas['class']
    UI_OHandler.update_objects(object_class, deviceID, datas['position'])
    # TODO: Run recognizor engine
    return 'OK'

@UI.route('/objects/<objectID>', methods=['GET', 'PUT', 'DELETE'])
def object_function(objectID):
    if request.method == 'GET':
        # get data
        #data = {'objectID':'1611', 'class':1}
        #data = UI_DBHandler.get('objects', {'objectID':objectID})
        #data = data[0] if len(data) > 0 else []
        data = UI_OHandler.get_object(objectID, UI_DTHandler)
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
    print(data)
    objectID = data['objectID']
    date1 = data['date1']
    date2 = data['date2']
    datas = UI_VHandler.get_values(objectID, date1, date2)

    #datas = [{'date':'2020-11-05 23:34:13', 'result':{'value':1234}}, {'date':'2020-11-05 23:35:16', 'result':{'value':1287}}]
    return jsonify(datas)

#--------------------

#------infos---------
@UI.route('/infos')
def send_infos():
    filename = ''
    return send_file(filename)
#--------------------


#----- Engine -------
