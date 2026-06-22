# UXsim Order Exchange 研究背景・資料案内メモ

## このメモの役割

このメモは、UXsim Order Exchange 改変作業を別チャット・別作業セッションで再開する際に、研究背景・添付資料・現在の実装位置を素早く共有するための案内メモである。

このメモ自体は、論文やExcel VBAモデルの内容を完全に代替するものではない。
新チャットで再開する場合は、このメモに加えて、関連資料を添付して読む必要がある。

## 研究の大目的

UXsimを改変し、交通ネットワーク上の交差点進入順序制御を研究する。

主に比較したい方式は以下である。

- 標準UXsim挙動
- FCFS: First-Come, First-Served
- Batch Processing
- Time-value Transaction

研究の中心的関心は、交差点に進入する車両の順序をどのように決めるか、またその順序制御が旅行時間・遅れ・効率性・時間価値に基づく便益配分にどのような影響を与えるかを評価することである。

## 研究上の主な関心

以下のような観点を扱う。

- UXsim標準挙動を壊さずに、対象Nodeだけに交差点進入順序制御を導入する
- 車両ごとに true VOT と declared VOT を持たせる
- 順序交換なしケースと順序交換ありケースを、同じ車両リストで比較する
- FCFS, Batch Processing, Time-value Transaction を同一条件下で比較する
- どのNodeに制御を導入するかを分析対象にする
- order_control_eligible=True のNode集合から、ランダム選択やネットワーク特徴量に基づく選択を行う
- 将来的には、Time-value Transaction の制度設計、支払い、受け取り、参加・非参加、申告VOTの戦略性を分析する

## 新チャットで添付すべき資料

新しいAIチャットで作業を再開する場合、可能であれば以下を添付する。

### 必須に近い資料

- ORDER_EXCHANGE_PROGRESS.md
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md
- git status の出力
- git log --oneline -20 の出力

### 研究背景を深く理解するために添付すべき資料

- 研究論文または研究構想ファイル
- Excel VBAモデル関連ファイル
- UXsim改変ロードマップ資料

### 必要に応じて追加で確認する資料

- uxsim/uxsim.py の該当箇所
- 追加済みテストファイル
- generate_vehicle_list_for_order_exchange.py
- tests_load_vehicle_list_to_uxsim.py
- その他、車両リスト生成・読み込み・Node設定に関係するファイル

## 各資料の役割

### ORDER_EXCHANGE_PROGRESS.md

フェーズ0からフェーズ3-5までの実装済み内容をまとめた進捗メモ。

主に以下を確認するために使う。

- どのブランチで作業しているか
- どのフェーズまで完了しているか
- どのファイルを追加・変更したか
- Vehicle, Node, World にどの研究用属性・補助関数を追加したか
- 次に進む予定は何か

### ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md

フェーズ3-5完了後、フェーズ4の制御ロジック本体に入る前の設計議論をまとめたメモ。

主に以下を確認するために使う。

- FCFSを検知領域進入順ではなく交差点到着順として定義し直した理由
- Node.transfer() の依存関係調査結果
- 標準UXsimはoutlink起点、FCFSはvehicle到着順起点であるという整理
- 方向切替・クリアランス制約の必要性
- 制御用状態と分析ログを分ける方針
- Vehicleに order_control_node_arrival_times を追加する候補
- 交差点進入制約の設計をさらに詰める必要があること

### 研究論文・研究構想ファイル

研究の理論的背景、制度設計、貢献、分析対象を理解するための資料。

主に以下を確認するために使う。

- Time-value Transaction の研究上の意味
- 時間価値に基づく順序交換の制度設計
- Case I, II, III の位置づけ
- 研究の主貢献
- 評価すべき指標
- 論文全体の問題設定

### Excel VBAモデル関連ファイル

既存の簡易モデルや順序交換ロジックの原型を理解するための資料。

主に以下を確認するために使う。

- 既存モデルでどのように車両順序を扱っていたか
- Batch Processing や Time-value Transaction の原型
- どのような入力・出力・評価指標を想定していたか
- UXsim改変で再現・拡張すべきロジック

### UXsim改変ロードマップ資料

UXsim改変の段階的な全体計画を理解するための資料。

主に以下を確認するために使う。

- フェーズごとの目的
- Vehicle属性追加
- Node属性追加
- 検知領域
- 候補車両抽出
- Node.transfer() 改変
- 支払い処理
- 評価・可視化
- 将来の拡張予定

## 現在の実装位置

現在の作業ブランチは以下。

feature/intersection-order-control

フェーズ3-5まで実装・コミット済み。

完了済みの主な内容は以下。

