# 如何使用
文本生成模型将接收的信息作为提示（Prompt），并返回一个根据提示信息生成的输出。

本文以调用通义千问模型为例，介绍如何使用文本生成模型。

# 消息类型
您通过API与大模型进行交互时的输入和输出也被称为消息（Message）。每条消息都属于一个角色（Role），角色包括系统（System）、用户（User）和助手（Assistant）。

- 系统消息（System Message，也称为 System Prompt）：用于告知模型要扮演的角色或行为。例如，您可以让模型扮演一个严谨的科学家等。默认值是“You are a helpful assistant”。您也可以将此类指令放在用户消息中，但放在系统消息中会更有效。

- 用户消息（User Message）：您输入给模型的文本。

- 助手消息（Assistant Message）：模型的回复。您也可以预先填写助手消息，作为后续助手消息的示例。

# 快速开始
API 使用前提：

已获取API Key并完成配置API Key到环境变量。

已安装SDK。

## 示例代码
```python 
import os
from dashscope import Generation

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "你是谁？"},
]
response = Generation.call(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-plus",
    messages=messages,
    result_format="message",
)

if response.status_code == 200:
    print(response.output.choices[0].message.content)
else:
    print(f"HTTP返回码：{response.status_code}")
    print(f"错误码：{response.code}")
    print(f"错误信息：{response.message}")
    print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
```
## 返回结果
``` 
我是通义千问，由阿里云开发的AI助手。我被设计用来回答各种问题、提供信息和与用户进行对话。有什么我可以帮助你的吗？
```
# 异步调用
您可以使用Asyncio接口调用实现并发，提高程序的效率。示例代码如下：
``` python
import asyncio
import platform
from dashscope.aigc.generation import AioGeneration
import os

# 定义异步任务列表
async def task(question):
    print(f"Sending question: {question}")
    response = await AioGeneration.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model="qwen-plus",  # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        prompt=question
        )
    print(f"Received answer: {response.output.text}")

# 主异步函数
async def main():
    questions = ["你是谁？", "你会什么？", "天气怎么样？"]
    tasks = [task(q) for q in questions]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    # 设置事件循环策略
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # 运行主协程
    asyncio.run(main(), debug=False)
```

# 控制生成的常用参数
Temperature 和 top_p

这两个参数都用于控制模型生成文本的多样性。temperature 或 top_p 越高，生成的文本更多样，反之生成的文本更确定。

具有多样性的文本，适用于创意写作（如小说、广告文案）、头脑风暴、聊天应用等场景。

具有确定性的文本，适用于有明确答案（如问题分析、选择题、事实查询）或要求用词准确（如技术文档、法律文本、新闻报导、学术论文）的场景。

## 原理介绍

- **temperature**

    temperature 越高，Token 概率分布变得更平坦（即高概率 Token 的概率降低，低概率 Token 的概率上升），使得模型在选择下一个 Token 时更加随机。

    temperature 越低，Token 概率分布变得更陡峭（即高概率 Token 被选取的概率更高，低概率 Token 的概率更低），使得模型更倾向于选择高概率的少数 Token。

- **top_p**

    top_p 采样是指从最高概率（最核心）的 Token 集合中进行采样。它将所有可能的下一个 Token 按概率从高到低排序，然后从概率最高的 Token 开始累加概率，直至概率总和达到阈值（例如80%，即 top_p=0.8），最后从这些概率最高、概率总和达到阈值的 Token 中随机选择一个用于输出。

    top_p 越高，考虑的 Token 越多，因此生成的文本更多样。

    top_p 越低，考虑的 Token 越少，因此生成的文本更集中和确定。

# 多轮对话
实现多轮对话的关键在于维护一个 messages 数组，您可以将每一轮的对话历史以及新的指令以{"role": "xxx", "content": "xxx"}的形式添加到 messages 数组中，从而使大模型可以参考历史对话信息进行回复。

示例代码以手机商店导购为例，导购与顾客会进行多轮对话来采集购买意向，采集完成后会结束会话。

```python 
import os
from dashscope import Generation
import dashscope

def get_response(messages):
    response = Generation.call(
        # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model="qwen-plus",
        messages=messages,
        result_format="message",
    )
    return response

# 初始化一个 messages 数组
messages = [
    {
        "role": "system",
        "content": """你是一名阿里云百炼手机商店的店员，你负责给用户推荐手机。手机有两个参数：屏幕尺寸（包括6.1英寸、6.5英寸、6.7英寸）、分辨率（包括2K、4K）。
        你一次只能向用户提问一个参数。如果用户提供的信息不全，你需要反问他，让他提供没有提供的参数。如果参数收集完成，你要说：我已了解您的购买意向，请稍等。""",
    }
]

assistant_output = "欢迎光临阿里云百炼手机商店，您需要购买什么尺寸的手机呢？"
print(f"模型输出：{assistant_output}\n")
while "我已了解您的购买意向" not in assistant_output:
    user_input = input("请输入：")
    # 将用户问题信息添加到messages列表中
    messages.append({"role": "user", "content": user_input})
    assistant_output = get_response(messages).output.choices[0].message.content
    # 将大模型的回复信息添加到messages列表中
    messages.append({"role": "assistant", "content": assistant_output})
    print(f"模型输出：{assistant_output}")
    print("\n")
```

# 流式输出
开始使用
对于 Qwen3 开源版、QwQ 商业版与开源版、QVQ 模型，仅支持流式输出方式调用。
OpenAI兼容DashScope
您可以通过DashScope SDK或HTTP方式使用流式输出的功能。Python SDK 需要设置 stream参数为 True；

流式输出的内容默认是非增量式（即每次返回的内容都包含之前生成的内容），如果您需要使用增量式流式输出，请设置`incremental_output`参数为 true 。

```python 
import os
from dashscope import Generation


messages = [
    {'role':'system','content':'you are a helpful assistant'},
    {'role': 'user','content': '你是谁？'}]
responses = Generation.call(
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen-plus", # 此处以qwen-plus为例，您可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=messages,
    result_format='message',
    stream=True,
    # 增量式流式输出
    incremental_output=True,
    # Qwen3模型通过enable_thinking参数控制思考过程（开源版默认True，商业版默认False）
    # 使用Qwen3开源版模型时，若未启用流式输出，请将下行取消注释，否则会报错
    # enable_thinking=False
    )
full_content = ""
print("流式输出内容为：")
for response in responses:
    full_content += response.output.choices[0].message.content
    print(response.output.choices[0].message.content)
print(f"完整内容为：{full_content}")
```
## 返回结果

 
流式输出内容为：
```
我是来自
阿里
云
的大规模语言模型
，我叫通
义千问。
```
完整内容为：`我是来自阿里云的大规模语言模型，我叫通义千问。`
