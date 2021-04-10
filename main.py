from pywss import Pyws, route
from driver import CaptureHelper
import json

auth_pwd='7355608'

@route('/camera')
def my_websocket(request, data):
    if not (data.__contains__("{") and data.__contains__("}")):
        return "{\"result\":\"Error Format\"}"
    jsonObj=json.loads(data)

    if jsonObj["authentication"]!=auth_pwd:
        print("错误的用户认证：",jsonObj["authentication"])
        return "{\"result\":\"authfailure\"}"
    
    if jsonObj["command"]=="singeImage":
        #print(data)
        ts=jsonObj["timestamp"]
        base64='data:image/jpg;base64,'+cph.GetSingleImageBase64(ts)
        jsonresult={"result":"image","water_pump":"open" if cph.water_pump else "shutdown","image":base64}
        return json.dumps(jsonresult)
    elif jsonObj["command"]=='pump_open':
        cph.WP_Set(True)
        jsonresult={"result":"water_pump","water_pump":"open"}
        return json.dumps(jsonresult)
    elif jsonObj["command"]=='pump_shut':
        cph.WP_Set(False)
        jsonresult={"result":"water_pump","water_pump":"shutdown"}
        return json.dumps(jsonresult)
    else:
        return "{result:\"No command matchs.\"}"

cph=CaptureHelper()
ws = Pyws(__name__, address='0.0.0.0', port=9050)
ws.serve_forever()