from dataclasses import dataclass
from enum import Enum


class ThemeName(str, Enum):
    BRIGHT_CANVA = "bright_canva"


@dataclass(frozen=True)
class Theme:
    name: ThemeName
    background: str
    gradients: tuple[str, str, str]
    text_body: str
    text_title: str
    accent: str
    badge_bg: str
    badge_text: str
    title_size: int
    subtitle_size: int
    bullet_size: int
    title_weight: int
    line_height: float
    margin: int
    padding: int
    card_radius: int
    shadow: str


BRIGHT_CANVA = Theme(
    name=ThemeName.BRIGHT_CANVA,
    background="#FFFFFF",
    gradients=("#1BA6A0", "#6D28D9", "#F97316"),
    text_body="#1F2937",
    text_title="#0F172A",
    accent="#0EA5E9",
    badge_bg="#0EA5E9",
    badge_text="#FFFFFF",
    title_size=58,
    subtitle_size=28,
    bullet_size=24,
    title_weight=700,
    line_height=1.35,
    margin=64,
    padding=32,
    card_radius=24,
    shadow="0 14px 28px rgba(15, 23, 42, 0.12)",
)


def get_theme(name: str) -> Theme:
    if name == ThemeName.BRIGHT_CANVA.value:
        return BRIGHT_CANVA
    raise ValueError(f"Unknown theme: {name}")
