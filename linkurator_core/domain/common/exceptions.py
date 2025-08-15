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


class InvalidCredentialError(Exception):
    pass


class InvalidCredentialTypeError(Exception):
    pass


class InvalidYoutubeRssFeedError(Exception):
    pass


class CannotFollowOwnedTopicError(Exception):
    pass


class CannotUnfollowAssignedSubscriptionError(Exception):
    pass


class SubscriptionAlreadyUpdatedError(Exception):
    pass


class InvalidRegistrationRequestError(Exception):
    pass


class FailToRevokeCredentialsError(Exception):
    pass


class UsernameAlreadyInUseError(Exception):
    pass


class NonExistingFileError(Exception):
    pass


class InvalidChatError(Exception):
    pass
