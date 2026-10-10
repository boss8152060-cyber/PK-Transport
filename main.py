"""PK Transport launcher: opens PKT Data, PKT Train and PKT Analyze.  Run:  py -3.12 main.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pkt.ui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
