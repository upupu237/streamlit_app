# 语音识别模块
import threading
import time
from time import mktime
import websocket
import base64
from datetime import datetime
import hashlib
import hmac
import json
import ssl
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time


STATUS_FIRST_FRAME = 0
STATUS_CONTINUE_FRAME = 1
STATUS_LAST_FRAME = 2

class Ws_Param:
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile
        self.iat_params = {
            "domain": "slm", "language": "zh_cn", "accent": "mandarin", "dwa": "wpgs",
            "result": {"encoding": "utf8", "compress": "raw", "format": "plain"}
        }

    def create_url(self):
        url = 'wss://iat.xf-yun.com/v1'
        # 此时 datetime 是导入的类，调用 now() 方法正确
        now = datetime.now()  # 已修正：使用导入的 datetime 类
        date = format_date_time(mktime(now.timetuple()))
        # 修正多行字符串中的缩进（避免签名错误）
        signature_origin = f"""host: iat.xf-yun.com
date: {date}
GET /v1 HTTP/1.1"""  # 注意：每行开头不能有多余缩进，否则签名验证失败
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode('utf-8')

        authorization_origin = f"api_key=\"{self.APIKey}\", algorithm=\"hmac-sha256\", headers=\"host date request-line\", signature=\"{signature_sha}\""
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        v = {"authorization": authorization, "date": date, "host": "iat.xf-yun.com"}
        return url + '?' + urlencode(v)

def recognize_pcm(appid, apikey, apisecret, pcm_path):
    result_text = []
    seen_words = set()  # 用于记录已出现的词语
    lock = threading.Lock()  # 线程锁保证线程安全

    def on_message(ws, message):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            print("无效的消息格式")
            return

        code = message["header"]["code"]
        status = message["header"]["status"]
        if code != 0:
            print(f"识别出错：{code}")
            ws.close()
            return

        payload = message.get("payload")
        if payload:
            try:
                text = json.loads(base64.b64decode(payload["result"]["text"]).decode("utf-8"))
            except (base64.binascii.Error, json.JSONDecodeError):
                print("解码失败")
                return

            for segment in text.get('ws', []):
                for candidate in segment.get('cw', []):
                    word = candidate.get('w')
                    if word:
                        with lock:
                            if word not in seen_words:
                                seen_words.add(word)
                                result_text.append(word)

        if status == 2:
            ws.close()

    def on_error(ws, error):
        print("识别错误:", error)

    def on_close(ws, close_status_code, close_msg):
        pass

    def on_open(ws):
        def run(*args):
            with open(pcm_path, 'rb') as fp:
                status = STATUS_FIRST_FRAME
                while True:
                    buf = fp.read(1280)
                    if not buf:
                        status = STATUS_LAST_FRAME
                    audio = base64.b64encode(buf).decode('utf-8')
                    d = {
                        "header": {"status": status, "app_id": appid},
                        "parameter": {"iat": ws_param.iat_params},
                        "payload": {"audio": {"audio": audio, "sample_rate": 16000, "encoding": "raw"}}
                    }
                    ws.send(json.dumps(d))
                    if status == STATUS_LAST_FRAME:
                        break
                    status = STATUS_CONTINUE_FRAME
                    time.sleep(0.04)

        # 启动独立线程发送音频数据
        threading.Thread(target=run).start()

    ws_param = Ws_Param(appid, apikey, apisecret, pcm_path)
    ws_url = ws_param.create_url()
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    # 拼接最终结果
    full_text = ''.join(result_text)
    return full_text  # 清洗已在collect阶段完成
