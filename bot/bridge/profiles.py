from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List
from urllib.parse import quote_plus

from supabase import Client

LOGGER = logging.getLogger(__name__)

DICEBEAR_BASE_URL = "https://api.dicebear.com/9.x/bottts-neutral/png"
DICTIONARY_ID = "dictionary"

DEFAULT_ADJECTIVES: List[str] = [
    "かわいい", "かっこいい", "おもしろい", "たのしい", "やさしい", "つよい", "よわい", "はやい", "おそい", "すばやい",
    "おおきい", "ちいさい", "ながい", "みじかい", "ひろい", "せまい", "あつい", "さむい", "あたたかい", "すずしい",
    "あかい", "あおい", "しろい", "くろい", "きいろい", "ちゃいろい", "あおじろい", "あかるい", "くらい", "あまい",
    "からい", "にがい", "すっぱい", "しょっぱい", "やわらかい", "かたい", "みずみずしい", "うるさい", "しぶい", "するどい",
    "にぶい", "たのもしい", "こころづよい", "あたらしい", "ふるい", "なつかしい", "めずらしい", "すごい", "まるい", "しかくい",
    "こい", "うすい", "かるい", "おもい", "けだかい", "きびしい", "おとなしい", "すばらしい", "たくましい", "うれしい",
    "あざやかな", "はなやかな", "しずかな", "にぎやかな", "おだやかな", "さわやかな", "つやつやな", "さらさらな", "なめらかな", "ふわふわな",
    "もふもふな", "ぴかぴかな", "きらきらな", "じょうぶな", "がんじょうな", "しなやかな", "優雅な", "上品な", "豪華な", "素朴な",
    "無邪気な", "純粋な", "可憐な", "温厚な", "ほがらかな", "気さくな", "まじめな", "正直な", "大胆な", "繊細な",
    "快適な", "健やかな", "清潔な", "清らかな", "陽気な", "快活な", "活発な", "器用な", "不器用な", "几帳面な",
    "粋な", "上質な", "高級な", "シンプルな", "クールな", "スマートな", "エレガントな", "キュートな", "ワイルドな", "ミステリアスな",
    "レトロな", "モダンな", "ポップな", "カラフルな", "カジュアルな", "フレッシュな", "フレンドリーな", "ハッピーな", "にこやかな", "清楚な",
]

DEFAULT_NOUNS: List[str] = [
    "ねこ", "いぬ", "うさぎ", "くま", "ことり", "とり", "きつね", "たぬき", "りす", "ねずみ",
    "ぞう", "きりん", "ぱんだ", "らいおん", "とら", "おおかみ", "くじら", "いるか", "さめ", "ぺんぎん",
    "かめ", "かえる", "へび", "あり", "はち", "ちょう", "ほたる", "かに", "えび", "いか",
    "たこ", "くらげ", "ひつじ", "やぎ", "うし", "ぶた", "うま", "にわとり", "ひよこ", "すずめ",
    "ふくろう", "はと", "つばめ", "かもめ", "かも", "おたまじゃくし", "かぶとむし", "くわがた", "てんとうむし", "花",
    "木", "森", "林", "草", "葉っぱ", "つぼみ", "実", "種", "根っこ", "空",
    "雲", "雨", "雪", "風", "星", "月", "太陽", "海", "川", "湖",
    "島", "山", "谷", "砂", "石", "岩", "砂利", "土", "氷", "光",
    "影", "音", "声", "音色", "メロディ", "リズム", "ことば", "えがお", "なみだ", "ゆめ",
    "きぼう", "こころ", "いのち", "せかい", "ぼうけん", "ひみつ", "まほう", "でんせつ", "おとぎ話", "えほん",
    "ものがたり", "うた", "しあわせ", "ゆうき", "ちから", "きずな", "まなざし", "ほほえみ", "ごはん", "パン",
    "ケーキ", "クッキー", "ドーナツ", "アイス", "チョコ", "キャンディ", "りんご", "みかん", "いちご", "ぶどう",
    "もも", "さくらんぼ", "すいか", "バナナ", "なし", "かき", "メロン", "かぼちゃ", "じゃがいも", "にんじん",
    "たまねぎ", "トマト", "きゅうり", "なす", "ピーマン", "きのこ", "おにぎり", "うどん", "そば", "ラーメン",
    "カレー", "ハンバーグ", "ピザ", "サンドイッチ", "スープ", "サラダ", "おちゃ", "こうちゃ", "コーヒー", "ジュース",
    "ミルク", "ソーダ", "みず", "はちみつ", "バター", "チーズ", "いえ", "まち", "みち", "ばしょ",
    "お店", "公園", "学校", "図書館", "駅", "空港", "たび", "ふね", "くるま", "でんしゃ",
    "バス", "じてんしゃ", "ひこうき", "ロケット", "エレベーター", "はし", "みなと", "さかみち", "まど", "ドア",
    "かぎ", "つくえ", "いす", "ベッド", "ほん", "ノート", "えんぴつ", "ペン", "けしごむ", "カバン",
    "ふでばこ", "かさ", "ふく", "ぼうし", "くつ", "てぶくろ", "マフラー", "メガネ", "時計", "カメラ",
]

