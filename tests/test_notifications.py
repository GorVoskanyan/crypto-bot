import unittest
from unittest.mock import MagicMock, patch
from autotrade.notifications.telegram import TelegramNotificationProvider

class TestNotifications(unittest.TestCase):

    @patch('autotrade.notifications.telegram.requests.post')
    def test_send_success(self, mock_post):
        """Test sending a notification successfully."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = TelegramNotificationProvider('token', 'chat_id')
        provider.send('Hello')

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['text'], 'Hello')

    @patch('autotrade.notifications.telegram.requests.post')
    def test_send_failure(self, mock_post):
        """Test graceful handling of send failure."""
        mock_post.side_effect = Exception("Connection Error")

        provider = TelegramNotificationProvider('token', 'chat_id')
        # Should log error but not crash
        provider.send('Hello')

        mock_post.assert_called_once()

    def test_missing_config(self):
        """Test skipping if config missing."""
        provider = TelegramNotificationProvider('', '')

        with patch('autotrade.notifications.telegram.requests.post') as mock_post:
             provider.send('Hello')
             mock_post.assert_not_called()

if __name__ == '__main__':
    unittest.main()
