# Qwen-Audio调用api示例
通义千问Audio是阿里云研发的大规模音频语言模型，能够接受多种音频（包括说话人语音、自然声音、音乐、歌声）和文本作为输入，并输出文本。通义千问Audio不仅能对输入的音频进行转录，还具备更深层次的语义理解、情感分析、音频事件检测、语音聊天等能力。
建议优先使用qwen-audio-turbo-latest模型，它是目前最新、能力最强的模型。同时，qwen-audio-turbo-latest还支持使用音频本身进行对话，适用于语音聊天场景。


开始使用
您需要已获取API Key并配置API Key到环境变量。如果通过SDK调用，还需要安装DashScope SDK。

### 基本示例

```python
import dashscope

messages = [
    {
        "role": "user",
        "content": [
            {"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"},
            {"text": "这段音频在说什么?"}
        ]
    }
]

response = dashscope.MultiModalConversation.call(
    model="qwen-audio-turbo-latest", 
    messages=messages,
    result_format="message"
    )
print(response)
```
 

响应示例

```json 
{
    "output": {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": "这段音频说的是:'欢迎使用阿里云'"
                        }
                    ]
                }
            }
        ]
    },
    "usage": {
        "audio_tokens": 85,
        "output_tokens": 10,
        "input_tokens": 33
    },
    "request_id": "1341c517-71bf-94f5-862a-18fbddb332e9"
}
```
### 使用本地文件
您可以参考以下示例代码，调用通义千问 Audio模型处理本地文件。以下代码使用的示例音频文件为：welcome.mp3

```python 
from dashscope import MultiModalConversation

# 请用您的本地音频的绝对路径替换 ABSOLUTE_PATH/welcome.mp3
audio_file_path = "file://ABSOLUTE_PATH/welcome.mp3"
messages = [
    {
        "role": "system", 
        "content": [{"text": "You are a helpful assistant."}]},
    {
        "role": "user",
        "content": [{"audio": audio_file_path}, {"text": "音频里在说什么?"}],
    }
]

response = MultiModalConversation.call(model="qwen-audio-turbo-latest", messages=messages)
print(response)
```
响应示例

```json 
{
    "status_code": 200,
    "request_id": "dd6b6c89-8550-9151-ac11-df31f17b026e",
    "code": "",
    "message": "",
    "output": {
        "text": null,
        "finish_reason": null,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": "这段音频说的是:'欢迎使用阿里云'"
                        }
                    ]
                }
            }
        ]
    },
    "usage": {
        "input_tokens": 33,
        "output_tokens": 10,
        "audio_tokens": 85
    }
}
```
### 多轮对话
通义千问Audio模型可以参考历史对话信息进行回复。您可以参考以下示例代码，实现多轮对话的功能。

```python 
from dashscope import MultiModalConversation

messages = [
    {
        "role": "user",
        "content": [
            {"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"},
            {"text": "这段音频在说什么?"},
        ]
    }
]

response = MultiModalConversation.call(model='qwen-audio-turbo-latest', messages=messages)
print("第1次回复:", response) 

# 将模型回复到messages中，并添加新的用户消息
messages.append({
    'role': response.output.choices[0].message.role,
    'content': response.output.choices[0].message.content
})
messages.append({
    "role": "user",
    "content": [
        {"text": "简单介绍这家公司。"}
    ]
})

response = MultiModalConversation.call(model='qwen-audio-turbo-latest', messages=messages)
print("第2次回复:", response)
```
响应示例

