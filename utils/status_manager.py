#-*- coding:utf-8 -*-

from glob import glob
import subprocess
import zipfile
import psutil
import io
import os

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
