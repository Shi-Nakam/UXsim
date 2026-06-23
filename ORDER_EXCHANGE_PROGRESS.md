# UXsim Order Exchange 改変作業メモ

## 現在の作業ブランチ

feature/intersection-order-control

## 目的

UXsimに交差点進入順序制御・順序交換アルゴリズムを段階的に導入する。

研究上の主な関心は以下：

- 標準UXsim挙動を壊さず、対象Nodeだけに交差点進入順序制御を導入できるようにする
- 車両ごとに true VOT と declared VOT を持たせる
- 順序交換なしケースと順序交換ありケースを、同じ車両リストで比較できるようにする
- 将来的に FCFS, Batch Processing, Time-value Transaction を比較できるようにする
- 導入Nodeの選択方法、導入割合、Nodeのネットワーク特徴量と効果の関係を分析できるようにする

## 完了済みフェーズ

### フェーズ0：作業基盤の準備

完了済み。

実施内容：

- 作業ブランチ feature/intersection-order-control を作成
- 標準UXsimサンプル demos_and_examples/example_00en_simple.py の正常実行を確認
- 最小ベースラインシナリオ tests_order_exchange_baseline.py を作成
- tests_order_exchange_baseline.py を実行し、48/48台の完了を確認
- Gitにコミット済み

関連コミット：

- 1edfa9f Add baseline scenario for order exchange development

### フェーズ1：Vehicle研究用属性の追加

完了済み。

Vehicleに以下の研究用属性を追加：

- vot_true
- vot_declared
- payment_paid
- payment_received
- order_exchange_log
- participates_in_order_exchange

意味：

- vot_true: 真のValue of Time
- vot_declared: 申告されたValue of Time
- payment_paid: 支払累計額
- payment_received: 受取累計額
- order_exchange_log: 順序交換履歴
- participates_in_order_exchange: 順序交換制度に参加する車両かどうかのフラグ

補足：

- 初期分析では vot_declared = vot_true とする
- 将来的には vot_declared != vot_true のケースや、非参加車両を扱う
- participates_in_order_exchange=False の車両でも、交通流上は通常通り存在し、対象Node通過時刻が早まる・遅れる・変わらないことがあり得る

追加テスト：

- tests_vehicle_research_attributes.py

関連コミット：

- 6a0578d Add first 5 research attributes to Vehicle for order exchange
- 97ffdfd Add test for Vehicle research attributes
- f07fa31 Add order exchange participation flag to Vehicle and update tests

### フェーズ2-1：固定車両リスト生成・投入基盤

完了済み。

作成ファイル：

- generate_vehicle_list_for_order_exchange.py
- tests_load_vehicle_list_to_uxsim.py

generate_vehicle_list_for_order_exchange.py の主な機能：

- generate_vehicle_list(...)
- load_vehicle_list_to_world(W, csv_path)

生成する車両リストの列：

- vehicle_id
- orig
- dest
- departure_time
- vot_true
- vot_declared
- participates_in_order_exchange

生成仕様：

- seed指定可能
- departure_time は指数分布の到着間隔を累積して生成
- ODは od_pairs と od_probabilities に従ってランダム選択
- vot_true は対数正規分布から生成
- 初期状態では vot_declared = vot_true
- participation_rate に応じて participates_in_order_exchange を True/False にする
- participates_in_order_exchange=False の場合、vot_declared は空欄としてCSVに出力し、読み込み時は None とする

確認済み事項：

- 同じseedなら同じ車両リストを再生成できる
- 異なるseedなら異なる車両リストになる
- seedごとの生成台数は期待値48台の周辺で上下する
- 生成CSVはGit管理に含めない

関連コミット：

- 9566437 Add initial fixed vehicle list generator for order exchange
- d6b8add Add initial test for loading generated vehicle list into UXsim

### フェーズ2-2：CSV車両リスト投入処理の整理

完了済み。

実施内容：

- CSVからUXsim WorldへVehicleを投入する処理を load_vehicle_list_to_world(W, csv_path) として関数化
- tests_load_vehicle_list_to_uxsim.py を更新して、関数化した処理を使用
- participates_in_order_exchange=False かつ vot_declared 空欄の車両を読み込むテストを追加
- 不参加車両について以下を確認：
  - veh.participates_in_order_exchange is False
  - veh.vot_declared is None
  - veh.vot_true はCSVの値と一致
  - payment_paid == 0
  - payment_received == 0
  - order_exchange_log == []

