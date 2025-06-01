#!/usr/bin/env python3
"""
测试音色创建接口的脚本
使用前请确保：
1. 设置了DASHSCOPE_API_KEY环境变量
2. 服务器正在运行
3. 有有效的JWT token
"""

import requests
import json
import os

# 配置
BASE_URL = "http://localhost:3000"
JWT_TOKEN = "your_jwt_token_here"  # 请替换为实际的JWT token

def test_voice_creation():
    """测试音色创建接口"""
    
    # 1. 首先上传一个音频文件
    print("1. 上传音频文件...")
    upload_url = f"{BASE_URL}/api/file/upload"
    
    # 这里使用一个示例音频文件，请替换为实际的音频文件路径
    audio_file_path = "sample_audio.mp3"  # 请替换为实际的音频文件路径
    
    if not os.path.exists(audio_file_path):
        print(f"错误：音频文件 {audio_file_path} 不存在")
        print("请提供一个有效的音频文件路径")
        return
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}'
    }
    
    with open(audio_file_path, 'rb') as f:
        files = {'file': ('sample.mp3', f, 'audio/mpeg')}
        data = {
            'is_public': 'false',
            'description': '音色训练样本'
        }
        
        response = requests.post(upload_url, files=files, data=data, headers=headers)
    
    if response.status_code != 201:
        print(f"文件上传失败: {response.status_code}")
        print(response.text)
        return
    
    upload_result = response.json()
    audio_file_id = upload_result.get('file_id')
    print(f"文件上传成功，文件ID: {audio_file_id}")
    
    # 2. 创建音色
    print("\n2. 创建音色...")
    create_voice_url = f"{BASE_URL}/api/voice/create_voice"
    
    voice_data = {
        "audio_file_id": audio_file_id,
        "voice_name": "测试音色",
        "voice_gender": "female",
        "voice_description": "这是一个测试音色",
        "is_public": False
    }
    
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(create_voice_url, json=voice_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("音色创建成功！")
        print(f"音色ID: {result['voice']['voice_id']}")
        print(f"DashScope音色ID: {result['dashscope_voice_id']}")
        print(f"试听音频ID: {result['voice']['voice_audition_url']}")
        
        # 3. 下载试听音频
        print("\n3. 下载试听音频...")
        audition_url = f"{BASE_URL}/api/file/download/{result['voice']['voice_audition_url']}"
        
        response = requests.get(audition_url, headers={'Authorization': f'Bearer {JWT_TOKEN}'})
        
        if response.status_code == 200:
            with open('audition_sample.mp3', 'wb') as f:
                f.write(response.content)
            print("试听音频下载成功: audition_sample.mp3")
        else:
            print(f"试听音频下载失败: {response.status_code}")
    else:
        print(f"音色创建失败: {response.status_code}")
        print(response.text)

def test_get_voices():
    """测试获取音色列表接口"""
    print("\n4. 获取音色列表...")
    
    get_voices_url = f"{BASE_URL}/api/voice/get_voices"
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "page": 1,
        "page_size": 10,
        "created_by_current_user": True
    }
    
    response = requests.post(get_voices_url, json=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"获取到 {len(result.get('voices', []))} 个音色")
        for voice in result.get('voices', []):
            print(f"- {voice['voice_name']} ({voice['voice_gender']}) - {voice['voice_description']}")
    else:
        print(f"获取音色列表失败: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("音色创建接口测试")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("警告：未设置DASHSCOPE_API_KEY环境变量")
        print("请设置: export DASHSCOPE_API_KEY='your_api_key'")
    
    if JWT_TOKEN == "your_jwt_token_here":
        print("错误：请在脚本中设置有效的JWT_TOKEN")
        exit(1)
    
    try:
        test_voice_creation()
        test_get_voices()
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 