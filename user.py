"""Classes representing users"""
from abc import ABC, abstractmethod

from email_client import EmailClient

class User(ABC):
    """Abstract class representing a user"""
    @abstractmethod
    def notify(self, content: str):
        """Send notification with given `content` to user"""

class UserEmail(User):
    """Class representing a user who interacts via email"""
    def __init__(self, email: str):
        self.email = email

    def __eq__(self, other):
        return self.email == other.email

    def notify(self, content: str):
        email = EmailClient()
        email.send(
            to_email=self.email,
            subject='DTMaaS Recording',
            content=content
        )

class UserDiscord(User):
    """Class representing a user who interacts via discord"""
    def __init__(self, user_id: int, channel_id: int):
        self.user_id = user_id
        self.channel_id = channel_id

    def __eq__(self, other):
        return self.user_id == other.user_id and self.channel_id == other.channel_id

    def notify(self, content: str):
        pass

class UserSerializer:
    """Serialization for a User"""
    TYPE_EMAIL = 'user_email'
    TYPE_DISCORD = 'user_discord'

    @classmethod
    def serialize(cls, user: User) -> dict:
        """Serialize `user` to a dictionary"""
        if isinstance(user, UserEmail):
            return {
                'type': cls.TYPE_EMAIL,
                'email': user.email
            }
        if isinstance(user, UserDiscord):
            return {
                'type': cls.TYPE_DISCORD,
                'user_id': user.user_id,
                'channel_id': user.channel_id
            }
        raise TypeError(f'Unsupported User type "{user.__class__.__name__}"')

    @classmethod
    def deserialize(cls, data: dict) -> User:
        """Deserialize a user from a dictionary"""
        if data['type'] == cls.TYPE_EMAIL:
            return UserEmail(email=data['email'])
        if data['type'] == cls.TYPE_DISCORD:
            return UserDiscord(user_id=data['user_id'], channel_id=data['channel_id'])
        raise TypeError(f'Unsupported User type "{data["type"]}"')
