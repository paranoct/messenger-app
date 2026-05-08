import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CliFlowTests(unittest.TestCase):
    def run_cli(self, commands):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        with tempfile.TemporaryDirectory(prefix="messenger-cli-test-") as tmpdir:
            return subprocess.run(
                [sys.executable, "-m", "cli.main_cli"],
                cwd=tmpdir,
                env=env,
                input=commands,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_chat_roles_messages_and_delete_commands(self):
        result = self.run_cli(
            "\n".join(
                [
                    "2",
                    "owner",
                    "owner@example.com",
                    "Pass1!",
                    "/chat new room",
                    "/register",
                    "member",
                    "member@example.com",
                    "Pass1!",
                    "/login",
                    "owner",
                    "Pass1!",
                    "/chat open room",
                    "/chat add member admin",
                    "/chat members",
                    "/chat role member member",
                    "/chat members",
                    "/send hello",
                    "/message delete 1",
                    "/messages",
                    "/message delete 1",
                    "/messages",
                    "/chat remove member",
                    "/chat members",
                    "/chat delete",
                    "/chat list",
                    "/quit",
                    "",
                ]
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Открыт чат 1", result.stdout)
        self.assertIn("Пользователь добавлен", result.stdout)
        self.assertIn("member [admin]", result.stdout)
        self.assertIn("Роль изменена", result.stdout)
        self.assertIn("member [member]", result.stdout)
        self.assertIn("owner: hello", result.stdout)
        self.assertIn("Сначала выполните /messages", result.stdout)
        self.assertIn("Сообщение удалено", result.stdout)
        self.assertIn("Пользователь удален из чата", result.stdout)
        self.assertIn("Чат удален", result.stdout)
        self.assertIn("Чатов пока нет", result.stdout)

    def test_login_error_is_generic(self):
        result = self.run_cli(
            "\n".join(
                [
                    "1",
                    "unknown",
                    "wrong",
                    "",
                ]
            )
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ошибка: Неверные учетные данные", result.stdout)


if __name__ == "__main__":
    unittest.main()
