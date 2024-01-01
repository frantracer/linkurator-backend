import abc
from typing import Optional, Dict, List
from uuid import UUID

from linkurator_core.domain.items.interaction import Interaction


class InteractionRepository(abc.ABC):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def add(self, interaction: Interaction) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, interaction_id: UUID) -> Optional[Interaction]:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, interaction_id: UUID) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_user_interactions_by_item_id(self, user_id: UUID, item_ids: List[UUID]) -> Dict[UUID, List[Interaction]]:
        raise NotImplementedError
