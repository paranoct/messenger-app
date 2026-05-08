from core.models.user import PublicUser, User
import hashlib
import hmac
import secrets

class UserService:
    PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
    PASSWORD_HASH_ITERATIONS = 200_000
    PUBLIC_ERROR = "Операция не выполнена"
    AUTH_ERROR = "Неверные учетные данные"
    INVALID_INPUT_ERROR = "Некорректные данные"

    def __init__(self, repo):
        self.users_repo = repo
        self.special_symbols = set("-_+=@#№%\"'!:;.,/?*()[]{}|")

    def register(self, username:str, email: str, password: str):
        return self.create_user(username, email, password)

    def login(self, username: str, password: str):
        try:
            username = self.validate_username(username)
            if not isinstance(password, str):
                raise ValueError
            password = password.strip()
            user = self.users_repo.get_user_by_name(username)
        except Exception:
            raise ValueError(self.AUTH_ERROR)

        if user is None or not self.verify_password(password, user.password_hash):
            raise ValueError(self.AUTH_ERROR)
        return self.to_public_user_model(user)

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            self.PASSWORD_HASH_ITERATIONS
        ).hex()
        return f"{self.PASSWORD_HASH_ALGORITHM}${self.PASSWORD_HASH_ITERATIONS}${salt}${digest}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt, saved_digest = password_hash.split("$")
            iterations = int(iterations)
            if algorithm != self.PASSWORD_HASH_ALGORITHM:
                return False

            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt),
                iterations
            ).hex()
        except (AttributeError, TypeError, ValueError):
            return False
        return hmac.compare_digest(digest, saved_digest)

    def validate_password(self, password):
        if not isinstance(password,str):
            raise ValueError(self.INVALID_INPUT_ERROR)
        password = password.strip()

        if len(password) < 6:
            raise ValueError(self.INVALID_INPUT_ERROR)

        has_digit = False
        has_letter = False
        has_special = False

        for ch in password:
            if ch.isdigit():
                has_digit = True
            elif ch.isalpha():
                has_letter = True
            elif ch in self.special_symbols:
                has_special = True

        if not has_digit:
            raise ValueError(self.INVALID_INPUT_ERROR)

        if not has_letter:
            raise ValueError(self.INVALID_INPUT_ERROR)

        if not has_special:
            raise ValueError(self.INVALID_INPUT_ERROR)

        return password


    def validate_username(self, username):
        if not isinstance(username, str):
            raise ValueError(self.INVALID_INPUT_ERROR)
        username = username.strip()
        if username == "" or len(username) < 4:
            raise ValueError(self.INVALID_INPUT_ERROR)
        return username

    def validate_email(self, email):
        if not isinstance(email, str):
            raise ValueError(self.INVALID_INPUT_ERROR)
        email = email.strip()
        at_idx = email.find("@")
        dot_idx = email.rfind(".")
        if not (at_idx > 0 and dot_idx > at_idx + 1 and dot_idx < len(email) - 1):
            raise ValueError(self.INVALID_INPUT_ERROR)
        return email

    def create_user(self, username: str, email: str, password: str):
        username = self.validate_username(username)
        email = self.validate_email(email)
        password = self.validate_password(password)
        password_hash = self.hash_password(password)
        try:
            user = self.users_repo.add_user(username, email, password_hash)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)
        return self.to_public_user_model(user)

    def get_user(self, id_or_name):
        try:
            id_or_name = str(id_or_name).strip()

            user = self.users_repo.get_user_by_name(id_or_name)
            if user:
                return self.to_public_user_model(user)

            if id_or_name.isdigit():
                user_id = int(id_or_name)
                user = self.users_repo.get_user_by_id(user_id)
                if user:
                    return self.to_public_user_model(user)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

        raise ValueError(self.PUBLIC_ERROR)

    def get_user_by_username(self, username):
        try:
            username = self.validate_username(username)
            user = self.users_repo.get_user_by_name(username)
            if user is None:
                raise ValueError
            return self.to_public_user_model(user)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

    def to_public_user(self, user: User, include_email=False):
        public_user = {
            "id": user.id,
            "username": user.username,
        }
        if include_email:
            public_user["email"] = user.email
        return public_user

    def to_public_user_model(self, user: User):
        return PublicUser(
            id=user.id,
            username=user.username,
            email=user.email,
        )

    def get_public_user(self, id_or_name, include_email=False):
        try:
            user = self.get_user(id_or_name)
            return self.to_public_user(user, include_email=include_email)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

    def list_public_users(self, include_email=False):
        try:
            return [
                self.to_public_user(user, include_email=include_email)
                for user in self.users_repo.list_users()
            ]
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

    def delete_account(self, current_user_id, input_password, user: User = None):
        try:
            if user is not None and current_user_id != user.id:
                raise ValueError
            if not isinstance(input_password, str):
                raise ValueError

            input_password = input_password.strip()
            user_from_db = self.users_repo.get_user_by_id(current_user_id)
            if not self.verify_password(input_password, user_from_db.password_hash):
                raise ValueError

            self.users_repo.delete_user(user_from_db)
        except Exception:
            raise ValueError(self.PUBLIC_ERROR)

    def list_users(self):
        return self.list_public_users()
