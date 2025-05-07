# 语音合成CosyVoice Python API

本文介绍语音合成CosyVoice Python API的使用。

前提条件
已开通服务并获取API Key。请配置API Key到环境变量，而非硬编码在代码中，防范因代码泄露导致的安全风险。

安装最新版DashScope SDK。

## 快速开始
SpeechSynthesizer类提供了语音合成的关键接口，支持以下几种调用方式：

- 同步调用：提交文本后，服务端立即处理并返回完整的语音合成结果。整个过程是阻塞式的，客户端需要等待服务端完成处理后才能继续下一步操作。适合短文本语音合成场景。

- 异步调用：将文本一次发送至服务端并实时接收语音合成结果，不允许将文本分段发送。适用于对实时性要求高的短文本语音合成场景。

- 流式调用：将文本逐步发送到服务端并实时接收语音合成结果，允许将长文本分段发送，服务端在接收到部分文本后便立即开始处理。适合实时性要求高的长文本语音合成场景。

### 同步调用
提交单个语音合成任务，无需调用回调函数，进行语音合成（无流式输出中间结果），最终一次性获取完整结果。


实例化SpeechSynthesizer类绑定请求参数，调用call方法进行合成并获取二进制音频数据。

发送的文本长度不得超过2000字符（详情请参见SpeechSynthesizer类的call方法）。
```python
# coding=utf-8

import dashscope
from dashscope.audio.tts_v2 import *

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
# dashscope.api_key = "your-api-key"

# 模型
model = "cosyvoice-v2"
# 音色
voice = "longxiaochun_v2"

# 实例化SpeechSynthesizer，并在构造方法中传入模型（model）、音色（voice）等请求参数
synthesizer = SpeechSynthesizer(model=model, voice=voice)
# 发送待合成文本，获取二进制音频
audio = synthesizer.call("今天天气怎么样？")
print('[Metric] requestId: {}, first package delay ms: {}'.format(
    synthesizer.get_last_request_id(),
    synthesizer.get_first_package_delay()))

# 将音频保存至本地
with open('output.mp3', 'wb') as f:
    f.write(audio)
```

### 异步调用
提交单个语音合成任务，通过回调的方式流式输出中间结果，合成结果通过ResultCallback中的回调函数流式获取。

实例化SpeechSynthesizer类绑定请求参数和回调接口（ResultCallback），调用call方法进行合成并通过回调接口（ResultCallback）的on_data方法实时获取合成结果。

发送的文本长度不得超过2000字符（详情请参见SpeechSynthesizer类的call方法）。

```python
# coding=utf-8

import dashscope
from dashscope.audio.tts_v2 import *

from datetime import datetime

def get_timestamp():
    now = datetime.now()
    formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
    return formatted_timestamp

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
# dashscope.api_key = "your-api-key"

# 模型
model = "cosyvoice-v2"
# 音色
voice = "longxiaochun_v2"


# 定义回调接口
class Callback(ResultCallback):
    _player = None
    _stream = None

    def on_open(self):
        self.file = open("output.mp3", "wb")
        print(get_timestamp() + " websocket is open.")

    def on_complete(self):
        print(get_timestamp() + " speech synthesis task complete successfully.")

    def on_error(self, message: str):
        print(f"speech synthesis task failed, {message}")

    def on_close(self):
        print(get_timestamp() + " websocket is closed.")
        self.file.close()

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " audio result length: " + str(len(data)))
        self.file.write(data)


callback = Callback()

# 实例化SpeechSynthesizer，并在构造方法中传入模型（model）、音色（voice）等请求参数
synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    callback=callback,
)

# 发送待合成文本，在回调接口的on_data方法中实时获取二进制音频
synthesizer.call("今天天气怎么样？")
print('[Metric] requestId: {}, first package delay ms: {}'.format(
    synthesizer.get_last_request_id(),
    synthesizer.get_first_package_delay()))
```

### 流式调用
在同一个语音合成任务中分多次提交文本，并通过回调的方式实时获取合成结果。

说明
流式输入时可多次调用streaming_call按顺序提交文本片段。服务端接收文本片段后自动进行分句：

完整语句立即合成

不完整语句缓存至完整后合成

调用 streaming_complete 时，服务端会强制合成所有已接收但未处理的文本片段（包括未完成的句子）。

发送文本片段的间隔不得超过23秒，否则触发“request timeout after 23 seconds”异常。

若无待发送文本，需及时调用 streaming_complete结束任务。

服务端强制设定23秒超时机制，客户端无法修改该配置。
实例化SpeechSynthesizer类

实例化SpeechSynthesizer类绑定请求参数和回调接口（ResultCallback）。

流式传输

多次调用SpeechSynthesizer类的streaming_call方法分片提交待合成文本，将待合成文本分段发送至服务端。

