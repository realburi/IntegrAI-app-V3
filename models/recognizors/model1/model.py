import torch.nn as nn
from .modules import ResNet_FeatureExtractor, BidirectionalLSTM
import torch

class Model(nn.Module):

    def __init__(self, input_channel, output_channel, hidden_size, num_class, weight=None):
        super(Model, self).__init__()
        """ FeatureExtraction """
        self.FeatureExtraction = ResNet_FeatureExtractor(input_channel, output_channel)
        self.FeatureExtraction_output = output_channel  # int(imgH/16-1) * 512
        self.AdaptiveAvgPool = nn.AdaptiveAvgPool2d((None, 1))  # Transform final (imgH/16-1) -> 1

        """ Sequence modeling"""
        self.SequenceModeling = nn.Sequential(
            BidirectionalLSTM(self.FeatureExtraction_output, hidden_size, hidden_size),
            BidirectionalLSTM(hidden_size, hidden_size, hidden_size))
        self.SequenceModeling_output = hidden_size

        """ Prediction """
        self.Prediction = nn.Linear(self.SequenceModeling_output, num_class)

        if weight is not None:
            self.load(weight)

    def load(self, path, device='cuda'):
        params = torch.load(path, map_location=device)
        new_params = {k.replace("module.", ""):v for k, v in params.items()}
        self.load_state_dict(new_params)


    def forward(self, input):
        """ Feature extraction stage """
        visual_feature = self.FeatureExtraction(input)
        visual_feature = self.AdaptiveAvgPool(visual_feature.permute(0, 3, 1, 2))  # [b, c, h, w] -> [b, w, c, h]
        visual_feature = visual_feature.squeeze(3)

        """ Sequence modeling stage """
        contextual_feature = self.SequenceModeling(visual_feature)

        """ Prediction stage """
        prediction = self.Prediction(contextual_feature.contiguous())

        return prediction
