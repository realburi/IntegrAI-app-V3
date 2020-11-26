#-*- coding:utf-8 -*-

from .modules import *
import torch.nn.functional as F
import torch.nn as nn
import torch

class Img2Seq_model(nn.Module):
    def __init__(self, voc, maxlen, beam_width=5, device='cpu', gradcam=False):
        super(Img2Seq_model, self).__init__()
        self.voc = voc
        self.char2id = dict(zip(voc, range(len(voc))))
        self.id2char = dict(zip(range(len(voc)), voc))
        self.device = device
        num_classes = len(voc)
        self.gradcam = gradcam
        eos_label = self.char2id['EOS']
        self.encoder = Encoder(ResNet50()).to(device)
        self.decoder = Decoder(num_classes, maxlen=maxlen, eos_label=eos_label, beam_width=beam_width, device=device, gradcam=gradcam)
        self.to(device)

    def forward(self, x, targets):
        encoded = self.encoder(x)
        preds, scores = self.decoder(encoded.contiguous(), targets)
        return preds, scores

    def transfer_learn_mode(self, new_voc, pathes):
        self.load(pathes)
        self.char2id = dict(zip(new_voc, range(len(new_voc))))
        self.decoder.eos = self.char2id['EOS']
        self.decoder.num_classes = len(new_voc)
        self.decoder.embedding = nn.Embedding(len(new_voc)+1, self.decoder.hidden_size).to(self.device)
        self.decoder.output_fc = nn.Linear(self.decoder.hidden_size, len(new_voc)).to(self.device)
        self.encoder.backbone.requires_grad = False
        print("Backbone freezed")

    def load(self, pathes):
        if isinstance(pathes, str):
            self.load_state_dict(torch.load(pathes, map_location=self.device))
        else:
            keys = ['Resnet', 'BiLSTM', 'AttnGRU']
            weight_pathes = {}
            for key in keys:
                for path in pathes:
                    if key in path:
                        weight_pathes[key] = path
            self.encoder.backbone.load_state_dict(torch.load(weight_pathes['Resnet'], map_location=self.device))
            self.encoder.lstm.load_state_dict(torch.load(weight_pathes['BiLSTM'], map_location=self.device))
            self.decoder.load_state_dict(torch.load(weight_pathes['AttnGRU'], map_location=self.device))
