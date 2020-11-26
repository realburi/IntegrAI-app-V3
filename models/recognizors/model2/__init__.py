#-*- coding:utf-8 -*-

from .network import Img2Seq_model
from .config import model_cfg
from .tools import input_process, output_process, get_digits
import torch

recognizor2_config = model_cfg

#imgs -> from a node
def recognizor2_process(imgs, model, device, config=recognizor2_config, voc=get_digits()):
    maxlen = config['maxlen']
    height = config['height']
    input_tensors = input_process(imgs, device=device, imgH=height)
    outputs = []
    with torch.no_grad():
        target_tensors = torch.IntTensor(1, maxlen).fill_(1).to(device)
        for input_tensor in input_tensors:
            output, s = model(input_tensor.unsqueeze(0), target_tensors)
            outputs.append(output.cpu().numpy())
    values = output_process(outputs, voc=voc)
    return values
