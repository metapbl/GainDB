"""gaindb/tag.py — 태그 처리 (4단계).

원본 mp3gain 의 apetag.c 동작을 공개 사양·관찰된 동작으로 독립 재구현(clean-room).
이 파일 단계 ①: APEv2 읽기 파서 (전 필드 + otherFields 보존 + Lyrics3/ID3v1 꼬리 감지).

원본 대응:
  struct MP3GainTagInfo   -> MP3GainTagInfo
  struct APETagStruct     -> ApeTag
  struct FileTagsStruct   -> FileTags
  ReadMP3APETag           -> _read_ape_tag
  ReadMP3Lyrics3v2Tag     -> _read_lyrics3v2_tag
  ReadMP3ID3v1Tag         -> _read_id3v1_tag
  ReadMP3GainAPETag       -> read_mp3gain_ape_tag
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import BinaryIO, Optional

# 원본: enum { MAX_FIELD_SIZE = 1024*1024 } — 이보다 큰 필드는 오류로 간주.
MAX_FIELD_SIZE = 1024 * 1024

# APE 푸터/헤더는 고정 32바이트 (struct APETagFooterStruct).
APE_FOOTER_SIZE = 32

# APE Flags bit31: 이 태그에 헤더가 존재함(footer 의 bit31) 또는
# "이것이 헤더다"(header 의 bit31). 원본의 1<<31.
APE_FLAG_HAS_HEADER = 1 << 31


def _read_le32(b: bytes, off: int = 0) -> int:
    """원본 Read_LE_Uint32: 리틀엔디언 4바이트 부호 없는 정수."""
    return b[off] | (b[off + 1] << 8) | (b[off + 2] << 16) | (b[off + 3] << 24)


def _strlen_max(b: bytes, start: int, max_len: int) -> int:
    """원본 strlen_max: start 부터 NUL 까지의 길이, 단 max_len 으로 상한."""
    n = 0
    while n < max_len and b[start + n] != 0:
        n += 1
    return n


@dataclass
class MP3GainTagInfo:
    """원본 struct MP3GainTagInfo 대응.

    APE/ID3 공용 게인 정보 컨테이너. 읽기 시 인식한 필드만 have_* 가 True.
    """

    have_track_gain: bool = False
    have_track_peak: bool = False
    have_album_gain: bool = False
    have_album_peak: bool = False
    have_undo: bool = False
    have_min_max_gain: bool = False
    have_album_min_max_gain: bool = False

    track_gain: float = 0.0
    track_peak: float = 0.0
    album_gain: float = 0.0
    album_peak: float = 0.0

    undo_left: int = 0
    undo_right: int = 0
    undo_wrap: bool = False

    # 원본은 unsigned char (0~255). 프레임 global_gain 의 현재 min/max.
    min_gain: int = 0
    max_gain: int = 0
    album_min_gain: int = 0
    album_max_gain: int = 0

    # 원본: dirty(로드 후 변경 여부), recalc(재계산 필요 비트마스크).
    # 쓰기/오케스트레이션 단계(③~)에서 사용. 읽기 단계에서는 건드리지 않음.
    dirty: bool = False
    recalc: int = 0


@dataclass
class ApeTag:
    """원본 struct APETagStruct 대응.

    footer/header 는 원본 32바이트를 그대로 보존(Version/Flags/Reserved 유지).
    LE 정수 접근은 _read_le32 헬퍼로. other_fields 는 인식 못 한 필드들의
    원본 바이트(각 필드의 vsize/flags 헤더 포함)를 그대로 이어붙인 블록.
    """

    have_header: bool = False
    header: Optional[bytes] = None        # 32바이트 또는 None
    footer: bytes = b""                   # 32바이트
    other_fields: bytes = b""             # 비-mp3gain 필드 원본 바이트
    other_fields_size: int = 0
    original_tag_size: int = 0            # 파일에서 깎인 총 바이트(헤더 있으면 +32)


@dataclass
class FileTags:
    """원본 struct FileTagsStruct 대응.

    tag_offset 는 오디오 본문이 끝나고 모든 꼬리 태그가 시작되는 위치.
    """

    tag_offset: int = 0
    ape_tag: Optional[ApeTag] = None
    lyrics3_tag: Optional[bytes] = None
    lyrics3_tag_size: int = 0
    id3v1_tag: Optional[bytes] = None


def _lyrics3_number6(b: bytes) -> int:
    """원본 Lyrics3GetNumber6: 6자리 ASCII 숫자. 비숫자면 0."""
    n = 0
    for i in range(6):
        c = b[i]
        if c < 0x30 or c > 0x39:  # '0'..'9'
            return 0
        n = n * 10 + (c - 0x30)
    return n


def _read_id3v1_tag(f: BinaryIO, file_tags: FileTags, tag_offset: int) -> int:
    """원본 ReadMP3ID3v1Tag.

    tag_offset 직전 128바이트가 'TAG' 로 시작하면 ID3v1 으로 보고 보존.
    찾으면 새 tag_offset(=128 깎은 값) 반환, 아니면 원래 tag_offset 그대로 반환.
    """
    if tag_offset < 128:
        return tag_offset
    f.seek(tag_offset - 128)
    tmp = f.read(128)
    if len(tmp) != 128 or tmp[:3] != b"TAG":
        return tag_offset
    file_tags.id3v1_tag = tmp
    return tag_offset - 128


def _read_lyrics3v2_tag(f: BinaryIO, file_tags: FileTags, tag_offset: int) -> int:
    """원본 ReadMP3Lyrics3v2Tag.

    Lyrics3v2 는 정의상 그 뒤에 ID3v1(128B)이 붙어 있다. 구조:
      ... LYRICSBEGIN <body> <6자리길이> LYRICS200 <ID3v1 128B>
    감지되면 ID3v1 을 보존하고, Lyrics3 전체(128 + footer(15) + body)를 보존.
    찾으면 깎은 tag_offset, 아니면 원래 값 반환.
    """
    if tag_offset < 128:
        return tag_offset
    f.seek(tag_offset - 128)
    tmpid3 = f.read(128)
    if len(tmpid3) != 128 or tmpid3[:3] != b"TAG":
        return tag_offset
    # ID3v1 보존 (Lyrics3 는 정의상 id3v1 을 포함).
    file_tags.id3v1_tag = tmpid3

    # Lyrics3v2 footer 는 ID3v1 바로 앞 15바이트: Length[6] + ID[9].
    if tag_offset < 128 + 15:
        return tag_offset
    f.seek(tag_offset - 128 - 15)
    footer = f.read(15)
    if len(footer) != 15 or footer[6:15] != b"LYRICS200":
        return tag_offset

    body_len = _lyrics3_number6(footer[0:6])
    # 원본: tag_offset - 128 - sizeof(T) - len 위치에 'LYRICSBEGIN' 가 있어야 함.
    if tag_offset < 128 + 15 + body_len:
        return tag_offset
    f.seek(tag_offset - 128 - 15 - body_len)
    begin = f.read(11)
    if len(begin) != 11 or begin != b"LYRICSBEGIN":
        return tag_offset

    # 전체 Lyrics3 태그(footer + body + 뒤의 id3v1 128) 보존.
    tag_len = 128 + body_len + 15
    new_offset = tag_offset - tag_len
    f.seek(new_offset)
    file_tags.lyrics3_tag = f.read(tag_len)
    file_tags.lyrics3_tag_size = tag_len
    return new_offset


def _read_ape_tag(
    f: BinaryIO, info: MP3GainTagInfo, file_tags: FileTags, tag_offset: int
) -> int:
    """원본 ReadMP3APETag.

    tag_offset 직전에서 APEv1/v2 푸터를 찾아 파싱한다.
    인식 필드(REPLAYGAIN_*, MP3GAIN_*)는 info 에 채우고, 나머지는 ape_tag.other_fields
    에 원본 바이트 그대로 보존. 찾으면 깎은 tag_offset, 아니면 원래 값 반환.

    APE 푸터/헤더 구조(각 4바이트 LE): ID[8] Version[8..] Length[12..]
    TagCount[16..] Flags[20..] Reserved[24..32].
    """
    if tag_offset < APE_FOOTER_SIZE:
        return tag_offset

    # 푸터 읽기 (파일 끝 직전 32바이트).
    f.seek(tag_offset - APE_FOOTER_SIZE)
    footer = f.read(APE_FOOTER_SIZE)
    if len(footer) != APE_FOOTER_SIZE or footer[0:8] != b"APETAGEX":
        return tag_offset

    version = _read_le32(footer, 8)
    if version not in (1000, 2000):
        return tag_offset

    tag_len = _read_le32(footer, 12)  # 푸터 포함·헤더 제외 길이
    if tag_len < APE_FOOTER_SIZE or tag_offset < tag_len:
        return tag_offset

    orig_tag_count = _read_le32(footer, 16)  # TagCount: offset 16
    footer_flags = _read_le32(footer, 20)    # Flags:    offset 20

    # 필드 데이터(푸터 직전 tag_len - 32 바이트) 읽기.
    body_len = tag_len - APE_FOOTER_SIZE
    f.seek(tag_offset - tag_len)
    body = f.read(body_len)
    if len(body) != body_len:
        return tag_offset

    ape = ApeTag()
    ape.footer = footer
    # other_fields 는 최대 body 크기. 인식 못 한 필드 바이트를 누적.
    other = bytearray()
    other_count = 0

    p = 0
    remaining_count = orig_tag_count
    while p < body_len and remaining_count > 0:
        remaining_count -= 1
        if body_len - p < 8:
            break
        vsize = _read_le32(body, p)
        # flags = _read_le32(body, p + 4)  # 보존만, 해석 안 함
        field_start = p          # vsize/flags 포함 필드 시작(원본의 'p - 8' 대응)
        p += 8

        remaining = body_len - p
        isize = _strlen_max(body, p, remaining)
        # 경계/크기 검사 (원본과 동일).
        if isize >= remaining or vsize > MAX_FIELD_SIZE or isize + 1 + vsize > remaining:
            break

        name = body[p : p + isize].decode("ascii", errors="replace")
        value_bytes = body[p + isize + 1 : p + isize + 1 + vsize]
        value = value_bytes.decode("utf-8", errors="replace")

        recognized = _store_ape_field(name, value, info)

        if not recognized:
            # 인식 못 한 필드는 vsize/flags 헤더 포함 원본 바이트 그대로 보존.
            block_len = 8 + isize + 1 + vsize
            other += body[field_start : field_start + block_len]
            other_count += 1

        p += isize + 1 + vsize

    ape.other_fields = bytes(other)
    ape.other_fields_size = len(other)

    new_offset = tag_offset - tag_len
    ape.original_tag_size = tag_len

    # 헤더 존재 시(footer flags bit31) 추가로 32바이트 읽고 깎음.
    if footer_flags & APE_FLAG_HAS_HEADER:
        if new_offset < APE_FOOTER_SIZE:
            # 원본은 여기서 return (이미 ape 는 세팅됨). 보수적으로 보존만.
            file_tags.ape_tag = ape
            return new_offset
        new_offset -= APE_FOOTER_SIZE
        f.seek(new_offset)
        ape.header = f.read(APE_FOOTER_SIZE)
        ape.have_header = True
        ape.original_tag_size += APE_FOOTER_SIZE

    file_tags.ape_tag = ape
    return new_offset


def _store_ape_field(name: str, value: str, info: MP3GainTagInfo) -> bool:
    """APE 필드 하나를 info 에 반영. 인식했으면 True, 아니면 False(=otherFields 행).

    원본 ReadMP3APETag 의 if/else 사슬 대응. 매칭은 대소문자 무시(_stricmp).
    UNDO/MINMAX 는 원본 APE 경로처럼 고정 오프셋 슬라이싱으로 파싱.
    """
    upper = name.upper()

    if upper == "REPLAYGAIN_TRACK_GAIN":
        info.have_track_gain = True
        info.track_gain = _atof(value)
    elif upper == "REPLAYGAIN_TRACK_PEAK":
        info.have_track_peak = True
        info.track_peak = _atof(value)
    elif upper == "REPLAYGAIN_ALBUM_GAIN":
        info.have_album_gain = True
        info.album_gain = _atof(value)
    elif upper == "REPLAYGAIN_ALBUM_PEAK":
        info.have_album_peak = True
        info.album_peak = _atof(value)
    elif upper == "MP3GAIN_UNDO":
        # value 형식: "+003,+003,W" — 원본은 [0:4],[5:9],[10] 슬라이싱.
        info.have_undo = True
        info.undo_left = _atoi(value[0:4])
        info.undo_right = _atoi(value[5:9])
        info.undo_wrap = value[10:11] in ("w", "W")
    elif upper == "MP3GAIN_MINMAX":
        # value 형식: "001,153" — 원본은 [0:3],[4:7] 슬라이싱.
        info.have_min_max_gain = True
        info.min_gain = _atoi(value[0:3])
        info.max_gain = _atoi(value[4:7])
    elif upper == "MP3GAIN_ALBUM_MINMAX":
        info.have_album_min_max_gain = True
        info.album_min_gain = _atoi(value[0:3])
        info.album_max_gain = _atoi(value[4:7])
    else:
        return False
    return True


def _atof(s: str) -> float:
    """원본 atof 동작 모사: 앞부분의 숫자만 파싱, 실패 시 0.0."""
    s = s.strip()
    # atof 는 앞에서부터 파싱 가능한 데까지. 가장 단순·안전하게 시도.
    end = 0
    seen_dot = False
    seen_e = False
    for i, c in enumerate(s):
        if c in "+-" and (i == 0 or s[i - 1] in "eE"):
            end = i + 1
        elif c.isdigit():
            end = i + 1
        elif c == "." and not seen_dot and not seen_e:
            seen_dot = True
            end = i + 1
        elif c in "eE" and not seen_e and end > 0:
            seen_e = True
            end = i + 1
        else:
            break
    try:
        return float(s[:end]) if end > 0 else 0.0
    except ValueError:
        return 0.0


def _atoi(s: str) -> int:
    """원본 atoi 동작 모사: 앞부분의 정수만 파싱, 실패 시 0."""
    s = s.strip()
    end = 0
    for i, c in enumerate(s):
        if c in "+-" and i == 0:
            end = i + 1
        elif c.isdigit():
            end = i + 1
        else:
            break
    try:
        return int(s[:end]) if end > 0 and s[:end] not in ("+", "-") else 0
    except ValueError:
        return 0


def read_mp3gain_ape_tag(filename: str):
    """원본 ReadMP3GainAPETag.

    파일 끝에서부터 APE / Lyrics3v2(+ID3v1) / ID3v1 꼬리를 반복 감지하며
    tag_offset 을 위로 깎는다. 한 바퀴에 아무것도 안 깎이면 종료.
    최종 tag_offset 이 오디오 본문 끝(= 태그 시작) 위치.

    반환: (info, file_tags)
    """
    with open(filename, "rb") as f:
        f.seek(0, 2)  # SEEK_END
        file_size = f.tell()
        tag_offset = file_size

        info = MP3GainTagInfo()
        file_tags = FileTags()
        file_tags.lyrics3_tag_size = 0

        while True:
            offs_bk = tag_offset
            tag_offset = _read_ape_tag(f, info, file_tags, tag_offset)
            tag_offset = _read_lyrics3v2_tag(f, file_tags, tag_offset)
            tag_offset = _read_id3v1_tag(f, file_tags, tag_offset)
            if offs_bk == tag_offset:
                break

        if 0 <= tag_offset <= file_size:
            file_tags.tag_offset = tag_offset
        else:
            # 손상된 태그 정보: 파일 끝으로 기본 처리(원본 동작).
            file_tags.tag_offset = file_size

    return info, file_tags
