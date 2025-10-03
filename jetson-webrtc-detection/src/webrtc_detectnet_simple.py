#!/usr/bin/env python3

import sys
import argparse
import time
from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput

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

            if len(detections) > 0 and frame_count % 30 == 0:
                print(f"[DETECT] Found {len(detections)} objects")
                for i, detection in enumerate(detections):
                    class_desc = net.GetClassDesc(detection.ClassID)
                    confidence = detection.Confidence
                    print(f"  [{i+1}] {class_desc}: {confidence:.2f}")

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
        print("\n[EXIT] Stopping WebRTC Object Detection Server...")

if __name__ == "__main__":
    main()
