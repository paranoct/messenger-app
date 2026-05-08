from core.services import create_services


def start_session(session_service, current_user):
    token = session_service.create_session(current_user.id)
    current_user_id = session_service.get_current_user_id(token)
    return token, current_user_id


def close_session(session_service, token):
    session_service.delete_session(token)


def resolve_user_id(user_service, id_or_name):
    return user_service.get_user(id_or_name).id


def resolve_username(user_service, username):
    return user_service.get_user_by_username(username).id


def print_members(members):
    if not members:
        print("Участников пока нет")
        return

    for member in members:
        print(f"{member['id']}. {member['username']} [{member['role']}]")


def register(user_service):
    while True:
        buf_username = None
        while buf_username is None:
            try:
                username = input("Введите ваш логин: ").strip()
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

        buf_password = None
        while buf_password is None:
            try:
                password = input("Введите ваш пароль: ").strip()
            except EOFError:
                return

            try:
                buf_password = user_service.validate_password(password)
            except ValueError as error:
                buf_password = None
                print(f"Ошибка: {error}")
        password = buf_password

        try:
            current_user = user_service.register(username, email, password)
        except ValueError as error:
            print(f"Ошибка: {error}")
            continue

        current_user_id = current_user.id
        return current_user, current_user_id

def login(user_service):
    while True:
        try:
            username = input("Введите ваш логин аккаунта: ").strip()
        except EOFError:
            return

        try:
            password = input("Введите пароль от вашего аккаунта: ").strip()
        except EOFError:
            return

        try:
            current_user = user_service.login(username, password)
        except ValueError as error:
            print(f"Ошибка: {error}")
            continue

        current_user_id = current_user.id
        return current_user, current_user_id

def delete_user(user_service, current_user, current_user_id):
    try:
        input_password = input("Введите пароль от удаляемого аккаунта для подтверджения действия: ").strip()
    except EOFError:
        return
    try:
        user_service.delete_account(current_user_id=current_user_id, user=current_user, input_password=input_password)
        return True
    except ValueError as error:
        print(f"Ошибка: {error}")
        return False

def choose(user_service):
    choose = None
    while choose is None:
        try:
            choose = input("(1) Войдите в аккаунт или (2) зарегистрируйтесь: ").strip()
        except EOFError:
            return
        if choose == "1":
            result = login(user_service)

            if result is None:
                return None
        elif choose == "2":
            result = register(user_service)

            if result is None:
                return None
        else:
            print("Неверная опция, выберите 1 - вход в аккаунт или 2 - регистрация")
            choose = None
    return result