関連コミット：

- af3fc46 Refactor vehicle list loading into reusable function
- 0080d26 Add non-participating vehicle case to loading test

### フェーズ3-2：Node制御方式設定属性の追加

完了済み。

Nodeに以下の研究用属性を追加：

- order_control_type
- batch_size
- transaction_case

order_control_type が取り得る値：

- "none"
- "fcfs"
- "batch"
- "time_value"

意味：

- "none": 標準UXsim挙動
- "fcfs": First-Come, First-Served 用
- "batch": Batch Processing 用
- "time_value": Time-value Transaction 用

設計上の整理：

- FCFSは理論的にはBatch Processingの batch_size=1 に近い
- ただしUXsim実装上は、FCFSはBatch Processingとは別モードとして扱えるようにした
- 理由は、FCFSはローリングホライズンやバッチ再計算間隔に縛られず、UXsimの通常タイムステップごとに処理できる可能性があるため

追加テスト：

- tests_node_order_control_attributes.py

確認済み事項：

- デフォルトNodeは order_control_type="none", batch_size=1, transaction_case=None
- fcfs Nodeを作成可能
- batch Nodeを作成可能
- time_value Nodeを作成可能
- 不正値で ValueError が出る
- 既存ベースライン・標準サンプルが正常動作

関連コミット：

- ad32622 Add Node order control configuration attributes

### フェーズ3-3：選択した複数Nodeへの制御方式一括設定関数の追加

完了済み。

実施内容：

- World クラスに set_order_control_for_nodes(...) を追加
- Node名リストで指定した複数Nodeに対して、以下の設定をまとめて適用できるようにした
  - order_control_type
  - batch_size
  - transaction_case
- 関数は、設定を変更したNodeオブジェクトのリストを返す
- 入力値チェックを追加
  - order_control_type は "none", "fcfs", "batch", "time_value" のみ許可
  - batch_size は1以上の整数のみ許可
  - transaction_case は None, "I", "II", "III" のみ許可
- Node.transfer() などの交通挙動は変更していない
- FCFS, Batch Processing, Time-value Transaction の実制御ロジックはまだ実装していない

追加テスト：

- tests_world_order_control_setters.py

確認済み事項：

- 複数Nodeに batch 設定をまとめて適用できる
- 指定されていないNodeはデフォルト状態のままである
- time_value 設定をNodeに適用できる
- fcfs 設定をNodeに適用できる
- 不正値で ValueError が出る
- tests_world_order_control_setters.py が正常実行
- tests_node_order_control_attributes.py が正常実行
- tests_order_exchange_baseline.py が正常実行
- demos_and_examples/example_00en_simple.py が正常実行

関連コミット：

- fbd8321 Add function to set order control collectively for selected nodes

### フェーズ3-4：order_control_eligible による制御対象Node管理の追加

完了済み。

実施内容：

- Nodeに order_control_eligible 属性を追加
- World.addNode(...) から order_control_eligible を指定可能にした
- World.infer_order_control_eligible_nodes(...) を追加
- World.set_order_control_eligible_flag_for_nodes(...) を追加
- World.set_order_control_for_nodes(...) を安全化

order_control_eligible の意味：

- order_control_eligible=True
  - このNodeは交差点進入順序制御の対象候補として扱える

- order_control_eligible=False
  - このNodeは原則として交差点進入順序制御の対象にしない

デフォルト：

- order_control_eligible=False

理由：
既存UXsimサンプルや標準挙動を壊さないため、何も指定しない限り、Nodeは制御対象候補にならないようにした。

追加した自動設定関数：

- infer_order_control_eligible_nodes(...)

機能：

- ネットワーク構築後に、各Nodeの inlinks と outlinks を見て order_control_eligible を自動設定する
- len(node.inlinks) >= 2 かつ len(node.outlinks) >= 1 のNodeを True にする
- それ以外のNodeを False にする

#### 判定条件の精緻化

