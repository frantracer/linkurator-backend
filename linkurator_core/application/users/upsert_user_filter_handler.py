from uuid import UUID

from linkurator_core.domain.users.user_filter import UserFilter
from linkurator_core.domain.users.user_filter_repository import UserFilterRepository


class UpsertUserFilterHandler:
    def __init__(self, user_filter_repository: UserFilterRepository) -> None:
        self.user_filter_repository = user_filter_repository

    async def handle(
        self,
        user_id: UUID,
        text_filter: str | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        include_items_without_interactions: bool = True,
        include_recommended_items: bool = True,
        include_discouraged_items: bool = True,
        include_viewed_items: bool = True,
        include_hidden_items: bool = True,
    ) -> None:
        existing_filter = await self.user_filter_repository.get(user_id)

        if existing_filter is None:
            new_filter = UserFilter.new(
                user_id=user_id,
                text_filter=text_filter,
                min_duration=min_duration,
                max_duration=max_duration,
                include_items_without_interactions=include_items_without_interactions,
                include_recommended_items=include_recommended_items,
                include_discouraged_items=include_discouraged_items,
                include_viewed_items=include_viewed_items,
                include_hidden_items=include_hidden_items,
            )
        else:
            new_filter = UserFilter(
                user_id=user_id,
                text_filter=text_filter,
                min_duration=min_duration,
                max_duration=max_duration,
                include_items_without_interactions=include_items_without_interactions,
                include_recommended_items=include_recommended_items,
                include_discouraged_items=include_discouraged_items,
                include_viewed_items=include_viewed_items,
                include_hidden_items=include_hidden_items,
                created_at=existing_filter.created_at,
                updated_at=existing_filter.updated_at,
            )

        await self.user_filter_repository.upsert(new_filter)
