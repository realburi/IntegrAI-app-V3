#-*- coding:utf-8 -*-

from .db_handler import DB_Handler
import json
import os

class Object_Handler(object):
    def __init__(self, master_handler):
        self.master_handler = master_handler

    def get_object(self, objectID:str, det_handler:DB_Handler):
        data = self.master_handler.get('objects', {'objectID':objectID})
        if len(data) == 0:
            return []
        else:
            data = data[0]
            object_class = data['class']
            if object_class != 0:
                return data
            else: # Paper Master Coordinate TO Detected Coordinate
                deviceID = data['deviceID']
                sql = "SELECT result FROM log WHERE id=(SELECT MAX(id) FROM log WHERE deviceID='{0}') AND deviceID='{0}';".format(deviceID)
                results = det_handler.run_custom_sql(sql)[0][0]
                results = json.loads(results)
                regions = [{"name":r['name'], "x1":r['x1'], "y1":r['y1'], "x2":r['x2'], "y2":r['y2']} for r in results if r['objectID'] is not None and r['registered'] ]
                data['position'] = regions
                return data


    def register_object(self, object_class:int, deviceID:str, datas:list):
        object_datas = []
        if object_class == 0: # 1device to 1object to many positions
            datas = datas['position']
            objectID = deviceID+"1"
            object_datas.append({
                "objectID":objectID,
                "deviceID":deviceID,
                "class":object_class,
                "position":json.dumps([{"x1":r["x1"], "y1":r["y1"], "x2":r["x2"], "y2":r["y2"], "name":r["name"]} for r in datas])
                })
        elif object_class != 0:# 1device to many objects to 1position
            count = self.master_handler.count("objects", conditions={"deviceID":deviceID})[0][0]
            print(len(datas), datas)
            objectID = deviceID+str(count+1) if datas['objectID'] is None else datas['objectID']
            object_datas.append({
                "objectID":objectID,
                "deviceID":deviceID,
                "class":object_class,
                "object_content":json.dumps(datas["objectContent"]),
                "position":json.dumps({"x1":datas["position"]["x1"], "y1":datas["position"]["y1"], "x2":datas["position"]["x2"], "y2":datas["position"]["y2"]}),
                "name":datas["name"]
            })
        print("L:", len(datas))
        self.master_handler.add("objects", "objectID", object_datas)
        print("OBJECT REGISTERED!")
        return objectID

    def recover_position(self, objectID:str, position:dict):
        """
            position: {'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2}
        """
        object = self.master_handler.get("objects", conditions={"objectID":objectID})
        if len(object) > 0:
            object = object[0]
            self.master_handler.add("objects", "objectID", [{"objectID":objectID, "position":json.dumps(position)}])
            print("Object {} | Recovered".format(objectID))
            return {"success":True}
        return {"success":False}

    def set_object(self, objectID:str, object_content:dict):
        """
            Update only object_content
        """
        data = {'objectID':objectID, 'object_content':json.dumps(object_content)}
        self.master_handler.add("objects", "objectID", [data])
        print("Object {} | Set".format(objectID))
        return {"success":True}

    def delete_object(self, objectID:str, rec_handler:DB_Handler=None):
        self.master_handler.delete("objects", conditions={"objectID":objectID})
        if rec_handler is not None:
            rec_handler.delete("log", conditions={"objectID":objectID})
            print("Object {} | Delete".format(objectID))
            return {"success":True}
        return {"success":False}

    def update_objects(self, object_class:int, deviceID:str, contents:list):
        """
            (Update only Positions)
            Register and Update? Master Coordinate -> Only for UI Upload Button
            INPUT:
                object_class: Object Class
                deviceID: deviceID
                content:[{'class':0, 'name':name, 'objectID':objectID or None, 'registered':True, 'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2}, ...]
        """
        if object_class == 0:
            objectID = contents[0]['objectID'] if len(contents) > 0 else deviceID+'1'
            objectID = deviceID+str(1) if objectID is None else objectID
            positions = []
            for r in contents:
                positions.append({"x1":r["x1"], "y1":r["y1"], "x2":r["x2"], "y2":r["y2"], "name":r["name"]})
            object_datas = {"objectID":objectID, "position":json.dumps(positions)}
            self.master_handler.add("objects", "objectID", [object_datas])
            print("deviceID: {} | Uploaded".format(deviceID))
        return {"success":True}
