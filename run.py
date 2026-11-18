"""Start Apex Steel Search.   python run.py   (or the built ApexSteelSearch.exe)"""
import os
import sys
import tempfile


def main():
    # Windowed .exe has no console: give libraries somewhere to write.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    selftest = "--selftest" in sys.argv
    if selftest:
        os.environ["APEX_SEARCH_HOME"] = tempfile.mkdtemp(prefix="apex_selftest_")
    from apex_search.gui.main_window import run_app
    sys.exit(run_app(selftest=selftest))


if __name__ == "__main__":
    main()
