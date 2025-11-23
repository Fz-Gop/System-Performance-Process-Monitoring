import threading
import time
import csv
from datetime import datetime

import psutil  # third-party library for system and process info


class SystemMonitor:
    """
    A medium-complexity system monitoring tool.

    - Periodically collects CPU, memory and disk usage.
    - Finds top N processes by CPU usage.
    - Logs data to a CSV file.
    - Prints a human-readable summary to the terminal.
    - Runs in a background thread until stopped.
    """

    def __init__(self, sample_interval=2.0, log_file="system_metrics.csv", top_n_processes=5):
        """
        :param sample_interval: Time (in seconds) between two measurements.
        :param log_file: CSV file where metrics will be saved.
        :param top_n_processes: How many top CPU-consuming processes to record.
        """
        self.sample_interval = sample_interval
        self.log_file = log_file
        self.top_n_processes = top_n_processes

        self._stop_event = threading.Event()
        self._writer_lock = threading.Lock()
        self._initialized_log = False
        self._thread = None

    def _init_log_file(self):
        """Create the CSV file and write header row once."""
        with self._writer_lock:
            if not self._initialized_log:
                with open(self.log_file, mode="w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp",
                        "cpu_percent",
                        "memory_percent",
                        "disk_percent",
                        "top_processes"  # stored as a string summary
                    ])
                self._initialized_log = True

    def collect_snapshot(self):
        """
        Collect one snapshot of system metrics:
        - timestamp
        - overall CPU, memory, disk usage
        - top N processes by CPU usage
        """
        timestamp = datetime.now().isoformat(timespec="seconds")

        # Overall system stats
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        memory_percent = mem.percent

        # On macOS, "/" is the root filesystem
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent

        # Collect per-process stats
        processes = []
        for proc in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info

                # Clean/normalize CPU and memory so they are NEVER None
                cpu_val = info.get("cpu_percent")
                mem_val = info.get("memory_percent")

                if cpu_val is None:
                    cpu_val = 0.0
                if mem_val is None:
                    mem_val = 0.0

                info["cpu_percent"] = float(cpu_val)
                info["memory_percent"] = float(mem_val)

                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Some processes may disappear or be protected; just skip them
                continue

        # Sort processes by CPU usage (highest first)
        processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
        top_processes = processes[:self.top_n_processes]

        # Build human-readable summary of top processes
        top_proc_summary = "; ".join(
            f"{p.get('name', 'unknown')}[pid={p.get('pid')}]: "
            f"CPU={p['cpu_percent']:.1f}%, MEM={p['memory_percent']:.1f}%"
            for p in top_processes
        )

        snapshot = {
            "timestamp": timestamp,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "top_processes_summary": top_proc_summary,
        }
        return snapshot

    def log_snapshot(self, snapshot):
        """Append one snapshot row to the CSV log file."""
        self._init_log_file()
        with self._writer_lock:
            with open(self.log_file, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    snapshot["timestamp"],
                    f"{snapshot['cpu_percent']:.1f}",
                    f"{snapshot['memory_percent']:.1f}",
                    f"{snapshot['disk_percent']:.1f}",
                    snapshot["top_processes_summary"],
                ])

    def print_snapshot(self, snapshot):
        """Print a human-friendly summary of the snapshot to the terminal."""
        print("-" * 60)
        print(f"Time:          {snapshot['timestamp']}")
        print(f"CPU Usage:     {snapshot['cpu_percent']:.1f}%")
        print(f"Memory Usage:  {snapshot['memory_percent']:.1f}%")
        print(f"Disk Usage:    {snapshot['disk_percent']:.1f}%")
        print("Top processes (by CPU):")
        if snapshot["top_processes_summary"]:
            for proc_text in snapshot["top_processes_summary"].split("; "):
                print(f"  - {proc_text}")
        else:
            print("  (No process info available)")

    def _monitor_loop(self):
        """Internal loop that runs in a background thread and collects data repeatedly."""
        self._init_log_file()
        while not self._stop_event.is_set():
            snapshot = self.collect_snapshot()
            self.log_snapshot(snapshot)
            self.print_snapshot(snapshot)

            # Sleep in small chunks so we can stop quickly if needed
            total_sleep = self.sample_interval
            step = 0.1
            steps = int(total_sleep / step)
            for _ in range(steps):
                if self._stop_event.is_set():
                    break
                time.sleep(step)

    def start(self):
        """Start the monitoring in a background (daemon) thread."""
        if self._thread is not None and self._thread.is_alive():
            print("System monitor is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"System monitor started. Logging to '{self.log_file}'. Press Ctrl+C to stop.")

    def stop(self):
        """Signal the monitoring thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        print("System monitor stopped.")


def main():
    # You can tweak these parameters if you want
    monitor = SystemMonitor(
        sample_interval=2.0,          # every 2 seconds
        log_file="system_metrics.csv",
        top_n_processes=5,
    )

    try:
        monitor.start()
        # Keep the main thread alive until user presses Ctrl+C
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nReceived Ctrl+C, stopping monitor...")
        monitor.stop()


if __name__ == "__main__":
    main()
