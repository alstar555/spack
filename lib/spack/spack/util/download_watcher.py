# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import time
import signal
import threading

def watcher(pid: int, download_path:str, timeout:int):
    """
    Monitors the download path for activity. If the directory hasn't been updated
    in `timeout` seconds, the download is assumed to be stalled, and the process
    is killed to free up resources for Spack's parallel downloader.

    Args:
        pid (int): Process ID of the download process.
        download_path (str): Directory path where files are being downloaded.
        timeout (int): Seconds of inactivity before considering the download stalled.
    """
    print(f"AAL: [Watcher] Monitoring: {download_path} (timeout = {timeout}s)")
    last_seen = time.time()

    # Wait up to 60 seconds for the directory to appear
    for _ in range(20):
        if os.path.exists(download_path):
            print("[Watcher] download_path appeared")
            break
        time.sleep(3)
    else:
        print(f"[Watcher] download_path never appeared: {download_path}")
        return

    try:
        while True:
            now = time.time()
            recent_activity_found = False

            try:
                for root, _, files in os.walk(download_path):
                    for f in files:
                        path = os.path.join(root, f)
                        try:
                            mtime = os.path.getmtime(path)
                            if now - mtime <= timeout:
                                # Recent modification found, reset and sleep
                                recent_activity_found = True
                                break
                        except FileNotFoundError:
                            continue 
                    if recent_activity_found:
                        break
            except Exception as e:
                print(f"[Watcher] Error walking directory: {e}")

            if not recent_activity_found:
                print(f"[Watcher] No recent file activity. Killing process {pid}")
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    print(f"[Watcher] Process {pid} already exited")
                return
            # Check every 5 seconds
            time.sleep(5)
    except Exception as e:
        print(f"[Watcher] Crashed: {e}")