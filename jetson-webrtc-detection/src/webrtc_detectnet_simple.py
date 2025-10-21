#!/usr/bin/env python3

import sys
import argparse
from datetime import datetime

from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput

try:
    from webrtc_detectnet import SpreadsheetReporter, SHEET_SUPPORT_AVAILABLE
except ImportError:
    SpreadsheetReporter = None
    SHEET_SUPPORT_AVAILABLE = False

def main():
    parser = argparse.ArgumentParser(description="Jetson WebRTC Object Detection Server")
    parser.add_argument("input", type=str, default="/dev/video0", nargs='?',
                       help="Input camera URI")
    parser.add_argument("--network", type=str, default="ssd-mobilenet-v2",
                       help="Detection network")
    parser.add_argument("--threshold", type=float, default=0.5,
                       help="Detection threshold")
    parser.add_argument("--port", type=int, default=8554,
                       help="WebRTC server port")
    parser.add_argument("--width", type=int, default=1280,
                       help="Video width")
    parser.add_argument("--height", type=int, default=720,
                       help="Video height")
    parser.add_argument("--sheet-credentials", type=str, default=None,
                       help="Path to Google service account credentials JSON")
    parser.add_argument("--sheet-id", type=str, default=None,
                       help="Google Spreadsheet ID (from the document URL)")
    parser.add_argument("--sheet-tab", type=str, default=None,
                       help="Worksheet/tab name (defaults to first sheet)")
    parser.add_argument("--sheet-buffer", type=int, default=10,
                       help="Batch size for spreadsheet updates (default: 10)")
    parser.add_argument("--sheet-interval", type=float, default=2.0,
                       help="Max seconds between spreadsheet flushes (default: 2)")

    args = parser.parse_known_args()[0]

    print("[INIT] Starting WebRTC Detection Server...")
    print(f"Input: {args.input}")
    print(f"Network: {args.network}")
    print(f"Threshold: {args.threshold}")
    print(f"Port: {args.port}")
    print(f"Resolution: {args.width}x{args.height}")

    # Load detection network
    print("[NET] Loading detection network...")
    net = detectNet(args.network, sys.argv, args.threshold)
    print("[OK] Detection network loaded")

    # Create video input/output
    print("[VIDEO] Initializing video input...")
    input_stream = videoSource(args.input, argv=sys.argv)
    print("[OK] Video input initialized")

    webrtc_uri = f"webrtc://@:{args.port}/detection"
    print(f"[WEBRTC] Initializing WebRTC output: {webrtc_uri}")
    output_stream = videoOutput(webrtc_uri, argv=sys.argv)
    print("[OK] WebRTC output initialized")

    # Optional spreadsheet reporter
    reporter = None
    if args.sheet_credentials or args.sheet_id:
        if not (args.sheet_credentials and args.sheet_id):
            print("[SHEET][WARN] Provide both --sheet-credentials and --sheet-id to enable spreadsheet logging.")
        elif not SHEET_SUPPORT_AVAILABLE:
            print("[SHEET][WARN] Install 'gspread' to enable spreadsheet logging.")
        else:
            try:
                reporter = SpreadsheetReporter(
                    credentials_path=args.sheet_credentials,
                    spreadsheet_id=args.sheet_id,
                    worksheet_name=args.sheet_tab,
                    batch_size=int(args.sheet_buffer),
                    flush_interval=float(args.sheet_interval),
                )
                target_sheet = args.sheet_tab or "default sheet"
                print(f"[SHEET] Streaming detections to spreadsheet '{args.sheet_id}' ({target_sheet}).")
            except Exception as error:
                print(f"[SHEET][ERROR] Failed to configure spreadsheet logging: {error}")
                reporter = None

    print(f"\n[START] WebRTC Object Detection Server started!")
    print(f"[URL] Access via browser: http://localhost:{args.port}")
    print("[INFO] Press Ctrl+C to stop\n")

    frame_count = 0

    try:
        while True:
            img = input_stream.Capture()

            if img is None:
                continue

            frame_count += 1

            # Run object detection
            detections = net.Detect(img, overlay="box,labels,conf")

            if len(detections) > 0:
                if frame_count % 30 == 0:
                    print(f"[DETECT] Found {len(detections)} objects")
                    for i, detection in enumerate(detections):
                        class_desc = net.GetClassDesc(detection.ClassID)
                        confidence = detection.Confidence
                        print(f"  [{i+1}] {class_desc}: {confidence:.2f}")

                if reporter:
                    timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
                    fps = f"{net.GetNetworkFPS():.2f}"
                    for detection in detections:
                        reporter.enqueue(
                            [
                                timestamp,
                                net.GetClassDesc(detection.ClassID),
                                f"{detection.Confidence:.3f}",
                                str(frame_count),
                                str(len(detections)),
                                fps,
                                f"{detection.Left:.1f}",
                                f"{detection.Top:.1f}",
                                f"{detection.Right:.1f}",
                                f"{detection.Bottom:.1f}",
                                args.input,
                                args.network,
                            ]
                        )

            # Output to WebRTC stream
            output_stream.Render(img)

            # Update status
            status = f"Object Detection | {net.GetNetworkFPS():.1f} FPS | Objects: {len(detections)}"
            output_stream.SetStatus(status)

            if not input_stream.IsStreaming() or not output_stream.IsStreaming():
                break

    except KeyboardInterrupt:
        print("\n[STOP] Stop signal received")
    except Exception as e:
        print(f"\n[ERROR] Runtime error: {e}")
    finally:
        if reporter:
            reporter.close()
        print("\n[EXIT] Stopping WebRTC Object Detection Server...")

if __name__ == "__main__":
    main()
