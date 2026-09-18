# Changelog

## Unreleased

- WAVとschema 1スコアから720p・音付きMP4を作る `pd_musicus_video.py`。
- プロトコル、通信方向、リセット、測定電力とイベント履歴の同期表示。
- PillowとFFmpegは動画出力時だけ必要。既存ファイル保護と長さ照合。

## 0.2.0 — 2026-09-16

- `--player` で起動するローカル同期プレイヤー。
- Source／Sink方向、現在のイベント、シーク可能な履歴、測定点の電力表示。
- 同梱サンプルとローカルWAV＋schema 1 JSONの読込み。
- Soft／Hard Resetの視覚的な区別、CTSケース表示、動きを抑えるOS設定への対応。
- localhost限定・配信対象を限定したサーバーと、音声シーク用のHTTP Range対応。
- CTSタイムラインに実測電流の中央値を追加（音声の編曲は変更なし）。

## 0.1.0 — 2026-09-15

- 統一CLI `pd_musicus.py` と5つの編曲モード、自動モード選択。
- 実測電力に応じたギター／ドラムの密度制御。
- Soft Reset／Hard Resetの音を区別し、AVS中心の編曲でも保持。
- 共通の時刻付きイベント／音符JSON schema 1。
- テンポ変更、plan-only、既存出力保護、長さ上限。
- 旧試作スクリプトの互換性を維持。
