#-*- coding:utf-8 -*-

from glob import glob
import subprocess
import zipfile
import psutil
import shutil
import io
import os

class Status_Manager(object):
    def __init__(self, db_folder, img_folder, max_db_storage, max_img_storage, unit='MB'):
        self.db_folder = db_folder
        self.img_folder = img_folder
        self.MAX_DB_STORAGE = max_db_storage
        self.MAX_IMG_STORAGE = max_img_storage
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
        return round(total_size, 3)

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
        output['max_db_storage'] = self.MAX_DB_STORAGE
        return output

    def get_img_size(self):
        imgfiles = glob(os.path.join(self.img_folder, '*'))
        output = {}
        total = 0
        for imgfile in imgfiles:
            total += os.path.getsize(imgfile)
        output['total'] = self.culc_unit(total)
        output['n_file'] = len(imgfiles)
        output['max_img_storage'] = self.MAX_IMG_STORAGE
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
        output = {
        'db':db_status,
        'img':img_status,
        'cpu':cpu_usage,
        'gpu':round(float(gpu_usage), 1),
        'memory_unit':self.unit,
        'cpu_temperature':cpu_temperature
        }
        return output

    def upload_master(self, master_file):
        with zipfile.ZipFile(master_file, "r") as zip:
            files = zip.namelist()
            filename = files[0]
            zip.extractall(".")
            os.chmod(filename, 0o644)
            filepath = os.path.join(self.db_folder, filename)
            print(filepath)
            shutil.move(filename, filepath)
            print("Extructed", filename)
        return {'updated':True}

    def dump_db(self, db_name):
        db_file = os.path.join(self.db_folder, db_name)
        filename = db_name + ".zip"
        with zipfile.ZipFile(filename, 'w') as zip:
            zipped_name = db_file.split('/')[-1]
            zip.write(db_file, zipped_name)
        print("DB {} dumped".format(db_name))
        return filename

    def compress_imgs(self):
        """
            not memory file
        """
        imgfiles = glob(os.path.join(self.img_folder, '*'))
        filename = "images.zip"
        print("IMGs:", len(imgfiles))
        with zipfile.ZipFile(filename, 'w') as zip:
            for imgfile in imgfiles:
                zip.write(imgfile)
        print('All files zipped successfully!')
        return filename

    def empty_db(self, handler):
        handler.delete('log', conditions={});

    def empty_imgs(self):
        for filepath in glob(os.path.join(self.img_folder, '*')):
            os.unlink(filepath)
        print("Clear ImageBank")

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

if __name__ == '__main__':
    sm = Status_Manager('../db', './imagebank', 145, 30)
    #sm.compress_imgs()
    res = sm.dump_db('master.db')
    print(res)
