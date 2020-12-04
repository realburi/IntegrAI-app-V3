#-*- coding:utf-8 -*-

from torchvision import transforms as T
from PIL import Image
import numpy as np
import torch

def input_process(imgs, imgH=64, device='cpu'):
    input_tensors = []
    for img in imgs:
        img = Image.fromarray(img, mode='RGB').convert('L')
        w, h = img.size
        ratio = w / float(h)
        imgW = int(np.floor(ratio * imgH))
        input_img = img.resize((imgW, imgH), Image.BILINEAR)
        input_tensor = T.ToTensor()(input_img)
        input_tensor.sub_(0.5).div_(0.5)
        input_tensors.append(input_tensor.to(device))
    return input_tensors

def output_process(preds, converter, device='cpu', ignore_idx=[]):
    preds_prob = torch.softmax(preds, dim=2)
    preds_prob = preds_prob.cpu().detach().numpy()
    preds_prob[:,:,ignore_idx] = 0.
    pred_norm = preds_prob.sum(axis=2)
    preds_prob = preds_prob/np.expand_dims(pred_norm, axis=-1)
    preds_prob = torch.from_numpy(preds_prob).float().to(device)

    preds_size = torch.IntTensor([preds.size(1)] * 1)
    k = preds_prob.cpu().detach().numpy()
    preds_str = converter.decode_beamsearch(k, beamWidth=5)
    return preds_str
