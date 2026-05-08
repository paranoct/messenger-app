from datetime import datetime

class MessageService:
    PUBLIC_ERROR = "Операция не выполнена"

    def __init__(self, msg_repo):
        self.msg_repo = msg_repo

    def create_message(self, chat_id: int, sender_id: int, text: str):
        try:
            message = self.msg_repo.add_message(chat_id, sender_id, text, datetime.now())
            return message
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

    def get_message(self, message_id):
        try:
            return self.msg_repo.get_message_by_id(message_id)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

    def _delete_message(self, message_id, current_user_id):
        try:
            message = self.msg_repo.get_message_by_id(message_id)
            if message.sender_id != current_user_id:
                raise ValueError

            self.msg_repo.delete_message(message_id=message_id)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)


    def get_messages_by_chat_id(self, chat_id):
        try:
            return self.msg_repo.list_messages_for_chat(chat_id=chat_id)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)
