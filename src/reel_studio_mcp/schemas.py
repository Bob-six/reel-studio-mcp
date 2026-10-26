import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Number = Annotated[float, Field(allow_inf_nan=False)]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Word(Input):
    text: str = Field(min_length=1, max_length=200)
    start: Number = Field(ge=0, le=1800)
    end: Number = Field(gt=0, le=1800)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("invalid_word_time")
        return self


class Line(Word):
    text: str = Field(min_length=1, max_length=600)
    words: list[Word] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def word_bounds(self):
        previous = self.start
        for word in self.words:
            if word.start < previous or word.end > self.end:
                raise ValueError("invalid_word_time")
            previous = word.end
        if self.words and " ".join(word.text for word in self.words) != " ".join(self.text.split()):
            raise ValueError("lyrics_words_mismatch")
        return self


class Layer(Input):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[\w-]+$")
    kind: Literal["text", "lyrics", "image", "shape", "countdown", "progress", "waveform", "song", "chords"]
    name: str = Field(default="", max_length=100)
    text: str = Field(default="", max_length=2000)
    x: Number = Field(default=10, ge=0, le=99)
    y: Number = Field(default=10, ge=0, le=99)
    width: Number = Field(default=80, ge=1, le=100)
    height: Number = Field(default=10, ge=1, le=100)
    start: Number = Field(default=0, ge=0, le=1800)
    end: Number | None = Field(default=None, gt=0, le=1800)
    hidden: bool = False
    locked: bool = False
    color: Color = "#ffffff"
    accent: Color = "#bca0ff"
    background: Color | None = None
    font_size: Number = Field(default=48, ge=12, le=160)
    weight: int = Field(default=600, ge=400, le=900)
    align: Literal["left", "center", "right"] = "center"
    direction: Literal["rtl", "ltr"] = "rtl"
    opacity: Number = Field(default=1, ge=0, le=1)
    radius: Number = Field(default=12, ge=0, le=100)
    outline: int = Field(default=0, ge=0, le=6)
    shadow: bool = True
    animation: Literal["none", "fade", "slide"] = "none"
    asset_id: str | None = Field(default=None, max_length=80)
    fit: Literal["cover", "contain"] = "cover"
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    lyric_style: Literal["karaoke", "single", "stacked", "upcoming"] = "karaoke"
    lyric_highlight: bool | None = None
    lyric_animation: Literal["none", "fade", "slide"] = "none"
    padding: Number = Field(default=0, ge=0, le=80)
    line_height: Number = Field(default=1.45, ge=1, le=2.5)
    context_opacity: Number = Field(default=0.45, ge=0, le=1)
    context_scale: Number = Field(default=0.75, ge=0.4, le=1)
    progress_style: Literal["bar", "rounded", "segmented"] = "bar"
    progress_direction: Literal["ltr", "rtl"] = "rtl"
    progress_segments: int = Field(default=20, ge=4, le=60)
    timer_style: Literal["remaining", "elapsed", "fraction", "singing"] = "remaining"
    song_style: Literal["title_artist", "title", "artist"] = "title_artist"
    chord_style: Literal["current", "strip"] = "current"

    @model_validator(mode="after")
    def bounds(self):
        if self.x + self.width > 100.001 or self.y + self.height > 100.001:
            raise ValueError("layer_outside_canvas")
        if self.end is not None and self.end <= self.start:
            raise ValueError("invalid_layer_time")
        return self


class Background(Input):
    color: Color = "#171127"
    secondary: Color = "#4b286d"
    asset_id: str | None = Field(default=None, max_length=80)
    fit: Literal["cover", "contain"] = "cover"
    dim: Number = Field(default=0.25, ge=0, le=0.9)
    blur: Number = Field(default=0, ge=0, le=30)


class Document(Input):
    version: Literal[1] = 1
    format: Literal["reels", "square", "landscape"] = "reels"
    clip_start: Number = Field(default=0, ge=0, le=1800)
    clip_end: Number = Field(default=30, gt=0, le=1800)
    lead_mute: tuple[Number, Number] | None = None
    backing_mute: tuple[Number, Number] | None = None
    volume: Number = Field(default=1, ge=0, le=1)
    fade_in: Number = Field(default=0.25, ge=0, le=5)
    fade_out: Number = Field(default=1, ge=0, le=5)
    background: Background = Field(default_factory=Background)
    layers: list[Layer] = Field(default_factory=list, max_length=40)
    lyrics: list[Line] | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def timeline(self):
        if not 0 < self.clip_end - self.clip_start <= 180:
            raise ValueError("clip_must_be_between_zero_and_180_seconds")
        for interval in (self.lead_mute, self.backing_mute):
            if interval and not self.clip_start <= interval[0] < interval[1] <= self.clip_end:
                raise ValueError("mute_outside_clip")
        if len({layer.id for layer in self.layers}) != len(self.layers):
            raise ValueError("duplicate_layer_id")
        if self.lyrics:
            previous = -1
            for line in self.lyrics:
                if line.start <= previous:
                    raise ValueError("lyrics_must_be_ordered")
                previous = line.start
        return self


class ProjectCreate(Input):
    title: str = Field(min_length=1, max_length=150)
    track_id: uuid.UUID | None = None
    document: Document = Field(default_factory=Document)
    is_template: bool = False


class ProjectUpdate(ProjectCreate):
    revision: int = Field(ge=1)


class AssetUpload(Input):
    name: str = Field(min_length=1, max_length=150)
    content_type: Literal["image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"]
    size: int = Field(gt=0, le=100 * 1024 * 1024)


class RenderRequest(Input):
    revision: int = Field(ge=1)
    request_id: uuid.UUID
    preview: bool = True
    preview_start: Number = Field(default=0, ge=0, le=180)


class PresignUploadRequest(BaseModel):
    upload_id: uuid.UUID | None = None
    filename: str = Field(min_length=1, max_length=300)
    content_type: str
    size: int = Field(gt=0)
    provider: Literal["local", "moises"] | None = None
