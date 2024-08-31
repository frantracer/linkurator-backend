from pydantic import Field, RootModel


class PasswordWith64HexCharacters(RootModel):  # type: ignore
    root: str = Field(
        ...,
        description="A password that is 64 hex characters long.",
        min_length=64,
        max_length=64,
        pattern="^[0-9a-fA-F]*$",
        json_schema_extra={"examples": [
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        ]},
    )

    def __str__(self) -> str:
        return self.root
