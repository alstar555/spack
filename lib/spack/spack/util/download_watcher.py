# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os
import signal
import select
import time
import threading


def download_watcher_communicate(proc, download_path, watcher_timeout):
    """Monitor download stage directory activity to detect stalled downloads.
    Kills download processes that show no file activity in their staging 
    directory for longer than watcher_timeout seconds."""

    print(f"AAL: [Watcher] In download_watcher_communicate")

    last_activity = time.time()

    while proc.poll() is None:
        activity_found = False
        for root, _, files in os.walk(download_path):
            for f in files:
                path = os.path.join(root, f)
                mtime = os.path.getmtime(path)
                 # Break early if file was modified recently
                if now - mtime <= watcher_timeout:
                    last_activity = mtime
                    activity_found = True
                    break
            if activity_found:
                break

        if time.time() - last_activity >= watcher_timeout:
            print(f"AAL: [Watcher] Killing stalled download process {proc.pid}")
            try:
                proc.kill()
            except ProcessLookupError:
                print(f"AAL: [Watcher] Process {proc.pid} already exited")
            break
        time.sleep(5)

    out, err = proc.communicate()
    return out, err


def download_watcher_communicate2(proc, watcher_timeout):
    """Simply time out process for running too long."""

    print(f"AAL: [Watcher] In download_watcher_communicate")

    last_active = time.time()

    while proc.poll() is None:

        # Check stdout activity
        # try:
        #     ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 1.0)
        #     if ready:
        #         # The download has output and therfore isn't stalled
        #         last_active = time.time()
        #         print(f"AAL: [Watcher] The download has stdout and therfore isn't stalled")
        #     else:
        #         print(f"AAL: [Watcher] No stdout")
        # except Exception:
        #     print(f"AAL: [Watcher] Select failed")
        #     time.sleep(1)

        if time.time() - last_active >= watcher_timeout:
            print(f"AAL: [Watcher] Killing stalled download process {proc.pid}")
            proc.kill()
            break
        time.sleep(5)

    out, err = proc.communicate()
    return out, err

def watcher(pid: int, download_path:str, timeout:int):
    """
    Monitors the download path for activity. If the directory hasn't been updated
    in `timeout` seconds, the download is assumed to be stalled, and the process
    is killed to free up resources for Spack's parallel downloader.

    Args:
        pid (int): Process ID of the download process.
        download_path (str): Directory path where files are downloaded.
        timeout (int): Seconds of inactivity before considering the download stalled.
    """
    print(f"AAL: [Watcher] Monitoring: {download_path} (timeout = {timeout}s)")
    start_time = time.time()

    # Wait for the directory to appear
    while not os.path.exists(download_path):
        if time.time() - start_time > timeout:
            print(f"AAL: [Watcher] download_path never appeared: {download_path}")
            try:
                os.kill(pid, signal.SIGKILL)
                print(f"[Watcher] Killed process {pid} due to missing download path")
            except ProcessLookupError:
                print(f"[Watcher] Process {pid} already exited")
            return

    last_seen = time.time()
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
                                # Download is active 
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
                    print(f"AAL: KILLED PROCESS: {pid}")
                except ProcessLookupError:
                    print(f"[Watcher] Process {pid} already exited")
                return
            # Check every 5 seconds
            time.sleep(5)
    except Exception as e:
        print(f"[Watcher] Crashed: {e}")