- Vehicle研究用属性の追加
- 固定車両リスト生成・読み込み基盤
- Node制御方式設定属性の追加
- order_control_type の導入
  - "none"
  - "fcfs"
  - "batch"
  - "time_value"
- order_control_eligible の導入
- order_control_eligible の自動判定
  - len(node.inlinks) >= 2
  - len(node.outlinks) >= 1
- order_control_eligible の手動補正
- 選択Nodeへの order control 設定
- order_control_eligible=True のNode集合からのランダム選択
- フェーズ4設計メモの作成

ただし、以下はまだ未実装。

- FCFSの実際のNode.transfer()制御
- Batch Processingの実制御ロジック
- Time-value Transactionの実制御ロジック
- 支払い・受け取り処理
- 交差点進入制約の実装
- 方向切替・クリアランス制約の実装
- 通過予定時刻の推定
- Batch候補集合の本格的な形成
- Time-value Transaction のCase I, II, III ロジック

## 現在の重要な設計論点

フェーズ4に進む前に、以下が重要な論点として残っている。

### 1. FCFSの定義

FCFSは、検知領域に入った順ではなく、対象Nodeに到着し、Node通過・次Link進入の処理待ちになった順と定義する方向。

ただし、早く到着した車両でも、outlinkが満杯などの制約で通過できない場合がある。
その場合、後から到着した車両が先に通過することはあり得る。

### 2. Node.transfer() の構造

標準UXsimの Node.transfer() はoutlink起点の構造である。

一方、FCFSはvehicle到着順起点の制御になりそうである。

そのため、将来的には以下の分離が望ましい。

- 車両選択ロジック
  - 標準UXsim
  - FCFS
  - Batch Processing
  - Time-value Transaction

- 選ばれたVehicleを実際に次Linkへ移す共通処理

### 3. 信号を使わない場合の交差点進入制約

FCFS, Batch Processing, Time-value Transaction では、標準UXsimの信号制御を使わない可能性が高い。

その場合、交差点内の安全・競合制約として、方向切替・クリアランス制約を別途設計する必要がある可能性がある。

検討中の考え方：

- 同じinlinkから続けて来る車両は連続して進入可能
- 異なるinlinkから来る車両に切り替える場合は、1タイムステップ分のクリアランス待ちを課す
- これをFCFS, Batch Processing, Time-value Transactionに共通適用する可能性がある
- 標準UXsimの order_control_type="none" には影響させない

### 4. 制御用状態と分析ログの区別

UXsim標準には log_t, log_link, log_x, log_t_link などのVehicleログがある。

しかし、FCFSで必要な対象Nodeへの到着時刻は、事後分析用ログではなく、制御ルールで使う状態量である。

そのため、以下を分けて考える。

- 制御用状態
  - FCFSなどの制御ロジックが参照する値
- 分析用ログ
  - 後から標準UXsim, FCFS, Batch Processing, Time-value Transactionを比較するための記録

### 5. Vehicle側に到着時刻を持たせる方針

最初の安全な小フェーズとして、Vehicleに以下を追加する候補がある。

- order_control_node_arrival_times

これは辞書とする。

用途：

- order control対象Nodeへの初回到着時刻を保存する
- 現在は主にFCFS順序決定に使う想定
- 将来Batch ProcessingやTime-value Transactionでも再利用する可能性がある

現時点では node.name をキーにする想定。

ただし、同一Vehicleが同一Nodeを複数回通るような循環経路では、node.name だけをキーにする設計では不十分になる可能性がある。
現在想定している単純ネットワーク・単純ODでは、同一Vehicleが同一Nodeを複数回通らないため、この設計で十分と考える。

## 新チャットで再開する際の推奨プロンプト

新チャットで再開する場合は、以下のように伝える。

```
UXsim改変作業を前のチャットから引き継ぎたいです。

添付した以下のファイルを読んで、現在の作業状況と設計方針を把握してください。

- ORDER_EXCHANGE_PROGRESS.md
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md
- ORDER_EXCHANGE_RESEARCH_CONTEXT.md
- 研究論文または研究構想資料
- Excel VBAモデル関連ファイル
- UXsim改変ロードマップ資料

現在のブランチは feature/intersection-order-control です。
フェーズ3-5まで実装・コミット済みです。

次は、フェーズ4として、以下のどちらから進めるかを検討する段階です。

A. 交差点進入制約の設計をさらに詰める
B. Vehicleに order_control_node_arrival_times を追加する小フェーズから始める

以下に git status と git log --oneline -20 の結果も貼ります。
```

## 新チャットで追加提出するとよいGit情報

新チャットには、以下の2つのコマンド結果も貼るとよい。

- git status
- git log --oneline -20

これにより、現在のブランチ、直近コミット、作業ツリーがcleanかどうかを確認できる。
