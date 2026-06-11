from __future__ import annotations

from pydantic import BaseModel


class ExportConfirmation(BaseModel):
    accepted: bool
