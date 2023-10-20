from typing import List, Optional

from pydantic import BaseModel, Field
from ..schema import Activity, Attachment


class AbilityResult(BaseModel):
    """The AbilityResult is a standard response struct for an ability."""

    ability_name: str
    ability_args: dict[str, str]
    success: bool
    message: Optional[str]
    activities: List[Activity] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    def summary(self) -> str:
        # kwargs = ", ".join(f"{k}={v}" for k, v in self.ability_args.items())

        # Success or Failure tag
        status_tag = "Success" if self.success else "Failure"

        # Include message if available
        message_info = f" {self.message}" if self.message else ""

        # Include activities count
        activities_info = (
            f", {len(self.activities)} activities" if self.activities else ""
        )

        # Include attachments count
        attachments_info = (
            f", {len(self.attachments)} attachments" if self.attachments else ""
        )

        return (
            f"[{status_tag}] {self.ability_name}:"
            f"{message_info}{activities_info}{attachments_info}"
        )
