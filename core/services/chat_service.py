from core.models.chat import Chat

class ChatService:
    PUBLIC_ERROR = "Операция не выполнена"

    def __init__(self, repo, message_service, memb_repo):
        self.chat_repo = repo
        self.chat_members_repo = memb_repo
        self.message_service = message_service

    def _raise_public_error(self):
        raise ValueError(self.PUBLIC_ERROR)

    def _ensure_chat_access(self, chat_id: int, current_user_id: int):
        try:
            chat = self.chat_repo.get_chat_by_id(chat_id)
            has_access = self.chat_members_repo.is_user_in_chat(chat_id, current_user_id)
        except Exception:
            self._raise_public_error()

        if chat is None or not has_access:
            self._raise_public_error()
        return chat

    def send_message(self, chat_id: int, text: str, current_user_id: int):
        self._ensure_chat_access(chat_id, current_user_id)
        try:
            return self.message_service.create_message(chat_id, current_user_id, text)
        except Exception:
            self._raise_public_error()

    def get_messages(self, chat_id: int, current_user_id: int):
        self._ensure_chat_access(chat_id, current_user_id)
        try:
            return self.message_service.get_messages_by_chat_id(chat_id)
        except Exception:
            self._raise_public_error()

    def delete_message(self, current_user_id, chat_id, message_id):
        try:
            self._ensure_chat_access(chat_id, current_user_id)
            message = self.message_service.get_message(message_id)

            if message.chat_id != chat_id:
                self._raise_public_error()

            self.message_service._delete_message(message_id, current_user_id)
        except Exception:
            self._raise_public_error()

    def create_chat(self, name: str, current_user_id:int):
        try:
            return self.chat_repo.add_chat_with_owner(name, current_user_id)
        except Exception:
            self._raise_public_error()

    def get_chat(self, id_or_name, current_user_id):
        try:
            id_or_name = str(id_or_name).strip()

            if id_or_name.isdigit():
                chat_id = int(id_or_name)
                chat = self.chat_repo.get_chat_by_id(chat_id)
                if chat:
                    self._ensure_chat_access(chat.id, current_user_id)
                    return chat.id

            chat = self.chat_repo.get_chat_by_name_for_user(id_or_name, current_user_id)
            if chat:
                return chat.id
        except Exception:
            self._raise_public_error()

        self._raise_public_error()

    def list_chats(self, current_user_id):
        try:
            return self.chat_repo.list_chats(current_user_id)
        except Exception:
            self._raise_public_error()

    def list_members(self, current_user_id, chat_id):
        try:
            self._ensure_chat_access(chat_id, current_user_id)
            members = self.chat_members_repo.list_members_by_chat_id(chat_id)
            return [
                {
                    "id": member.id,
                    "username": member.username,
                    "role": self.chat_members_repo.get_user_role(chat_id, member.id),
                }
                for member in members
            ]
        except Exception:
            self._raise_public_error()

    def add_user_to_chat(self, current_user_id, chat_id, target_user_id, role="member"):
        try:
            self._ensure_chat_access(chat_id, current_user_id)
            current_user_role = self.chat_members_repo.get_user_role(chat_id, current_user_id)

            if current_user_role not in ("owner", "admin"):
                self._raise_public_error()

            role = str(role).strip()
            if role == "owner":
                self._raise_public_error()

            if current_user_role == "admin" and role != "member":
                self._raise_public_error()

            self.chat_members_repo.add_user_to_chat(
                user_id=target_user_id,
                chat_id=chat_id,
                role=role,
            )
        except Exception:
            self._raise_public_error()

    def delete_chat(self, current_user_id, chat_id):
        try:
            chat = self._ensure_chat_access(chat_id, current_user_id)

            if not self.chat_members_repo.is_chat_owner(chat_id, current_user_id):
                self._raise_public_error()

            self.chat_repo.delete_chat(chat)
        except Exception:
            self._raise_public_error()

    def remove_user_from_chat(self, current_user_id, chat_id, target_user_id):
        try:
            self._ensure_chat_access(chat_id, current_user_id)

            current_user_role = self.chat_members_repo.get_user_role(chat_id, current_user_id)
            target_user_role = self.chat_members_repo.get_user_role(chat_id, target_user_id)

            if target_user_role is None:
                self._raise_public_error()

            if current_user_id == target_user_id:
                self._raise_public_error()

            if current_user_role == "owner":
                if target_user_role == "owner":
                    self._raise_public_error()
            elif current_user_role == "admin":
                if target_user_role != "member":
                    self._raise_public_error()
            else:
                self._raise_public_error()

            self.chat_members_repo.delete_user_from_chat(chat_id, target_user_id)
        except Exception:
            self._raise_public_error()

    def change_user_role(self, current_user_id, chat_id, target_user_id, role):
        try:
            self._ensure_chat_access(chat_id, current_user_id)

            role = str(role).strip()
            if role == "owner" or role not in ("admin", "member"):
                self._raise_public_error()

            current_user_role = self.chat_members_repo.get_user_role(chat_id, current_user_id)
            target_user_role = self.chat_members_repo.get_user_role(chat_id, target_user_id)

            if current_user_role != "owner":
                self._raise_public_error()

            if target_user_role is None:
                self._raise_public_error()

            if current_user_id == target_user_id:
                self._raise_public_error()

            if target_user_role == "owner":
                self._raise_public_error()

            self.chat_members_repo.change_user_role(chat_id, target_user_id, role)
        except Exception:
            self._raise_public_error()
