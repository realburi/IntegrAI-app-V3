#-*- coding:utf-8 -*-

from glob import glob
import zipfile
import time
import os

class ImageBankHandler(object):
    def __init__(self, folder_path, max_storage=1000):
        self.folder_path = folder_path
        self.max_storage = max_storage

    def get_all(self, deviceID:str):
        # return img pathes
        return glob(os.path.join(self.folder_path, deviceID+'*'))

    def get_latest(self, deviceID:str):
        device_imgfiles = self.get_all(deviceID)
        if len(device_imgfiles) > 0:
            latest_file = max(device_imgfiles, key=os.path.getctime)
            return latest_file
        else:
            return None

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
