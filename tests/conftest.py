import os

# Qt widgets need a display; "offscreen" renders in memory so UI tests run headless (and in CI).
# Must be set before the first QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
