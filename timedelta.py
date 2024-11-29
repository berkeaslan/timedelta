# timedelta by Berke Aslan
# version: 0.1.0 (pre-alpha)

import time
from datetime import datetime

def format_delta(delta):
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def save_to_log(start_time, end_time, delta, did):
    with open('timedelta.log', 'a') as log_file:
        log_entry = f"Start: {start_time.strftime('%d-%m-%Y %H:%M:%S')}, "
        log_entry += f"End: {end_time.strftime('%d-%m-%Y %H:%M:%S')}, "
        log_entry += f"Delta: {format_delta(delta)}, "
        log_entry += f"Did: {did}\n"
        log_file.write(log_entry)

def timer_loop():
    start_time = datetime.now()

    try:
        while True:
            current_time = datetime.now()
            delta = current_time - start_time

            print(f"\rDelta: {format_delta(delta)} | Press Ctrl+C once to log | Press Ctrl+C twice to stop", end="", flush=True)

            time.sleep(1)

    except KeyboardInterrupt:
        end_time = datetime.now()
        return start_time, end_time, end_time - start_time

def main():
    while True:
        start_time, end_time, delta = timer_loop()

        did = input("\nEnter what you did: ")
        save_to_log(start_time, end_time, delta, did)

        print(f"\r'{did}' saved. Delta: {format_delta(delta)}", end="", flush=True)
        time.sleep(2)

        print("\nStarting new timer...", end="", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main()