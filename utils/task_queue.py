#-*- coding:utf-8 -*-

from PIL import Image
import numpy as np
import datetime
import queue
import json
import time

class Detector_Handler(object):
    def __init__(self, detect_config, det_handler, master_handler, img_handler, region_repairer=None, hooked_taskque=None, device='cuda'):
        self.detect_config = detect_config
        self.det_handler = det_handler
        self.master_handler = master_handler
        self.img_handler = img_handler
        self.device = device
        self.taskque = queue.Queue()
        self.working = False
        self.region_repairer = region_repairer
        self.finished_tasks = []
        self.hooked_taskque = hooked_taskque
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
        """
            taskque content:
                {'deviceID':deviceID, 'class':device_class}
        """
        self.working = True
        data = self.taskque.get()
        deviceID = data['deviceID']
        device_class = data['class']
        imgfile = self.img_handler.get_latest(deviceID)
        img = np.array(Image.open(imgfile))
        print("deviceID:{} | Detecting".format(deviceID))

        result = {}
        if device_class in self.detect_config:
            output = self.detect_config[device_class]['process']([img], self.detect_config[device_class]['model'], device=self.device)[0] #[img], model, device=self.device
            # output = [[x1, y1, x2, y2, s, l], [x1, y1, x2, y2, s, l], ... ]
            # Region Repairer
            if self.region_repairer is not None:
                output = self.region_repairer(deviceID, output, self.master_handler)
                result = output
                result['timestamp'] = self.get_timestamp()
            else:
                output = self.export_to_json(output)
                result = {'deviceID':deviceID, 'class': 0,'result':output, 'timestamp':self.get_timestamp()}

            #results.append(result)
            self.det_handler.insert('log', result)
            print("deviceID:{} | Detection Result inserted".format(deviceID))

            if self.hooked_taskque is not None:
                self.hooked_taskque.put({'deviceID':deviceID, 'class':output['class']})


        if not self.taskque.empty():
            time.sleep(0.1)
            return self()
        else:
            self.working = False
            return


class Recognizor_Handler(object):
    def __init__(self, recognize_config, rec_handler, det_handler, dev_handler, img_handler, device='cuda'):
        self.recognize_config = recognize_config
        self.rec_handler = rec_handler
        self.dev_handler = dev_handler
        self.det_handler = det_handler
        self.img_handler = img_handler
        self.device = device
        self.taskque = queue.Queue()
        self.working = False
        self.format = "%Y-%m-%d %H:%M:%S"

    def put(self, data:dict): # data = {'deviceID':, 'class':object_class}
        self.taskque.put(data)
        if not self.working:
            self()

    def get_timestamp(self):
        now = datetime.datetime.now()
        now = now.strftime(self.format)
        return now

    def get_valueid(self):
        return ''.join(np.random.choice(list('0123456789')) for _ in range(7))

    def img2regions(self, deviceID, imgfile):
        img = np.array(Image.open(imgfile))
        H, W = img.shape[:2]
        objects = self.dev_handler.get_candidates(deviceID, self.det_handler)
        img_regions, datas = [], []
        for object in objects:
            if object['objectID'] is not None and object['registered']:
                x1, y1 = int(W*object['x1']), int(H*object['y1'])
                x2, y2 = int(W*object['x2']), int(H*object['y2'])
                img_regions.append(img[y1:y2+1, x1:x2+1, :])
                datas.append({'objectID':object['objectID'], 'name':object['name'], 'imgfile':imgfile})
        return img_regions, datas

    def get_code(self):
        # TODO: get related devices groups then generate code
        return

    def __call__(self):
        """
            taskque content:
                {'deviceID':deviceID, 'class':object_class}
        """
        self.working = True
        data = self.taskque.get()
        object_class = data['class']
        deviceID = data['deviceID']
        imgfile = self.img_handler.get_latest(deviceID)

        results = []
        print("deviceID:{} | Recognizing ".format(deviceID))
        if object_class in self.recognize_config and self.dev_handler is not None:
            regions, datas = self.img2regions(deviceID, imgfile)
            outputs = self.recognize_config[object_class]['process'](regions, self.recognize_config[object_class]['model'], device=self.device)
            _imgfile = imgfile.split('/')[-1]
            if object_class == 0: #
                valueID = self.get_valueid()
                code = None
                res = [{"name":d['name'], "value":o} for o, d in zip(outputs, datas)]
                result = {"objectID":datas[0]['objectID'], "class":object_class, "valueID":valueID, "result":json.dumps(res), "imgfile":_imgfile, "code":code, 'timestamp':self.get_timestamp()}
                results.append(result)
            elif object_class is not None:
                for output, data in zip(outputs, datas):
                    valueID = self.get_valueid()
                    code = None
                    result = {"objectID":data['objectID'], "class":object_class, "valueID":valueID, "result":json.dumps({"value": output}), "imgfile":_imgfile, "code":code, 'timestamp':self.get_timestamp()}
                    results.append(result)
            print(results)
            for result in results:
                self.rec_handler.must_insert('log', result)
            print("deviceID:{} | Objects Recognized ".format(deviceID))
        if not self.taskque.empty():
            time.sleep(0.1)
            return self()
        else:
            self.working = False
            return
