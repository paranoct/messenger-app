from core.services import ChatService, MessageService, UserService
from core.repositories import SQLiteUsersRepository, SQLiteChatRepository, SQLiteMessagesRepository

def register(user_service):
    buf_username = None
    while buf_username is None:
        try:
            username = input("Введите ваш username: ").strip()
        except EOFError:
            return
        
        try:
            buf_username = user_service.validate_username(username)
        except ValueError as error:
            buf_username = None
            print(f"Ошибка: {error}")
    username = buf_username
    buf_email = None
    while buf_email is None:
        try:
            email = input("Введите ваш email: ").strip()
        except EOFError:
            return
        
        try:
            buf_email = user_service.validate_email(email)
        except ValueError as error:
            buf_email = None
            print(f"Ошибка: {error}")
    email = buf_email
    try:
        current_user = user_service.create_user(username, email)
    except ValueError as error:
        print(f"Ошибка: {error}")
        return register(user_service)
    current_user_id = current_user.id
    return current_user, current_user_id

def start_app():
    username = ""
    email = ""
    current_chat_id = None
    current_user_id = None
    chat_repo = SQLiteChatRepository()
    users_repo = SQLiteUsersRepository()
    msg_repo = SQLiteMessagesRepository()
    msg_service = MessageService(msg_repo=msg_repo)
    user_service = UserService(repo=users_repo)
    chat_service = ChatService(message_service=msg_service, repo=chat_repo)

    result = register(user_service)
    if result is None:
        return
    current_user, current_user_id = result
        
    
    print("Введите /help чтобы узнать список доступных команд")
    while True:
        try:
            command = input("\n> ").strip()
        except EOFError:
            print()
            break
        try:
            if command == "/help":
                print("""Вот список доступных команд:
/help - вывести список команд
/quit - завершить работу
/chat new - создать новый чат
/chat list - посмотреть список доступных чатов
/chat open - открыть чат по имени или id
/send - отправить в открытый чат сообщение
/messages - вывести историю сообщений""")
            elif command == "/chat new":
                print("Chat name cannot be empty")

            elif command.startswith("/chat new "):
                chat_name = command.removeprefix("/chat new ").strip()
                chat_service.create_chat(chat_name)

            elif command == "/chat list":
                chats = chat_service.list_chats()

                if not chats:
                    print("Чатов пока нет")
                else:
                    for chat in chats:
                        print(f"{chat.id}. {chat.name}")

            elif command == "/chat open":
                print("Chat id or name cannot be empty")

            elif command.startswith("/chat open "):
                chat_name_or_id = command.removeprefix("/chat open ").strip()
                current_chat_id = chat_service.get_chat(chat_name_or_id)
                
            elif command == "/send":
                print("Message cannot be empty")

            elif command.startswith("/send "):
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                text = command.removeprefix("/send ").strip()
                if text == "":
                    print("Message cannot be empty")
                    continue

                chat_service.send_message(chat_id=current_chat_id, sender_id=current_user_id, text=text)

            elif command == "/messages":
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                messages = chat_service.get_messages(current_chat_id)

                if not messages:
                    print("Сообщений пока нет")
                else:
                    for message in messages:
                        created_at = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{created_at}] {user_service.get_user(message.sender_id).username}: {message.text}")

            elif command == "/quit":
                break
            else:
                print("Command was not found in the list of avaliable commands. Print /help to see")

        except ValueError as error:
            print(f"Ошибка: {error}")

if __name__ == "__main__":
    start_app()