在发送文本的过程中，服务端会通过回调接口（ResultCallback）的on_data方法，将合成结果实时返回给客户端。

每次调用streaming_call方法发送的文本片段（即text）长度不得超过2000字符，累计发送的文本总长度不得超过20万字符。

结束处理

调用SpeechSynthesizer类的streaming_complete方法结束语音合成。

该方法会阻塞当前线程，直到回调接口（ResultCallback）的on_complete或者on_error回调触发后才会释放线程阻塞。


```python 
# coding=utf-8
#
# Installation instructions for pyaudio:
# APPLE Mac OS X
#   brew install portaudio
#   pip install pyaudio
# Debian/Ubuntu
#   sudo apt-get install python-pyaudio python3-pyaudio
#   or
#   pip install pyaudio
# CentOS
#   sudo yum install -y portaudio portaudio-devel && pip install pyaudio
# Microsoft Windows
#   python -m pip install pyaudio

import time
import pyaudio
import dashscope
from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
from dashscope.audio.tts_v2 import *

from datetime import datetime

def get_timestamp():
    now = datetime.now()
    formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
    return formatted_timestamp

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
# dashscope.api_key = "your-api-key"

# 模型
model = "cosyvoice-v2"
# 音色
voice = "longxiaochun_v2"


# 定义回调接口
class Callback(ResultCallback):
    _player = None
    _stream = None

    def on_open(self):
        print("websocket is open.")
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        print(get_timestamp() + " speech synthesis task complete successfully.")

    def on_error(self, message: str):
        print(f"speech synthesis task failed, {message}")

    def on_close(self):
        print(get_timestamp() + " websocket is closed.")
        # 停止播放器
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " audio result length: " + str(len(data)))
        self._stream.write(data)


callback = Callback()

test_text = [
    "流式文本语音合成SDK，",
    "可以将输入的文本",
    "合成为语音二进制数据，",
    "相比于非流式语音合成，",
    "流式合成的优势在于实时性",
    "更强。用户在输入文本的同时",
    "可以听到接近同步的语音输出，",
    "极大地提升了交互体验，",
    "减少了用户等待时间。",
    "适用于调用大规模",
    "语言模型（LLM），以",
    "流式输入文本的方式",
    "进行语音合成的场景。",
]

# 实例化SpeechSynthesizer，并在构造方法中传入模型（model）、音色（voice）等请求参数
synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    format=AudioFormat.PCM_22050HZ_MONO_16BIT,  
    callback=callback,
)


# 流式发送待合成文本。在回调接口的on_data方法中实时获取二进制音频
for text in test_text:
    synthesizer.streaming_call(text)
    time.sleep(0.1)
# 结束流式语音合成
synthesizer.streaming_complete()

print('[Metric] requestId: {}, first package delay ms: {}'.format(
    synthesizer.get_last_request_id(),
    synthesizer.get_first_package_delay()))
```

## 请求参数
请求参数通过SpeechSynthesizer类的构造方法进行设置。


| 参数 | 类型 | 默认值 | 是否必须 | 说明 |
| --- | --- | --- | --- | --- |
| model | str | - | 是 | 指定模型，支持cosyvoice-v1、cosyvoice-v2。|
| voice | str | - | 是 | 指定语音合成所使用的音色。 | 支持如下两种音色：默认音色（参见音色列表）。通过声音复刻功能定制的专属音色。使用声音复刻音色时（请确保声音复刻与语音合成使用同一账号），需将voice参数设置为复刻音色的ID，完整操作流程请参见使用复刻的音色进行语音合成。cosyvoice-v1和cosyvoice-v2模型均支持声音复刻功能。 |
| format | enum | 因音色而异 | 否 | 指定音频编码格式及采样率。 | 若未指定format，系统将根据voice参数自动选择该音色的推荐格式（如龙小淳默认使用MP3_22050HZ_MONO_256KBPS），详情请参见音色列表。 |
| volume | int | 50 | 否 | 合成音频的音量，取值范围：0~100。|
| speech_rate | float | 1.0 | 否 | 合成音频的语速，取值范围：0.5~2。0.5：表示默认语速的0.5倍速。1：表示默认语速。默认语速是指模型默认输出的合成语速，语速会因音色不同而略有不同。约每秒钟4个字。2：表示默认语速的2倍速。 |
| pitch_rate | float | 1.0 | 否 | 合成音频的语调，取值范围：0.5~2。|
| callback | ResultCallback | - | 否 | 回调接口（ResultCallback）| 

