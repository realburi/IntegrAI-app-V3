#-*- coding:utf-8 -*-

from numba import jit
from pprint import pprint
import numpy as np
import json

@jit
def culc_iou(box1, box2):
    """
        - box:array([x1, y1, x2, y2])
    """
    xx1 = np.maximum(box1[0], box2[0])
    yy1 = np.maximum(box1[1], box2[1])
    xx2 = np.minimum(box1[2], box2[2])
    yy2 = np.minimum(box1[3], box2[3])
    w, h = np.maximum(xx2-xx1, 0), np.maximum(yy2-yy1, 0)
    m = (box1[2]-box1[0])*(box1[3]-box1[1]) + (box2[2]-box2[0])*(box2[3]-box2[1]) - w*h + 1e-8
    return w*h / m

class Region_Repairer(object):
    """
        main_handler: DET_Handler
        iou_thresh: overlapped threshold
    """
    def __init__(self, main_handler, iou_thresh=0.1, update_master=True):
        self.handler = main_handler
        self.iou_thresh = iou_thresh
        self.update_master = update_master

    def transform_positions(self, master, result):
        """
            only for object_class==0
            master: [X, Y]
            result: [[x1, y1, x2, y2, ...], [x1, y1, x2, y2, ...], ...]
        """
        X, Y = master
        distances = [r[0]**2 + r[1]**2 for r in result]
        index = np.argmin(distances)
        left_topX = result[index][0]
        left_topY = result[index][1]
        transformed = [[r[0]-left_topX+X, r[1]-left_topY+Y, r[2]-left_topX+X, r[3]-left_topY+Y] for r in result]
        return transformed

    def get_positions(self, object_class, objects):
        if len(objects) == 0:
            return []
        if object_class == 0: # Paper
            return [[o['x1'], o['y1'], o['x2'], o['y2']] for o in objects[0]['position']]
        else: # Meters...
            return [[o['position']['x1'], o['position']['y1'], o['position']['x2'], o['position']['y2']] for o in objects]

    def get_candidates(self, deviceID, result, master_handler):
        """
            INPUT:
                deviceID:deviceID
                result:[[x1, y1, x2, y2, score, label], [x1, y1, x2, y2, score, label], ... ]
                master_db: master DB_Handler

            OUTPUT:
                output = ([
                        {'x1':new_x1, 'y1':new_y1, 'x2':new_x2, 'y2':new_y2, 'registered':True, 'name':name, 'objectID':objectID},
                        {'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2, 'registered':True, 'name':name, 'objectID':objectID},
                        {'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2, 'registered':False, 'name':None, 'objectID':None}...
                        ], object_class)
        """
        print("deviceID:{} | Region Repairer ".format(deviceID))
        candidates = []
        registered_objects = master_handler.get('objects', {'deviceID':deviceID})
        device = master_handler.get('devices', {'deviceID':deviceID})[0]
        # TODO: if no objects registered
        object_class = device['object_class']
        registered_objects_position = self.get_positions(object_class, registered_objects)
        independent_indexes = []

        transformed_result = []
        if object_class == 0 and len(registered_objects) > 0:
            distances = [r[0]**2 + r[1]**2 for r in registered_objects_position]
            index = np.argmin(distances)
            X = registered_objects_position[index][0]
            Y = registered_objects_position[index][1]
            transformed_result = self.transform_positions((X, Y), result)

        if len(registered_objects) == 0:
            independent_indexes = [i for i, r in enumerate(result)]

        for i, rpos in enumerate(registered_objects_position):
            objectID = registered_objects[i]['objectID'] if object_class != 0 else registered_objects[0]['objectID']
            matched_indexes, overlapped_indexes = self.match(rpos, result) if object_class!=0 else self.match(rpos, transformed_result)
            name = registered_objects[i]['name'] if object_class !=0 else registered_objects[0]['position'][i]['name']
            if len(matched_indexes) > 0:
                matched_regions = [result[j] for j in matched_indexes]
                #matched_regions.append(rpos)
                new_x1, new_y1, new_x2, new_y2 = self.repair(matched_regions)
                candidates.append({
                    'x1':new_x1,
                    'y1':new_y1,
                    'x2':new_x2,
                    'y2':new_y2,
                    'registered':True,
                    'name':name,
                    'objectID':objectID
                })
            else:
                candidates.append({
                    'x1':rpos[0],
                    'y1':rpos[1],
                    'x2':rpos[2],
                    'y2':rpos[3],
                    'registered':True,
                    'name':name,
                    'objectID':objectID
                })

            for index, r in enumerate(result):
                if index not in matched_indexes and index not in overlapped_indexes and index not in independent_indexes:
                    independent_indexes.append(index)

        for independent_index in independent_indexes:
            region = result[independent_index]
            candidates.append({
                'x1':region[0],
                'y1':region[1],
                'x2':region[2],
                'y2':region[3],
                'registered':False,
                'name':None,
                'objectID':None
                })

        return candidates, object_class


    def repair(self, regions):
        """
            regions: [[x1, y1, x2, y2, ...], [x1, y1, x2, y2, ...], ...]
        """
        coordinates = [[], [], [], []]
        for r in regions:
            for i in range(len(coordinates)):
                coordinates[i].append(r[i])
        x1, y1 = min(coordinates[0]), min(coordinates[1])
        x2, y2 = max(coordinates[2]), max(coordinates[3])
        return x1, y1, x2, y2

    def match(self, region, regions):
        """
            region: [x1, y1, x2, y2, ...],
            regions:[[x1, y1, x2, y2, ...], [x1, y1, x2, y2, ...], ...]
        """
        region = np.array(region[:4])
        regions = np.array(regions)[:, :4]
        scores = [culc_iou(region, r) for r in regions]
        matched_indexes = [i for i, s in enumerate(scores) if s > self.iou_thresh]
        overlapped_indexes = [i for i, s in enumerate(scores) if self.iou_thresh >= s > 0]
        return matched_indexes, overlapped_indexes

    def update(self, candidates, object_class, master_handler):
        """
            Upate positions of registered objects
        """
        candidates = [c for c in candidates if c['objectID'] is not None and c['registered']]
        if object_class == 0 and len(candidates) > 0:
            objectID = candidates[0]['objectID']
            position = [{'x1':c['x1'], 'y1':c['y1'], 'x2':c['x2'], 'y2':c['y2'], 'name':c['name']} for c in candidates if c['objectID'] is not None and c['registered']]
            register_objects = [{'objectID':objectID, 'position':json.dumps(position)}]
        else:
            register_objects = [{'objectID':c['objectID'], 'position':json.dumps({'x1':c['x1'], 'y1':c['y1'], 'x2':c['x2'], 'y2':c['y2'], 'name':c['name']})} for c in candidates]
        master_handler.add('objects', 'objectID', register_objects)

    def __call__(self, deviceID, result, master_handler):
        """
        OUTPUT:
            output = {
                'deviceID':deviceID,
                'class': 1,  -> object_class
                'result':[
                    {'x1':new_x1, 'y1':new_y1, 'x2':new_x2, 'y2':new_y2, 'registered':True, 'name':name, 'objectID':objectID},
                    {'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2, 'registered':True, 'name':name, 'objectID':objectID},
                    {'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2, 'registered':False, 'name':None, 'objectID':None}...
                    ]
            },
        """
        candidates, object_class = self.get_candidates(deviceID, result, master_handler)
        candidates_data = json.dumps(candidates)
        result = {'deviceID':deviceID, 'class': object_class,'result':candidates_data}
        if self.update_master:
            self.update(candidates, object_class, master_handler)
        return result


if __name__ == '__main__':
    from toolbox import DB_Handler
    master_db = DB_Handler('/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/db/master.db')
    detector_db = DB_Handler('/home/galaxygliese/Desktop/integrAI/TECH/AppV3/developing/db/detected.db')
    rr = Region_Repairer(detector_db)

    deviceID = '162'
    results = detector_db.get('log', {'deviceID':deviceID})#[[0.11, 0.15, 0.13, 0.2, 1], [0.45, 0.2, 0.56, 0.26, 1],[0.15, 0.15, 0.23, 0.30, 1]]
    print(len(results))
    #result = [[r['x1'], r['y1'], r['x2'], r['y2'], 1, 0] for r in results[-1]['result']]
    result = [[r['x1'], r['y1'], r['x2'], r['y2'], 1, 1] for r in results[-1]['result']]
    #print(result, len(result))
    output = rr.get_candidates(deviceID, result=result, master_handler=master_db)
    print("O L:", len(output))
    #pprint(output)
