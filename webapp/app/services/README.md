# EchoMimic Services 模块使用指南

本模块封装了与阿里云DashScope API交互的服务，包括语音识别(ASR)、文本生成(LLM)和语音合成(TTS)功能，支持多种调用方式，特别优化了流式处理以降低系统延迟。

## 目录

- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [核心服务](#核心服务)
  - [AliyunAPIService](#aliyunapiservice)
  - [WebSocketAudioPlayer](#websocketaudioplayer)
  - [FileWriterCallback](#filewritercallback)
- [使用场景示例](#使用场景示例)
  - [语音转文字](#语音转文字)
  - [文字转语音](#文字转语音)
  - [流式大模型+语音合成](#流式大模型语音合成)
- [前端集成指南](#前端集成指南)

## 快速开始

```python
from webapp.app.services import AliyunAPIService, WebSocketAudioPlayer

# 创建服务实例
aliyun_service = AliyunAPIService()

# 语音识别
text = aliyun_service.recognize_audio("https://example.com/audio.wav")
print(f"识别结果: {text}")

# 文字转语音（同步方式）
audio_url = aliyun_service.synthesize_speech("你好，这是一条测试消息")
print(f"语音文件URL: {audio_url}")

# 流式大模型+语音合成（低延迟）
def on_audio_chunk(audio_data):
    # 处理音频数据块...
    pass
    
aliyun_service.stream_llm_with_tts(
    prompt="给我讲个笑话",
    on_audio_chunk=on_audio_chunk
)
```

## 环境配置

1. **DashScope API Key**: 需要设置环境变量 `DASHSCOPE_API_KEY` 或在初始化时传入

   ```python
   # 通过环境变量
   # export DASHSCOPE_API_KEY=your_api_key
   
   # 或通过代码传入
   service = AliyunAPIService(api_key="your_api_key")
   ```

2. **临时文件存储**: 配置临时音频文件存储路径，设置环境变量 `TMP_DIR`（默认为 `tmp/audio`）

3. **文件URL前缀**: 配置公共访问URL前缀，设置环境变量 `BASE_URL`

## 核心服务

### AliyunAPIService

封装阿里云DashScope API调用的主服务类。

#### 初始化

```python
service = AliyunAPIService(api_key=None)  # 可选参数，如不提供则从环境变量获取
```

#### 主要方法

1. **recognize_audio**: 调用阿里云Qwen-Audio多模态大模型进行语音理解和识别
   ```python
   text = service.recognize_audio(
       audio_url,       # 音频文件URL
       prompt=None      # 可选的文本提示，引导模型理解
   )
   ```

2. **synthesize_speech**: 调用阿里云CosyVoice进行文本转语音(TTS)，使用同步方式
   ```python
   audio_url = service.synthesize_speech(
       text,           # 要转换为语音的文本
       voice_id=None   # 可选的音色ID
   )
   ```

3. **synthesize_speech_async**: 异步方式进行TTS，使用回调函数接收结果
   ```python
   service.synthesize_speech_async(
       text,           # 要转换为语音的文本
       voice_id=None,  # 可选的音色ID
       on_complete=lambda url: print(f"完成: {url}"),  # 完成时的回调
       on_error=lambda msg: print(f"错误: {msg}")      # 出错时的回调
   )
   ```

4. **synthesize_speech_streaming**: 流式处理方式进行TTS，需要自定义回调处理类
   ```python
   custom_callback = MyCustomCallback()  # 实现ResultCallback接口
   service.synthesize_speech_streaming(
       text,               # 要转换为语音的文本
       voice_id=None,      # 可选的音色ID
       callback=custom_callback  # 自定义回调处理类
   )
   ```

5. **stream_llm_with_tts**: 调用大语言模型生成回复并实时进行语音合成（低延迟）
   ```python
   service.stream_llm_with_tts(
       prompt,                # 用户输入的问题或指令
       system_prompt=None,    # 系统提示，引导大语言模型的行为
       voice_id=None,         # 语音合成使用的音色ID
       llm_model="qwen-turbo",  # 使用的大语言模型
       tts_model="cosyvoice-v2", # 使用的语音合成模型
       on_text_chunk=lambda text: print(f"文本块: {text}"),  # 文本块回调
       on_audio_chunk=lambda data: process_audio(data),      # 音频块回调
       on_error=lambda msg: print(f"错误: {msg}"),           # 错误回调
       on_complete=lambda: print("处理完成")                 # 完成回调
   )
   ```

### WebSocketAudioPlayer

通过WebSocket将音频数据实时传送给前端的播放器，适用于实时语音交互场景。

#### 初始化

```python
player = WebSocketAudioPlayer(
    socket_emit_func,  # SocketIO emit函数
    session_id,        # 会话ID
    event_name="audio_chunk"  # 事件名称前缀
)
```

#### 主要方法

1. **start**: 开始音频流处理
   ```python
   player.start()  # 初始化并发送开始事件
   ```

2. **write**: 写入音频数据并发送给客户端
   ```python
   player.write(audio_data)  # 写入音频数据字节
   ```

3. **stop**: 停止音频流处理并发送结束信号
   ```python
   player.stop()  # 发送结束事件
   ```

### FileWriterCallback

将语音合成结果写入文件的回调处理类。

#### 初始化

```python
callback = FileWriterCallback(
    on_complete_callback=lambda url: print(f"文件URL: {url}"),  # 完成回调
    on_error_callback=lambda msg: print(f"错误: {msg}")         # 错误回调
)
```

## 使用场景示例

### 语音转文字

```python
def process_user_audio(audio_url):
    service = AliyunAPIService()
    try:
        # 使用提示引导模型理解语音内容
        prompt = "请将这段语音准确转换为文字"
        text = service.recognize_audio(audio_url, prompt=prompt)
        return text
    except Exception as e:
        print(f"语音识别失败: {str(e)}")
        return None
```

### 文字转语音

```python
def generate_speech(text, voice_id=None):
    service = AliyunAPIService()
    
    # 同步方式
    try:
        audio_url = service.synthesize_speech(text, voice_id=voice_id)
        return audio_url
    except Exception as e:
        print(f"语音合成失败: {str(e)}")
        return None
        
    # 异步方式
    def on_complete(url):
        print(f"语音合成完成，URL: {url}")
        # 这里可以发送URL给客户端...
        
    def on_error(message):
        print(f"语音合成失败: {message}")
        
    service.synthesize_speech_async(
        text, 
        voice_id=voice_id,
        on_complete=on_complete,
        on_error=on_error
    )
```

### 流式大模型+语音合成

```python
def handle_user_query(query, session_id, socketio):
    service = AliyunAPIService()
    
    # 创建音频播放器
    player = WebSocketAudioPlayer(
        socket_emit_func=socketio.emit,
        session_id=session_id,
        event_name="tts_audio_chunk"
    )
    
    player.start()
    
    # 创建回调函数
    def on_text_chunk(text):
        # 实时发送文本给客户端显示
        socketio.emit('ai_text_chunk', {'text': text}, room=session_id)
        
    def on_audio_chunk(audio_data):
        # 通过WebSocketAudioPlayer发送音频数据
        player.write(audio_data)
        
    def on_error(message):
        socketio.emit('error', {'message': message}, room=session_id)
        player.stop()
        
    def on_complete():
        player.stop()
        socketio.emit('response_complete', {}, room=session_id)
    
    # 系统提示，引导AI的回复风格
    system_prompt = "你是一个友善的助手，请用简短、自然的语言回答用户问题"
    
    # 启动流式处理
    try:
        service.stream_llm_with_tts(
            prompt=query,
            system_prompt=system_prompt,
            on_text_chunk=on_text_chunk,
            on_audio_chunk=on_audio_chunk,
            on_error=on_error,
            on_complete=on_complete
        )
    except Exception as e:
        player.stop()
        socketio.emit('error', {'message': str(e)}, room=session_id)
```

## 前端集成指南

前端需要处理以下WebSocket事件以支持流式音频播放：

### 音频块事件

1. **tts_audio_chunk_start**: 初始化音频播放器
   ```javascript
   socket.on('tts_audio_chunk_start', function(data) {
     // 初始化音频播放器
     initAudioPlayer();
   });
   ```

2. **tts_audio_chunk**: 接收并播放音频块
   ```javascript
   socket.on('tts_audio_chunk', function(data) {
     // 解码Base64音频数据
     const audioData = atob(data.audio_data);
     
     // 将音频数据添加到音频播放器的缓冲区
     appendToAudioBuffer(audioData);
     
     // 如果尚未开始播放，启动播放
     if (!isPlaying) {
       startPlaying();
     }
   });
   ```

3. **tts_audio_chunk_end**: 处理播放结束
   ```javascript
   socket.on('tts_audio_chunk_end', function(data) {
     // 等待缓冲区播放完毕后关闭播放器
     onPlaybackComplete();
   });
   ```

### 音频播放器实现示例

```javascript
// 简单的示例实现
let audioContext = null;
let audioQueue = [];
let isPlaying = false;

function initAudioPlayer() {
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  audioQueue = [];
  isPlaying = false;
}

function appendToAudioBuffer(base64Data) {
  // 将Base64数据转换为二进制数组
  const byteCharacters = atob(base64Data);
  const byteArray = new Uint8Array(byteCharacters.length);
  
  for (let i = 0; i < byteCharacters.length; i++) {
    byteArray[i] = byteCharacters.charCodeAt(i);
  }
  
  // 添加到队列
  audioQueue.push(byteArray);
  
  // 如果未播放，开始播放
  if (!isPlaying) {
    playNextChunk();
  }
}

function playNextChunk() {
  if (audioQueue.length === 0) {
    isPlaying = false;
    return;
  }
  
  isPlaying = true;
  const chunk = audioQueue.shift();
  
  // 解码音频数据
  audioContext.decodeAudioData(chunk.buffer, function(buffer) {
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);
    
    // 播放完成后播放下一个
    source.onended = playNextChunk;
    source.start(0);
  });
}

function onPlaybackComplete() {
  // 完成所有播放后的清理工作
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
}
```

## 注意事项

1. **API密钥安全**: 避免在客户端代码中暴露API密钥，始终在服务器端管理
2. **异常处理**: 所有API调用都应有适当的错误处理机制
3. **临时文件管理**: 定期清理临时音频文件，避免磁盘空间耗尽
4. **流量控制**: 监控API使用情况，避免超出配额
5. **浏览器兼容性**: 流式音频播放在不同浏览器上可能需要不同处理方式 