class User:
    def __init__(self, id, username, email):
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")
        if not email or not email.strip():
            raise ValueError("E-mail cannot be empty")

        self.id = id
        self.username = username.strip()
        self.email = email.strip()