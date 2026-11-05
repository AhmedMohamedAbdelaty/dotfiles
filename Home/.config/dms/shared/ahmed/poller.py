#!/usr/bin/python3
"""Single-owner status polling for the Dux trial."""
import asyncio
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time

HOME = Path.home()
CACHE = HOME / ".cache/dux-ahmed-status"
JOBS = {
    "prayer": (30, [str(HOME / ".config/waybar/prayertimes.py")]),
    "timer": (1, [str(HOME / ".config/waybar/timer-manager.py"), "status"]),
    "productivity": (30, [str(HOME / ".config/waybar/productivity-manager.py"), "status"]),
}


def publish(name, value):
    value["_duxUpdated"] = time.time()
    fd, path = tempfile.mkstemp(prefix="." + name + "-", dir=CACHE)
    try:
        with os.fdopen(fd, "w") as file:
            json.dump(value, file, ensure_ascii=False)
            file.write("\n")
        os.replace(path, CACHE / (name + ".json"))
    finally:
        if os.path.exists(path):
            os.unlink(path)


async def poll(name, interval, command):
    while True:
        process = None
        try:
            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            output, _ = await process.communicate()
            if process.returncode:
                raise RuntimeError("status command failed")
            value = json.loads(output)
            if not isinstance(value, dict) or not isinstance(value.get("text"), str):
                raise ValueError("invalid status")
        except asyncio.CancelledError:
            if process and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 5)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            raise
        except (OSError, ValueError, RuntimeError):
            value = {"text": name + " unavailable"}
        try:
            publish(name, value)
        except OSError as exc:
            # A cache write failure must not stop future reminder checks.
            print(f"{name}: status cache write failed: {exc}", file=sys.stderr, flush=True)
        await asyncio.sleep(interval)


async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    tasks = [asyncio.create_task(poll(name, *job)) for name, job in JOBS.items()]
    await stop.wait()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(CACHE / "poller.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("Dux status poller already running")
        asyncio.run(main())