```json
第1次回复: {"status_code": 200, "request_id": "03084263-bc78-985d-9357-583f355d6a80", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": [{"text": "这段音频说的是:'欢迎使用阿里云'"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 10, "audio_tokens": 85}}
第2次回复: {"status_code": 200, "request_id": "27ebd962-f67c-9ca5-9510-be26d7988ca6", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": [{"text": "阿里巴巴集团是一家总部位于中国杭州的全球领先的电子商务和科技公司，成立于1999年。阿里巴巴集团旗下拥有包括淘宝、天猫、支付宝、菜鸟网络等在内的多个知名业务，涉及电商、金融、物流、云计算等多个领域。阿里巴巴在全球范围内开展业务，业务覆盖超过200个国家和地区，员工数量超过10万人。"}]}}]}, "usage": {"input_tokens": 56, "output_tokens": 74, "audio_tokens": 85}}
```
### 流式输出
模型并不是一次性生成最终结果，而是逐步地生成中间结果，最终结果由中间结果拼接而成。使用非流式输出方式需要等待模型生成结束后再将生成的中间结果拼接后返回，而流式输出可以实时地将中间结果返回，您可以在模型进行输出的同时进行阅读，减少等待模型回复的时间。

```python
import dashscope

messages = [
    {
        "role": "user",
        "content": [
            {"audio": "https://dashscope.oss-cn-beijing.aliyuncs.com/audios/welcome.mp3"},
            {"text": "这段音频在说什么?"}
        ]
    }
]

response = dashscope.MultiModalConversation.call(
    model="qwen-audio-turbo-latest", 
    messages=messages,
    stream=True,
    incremental_output=True,
    result_format="message"
    )
for chunk in response:
    print(chunk)
```
响应示例

 
```json
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "这段"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 1, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "音频"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 2, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "说的是"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 3, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": []}}]}, "usage": {"input_tokens": 33, "output_tokens": 3, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": ":'欢迎"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 5, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "使用"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 6, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "阿里"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 7, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "云"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 8, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": []}}]}, "usage": {"input_tokens": 33, "output_tokens": 8, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": []}}]}, "usage": {"input_tokens": 33, "output_tokens": 8, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "null", "message": {"role": "assistant", "content": [{"text": "'"}]}}]}, "usage": {"input_tokens": 33, "output_tokens": 10, "audio_tokens": 85}}
{"status_code": 200, "request_id": "f877cf8d-6109-9e84-b68f-9c618e0975fe", "code": "", "message": "", "output": {"text": null, "finish_reason": null, "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": []}}]}, "usage": {"input_tokens": 33, "output_tokens": 10, "audio_tokens": 85}}
```
### 语音对话
您可以直接用语音向模型发出指令，无需输入文本指令。例如：如果音频中包含内容“这种环境下适合做什么”，模型会回复适合做的事情，而不是返回这段语音的文本。

目前qwen-audio-turbo-latest、qwen-audio-turbo-2024-12-04、qwen2-audio-instruct模型支持语音聊天。

```python 
import dashscope

messages = [
    {
        "role": "user",
        "content": [
            {"audio": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20240916/kvkadk/%E6%8E%A8%E8%8D%90%E4%B9%A6.wav"}
        ]
    }
]

response = dashscope.MultiModalConversation.call(model='qwen-audio-turbo-latest', messages=messages)
print(response)
```

响应示例

```json 
{
  "status_code": 200,
  "request_id": "84f2bfbe-71a0-9291-b711-bdc615b5aea3",
  "code": "",
  "message": "",
  "output": {
    "text": null,
    "finish_reason": null,
    "choices": [
      {
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": [
            {
              "text": "当然可以，不过需要先了解你的兴趣方向。你喜欢哪种类型的文学作品呢？比如小说、散文、诗歌还是戏剧？"
            }
          ]
        }
      }
    ]
  },
  "usage": {
    "input_tokens": 28,
    "output_tokens": 28,
    "audio_tokens": 237
  }
}
```
支持的音频文件
音频文件大小不超过10 MB。

音频的时长建议不超过30秒，如果超过30秒，模型会自动截取前30秒的音频。

音频文件的格式支持大部分常见编码的音频格式，例如AMR、WAV（CodecID: GSM_MS）、WAV（PCM）、3GP、3GPP、AAC、MP3等。

音频中支持的语言包括中文、英语、粤语、法语、意大利语、西班牙语、德语和日语。