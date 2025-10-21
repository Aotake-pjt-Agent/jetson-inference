#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jetson WebRTC Object Detection Server
Real-time object detection with optional spreadsheet logging.

Copyright (c) 2025, Aotake Project. All rights reserved.
"""

import os
import sys
import argparse
import queue
import threading
import time
from datetime import datetime
from typing import List, Optional

# Ensure UTF-8 output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")
os.environ.setdefault("LANG", "C.UTF-8")

try:
    import gspread
except ImportError:  # pragma: no cover - optional dependency
    gspread = None

from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput, Log


SHEET_SUPPORT_AVAILABLE = gspread is not None


class SpreadsheetReporter:
    """
    Append detection rows to a Google Spreadsheet from a background thread.
    """

    def __init__(
        self,
        credentials_path: str,
        spreadsheet_id: str,
        worksheet_name: Optional[str] = None,
        batch_size: int = 10,
        flush_interval: float = 2.0,
    ):
        if gspread is None:
            raise RuntimeError("gspread is not installed; spreadsheet logging is unavailable.")

        self.batch_size = max(1, batch_size)
        self.flush_interval = max(0.5, float(flush_interval))
        self.queue: "queue.Queue[List[str]]" = queue.Queue()
        self.stop_event = threading.Event()
        self._last_error = None
        self._last_error_time = 0.0

        # Authenticate with the spreadsheet
        self.client = gspread.service_account(filename=credentials_path)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)
        self.worksheet = (
            self.spreadsheet.worksheet(worksheet_name)
            if worksheet_name
            else self.spreadsheet.sheet1
        )

        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _emit_error(self, error: Exception):
        now = time.time()
        if not self._last_error or str(error) != self._last_error or (now - self._last_error_time) > 10:
            print(f"[SHEET][WARN] Failed to append rows: {error}")
            self._last_error = str(error)
            self._last_error_time = now

    def _flush(self, rows: List[List[str]]):
        if not rows:
            return
        try:
            self.worksheet.append_rows(rows, value_input_option="USER_ENTERED")
        except Exception as error:  # pragma: no cover - depends on external service
            self._emit_error(error)

    def _worker_loop(self):
        pending: List[List[str]] = []
        last_flush = time.time()

        while not self.stop_event.is_set():
            timeout = max(0.1, self.flush_interval - (time.time() - last_flush))
            try:
                row = self.queue.get(timeout=timeout)
                pending.append(row)
                self.queue.task_done()
            except queue.Empty:
                pass

            if pending and (
                len(pending) >= self.batch_size
                or (time.time() - last_flush) >= self.flush_interval
                or self.stop_event.is_set()
            ):
                self._flush(pending)
                pending = []
                last_flush = time.time()

        # Flush any remaining rows on shutdown
        if pending:
            self._flush(pending)

    def enqueue(self, row: List[str]):
        self.queue.put(row)

    def close(self):
        self.stop_event.set()
        self.worker.join(timeout=2.0)
        try:
            # Attempt to drain remaining tasks gracefully
            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()
        except queue.Empty:
            pass


class WebRTCDetectionServer:
    """
    WebRTC detection server with optional spreadsheet streaming.
    """

    def __init__(
        self,
        input_uri: str,
        network: str = "ssd-mobilenet-v2",
        threshold: float = 0.5,
        port: int = 8554,
        width: int = 1280,
        height: int = 720,
        sheet_credentials: Optional[str] = None,
        sheet_id: Optional[str] = None,
        sheet_tab: Optional[str] = None,
        sheet_buffer: int = 10,
        sheet_interval: float = 2.0,
    ):
        self.input_uri = input_uri
        self.network = network
        self.threshold = threshold
        self.port = port
        self.width = width
        self.height = height
        self.sheet_config = {
            "credentials": sheet_credentials,
            "sheet_id": sheet_id,
            "tab": sheet_tab,
            "buffer": sheet_buffer,
            "interval": sheet_interval,
        }

        self.net: Optional[detectNet] = None
        self.input: Optional[videoSource] = None
        self.output: Optional[videoOutput] = None
        self.reporter: Optional[SpreadsheetReporter] = None

        # Statistics
        self.frame_count = 0
        self.detection_count = 0
        self.start_time = time.time()

    def initialize(self) -> bool:
        """
        Initialize detection network, video I/O, and optional spreadsheet reporting.
        """
        print("[INIT] Initializing WebRTC Detection Server...")
        print(f"   Input: {self.input_uri}")
        print(f"   Network: {self.network}")
        print(f"   Threshold: {self.threshold}")
        print(f"   Port: {self.port}")
        print(f"   Resolution: {self.width}x{self.height}")

        try:
            print("[NET] Loading detection network...")
            self.net = detectNet(self.network, sys.argv, self.threshold)
            print(f"[OK] Loaded detection network '{self.network}'")

            print("[VIDEO] Initializing video input...")
            self.input = videoSource(self.input_uri, argv=sys.argv)
            print(f"[OK] Video source '{self.input_uri}' ready")

            print("[WEBRTC] Initializing WebRTC output...")
            webrtc_uri = f"webrtc://@:{self.port}/detection"
            self.output = videoOutput(webrtc_uri, argv=sys.argv)
            print(f"[OK] WebRTC output listening at {webrtc_uri}")

            self._setup_spreadsheet()
            return True
        except Exception as error:
            print(f"[ERROR] Initialization failed: {error}")
            return False

    def _setup_spreadsheet(self):
        creds = self.sheet_config["credentials"]
        sheet_id = self.sheet_config["sheet_id"]

        if not creds and not sheet_id:
            return  # Spreadsheet logging disabled

        if not creds or not sheet_id:
            print("[SHEET][WARN] Spreadsheet logging requires both --sheet-credentials and --sheet-id.")
            return

        if gspread is None:
            print("[SHEET][WARN] Install 'gspread' to enable spreadsheet logging.")
            return

        try:
            self.reporter = SpreadsheetReporter(
                credentials_path=creds,
                spreadsheet_id=sheet_id,
                worksheet_name=self.sheet_config["tab"],
                batch_size=int(self.sheet_config["buffer"]),
                flush_interval=float(self.sheet_config["interval"]),
            )

            target_sheet = self.sheet_config["tab"] or "default sheet"
            print(f"[SHEET] Streaming detections to spreadsheet '{sheet_id}' ({target_sheet}).")
        except Exception as error:
            print(f"[SHEET][ERROR] Unable to configure spreadsheet logging: {error}")
            self.reporter = None

    @staticmethod
    def get_local_ip() -> str:
        try:
            import socket

            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "localhost"

    def _enqueue_detections(self, detections):
        if not self.reporter or not self.net or not detections:
            return

        timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
        fps = f"{self.net.GetNetworkFPS():.2f}" if self.net else ""

        for detection in detections:
            class_desc = self.net.GetClassDesc(detection.ClassID)
            self.reporter.enqueue(
                [
                    timestamp,
                    class_desc,
                    f"{detection.Confidence:.3f}",
                    str(self.frame_count),
                    str(len(detections)),
                    fps,
                    f"{detection.Left:.1f}",
                    f"{detection.Top:.1f}",
                    f"{detection.Right:.1f}",
                    f"{detection.Bottom:.1f}",
                    self.input_uri,
                    self.network,
                ]
            )

    def _print_detection_info(self, detections):
        if not detections or not self.net:
            return

        print(f"[DETECT] {len(detections)} objects detected:")
        for idx, detection in enumerate(detections, start=1):
            class_desc = self.net.GetClassDesc(detection.ClassID)
            confidence = detection.Confidence
            print(f"   [{idx}] {class_desc}: {confidence:.2f}")

    def _print_statistics(self):
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0.0

        print("\n[STATS] Runtime statistics:")
        print(f"   Elapsed: {elapsed:.1f}s")
        print(f"   Frames: {self.frame_count}")
        print(f"   Detections: {self.detection_count}")
        print(f"   Average FPS: {fps:.1f}")
        if self.net:
            print(f"   Network FPS: {self.net.GetNetworkFPS():.1f}")

    def run(self) -> bool:
        if not self.initialize():
            return False

        local_ip = self.get_local_ip()
        print("\n[START] WebRTC Object Detection Server is running.")
        print(f"[URL] Access via browser: http://{local_ip}:{self.port}")
        print(f"[URL] or http://localhost:{self.port}")
        print("[INFO] Press Ctrl+C to stop.\n")

        try:
            while True:
                img = self.input.Capture() if self.input else None

                if img is None:
                    continue

                self.frame_count += 1

                detections = self.net.Detect(img, overlay="box,labels,conf") if self.net else []

                if detections:
                    self.detection_count += len(detections)
                    if self.frame_count % 30 == 0:
                        self._print_detection_info(detections)
                    self._enqueue_detections(detections)

                if self.output:
                    self.output.Render(img)
                    status = (
                        f"Object Detection | Network {self.net.GetNetworkFPS():.1f} FPS | "
                        f"Objects: {len(detections)}"
                        if self.net
                        else f"Object Detection | Objects: {len(detections)}"
                    )
                    self.output.SetStatus(status)

                if self.frame_count % 300 == 0:
                    self._print_statistics()

                if (
                    self.input
                    and self.output
                    and (not self.input.IsStreaming() or not self.output.IsStreaming())
                ):
                    break

        except KeyboardInterrupt:
            print("\n[STOP] Received stop signal.")
        except Exception as error:
            print(f"\n[ERROR] Runtime error: {error}")
        finally:
            print("\n[EXIT] Shutting down WebRTC Object Detection Server...")
            self._print_statistics()
            if self.reporter:
                self.reporter.close()
            return True


def main():
    parser = argparse.ArgumentParser(
        description="Jetson WebRTC Object Detection Server",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python3 webrtc_detectnet.py /dev/video0
  python3 webrtc_detectnet.py /dev/video0 --network ssd-mobilenet-v2 --port 8554
  python3 webrtc_detectnet.py csi://0 --threshold 0.7 --width 1920 --height 1080
  python3 webrtc_detectnet.py /dev/video0 --sheet-credentials service.json --sheet-id <ID>
        """,
    )

    parser.add_argument("input", type=str, default="/dev/video0", nargs="?", help="Input camera URI.")
    parser.add_argument("--network", type=str, default="ssd-mobilenet-v2", help="Detection network.")
    parser.add_argument("--threshold", type=float, default=0.5, help="Detection confidence threshold.")
    parser.add_argument("--port", type=int, default=8554, help="WebRTC server port.")
    parser.add_argument("--width", type=int, default=1280, help="Video width.")
    parser.add_argument("--height", type=int, default=720, help="Video height.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    # Spreadsheet logging options
    parser.add_argument(
        "--sheet-credentials",
        type=str,
        default=None,
        help="Path to Google service account credentials JSON.",
    )
    parser.add_argument(
        "--sheet-id",
        type=str,
        default=None,
        help="Google Spreadsheet ID (from the document URL).",
    )
    parser.add_argument(
        "--sheet-tab",
        type=str,
        default=None,
        help="Worksheet/tab name to append rows to (defaults to first sheet).",
    )
    parser.add_argument(
        "--sheet-buffer",
        type=int,
        default=10,
        help="Number of detection rows to batch before sending (default: 10).",
    )
    parser.add_argument(
        "--sheet-interval",
        type=float,
        default=2.0,
        help="Maximum seconds between spreadsheet updates (default: 2.0).",
    )

    args = parser.parse_known_args()[0]

    if args.verbose:
        Log.SetLevel(Log.VERBOSE)

    server = WebRTCDetectionServer(
        input_uri=args.input,
        network=args.network,
        threshold=args.threshold,
        port=args.port,
        width=args.width,
        height=args.height,
        sheet_credentials=args.sheet_credentials,
        sheet_id=args.sheet_id,
        sheet_tab=args.sheet_tab,
        sheet_buffer=args.sheet_buffer,
        sheet_interval=args.sheet_interval,
    )

    success = server.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