- 当初は len(node.inlinks) > 0 and len(node.outlinks) > 0 を条件としていた
- その後、inlinks=1, outlinks=1 の単純通過Nodeは順序交換方式の比較対象として意味が薄いと判断した
  - 複数流入がないため、交差点進入順序の交換相手が基本的に存在しない
  - FCFS自体はそのようなNodeでも自然に成立し得る
  - しかし研究上は、FCFS / Batch Processing / Time-value Transaction を同じ制御対象Node集合で比較したい
  - Batch Processing と Time-value Transaction が意味を持つのは、少なくとも複数流入を持つNodeである
- 現在は len(node.inlinks) >= 2 and len(node.outlinks) >= 1 を自動判定条件としている
- inlinks=1, outlinks=1 の単純な中間Nodeは order_control_eligible=False になる
- tests_order_control_eligibility.py に、その確認を追加済み

注意：

- この自動判定は、origin node や destination node を除外するのに有効
- ただし、補助Nodeを完全には除外できない
- そのため、手動補正関数と組み合わせて使う前提

追加した手動設定関数：

- set_order_control_eligible_flag_for_nodes(node_names, is_eligible)

機能：

- 指定したNode名リストに対して、order_control_eligible を True または False に手動設定する
- 自動判定で True になってしまった補助Nodeを False に除外できる
- 例外的に制御対象候補にしたいNodeを True に設定できる

set_order_control_for_nodes(...) の安全化：

- order_control_type が "fcfs", "batch", "time_value" の場合、
  指定されたNodeは order_control_eligible=True でなければならない
- order_control_eligible=False のNodeが含まれている場合は ValueError を出す
- order_control_type="none" の場合は、制御解除・標準挙動を表すため、order_control_eligible=False のNodeにも適用できる

追加・更新したテスト：

- tests_node_order_control_attributes.py
- tests_world_order_control_setters.py
- tests_order_control_eligibility.py

確認済み事項：

- デフォルトNodeでは order_control_eligible is False
- W.addNode(..., order_control_eligible=True) で True にできる
- infer_order_control_eligible_nodes(...) により、len(node.inlinks) >= 2 かつ len(node.outlinks) >= 1 のNodeだけを True にできる
- origin node と destination node は False になる
- inlinks=1, outlinks=1 の単純な中間Nodeは order_control_eligible=False になることを確認
- tests_order_control_eligibility.py にその確認を追加済み
- set_order_control_eligible_flag_for_nodes(...) により、手動で True / False を上書きできる
- is_eligible に bool 以外を渡すと ValueError が出る
- order_control_eligible=False のNodeに batch などを設定しようとすると ValueError が出る
- order_control_eligible=True に戻せば batch 設定できる
- order_control_type="none" は order_control_eligible=False のNodeにも適用できる
- tests_order_control_eligibility.py が正常実行
- tests_node_order_control_attributes.py が正常実行
- tests_world_order_control_setters.py が正常実行
- tests_order_exchange_baseline.py が正常実行
- demos_and_examples/example_00en_simple.py が正常実行

関連コミット：

- 1fe035e Add automatic and manual setting of order control eligibility
- ec89308 Refine order control eligibility inference criteria

### フェーズ3-5：order_control_eligible=True のNode集合からのランダム選択機能追加

完了済み。

実施内容：

- World に order_control_eligibility_prepared フラグを追加
- infer_order_control_eligible_nodes(...) 実行後に order_control_eligibility_prepared=True になるようにした
- World.set_order_control_for_randomly_selected_eligible_nodes(...) を追加
- order_control_eligible=True のNode集合から、fraction に基づいてランダムに一部Nodeを選択できるようにした
- 選ばれたNodeに order_control_type, batch_size, transaction_case を設定できるようにした
- 設定処理は既存の set_order_control_for_nodes(...) に委譲する設計にした

追加した関数：

- set_order_control_for_randomly_selected_eligible_nodes(
    fraction,
    order_control_type="none",
    batch_size=1,
    transaction_case=None,
    random_seed=None,
  )

主な仕様：

- infer_order_control_eligible_nodes(...) を実行していない状態で呼ぶと ValueError を出す
- order_control_eligible=True のNodeだけをランダム選択候補とする
- order_control_eligible=True の候補Nodeが0個の場合は ValueError を出す
- fraction は 0以上1以下の数値のみ許可する
- bool や文字列など、不正な fraction では ValueError を出す
- fraction=0 の場合は空リストを返す
- fraction から選択個数 n_select を以下で計算する
  - n_select = int(math.floor(n_candidates * fraction + 0.5))
