import uuid
import io
import logging

from pydub import AudioSegment
from typing import List, Dict, Any

from app.models.conversation_model import Conversation
from app.models.message_model import Message
from app.models.ai_role_model import AIRole
from app.models.voice_model import Voice
from app import db

from app.file import get_file_path_type, temp_file_manager

logger = logging.getLogger(__name__)

class SessionInfo:
    def __init__(
            self,
            conversation_id: str, 
            voice_id: str,
            speech_rate: float, 
            pitch_rate: float, 
            image_id: str,
            mode: str,
        ):
        self.conversation_id = conversation_id
        
        conversation: Conversation = Conversation.query.filter_by(conversation_id=uuid.UUID(conversation_id).bytes).first()
        history_messages: List[Message] = Message.query.filter_by(conversation_id=uuid.UUID(conversation_id).bytes).order_by(Message.created_at.asc()).all()
        self.messages = []
        if history_messages:
            for message in history_messages:
                match message.type:
                    case "text":
                        if message.is_user:
                            self.messages.append({
                                "role": "user",
                                "content": [{"text": message.content}]
                            })
                        else:
                            self.messages.append({
                                "role": "assistant",
                                "content": [{"text": message.content}]
                            })
                    case _:
                        self.messages.append({
                            "role": "user",
                            "content": [{"text": message.content}]
                        })
        
        role: AIRole = AIRole.query.filter_by(role_id=conversation.role_id).first()
        match role.gender:
            case "male":
                gender_str = "你是一个男性。"
            case "female":
                gender_str = "你是一个女性。"
            case "other":
                gender_str = "你可以是任何性别。"
        age_str = "" if role.age is None else f"你的年龄是：{role.age}岁。"
        response_language = "中文" if role.response_language == "chinese" else "英文"
        system_prompt = f"""
            你将按照以下要求扮演角色与用户对话。
            你的名字:{role.name}。
            {gender_str}{age_str}
            你的性格要求:{role.personality}。
            你应该使用{response_language}与用户交流。
        """
        self.messages.append = {
            "role": "system", 
            "content": [{"text": system_prompt}]
        }
        
        
        voice: Voice = Voice.query.filter_by(voice_id=uuid.UUID(voice_id).bytes).first()
        self.voice_name = voice.name
        self.voice_call_name = voice.call_name
        self.speech_rate = speech_rate
        self.pitch_rate = pitch_rate
        self.image_id = image_id
        self.temp_files = [image_id]

        self.mode: str = mode

        self.audio_chunks: List[bytes] = []

        self.task_info: Dict[str, Any] = {}

        self.audio_id: str = None

    def add_audio_chunk(self, chunk: bytes):
        self.audio_chunks.append(chunk)

    def save_audio_chunks(self, is_response: bool = False):
        if len(self.audio_chunks) > 0:
            try:
                audio_file_path, audio_file_type = get_file_path_type("audio.mp3")
                # 创建空的AudioSegment
                combined = AudioSegment.empty()
                
                # 添加每个块
                for chunk in self.audio_chunks:
                    # 从二进制数据创建AudioSegment
                    segment = AudioSegment.from_file(io.BytesIO(chunk), format="mp3")
                    combined += segment
                
                # 导出到文件
                combined.export(audio_file_path, format="mp3")
                self.audio_chunks.clear()

                audio_id = temp_file_manager.add_file(audio_file_path, "audio.wav", audio_file_type)
                self.temp_files.append(audio_id)
                if is_response:
                    self.audio_id = audio_id
                    return True

                audio_file_path = f"file:/{audio_file_path}"
                self.messages.append({
                    "role": "user",
                    "content": [{"audio": audio_file_path}]
                })
                return True
            except Exception as e:
                logger.error(f"保存音频块失败: {e}")
                return False
        return False
    
    def add_message(self, role: str, type: str, content: str):
        self.messages.append({
            "role": role,
            "content": [{type: content}]
        })

    def change_voice(self, voice_id: str, speech_rate: float, pitch_rate: float) -> bool:
        try:
            voice: Voice = Voice.query.filter_by(voice_id=uuid.UUID(voice_id).bytes).first()
            self.voice_id = voice_id
            self.voice_name = voice.name
            self.voice_call_name = voice.call_name
            self.speech_rate = speech_rate
            self.pitch_rate = pitch_rate
        except Exception as e:
            logger.error(f"更换语音失败: {e}")
            return False
        return True
    
    def insert_final_message(self, text: str) -> bool:
        try:
            message = Message(self.conversation_id, self.mode, text, True)
            db.session.add(message)
            db.session.commit()
        except Exception as e:
            logger.error(f"插入最终消息失败: {e}")
            return False
        return True

session_manager: Dict[str, SessionInfo] = {}
    
    


