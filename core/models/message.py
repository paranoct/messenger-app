from datetime import datetime

class Message:
    def __init__(self, id: int, chat_id: int, sender_id: int, text: str, created_at: datetime):
        if not text or not text.strip():
            raise ValueError("Сообщение не может быть пустым")
        self.id = id
        self.chat_id = chat_id
        self.sender_id = sender_id
        self.text = text.strip()
        self.created_at = created_at
