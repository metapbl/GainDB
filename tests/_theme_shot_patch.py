# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""빌드 결과 캡처용 임시 코드를 gui/__main__.py 에 넣는다 (macOS 러너·로컬 확인).

실행 파일에는 외부 스크립트를 붙일 수 없어 진입점을 잠깐 고쳐 빌드한다. 고친
파일은 커밋하지 않는다. 로컬에서는 확인 후 `git checkout -- gui/__main__.py` 뒤
다시 빌드한다. 캡처 저장 폴더는 환경변수 THEME_SHOT 으로 받는다.
"""

from pathlib import Path

SNIPPET = '''    import os
    if os.environ.get("THEME_SHOT"):
        from pathlib import Path
        from PySide6.QtCore import QTimer
        def _shots():
            for mode in ("dark", "light"):
                theme.apply_theme(app, mode)
                app.processEvents()
                window.grab().save(str(Path(os.environ["THEME_SHOT"]) / f"{mode}.png"))
            app.quit()
        QTimer.singleShot(1500, _shots)
'''

entry = Path(__file__).resolve().parent.parent / "gui" / "__main__.py"
source = entry.read_text(encoding="utf-8")
marker = "    return app.exec()"
assert marker in source
entry.write_text(source.replace(marker, SNIPPET + marker, 1), encoding="utf-8")
