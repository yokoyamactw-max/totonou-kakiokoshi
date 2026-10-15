# ととのう書き起こし（totonou-kakiokoshi）

セミナー・講座・会議の動画を、**スクリーンショット付きの読みやすい書き起こしHTML** にする Claude Code 用のスキルです。

Claude Code に「この動画を書き起こして」と動画のURLやファイルを渡すだけで、次の形の資料ができます。

- 冒頭に要約：講義なら「3行でいうと」「章立て」「重要ポイント」、会議なら「決まったこと」「ToDo」
- その下に、スライドが切り替わるごとの画面キャプチャと、時刻付きの書き起こし（言いよどみを取って読みやすく整えた文章）
- 各ブロックで「元の書き起こし」を開くと、整える前の文章も確認できる

1ファイルのHTMLなので、ブラウザで開くだけで読めます。

**使い方マニュアル（図解・Mac/Windows 別の手順）**：https://totonou-kakiokoshi.pages.dev/

## できること

| 取り込める素材 | 例 |
|---|---|
| ページのURL | Loom、YouTube、Vimeo など（ログイン不要で見られるもの） |
| UTAGE の講座ページ | ページ内の動画（HLS）を拾って取り込む |
| Google Drive | 「リンクを知っている全員」で共有したファイル |
| パソコン内のファイル | mp4 / mov / m4a など。Zoom のクラウド録画は一度ダウンロードしてから |

「23:00〜25:40だけ」のような一部区間の書き起こしもできます。
Obsidian を使っている人は、検索用の「目次ノート」も一緒に作れます（任意）。

## 動く環境

| パソコン | 文字起こしエンジン | 1時間半の動画の文字起こし |
|---|---|---|
| Apple シリコン（M1 以降）の Mac | mlx-whisper | 3〜10分ほど |
| Windows 10 / 11（x64）・Intel Mac | faster-whisper（CPU） | 30分〜1時間半ほど（パソコンの性能しだい） |

- **Claude Code**（ターミナル版、またはデスクトップアプリの Code タブ）で使います
- ディスクの空き：音声認識モデル（約1.6GB）＋作業用に動画1本あたり 1GB 程度（聞き直し機能を使うときだけ、追加で約3GB）
- Windows 版は Windows 実機での動作確認がまだです。うまく動かないときは Issue でお知らせください
- Cowork と Web 版 claude.ai・スマホでは使えません（どちらもクラウド上で動くため、大きな動画や文字起こしモデルを扱えない。Pro・Max の Cowork は 2026年10月からクラウド実行）

## 料金

- 文字起こしはパソコンの中で動く音声認識を使うので**無料**です。外部の有料APIは使いません
- 要約と文章の整形は Claude が行うので、お使いの Claude プランの利用枠を消費します（1時間半のセミナー1本で、サブエージェントを4体ほど動かす量です）

## インストール

### いちばん簡単な方法：Claude Code に頼む

Claude Code に次の文をそのまま貼って送ります。必要なソフトの確認・導入まで Claude が案内します。

```
https://totonou-kakiokoshi.pages.dev/totonou-kakiokoshi.zip をダウンロードして展開し、中の totonou-kakiokoshi フォルダを、ホームフォルダの .claude/skills/ の中に入れてください（フォルダがなければ作り、前の版があれば置き換えてください）。終わったら、ととのう書き起こしの環境チェックをして、足りないものがあれば教えてください。
```

### GitHub から入れる（ターミナルを使える人向け。更新が簡単）

```bash
claude plugin marketplace add yokoyamactw-max/totonou-kakiokoshi
```

```bash
claude plugin install totonou-kakiokoshi@yokoyama-skills
```

Claude Code を開き直すと使えるようになります。
新しい版が出たときは `claude plugin marketplace update yokoyama-skills` のあと `claude plugin update totonou-kakiokoshi@yokoyama-skills` で更新できます。

### 必要なソフト（Claude に頼めば案内されます）

**Mac**（Homebrew が必要。https://brew.sh ）

```bash
brew install python ffmpeg yt-dlp numpy pipx
```

- M系 Mac：`pipx install mlx-whisper && pipx ensurepath` のあと、ターミナルを開き直す
- Intel Mac：`python3 <スキルのフォルダ>/scripts/check_env.py --setup`

**Windows**（PowerShell で実行）

```powershell
winget install --id Python.Python.3.12 -e
winget install --id Microsoft.VCRedist.2015+.x64 -e
winget install --id yt-dlp.yt-dlp -e
```

yt-dlp と一緒に ffmpeg も入ります（見つからないと言われたら `winget install --id Gyan.FFmpeg -e`）。Windows on ARM（Snapdragon 搭載機など）には対応していません。

一度 Claude Code を閉じて開き直してから、`python -m pip install numpy` と `python <スキルのフォルダ>\scripts\check_env.py --setup` を実行します（文字起こし用の専用環境とモデルを用意します。10〜20分ほど）。

## 使い方

Claude Code に「ととのう書き起こし」と話しかけて、動画のURLかファイルを渡すだけです。

- 「ととのう書き起こし https://www.loom.com/share/xxxx」
- 「ダウンロードフォルダの 会議録画.mp4 をHTMLで書き起こして。ToDoも出して」
- 「この動画の 23:00〜25:40 だけ、ととのう書き起こしで」

途中で、素材が誰のものか・全編か一部か・講義か会議かを聞かれることがあります。
できあがったHTMLは、指定がなければ「書類（Documents）」フォルダの `ととのう書き起こし` に保存されます。

## 注意

- **他人の講座・セミナーの書き起こしは、個人の学習用にとどめてください。** できあがったHTMLには講義の全文とスライドがそのまま入っています。権利者の許可なく公開・共有しないでください
- 自動の文字起こしなので、聞き間違いが残ることがあります。金額・日付・条件など大事な数字は、元の動画で確かめてください
- HTMLにはスクショを埋め込むので、1時間半の講義で30〜40MBほどになります

## 利用規約

個人・自社の業務での使用と改変は自由です。第三者への再配布・公開・販売、有料サービスへの組み込みは、事前の許可が必要です。詳しくは [LICENSE](LICENSE) をご覧ください。

作者：横山直宏
