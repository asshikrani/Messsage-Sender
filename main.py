# AS message_sender_gui.py
# Requirements:
#   pip install pyqt5 pyautogui
# Packaging (optional):
#   pyinstaller --onefile --noconsole --name "name of file" --icon=logo.ico AS_message_sender_gui.py

import sys
import time
import threading
import pyautogui

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QPushButton, QCheckBox, QFrame, QTextEdit,
    QMessageBox, QGroupBox, QSizePolicy
)

# Safety: moving mouse to top-left corner aborts PyAutoGUI actions
pyautogui.FAILSAFE = True

# Branding colors (green theme)
APP_PRIMARY = "#0FA07B"   # main button / accent
APP_SECONDARY = "#31E08F" # hover / highlight
APP_BG = "#071E18"        # overall background
APP_CARD = "#0C2E27"      # cards/panels
APP_BORDER = "#18453F"    # borders
APP_TEXT = "#E8FFF7"      # main text
APP_MUTED = "#9EDCCB"     # muted text

# ---------- Worker Thread ----------
class SenderWorker(QThread):
    progress = pyqtSignal(int)      # number of messages sent
    finished = pyqtSignal(str)      # finished message
    aborted = pyqtSignal(str)       # abort reason

    def __init__(self, message: str, total: int, delay: float, stop_flag: threading.Event):
        super().__init__()
        self.message = message
        self.total = total
        self.delay = delay
        self.stop_flag = stop_flag

    def run(self):
        try:
            # Send messages in a loop. Respect stop_flag at each step.
            for i in range(self.total):
                if self.stop_flag.is_set():
                    self.aborted.emit("Stopped by user.")
                    return
                # Type and send
                pyautogui.typewrite(self.message)
                pyautogui.press("enter")
                self.progress.emit(i + 1)
                # Sleep - ensure we don't starve the event loop (small yields)
                time.sleep(max(self.delay, 0.0))
            self.finished.emit("All messages sent successfully.")
        except pyautogui.FailSafeException:
            self.aborted.emit("Aborted: PyAutoGUI failsafe triggered (mouse to top-left).")
        except Exception as e:
            self.aborted.emit(f"Error: {e}")