- これは fraction から得られる値を四捨五入相当にして整数化するため
- ランダム選択は、各Nodeを独立確率で選ぶ方式ではない
- 候補Node集合から n_select 個を重複なしでランダム抽出する
- random_seed により、同じ条件なら同じNode集合を再現できる
- exclude_node_names のような一時除外引数は採用しない
- 補助Nodeなどを除外したい場合は、事前に set_order_control_eligible_flag_for_nodes(..., False) で order_control_eligible 自体を False にする方針

設計上の整理：

- ランダム選択関数は、単独で使うものではない
- 基本的な利用手順は以下：
  1. NodeとLinkでネットワークを構築する
  2. infer_order_control_eligible_nodes(...) を実行する
  3. 必要に応じて set_order_control_eligible_flag_for_nodes(...) で補助Nodeなどを手動補正する
  4. set_order_control_for_randomly_selected_eligible_nodes(...) を実行する
- 補助Node除外などの手動補正が済んでいるかどうかは、コードでは自動判定しない
- そのため、docstringには、必要な手動補正を済ませてから呼ぶことを明記した

追加テスト：

- tests_random_eligible_order_control.py

確認済み事項：

- infer_order_control_eligible_nodes(...) 未実行時にランダム選択関数を呼ぶと ValueError が出る
- infer 実行後、order_control_eligible=True のNode集合から fraction に基づいてランダム選択できる
- fraction=0.5 かつ order_control_eligible=True の候補Nodeが4個の場合、2個が選ばれることを確認
- 選ばれたNodeには order_control_type="batch", batch_size=10 が設定される
- 選ばれなかった order_control_eligible=True のNode は order_control_type="none" のままである
- 同じ random_seed を使うと、同じNode集合が選ばれることを確認
- fraction=0 の場合は空リストを返す
- 不正な fraction で ValueError が出る
- order_control_eligible=True の候補Nodeが0個の場合に ValueError が出る
- tests_random_eligible_order_control.py が正常実行
- tests_order_control_eligibility.py が正常実行
- tests_world_order_control_setters.py が正常実行
- tests_node_order_control_attributes.py が正常実行
- tests_order_exchange_baseline.py が正常実行
- demos_and_examples/example_00en_simple.py が正常実行

関連コミット：

- 6bdeefa Add random selection from order-control eligible nodes

### フェーズ4-1：Vehicleに order_control_node_arrival_times を追加

完了済み。

実施内容：

- Vehicleに order_control_node_arrival_times 属性を追加
- 初期値は空辞書 {}
- この辞書は、order-control対象Nodeへの初回到着時刻を将来記録するための器である
- 現時点では、実際に到着時刻を記録する処理はまだ実装していない
- 現時点では node.name をキーにする想定
- 値は将来的に W.T * W.DELTAT による秒単位の時刻を入れる想定
- 主にFCFS順序決定で使う想定
- 将来的には Batch Processing や Time-value Transaction でも再利用する可能性がある
- これは事後分析用ログではなく、制御ロジックが参照する制御用状態である

今回あえて実装していないこと：

- Vehicle.update() 内で到着時刻を記録する処理
- Node.transfer() の変更
- FCFS用の車両選択ロジック
- order_control_node_arrival_orders
- Node側 arrival_order_counter
- order_control_node_passage_log
- 通過時刻ログ
- 方向切替・クリアランス制約
- Batch Processing の実制御ロジック
- Time-value Transaction の実制御ロジック

追加・更新したテスト：

- tests_vehicle_research_attributes.py

確認済み事項：

- 研究用属性を明示的に指定したVehicleでも order_control_node_arrival_times == {}
- デフォルト設定で作成したVehicleでも order_control_node_arrival_times == {}
- tests_vehicle_research_attributes.py が正常実行
- tests_order_exchange_baseline.py が正常実行
- demos_and_examples/example_00en_simple.py が正常実行

関連コミット：

- b293c58 Add vehicle dict for first arrival times at order-control nodes

### フェーズ3-4/3-5補修：Node作成時の order_control_type 設定にも eligibility 制約を適用

