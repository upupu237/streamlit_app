# 讯飞星火大模型接口
import _thread as thread
import ssl
import websocket
from datetime import datetime
from time import mktime, sleep
from urllib.parse import urlparse, urlencode
from wsgiref.handlers import format_date_time
import hashlib
import hmac
import time
import logging
import json
import base64

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 讯飞星火X1 API配置（可根据需要调整为从环境变量读取）
APPID = "79be4290"
APIKey = "867eb662349b45edf64a4d48bc638a62"
APISecret = "ZjE5NTZiYWFmNWNlMjg0OTUzMWVlM2Uz"
DOMAIN = "x1"
SPARK_URL = "wss://spark-api.xf-yun.com/v1/x1"
API_TIMEOUT = 60  # 超时时间（秒）
MAX_RETRIES = 5  # 最大重试次数
RETRY_DELAY = 3  # 重试间隔(秒)


class WsParam:
    """生成WebSocket连接参数"""

    def __init__(self, appid, api_key, api_secret, spark_url):
        self.appid = appid
        self.api_key = api_key
        self.api_secret = api_secret
        self.spark_url = spark_url
        self.host = urlparse(spark_url).netloc
        self.path = urlparse(spark_url).path

    def create_url(self):
        """生成带鉴权的WebSocket URL"""
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"

        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode('utf-8')

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        return f"{self.spark_url}?{urlencode(v)}"


# 全局变量（函数内使用）
answer = ""
is_complete = False
error_message = ""
last_response_time = 0


# WebSocket回调函数
def on_error(ws, error):
    """处理错误信息"""
    global is_complete, error_message
    error_message = f"WebSocket错误: {str(error)}"
    logger.error(error_message)
    is_complete = True


def on_close(ws, close_status_code, close_msg):
    """处理连接关闭（添加判空检查）"""
    global is_complete
    try:
        # 关键修复：关闭前检查连接是否存在且仍在连接状态
        if ws is not None:  # 确保ws对象未被释放
            # 检查connected属性（不同版本websocket-client可能属性名不同，此处用getattr兼容）
            if getattr(ws, 'connected', False):
                ws.close()  # 确保关闭连接
    except Exception as e:
        logger.error(f"关闭WebSocket时发生异常：{e}")
    logger.info(f"WebSocket连接关闭: {close_status_code}, {close_msg}")
    is_complete = True


def on_open(ws):
    """连接建立后发送请求数据"""
    logger.info("WebSocket连接已建立")
    thread.start_new_thread(run, (ws,))


def run(ws, *args):
    """发送请求参数"""
    global last_response_time
    data = json.dumps(gen_params(ws.appid, ws.domain, ws.question))
    logger.info(f"发送请求数据: {data[:100]}...")  # 只记录前100个字符
    ws.send(data)
    last_response_time = time.time()


def on_message(ws, message):
    """处理模型返回消息"""
    global answer, is_complete, error_message, last_response_time
    last_response_time = time.time()
    try:
        data = json.loads(message)
        logger.debug(f"收到消息: {message[:100]}...")  # 只记录前100个字符

        code = data['header']['code']

        if code != 0:
            error_message = f"请求错误: {code}, 详情: {data}"
            logger.error(error_message)
            ws.close()
            is_complete = True
            return

        choices = data["payload"]["choices"]
        status = choices["status"]
        text = choices['text'][0]

        if 'content' in text and text['content']:
            content = text["content"]
            answer += content
            logger.info(f"累积内容: {content[:50]}...")  # 只记录前50个字符

        if status == 2:
            logger.info("收到结束标识，会话完成")
            is_complete = True
            ws.close()
    except Exception as e:
        error_message = f"处理消息失败: {str(e)}"
        logger.error(error_message, exc_info=True)  # 记录完整堆栈信息
        is_complete = True
        ws.close()


def gen_params(appid, domain, question):
    """生成符合官方要求的请求参数结构"""
    return {
        "header": {
            "app_id": appid,
            "uid": "streamlit_user"
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_k": 6,  # 符合API限制
                "penalty_score": 1.0
            }
        },
        "payload": {
            "message": {
                "text": question
            }
        }
    }


def call_spark_x1(prompt):
    """调用星火X1模型（对外统一接口）"""
    global answer, is_complete, error_message, last_response_time

    for attempt in range(MAX_RETRIES):
        # 重置状态
        answer = ""
        is_complete = False
        error_message = ""

        question = [{"role": "user", "content": prompt}]

        try:
            logger.info(f"尝试调用星火API (第{attempt + 1}/{MAX_RETRIES}次)")

            ws_param = WsParam(APPID, APIKey, APISecret, SPARK_URL)
            ws_url = ws_param.create_url()
            logger.info(f"生成的URL: {ws_url[:100]}...")

            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.appid = APPID
            ws.domain = DOMAIN
            ws.question = question

            # 启动WebSocket连接
            wst = thread.start_new_thread(ws.run_forever, ())
            logger.info("WebSocket线程已启动")

            # 超时控制
            start_time = time.time()
            last_response_time = start_time

            while not is_complete:
                elapsed = time.time() - start_time

                # 总超时检测（添加判空检查）
                if elapsed > API_TIMEOUT:
                    # 关键修复：关闭前检查ws是否存在
                    if ws is not None:
                        try:
                            if getattr(ws, 'connected', False):
                                ws.close()
                        except Exception as e:
                            logger.error(f"超时关闭WebSocket异常：{e}")
                    error_message = f"调用超时（总时间超过{API_TIMEOUT}秒）"
                    logger.warning(error_message)
                    raise Exception(error_message)

                sleep(0.1)

            # 检查是否有错误
            if error_message:
                raise Exception(error_message)

            if answer.strip():
                logger.info(f"成功获取响应: {answer[:50]}...")
                return answer.strip()
            else:
                error_message = "未获取到有效回复内容"
                logger.warning(error_message)
                raise Exception(error_message)

        except Exception as e:
            logger.error(f"调用失败: {str(e)}")
            if attempt >= MAX_RETRIES - 1:
                raise Exception(f"调用失败（已重试{MAX_RETRIES}次）: {str(e)}")

            # 重试前等待
            logger.info(f"将在{RETRY_DELAY}秒后重试...")
            sleep(RETRY_DELAY)