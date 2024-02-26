from datetime import datetime
from typing import Callable
from uuid import UUID

UuidGenerator = Callable[[], UUID]
DateGenerator = Callable[[], datetime]