完了済み。

実施内容：

- Node.__init__(...) に order_control_eligible の型チェックを追加
- order_control_eligible は bool のみ許可するようにした
- order_control_eligible="yes" のような文字列を ValueError にする
- order_control_eligible=1 のような int も ValueError にする
- Node作成時に order_control_type!="none" を指定する場合、order_control_eligible=True を必須にした
- これにより、W.addNode(..., order_control_type="fcfs", order_control_eligible=False) のような不整合を ValueError にする
- order_control_type="none" は、従来どおり order_control_eligible=False でも許可する
- World.set_order_control_for_nodes(...) 側の既存安全チェックは変更していない
- Node.__init__(...) のdocstringに、推奨ワークフローを具体例つきで追記
- World.addNode(...) のdocstringにも、直接 order_control_type を指定する場合の注意を追記

設計上の意味：

- これまでは set_order_control_for_nodes(...) を使う場合には安全だった
- しかし、W.addNode(...) 時点で直接 order_control_type="fcfs" などを指定した場合、order_control_eligible=False のまま制御方式を設定できる抜け道があった
- 今回の修正により、Node作成時でも set_order_control_for_nodes(...) 使用時でも、eligibility 制約が一貫して適用されるようになった

推奨ワークフロー：

- 基本的には、Node作成時には order_control_type="none" のままにする
- NodeとLinkを構築する
- World.infer_order_control_eligible_nodes(...) を実行する
- 必要に応じて World.set_order_control_eligible_flag_for_nodes(...) で手動補正する
- 最後に World.set_order_control_for_nodes(...) で order_control_type を設定する

直接指定する場合：

- W.addNode(..., order_control_type="fcfs") のような指定は、order_control_eligible=False がデフォルトなので ValueError になる
- W.addNode(..., order_control_eligible=True, order_control_type="fcfs") のように、order_control_eligible=True を明示した場合は許可される
- batch, time_value も同様

追加・更新したテスト：

- tests_node_order_control_attributes.py

確認済み事項：

- order_control_eligible=False のまま order_control_type="fcfs" を指定すると ValueError
- order_control_eligible=False のまま order_control_type="batch" を指定すると ValueError
- order_control_eligible=False のまま order_control_type="time_value" を指定すると ValueError
- order_control_type="none" かつ order_control_eligible=False は許可される
- order_control_eligible=True を明示すれば、addNode時点で order_control_type="fcfs" を指定できる
- order_control_eligible="yes" で ValueError
- order_control_eligible=1 で ValueError
- tests_node_order_control_attributes.py が正常実行
- tests_world_order_control_setters.py が正常実行
- tests_order_control_eligibility.py が正常実行
- tests_order_exchange_baseline.py が正常実行
- demos_and_examples/example_00en_simple.py が正常実行
- tests_vehicle_research_attributes.py が正常実行

関連コミット：

- 6ac9bc5 Enforce eligibility when setting order_control_type at node creation

## 現在までに追加した主なファイル

- tests_order_exchange_baseline.py
- tests_vehicle_research_attributes.py
- generate_vehicle_list_for_order_exchange.py
- tests_load_vehicle_list_to_uxsim.py
- tests_node_order_control_attributes.py
- tests_world_order_control_setters.py
- tests_order_control_eligibility.py
- tests_random_eligible_order_control.py

## uxsim/uxsim.py の主な変更

### Vehicleへの追加属性

- vot_true
- vot_declared
- payment_paid
- payment_received
- order_exchange_log
- participates_in_order_exchange
- order_control_node_arrival_times

### Nodeへの追加属性

- order_control_type
- batch_size
- transaction_case
- order_control_eligible

Node.__init__(...) での追加チェック：

- order_control_eligible は bool のみ許可
- order_control_type!="none" の場合、order_control_eligible=True が必要
- order_control_type="none" は order_control_eligible=False でも許可

### Worldへの追加属性

- order_control_eligibility_prepared

### Worldへの追加メソッド

- set_order_control_for_nodes(...)
- infer_order_control_eligible_nodes(...)
- set_order_control_eligible_flag_for_nodes(...)
- set_order_control_for_randomly_selected_eligible_nodes(...)

## 現在の重要な設計方針

### 標準UXsim挙動を壊さない

