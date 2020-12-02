#-*- coding:utf-8 -*-

from .db_handler import DB_Handler
from glob import glob
import threading
import requests
import time
import json
import os

class Device_Handler(object):
    def __init__(self, img_folder, handler, router, taskque=None):
        self.img_folder = img_folder
        self.handler = handler
        self.router = router
        self.connectors = {}
        self.threads = {}
        self.taskque = taskque
        self.stop_all_threads = False
        self.load_connectors()

    def load_connectors(self):
        datas = self.handler.get('devices')
        for data in datas:
            deviceID = data['deviceID']
            period = data['device_content']['frequency'] if 'frequency' in data['device_content'] else 0
            related_devices = data['device_content']['related_devices'] if 'related_devices' in data['device_content'] else []
            self.connectors[deviceID] = Device_Connector(deviceID, data['class'], data['url'], self.img_folder, period, related_devices)
            self.run_device_thread(deviceID, data['class'], data['url'])

    def convert(self, data:dict):
        #url = self.router + data['deviceID']
        data['url'] = 'http://' + data['deviceID'] + '.local' + '/capture'
        return data

    def get_devices(self):
        devices = self.handler.get('devices', columns=['deviceID', 'class'])
        datas = []
        for device in devices:
            n_obj = self.handler.count('objects', {'deviceID':device['deviceID']})[0][0]
            device['num_objects'] = n_obj
        return devices

    def get_device(self, deviceID:str, det_handler:DB_Handler=None):
        data = self.handler.get('devices', {'deviceID':deviceID})
        if len(data) == 1:
            data = data[0]
            if det_handler is not None:
                candidates = self.get_candidates(deviceID, det_handler=det_handler)
                data['positions'] = candidates
            else:
                objects = self.get_objects(deviceID, det_handler=det_handler)
                data['positions'] = objects
        return data

    def register_device(self, data:dict):
        """
            INPUT:
                data: {"deviceID":deviceID, "device_content":{"frequency":--, "quality":--, "related_devices":--}}

            OUTPUT:
                [
                    {"deviceID":deviceID, "class":device_class}, ...
                ]
        """
        data = self.convert(data)
        deviceID = data['deviceID']
        devices = self.handler.get('devices', columns=['deviceID'])
        if deviceID not in devices:
            device_content = data['device_content'] if 'device_content' in data else {'frequency':0, 'quality':640, 'related_devices':[]}
            data['device_content'] = json.dumps(device_content)
            self.handler.add('devices', 'deviceID', [data])
            # ADD self.connectors[deviceID]
            period = device_content['frequency'] if 'frequency' in device_content else 0
            related_devices = device_content['related_devices'] if 'related_devices' in device_content else []
            self.connectors[deviceID] = Device_Connector(deviceID, data['class'], data['url'], self.img_folder, period, related_devices)
            self.run_device_thread(deviceID, data['class'], data['url'])
        return self.handler.get('devices', columns=['deviceID', 'class'])

    def set_device(self, deviceID:str, data:dict):
        """
            INPUT:
                data: {"device_content":{"frequency": ---, "quality":---, "related_devices":[deviceID1, deviceID2, ... ]}}
        """
        _data = data.copy()
        _data['deviceID'] = deviceID
        _data['device_content'] = json.dumps(data['device_content'])
        self.update_related_devices(deviceID, data['device_content']['related_devices'])
        self.handler.add('devices', 'deviceID', [_data])
        # SET self.connectors
        period = data['device_content']['frequency'] if 'frequency' in data['device_content'] else 0
        related_devices = data['device_content']['related_devices'] if 'related_devices' in data['device_content'] else []
        #refresh connectors
        self.connectors[deviceID].period = period
        self.connectors[deviceID].related_devices = related_devices

    def update_related_devices(self, deviceID, new_related_devices):
        """
            INPUT:
                deviceID:deviceID
                new_related_devices:[deviceID1, deviceID2, ...]
        """
        current_device_content = self.handler.get('devices', conditions={'deviceID':deviceID}, columns=['device_content'])[0]
        current_related_devices = current_device_content['device_content']['related_devices']
        current_period = current_device_content['device_content']['frequency']

        adding_related_devices = [devID for devID in new_related_devices if devID not in current_related_devices]
        ejecting_related_devices = [devID for devID in current_related_devices if devID not in new_related_devices]
        # 1. add this deviceID -> new related_devices' device_content
        updating_datas = []
        adding_related_devices_content = [self.handler.get('devices', conditions={'deviceID':devID}, columns=['device_content']) for devID in adding_related_devices]
        for devID, device_content in zip(adding_related_devices, adding_related_devices_content):
            content = device_content[0]['device_content']
        # 2. set frequency -> 0 ( frequency==this deviceID's frequency)
            content['frequency'] = 0
            if deviceID not in content['related_devices']:
               content['related_devices'].append(deviceID)
            updating_datas.append({'deviceID':devID, 'device_content':json.dumps(content)})

        # 3. eject this deviceID -> ejecting related_devices
        ejecting_related_devices_content = [self.handler.get('devices', conditions={'deviceID':devID}, columns=['device_content']) for devID in ejecting_related_devices]
        for devID, device_content in zip(ejecting_related_devices, ejecting_related_devices_content):
             content = device_content[0]['device_content']
             if deviceID in content['related_devices']:
                 content['related_devices'].remove(deviceID)
             updating_datas.append({'deviceID':devID, 'device_content':json.dumps(content)})
        self.handler.add('devices', 'deviceID', updating_datas)
        print("deviceID:{} | SET Related Devices: ADD:{}, EJECT:{}".format(deviceID, str(adding_related_devices), str(ejecting_related_devices)))


    def delete_device(self, deviceID:str):
        # 1. clear all related_devices
        self.update_related_devices(deviceID, [])
        # 2. delete devices
        self.handler.delete('devices', {'deviceID':deviceID})
        del self.connectors[deviceID]
        del self.threads[deviceID]
        # DELETE self.connectors[deviceID]

    def count_content_objects(self, candidates:list):
        return len([c for c in candidates if c['registered']])

    def get_candidates(self, deviceID:str, det_handler:DB_Handler):
        sql = "SELECT class, result FROM log WHERE id=(SELECT MAX(id) FROM log WHERE deviceID='{0}') AND deviceID='{0}';".format(deviceID)
        results = det_handler.run_custom_sql(sql)
        register_objectIDs = [o['objectID'] for o in self.handler.get('objects', {'deviceID':deviceID})]
        datas = []
        if len(results) > 0:
            object_class, result = results[0]
            result = json.loads(result)
            for object in result:
                if object['objectID'] in register_objectIDs or object['objectID'] is None:
                    datas.append({
                        'objectID':object['objectID'],
                        'name':object['name'],
                        'class':object_class,
                        'x1':object['x1'],
                        'y1':object['y1'],
                        'x2':object['x2'],
                        'y2':object['y2'],
                        'registered':object['registered'],
                    })
        return datas


    def get_objects(self, deviceID:str, handler:DB_Handler=None):
        objects = self.handler.get('objects', {'deviceID':deviceID})
        datas = []
        if len(objects) == 0:
            return datas
        for obj in objects:
                objectID = obj['objectID']
                name = obj['name']
                object_class = obj['class']
                if isinstance(obj['position'], dict):
                    datas.append({
                        'objectID':objectID,
                        'name':name,
                        'class':object_class,
                        'x1':obj['position']['x1'],
                        'y1':obj['position']['y1'],
                        'x2':obj['position']['x2'],
                        'y2':obj['position']['y2'],
                        'registered':True,
                    })
                elif isinstance(obj['position'], list):
                    for position in obj['position']:
                        datas.append({
                            'objectID':objectID,
                            'name':position['name'],
                            'class':object_class,
                            'x1':position['x1'],
                            'y1':position['y1'],
                            'x2':position['x2'],
                            'y2':position['y2'],
                            'registered':True,
                        })
        return datas

    def access_device(self, deviceID:str):
        deviceID = str(deviceID)
        if str(deviceID) in self.connectors:
            print("OK!")
            self.connectors[deviceID].process()
            print("OK! HOOK")
            self.detector_hook(deviceID, self.connectors[deviceID].device_class)

    def detector_hook(self, deviceID:str, device_class:int):
        #engine hook
        print("deviceID:{} | HOOKED!".format(deviceID))
        if self.taskque is not None:
            data = {'deviceID':deviceID, 'class':device_class}
            self.taskque.put(data)
            #self.celery.deley(data)

    def device_thread(self, connector):
        while True:
            if connector.period > 0 and int(connector.device_class) == 0:
                connector.process()
                self.detector_hook(connector.deviceID, connector.device_class)
                time.sleep(connector.period)
            else:
                break
            if self.stop_all_threads:
                break

    def run_device_thread(self, deviceID:str, device_class:int, url:str):
        self.stop_all_threads = False
        if deviceID in self.connectors:
            self.threads[deviceID] = threading.Thread(name=deviceID, target=self.device_thread, args=(self.connectors[deviceID], ))
            self.threads[deviceID].start()

    def stop_threads(self):
        self.stop_all_threads = True

