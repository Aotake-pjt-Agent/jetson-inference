# Jetson WebRTC Detection 日本語ガイド

NVIDIA Jetson 上で SSD MobileNet V2 を用いたリアルタイム物体検出を行い、その結果を WebRTC 経由でブラウザへ配信するプロジェクトです。検出結果を Google スプレッドシートに送信するオプションもサポートしています。

## プロジェクト構成

```
jetson-webrtc-detection
├── src
│   ├── webrtc_detectnet.py         # 機能豊富な WebRTC サーバー
│   ├── webrtc_detectnet_simple.py  # 簡易版サーバー
│   └── static/                     # WebRTC クライアント UI (HTML/CSS/JS)
├── models/                         # 既定の SSD MobileNet V2 モデル
├── config.yaml                     # 追加設定（必要に応じて編集）
├── requirements.txt                # Python 依存関係
└── README*.md                      # ドキュメント
```

## セットアップ手順

1. **リポジトリを取得**
   ```bash
   git clone <repository-url>
   cd jetson-inference/jetson-webrtc-detection
   ```

2. **依存ライブラリをインストール**
   ```bash
   pip3 install -r requirements.txt
   ```
   `requirements.txt` に `gspread` と `google-auth` が含まれているため、Docker 実行時も自動で導入されます。ホスト環境で個別にセットアップする場合は `pip3 install gspread google-auth` を実行してください。

3. **モデルと設定を確認**  
   既定のモデルは `models/ssd-mobilenet-v2` に同梱されています。`config.yaml` で使用するカメラやポート番号を調整できます。

## 実行方法

### Python スクリプトから直接起動
```bash
python3 src/webrtc_detectnet.py /dev/video0 \
  --network ssd-mobilenet-v2 --port 8554 \
  --sheet-credentials /opt/keys/service.json \
  --sheet-id 1AbCdEfGh... \
  --sheet-tab LOG --sheet-buffer 20 --sheet-interval 1.0
```
`--sheet-*` オプションは省略可能です。指定しない場合はブラウザ配信のみ行います。

### ラッパースクリプトを利用
リポジトリ直下の `run_webrtc_detection.sh` からも同等のオプションで起動できます。
```bash
./run_webrtc_detection.sh --camera /dev/video0 --network ssd-mobilenet-v2 \
  --sheet-credentials /opt/keys/service.json --sheet-id 1AbCdEfGh...
```

## スプレッドシート連携の準備

1. Google Cloud Console でサービスアカウントを作成し、JSON キーをダウンロード。リポジトリ外に保管します。  
2. 対象スプレッドシートを開き、サービスアカウントのメールアドレスに編集権限を付与。  
3. 上記コマンドの `--sheet-credentials` に JSON のパス、`--sheet-id` にシートの ID（URL 中の文字列）を指定します。  
4. 起動ログに `[SHEET]` が表示され、数件の検出で行が追記されることを確認してください。API レート制限に遭遇する場合は `--sheet-buffer` や `--sheet-interval` を調整します。

## 利用時の注意

- Jetson にカメラが接続され、`/dev/video*` などの URI からアクセスできることを確認してください。CSI カメラの場合は `csi://0` 形式が利用できます。  
- `webrtc_detectnet_simple.py` は最小限のログと機能を備えた軽量版です。高度な制御やスプレッドシート連携が不要な場合に利用してください。  
- 認証情報ファイルや生成されるキャッシュはバージョン管理に含めないでください。 `.gitignore` への追加を推奨します。

質問や問題がありましたら、プロジェクトの Issue もしくはメンテナへ報告してください。楽しんでお使いください！
