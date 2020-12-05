#-*- coding:utf-8 -*-

from .db_handler import DB_Handler
import json

class Value_Handler(object):
    def __init__(self, rec_handler, num_max_samples=5000, db_limit=30000):
        self.rec_handler = rec_handler
        self.num_max_samples = num_max_samples
        self.db_limit = db_limit

    def get_values(self, objectID, date1, date2):
        """
            INPUT:
                objectID: objectID,
                date1, date2: "YYYY-mm-dd HH:MM:SS"
                object_class: object_class

            OUTPUT:
                object_class == 0:
                    [{'valueID':valueID, 'date':"YYYY-mm-dd HH:MM:SS", 'imgfile':imgfile, 'result':[{'name':name1, 'value':v1}, {'name':name2, 'value':v2}, ... ]}, ...]

                object_class != 0:
                    [{'valueID':valueID, 'date':"YYYY-mm-dd HH:MM:SS", 'imgfile':imgfile, 'result':{'value':v1}}, ...]
        """
        sql = "SELECT * FROM log WHERE objectID='{0}' AND DATETIME('{1}') <= DATETIME(timestamp) AND DATETIME(timestamp) <= DATETIME('{2}') ORDER BY timestamp LIMIT {3};".format(objectID, date1, date2, self.db_limit)
        samples = self.rec_handler.run_custom_sql(sql)
        samples = self.format_samples(samples)
        return samples

    def format_samples(self, samples):
        new_samples = []
        valueID_buf = None # Do not pick VALUE twice
        for s in samples:
            if s[6] != valueID_buf:
                new_samples.append({"result":json.loads(s[3]), "date":s[4], "code":s[5], "valueID":s[6], "imgfile":s[7]})
                valueID_buf = s[6]
        return new_samples

    def pick_samples(self, object_class, samples):
        """
            pick NUM_MAX_SAMPLES
        """
        if object_class == 0:
            return samples[-30:]
        elif object_class != 0 and len(samples) < self.num_max_samples:
            return samples
        else:
            return

    def set_value(self, valueID, data):
        """
            INPUT:
                valueID: valueID
                data: {'data':{'result':[...], 'date':...}}
        """
        _data = {'valueID':valueID, 'result':json.dumps(data['data']['result'])}
        self.rec_handler.add("log", "valueID", [_data])
        print("valueID:{} | Value Edited".format(valueID))
        return {'success':True}

    def delete_value(self, valueID):
        self.rec_handler.delete('log', {'valueID':valueID})
        print("valueID:{} | Deleted".format(valueID))
        return {'success':True}

if __name__ == '__main__':
    from pprint import pprint
    rec_handler = DB_Handler('../../db/recognized.db')
    vh = Value_Handler(rec_handler)
    vh.get_values('1621', '2020-11-30', '2020-12-03', 1)
