from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WidgetType(str, Enum):
    signup = "signup"
    contact = "contact"
    cta = "cta"
    popover = "popover"


class FieldType(str, Enum):
    text = "text"
    email = "email"
    textarea = "textarea"


class FormField(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=80)
    type: FieldType = FieldType.text
    required: bool = True
    max_length: int = Field(default=255, ge=1, le=2_000)


class WidgetCreate(BaseModel):
    type: WidgetType
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    fields: list[FormField] = Field(default_factory=list, max_length=20)
    button_text: str = Field(default="Submit", min_length=1, max_length=40)
    display_options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "button_text")
    @classmethod
    def no_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("fields")
    @classmethod
    def unique_field_names(cls, value: list[FormField]) -> list[FormField]:
        names = [field.name for field in value]
        if len(names) != len(set(names)):
            raise ValueError("field names must be unique")
        return value


class WidgetUpdate(WidgetCreate):
    pass


class SubmissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    widget_id: UUID
    data: dict[str, str] = Field(max_length=20)
    website: str = Field(default="", max_length=500)


class AuthCredentials(BaseModel):
    email: str | None = None
    password: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class GeoResult(BaseModel):
    country: str | None = None
    country_code: str | None = None
    city: str | None = None
    provider: str
