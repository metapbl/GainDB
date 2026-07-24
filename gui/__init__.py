# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""gui/ — PySide6 프런트엔드 (8단계, 독립 구현).

메인 창의 화면 구성·동작을 관찰해 독립 구현한다. 코어(gaindb)는 subprocess 가
아니라 직접 import 한다. GUI 는 계산하지 않으며, gaindb.api 의 네 함수만
호출한다.
"""