GUILD_COLOR_PALETTE: List[int] = [
    0xE74C3C,  # red
    0xE67E22,  # orange
    0xF1C40F,  # yellow
    0x2ECC71,  # green
    0x1ABC9C,  # teal
    0x3498DB,  # blue
    0x9B59B6,  # purple
    0x34495E,  # navy
    0xC0392B,  # deep red
    0xD35400,  # deep orange
    0x27AE60,  # deep green
    0x2980B9,  # deep blue
    0x8E44AD,  # deep purple
    0x7F8C8D,  # gray
]


@dataclass(slots=True, frozen=True)
class BridgeProfile:
    seed: str
    display_name: str
    avatar_url: str


class BridgeProfileStore:
    """Manage adjective/noun dictionaries stored in Supabase."""

    def __init__(self, supabase: Client, table_name: str = "bridge_profiles") -> None:
        self._supabase = supabase
        self._table_name = table_name
        self._dictionary, self._guild_colors = self._load_or_seed_dictionary()

    def _load_or_seed_dictionary(self) -> tuple[Dict[str, List[str]], Dict[int, int]]:
        response = (
            self._supabase.table(self._table_name)
            .select("adjectives, nouns, guild_colors")
            .eq("id", DICTIONARY_ID)
            .execute()
        )
        record = None
        if isinstance(response.data, list) and response.data:
            record = response.data[0]
        elif isinstance(response.data, dict):
            record = response.data

        if record:
            adjectives = list(record.get("adjectives") or [])
            nouns = list(record.get("nouns") or [])
            if not adjectives or not nouns:
                raise RuntimeError("Bridge profile dictionary is empty.")
            guild_colors_raw = record.get("guild_colors") or {}
            guild_colors, needs_update = self._normalize_guild_colors(guild_colors_raw)
            if needs_update:
                self._supabase.table(self._table_name).update(
                    {"guild_colors": self._serialize_guild_colors(guild_colors)}
                ).eq("id", DICTIONARY_ID).execute()
            return {"adjectives": adjectives, "nouns": nouns}, guild_colors

        self._supabase.table(self._table_name).upsert(
            {
                "id": DICTIONARY_ID,
                "adjectives": list(DEFAULT_ADJECTIVES),
                "nouns": list(DEFAULT_NOUNS),
                "guild_colors": {},
            },
            on_conflict="id",
        ).execute()
        LOGGER.info("Bridge profile dictionary seeded with default adjectives and nouns.")
        return (
            {
                "adjectives": list(DEFAULT_ADJECTIVES),
                "nouns": list(DEFAULT_NOUNS),
            },
            {},
        )

    def refresh_dictionary(self) -> None:
        """Reload the adjective and noun lists from the database."""
        self._dictionary, self._guild_colors = self._load_or_seed_dictionary()

    def ensure_guild_colors(self, guild_ids: Iterable[int]) -> Dict[int, int]:
        missing = [gid for gid in guild_ids if gid not in self._guild_colors]
        if not missing:
            return dict(self._guild_colors)

        existing_colors = set(self._guild_colors.values())
        for gid in sorted(missing):
            color = self._pick_guild_color(existing_colors)
            self._guild_colors[gid] = color
            existing_colors.add(color)

        self._supabase.table(self._table_name).update(
            {"guild_colors": self._serialize_guild_colors(self._guild_colors)}
        ).eq("id", DICTIONARY_ID).execute()
        return dict(self._guild_colors)

    def get_guild_color(self, guild_id: int) -> int | None:
        return self._guild_colors.get(guild_id)

    def get_profile(self, *, seed: str) -> BridgeProfile:
        dictionary = self._dictionary
        rng = random.Random(seed)

        adjectives: List[str] = dictionary["adjectives"]
        nouns: List[str] = dictionary["nouns"]

        adjective = rng.choice(adjectives)
        noun = rng.choice(nouns)
        display_name = f"{adjective}{noun}"
        avatar_seed = f"{seed}-{adjective}-{noun}"
        avatar_url = f"{DICEBEAR_BASE_URL}?seed={quote_plus(avatar_seed)}"

        return BridgeProfile(
            seed=avatar_seed,
            display_name=display_name,
            avatar_url=avatar_url,
        )

    @staticmethod
    def _serialize_guild_colors(guild_colors: Dict[int, int]) -> Dict[str, int]:
        return {str(gid): int(color) for gid, color in guild_colors.items()}

    @staticmethod
    def _normalize_guild_colors(raw: object) -> tuple[Dict[int, int], bool]:
        if not isinstance(raw, dict):
            return {}, True
        normalized: Dict[int, int] = {}
        changed = False
        for key, value in raw.items():
            try:
                gid = int(key)
                color = int(value)
            except (TypeError, ValueError):
                changed = True
                continue
            if gid <= 0 or color < 0 or color > 0xFFFFFF:
                changed = True
                continue
            normalized[gid] = color
            if str(key) != str(gid) or int(value) != color:
                changed = True
        return normalized, changed

    @staticmethod
    def _pick_guild_color(existing_colors: set[int]) -> int:
        if not existing_colors:
            return GUILD_COLOR_PALETTE[0]

        existing_lab = [_rgb_to_lab(_color_to_rgb(color)) for color in existing_colors]
        candidates = _build_color_candidates(existing_colors)
        if not candidates:
            return GUILD_COLOR_PALETTE[0]
        best_color = candidates[0]
        best_score = -1.0
        for candidate in candidates:
            lab = _rgb_to_lab(_color_to_rgb(candidate))
            min_distance = min(_delta_e(lab, existing) for existing in existing_lab)
            if min_distance > best_score:
                best_score = min_distance
                best_color = candidate
        return best_color


