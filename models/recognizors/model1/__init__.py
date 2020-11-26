#-*- coding:utf-8 -*-

from PIL import Image
import pyocr
import pyocr.builders
recognizor1_config = {'lang':'jpn', 'layout':6}

def recognizor1_model():
    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("recognizer1 is not Available!")
        return
    else:
        return tools[0]

def recognizor1_process(imgs, model, config=recognizor1_config, device='cpu'):
    results = []
    for img in imgs:
        if type(img).__name__ == 'ndarray':
            img = Image.fromarray(img)
        txt = model.image_to_string(img, lang=config['lang'], builder=pyocr.builders.TextBuilder(tesseract_layout=config['layout']))
        results.append(txt)
    return results
