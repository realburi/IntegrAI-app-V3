#-*- coding:utf-8 -*-
#
# How to add new DL model:
# 1. make new director 'detector2' or 'recognition2'
# 2. add files (network.py, config.py, __init__.py ...)
# 3. __init__.py have to include detector2_process, detector2_model, detector2_config
# 4. add "from .model2 import detector2_process, detector2_model, detector2_config " /detector/__init__.py

from config import Config_Object
from models import *

device = 'cuda'

detector1 = CRAFT(device=device).eval()
detector1.load(detector1_config['weights'])
print("Detector1 OK!")

recognizor1 = recognizor1_model()
print("Recognizor1 OK!")

recognizor2 = Img2Seq_model(voc=get_digits(), maxlen=recognizor2_config['maxlen'], device=device).eval()
recognizor2.load(recognizor2_config['weights'])
print("recognizor2 OK!")

detect_dict = {
    0:{'model':detector1, 'process':detector1_process}
}

recogize_dict = {
    0:{'model':recognizor1, 'process':recognizor1_process},
    1:{'model':recognizor2, 'process':recognizor2_process}
}

if __name__ == '__main__':
   print("Running on:", device)
