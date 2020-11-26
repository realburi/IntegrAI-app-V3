#-*- coding:utf-8 -*-

from glob import glob
import subprocess
import threading
import requests
import zipfile
import sqlite3
import psutil
import time
import json
import io
import os


#----- DB Handler Object -------
class DB_Handler(object):
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        #self.cursor = self.conn.cursor()

    def session(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def commit(self, sql):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        cursor.execute(sql)
        self.conn.commit()
        cursor.close()
        return 'Ok'

    def select(self, table_name:str, conditions:dict, columns:list = []):
        selected = "*" if len(columns) == 0 else ",".join(columns)
        sql = "SELECT " + selected + " FROM {} ".format(table_name)
        if len(conditions) > 0:
            sql += "WHERE"
        for column, value in conditions.items():
            sql += " " + str(column) + "=" + "{},".format(value)
        sql = sql[:-1] + ";"
        return self.session(sql)

    def count(self, table_name:str, conditions:dict):
        sql = "SELECT COUNT(*) FROM {} ".format(table_name)
        if len(conditions) > 0:
            sql += "WHERE"
        for column, value in conditions.items():
            sql += " " + str(column) + "=" + "{},".format(value)
        sql = sql[:-1] + ";"
        return self.session(sql)

    def insert(self, table_name:str, data:dict):
        sql = "INSERT INTO " + str(table_name) + " "
        arguments, contents = "", ""
        for column, value in data.items():
            arguments += str(column)+", "
            contents += "'{}', ".format(value)
        sql += "(" + arguments[:-2] + ")" + " VALUES " + "(" + contents[:-2] + ");"
        return self.commit(sql)

    def update(self, table_name:str, data:dict, conditions:dict):
        sql += "UPDATE " + str(table_name) + " SET"
        for column, value in data.items():
            sql += " " + str(column) + "=" + "'{}', ".format(value)
        sql = sql[:-1] + " "
        if len(conditions) > 0:
            sql += " WHERE "
        for column, value in conditions.items():
            sql += " " + str(column) + "=" + "'{}', ".format(value)
        sql = sql[:-1] + ";"
        return self.commit(sql)

    def delete(self, table_name:str, conditions:dict):
        sql = "DELETE FROM " + str(table_name) + " WHERE"
        for i, column in enumerate(conditions):
            if i > 0:
                sql += " AND "
            sql += " " + str(column) + "=" + "'{} '".format(conditions[column])
        sql = sql[:-1] + ";"
        return self.commit(sql)

    def add(self, table_name:str, key:str, datas:list):
        output = {'inserted':0, 'updated':0}
        for data in datas:
            KEY = data[key]
            count = int(self.count(table_name), {key:KEY}[0][0])
            if count == 0:
                self.insert(table_name, data)
                output['inserted'] += 1
            else:
                self.update(table_name, data, {key:KEY})
                output['updated'] += 1
        return output

    def columns(self, table_name:str):
        sql = "PRAGMA table_info({});".format(table_name)
        return [infos[1] for infos in self.session(sql)]

    def get(self, table_name:str, conditions:dict = {}, columns:list = []):
        rows = self.select(table_name, conditions, columns)
        cols = self.columns(table_name) if len(columns) == 0 else columns
        datas = []
        for row in rows:
            data = self.load_json({col:val for col, val in zip(cols, row)})
            datas.append(data)
        return datas

    def load_json(self, data):
        _data = {}
        for k, v in data.items():
            _data[k] = json.loads(v) if not isinstance(v, int) and not isinstance(v, float) and v is not None and '{' in v and '}' in v else v
        return _data

    def disconnect(self):
        #self.cursor.close()
        self.conn.close()

#----- Status Manager Object -------
class Status_Manager(object):
    def __init__(self, db_folder, img_folder, max_storage, unit='MB'):
        self.db_folder = db_folder
        self.img_folder = img_folder
        self.MAX_STORAGE = max_storage
        self.unit = unit

    def culc_unit(self, size):
        if self.unit == 'MB' or self.unit == 'mb':
            scale = 10**6
        elif self.unit == 'GB' or self.unit == 'GB':
            scale = 10**9
        else:
            scale = 1
        return round(size / scale, 3)

    def get_folder_size(self, start_path = '.'):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def get_db_size(self):
        db_files = glob(os.path.join(self.db_folder, '*'))
        output = {}
        total = 0
        for db_file in db_files:
            _db_file = db_file.split('/')[-1].replace(".db", "")
            size = os.path.getsize(db_file)
            output[_db_file] = {'size':self.culc_unit(size)}
            total += size
        output['total'] = self.culc_unit(total)
        return output

    def get_img_size(self):
        imgfiles = glob(os.path.join(self.img_folder, '*'))
        output = {}
        total = 0
        for imgfile in imgfiles:
            total += os.path.getsize(imgfile)
        output['total'] = self.culc_unit(total)
        output['n_file'] = len(imgfiles)
        return output

    def get_cpu_temperature(self):
        statuses = psutil.sensors_temperatures()
        temperatures = [s.current for s in statuses['coretemp']]
        if len(temperatures) == 0:
            return 0
        return round(sum(temperatures) / len(temperatures), 2)

    def get_status(self):
        db_status = self.get_db_size()
        img_status = self.get_img_size()
        cpu_usage = psutil.cpu_percent()
        gpu_usage = self.get_gpu_info()
        cpu_temperature = self.get_cpu_temperature()
        output = {'db':db_status, 'img':img_status, 'cpu':cpu_usage, 'gpu':round(float(gpu_usage), 1), 'memory_unit':self.unit, 'cpu_temperature':cpu_temperature}
        return output

    def upload_db(self, filename):
        os.chmod(filename, 0o644)
        return

    def compress_imgs(self):
        imgfiles = glob(os.path.join(self.img_folder, '*'))
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for filename in imgfiles:
                file_handler = open(filename, 'rb')
                content = file_handler.read()
                file_handler.close()
                _filename = filename.split('/')[-1]
                data = zipfile.ZipInfo(_filename)
                data.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(data, content)
        memory_file.seek(0)
        return memory_file

    def empty_db(self):
        pass

    def empty_imgs(self):
        pass

    # not for Jetson NANO
    def get_gpu_info(self, nvidia_smi_path='nvidia-smi', keys=['utilization.gpu'], no_units=True):
        nu_opt = '' if not no_units else ',nounits'
        cmd = '%s --query-gpu=%s --format=csv,noheader%s' % (nvidia_smi_path, ','.join(keys), nu_opt)
        output = subprocess.check_output(cmd, shell=True)
        lines = output.decode().split('\n')
        lines = [ line.strip() for line in lines if line.strip() != '' ]
        output = [ { k: v for k, v in zip(keys, line.split(', ')) } for line in lines ]
        output = output[0][keys[0]]
        return output

#----- Device Controller Object -------
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
            related_devcies = data['device_content']['related_devcies'] if 'related_devcies' in data['device_content'] else []
            self.connectors[deviceID] = Device_Connector(deviceID, data['class'], data['url'], self.img_folder, period, related_devcies)
            self.run_device_thread(deviceID, data['class'], data['url'])

    def convert(self, data:dict):
        #url = self.router + data['deviceID']
        data['url'] = 'http://' + data['deviceID'] + '.local' + '/capture'
        return data

    def get_device(self, deviceID:str, master:bool=True, handler:DB_Handler=None):
        data = self.handler.get('devices', {'deviceID':deviceID})
        if len(data) == 1:
            data = data[0]
            data['positions'] = self.get_objects(deviceID, master=master, handler=handler)
        return data

    def register_device(self, data:dict):
        data = self.convert(data)
        deviceID = data['deviceID']
        self.handler.add('devices', 'deviceID', data)
        # ADD self.connectors[deviceID]
        period = data['device_content']['frequency'] if 'frequency' in data['device_content'] else 0
        related_devcies = data['device_content']['related_devcies'] if 'related_devcies' in data['device_content'] else []
        self.connectors[deviceID] = Device_Connector(deviceID, data['class'], data['url'], self.img_folder, period, related_devcies)
        self.run_device_thread(deviceID, data['class'], data['url'])

    def set_device(self, data:dict):
        data = self.convert(data)
        self.handler.add('devices', 'deviceID', data)
        # SET self.connectors
        period = data['device_content']['frequency'] if 'frequency' in data['device_content'] else 0
        related_devcies = data['device_content']['related_devcies'] if 'related_devcies' in data['device_content'] else []
        self.connector[deviceID].period = period
        self.connector[deviceID].related_devcies = related_devcies

    def delete_device(self, deviceID:str):
        self.handler.delete('devices', {'deviceID':deviceID})
        del self.connectors[deviceID]
        del self.threads[deviceID]
        # DELETE self.connectors[deviceID]

    def get_objects(self, deviceID:str, master:bool=True, handler:DB_Handler=None):
        objects = self.handler.get('objects', {'deviceID':deviceID})
        datas = []
        if master:
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
                        'y2':obj['position']['y2']
                    })
                elif isinstance(obj['position'], list):
                    for position in obj['position']:
                        datas.append({
                            'objectID':objectID,
                            'name':name,
                            'class':object_class,
                            'x1':position['x1'],
                            'y1':position['y1'],
                            'x2':position['x2'],
                            'y2':position['y2']
                        })
        else:
            #TODO: get latest regions and match them
            regions = []
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
        print("HOOKED!")
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
    def __init__(self, deviceID:str, device_class:int, url:str, imgfolder:str, period:int, related_devcies:list = [], timeout=1., debug=True):
        self.deviceID = deviceID
        self.device_class = device_class
        self.period = period
        self.related_devcies = related_devcies
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
            self.url = 'http://localhost:5432/'+str(self.deviceID)
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
                self.active = False

    def access_related_devices(self):
        for related in self.related_devcies:
            related.access()

    def process(self):
        self.access()
        self.access_related_devices()


#----- ImageBankd Handler Object -------
class ImageBankHandler(object):
    def __init__(self, folder_path, max_storage=1000):
        self.folder_path = folder_path
        self.max_storage = max_storage

    def get_all(self, deviceID:str):
        # return img pathes
        return glob(os.path.join(self.folder_path, deviceID+'*'))

    def get_latest(self, deviceID:str):
        device_imgfiles = self.get_all(deviceID)
        latest_file = max(device_imgfiles, key=os.path.getctime)
        return latest_file

    def check(self):
        files = glob(os.path.join(self.folder_path, '*'))
        if len(files) > self.max_storage:
            pass

    def clean(self):
        # TODO: Clean Image bank
        pass

    def upload(self):
        #TODO: Zip? and upload images
        return NotImplementedError


if __name__ == '__main__':
    from pprint import pprint
    dh = Device_Handler('./imagebank', DB_Handler('../db/master.db'), '')
    data = dh.get_device('162')
    #ih = ImageBankHandler('/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/backend/imagebank')
    #data = ih.get_latest('161')
    pprint(data)
