class Chat:
    def __init__(self, id: int, name: str):
        if not name or not name.strip():
            raise ValueError("Chat name cannot be empty")

        self.id = id
        self.name = name.strip()    
    