#!/bin/bash

# Jetson WebRTC Object Detection Server
# Copyright (c) 2025, Aotake Project. All rights reserved.

echo "🚀 Jetson WebRTC Object Detection Server 起動中..."
echo ""

# Change to the jetson-inference directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if we're in a Docker container
if [ -f /.dockerenv ]; then
    echo "📦 Docker環境で実行中"
    WEBRTC_SCRIPT="jetson-webrtc-detection/src/webrtc_detectnet.py"
else
    echo "🖥️  ホスト環境で実行中"
    WEBRTC_SCRIPT="jetson-webrtc-detection/src/webrtc_detectnet.py"
fi

# Default parameters
CAMERA_INPUT="/dev/video0"
NETWORK="ssd-mobilenet-v2"
THRESHOLD="0.5"
PORT="8554"
WIDTH="1280"
HEIGHT="720"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --camera)
            CAMERA_INPUT="$2"
            shift 2
            ;;
        --network)
            NETWORK="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --width)
            WIDTH="$2"
            shift 2
            ;;
        --height)
            HEIGHT="$2"
            shift 2
            ;;
        --help|-h)
            echo "使用方法: $0 [オプション]"
            echo ""
            echo "オプション:"
            echo "  --camera DEVICE    カメラデバイス (デフォルト: /dev/video0)"
            echo "  --network MODEL    検知モデル (デフォルト: ssd-mobilenet-v2)"
            echo "  --threshold FLOAT  検知閾値 (デフォルト: 0.5)"
            echo "  --port PORT        WebRTCポート (デフォルト: 8554)"
            echo "  --width WIDTH      映像幅 (デフォルト: 1280)"
            echo "  --height HEIGHT    映像高さ (デフォルト: 720)"
            echo "  --help, -h         このヘルプを表示"
            echo ""
            echo "例:"
            echo "  $0"
            echo "  $0 --camera /dev/video0 --network ssd-mobilenet-v2 --port 8554"
            echo ""
            exit 0
            ;;
        *)
            echo "不明なオプション: $1"
            echo "使用方法については --help を参照してください"
            exit 1
            ;;
    esac
done

# Display configuration
echo "📋 設定:"
echo "  カメラ: $CAMERA_INPUT"
echo "  ネットワーク: $NETWORK"
echo "  検知閾値: $THRESHOLD"
echo "  WebRTCポート: $PORT"
echo "  解像度: ${WIDTH}x${HEIGHT}"
echo ""

# Check if camera device exists
if [ ! -e "$CAMERA_INPUT" ] && [ "$CAMERA_INPUT" != "csi://0" ]; then
    echo "❌ エラー: カメラデバイス $CAMERA_INPUT が見つかりません"
    echo "利用可能なカメラデバイス:"
    ls -la /dev/video* 2>/dev/null || echo "  カメラデバイスが見つかりません"
    exit 1
fi

# Use the simple WebRTC script
WEBRTC_SCRIPT="jetson-webrtc-detection/src/webrtc_detectnet_simple.py"

# Check if WebRTC script exists
if [ ! -f "$WEBRTC_SCRIPT" ]; then
    echo "❌ エラー: WebRTC検知スクリプト $WEBRTC_SCRIPT が見つかりません"
    exit 1
fi

# Get local IP address for display
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo "🌐 WebRTC Object Detection Server を起動します..."
echo "📱 ブラウザでアクセス: http://$LOCAL_IP:$PORT"
echo "🔗 または: http://localhost:$PORT (同一マシンの場合)"
echo ""
echo "🛑 停止するには Ctrl+C を押してください"
echo ""

# Run the WebRTC detection server
python3 "$WEBRTC_SCRIPT" "$CAMERA_INPUT" \
    --network="$NETWORK" \
    --threshold="$THRESHOLD" \
    --port="$PORT" \
    --width="$WIDTH" \
    --height="$HEIGHT"

# Cleanup message
echo ""
echo "🔚 WebRTC Object Detection Server を停止しました"