class Device_Connector(object):
    def __init__(self, deviceID:str, device_class:int, url:str, imgfolder:str, period:int, related_devices:list = [], timeout=1., debug=True):
        self.deviceID = deviceID
        self.device_class = device_class
        self.period = period
        self.related_devices = related_devices
        self.active = False
        self.imgfolder = imgfolder
        self.imgpath = os.path.join(imgfolder, deviceID+'.jpg')
        self.url = url if 'http' in url else 'http://' + url + '/capture'
        self.timeout = timeout
        self.debug = debug

    def save_content(self, content):
        t = time.localtime()
        timestamp = time.strftime('%Y-%m-%d_%H-%M-%S', t)
        imgpath = os.path.join(self.imgfolder, self.deviceID+"_"+timestamp+".jpg")
        img_handler = open(imgpath, 'wb')
        img_handler.write(content)
        img_handler.close()

    def access(self):
        if self.debug:
            print("ACCESS TO {}".format(self.deviceID))
            self.url = 'http://localhost:5001/capture/'+str(self.deviceID)
        if int(self.device_class) == 0:  # class = 1 is button device
            print("URL:", self.url)
            try:
                r = requests.get(self.url, timeout=self.timeout)
                if r.status_code == 200:
                    self.save_content(r.content)
                    self.active = True
                elif r.status_code != 200:
                    self.active = False
            except requests.exceptions.ConnectionError as e:
                print("CANNOT CONNECTED:", deviceID)
                self.active = False

    def access_related_devices(self):
        for related in self.related_devices:
            related.access()

    def process(self):
        self.access()
        self.access_related_devices()

if __name__ == '__main__':
    from pprint import pprint
    db_handler = DB_Handler('../db/master.db')
    dh = Device_Handler('./imagebank', db_handler, '192.169.1.0')
    new_data = {'device_content':{"frequency":0, "quality":0, "related_devices":['162', '163']}}
    #new_data = {'device_content':{"frequency":0, "quality":0, "related_devices":[]}}
    dh.set_device('161', new_data)
    db_handler.disconnect()
