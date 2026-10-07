import unittest
from unittest.mock import patch, MagicMock
from autotrade.notifications.telegram import TelegramNotificationProvider

class TestTelegramProvider(unittest.TestCase):

    def setUp(self):
        self.provider = TelegramNotificationProvider(token="dummy_token", chat_id="123456")

    @patch('autotrade.notifications.telegram.requests.post')
    def test_send_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.provider.send("Test message")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['chat_id'], '123456')
        self.assertEqual(kwargs['json']['text'], "Test message")

    def test_register_command(self):
        async def dummy_handler():
            return "OK"

        self.provider.register_command("status", dummy_handler)
        self.assertIn("/status", self.provider.command_handlers)

if __name__ == '__main__':
    unittest.main()
