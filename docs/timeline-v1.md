# PD musicus timeline schema 1

`schema_version: 1`, `app_version: 0.1.0`。
時間はすべて編曲後の音声先頭を0とする秒数です。元の測定時間とは異なります。

## トップレベル

- `mode`, `bpm`: 編曲条件。
- `inputs`: 元ファイルの絶対パスとSHA-256。由来を確認するための情報。
- `audio`: JSONと同じディレクトリのWAV名。plan-onlyではnull。
- `duration_s`, `sample_rate`, `channels`: 出力音声情報。
- `timebase`: `arranged_audio_seconds`。
- `timeline`: 再生時刻順のイベント。
- `notes`: 再生時刻順の合成音符。
- `notices`: モードごとの解釈上の制約。

## timelineイベント

共通：`id`, `kind`, `at_s`, `label`, `timing`。

PDイベントには `source_row`（CSVのSno）、`source_time_us`（32 bit折返し補正後の機器時刻）、
`role`, `sop`, `status` が付きます。`kind` は `protocol`, `soft_reset`, `hard_reset`。
要求イベントの `data` には、解釈できた電圧・電流とAccept／PS_RDYの参照行を保存します。
powerではASD行番号・実測値・強度も加わります。

CTS測定イベントは `kind: measurement`。`source_lines` はヘッダーを1行目とするASD CSVの物理行番号。
`data` にケースID、測定中央値、状態一覧、音域、強度を保存します。

`timing` は `arranged`、`one_beat_per_case`、または `interpolated_between_arranged_events`。
補間イベントを実際の応答遅延の測定値として表示しないでください。
同時刻イベントは許容されます。IDは1つの生成結果内でのみ一意です。

## notes音符

- `id`, `at`, `duration`: 音符識別子、開始秒数、長さ。
- `pitch`: MIDI音高相当の数値。微小なデチューンを含む場合は小数。
- `voice`: 合成音源名（guitar, piano, marimba, bass, kick等）。
- `gain`: ミックス前の振幅係数。実測電流や最終音声の音量ではありません。
- `pan`: -1=左、0=中央、1=右。
- `layer`: 存在する場合、protocol、authored、power_riff等の編曲上の役割。

イベントと音符は必ずしも1対1ではありません。和音、伴奏、装飾音があります。
将来のUIはプロトコル表示にtimeline、発音アニメーションにnotesを使えます。
入力由来のラベルをHTMLとして解釈せず、テキストとして表示してください。

## 拡張方針

任意フィールドの追加はschema 1のまま可能。既存フィールドの意味や単位を変える場合はschema番号を上げます。
未知フィールドは読込み側で無視できる設計にします。
