from abc import ABC, abstractmethod

class NotificationProvider(ABC):
    """
    Abstract base class for sending notifications.
    """

    @abstractmethod
    def send(self, message: str):
        """
        Sends a message to the user.
        """
        pass
