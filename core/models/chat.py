class Chat:
    def __init__(self, id: int, name: str):
        if not name or not name.strip():
            raise ValueError("Название чата не может быть пустым")

        self.id = id
        self.name = name.strip()

