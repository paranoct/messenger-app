class User:
    def __init__(self, id, username, email, password_hash):
        if not username or not username.strip():
            raise ValueError("Логин не может быть пустым")
        if not email or not email.strip():
            raise ValueError("Электронная почта не может быть пустой")
        if not password_hash or not password_hash.strip():
            raise ValueError("Хеш пароля не может быть пустым")

        self.id = id
        self.username = username.strip()
        self.email = email.strip()
        self.password_hash = password_hash.strip()


class PublicUser:
    def __init__(self, id, username, email=None):
        if not username or not username.strip():
            raise ValueError("Логин не может быть пустым")

        self.id = id
        self.username = username.strip()
        self.email = email.strip() if email is not None else None
