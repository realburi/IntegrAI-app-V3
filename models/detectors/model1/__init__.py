#-*- coding:utf-8 -*-

from .network import CRAFT
from .tools import input_process, output_process
from .config import model_cfg
import torch

detector1_config = model_cfg

def detector1_process(imgs, model, config=detector1_config, device='cuda'):
    canvas_size = config['canvas_size']
    mag_ratio = config['mag_ratio']
    text_threshold = config['text_threshold']
    link_threshold = config['link_threshold']
    low_text = config['low_text']
    input_tensors, ratios, input_sizes = input_process(imgs, canvas_size, mag_ratio, device=device)
    with torch.no_grad():
        if isinstance(input_tensors, list):
            outputs = []
            for input_tensor in input_tensors:
                res, _ = model(input_tensor.unsqueeze(0))
                output = res.cpu()
                torch.cuda.empty_cache()
                del res
                outputs.append(output)
        else:
            res, _ = model(input_tensors.to(device))
            outputs = res.cpu()
            torch.cuda.empty_cache()
            del res
    coordinates = output_process(outputs, ratios, input_sizes, text_threshold, link_threshold, low_text)
    return coordinates
