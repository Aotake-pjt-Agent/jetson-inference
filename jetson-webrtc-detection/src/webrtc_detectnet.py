#!/usr/bin/env python3

"""
Jetson WebRTC Object Detection Server
リアルタイム物体検知のWebRTCストリーミング配信

Copyright (c) 2025, Aotake Project. All rights reserved.
"""

import sys
import argparse
import time
import threading
from jetson_inference import detectNet
from jetson_utils import videoSource, videoOutput, Log

class WebRTCDetectionServer:
    def __init__(self, input_uri, network="ssd-mobilenet-v2", threshold=0.5, 
                 port=8554, width=1280, height=720):
        """
        WebRTC物体検知サーバーを初期化
        
        Args:
            input_uri (str): 入力カメラのURI（例: /dev/video0）
            network (str): 使用する検知ネットワーク
            threshold (float): 検知閾値
            port (int): WebRTCサーバーのポート
            width (int): 映像の幅
            height (int): 映像の高さ
        """
        self.input_uri = input_uri
        self.network = network
        self.threshold = threshold
        self.port = port
        self.width = width
        self.height = height
        
        # 統計情報
        self.frame_count = 0
        self.detection_count = 0
        self.start_time = time.time()
        
        print(f"🔧 WebRTC検知サーバーを初期化中...")
        print(f"   入力: {input_uri}")
        print(f"   ネットワーク: {network}")
        print(f"   閾値: {threshold}")
        print(f"   ポート: {port}")
        print(f"   解像度: {width}x{height}")
        
    def initialize(self):
        """
        検知ネットワークとビデオI/Oを初期化
        """
        try:
            # 物体検知ネットワークを読み込み
            print("🤖 物体検知ネットワークを読み込み中...")
            self.net = detectNet(self.network, sys.argv, self.threshold)
            print(f"✅ 検知ネットワーク '{self.network}' を読み込み完了")
            
            # ビデオ入力を作成
            print("📹 ビデオ入力を初期化中...")
            self.input = videoSource(self.input_uri, argv=sys.argv)
            print(f"✅ ビデオ入力 '{self.input_uri}' を初期化完了")
            
            # WebRTC出力を作成
            webrtc_uri = f"webrtc://@:{self.port}/detection"
            print(f"🌐 WebRTC出力を初期化中: {webrtc_uri}")
            self.output = videoOutput(webrtc_uri, argv=sys.argv)
            print(f"✅ WebRTC出力を初期化完了")
            
            return True
            
        except Exception as e:
            print(f"❌ 初期化エラー: {e}")
            return False
    
    def get_local_ip(self):
        """
        ローカルIPアドレスを取得
        """
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except:
            return "localhost"
    
    def print_detection_info(self, detections):
        """
        検知結果を表示
        """
        if len(detections) > 0:
            print(f"🔍 {len(detections)} 個の物体を検知:")
            for i, detection in enumerate(detections):
                class_id = detection.ClassID
                class_desc = self.net.GetClassDesc(class_id)
                confidence = detection.Confidence
                print(f"   [{i+1}] {class_desc}: {confidence:.2f}")
    
    def print_statistics(self):
        """
        統計情報を表示
        """
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        print(f"\n📊 統計情報:")
        print(f"   実行時間: {elapsed:.1f}秒")
        print(f"   処理フレーム数: {self.frame_count}")
        print(f"   検知回数: {self.detection_count}")
        print(f"   平均FPS: {fps:.1f}")
        print(f"   ネットワークFPS: {self.net.GetNetworkFPS():.1f}")
    
    def run(self):
        """
        メインの検知ループを実行
        """
        if not self.initialize():
            return False
        
        local_ip = self.get_local_ip()
        print(f"\n🎉 WebRTC Object Detection Server が起動しました！")
        print(f"📱 ブラウザでアクセス: http://{local_ip}:{self.port}")
        print(f"🔗 または: http://localhost:{self.port}")
        print("🛑 停止するには Ctrl+C を押してください\n")
        
        try:
            # メインの検知ループ
            while True:
                # フレームをキャプチャ
                img = self.input.Capture()
                
                if img is None:  # タイムアウト
                    continue
                
                self.frame_count += 1
                
                # 物体検知を実行
                detections = self.net.Detect(img, overlay="box,labels,conf")
                
                if len(detections) > 0:
                    self.detection_count += len(detections)
                    # 詳細な検知情報を表示（オプション）
                    if self.frame_count % 30 == 0:  # 30フレームに1回表示
                        self.print_detection_info(detections)
                
                # WebRTCストリームに出力
                self.output.Render(img)
                
                # ステータスを更新
                status = f"Object Detection | Network {self.net.GetNetworkFPS():.1f} FPS | Objects: {len(detections)}"
                self.output.SetStatus(status)
                
                # 統計情報を定期的に表示
                if self.frame_count % 300 == 0:  # 300フレームに1回
                    self.print_statistics()
                
                # ストリーミングが停止した場合は終了
                if not self.input.IsStreaming() or not self.output.IsStreaming():
                    break
                    
        except KeyboardInterrupt:
            print("\n⏹️  停止信号を受信しました")
        except Exception as e:
            print(f"\n❌ 実行エラー: {e}")
        finally:
            print("\n🔚 WebRTC Object Detection Server を停止します...")
            self.print_statistics()
            return True

def main():
    """
    メイン関数 - コマンドライン引数を解析してサーバーを起動
    """
    parser = argparse.ArgumentParser(
        description="Jetson WebRTC Object Detection Server",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用例:
  python3 webrtc_detectnet.py /dev/video0
  python3 webrtc_detectnet.py /dev/video0 --network ssd-mobilenet-v2 --port 8554
  python3 webrtc_detectnet.py csi://0 --threshold 0.7 --width 1920 --height 1080
        """
    )
    
    parser.add_argument("input", type=str, default="/dev/video0", nargs='?',
                       help="入力カメラのURI (例: /dev/video0, csi://0)")
    
    parser.add_argument("--network", type=str, default="ssd-mobilenet-v2",
                       help="物体検知ネットワーク (デフォルト: ssd-mobilenet-v2)")
    
    parser.add_argument("--threshold", type=float, default=0.5,
                       help="検知信頼度の閾値 (デフォルト: 0.5)")
    
    parser.add_argument("--port", type=int, default=8554,
                       help="WebRTCサーバーのポート (デフォルト: 8554)")
    
    parser.add_argument("--width", type=int, default=1280,
                       help="出力映像の幅 (デフォルト: 1280)")
    
    parser.add_argument("--height", type=int, default=720,
                       help="出力映像の高さ (デフォルト: 720)")
    
    parser.add_argument("--verbose", action="store_true",
                       help="詳細ログを表示")
    
    # 引数を解析
    args = parser.parse_known_args()[0]
    
    if args.verbose:
        Log.SetLevel(Log.VERBOSE)
    
    # WebRTC検知サーバーを作成・実行
    server = WebRTCDetectionServer(
        input_uri=args.input,
        network=args.network,
        threshold=args.threshold,
        port=args.port,
        width=args.width,
        height=args.height
    )
    
    success = server.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()