def _build_color_candidates(existing_colors: set[int]) -> List[int]:
    candidates: List[int] = [color for color in GUILD_COLOR_PALETTE if color not in existing_colors]
    for hue in range(0, 360, 10):
        rgb = _hsl_to_rgb(hue / 360.0, 0.65, 0.55)
        color = _rgb_to_color(rgb)
        if color not in existing_colors and color not in candidates:
            candidates.append(color)
    return candidates


def _color_to_rgb(color: int) -> tuple[int, int, int]:
    return (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF


def _rgb_to_color(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    return (r << 16) | (g << 8) | b


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    if s == 0.0:
        channel = int(round(l * 255))
        return channel, channel, channel

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    r = hue_to_rgb(p, q, h + 1 / 3)
    g = hue_to_rgb(p, q, h)
    b = hue_to_rgb(p, q, h - 1 / 3)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def _rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = [channel / 255.0 for channel in rgb]

    def to_linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin, g_lin, b_lin = to_linear(r), to_linear(g), to_linear(b)
    x = r_lin * 0.4124 + g_lin * 0.3576 + b_lin * 0.1805
    y = r_lin * 0.2126 + g_lin * 0.7152 + b_lin * 0.0722
    z = r_lin * 0.0193 + g_lin * 0.1192 + b_lin * 0.9505

    x /= 0.95047
    y /= 1.00000
    z /= 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = f(x), f(y), f(z)
    l = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return l, a, b


def _delta_e(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    return math.sqrt(
        (lab1[0] - lab2[0]) ** 2
        + (lab1[1] - lab2[1]) ** 2
        + (lab1[2] - lab2[2]) ** 2
    )


__all__ = ["BridgeProfile", "BridgeProfileStore"]
