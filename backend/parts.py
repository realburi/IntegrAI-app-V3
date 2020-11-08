#-*- coding:utf-8 -*-

from utils import DB_Handler, Status_Manager
from config import Config_Object
import os

db_path = Config_Object['db_path']
img_path = Config_Object['img_path']
Master_Handler = DB_Handler(os.path.join(db_path, 'master.db'))
Detecor_Handler = DB_Handler(os.path.join(db_path, 'detected.db'))
Recognizor_Handler = DB_Handler(os.path.join(db_path, 'recognized.db'))

Status_Manager = Status_Manager(db_path, img_path, 128000)

if __name__ == '__main__':
    from pprint import pprint
    devices = Master_Handler.get('devices', {'deviceID':'162'}, columns=['deviceID', 'class'])
    objects = Master_Handler.get('objects')
    status = Status_Manager.get_status()
    pprint(status)

    Master_Handler.disconnect()
    Detecor_Handler.disconnect()
    Recognizor_Handler.disconnect()
