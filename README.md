# ととのう書き起こし（totonou-kakiokoshi）

セミナー・講座・会議の動画を、**スクリーンショット付きの読みやすい書き起こしHTML** にする Claude Code 用のスキルです。

Claude Code に「この動画を書き起こして」と動画のURLやファイルを渡すだけで、次の形の資料ができます。

- 冒頭に要約：講義なら「3行でいうと」「章立て」「重要ポイント」、会議なら「決まったこと」「ToDo」
- その下に、スライドが切り替わるごとの画面キャプチャと、時刻付きの書き起こし（言いよどみを取って読みやすく整えた文章）
- 各ブロックで「元の書き起こし」を開くと、整える前の文章も確認できる

1ファイルのHTMLなので、ブラウザで開くだけで読めます。

## できること

| 取り込める素材 | 例 |
|---|---|
| ページのURL | Loom、YouTube、Vimeo など（ログイン不要で見られるもの） |
| UTAGE の講座ページ | ページ内の動画（HLS）を拾って取り込む |
| Google Drive | 「リンクを知っている全員」で共有したファイル |
| パソコン内のファイル | mp4 / mov / m4a など。Zoom のクラウド録画は一度ダウンロードしてから |

「23:00〜25:40だけ」のような一部区間の書き起こしもできます。

## 料金

- 文字起こしは Mac の中で動く音声認識（mlx-whisper）を使うので**無料**です。外部の有料APIは使いません
- 要約と文章の整形は Claude が行うので、お使いの Claude プランの利用枠を消費します（1時間半のセミナー1本で、サブエージェントを4体ほど動かす量です）

## 動く環境

- **Apple シリコン（M1 以降）の Mac**（Intel Mac・Windows では文字起こし部分が動きません）
- **Claude Code**（ターミナル版、またはデスクトップアプリの Code タブ）
- ディスクの空き：作業用に動画1本あたり 1GB 程度。初回は音声認識モデル（約1.6GB）を自動でダウンロードします

## インストール

### 1. 必要なソフトを入れる（最初の1回だけ）

「ターミナル」アプリを開いて、次を順に実行します。

Homebrew が入っていなければ、先に https://brew.sh の手順で入れてください。

```bash
brew install python ffmpeg yt-dlp numpy pipx
```

```bash
pipx install mlx-whisper && pipx ensurepath
```

終わったらターミナルを一度閉じて開き直します。

### 2. スキルを入れる（A か B のどちらか）

**A. GitHub から入れる（おすすめ。更新も簡単）**

ターミナルで次の2つを実行します。

```bash
claude plugin marketplace add yokoyamactw-max/totonou-kakiokoshi
```

```bash
claude plugin install totonou-kakiokoshi@yokoyama-skills
```

Claude Code を開き直すと使えるようになります。
新しい版が出たときは `claude plugin marketplace update yokoyama-skills` のあと `claude plugin update totonou-kakiokoshi@yokoyama-skills` で更新できます。

**B. zip ファイルで入れる**

1. 受け取った `totonou-kakiokoshi-v1.1.0.zip` をダブルクリックして解凍する
2. 中の `totonou-kakiokoshi` フォルダを、ホームフォルダの `.claude/skills/` に入れる（最終的に `~/.claude/skills/totonou-kakiokoshi/SKILL.md` がある状態）
   - Finder で `Command + Shift + G` を押し、`~/.claude/skills` と入力すると開けます。フォルダがなければ作ってください
3. Claude Code を開き直す

### 3. 動くか確認する

Claude Code に「ととのう書き起こしの環境チェックをして」と頼むと、必要なソフトがそろっているかを確認してくれます。

## 使い方

Claude Code に「ととのう書き起こし」と話しかけて、動画のURLかファイルを渡すだけです。

- 「ととのう書き起こし https://www.loom.com/share/xxxx」
- 「~/Downloads/会議録画.mp4 をHTMLで書き起こして。ToDoも出して」
- 「この動画の 23:00〜25:40 だけ、ととのう書き起こしで」

「HTMLで書き起こし」「スクショ付きで書き起こし」と言っても動きます。
コマンドで確実に呼びたいときは、GitHub から入れた場合は `/totonou-kakiokoshi:totonou-kakiokoshi`、zip で入れた場合は `/totonou-kakiokoshi` です。

途中で、素材が誰のものか・全編か一部か・講義か会議かを聞かれることがあります。

できあがったHTMLは、指定がなければ `~/Documents/ととのう書き起こし/` に保存されます。作業用の動画などは `~/Movies/totonou-kakiokoshi/` に残るので、不要になったら削除してください。

1時間半のセミナーで、全体の所要時間はおよそ20〜30分（取り込み10分前後＋文字起こし数分＋整形）です。

## 注意

- **他人の講座・セミナーの書き起こしは、個人の学習用にとどめてください。** できあがったHTMLには講義の全文とスライドがそのまま入っています。権利者の許可なく公開・共有しないでください
- 自動の文字起こしなので、聞き間違いが残ることがあります。金額・日付・条件など大事な数字は、要約で「聞き取り不明瞭」と示された箇所を中心に、元の動画で確かめてください
- HTMLにはスクショを埋め込むので、1時間半の講義で30〜40MBほどになります

## 利用規約

個人・自社の業務での使用と改変は自由です。第三者への再配布・公開・販売、有料サービスへの組み込みは、事前の許可が必要です。詳しくは [LICENSE](LICENSE) をご覧ください。

作者：横山直宏
