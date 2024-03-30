class UserNotFoundError(Exception):
    pass


class TopicNotFoundError(Exception):
    pass


class SubscriptionNotFoundError(Exception):
    pass


class ItemNotFoundError(Exception):
    pass


class DuplicatedKeyError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class CredentialsAlreadyExistsError(Exception):
    pass


class InvalidCredentialTypeError(Exception):
    pass


class InvalidYoutubeRssFeedError(Exception):
    pass
