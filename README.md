# System Performance & Process Monitoring Tool

A Python-based system monitor that periodically collects CPU, memory and disk usage,
identifies the top CPU-consuming processes, prints a human-readable summary to the terminal,
and logs all metrics to a CSV file for later analysis.

## Features

- Samples system metrics every N seconds (configurable).
- Logs timestamp, overall CPU, memory, disk usage and top processes to `system_metrics.csv`.
- Uses a background thread for non-blocking monitoring.
- Thread-safe CSV writing using a lock.
- Tested on macOS.

## How to Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install psutil
python3 system_monitor.py
```

Press Ctrl + C to stop the monitor.
