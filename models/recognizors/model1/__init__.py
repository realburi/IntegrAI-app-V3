#-*- coding:utf-8 -*-

from .model import  Model as OCRmodel
from .tools import input_process, output_process
from .utils import getChar, CTCLabelConverter
from .config import model_cfg
import torch

number = '0123456789'
symbol  = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
en_char = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
voc_txt = model_cfg['voc']

ja_char = getChar(voc_txt)
character = number + symbol + en_char + ja_char
recognizor1_config = {'input_channel': 1, 'output_channel': 512, 'hidden_size': 512, 'num_class':len(character)+1}
converter = CTCLabelConverter(character, {}, {})

recognizor1_config['weight'] = model_cfg['weight']

#imgs -> from a node
def recognizor1_process(imgs, model, device, converter=converter):
    input_tensors = input_process(imgs, device=device, imgH=64)
    outputs = []
    with torch.no_grad():
        for input_tensor in input_tensors:
            temp = model(input_tensor.unsqueeze(0))
            output = temp.clone()
            del temp
            torch.cuda.empty_cache()
            result = output_process(output, converter)[0]
            outputs.append(result)
    return outputs
