#-*- coding:utf-8 -*-

from PIL import Image
import numpy as np
import datetime
import queue
import json
import time

class Detector_Handler(object):
    def __init__(self, detect_config, db_handler, img_handler, device='cuda'):
        self.detect_config = detect_config
        self.db_handler = db_handler
        self.img_handler = img_handler
        self.device = device
        self.taskque = queue.Queue()
        self.working = False
        self.format = "%Y-%m-%d %H:%M:%S"

    def put(self, data:dict):
        self.taskque.put(data)
        if not self.working:
            self()

    def export_to_json(self, output):
        output = [{'x1':round(o[0], 3), 'y1':round(o[1], 3), 'x2':round(o[2], 3), 'y2':round(o[3], 3)} for o in output[0]]
        return json.dumps(output)

    def get_timestamp(self):
        now = datetime.datetime.now()
        now = now.strftime(self.format)
        return now

    def __call__(self):
        self.working = True
        data = self.taskque.get()
        deviceID = data['deviceID']
        device_class = data['class']
        imgfile = self.img_handler.get_latest(deviceID)
        img = np.array(Image.open(imgfile))

        result = {}
        if device_class in self.detect_config:
            output = self.detect_config[device_class]['process']([img], self.detect_config[device_class]['model'], device=self.device) #[img], model, device=self.device
            # result = [[x1, y1, x2, y2, s, l], [x1, y1, x2, y2, s, l], ... ]
            output = self.export_to_json(output)
            result = {'deviceID':deviceID, 'class': 0,'result':output, 'timestamp':self.get_timestamp()}
            print(result)
            #results.append(result)
            self.db_handler.insert('log', result)
        if not self.taskque.empty():
            time.sleep(0.1)
            return self()
        else:
            self.working = False
            return


class Recognizor_Handler(object):
    def __init__(self, recognize_config, db_handler, img_handler, device='cuda'):
        self.recognize_config = recognize_config
        self.db_handler = db_handler
        self.img_handler = img_handler
        self.device = device
        self.taskque = queue.Queue()
        self.working = False
        self.format = "%Y-%m-%d %H:%M:%S"

    def put(self, data:dict): # data = {'deviceID':, 'class':object_class, 'position':}
        self.taskque.put(data)
        if not self.working:
            self()

    def export_to_json(self, output):
        output = [{'x1':round(o[0], 3), 'y1':round(o[1], 3), 'x2':round(o[2], 3), 'y2':round(o[3], 3)} for o in output]
        return json.dumps(output)

    def get_timestamp(self):
        now = datetime.datetime.now()
        now = now.strftime(self.format)
        return now

    def __call__(self):
        print(self.taskque)
        self.working = True
        data = self.taskque.get()
        objectID = data['objectID']
        object_class = data['class']
        deviceID = data['deviceID']
        position
        imgfile = self.img_handler.get_latest(deviceID)
        img = np.array(Image.open(imgfile))


        results = []
        if device_class in self.recognize_config:
            output = self.detect_config[device_class]['process']([img], self.detect_config['model'], device=self.divice) #[img], model, device=self.device
            # result = [[x1, y1, x2, y2, s, l], [x1, y1, x2, y2, s, l], ... ]
            output = self.export_to_json(output)
            result = {'objectID':objectID, 'class': object_class,'result':output, 'timestamp':self.get_timestamp()}
            results.append(result)

            print("R:", results)
            self.db_handler.insert('log', results)
        if not self.taskque.empty():
            time.sleep(0.1)
            return self()
        else:
            self.working = False
            return