#### format中可指定的音频编码格式及采样率如下：
- AudioFormat.WAV_8000HZ_MONO_16BIT，代表音频格式为wav，采样率为8kHz
- AudioFormat.WAV_16000HZ_MONO_16BIT，代表音频格式为wav，采样率为16kHz
- AudioFormat.WAV_22050HZ_MONO_16BIT，代表音频格式为wav，采样率为22.05kHz
- AudioFormat.WAV_24000HZ_MONO_16BIT，代表音频格式为wav，采样率为24kHz
- AudioFormat.WAV_44100HZ_MONO_16BIT，代表音频格式为wav，采样率为44.1kHz
- AudioFormat.WAV_48000HZ_MONO_16BIT，代表音频格式为wav，采样率为48kHz
- AudioFormat.MP3_8000HZ_MONO_128KBPS，代表音频格式为mp3，采样率为8kHz
- AudioFormat.MP3_16000HZ_MONO_128KBPS，代表音频格式为mp3，采样率为16kHz
- AudioFormat.MP3_22050HZ_MONO_256KBPS，代表音频格式为mp3，采样率为22.05kHz
- AudioFormat.MP3_24000HZ_MONO_256KBPS，代表音频格式为mp3，采样率为24kHz
- AudioFormat.MP3_44100HZ_MONO_256KBPS，代表音频格式为mp3，采样率为44.1kHz
- AudioFormat.MP3_48000HZ_MONO_256KBPS，代表音频格式为mp3，采样率为48kHz
- AudioFormat.PCM_8000HZ_MONO_16BIT，代表音频格式为pcm，采样率为8kHz
- AudioFormat.PCM_16000HZ_MONO_16BIT，代表音频格式为pcm，采样率为16kHz
- AudioFormat.PCM_22050HZ_MONO_16BIT，代表音频格式为pcm，采样率为22.05kHz
- AudioFormat.PCM_24000HZ_MONO_16BIT，代表音频格式为pcm，采样率为24kHz
- AudioFormat.PCM_44100HZ_MONO_16BIT，代表音频格式为pcm，采样率为44.1kHz
- AudioFormat.PCM_48000HZ_MONO_16BIT，代表音频格式为pcm，采样率为48kHz

#### 音色列表
你应当从我已经部署好的数据库中获取音色相关信息。以下是数据库中表的相关信息。
```python
class Voice(db.Model):
    __tablename__ = 'voices'
    # 在 Python 层生成有序 UUID v7，存为 16 字节二进制
    voice_id = Column(BINARY(16),primary_key=True,default=lambda: uuid7().bytes,nullable=False)
    @property
    def voice_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.voice_id))
    voice_name = Column(VARCHAR(50), nullable=False)
    # 外键引用 files.file_id，同样是 16 字节二进制
    voice_url = Column(BINARY(16),ForeignKey('files.file_id', ondelete='SET NULL'),nullable=False)
    @property
    def voice_url_str(self) -> str:
        return str(uuid.UUID(bytes=self.voice_url))
    created_at = Column(TIMESTAMP,nullable=False,default=datetime.utcnow
    created_by = Column(BINARY(16),ForeignKey('users.id', ondelete='CASCADE'),nullable=False)
    @property
    def created_by_user_id_str(self) -> str:
        return str(uuid.UUID(bytes=self.created_by))
    is_public        = Column(BOOLEAN, nullable=False, default=False)
    call_name        = Column(VARCHAR(255), nullable=False)
    voice_gender     = Column(VARCHAR(6),  nullable=False)
    voice_description = Column(TEXT,       nullable=False)
    __table_args__ = (
        # 确保 gender 只能是 'male'/'female'/'other'
        CheckConstraint(voice_gender.in_(['male', 'female', 'other']),name='voice_gender_check'),
    )
    # 关联到 User
    creator = db.relationship(
        'User',
        backref=db.backref('voices', lazy=True),
        foreign_keys=[created_by]
    )

class User(db.Model):
    __tablename__ = 'users'
    # 用 uuid7() 在 Python 端生成有序的 16 字节 UUID
    id = db.Column(BINARY(16),primary_key=True,default=lambda: uuid7().bytes,nullable=False)
    # 只读属性：把 bytes 转成标准 UUID 格式字符串
    @property
    def id_str(self) -> str:
        return str(uuid.UUID(bytes=self.id))
    username     = db.Column(db.String(18),  nullable=False)
    phone_number = db.Column(db.String(11),  nullable=True)
    email        = db.Column(db.String(50),  nullable=True)
    password     = db.Column(db.String(255), nullable=False)
    theme_color  = db.Column(db.Integer,     nullable=True)
    avatar_url = db.Column(BINARY(16), db.ForeignKey('files.file_id', ondelete='SET NULL'),nullable=True)
    @property
    def avatar_url_str(self) -> str | None:
        if self.avatar_url:
            return str(uuid.UUID(bytes=self.avatar_url))
        return None

    created_at    = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.TIMESTAMP, nullable=True)
```

