Config_Object = {
    'router':'192.168.1.',
    'db_path':'/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/db',
    'img_path':'/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/backend/imagebank',
    'class':[0, 1],
    'iou_thresh':0.2,
    'max_db_storage':50, #MB
    'max_img_storage':32, #GB
    'detector':{    # device class: detector name
        0:'CRAFT',
        1:None,
    },
    'recognizor':{ # object class: object name
        0:'NoneType', # paper
        1:'Img2Seq_model', # digital meter
    }
}