# ---------- Main App ----------
class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AS Message_Sender")
        self.resize(900, 560)
        self.setMinimumSize(1120, 740)

        # threading control
        self.stop_flag = threading.Event()
        self.worker = None

        # countdown timer for preparation
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)
        self._countdown_left = 0

        # styling & components
        self._apply_global_style()
        self._build_ui()

    # ---------- Styling ----------
    def _apply_global_style(self):
        # Set Segoe UI if available (OS will fallback if not)
        app_font = QFont("Segoe UI", 10)
        QApplication.instance().setFont(app_font)

        # QSS: keep it modern, green theme, rounded cards
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {APP_BG};
                color: {APP_TEXT};
            }}
            QGroupBox {{
                background-color: {APP_CARD};
                border: 1px solid {APP_BORDER};
                border-radius: 12px;
                margin-top: 27px;
                padding: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                color: {APP_MUTED};
                font-weight: 700;
            }}
            QLabel#headline {{
                font-size: 20px;
                font-weight: 800;
                color: {APP_SECONDARY};
            }}
            QLabel#muted {{
                color: {APP_MUTED};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{
                background-color: #05281f;
                border: 1px solid #14493b;
                border-radius: 8px;
                padding: 8px;
                color: {APP_TEXT};
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
                border: 1px solid {APP_SECONDARY};
            }}
            QPushButton {{
                background-color: {APP_PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 700;
                min-width: 96px;
            }}
            QPushButton:hover {{
                background-color: {APP_SECONDARY};
            }}
            QPushButton:disabled {{
                background-color: #18433A;
                color: #7fbfb0;
            }}
            QTextEdit {{
                background-color: #05281f;
            }}
            QFrame#divider {{
                background-color: {APP_BORDER};
                min-height: 1px;
                max-height: 1px;
            }}
        """)

    # ---------- UI Build ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("AS_Message Sender")
        title.setObjectName("headline")
        subtitle = QLabel("Automate messaging • Safe • Fast")
        subtitle.setObjectName("muted")
        subtitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        brand = QLabel("Powered by Ahmad Siddique  •  https://ahmadsiddique.vercel.app/")
        brand.setObjectName("muted")
        brand.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header.addWidget(title)
        header.addWidget(subtitle)
        header.addWidget(brand)
        root.addLayout(header)

        # top divider
        div = QFrame()
        div.setObjectName("divider")
        root.addWidget(div)

        # Main horizontal area: left = inputs, right = controls + logs
        main_area = QHBoxLayout()
        main_area.setSpacing(14)
        root.addLayout(main_area, 1)

        # ---------- LEFT: Inputs Card ----------
        inputs_card = QGroupBox("Message Settings")
        inputs_layout = QVBoxLayout()
        inputs_layout.setSpacing(10)

        # Message input
        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Type the message text to send...")
        inputs_layout.addWidget(self._labeled("Message", self.message_edit))

        # Count + Delay row
        row1 = QHBoxLayout()
        # Times to send
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000000)
        self.count_spin.setValue(10)
        row1.addWidget(self._labeled("Times to send", self.count_spin))

        # Delay
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 10.0)
        self.delay_spin.setDecimals(2)
        self.delay_spin.setSingleStep(0.05)
        self.delay_spin.setValue(0.50)
        row1.addWidget(self._labeled("Delay (s)", self.delay_spin))

        inputs_layout.addLayout(row1)

        # Auto-delay checkbox
        self.auto_delay_cb = QCheckBox("Auto choose sensible delay if set to 0")
        self.auto_delay_cb.setChecked(True)
        self.auto_delay_cb.setToolTip("If checked and Delay is set to 0.00, the app will pick a safe default. "
                                      "Fast PC → 0.10 • Safer/slower → 0.40")
        inputs_layout.addWidget(self.auto_delay_cb)

        # Preparation time
        self.prep_spin = QSpinBox()
        self.prep_spin.setRange(0, 120)
        self.prep_spin.setValue(15)
        inputs_layout.addWidget(self._labeled("Preparation time (seconds)", self.prep_spin))

        # Helpful tips
        tips = QTextEdit()
        tips.setReadOnly(True)
        tips.setMinimumHeight(110)
        tips.setText(
            "Delay guidance:\n"
            " • Fast PC: 0.10 seconds\n"
            " • Safer/slower: 0.40 seconds\n\n"
            "Time to Send:\n"
            " • Enter number how much time you want to send message\n"
            "\n"
            "Preperation Time:\n"
            " • Time required to move your cursor to the input field\n"
            " • Generally you can setup this to 15sec\n\n"
            "Safety & Tips:\n"
            " • For Instant Stop Move Cursor Top-Left Corner of Display.\n"
            " • You can press Stop anytime in the app.\n"
            " • PyAutoGUI failsafe is ON — move mouse to top-left quickly to abort.\n"
            " • Test first in Notepad or a safe input field.\n"
            " • Do not include time suffixes (enter 0.1, not '0.1s')."
        )
        inputs_layout.addWidget(self._labeled("Helpful Tips", tips))

        inputs_card.setLayout(inputs_layout)
        inputs_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_area.addWidget(inputs_card, 45)  # left column ~45%

        # ---------- RIGHT: Controls & Status ----------
        status_card = QGroupBox("Run & Status")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(12)

        # Buttons row
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_run)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_run)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        status_layout.addLayout(btn_row)

        # Countdown & progress
        self.countdown_label = QLabel("Ready.")
        self.countdown_label.setObjectName("muted")
        status_layout.addWidget(self.countdown_label)

        self.progress_label = QLabel("Progress: 0 / 0")
        status_layout.addWidget(self.progress_label)

        # Log area
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        status_layout.addWidget(self.log, 1)

        # Extra quick controls row (clear log, test typing)
        quick_row = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(lambda: self.log.clear())
        self.test_btn = QPushButton("Test Type")
        self.test_btn.clicked.connect(self._test_type)
        quick_row.addWidget(self.clear_log_btn)
        quick_row.addWidget(self.test_btn)
        status_layout.addLayout(quick_row)

        status_card.setLayout(status_layout)
        status_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_area.addWidget(status_card, 55)  # right column ~55%

        # Footer
        footer = QLabel("Tip: Test in Notepad first. Move mouse to top-left anytime to abort (PyAutoGUI failsafe).")
        footer.setObjectName("muted")
        root.addWidget(footer)

    # helper to return widget wrapped with a small label
    def _labeled(self, title: str, widget):
        wrapper = QVBoxLayout()
        lbl = QLabel(title)
        lbl.setObjectName("muted")
        wrapper.addWidget(lbl)
        wrapper.addWidget(widget)
        container = QWidget()
        container.setLayout(wrapper)
        return container

    # ---------- Run control logic ----------
    def start_run(self):
        message = self.message_edit.text().strip()
        total = int(self.count_spin.value())
        delay = float(self.delay_spin.value())

        # Auto-delay behavior
        if self.auto_delay_cb.isChecked() and delay == 0.0:
            delay = 0.5  # sensible default

        # validation
        if not message:
            self._warn("Please enter a message to send.")
            return
        if total <= 0:
            self._warn("Times to send must be at least 1.")
            return
        if delay < 0:
            self._warn("Delay cannot be negative.")
            return

        # prepare UI & flags
        self._set_inputs_enabled(False)
        self.stop_flag.clear()
        self.progress_label.setText(f"Progress: 0 / {total}")
        self.log.clear()
        short_msg = (message[:80] + "…") if len(message) > 80 else message
        self._append_log(f"Configured: message='{short_msg}', count={total}, delay={delay:.2f}s")

        # Start countdown
        prep = int(self.prep_spin.value())
        self._countdown_left = prep
        if prep > 0:
            self.countdown_label.setText(f"Starting in {prep} s… place your cursor in the target input.")
            self.countdown_timer.start(1000)
        else:
            self.countdown_label.setText("Starting now…")
            self._begin_worker(message, total, delay)

    def _tick_countdown(self):
        self._countdown_left -= 1
        if self._countdown_left > 0:
            self.countdown_label.setText(f"Starting in {self._countdown_left} s… place your cursor in the target input.")
        else:
            self.countdown_timer.stop()
            self.countdown_label.setText("Starting now…")
            # pull current values (user might have tweaked)
            message = self.message_edit.text().strip()
            total = int(self.count_spin.value())
            delay = float(self.delay_spin.value())
            if self.auto_delay_cb.isChecked() and delay == 0.0:
                delay = 0.5
            self._begin_worker(message, total, delay)

    def _begin_worker(self, message, total, delay):
        # Start the thread
        self.worker = SenderWorker(message, total, delay, self.stop_flag)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.aborted.connect(self._on_aborted)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.worker.start()
        self._append_log("Worker started. Use Stop button or move mouse to top-left to abort.")

    def stop_run(self):
        if self.worker and self.worker.isRunning():
            self.stop_flag.set()
            self._append_log("Stop requested by user...")
            self.countdown_timer.stop()
        else:
            self._append_log("Nothing is running to stop.")

    # ---------- Worker callbacks ----------
    def _on_progress(self, sent):
        total = int(self.count_spin.value())
        self.progress_label.setText(f"Progress: {sent} / {total}")

    def _on_finished(self, msg):
        self._append_log(f"✅ {msg}")
        self._reset_ui_after_run()

    def _on_aborted(self, reason):
        self._append_log(f"⛔ {reason}")
        self._reset_ui_after_run()

    def _reset_ui_after_run(self):
        self.stop_flag.set()
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.countdown_label.setText("Ready.")
        self._set_inputs_enabled(True)
        self.worker = None

    def _set_inputs_enabled(self, enabled: bool):
        for w in [self.message_edit, self.count_spin, self.delay_spin, self.auto_delay_cb, self.prep_spin]:
            w.setEnabled(enabled)
        # disable start if countdown is active
        self.start_btn.setEnabled(enabled and not self.countdown_timer.isActive())

    # ---------- Utilities ----------
    def _append_log(self, text: str):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {text}")

    def _warn(self, text: str):
        QMessageBox.warning(self, "Validation", text)

    def _test_type(self):
        """Quick test: type a short text immediately (useful for quick verification)."""
        try:
            self._append_log("Performing quick type test in 3 seconds. Place the cursor into target input.")
            time.sleep(3)
            pyautogui.typewrite("Test ▶️")
            pyautogui.press("enter")
            self._append_log("Test typed.")
        except pyautogui.FailSafeException:
            self._append_log("Test aborted: PyAutoGUI failsafe triggered.")
        except Exception as e:
            self._append_log(f"Test error: {e}")


# ---------- Main ----------
def main():
    app = QApplication(sys.argv)
    win = App()
    win.show()
    # For PyQt5, use exec_()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

