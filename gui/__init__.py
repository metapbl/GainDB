"""gui/ — PySide6 프런트엔드 (8단계, clean-room).

원본 MP3GainGUI(VB6)의 화면 구성·동작만 관찰해 독립 구현한다. VB 코드는
옮기지 않는다(CLAUDE.md 2.2). 코어(gaindb)는 subprocess 가 아니라 직접
import 한다. GUI 는 계산하지 않으며, gaindb.api 의 네 함수만 호출한다.
"""
