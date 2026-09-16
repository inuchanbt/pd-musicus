# PD musicus

USB Power Deliveryの交渉と負荷測定を音楽にする、オフラインのツールです。
要求と応答を掛け合いに変換し、実測電力が大きくなるほどギターやドラム、音数が増えます。
リセットや測定のfailed状態も、それぞれの音で表現します。

**v0.2.0** · [English](README.md) · [MITライセンス](LICENSE)

## 音に合わせてプロトコルを見る

```sh
python pd_musicus.py --player
```

ブラウザーが開き、同梱の0.5 A／5 Aサンプルを選んで再生できます。
現在のイベント、Source／Sink間の方向、前後の履歴、実測電圧・電流・電力を表示します。
一時停止やシークに追従し、履歴のイベントをクリックして再生位置を移動できます。

**Open your recording** で、WAVと対応する `.score.json`（schema 1）をまとめて選択できます。
処理はブラウザー内で行い、ファイルはアップロードしません。CTS版は測定ケースを表示し、
PD版はSoft Reset／Hard Resetを区別します。

サーバーは `127.0.0.1` 限定で、プレイヤーと同梱サンプルだけを配信します。
停止はターミナルでCtrl+C。`--port 18765` でポート指定、`--no-browser` で自動起動を抑制できます。
指定ポートが利用できない場合は空きポートへ切り替え、起動URLを表示します。
`player/index.html` を直接開いてローカルWAV／JSONを選ぶこともできますが、同梱サンプルボタンにはサーバーが必要です。

表示は編曲後の音声時間に対応し、実際の通信遅延ではありません。実測値はその測定点の値です。
動くバーは再生状態と電力の演出で、音声スペクトラムではありません。動画書き出しは今後の機能です。

## まず聴いてみる

同じ21 → 48 → 21 VのEPR AVS掃引を、異なる負荷で演奏しました。

| サンプル | 音の特徴 | WAV |
|---|---|---|
| 0.5 A：約10～24 W | 柔らかいピアノ／マリンバ風 | [試聴・ダウンロード](examples/avs_0p5a.wav) |
| 5 A：約105～239 W | 電力に応じてギター・ドラム・連打が増加 | [試聴・ダウンロード](examples/avs_5a.wav) |

どちらも約45秒。同じ電力連動モードとテンポを使っています。
ブラウザーによってはダウンロードして再生してください。
[元データと再生成手順](examples/README.md)も同梱しています。

## 実行環境

Python 3.10以降。外部パッケージは不要です。
各Pythonファイルを同じフォルダーに置き、リポジトリのルートで実行します。
保存済みログを使うため、試聴・再生成に測定機器は必要ありません。

```sh
python pd_musicus.py examples/avs_5a_pd.csv --asd examples/avs_5a_asd.csv --out output/demo.wav
```

独自のPDキャプチャから掛け合いを作る例：

```sh
python pd_musicus.py captures/session_pd.csv --out output/duet.wav
```

## モード

| モード | 入力 | 内容 |
|---|---|---|
| `auto`（既定） | CSV | CTS列があればcts、PD＋--asdならpower、それ以外はduet |
| `conversation` | CY4500 Utility形式のPD CSV | 電子音による掛け合い |
| `duet` | 同上 | 拍に揃えたピアノ／マリンバ風と伴奏 |
| `avs` | 同上 | EPR AVS要求電圧を五音音階へ変換 |
| `power` | PD CSV＋同一試験のASD AVS CSV | 実測ワット数でギター・ドラムの密度を変更 |
| `cts` | ASD CTS-like CSV | 要求電圧と実測電力をギターリフへ変換 |

```sh
python pd_musicus.py captures/sweep_pd.csv --mode avs --bpm 120 --out output/avs.wav
python pd_musicus.py captures/cts_asd.csv --mode cts --out output/guitar.wav
python pd_musicus.py captures/session_pd.csv --plan-only --out output/preview.wav
python pd_musicus.py --help
```

- `--bpm`：30～240。既定値はモードによって異なります。
- `--out`：保存先。省略時は `output/<入力名>_musicus.wav`。
- `--plan-only`：音声を作らずJSONだけ生成。
- `--overwrite`：既存の出力を明示的に上書き。
- `--max-seconds`：編曲の長さ上限。既定180秒、最大600秒。途中で切らず、長すぎる入力を拒否します。

## 音とデータの対応

電圧で音域、実測ワット数で音色・音数・リズム密度が変わります。
powerモードは30 W以下で追加パートなし、240 Wで最大強度です。
ctsは0～240 Wを強度0～1に対応させます。

Soft Resetは下降するベル、Hard Resetは低い歪み音として区別します。
AVS中心の編曲でもリセットを残しますが、再生位置は前後の編曲イベントから補間したものです。
CTSのfailed状態は不協和音で残し、測定失敗から実際のPDリセットを推測することはしません。

音色は合成音で、和音・リフ・伴奏・ドラムの具体的な譜面は創作です。
演奏時間は圧縮・再配置され、実際の通信遅延を表しません。

## 出力と拡張

- 44.1 kHz／16 bit／ステレオWAV。ピークを0.82に正規化。
- 同名の `.score.json`。元ログの参照、実測値、再生時刻、全音符を保存。

ログ読込み、編曲、音声化を分離しています。[タイムライン仕様](docs/timeline-v1.md)は、
将来のプロトコル逐次表示や電力連動の視覚効果に使えます。
同期プレイヤーを同梱しています。録音サンプル音源と動画書き出しは未実装です。

## 対応範囲

- PD入力はUtility形式CSVのみ。旧CLIのバイト列表現CSV、JSONL、scope CSVは未対応。
- EPR AVSはEPR_REQUEST同梱PDOで単位を判別。PPS／SPR AVSの電圧解釈、拡張PDO再構成は未実装。
- powerはASDの `avs-continuous` 行とPD要求の点数・順序・要求電圧／電流を照合。初期負荷ランプは省きます。
- PD／ASD間のクロック同期は行いません。必ず同一試験のファイルを指定してください。
- ctsは同一ケースの連続行をまとめて実測電力の中央値を使います。欠損値や未対応形式は拒否する場合があります。
- 認証の合否判定や測定エラーの原因診断をするツールではありません。

## 開発

```sh
python -m unittest -v
node player/test_timeline.cjs
```

テストは人工データを使用し、ハードウェア不要です。
JavaScriptテストの実行だけはNode.jsが必要です。プレイヤーの利用には不要です。
入口は `pd_musicus.py`。同じフォルダーの `pd_music.py`、`avs_music.py`、
`power_music.py`、`cts_music.py` も必要です。旧コマンドは互換用に残しています。

個人の測定ログ・生成音声はGit対象外です。`examples/` のサンプルだけを公開しています。
コード、同梱CSV、合成WAVはMITライセンスです。第三者の楽器録音は含みません。