- デフォルトではすべて標準UXsim挙動になるようにする
- 新機能を使わない限り既存サンプルが同じ結果で動くことを毎回確認する

### 車両リストは固定生成・再利用可能にする

- 同じseedなら同じ車両リスト
- 順序交換なしケースと順序交換ありケースで同じ車両リストを使う
- 将来的には複数seedで評価する

### VOTは true と declared を分ける

- vot_true: 真の時間価値
- vot_declared: 申告時間価値
- 初期分析では vot_declared = vot_true
- 将来的には戦略的申告、過大申告、過小申告、非参加などを分析する

### Node制御方式はNodeごとに保持する

- 一部Nodeは標準UXsim
- 一部NodeはFCFS
- 一部NodeはBatch Processing
- 一部NodeはTime-value Transaction

のような混在を将来的に可能にする。

### Node選択方法は研究テーマになり得る

将来的には、以下のようなNode選択方式を想定する。

- 全Node
- Node名リスト
- ランダムに一定割合
- centrality等のネットワーク特徴量に基づく選択
- 流入リンク数・交通量・ボトルネック性等に基づく選択

### 制御対象Nodeは order_control_eligible フラグで管理する

- Nodeごとに order_control_eligible を持たせる
- まず len(node.inlinks) >= 2 かつ len(node.outlinks) >= 1 に基づいて自動判定する
- inlinks=1, outlinks=1 の単純な通過Nodeは、原則として order_control_eligible=False とする
- 補助Nodeなどは、自動判定後に必要に応じて手動で False に上書きする
- 例外的に制御対象候補にしたいNodeは手動で True に上書きできる
- order_control_eligible=True のNodeだけが fcfs / batch / time_value の設定対象になれる
- order_control_eligible=False のNodeには、fcfs / batch / time_value を設定できない
- この制約は set_order_control_for_nodes(...) 経由だけでなく、Node作成時の直接指定にも適用される
- order_control_type="none" は制御解除・標準挙動なので order_control_eligible=False でも許可する

### ランダム選択は order_control_eligible=True のNode集合を対象にする

- ランダム選択は、infer_order_control_eligible_nodes(...) 実行後に行う
- 必要な補助Node除外などは、set_order_control_eligible_flag_for_nodes(...) によって事前に行う
- ランダム選択関数は、補助Nodeを自動検出して除外しない
- fraction は導入割合を表す
- fraction から選択数 n_select を四捨五入相当により決める
- 候補Node集合から n_select 個を重複なしでランダム抽出する
- random_seed により再現可能にする

### 制御用状態と分析ログを分ける

- order_control_node_arrival_times は、事後分析用ログではなく、FCFSなどの制御ロジックが参照する制御用状態である
- 実際に到着時刻を記録する処理は後続フェーズで実装する
- 現時点では node.name をキーにする
- 同一Vehicleが同一Nodeを複数回通る場合はキー設計の拡張が必要

## 次に進む予定

次に進む候補：

- VehicleがFCFS対象Node、またはより一般にorder-control対象Nodeの incoming_vehicles に初めて入った時刻を、order_control_node_arrival_times に記録する処理を設計・実装する
- ただし、記録条件は慎重に設計する必要がある
  - order_control_type=="fcfs" のNodeだけを対象にするか
  - order_control_type!="none" のNode全般を対象にするか
  - order_control_eligible=True も条件に含めるか
- 到着時刻は初回のみ記録し、通過できずに次ステップ以降も incoming_vehicles に入り直しても上書きしない
- Node.transfer() のFCFS分岐や方向切替・クリアランス制約は、まだ後続フェーズで扱う

## 新しいチャットで再開する場合

新しいチャットでは、以下を伝える。

- ORDER_EXCHANGE_PROGRESS.md を読んでください
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md を読んでください
- ORDER_EXCHANGE_RESEARCH_CONTEXT.md を読んでください
- 現在のブランチは feature/intersection-order-control です
- フェーズ4-1まで完了済みです
- order_control_eligible の自動判定条件は、len(node.inlinks) >= 2 かつ len(node.outlinks) >= 1 に修正済みです
- git log --oneline -20 と git status の結果を貼ります
- 次は、order_control_node_arrival_times への到着時刻記録処理の設計・実装を検討する予定です
