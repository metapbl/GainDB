r"""gui/i18n.py — 다국어(한글/영문) 국제화 인프라(clean-room).

원본 MP3GainGUI 의 basLocalizer(런타임 문자열 테이블 교체 + 영문 폴백 +
언어 메뉴 수동 전환 + 선택 언어 영속화)를 Qt 표준 국제화 메커니즘으로 재현한다.
원본은 VB6 에 표준 i18n 이 없어 외부 INI + 자체 조회 함수(GetLocalString)를
직접 만들었으나, 우리는 Qt 표준(tr() + .qm + QTranslator)이 있으므로 그것을
쓴다 — 재현 대상은 "동작"(런타임 교체·폴백·수동 전환·영속화)이지 언어 제약의
산물(자체 조회 함수)이 아니다(8단계 아키텍처 결정과 일관).

지원 언어(합의): 영문(en, 소스 원문 = 번역파일 없음) + 한국어(ko, gaindb_ko.qm).
tr() 로 감싼 문자열은 번역이 없으면 원문(영문)을 그대로 반환하므로 영문 폴백이
자동 확보된다(원본 GetLocalString 의 기본값 폴백과 동일 효과).

초기 언어 결정(합의): QSettings i18n/language 키가 있으면(사용자가 한 번이라도
명시 선택했으면) 그 값을 최우선. 없으면(첫 실행) QLocale.system() 을 감지해
한국어 환경이면 ko, 그 외 en. 사용자가 메뉴에서 고르는 순간 저장되어 이후
자동 감지가 사용자 선택을 덮지 않는다.

즉시 전환(합의): install_translator 가 기존 translator 를 제거하고 새 것을
설치하면 Qt 가 활성 위젯에 QEvent.LanguageChange 를 흘린다. 각 위젯은
changeEvent 에서 이를 잡아 retranslateUi 로 자기 문자열을 다시 tr() 한다.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QLocale, QSettings, QTranslator

# QSettings 조직/앱 이름(main_window 와 동일 매체를 써 설정을 한곳에 모은다).
_SETTINGS_ORG = "GaindB"
_SETTINGS_APP = "GaindB"

# 지원 언어 코드. en 은 소스 원문이라 .qm 이 없다(폴백=원문).
SUPPORTED = ("en", "ko")
DEFAULT_LANGUAGE = "en"

# 설치된 QTranslator 를 모듈 전역으로 보유(GC 방지 + 재설치 시 제거용).
# QApplication 은 translator 를 약참조만 잡으므로 파이썬 측에서 살려둬야 한다.
_active_translator: QTranslator | None = None


def _base_dir() -> str:
    """리소스 기준 디렉터리. PyInstaller onefile 이면 _MEIPASS, 아니면 이 파일 폴더.

    gui/resources.py 와 같은 패턴(배포 대비). .qm 은 gui/translations/ 아래 둔다.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, "gui", "translations")
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "translations")


def qm_path(lang: str) -> str:
    """언어 코드에 대응하는 .qm 파일 경로(존재 여부는 호출자가 확인)."""
    return os.path.join(_base_dir(), f"gaindb_{lang}.qm")


def resolve_language() -> str:
    """시작 시 사용할 언어를 결정한다(저장값 우선, 없으면 시스템 로케일 감지).

    - QSettings i18n/language 가 SUPPORTED 안의 값이면 그것(사용자 명시 선택).
    - 없거나 미지원 값이면 QLocale.system() 이 ko 로 시작하면 ko, 그 외 en.
    """
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    saved = settings.value("i18n/language", "", type=str)
    if saved in SUPPORTED:
        return saved

    sys_name = QLocale.system().name()  # 예: "ko_KR", "en_US"
    if sys_name.lower().startswith("ko"):
        return "ko"
    return DEFAULT_LANGUAGE


def save_language(lang: str) -> None:
    """사용자가 고른 언어를 QSettings 에 영속화한다(원본 LanguageFile 저장 대응)."""
    if lang not in SUPPORTED:
        lang = DEFAULT_LANGUAGE
    settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    settings.setValue("i18n/language", lang)


def install_translator(app, lang: str) -> str:
    """app 에 lang 번역을 설치한다. 반환값은 실제로 적용된 언어 코드.

    기존 translator 를 먼저 제거한 뒤(중첩 방지) 새 것을 설치한다. en 이거나
    .qm 로드 실패면 translator 없이 원문(영문)으로 동작한다 — 이때 반환은 "en".
    설치가 성공하면 Qt 가 활성 위젯에 LanguageChange 이벤트를 흘린다.
    """
    global _active_translator

    if _active_translator is not None:
        app.removeTranslator(_active_translator)
        _active_translator = None

    if lang == "en":
        return "en"

    path = qm_path(lang)
    translator = QTranslator(app)
    if os.path.exists(path) and translator.load(path):
        app.installTranslator(translator)
        _active_translator = translator
        return lang

    # .qm 이 없거나 로드 실패: 원문(영문) 폴백. 조용히 en 으로 떨어진다
    # (원본도 로드 실패 시 "will continue, but in English").
    return "en"
