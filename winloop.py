# main.py
# Poll every 5 seconds: print activity snapshot + visible windows.

from time32 import *
import time
import datetime

POLL_SECONDS = 5

def main():
    try:
        while True:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("=" * 80)
            print(f"Snapshot @ {ts}")
            print("-" * 80)
            print_activity_snapshot()
            print("\n" + "-" * 80)
            print_window_list()
            print("=" * 80 + "\n")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nExiting on Ctrl+C.")

if __name__ == "__main__":
    main()