## 关键接口
SpeechSynthesizer类
SpeechSynthesizer通过“from dashscope.audio.tts_v2 import *”方式引入，提供语音合成的关键接口。


| 方法 | 参数 | 返回值 | 描述 |
| --- | --- | --- | --- |
| def call(self, text: str, timeout_millis=None) | text：待合成文本，timeout_millis：阻塞线程的超时时间，单位为毫秒，不设置或值为0时不生效 | 没有指定ResultCallback时返回二进制音频数据，否则返回None | 将整段文本转换为语音。在创建SpeechSynthesizer实例时，存在以下两种情况：没有指定ResultCallback：call方法会阻塞当前线程直到语音合成完成并返回二进制音频数据。使用方法请参见同步调用。指定了ResultCallback：call方法会立刻返回None，并通过回调接口（ResultCallback）的on_data方法返回语音合成的结果。使用方法请参见异步调用。注意：调用call方法发送的文本（即text）长度不得超过2000字符。字符计算规则：1个汉字算作2个字符。1个英文字母、1个标点或1个句子中间的空格均算作1个字符。 |
| def streaming_call(self, text: str) | text：待合成文本片段 | 无 | 流式发送待合成文本。您可以多次调用该接口，将待合成文本分多次发送给服务端。合成结果通过回调接口（ResultCallback）的on_data方法获取。使用方法请参见流式调用。注意：必须在所有streaming_call调用完成后执行streaming_complete结束任务。每次调用streaming_call方法发送的文本片段（即text）长度不得超过2000字符，累计发送的文本总长度不得超过20万字符。字符计算规则：1个汉字算作2个字符。1个英文字母、1个标点或1个句子中间的空格均算作1个字符。 | 
| def streaming_complete(self, complete_timeout_millis=600000) | complete_timeout_millis：等待时间，单位为毫秒 | 无 | 结束流式语音合成。该方法阻塞当前线程N毫秒（具体时长由complete_timeout_millis决定），直到任务结束。如果completeTimeoutMillis设置为0，则无限期等待。默认情况下，如果等待时间超过10分钟，则停止等待。使用方法请参见流式调用。 | 
| def get_last_request_id(self) | 无 | 上一个任务的request_id | 获取上一个任务的request_id。| 
| def get_first_package_delay(self) | 无 | 首包延迟 | 获取首包延迟。 | 首包延迟是开始发送文本和接收第一个音频包之间的时间，单位为毫秒。在任务完成后使用。| 
| def get_response(self) | 无 | 最后一次报文 | 获取最后一次报文（为JSON格式的数据），可以用于获取task-failed报错。 | 

## 回调接口（ResultCallback）
异步调用或流式调用时，服务端会通过回调的方式，将关键流程信息和数据返回给客户端。您需要实现回调方法，处理服务端返回的信息或者数据。
```python
class Callback(ResultCallback):
    def on_open(self) -> None:
        print('连接成功')
    
    def on_data(self, data: bytes) -> None:
        # 实现接收合成二进制音频结果的逻辑

    def on_complete(self) -> None:
        print('合成完成')

    def on_error(self, message) -> None:
        print('出现异常：', message)

    def on_close(self) -> None:
        print('连接关闭')


callback = Callback()

```
| 方法 | 参数 | 返回值 | 描述 |
| --- | --- | --- | --- |
| def on_open(self) -> None | 无 | 无 | 当和服务端建立连接完成后，该方法立刻被回调。|
| def on_event( self, message: str) -> None | message：服务端返回的信息 | 无 | 当服务有回复时会被回调。 | 当前可忽略该接口。 | 
| def on_complete(self) -> None | 无 | 无 | 当所有合成数据全部返回（语音合成完成）后被回调。 | 
| def on_error(self, message) -> None | message：异常信息 | 无 | 发生异常时该方法被回调。|
| def on_data(self, data: bytes) -> None | data：服务器返回的二进制音频数据 | 无 | 当服务器有合成音频返回时被回调。您可以将二进制音频数据合成为一个完整的音频文件后使用播放器播放，也可以通过支持流式播放的播放器实时播放。重要:在流式语音合成中，完整的音频文件会被分多次返回。播放流式音频时，需要使用支持流式播放的音频播放器，而不是将每一帧作为独立的音频进行播放，否则可能导致解码失败。支持流式播放的播放器：ffmpeg、pyaudio (Python)、AudioFormat (Java)、MediaSource (Javascript)等。将音频数据合成为一个完整的音频文件时，请以追加模式将数据写入同一个文件。在使用wav或mp3格式进行流式语音合成时，文件头信息仅包含在第一帧中，后续帧为纯音频数据。 |
| def on_close(self) -> None | 无 | 无 | 当服务已经关闭连接后被回调。 | 
