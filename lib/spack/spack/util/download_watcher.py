# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import signal
import select
from subprocess import Popen
from typing import Tuple
import time
import threading


def download_watcher_communicate(proc: Popen, download_path: str, watcher_timeout:int) -> Tuple[str, str]:
    """
    Monitor download stage directory activity to detect stalled downloads.
    Kills the process if no files in the stage download directory
    have been modified within the last `watcher_timeout` seconds.

    Args:
        proc (subprocess.Popen): The subprocess to monitor.
        download_path (str): Path to the directory being watched for activity.
        watcher_timeout (int): Timeout in seconds for watchdog process monitoring downloads

    Returns:
        Tuple[str, str]: The output and error from the process.
    """

    print(f"AAL: [Watcher] In download_watcher_communicate")

    last_activity = None

    while proc.poll() is None:
        # Waiting for initial directory to create
        if not os.path.isdir(download_path):
            time.sleep(5)
            continue
            
        activity_found = False
        for root, _, files in os.walk(download_path):
            print(f"AAL: [Watcher] Scanning directory: {root} with {len(files)} files in dir {download_path}")
            for f in files:
                path = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(path)
                    time_since_modified = time.time() - mtime
                    print(f"AAL: [Watcher] File last modified {time_since_modified} sec ago")

                    # Update last_activity to most recent mtime
                    if last_activity is None or mtime > last_activity:
                        last_activity = mtime

                    # Break early if file was modified recently
                    if time_since_modified <= watcher_timeout:
                        print(f"AAL: [Watcher] Time file last modified: {time_since_modified} seconds ago")
                        last_activity = mtime
                        activity_found = True
                        break
                except FileNotFoundError:
                    print(f"AAL: [Watcher] File was not found") 
            if activity_found:
                break

        if last_activity is None:
            # No activity detected yet
            # print("AAL: [Watcher] No activity detected yet")
            continue

        time_since_modified = time.time() - last_activity
        print(f"AAL: [Watcher] time_since_modified: {time_since_modified}") 
        if time_since_modified >= watcher_timeout:
            try:
                print(f"AAL: [Watcher] Killing stalled download process {proc.pid}")
                proc.kill()
            except ProcessLookupError:
                print(f"AAL: [Watcher] ProcessLookupError: Process {proc.pid} already exited")
            break

        # Check every 5 seconds
        print(f"AAL: [Watcher] Check every 5 sec")
        time.sleep(5)

    print(f"AAL: [Watcher] Download Watcher Finished, Process Ended")
    out, err = proc.communicate()
    return out, err