def run_cli(user_service, chat_service, session_service):
    current_chat_id = None
    message_ids_by_number = {}
    current_session_token = None
    result = choose(user_service)
    if result is None:
        return
    current_user, current_user_id = result
    current_session_token, current_user_id = start_session(session_service, current_user)
    current_chat_id = None


    print("Введите /help чтобы узнать список доступных команд")
    while True:
        if current_user is None:
            result = choose(user_service)
            if result is None:
                return
            current_user, current_user_id = result
            current_session_token, current_user_id = start_session(session_service, current_user)
            current_chat_id = None
            message_ids_by_number = {}

        try:
            command = input("\n> ").strip()
        except EOFError:
            print()
            break
        try:
            try:
                current_user_id = session_service.get_current_user_id(current_session_token)
            except ValueError as error:
                print(f"Ошибка: {error}")
                current_session_token = None
                current_user_id = None
                current_user = None
                current_chat_id = None
                message_ids_by_number = {}
                continue

            if command == "/help":
                print("""Вот список доступных команд:
/help - вывести список команд
/register - зарегистрировать новый аккаунт
/login - войти в уже существующий аккаунт
/delete_account - удалить текущий аккаунт
/quit - завершить работу
/chat new - создать новый чат
/chat list - посмотреть список доступных чатов
/chat open - открыть чат по имени или id
/chat members - посмотреть участников открытого чата
/chat add <username> [member|admin] - добавить участника
/chat remove <user_id|username> - удалить участника
/chat role <user_id|username> <member|admin> - изменить роль участника
/chat delete - удалить открытый чат
/send - отправить в открытый чат сообщение
/message delete <номер_из_/messages> - удалить свое сообщение
/messages - вывести историю сообщений""")
            elif command == "/login":
                result = login(user_service)
                if result is None:
                    return
                close_session(session_service, current_session_token)
                current_user, current_user_id = result
                current_session_token, current_user_id = start_session(session_service, current_user)
                current_chat_id = None
                message_ids_by_number = {}

            elif command == "/register":
                result = register(user_service)
                if result is None:
                    return
                close_session(session_service, current_session_token)
                current_user, current_user_id = result
                current_session_token, current_user_id = start_session(session_service, current_user)
                current_chat_id = None
                message_ids_by_number = {}

            elif command == "/delete_account":
                result = delete_user(user_service, current_user, current_user_id)
                if result:
                    close_session(session_service, current_session_token)
                    current_session_token = None
                    current_user_id = None
                    current_user = None
                    current_chat_id = None
                    message_ids_by_number = {}

            elif command == "/chat new":
                print("Название чата не может быть пустым")

            elif command.startswith("/chat new "):
                chat_name = command.removeprefix("/chat new ").strip()
                chat_service.create_chat(chat_name, current_user_id)
                message_ids_by_number = {}

            elif command == "/chat list":
                chats = chat_service.list_chats(current_user_id)

                if not chats:
                    print("Чатов пока нет")
                else:
                    for chat in chats:
                        print(f"{chat.id}. {chat.name}")

            elif command == "/chat open":
                print("id или название чата не может быть пустым")

            elif command.startswith("/chat open "):
                chat_name_or_id = command.removeprefix("/chat open ").strip()
                try:
                    current_chat_id = chat_service.get_chat(chat_name_or_id, current_user_id)
                    message_ids_by_number = {}
                    print(f"Открыт чат {current_chat_id}")
                except ValueError as error:
                    current_chat_id = None
                    print(f"Ошибка: {error}")

            elif command == "/chat members":
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                members = chat_service.list_members(current_user_id, current_chat_id)
                print_members(members)

            elif command == "/chat add":
                print("Укажите пользователя")

            elif command.startswith("/chat add "):
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                parts = command.removeprefix("/chat add ").split()
                if not parts:
                    print("Укажите пользователя")
                    continue

                target_user_id = resolve_username(user_service, parts[0])
                role = parts[1] if len(parts) > 1 else "member"
                chat_service.add_user_to_chat(
                    current_user_id=current_user_id,
                    chat_id=current_chat_id,
                    target_user_id=target_user_id,
                    role=role,
                )
                print("Пользователь добавлен")

            elif command == "/chat remove":
                print("Укажите пользователя")

            elif command.startswith("/chat remove "):
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                target_user_id = resolve_user_id(
                    user_service,
                    command.removeprefix("/chat remove ").strip(),
                )
                chat_service.remove_user_from_chat(
                    current_user_id=current_user_id,
                    chat_id=current_chat_id,
                    target_user_id=target_user_id,
                )
                print("Пользователь удален из чата")

            elif command == "/chat role":
                print("Укажите пользователя и роль")

            elif command.startswith("/chat role "):
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                parts = command.removeprefix("/chat role ").split()
                if len(parts) != 2:
                    print("Укажите пользователя и роль")
                    continue

                target_user_id = resolve_user_id(user_service, parts[0])
                chat_service.change_user_role(
                    current_user_id=current_user_id,
                    chat_id=current_chat_id,
                    target_user_id=target_user_id,
                    role=parts[1],
                )
                print("Роль изменена")

            elif command == "/chat delete":
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                chat_service.delete_chat(current_user_id, current_chat_id)
                current_chat_id = None
                message_ids_by_number = {}
                print("Чат удален")

            elif command == "/send":
                print("Сообщение не может быть пустым")

            elif command.startswith("/send "):
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                text = command.removeprefix("/send ").strip()
                if text == "":
                    print("Сообщение не может быть пустым")
                    continue

                chat_service.send_message(chat_id=current_chat_id, text=text, current_user_id=current_user_id)
                message_ids_by_number = {}

            elif command == "/message delete":
                print("Укажите номер сообщения из /messages")

            elif command.startswith("/message delete "):
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                message_number = command.removeprefix("/message delete ").strip()
                if not message_number.isdigit():
                    print("Укажите корректный номер сообщения")
                    continue

                message_id = message_ids_by_number.get(int(message_number))
                if message_id is None:
                    print("Сначала выполните /messages и выберите номер из вывода")
                    continue

                chat_service.delete_message(
                    current_user_id=current_user_id,
                    chat_id=current_chat_id,
                    message_id=message_id,
                )
                message_ids_by_number = {}
                print("Сообщение удалено")

            elif command == "/messages":
                if current_chat_id is None:
                    print("Сначала откройте чат")
                    continue

                messages = chat_service.get_messages(current_chat_id, current_user_id)

                if not messages:
                    message_ids_by_number = {}
                    print("Сообщений пока нет")
                else:
                    message_ids_by_number = {}
                    for number, message in enumerate(messages, start=1):
                        message_ids_by_number[number] = message.id
                        created_at = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            username = user_service.get_user(message.sender_id).username
                        except ValueError as error:
                            username = "Удалённый пользователь"
                        if username is None:
                            username = "Удалённый пользователь"
                        print(f"{number}. [{created_at}] {username}: {message.text}")

            elif command == "/quit":
                break
            else:
                print("Команда не найдена. Введите /help, чтобы посмотреть список доступных команд")

        except ValueError as error:
            print(f"Ошибка: {error}")

def start_app():
    with create_services() as app_services:
        run_cli(
            app_services.user_service,
            app_services.chat_service,
            app_services.session_service,
        )

if __name__ == "__main__":
    start_app()
