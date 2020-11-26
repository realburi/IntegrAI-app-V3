#-*- coding:utf-8 -*-

from torchvision import transforms as T
from PIL import Image
import numpy as np
import string
import torch
import cv2

def get_digits(EOS='EOS', PADDING='PADDING', UNKNOWN='UNKNOWN', additionals=['-', '+', r'\n']):
    voc = list(string.printable[:10])
    for add in additionals:
        voc.append(add)
    voc.append(EOS)
    voc.append(PADDING)
    voc.append(UNKNOWN)
    return voc

def input_process(imgs, imgH=32, device='cpu'):
    input_tensors = []
    for img in imgs:
        img = Image.fromarray(img, mode='RGB')
        w, h = img.size
        ratio = w / float(h)
        imgW = int(np.floor(ratio * imgH))
        input_img = img.resize((imgW, imgH), Image.BILINEAR)
        input_tensor = T.ToTensor()(input_img)
        input_tensor.sub_(0.5).div_(0.5)
        input_tensors.append(input_tensor.to(device))
    return input_tensors

def output_process(outputs, voc):
    char2id = dict(zip(voc, range(len(voc))))
    id2char = dict(zip(range(len(voc)), voc))
    eos_label = char2id['EOS']
    unknown_label = char2id['UNKNOWN']
    num_classes = len(char2id)
    labels = []
    for output in outputs: # output [1, 10]
        length = output.shape[0]
        label_lengths = output.shape[1]
        _labels = []
        for i in range(length):
            _chars = []
            for j in range(label_lengths):
                if output[i, j] != eos_label:
                    if output[i, j] != unknown_label:
                       _chars.append(id2char[output[i, j]])
                else:
                    break
            label = ''.join(_chars)
            _labels.append(label)
        labels.append(_labels[0])
    return labels

if __name__ == '__main__':
    imgs = [np.random.rand(224, 224, 3) for i in range(2)]
    input_tensors = input_process(imgs)
    print(input_tensors[0].shape)
