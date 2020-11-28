Config_Object = {
    'router':'192.168.1.',
    'db_path':'/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/db',
    'img_path':'/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/backend/imagebank',
    'class':[0, 1],
    'iou_thresh':0.1,
    'max_storage':145, #MB
    'detector':{
        0:'CRAFT', # device class: detector name
        1:None,
    },
    'recognizor':{
        0:'NoneType', # paper
        1:'Img2Seq_model', # digital meter
    }
}
