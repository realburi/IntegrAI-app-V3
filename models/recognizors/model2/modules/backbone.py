#-*- coding:utf-8 -*-

import torch.nn.functional as F
import torch.nn as nn
import torch


def conv3x3(in_planes, out_planes, stride=1):
  return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                   padding=1, bias=False)


def conv1x1(in_planes, out_planes, stride=1):
  return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class ResidualBlock(nn.Module):
   def __init__(self, inplanes, planes, stride=1, downsample=None):
     super(ResidualBlock, self).__init__()
     self.conv1 = conv1x1(inplanes, planes, stride)
     self.bn1 = nn.BatchNorm2d(planes)
     self.relu = nn.ReLU(inplace=True)
     self.conv2 = conv3x3(planes, planes)
     self.bn2 = nn.BatchNorm2d(planes)
     self.downsample = downsample
     self.stride = stride

   def forward(self, x):
     residual = x
     out = self.conv1(x)
     out = self.bn1(out)
     out = self.relu(out)
     out = self.conv2(out)
     out = self.bn2(out)

     if self.downsample is not None:
       residual = self.downsample(x)
     out += residual
     out = self.relu(out)
     return out


class ResNet50(nn.Module):
  def __init__(self):
    super(ResNet50, self).__init__()

    in_channels = 3
    self.inplanes = 32
    self.layer0 = nn.Sequential(
        nn.Conv2d(in_channels, self.inplanes, kernel_size=(3, 3), stride=1, padding=1, bias=False),
        nn.BatchNorm2d(self.inplanes),
        nn.ReLU(inplace=True))

    self.layer1 = self._make_layer(self.inplanes,  3, [2, 2])
    self.layer2 = self._make_layer(64,  4, [2, 2])
    self.layer3 = self._make_layer(128, 6, [2, 1])
    self.layer4 = self._make_layer(256, 6, [2, 1])
    self.layer5 = self._make_layer(512, 3, [2, 1])
    self.out_planes = 512

  def _make_layer(self, planes, blocks, stride):
    downsample = None
    if stride != [1, 1] or self.inplanes != planes:
      downsample = nn.Sequential(
          conv1x1(self.inplanes, planes, stride),
          nn.BatchNorm2d(planes))

    layers = []
    layers.append(ResidualBlock(self.inplanes, planes, stride, downsample))
    self.inplanes = planes
    for _ in range(1, blocks):
      layers.append(ResidualBlock(self.inplanes, planes))
    return nn.Sequential(*layers)

  def forward(self, x, gradcam=False):
      assert x.shape[2] == 32
      x = self.layer0(x)
      x = self.layer1(x)
      x = self.layer2(x)
      x = self.layer3(x)
      x = self.layer4(x)
      x = self.layer5(x)
      if gradcam == True:
           feats = x
      if gradcam == True:
          return x, feats
      return x


if __name__ == '__main__':
    backbone = ResNet50()
    backbone.load_state_dict(torch.load('../weights/Resnet50_pretrained_SVT.pth'))
    x = torch.rand(2, 3, 32, 128)
    o = backbone(x)
    print(o.shape)
