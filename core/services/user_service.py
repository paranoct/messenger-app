from core.models.user import User
class UserService:
    def __init__(self, repo):
        self.users_repo = repo
    
    def validate_username(self, username):
        username = username.strip()
        if username == "" or len(username) < 4:
            raise ValueError("Невалидное имя пользователя. Минимальная длина логина 4 символа")
        return username

    def validate_email(self, email):
        email = email.strip()
        at_idx = email.find("@")
        dot_idx = email.rfind(".")
        if not (at_idx > 0 and dot_idx > at_idx + 1 and dot_idx < len(email) - 1):
            raise ValueError("Введенный email адрес не существует")
        return email

    def create_user(self, username: str, email: str):
        username = self.validate_username(username)
        email = self.validate_email(email)
        user = self.users_repo.add_user(username, email)
        return user

    def get_user(self, id_or_name):
        id_or_name = str(id_or_name).strip()

        user = self.users_repo.get_user_by_name(id_or_name)
        if user:
            return user

        if id_or_name.isdigit():
            user_id = int(id_or_name)
            user = self.users_repo.get_user_by_id(user_id)
            if user:
                return user
            
        raise ValueError("User with given id or name was not found")
    
    def list_users(self):
        return self.users_repo.list_users()
