import os
import time
import queue
import threading
import pandas as pd
import numpy as np
from collections import deque

# File paths
CSV_FILE = os.path.join("realKnownCause", "machine_temperature_system_failure.csv")
PARQUET_OUTPUT = "features.parquet"
JSON_OUTPUT = "features.json"

# Window settings (5-minute granularity, 12 steps = 60 minutes)
WINDOW_SIZE = 12

# Create thread-safe queue for events
event_queue = queue.Queue(maxsize=1000)

def producer(file_path, q):
    """
    Simulates a streaming producer (like Kafka) by reading the CSV file
    and emitting each record into the queue.
    """
    print("[Producer] Starting stream producer...")
    if not os.path.exists(file_path):
        print(f"[Producer] Error: CSV file not found at {file_path}")
        q.put(None)
        return

    df = pd.read_csv(file_path)
    total_records = len(df)
    print(f"[Producer] Loaded {total_records} records. Beginning streaming...")

    for idx, row in df.iterrows():
        # Convert pandas row to dictionary
        event = {
            "timestamp": row["timestamp"],
            "value": float(row["value"])
        }
        # Push to queue (blocks if queue is full)
        q.put(event)

        # Small delay to simulate streaming (0.0001 seconds per record)
        time.sleep(0.0001)

        if (idx + 1) % 5000 == 0:
            print(f"[Producer] Emitted {idx + 1}/{total_records} events.")

    # Push Sentinel value to notify Consumer that stream is finished
    q.put(None)
    print("[Producer] Stream finished emitting all records.")

def consumer(q, window_size, processed_data):
    """
    Simulates a streaming consumer (like Flink/Spark) by reading from the queue,
    calculating rolling metrics on the window, and preparing outputs.
    """
    print("[Consumer] Starting stream consumer...")
    window = deque(maxlen=window_size)
    prev_value = None
    count = 0

    while True:
        event = q.get()
        if event is None:  # Sentinel check
            q.task_done()
            break

        timestamp = event["timestamp"]
        value = event["value"]

        # Append to sliding window
        window.append(value)
        count += 1

        # Calculate streaming features
        rolling_mean = float(np.mean(window))
        # numpy.std on small arrays is fast; ddof=0 or 1. Let's use ddof=0 to handle len=1 without NaN
        rolling_std = float(np.std(window)) if len(window) > 1 else 0.0
        
        # Rate of change: (current_value - prev_value)
        rate_of_change = (value - prev_value) if prev_value is not None else 0.0
        prev_value = value

        # Save processed record
        processed_data.append({
            "timestamp": timestamp,
            "value": value,
            "rolling_mean": rolling_mean,
            "rolling_std": rolling_std,
            "rate_of_change": rate_of_change
        })

        q.task_done()
        if count % 5000 == 0:
            print(f"[Consumer] Processed {count} events. Current Window Size: {len(window)}")

    print(f"[Consumer] Consumer finished. Processed {count} total events.")

def main():
    start_time = time.time()
    processed_events = []

    # Initialize threads
    prod_thread = threading.Thread(target=producer, args=(CSV_FILE, event_queue))
    cons_thread = threading.Thread(target=consumer, args=(event_queue, WINDOW_SIZE, processed_events))

    # Start threads
    prod_thread.start()
    cons_thread.start()

    # Wait for threads to finish
    prod_thread.join()
    cons_thread.join()

    # Convert to DataFrame
    df_features = pd.DataFrame(processed_events)
    print(f"\n[Pipeline] Features computed successfully. Shape: {df_features.shape}")

    # Output to JSON
    print(f"[Pipeline] Exporting features to {JSON_OUTPUT}...")
    df_features.to_json(JSON_OUTPUT, orient="records", indent=2)
    print(f"[Pipeline] Saved {JSON_OUTPUT}")

    # Output to Parquet if possible
    print(f"[Pipeline] Exporting features to {PARQUET_OUTPUT}...")
    try:
        df_features.to_parquet(PARQUET_OUTPUT, index=False)
        print(f"[Pipeline] Saved {PARQUET_OUTPUT}")
    except ImportError:
        print("[Pipeline] Warning: 'pyarrow' or 'fastparquet' is required to save parquet files.")
        print("[Pipeline] Attempting to install 'pyarrow' to fulfill assignment requirement...")
        # We will let the execution script handle installation, but we will catch it here.

    duration = time.time() - start_time
    print(f"[Pipeline] Total execution time: {duration:.2f} seconds.")

if __name__ == "__main__":
    main()
