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

## 文書保守方針

**採用日：2026-08-25**（作業の途中から正式採用。研究メモ作成当初から一貫適用されていたものではない）

- 過去フェーズの記述は、**歴史的記録**として原則保存する。現在状態と異なる場合は、**削除ではなく**更新注記と最新参照先を追加して整理する。
- 判断が難しい場合は**保守的に残す**。採用前の編集について、失われた記述を**推測で復元しない**。
- 誤字、Markdown 崩れ、明白な転記ミス、歴史的意味のない完全重複は、歴史的意味を変えない範囲で直接修正できる。
- **詳細な方針**は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` の「**文書保守方針**」を参照する。

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

### フェーズ4-2：order-control対象Nodeへの初回到着時刻を記録

完了済み。

実施内容：

- Vehicle クラスに record_order_control_node_first_arrival(node) を追加
- Vehicle が order-control対象Node に初めて到着した時刻を、order_control_node_arrival_times に記録できるようにした
- 到着時刻は、Vehicle が node.incoming_vehicles に入ったタイムステップの時刻と定義した
- Vehicle.update() 内で incoming_vehicles.append(s) が行われる箇所を修正し、append の直後に record_order_control_node_first_arrival(node) を呼ぶようにした
- incoming_vehicles.append(s) が複数箇所にあるため、同じ方針ですべての該当箇所を修正した
- 記録値は W.T * W.DELTAT による秒単位の時刻である
- 現時点では node.name をキーとして order_control_node_arrival_times に保存する
- 同一Vehicleが同一Nodeを複数回通る場合は、将来的にキー設計の拡張が必要である

記録条件：

- node.order_control_eligible is True
- node.order_control_type != "none"
- node.name が vehicle.order_control_node_arrival_times にまだ存在しない

つまり、order-control対象候補であり、かつ実際に fcfs / batch / time_value のいずれかが設定されているNodeのみ記録する。
また、同じVehicle・同じNodeについて既に記録済みの場合は上書きしない。

設計上の意味：

- order_control_node_arrival_times は、事後分析用ログではなく、FCFSなどの制御ロジックが参照する制御用状態である
- FCFSでは、最初にNode通過待ち状態になった時刻を保持し続ける必要がある
- VehicleがNodeに到着しても、outlinkが満杯などで通過できない場合、通常、そのVehicleは現在Linkの下流端に残り、次ステップ以降も再び incoming_vehicles に入る
- その場合でも、初回到着時刻は上書きされない
- これにより、将来のFCFS制御で、通過できずに待たされたVehicleの到着順が後ろにずれることを防ぐ

今回あえて実装していないこと：

- Node.transfer() のFCFS分岐
- FCFS用の車両選択ロジック
- Batch Processing の実制御ロジック
- Time-value Transaction の実制御ロジック
- 方向切替・クリアランス制約
- order_control_node_arrival_orders
- Node側 arrival_order_counter
- order_control_node_passage_log
- 通過時刻ログ

追加したテスト：

- tests_order_control_node_arrival_times.py

確認済み事項：

- 2流入1流出の merge node を作成し、infer_order_control_eligible_nodes() により merge.order_control_eligible=True になることを確認
- merge に order_control_type="fcfs" を設定した場合、Vehicleが merge に初めて到着すると order_control_node_arrival_times["merge"] が記録されることを確認
- merge -> dest の outlink に capacity_in=0 を設定し、Vehicleが merge を通過できない状況を作成
- Vehicleが次ステップ以降も merge の incoming_vehicles に入り直しても、order_control_node_arrival_times["merge"] が初回値のまま上書きされないことを確認
- order_control_type="none" のNodeでは、order_control_eligible=True であっても到着時刻が記録されないことを確認
- tests_order_control_node_arrival_times.py が正常実行
- tests_vehicle_research_attributes.py が正常実行
- tests_node_order_control_attributes.py が正常実行
- tests_world_order_control_setters.py が正常実行
- tests_order_control_eligibility.py が正常実行
- tests_order_exchange_baseline.py が正常実行
- demos_and_examples/example_00en_simple.py が正常実行

関連コミット：

- 481ea84 Record first arrival times at order-control nodes

### フェーズ4-2完了後：FCFS transfer 詳細設計メモの作成

完了済み。

フェーズ4-2完了後の追加設計メモとして、`ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md` を新規作成した。

#### 位置づけ

| ファイル | 位置づけ |
|----------|----------|
| ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md | フェーズ3-5完了後、フェーズ4の制御ロジック本体に入る前の大枠設計メモ |
| ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md | FCFS用 Node.transfer() 分岐の実装に入る直前の詳細設計メモ |

新しいメモは、フェーズ4-2完了後、特にFCFS transfer実装に向けた具体的な設計論点を整理したものである。

#### メモに整理した主な内容

- 標準 Node.transfer() は outlink起点の処理であること
- FCFSは Vehicle到着順起点の処理として設計すること
- まず案A、つまりクリアランスなしFCFSを実装する方針であること
- 案Aでは、到着順、容量制約、先頭Vehicle制約、outlink受入制約のみを扱い、方向切替・クリアランス制約はまだ入れないこと
- 将来の案B、つまりクリアランスありFCFSでは、クリアランス待ちと容量制約による通過不能を区別する必要があること
- 同時到着時の順序固定については、到着時刻そのものを書き換えず、将来的に tiebreaker を別管理する案を整理したこと
- 実際のリンク間移動処理は副作用が多いため、将来的には共通ヘルパー化を検討するが、初回実装では慎重に進める必要があること
- 次の実装フェーズでは、FCFS用 Node.transfer() 分岐の最小実装に進む予定であること

関連コミット：

- 4d317e3 Add FCFS transfer design notes

### フェーズ4-3：初期版クリアランスなしFCFS transfer の実装

完了済み。

#### 実施内容

- 案Aとして、クリアランスなしFCFS transfer の初期実装を行った
- `Node.transfer()` の冒頭に、`order_control_eligible=True` かつ `order_control_type=="fcfs"` の場合だけ FCFS処理へ分岐する処理を追加した
- FCFS対象Nodeでは、`Node.transfer()` から `transfer_fcfs()` を呼び、`return` により標準transfer処理との二重実行を避ける
- `order_control_type="none"` のNodeでは、標準UXsimの `Node.transfer()` 処理を維持する
- 標準 `Node.transfer()` の既存本体は、冒頭分岐追加以外変更していない
- 標準 `Node.transfer()` の既存処理との共通ヘルパー化・関数分割は行っていない
- Nodeクラスに `transfer_fcfs()` を追加した
- `transfer_fcfs()` では、`incoming_vehicles` の中から `route_next_link` を持ち、対象Nodeへの初回到着時刻が記録されているVehicleを候補にする
- 候補Vehicleを `order_control_node_arrival_times[node.name]` の早い順に安定ソートする
- 各Vehicleについて、その時点の最新状態で通過可能性を判定する
- 通過可能なVehicleは、標準 `Node.transfer()` と同等のリンク間移動処理により次Linkへ移す
- 通過不能なVehicleは、その時点ではスキップし、次の到着順Vehicleを検討する
- 1台通すたびに `capacity_in_remain`, `capacity_out_remain`, `flow_capacity_remain` などが更新されるため、後続Vehicleは更新後の条件で評価される
- FCFS分岐では、標準UXsimの `signal_phase` / `signal_group` による信号条件は使わない
- `transfer_fcfs()` の最後で、標準 `Node.transfer()` と同様に trip end待ちVehicleの処理を行い、最後に `incoming_vehicles` をクリアする

#### 今回あえて実装していないこと

- 方向切替・クリアランス制約はまだ未実装
- 同時到着時の固定 tiebreaker はまだ未実装
- Batch Processing はまだ未実装
- Time-value Transaction はまだ未実装
- 支払い・受け取り処理はまだ未実装
- 通過ログ・順序ログはまだ未実装
- 標準 `Node.transfer()` との共通ヘルパー化は行っていない
- FCFS, Batch, Time-value のorder-control系共通ヘルパー化は、将来必要性が明確になった段階で検討する

#### 追加・変更したファイル

変更ファイル：

- `uxsim/uxsim.py`
  - `Node.transfer()` にFCFS分岐を追加
  - `Node.transfer_fcfs()` を追加

追加ファイル：

- `tests_fcfs_order_control_transfer.py`
  - FCFS transfer 初期実装用のスモークテストを追加

#### tests_fcfs_order_control_transfer.py の内容

- 2流入1流出の merge node を持つ最小ネットワークを作成
- `W.infer_order_control_eligible_nodes()` により merge が `order_control_eligible=True` になることを確認
- `W.set_order_control_for_nodes(["merge"], order_control_type="fcfs")` により merge をFCFS対象Nodeに設定
- FCFSケースで、すべてのVehicleがtrip完了することを確認
- FCFSケースで、すべてのVehicleについて merge への初回到着時刻が記録されることを確認
- `order_control_type="none"` の標準ケースでもすべてのVehicleがtrip完了することを確認
- `order_control_type="none"` の標準ケースでは、merge へのorder-control用到着時刻が記録されないことを確認

#### 実行・確認したテスト

新規テスト：

- `python tests_fcfs_order_control_transfer.py` — 成功

既存テスト：

- `python tests_order_control_node_arrival_times.py` — 成功
- `python tests_order_exchange_baseline.py` — 成功
- `python tests_node_order_control_attributes.py` — 成功
- `python tests_world_order_control_setters.py` — 成功
- `python tests_order_control_eligibility.py` — 成功
- `python tests_random_eligible_order_control.py` — 成功
- `python tests_vehicle_research_attributes.py` — 成功
- `python demos_and_examples/example_00en_simple.py` — 成功

#### 標準挙動維持の確認

`tests_order_exchange_baseline.py` について、FCFS実装前後で以下の主要交通結果が一致した。

- number of completed trips: 48 / 48
- total travel time: 2928.0 s
- average travel time of trips: 61.0 s
- average delay of trips: 1.0 s
- delay ratio: 0.017
- total distance traveled: 48000.0 m

`demos_and_examples/example_00en_simple.py` について、FCFS実装前後で以下の主要交通結果が一致した。

- number of completed trips: 735 / 810
- total travel time: 119475.0 s
- average travel time of trips: 162.6 s
- average delay of trips: 62.6 s
- delay ratio: 0.385
- total distance traveled: 1632250.0 m

setup time や computation time は実行環境により揺れるため、交通結果の一致確認対象からは除外した。

関連コミット：

- 984bda9 Add phase 4-3 initial clearance-free FCFS transfer

### フェーズ4-3追加検証：FCFS arrival order と blocked-outlink skip のテスト追加

完了済み。

#### 位置づけ

- これは新しいFCFS制御実装ではなく、フェーズ4-3で実装した初期版クリアランスなしFCFS transfer の詳細挙動を検証するためのテスト追加である
- 案B：クリアランスありFCFSの実装ではない
- tiebreaker、Batch Processing、Time-value Transaction、支払い処理は扱っていない

#### 追加したファイル

- `tests_fcfs_order_control_behavior.py`
  - フェーズ4-3で実装した clearance-free FCFS transfer の詳細挙動を検証するテスト

#### tests_fcfs_order_control_behavior.py の内容

テスト1：`test_fcfs_arrival_order_matches_passing_order()`

目的：

- FCFS対象Nodeにおいて、先にmergeへ到着したVehicleが、後に到着したVehicleより先にmergeを通過することを確認する

ネットワーク：

- orig1 -> link1 -> merge -> out -> dest
- orig2 -> link2 -> merge -> out -> dest
- link1 = 200m
- link2 = 600m
- out = 500m
- 全Linkは number_of_lanes=1
- free_flow_speed=20
- deltan=1
- merge は order_control_type="fcfs"

Vehicle：

- veh_early: orig1 -> dest
- veh_late: orig2 -> dest
- 両方とも departure_time=0
- link1を短くすることで veh_early が先にmergeへ到着する

確認内容：

- merge が order_control_eligible=True であること
- merge が order_control_type="fcfs" であること
- veh_early と veh_late の両方に order_control_node_arrival_times["merge"] が記録されること
- veh_early のmerge到着時刻 < veh_late のmerge到着時刻であること
- out.vehicles_enter_log に基づき、通過順が veh_early -> veh_late であること
- veh_early と veh_late がtrip完了すること

テスト2：`test_fcfs_skips_blocked_first_arrival_and_serves_next_feasible_vehicle()`

目的：

- 先にmergeへ到着したVehicleが、進みたいoutlinkの受入制約により通れない場合、後に到着したVehicleが別outlinkへ通れるなら、先着Vehicleをスキップして後続Vehicleを通すことを確認する

ネットワーク：

- orig1 -> link1 -> merge -> out1 -> dest1
- orig2 -> link2 -> merge -> out2 -> dest2
- link1 = 200m
- link2 = 600m
- out1 = 500m, capacity_in=0
- out2 = 500m
- 全Linkは number_of_lanes=1
- free_flow_speed=20
- deltan=1
- merge は order_control_type="fcfs"

Vehicle：

- veh_early_blocked: orig1 -> dest1
- veh_late_feasible: orig2 -> dest2
- 両方とも departure_time=0
- link1を短くすることで veh_early_blocked が先にmergeへ到着する
- out1.capacity_in=0 により veh_early_blocked はmergeからout1へ入れない
- out2は通常どおり受入可能で、veh_late_feasible はmergeからout2へ進める

確認内容：

- merge が order_control_eligible=True であること
- merge が order_control_type="fcfs" であること
- veh_early_blocked と veh_late_feasible の両方に order_control_node_arrival_times["merge"] が記録されること
- veh_early_blocked のmerge到着時刻 < veh_late_feasible のmerge到着時刻であること
- out1.vehicles_enter_log に veh_early_blocked が含まれないこと
- out2.vehicles_enter_log に veh_late_feasible が含まれること
- veh_late_feasible がtrip完了すること
- veh_early_blocked はout1に入れないため、trip未完了でも許容すること

#### 実行結果

実行コマンド：

```
python tests_fcfs_order_control_behavior.py
```

結果：

- FCFS arrival-order behavior test passed.
- FCFS blocked-first-vehicle skip behavior test passed.
- FCFS order control behavior tests all passed.

つまり、両テストとも成功した。

#### 今回のテスト追加によって確認できたこと

- フェーズ4-3で実装した transfer_fcfs() が、order_control_node_arrival_times に基づき、到着順評価を行えていること
- 到着順がそのまま通過順になる基本ケースが成立していること
- 先着Vehicleがoutlink受入制約により通れない場合、そのVehicleをスキップし、後続の通過可能Vehicleを通せること
- これは、将来の案B：クリアランスありFCFSに進む前に、案A：クリアランスなしFCFSの基本挙動を確認するための重要な回帰テストであること

#### 今回のテストでまだ扱っていないこと

- 先着Vehicleがinlink先頭車でないため通れないケースはまだ未検証
- 同時到着時の挙動はまだ未検証
- tiebreakerはまだ未実装・未検証
- 方向切替・クリアランス制約はまだ未実装・未検証
- Batch Processing と Time-value Transaction はまだ未実装・未検証
- 支払い処理はまだ未実装・未検証

#### 関連コミット

- 09a0f3a Add tests for phase 4-3 FCFS arrival order and blocked-outlink skip

このコミットは origin/feature/intersection-order-control に push 済みである。

#### GitHubへの初回push

今回、これまでローカルGitのみで管理していた feature/intersection-order-control ブランチを、初めて GitHub 上の origin に push した。

実施内容：

- origin が https://github.com/Shi-Nakam/UXsim.git を指していることを確認した
- upstream が https://github.com/toruseo/UXsim.git を指していることを確認した
- feature/intersection-order-control ブランチを origin に初回pushした
- 初回pushのコマンドは `git push -u origin feature/intersection-order-control`
- これにより、GitHub上に origin/feature/intersection-order-control ブランチが作成された
- 以後、このローカルブランチは origin/feature/intersection-order-control をtrackingする状態になった
- その後、09a0f3a も git push により GitHubへ反映済みである

確認結果：

- git status で `Your branch is up to date with 'origin/feature/intersection-order-control'.` を確認した
- git branch -vv で feature/intersection-order-control が `[origin/feature/intersection-order-control]` をtrackingしていることを確認した
- git log --oneline -5 で HEAD と origin/feature/intersection-order-control が 09a0f3a を指していることを確認した

位置づけ：

- これにより、フェーズ4-3までの実装、設計メモ、進捗メモ、詳細検証テストを含む作業履歴が、ローカルPCだけでなくGitHubにも保存された
- 今後は、ローカルで git commit した後、区切りごとに git push によりGitHubへ退避する運用に移行する
- これにより、PC故障・紛失・誤削除に対する安全性が向上した

GitHub認証に関する補足：

- 現時点では HTTPS + Personal Access Token (PAT) により GitHub push 認証を行っている
- 今回作成したPATは 90 days の有効期限で作成した
- その後の git push では、macOSの osxkeychain により認証情報が保存された可能性があり、PAT再入力なしで push に成功した
- ただし、PATは期限切れになる可能性がある
- 長期研究開発でGitHub運用に慣れてきた段階では、HTTPS + PAT から SSH 接続へ移行することを検討する
- SSH接続に移行すれば、PAT更新やHTTPS認証まわりの手間を減らせる可能性がある
- SSH移行は必須ではないが、長期運用では推奨される候補として記録しておく

### フェーズ4-4：FCFS同時到着時の固定tiebreaker実装と検証テスト追加

完了済み。

#### 位置づけ

- フェーズ4-4では、フェーズ4-3で実装した初期版クリアランスなしFCFS transferに対して、同時到着時の順位を固定するためのtiebreakerを追加した
- これは案B：クリアランスありFCFSに進む前の前提整備である
- クリアランス制約そのものはまだ実装していない
- Batch Processing、Time-value Transaction、支払い処理もまだ実装していない

#### uxsim/uxsim.py の変更内容

Vehicleへの追加属性：

- Vehicleに `order_control_node_arrival_tiebreakers = {}` を追加した
- この属性は、order-control対象Nodeごとに、同時到着時の固定補助順位を保存する辞書である
- キーは `node.name`
- 値は初回到着時に生成された固定tiebreaker値である
- `order_control_node_arrival_times` と対になる制御用属性である

`record_order_control_node_first_arrival(node)` の変更：

- order-control対象Nodeへの初回到着時に、arrival_time と tiebreaker を同時に記録するようにした
- arrival_time は `order_control_node_arrival_times[node.name]` に記録する
- tiebreaker は `order_control_node_arrival_tiebreakers[node.name]` に記録する
- tiebreaker は `s.W.rng.random()` により生成する
- Python標準の `random.random()` は使っていない
- 同一Vehicle・同一Nodeについて、arrival_time も tiebreaker も初回のみ記録し、以後上書きしない
- arrival_time そのものは補正・変更していない
- tiebreaker は同時到着Vehicleに限らず、order-control対象Nodeへ初回到着したすべてのVehicleに記録する。ただし、ソートでは arrival_time が第1キーなので、arrival_time が異なるVehicle同士では tiebreaker は実質的に順位に影響しない

`transfer_fcfs()` の変更：

- FCFS候補Vehicleのソートキーを、従来の arrival_time のみから、以下の3要素に変更した
  1. `order_control_node_arrival_times[node.name]`
  2. `order_control_node_arrival_tiebreakers[node.name]`
  3. `veh.id`
- つまり、実装上は概念的に以下のソートキーになっている

  `(arrival_time, tiebreaker, veh.id)`

- 第1キーは実際の初回到着時刻
- 第2キーは同時到着時の固定tiebreaker
- 第3キーの `veh.id` は、万一 tiebreaker まで同値だった場合の決定的な最終タイブレークである
- `transfer_fcfs()` 内では新しい乱数を引かず、記録済みのtiebreakerと既存の `veh.id` を読むだけである
- 通過可否判定や blocked-outlink skip の処理本体は変更していない
- 方向切替・クリアランス制約はまだ入れていない

blocked-outlink skip の意味：

- ここでいう blocked-outlink skip とは、先に到着したVehicleが、進みたいoutlinkの受入制約により通過できない場合に、そのVehicleをその時点ではスキップし、到着順で後順位のVehicleが別outlinkへ通過可能であれば通す、という現在の案A：クリアランスなしFCFSの挙動を指す
- 今回のtiebreaker実装では、評価順を `(arrival_time, tiebreaker, veh.id)` に変更したが、その評価順が決まった後の blocked-outlink skip の処理本体は変更していない

#### 追加したテストファイル

- `tests_fcfs_order_control_tiebreaker.py`
  - FCFS同時到着時の固定tiebreakerが正しく機能することを確認するテスト

#### tests_fcfs_order_control_tiebreaker.py の内容

テスト：`test_fcfs_tiebreaker_orders_simultaneous_arrivals()`

目的：

- 同じタイムステップに merge へ同時到着した2台のVehicleについて、arrival_time が同じ場合に、固定tiebreaker順に merge を通過することを確認する

ネットワーク：

- orig1 -> link1 -> merge -> out -> dest
- orig2 -> link2 -> merge -> out -> dest
- link1 = 400m
- link2 = 400m
- out = 500m
- 全Linkは number_of_lanes=1
- free_flow_speed=20
- deltan=1
- random_seed=0
- merge は order_control_type="fcfs"

Vehicle：

- veh_tie_1: orig1 -> dest
- veh_tie_2: orig2 -> dest
- 両方とも departure_time=0
- link1 と link2 を同じ長さ・同じ速度にすることで、veh_tie_1 と veh_tie_2 が merge に同時到着するようにしている

確認内容：

- merge が order_control_eligible=True であること
- merge が order_control_type="fcfs" であること
- veh_tie_1 と veh_tie_2 の両方に order_control_node_arrival_times["merge"] が記録されること
- veh_tie_1 と veh_tie_2 の両方に order_control_node_arrival_tiebreakers["merge"] が記録されること
- veh_tie_1 と veh_tie_2 の arrival_time が等しいこと
- 同時到着しなかった場合は、「同時到着せず」として arrival_time を含むassertメッセージを出すこと
- tiebreaker が数値として取得できること
- veh.id が両車で異なること
- expected_order を transfer_fcfs() と同じソートキー、つまり `(arrival_time, tiebreaker, veh.id)` で作ること
- out.vehicles_enter_log から actual_order を取得すること
- actual_order == expected_order であること
- tiebreaker順に通過しなかった場合は、「tiebreaker順に通過せず」として expected_order, actual_order, arrival_time, tiebreaker, veh.id を含むassertメッセージを出すこと
- veh_tie_1 と veh_tie_2 がtrip完了すること

#### 実行結果

実行コマンド：

```
python tests_fcfs_order_control_tiebreaker.py
```

結果：

- FCFS simultaneous-arrival tiebreaker test passed.

既存FCFS挙動が壊れていないことを確認するため、以下も実行済みである。

実行コマンド：

```
python tests_fcfs_order_control_behavior.py
```

結果：

- FCFS arrival-order behavior test passed.
- FCFS blocked-first-vehicle skip behavior test passed.
- FCFS order control behavior tests all passed.

#### 今回確認できたこと

- 同時到着時に arrival_time が同じ値として記録されること
- tiebreaker のために arrival_time そのものを補正していないこと
- tiebreaker が order-control対象Nodeへの初回到着時に固定値として記録されること
- transfer_fcfs() が `(arrival_time, tiebreaker, veh.id)` に基づいて候補Vehicleを評価できること
- 同時到着Vehicleについて、固定tiebreaker順に通過順が決まること
- 既存の arrival-order behavior と blocked-outlink skip behavior が維持されていること
- 今回のtiebreaker実装は、将来の案B：クリアランスありFCFSにおいて、同時到着時の優先順位を固定するための前提整備であること

#### 今回まだ扱っていないこと

- 方向切替・クリアランス制約はまだ未実装
- クリアランス待ちと容量制約による通過不能の区別はまだ未実装
- 先順位Vehicleがクリアランス待ちの場合に、後順位Vehicleが先順位Vehicleを追い越せないようにするルールはまだ未実装
- Batch Processing はまだ未実装
- Time-value Transaction はまだ未実装
- 支払い処理はまだ未実装
- tiebreaker まで同値になった場合に veh.id が第3キーとして機能することの人工的な専用テストは、今回は追加していない。ただし expected_order には実装と同じく veh.id を含めている

#### 関連コミット

- d3f3c4d phase 4-4: add FCFS arrival tiebreakers and tests

このコミットは origin/feature/intersection-order-control に push 済みである。

### フェーズ4-5設計：クリアランスありFCFS正式設計メモの追加

完了済み。

#### 位置づけ

- phase 4-5として、案B：クリアランスありFCFSの正式設計メモを追加した
- 今回は設計メモ作成のみであり、コード実装はまだ行っていない
- クリアランスありFCFSは、本研究で評価対象とする本来のFCFSモデルとして位置づける
- クリアランスなしFCFSは、実装検証用・デバッグ用・退避用として残す方針である
- Batch Processing、Time-value Transaction、支払い処理はまだ実装していない

#### 追加したファイル

- `ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md`
  - phase 4-5：案BクリアランスありFCFSの正式設計メモ

#### 設計メモに含めた主な内容

- 案A：クリアランスなしFCFSと、案B：クリアランスありFCFSの位置づけ
- 既存 `transfer_fcfs()` を `transfer_fcfs_no_clearance()` に改名して、回帰確認・デバッグ用として残す方針
- 案B用に `transfer_fcfs_clearance()` を新設する方針
- 最終的に `order_control_type="fcfs"` は `transfer_fcfs_clearance()` を呼ぶ想定であること
- `transfer_fcfs_clearance()` が、既存FCFS処理から何を踏襲し、何を変更し、何を追加するか
- inlink が異なれば異方向切替とみなすこと
- `clearance_timesteps` の意味
- `clearance_timesteps = 0` の意味
- `clearance_timesteps` はFCFSだけでなく、将来のBatch Processing、Time-value Transactionにも共通に適用する想定であること
- World共通clearance設定と setter 方針
- Nodeに必要な状態
  - `order_control_clearance_timesteps`
  - `last_order_control_inlink`
  - `last_order_control_entry_timestep`
- 通過後に `last_order_control_inlink` と `last_order_control_entry_timestep` を更新する方針
- 同一タイムステップ内の複数通過ルール
- X/Y/Z問題
- 修正版の判定順
- シナリオ1〜3との整合確認
- 通過不能理由の扱い
- phase 4-5 実装順序案
- phase 4-5 テスト方針
- 未解決・注意事項

#### X/Y/Z問題

- 方向A：車X、先着順位1
- 方向B：車Y、先着順位2
- 方向A：車Z、先着順位3

単純に、

- 容量・物理制約NGなら continue
- クリアランスNGなら break

とすると、Xが容量制約で通れず、Yも容量制約で通れない場合に、Zが検討されてしまい、方向Bの先順位Vehicle Yを方向Aの後順位Vehicle Zが追い越す可能性がある。

このため、単純な continue / break 設計では不十分である。

#### 修正版の判定順

候補Vehicleは、既存のFCFS順序に従い、

```
(arrival_time, tiebreaker, veh.id)
```

の順で評価する。

各候補Vehicleについて、以下の順で判定する。

1. 候補Vehicleの inlink を取得する。
2. 直近通過 inlink と比較する。
3. 異方向で、かつクリアランス未充足なら、容量・物理制約を見る前に break する。
4. クリアランス不要またはクリアランス充足の場合に限り、容量・物理制約を見る。
5. 容量・物理制約NGなら continue する。
6. 容量・物理制約OKなら通過させる。
7. 通過後、`last_order_control_inlink` と `last_order_control_entry_timestep` を更新する。

この修正版判定順により、少なくとも設計メモで検討したシナリオ1〜3には整合的に対応できる見通しが立った。

#### 今回まだ実装していないこと

- `transfer_fcfs()` の `transfer_fcfs_no_clearance()` への改名はまだ未実装
- `transfer_fcfs_clearance()` はまだ未実装
- Nodeへの clearance用状態追加はまだ未実装
- World共通clearance設定はまだ未実装
- World共通clearance設定用setterはまだ未実装
- `Node.transfer()` の fcfs 分岐切替はまだ未実装
- phase 4-5用のクリアランスありFCFSテストはまだ未実装
- Batch Processing、Time-value Transaction、支払い処理はまだ未実装

#### 関連コミット

- c060dce phase 4-5: add clearance FCFS design notes

このコミットは origin/feature/intersection-order-control に push 済みである。

### フェーズ4-5実装：クリアランスありFCFSの実装・接続・検証

完了済み。

#### 全体概要

- phase 4-5として、設計メモで整理したクリアランスありFCFSを実装・接続・検証した。
- 既存のクリアランスなしFCFSは `transfer_fcfs_no_clearance()` として退避済み。
- 新たに `transfer_fcfs_clearance()` を実装し、現在の `order_control_type=="fcfs"` の通常経路は `transfer_fcfs_clearance()` を呼ぶ。
- `clearance_timesteps` は World共通設定として追加済み。
- Nodeには clearance用状態として以下を追加済み。
  - `order_control_clearance_timesteps`
  - `last_order_control_inlink`
  - `last_order_control_entry_timestep`
- `clearance_timesteps=0` / `1` の基本テストを追加済み。
- X/Y/Z問題の6テストを追加済み。
- baseline および `example_00en_simple.py` の主要交通結果は既知基準値と一致。
- Batch Processing、Time-value Transaction、支払い処理はまだ未実装。

#### Step 1：クリアランスなしFCFSの退避

実施コミット：

- 2b980db phase 4-5: rename clearance-free FCFS transfer

実施内容：

- 既存の `transfer_fcfs()` を `transfer_fcfs_no_clearance()` に改名した。
- `transfer_fcfs_no_clearance()` は、クリアランスなしFCFSとして回帰確認・デバッグ用に残した。
- 本研究で評価対象とする最終的なFCFSモデルとしては使用しない旨をコメント・docstringで明記した。
- この時点では `Node.transfer()` の fcfs 分岐は `transfer_fcfs_no_clearance()` を呼んでおり、挙動は従来どおりだった。
- `transfer_fcfs_no_clearance()` の内部ロジックは変更していない。
- `transfer_fcfs_clearance()` はこの時点では未作成。

#### Step 2：clearance設定・Node状態・setter追加

実施コミット：

- 5d98f83 phase 4-5: add order-control clearance settings
- f03fd81 phase 4-5: clarify clearance state comments

実施内容：

- Worldに `order_control_clearance_timesteps = 1` を追加した。
- Nodeに以下の属性を追加した。
  - `order_control_clearance_timesteps`
  - `last_order_control_inlink`
  - `last_order_control_entry_timestep`
- Node側コメントは最終的に以下の趣旨に整理した。
  - World共通のorder-control clearance設定を、Nodeごとの参照値として保持する。
  - `last_order_control_*` は、clearance-awareなorder-control transferで、直近にこのNodeへ進入したVehicleのinlinkと進入タイムステップを記録するための初期値。
- `World.set_order_control_clearance_timesteps(clearance_timesteps)` を追加した。
- setterは以下を行う。
  - World共通値を更新する。
  - 既存全Nodeの `node.order_control_clearance_timesteps` に同じ値を反映する。
- setterのバリデーション：
  - intのみ許可。
  - boolは拒否。
  - 負値は拒否。
  - 無効値はValueError。
- `W.addNode(...)` で新規作成されるNodeは、その時点の `W.order_control_clearance_timesteps` を保持する。
- `set_order_control_for_nodes()` にclearance_timesteps個別override引数は追加していない。
- transferロジックはこのStepでは変更していない。

追加テスト：

- `tests_order_control_clearance_settings.py`

確認内容：

- World初期値1。
- Node初期値1。
- setterで0/2に変更した際、既存全Nodeに反映。
- setter後に作成したNodeが現在のWorld共通値を継承。
- -1, 1.5, "1", True, False を拒否。

#### Step 3A：transfer_fcfs_clearance() の未接続追加

実施コミット：

- 63a553f phase 4-5: add unconnected clearance-aware FCFS transfer method

実施内容：

- Nodeクラス内に `transfer_fcfs_clearance()` を新設した。
- ただし、この時点では `Node.transfer()` の fcfs 分岐にはまだ接続していなかった。
- したがって、通常シミュレーション経路ではまだ `transfer_fcfs_clearance()` は呼ばれていなかった。
- `transfer_fcfs_no_clearance()` の処理をベースに、以下を踏襲した。
  - candidates の作り方
  - ソートキー `(arrival_time, tiebreaker, veh.id)`
  - `route_next_link` を持つVehicleだけを候補にする考え方
  - `order_control_node_arrival_times` が記録済みのVehicleだけを候補にする考え方
  - 既存FCFSの通過可否判定
  - 通過処理
  - `capacity_in_remain`, `capacity_out_remain`, `flow_capacity_remain` の更新
  - trip終了処理
  - `incoming_vehicles` の後処理
- 新たに追加したクリアランス判定：
  - 通過前に `current_inlink = veh.link` を保存する。
  - `s.last_order_control_inlink` が None の場合はクリアランス不要。
  - `current_inlink == s.last_order_control_inlink` の場合は同方向なのでクリアランス不要。
  - `current_inlink != s.last_order_control_inlink` の場合は異方向切替として `clearance_timesteps` に基づき判定。
  - 判定式は `s.W.T - s.last_order_control_entry_timestep > s.order_control_clearance_timesteps`。
  - クリアランス未充足なら、既存FCFSの通過可否判定を見る前に break。
  - クリアランス不要または充足後に、既存FCFSの通過可否判定を行う。
  - 既存FCFSの通過可否判定で通れない場合は continue。
  - 通過成功後、`last_order_control_inlink` と `last_order_control_entry_timestep` を更新。
- `last_order_control_inlink` には、通過前に保存した `current_inlink` を使う。
- `last_order_control_entry_timestep` には現在の timestep `s.W.T` を使う。

#### Step 3B：通常fcfs経路への接続と clearance=0 基本テスト

実施コミット：

- 0e7b300 phase 4-5: connect clearance-aware FCFS transfer and add basic test

実施内容：

- `Node.transfer()` の `order_control_type=="fcfs"` 分岐を、`transfer_fcfs_no_clearance()` から `transfer_fcfs_clearance()` に切り替えた。
- この変更により、通常のfcfs経路はクリアランスありFCFSを使う状態になった。
- `transfer_fcfs_no_clearance()` は削除せず、回帰確認・デバッグ用として残した。

変更イメージ：

```
if s.order_control_eligible and s.order_control_type == "fcfs":
    s.transfer_fcfs_clearance()
    return
```

追加テスト：

- `tests_fcfs_order_control_clearance_basic.py`
  - 後続Step 3Cで `tests_fcfs_order_control_clearance_0.py` に改名済み。

確認内容：

- `clearance_timesteps=0` の基本挙動を確認。
- 同時到着2台について、`actual_order == expected_order` を確認。
- `expected_order` は `(arrival_time, tiebreaker, veh.id)` の昇順。
- `clearance_timesteps=0` でも、同一タイムステップ内の異方向連続通過が起きないことを確認。
- 2台ともtrip完了。

#### Step 3C：clearance=0/1 テスト整理・追加

実施コミット：

- 7d6964d phase 4-5: rename FCFS clearance 0 test and add FCFS clearance 1 test

実施内容：

- `tests_fcfs_order_control_clearance_basic.py` を `tests_fcfs_order_control_clearance_0.py` に改名した。
- `tests_fcfs_order_control_clearance_1.py` を新規追加した。
- `uxsim/uxsim.py` は変更していない。
- `transfer_fcfs_clearance()`, `transfer_fcfs_no_clearance()`, `Node.transfer()` は変更していない。

`tests_fcfs_order_control_clearance_0.py`：

- `clearance_timesteps=0` の基本挙動テスト。
- `actual_order == expected_order` を確認。
- 2台のout進入時刻が同一でないことを確認。
- 2台目のout進入時刻が1台目より後であることを確認。

`tests_fcfs_order_control_clearance_1.py`：

- `clearance_timesteps=1` の基本挙動テスト。
- `actual_order == expected_order` を確認。
- `time_gap = second_enter_time - first_enter_time` を確認。
- `time_gap >= 2 * W.DELTAT - tolerance` を確認。
- 成功時に以下をprintする。
  - first_enter_time
  - second_enter_time
  - time_gap
  - W.DELTAT
  - time_gap / W.DELTAT
- 実際の成功時出力例：
  - first_enter_time: 21
  - second_enter_time: 23
  - time_gap: 2
  - W.DELTAT: 1
  - time_gap / W.DELTAT: 2.0

#### Step 3D：X/Y/Z問題テスト追加

実施コミット：

- 7c53265 phase 4-5: add FCFS clearance X/Y/Z tests

新規追加ファイル：

- `tests_fcfs_order_control_clearance_xyz.py`

実施内容：

- X/Y/Z問題の中核挙動を確認する6テストを追加した。
- `uxsim/uxsim.py` は変更していない。
- `transfer_fcfs_clearance()`, `transfer_fcfs_no_clearance()`, `Node.transfer()` は変更していない。
- 既存テストファイルも変更していない。

X/Y/Z問題の定義：

- X：方向A、先着順位1
- Y：方向B、先着順位2
- Z：方向A、先着順位3
- XとZは同じinlinkからmergeへ進入。
- Yは異なるinlinkからmergeへ進入。
- 候補順序は `(arrival_time, tiebreaker, veh.id)` により X -> Y -> Z となることを必須assert。

enter_time の扱い：

- enter_time は `Link.vehicles_enter_log` のkeyとして記録される時刻値。
- Test 1/2では `out.vehicles_enter_log` から `x_enter_time`, `y_enter_time`, `z_enter_time` を取得。
- Test 3では `outA.vehicles_enter_log` から `x_enter_time`, `z_enter_time` を取得し、`outB.vehicles_enter_log` にveh_yが存在しないことを確認。

gap の扱い：

- Test 1/2：
  - `y_gap = y_enter_time - x_enter_time`
  - `z_gap_after_y = z_enter_time - y_enter_time`
- Test 3：
  - `z_gap_after_x = z_enter_time - x_enter_time`
- `tolerance = 1e-9`
- 上限側にも tolerance を入れる。
- clearance=0：
  - `1 * W.DELTAT - tolerance <= gap < 2 * W.DELTAT - tolerance`
- clearance=1：
  - `2 * W.DELTAT - tolerance <= gap < 3 * W.DELTAT - tolerance`

使用したネットワーク：

- Network A：Test 1A/1B/2A/2B用。
  - origA/origB -> merge -> 共通out -> dest。
  - X/Y/Z全て同じoutへ進入可能。
- Network B：Test 3A/3B用。
  - X/ZはoutAへ向かう。
  - YのみoutBへ向かう。
  - outBは `capacity_in=0` により受入不能。

作成した6つのテスト：

- Test 1A：`test_xyz_simultaneous_clearance_zero_blocks_z`
  - Network A、同時到着型、X=0/Y=0/Z=1、clearance=0。
- Test 1B：`test_xyz_staggered_clearance_zero_blocks_z`
  - Network A、逐次到着型、X=0/Y=1/Z=2、clearance=0。
- Test 2A：`test_xyz_simultaneous_clearance_one_blocks_z`
  - Network A、同時到着型、X=0/Y=0/Z=1、clearance=1。
- Test 2B：`test_xyz_staggered_clearance_one_blocks_z`
  - Network A、逐次到着型、X=0/Y=1/Z=2、clearance=1。
- Test 3A：`test_xyz_simultaneous_y_blocked_z_passes_after_clearance`
  - Network B、同時到着型、X=0/Y=0/Z=1、clearance=1、Y blocked。
- Test 3B：`test_xyz_staggered_y_blocked_z_passes_after_clearance`
  - Network B、逐次到着型、X=0/Y=1/Z=2、clearance=1、Y blocked。

seed探索：

- 同時到着型ではX/Yがmergeに同時到着するため、X/Yの相対順序はtiebreakerに依存する。
- seed探索により `expected_order == ["veh_x", "veh_y", "veh_z"]` となるseedを採用した。
- 実際には seed=1 が採用された。
- seed探索では、`actual_order`, `enter_time`, gap条件を選択基準にしていない。
- 逐次到着型では seed=0 を使用し、arrival_time により `expected_order == ["veh_x", "veh_y", "veh_z"]` が成立。

テスト結果：

- Test 1A / 1B：clearance=0
  - `actual_order == expected_order == ["veh_x", "veh_y", "veh_z"]`
  - `y_gap = 1`
  - `z_gap_after_y = 1`
- Test 2A / 2B：clearance=1
  - `actual_order == expected_order == ["veh_x", "veh_y", "veh_z"]`
  - `y_gap = 2`
  - `z_gap_after_y = 2`
- Test 3A / 3B：Y outlink blocked 簡易版
  - outBは `capacity_in=0` でブロック。
  - veh_yはoutBに進入していない。
  - outAでは veh_x と veh_z が進入。
  - `x_enter_time=21`, `z_enter_time=23`
  - `z_gap_after_x=2`
  - veh_x, veh_z はtrip完了。
  - veh_y のtrip完了は要求していない。

#### 現在の実装状態

- 現在の `order_control_type=="fcfs"` の通常経路は `transfer_fcfs_clearance()` を呼ぶ。
- `transfer_fcfs_no_clearance()` は回帰確認・デバッグ用として残っている。
- `clearance_timesteps` はWorld共通設定として持つ。
- Nodeごとに `order_control_clearance_timesteps` を保持する。
- Nodeごとに `last_order_control_inlink` と `last_order_control_entry_timestep` を保持する。
- 通過成功後、`transfer_fcfs_clearance()` は `last_order_control_inlink` と `last_order_control_entry_timestep` を更新する。
- clearance=0/1 と X/Y/Z問題についてテスト済み。
- 標準UXsim挙動を壊さないことを、baselineおよびexampleで確認済み。

#### 実行済みテスト

以下を実行済みで、すべて成功した。

- `python tests_fcfs_order_control_clearance_xyz.py`
- `python tests_fcfs_order_control_clearance_0.py`
- `python tests_fcfs_order_control_clearance_1.py`
- `python tests_order_control_clearance_settings.py`
- `python tests_fcfs_order_control_transfer.py`
- `python tests_fcfs_order_control_behavior.py`
- `python tests_fcfs_order_control_tiebreaker.py`
- `python tests_order_control_node_arrival_times.py`
- `python tests_vehicle_research_attributes.py`
- `python tests_order_exchange_baseline.py`
- `python demos_and_examples/example_00en_simple.py`

baseline主要交通結果：

- completed trips: 48 / 48
- total travel time: 2928.0 s
- average travel time: 61.0 s
- average delay: 1.0 s
- delay ratio: 0.017
- total distance: 48000.0 m

`example_00en_simple.py` 主要交通結果：

- completed trips: 735 / 810
- total travel time: 119475.0 s
- average travel time: 162.6 s
- average delay: 62.6 s
- delay ratio: 0.385
- total distance: 1632250.0 m

#### まだ未実装・後続事項

- Batch Processing は未実装。
- Time-value Transaction は未実装。
- 支払い処理は未実装。
- Node別の `clearance_timesteps` override は未実装。
- `transfer_fcfs_no_clearance()` は残しているが、通常のfcfs経路からは外れている。
- 今後、ORDER_EXCHANGE_PROGRESS.md のこの記録をもとに、Batch Processing / Time-value Transaction へ進む。

#### 関連コミット

- 2b980db phase 4-5: rename clearance-free FCFS transfer
- 5d98f83 phase 4-5: add order-control clearance settings
- f03fd81 phase 4-5: clarify clearance state comments
- 63a553f phase 4-5: add unconnected clearance-aware FCFS transfer method
- 0e7b300 phase 4-5: connect clearance-aware FCFS transfer and add basic test
- 7d6964d phase 4-5: rename FCFS clearance 0 test and add FCFS clearance 1 test
- 7c53265 phase 4-5: add FCFS clearance X/Y/Z tests

これらは origin/feature/intersection-order-control に push 済みである。

### フェーズ4-5追加検証：UXsim標準挙動とFCFS(clearance=0/1)のsanity check比較

完了済み。

#### 全体概要

- phase 4-5のFCFS実装について、小規模単体テスト・X/Y/Z問題テストに加えて、中規模・grid型ネットワークでのsanity check比較を実施した。
- Step 4A〜4Dは FCFS(clearance=0)、Step 4Eは FCFS(clearance=1) を対象とする。
- 比較対象は以下の5種類。
  - corridor型ネットワークにおけるunsignalized UXsim標準transfer vs FCFS(clearance=0)（Step 4A）
  - grid型ネットワークにおけるunsignalized UXsim標準transfer vs FCFS(clearance=0)（Step 4B）
  - grid型ネットワークにおけるsignalized UXsim標準transfer vs FCFS(clearance=0)（Step 4C：1000台）
  - grid型ネットワークにおけるsignalized UXsim標準transfer vs FCFS(clearance=0)（Step 4D：高需要5000台・10000台）
  - grid型ネットワークにおけるsignalized all-red UXsim標準transfer vs FCFS(clearance=1)（Step 4E：高需要5000台・10000台）
- 目的は研究上の性能評価ではなく、FCFS実装が中規模・複数経路ネットワークで極端に破綻しないことを確認する sanity check である。
- FCFSがUXsim標準より常に良い、または常に悪いと主張するものではない。
- ケースによってFCFSが良い場合も悪い場合もあり得る。
- 重要なのは、完了台数・平均旅行時間・総旅行時間・総走行距離などが極端に乖離しないかを確認すること。
- Step 4A〜4Eはいずれも `uxsim/uxsim.py` を変更せず、新規テストファイルのみ追加した。

#### Step 4A：corridor型ネットワークでのunsignalized UXsim標準 vs FCFS(clearance=0)

実施コミット：

- 683f560 phase 4-5: add corridor FCFS vs UXsim standard sanity test

重要な補足：

- このコミット名には unsignalized と入っていない。
- しかし実態としては、明示的信号制御なしのUXsim標準transferとFCFS(clearance=0)の比較である。
- したがって、このStep 4Aは「corridor型 unsignalized UXsim標準transfer vs FCFS(clearance=0)」として位置づける。

新規追加ファイル：

- `tests_order_control_fcfs_vs_uxsim_standard_medium_network.py`

目的：

- corridor型中規模ネットワークで、unsignalized UXsim標準transferとFCFS(clearance=0)を比較する。
- FCFS(clearance=0)をeligible node全体に適用したとき、極端な破綻が起きないことを確認する。

ネットワーク概要：

- 幹線 corridor 型ネットワーク。
- `u1/u2 -> m0 -> m1 -> j2 -> m2 -> ... -> m9 -> d_main` のような幹線構造。
- side流入 `s1`〜`s8` 等を持つ。
- 途中出口 `d3`, `d5`, `d7` を持つ。
- 全Linkで `number_of_lanes=1`。
- 全Linkで `merge_priority=1`。
- `deltan=1`。
- `random_seed=0`。
- `tmax=2500`。
- FCFS eligible nodeは10個。
  - `m0`, `m1`, `j2`, `m2`, `m3`, `j4`, `m5`, `m6`, `m7`, `m8`

需要：

- Vehicle数：500。
- first departure time：0.0。
- last departure time：300.0。
- demand duration：300.0。
- average departure interval：約0.601。
- vehicles per timestep：約1.667。
- 11 origins × 4 destinations から `DEMAND_GEN_SEED=42` でODを生成。
- 標準ケースとFCFSケースで同一 `vehicle_plans` を使用。

比較結果：

- UXsim標準：
  - completed trips：383 / 500
  - completed ratio：0.766
  - total travel time：53941.0 s
  - average travel time：140.8 s
  - average delay：11.2 s
  - delay ratio：0.080
  - total distance：992850.0 m
- FCFS(clearance=0)：
  - completed trips：383 / 500
  - completed ratio：0.766
  - total travel time：56257.0 s
  - average travel time：146.9 s
  - average delay：17.3 s
  - delay ratio：0.118
  - total distance：992850.0 m

Comparison ratios：

- completed ratio difference：0.000
- average travel time ratio：1.043
- total travel time ratio：1.043
- total distance traveled ratio：1.000

解釈：

- FCFS(clearance=0)はunsignalized UXsim標準transferより約4.3%遅い。
- ただし完了台数・総走行距離は同一。
- 極端な破綻は検出されなかった。

#### Step 4B：grid型ネットワークでのunsignalized UXsim標準 vs FCFS(clearance=0)

実施コミット：

- 492f33e phase 4-5: add grid FCFS vs unsignalized UXsim standard sanity test

新規追加ファイル：

- `tests_order_control_fcfs_vs_uxsim_standard_grid_network.py`

目的：

- grid / mesh型ネットワークで、unsignalized UXsim standard transfer と FCFS(clearance=0)を比較する。
- corridor型では見えにくい、複数経路・経路選択・リンク選好があり得る状況で、FCFSが極端に破綻しないことを確認する。

ネットワーク概要：

- 6×6内部grid。
- 内部gridノード：36個（`g_0_0` から `g_5_5`）。
- 外周ODノード：24個（`top_*`, `bottom_*`, `left_*`, `right_*`）。
- 合計：60ノード。
- 内部双方向リンク：120本。
- 外周OD接続双方向リンク：48本。
- 合計：168リンク。
- 全Linkで `number_of_lanes=1`。
- 全Linkで `merge_priority=1`。
- 外周ODノードの角は辺ごとに別ノードとして扱う。
- `origin_grid_coord` / `destination_grid_coord` は、外周ODノードが接続する内部gridノードの座標であり、OD距離判定用メタデータとして使用。

標準ケースの制御：

- UXsim standard `Node.transfer`。
- `order_control_type="none"`。
- `set_order_control_for_nodes()` は未呼び出し。
- explicit signal settings：no。
- default signal settings：`signal=[0]`。
- signalized node count：0。
- `signal=[0]` は `uxsim.py` のdocstring上、no signal を意味する。
- したがって、この比較は「明示的信号制御あり」ではなく、「unsignalized UXsim standard transfer」とFCFS(clearance=0)の比較である。

需要：

- Vehicle数：1000。
- first departure time：0.0。
- last departure time：500.0。
- demand duration：500.0。
- average departure interval：約0.501。
- vehicles per timestep：2.0。
- OD Manhattan distance：min 5、average 約6.73、max 10。
- `vehicle_plans` は標準ケースとFCFSケースで完全共通。
- 固定routeは指定せず、ODのみ指定。

FCFS対象：

- eligible node：36個。
- 全内部gridノード `g_0_0`〜`g_5_5` がFCFS対象。
- `clearance_timesteps=0`。

比較結果：

- UXsim標準：
  - completed trips：1000 / 1000
  - completed ratio：1.000
  - total travel time：165917.0 s
  - average travel time：165.9 s
  - average delay：1.3 s
  - delay ratio：0.008
  - total distance：3292000.0 m
- FCFS(clearance=0)：
  - completed trips：1000 / 1000
  - completed ratio：1.000
  - total travel time：167772.0 s
  - average travel time：167.8 s
  - average delay：3.2 s
  - delay ratio：0.019
  - total distance：3292000.0 m

Comparison ratios：

- completed ratio difference：0.000
- average travel time ratio：1.011
- total travel time ratio：1.011
- total distance traveled ratio：1.000

解釈：

- unsignalized UXsim standard transfer と FCFS(clearance=0) は、grid型・1000台規模でもほぼ同等。
- FCFSは標準より約1.1%遅い。
- 完了台数・総走行距離は同一。
- 極端な破綻は検出されなかった。

#### Step 4C：grid型ネットワークでのsignalized UXsim標準 vs FCFS(clearance=0)

実施コミット：

- c810e2b phase 4-5: add grid FCFS vs signalized UXsim standard sanity test

新規追加ファイル：

- `tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_network.py`

目的：

- grid / mesh型ネットワークで、明示的な信号制御ありUXsim標準挙動とFCFS(clearance=0)を比較する。
- Step 4Bのunsignalized比較に対し、signalized UXsim standardとの比較を行う。
- FCFS(clearance=0)がsignalized UXsim standardと比べて極端に破綻しないことを確認する。

信号設定：

- 内部gridノード36個すべてに `signal=[60, 60]` を設定。
- phase 0：東西方向。
- phase 1：南北方向。
- signal_group 0：東西リンク（水平内部リンク、left/right接続）。
- signal_group 1：南北リンク（垂直内部リンク、top/bottom接続）。
- 外周ODノードには信号を設定しない。
- signalized OD node count：0。
- signal offsets：全内部gridで0。

ネットワーク概要：

- Step 4Bと同じ6×6 grid / mesh型。
- 内部gridノード：36個。
- 外周ODノード：24個。
- 合計：60ノード / 168リンク。
- 全Linkで `number_of_lanes=1`。
- 全Linkで `merge_priority=1`。
- 内部リンクおよびOD接続リンクは双方向。
- 外周ODノードは発着点として信号なし。
- destination外周ノードで不要な信号待ちが発生しないようにした。

需要：

- Step 4Bと同一需要。
- Vehicle数：1000。
- departure：0〜500。
- demand duration：500。
- vehicles per timestep：2.0。
- OD Manhattan distance：min 5、average 約6.73、max 10。
- `vehicle_plans` はsignalized標準ケースとFCFSケースで完全共通。
- 固定routeは指定せず、ODのみ指定。

FCFS対象：

- eligible node：36個。
- 全内部gridノード `g_0_0`〜`g_5_5` がFCFS対象。
- `clearance_timesteps=0`。
- FCFSケースでは内部gridノードに信号を設定しない。信号なし + FCFSとして実行。

比較結果：

- Signalized UXsim standard：
  - completed trips：1000 / 1000
  - completed ratio：1.000
  - total travel time：335835.0 s
  - average travel time：335.8 s
  - average delay：171.2 s
  - delay ratio：0.510
  - total distance：3498400.0 m
- FCFS(clearance=0)：
  - completed trips：1000 / 1000
  - completed ratio：1.000
  - total travel time：167772.0 s
  - average travel time：167.8 s
  - average delay：3.2 s
  - delay ratio：0.019
  - total distance：3292000.0 m

Comparison ratios：

- completed ratio difference：0.000
- average travel time ratio：0.500
- total travel time ratio：0.500
- total distance traveled ratio：0.941

解釈：

- Signalized UXsim standard は FCFS(clearance=0) より平均旅行時間が約2倍長い。
- これは `signal=[60,60]` の固定2相信号により信号待ちが大きく生じたためと考えられる。
- FCFS(clearance=0)は信号待ちを持たず、到着順ベースで通過するため、このネットワーク・需要では大幅に短い旅行時間となった。
- 完了台数は両ケースとも1000/1000で同一。
- 総走行距離は signalized標準の方がやや長い（3498400.0 m vs 3292000.0 m、ratio 0.941）。
- grid型で経路選択・混雑回避が働いた結果、両ケースで経路選択が異なった可能性がある。
- 極端な破綻は検出されなかった。
- ただし、この結果から「FCFSが常に信号制御より優れる」とは結論しない。
- あくまで固定2相信号 `[60,60]` を用いたsignalized UXsim standardとのsanity checkである。

#### Step 4D：高需要grid型 signalized UXsim標準 vs clearance-zero FCFS

実施コミット：

- 1ef9f9a phase 4-5: add high-demand grid clearance-zero FCFS vs signalized UXsim sanity test

新規追加ファイル：

- `tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py`

概要：

- Step 4Dでは、Step 4Cと同じ6×6 grid / mesh型ネットワークを用いた。
- Step 4Cでは1000台を0〜500 timestepで投入したが、Step 4Dでは高需要条件として5000台・10000台を同じ0〜500 timestepに投入した。
- 比較対象は signalized UXsim standard と FCFS(clearance=0)。
- signalized UXsim standard は、内部gridノード36個に `signal=[60,60]` を設定した固定2相信号。
- phase 0 は東西方向、phase 1 は南北方向。
- 外周ODノード24個には信号を設定していない。
- FCFSケースでは、内部gridノードを信号なしとし、eligible node全体をFCFS対象にした。
- FCFSケースの `clearance_timesteps=0`。
- 全Linkで `number_of_lanes=1`。
- 全Linkで `merge_priority=1`。
- `merge_priority` は両ケースで同じLink属性として設定しているが、FCFSの通過順序は `merge_priority` ではなく `(arrival_time, tiebreaker, veh.id)` に基づく想定である。
- 目的は、高需要時に固定2相信号 `[60,60]` が相対的に有利になる可能性を確認すること、およびFCFS(clearance=0)が高需要時にも極端に破綻しないことを確認すること。
- これは研究上の性能評価ではなく、sanity checkである。

high_demand_cases：

- Case 1：
  - num_vehicles：5000
  - departure_start：0
  - departure_end：500
  - tmax：30000
  - vehicles per timestep：10.0
- Case 2：
  - num_vehicles：10000
  - departure_start：0
  - departure_end：500
  - tmax：50000
  - vehicles per timestep：20.0

補足：

- Step 4Cは1000台を0〜500 timestepに投入していたため、需要密度は2.0 veh/timestep。
- Step 4Dでは、Step 4Cに対して5倍・10倍の需要密度を試した。

ネットワーク・制御設定：

- 6×6内部grid。
- 内部gridノード：36個。
- 外周ODノード：24個。
- 合計：60ノード。
- 内部双方向リンク：120本。
- 外周OD接続双方向リンク：48本。
- 合計：168リンク。
- 全Linkで `number_of_lanes=1`。
- 全Linkで `merge_priority=1`。
- `origin_grid_coord` / `destination_grid_coord` は、外周ODノードが接続する内部gridノードの座標であり、OD距離判定用メタデータとして使用。

signalized UXsim standard：

- 内部gridノード36個すべてに `signal=[60,60]`。
- phase 0：東西方向。
- phase 1：南北方向。
- signal_group 0：東西リンク、水平内部リンク、left/right接続。
- signal_group 1：南北リンク、垂直内部リンク、top/bottom接続。
- 外周ODノードには信号を設定しない。
- signalized OD node count：0。
- signal offset：全内部gridで0。

FCFS(clearance=0)：

- 内部gridノード・外周ODノードとも信号なし。
- `W.infer_order_control_eligible_nodes()` によりeligible nodeを取得。
- eligible nodeは36個。
- 全内部gridノード `g_0_0`〜`g_5_5` がFCFS対象。
- `W.set_order_control_clearance_timesteps(0)`。
- `W.set_order_control_for_nodes(..., order_control_type="fcfs")`。

Case 1：5000台の結果

- 5000台、departure 0〜500、tmax 30000、vehicles per timestep 10.0。
- OD Manhattan distance：min 5、average 約6.7296、max 10。

Signalized UXsim standard：

- completed trips：5000 / 5000
- completed ratio：1.000
- unfinished vehicles：0
- unfinished ratio：0.000
- total travel time：7164538.0 s
- average travel time：1432.9 s
- average delay：約1268.3 s
- delay ratio：0.885
- total distance：23185600.0 m
- last completed trip time：3449.0 s
- max completed travel time：3154.0 s
- last completed trip time / tmax：0.115

FCFS(clearance=0)：

- completed trips：5000 / 5000
- completed ratio：1.000
- unfinished vehicles：0
- unfinished ratio：0.000
- total travel time：4160694.0 s
- average travel time：832.1 s
- average delay：約667.5 s
- delay ratio：0.802
- total distance：18959200.0 m
- last completed trip time：1928.0 s
- max completed travel time：1705.0 s
- last completed trip time / tmax：0.064

Comparison ratios（FCFS / signalized）：

- completed ratio difference：0.000
- average travel time ratio：0.581
- total travel time ratio：0.581
- total distance traveled ratio：0.818

解釈：

- 5000台ケースでは、FCFS(clearance=0)の平均旅行時間はsignalized UXsim standardの約58.1%。
- signalized standardもFCFSも全車完了。
- 未完了車両は両ケースとも0。
- tmaxには十分余裕がある。
- 高需要化により、Step 4Cの1000台ケースよりもsignalized standardが相対的に改善する傾向が見えたが、依然としてFCFSの方が短い旅行時間だった。

Case 2：10000台の結果

- 10000台、departure 0〜500、tmax 50000、vehicles per timestep 20.0。
- OD Manhattan distance：min 5、average 約6.7448、max 10。

Signalized UXsim standard：

- completed trips：10000 / 10000
- completed ratio：1.000
- unfinished vehicles：0
- unfinished ratio：0.000
- total travel time：27065593.0 s
- average travel time：2706.6 s
- average delay：約2541.7 s
- delay ratio：0.939
- total distance：47784800.0 m
- last completed trip time：5828.0 s
- max completed travel time：5451.0 s
- last completed trip time / tmax：0.117

FCFS(clearance=0)：

- completed trips：10000 / 10000
- completed ratio：1.000
- unfinished vehicles：0
- unfinished ratio：0.000
- total travel time：17989241.0 s
- average travel time：1798.9 s
- average delay：約1634.0 s
- delay ratio：0.908
- total distance：41086400.0 m
- last completed trip time：3766.0 s
- max completed travel time：3593.0 s
- last completed trip time / tmax：0.075

Comparison ratios（FCFS / signalized）：

- completed ratio difference：0.000
- average travel time ratio：0.665
- total travel time ratio：0.665
- total distance traveled ratio：0.860

解釈：

- 10000台ケースでは、FCFS(clearance=0)の平均旅行時間はsignalized UXsim standardの約66.5%。
- signalized standardもFCFSも全車完了。
- 未完了車両は両ケースとも0。
- tmaxには十分余裕がある。
- 5000台ケースよりもさらにsignalized standardが相対的に改善したが、今回の範囲では依然としてFCFSの方が短い旅行時間だった。

Step 4C / Step 4D の比較（平均旅行時間 ratio、FCFS / signalized）：

- Step 4C：1000台、2.0 veh/timestep、ratio 約0.500
- Step 4D Case 1：5000台、10.0 veh/timestep、ratio 約0.581
- Step 4D Case 2：10000台、20.0 veh/timestep、ratio 約0.665

解釈：

- 需要を5倍・10倍にすると、signalized UXsim standardとFCFS(clearance=0)の差は縮小した。
- これは、固定2相信号 `[60,60]` が高需要時に相対的に改善する可能性を示している。
- ただし、今回の範囲では依然としてFCFS(clearance=0)の方が短い旅行時間だった。
- この結果から、FCFSが常に信号制御より優れるとは結論しない。
- あくまで同一ネットワーク・同一需要生成条件・固定2相信号 `[60,60]` におけるsanity check結果である。
- 本格的には、さらに高需要、信号offset、サイクル長、需要分布、ネットワークサイズなどを変えた体系的検証が必要。

#### Step 4E：高需要grid型 signalized all-red UXsim標準 vs clearance-one FCFS

実施コミット：

- af11393 phase 4-5: add high-demand grid clearance-one FCFS vs signalized all-red UXsim sanity test

新規追加ファイル：

- `tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand.py`

概要：

- Step 4Eでは、Step 4Dと同じ6×6 grid / mesh型ネットワークを用いた。
- Step 4Dは FCFS(clearance=0) と signalized UXsim standard の高需要比較だった。
- Step 4Eでは、FCFS側を `clearance_timesteps=1` に設定した。
- signalized UXsim standard側にも、方向切替時のクリアランスに相当する全赤フェーズを追加した。
- signalized側の信号設定は `signal=[60, W.DELTAT, 60, W.DELTAT]`。
- 今回の実行では `W.DELTAT=1` だったため、実際の signal setting は `[60, 1, 60, 1]`。
- phase 0：東西方向青。
- phase 1：全赤。
- phase 2：南北方向青。
- phase 3：全赤。
- signal_group=1 および signal_group=3 のリンク数は0。
- これにより、phase 1 / phase 3 は全赤として機能する想定。
- signal_offset は内部gridノードごとに異なる値を設定した。
- signal_offset strategy は `((row + column) % 4) * (cycle_length / 4)`。
- signal offset unique values は `[0.0, 30.5, 61.0, 91.5]`。
- これは全内部gridノードが同時に同じphaseへ切り替わる完全同期信号を避けるための簡易・再現可能なオフセットであり、最適化されたオフセットではない。
- 外周ODノード24個には信号を設定していない。
- FCFSケースでは、内部gridノード・外周ODノードとも信号なし。
- FCFSケースでは `clearance_timesteps=1`。
- eligible node 36個すべてをFCFS対象にした。
- 全Linkで `number_of_lanes=1`。
- 全Linkで `merge_priority=1`。
- `merge_priority` は両ケースで同じLink属性として設定しているが、FCFSの通過順序は `merge_priority` ではなく `(arrival_time, tiebreaker, veh.id)` に基づく想定である。
- 目的は、FCFSの高頻度方向切替に伴うクリアランスロスが入った場合に、高需要gridで signalized all-red とどう比較されるかを確認することである。
- これは研究上の性能評価ではなく、sanity checkである。

high_demand_cases：

- Case 1：5000台、departure 0〜500、tmax 30000、vehicles per timestep 10.0
- Case 2：10000台、departure 0〜500、tmax 50000、vehicles per timestep 20.0

補足：

- Step 4Dと同じ高需要ケース。
- Step 4Dでは FCFS(clearance=0) を用いた。
- Step 4Eでは FCFS(clearance=1) を用いた。
- Step 4Eのsignalized側は、全赤フェーズ付き4相信号である。

ネットワーク・制御設定：

- 6×6内部grid。内部gridノード36個、外周ODノード24個、合計60ノード、168リンク。
- 全Linkで `number_of_lanes=1`、`merge_priority=1`。
- `origin_grid_coord` / `destination_grid_coord` はOD距離判定用メタデータ。

signalized UXsim all-red：

- 内部gridノード36個すべてに `signal=[60, W.DELTAT, 60, W.DELTAT]`。
- 実行時の `W.DELTAT=1` により、実際の signal setting は `[60, 1, 60, 1]`。
- signal cycle length：122。
- phase 0：東西方向青。phase 1：全赤。phase 2：南北方向青。phase 3：全赤。
- signal_group 0：東西リンク、水平内部リンク、left/right接続。
- signal_group 1：未使用。リンク数0。
- signal_group 2：南北リンク、垂直内部リンク、top/bottom接続。
- signal_group 3：未使用。リンク数0。
- 外周ODノードには信号を設定しない。signalized OD node count：0。
- signal_offset strategy：`((row + column) % 4) * (cycle_length / 4)`。
- signal offset unique values：`[0.0, 30.5, 61.0, 91.5]`。

FCFS(clearance=1)：

- 内部gridノード・外周ODノードとも信号なし。
- `W.infer_order_control_eligible_nodes()` によりeligible nodeを取得（36個）。
- 全内部gridノード `g_0_0`〜`g_5_5` がFCFS対象。
- `W.set_order_control_clearance_timesteps(1)`。
- `W.set_order_control_for_nodes(..., order_control_type="fcfs")`。
- FCFS clearance_timesteps は1であることをassert済み。

Case 1：5000台の結果

- OD Manhattan distance：min 5、average 約6.7296、max 10。

Signalized UXsim standard with all-red clearance：

- completed trips：5000 / 5000、completed ratio：1.000
- unfinished vehicles：0、unfinished ratio：0.000
- total travel time：5510114.0 s、average travel time：1102.0 s
- average delay：約937.4 s、delay ratio：0.851
- total distance：20188000.0 m
- last completed trip time：2724.0 s、max completed travel time：2531.0 s
- last completed trip time / tmax：0.091

FCFS(clearance=1)：

- completed trips：5000 / 5000、completed ratio：1.000
- unfinished vehicles：0、unfinished ratio：0.000
- total travel time：7638201.0 s、average travel time：1527.6 s
- average delay：約1363.0 s、delay ratio：0.892
- total distance：19796000.0 m
- last completed trip time：3263.0 s、max completed travel time：3055.0 s
- last completed trip time / tmax：0.109

Comparison ratios（FCFS / signalized all-red）：

- completed ratio difference：0.000
- average travel time ratio：1.386
- total travel time ratio：1.386
- total distance traveled ratio：0.981

解釈：

- 5000台ケースでは、FCFS(clearance=1)の平均旅行時間はsignalized all-redの約1.386倍。
- signalized all-red の方が短い旅行時間だった。
- 両ケースとも全車完了、未完了車両0、tmaxに十分余裕。
- FCFS(clearance=1)では、随時方向切替に伴うクリアランスロスが効いた可能性がある。

Case 2：10000台の結果

- OD Manhattan distance：min 5、average 約6.7448、max 10。

Signalized UXsim standard with all-red clearance：

- completed trips：10000 / 10000、completed ratio：1.000
- unfinished vehicles：0、unfinished ratio：0.000
- total travel time：26989929.0 s、average travel time：2699.0 s
- average delay：約2534.1 s、delay ratio：0.939
- total distance：50367200.0 m
- last completed trip time：5703.0 s、max completed travel time：5415.0 s
- last completed trip time / tmax：0.114

FCFS(clearance=1)：

- completed trips：10000 / 10000、completed ratio：1.000
- unfinished vehicles：0、unfinished ratio：0.000
- total travel time：30822256.0 s、average travel time：3082.2 s
- average delay：約2917.3 s、delay ratio：0.947
- total distance：38087200.0 m
- last completed trip time：5915.0 s、max completed travel time：5619.0 s
- last completed trip time / tmax：0.118

Comparison ratios（FCFS / signalized all-red）：

- completed ratio difference：0.000
- average travel time ratio：1.142
- total travel time ratio：1.142
- total distance traveled ratio：0.756

解釈：

- 10000台ケースでは、FCFS(clearance=1)の平均旅行時間はsignalized all-redの約1.142倍。
- signalized all-red の方が短い旅行時間だった。
- 両ケースとも全車完了、未完了車両0、tmaxに十分余裕。
- 5000台ケースよりも差は縮小したが、今回の範囲ではsignalized all-redの方が短い旅行時間だった。

Step 4D / Step 4E の対比：

Step 4D：

- FCFS(clearance=0)、signalized UXsim standard（固定2相 `[60,60]`）
- 5000台：FCFS / signalized average travel time ratio 約0.581
- 10000台：FCFS / signalized average travel time ratio 約0.665
- clearance=0 ではFCFSの方が短い旅行時間だった。

Step 4E：

- FCFS(clearance=1)、signalized UXsim all-red（4相 `[60,1,60,1]`、staggered offset）
- 5000台：FCFS / signalized all-red average travel time ratio 約1.386
- 10000台：FCFS / signalized all-red average travel time ratio 約1.142
- clearance=1 ではsignalized all-redの方が短い旅行時間だった。

解釈：

- clearance=0 ではFCFSが有利に見えた。
- clearance=1 にすると、FCFSの高頻度方向切替コストが効き、signalized all-redが有利になるケースが確認された。
- これは、FCFSの性能がclearance設定に強く依存する可能性を示す重要なsanity check結果である。
- ただし、これは特定のgrid network、需要生成、信号設定、オフセット戦略における観察であり、一般結論ではない。
- 今後は clearance_timesteps、signal cycle、signal offset、需要密度、ネットワークサイズを体系的に変える必要がある。

#### 比較結果の解釈

- Step 4A〜4Eにより、FCFS(clearance=0/1)は中規模corridor型、grid unsignalized型、grid signalized型（中需要・高需要）のいずれでも、完了台数・総走行距離・旅行時間指標において極端な破綻を示さなかった。
- corridor型（Step 4A、clearance=0）ではFCFSが約4.3%遅かった。
- unsignalized grid型（Step 4B、clearance=0）ではFCFSが約1.1%遅かった。
- signalized grid型（Step 4C：1000台、clearance=0）ではFCFSが約50%の平均旅行時間となり、固定2相信号よりかなり短かった。
- signalized grid型（Step 4D：5000台・10000台、clearance=0）では、高需要化に伴いFCFS/signalized ratioが0.500→0.581→0.665と縮小したが、依然としてFCFSの方が短い旅行時間だった。
- signalized all-red grid型（Step 4E：5000台・10000台、clearance=1）では、FCFS/signalized all-red ratioが約1.386→1.142となり、signalized all-redの方が短い旅行時間だった。
- unsignalized grid型でほぼ同等だったことは、信号がないUXsim標準transferとFCFS(clearance=0)が大きく乖離しないことの確認になる。
- signalized grid型（clearance=0）でFCFSが大幅に短い旅行時間となったことは、固定2相信号の信号待ちが強く効いたためと解釈できる。Step 4Dでは高需要によりこの差は縮小した。
- clearance=0 と clearance=1 で相対関係が逆転し得ることは、FCFS性能がclearance設定に強く依存する可能性を示す。
- ただし、これは研究上の性能評価ではなく、まだ sanity check の段階である。
- 本格的な性能比較には、需要条件、信号設定、オフセット、信号最適化、クリアランス値、ネットワーク構造などを体系的に変えた実験設計が必要。

#### 現在の理解

- FCFS(clearance=0/1)の単体・X/Y/Z問題テストに加え、corridor型・grid unsignalized型・grid signalized型（中需要・高需要）のsanity checkでも極端な破綻は見られなかった。
- unsignalized UXsim standard transfer との比較（clearance=0）では、FCFSはおおむね同等〜やや遅い程度だった。
- signalized UXsim standard（固定2相 `[60,60]`、clearance=0）との比較では、Step 4C/4DでFCFSの方が短い旅行時間だった。これは信号待ちの影響が大きいためであり、性能優位の一般結論ではない。
- signalized all-red UXsim standard（4相 `[60,1,60,1]`、staggered offset）と FCFS(clearance=1) の高需要比較（Step 4E）では、signalized all-redの方が短い旅行時間だった。
- clearance=0 ではFCFS有利、clearance=1 ではsignalized all-red有利という対比が確認され、FCFS性能はclearance設定に強く依存する可能性がある。
- Step 4A〜4Eはすべて新規テストファイルのみの追加であり、`uxsim/uxsim.py` は変更していない。

#### 実行済みテスト

以下を実行済みで、すべて成功した。

- `python tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand.py`
- `python tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py`
- `python tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_network.py`
- `python tests_order_control_fcfs_vs_uxsim_standard_grid_network.py`
- `python tests_order_control_fcfs_vs_uxsim_standard_medium_network.py`
- `python tests_fcfs_order_control_clearance_xyz.py`
- `python tests_fcfs_order_control_clearance_0.py`
- `python tests_fcfs_order_control_clearance_1.py`
- `python tests_order_control_clearance_settings.py`
- `python tests_fcfs_order_control_transfer.py`
- `python tests_fcfs_order_control_behavior.py`
- `python tests_fcfs_order_control_tiebreaker.py`
- `python tests_order_control_node_arrival_times.py`
- `python tests_vehicle_research_attributes.py`
- `python tests_order_exchange_baseline.py`
- `python demos_and_examples/example_00en_simple.py`

baseline主要交通結果：

- completed trips：48 / 48
- total travel time：2928.0 s
- average travel time：61.0 s
- delay ratio：0.017
- total distance：48000.0 m

`example_00en_simple.py` 主要交通結果：

- completed trips：735 / 810
- total travel time：119475.0 s
- average travel time：162.6 s
- delay ratio：0.385
- total distance：1632250.0 m

#### 関連コミット

- 683f560 phase 4-5: add corridor FCFS vs UXsim standard sanity test
- 492f33e phase 4-5: add grid FCFS vs unsignalized UXsim standard sanity test
- c810e2b phase 4-5: add grid FCFS vs signalized UXsim standard sanity test
- 1ef9f9a phase 4-5: add high-demand grid clearance-zero FCFS vs signalized UXsim sanity test
- af11393 phase 4-5: add high-demand grid clearance-one FCFS vs signalized all-red UXsim sanity test

これらは origin/feature/intersection-order-control に push 済みである。

#### 後続事項

- Step 4D/4Eの結果を踏まえた簡易分析メモの作成。
- clearance_timesteps=0/1比較の整理。
- signal offset戦略を変えた比較。
- signal cycleや全赤時間を変えた比較。
- demand densityやnetwork sizeを変えた比較。
- signalized UXsim standard と FCFS の比較条件をより体系化した実験設計。
- Batch Processing、Time-value Transaction、支払い処理は引き続き未実装。

### フェーズ4-6設計：BATCH Processing正式設計メモの追加

完了済み。

#### 位置づけ

- phase 4-6として、BATCH Processing実装前の正式設計メモを追加した。
- 今回は設計メモ作成のみであり、BATCH実装本体はまだ行っていない。

#### 追加したファイル

- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md`
  - phase 4-6：交差点BATCH処理の実装前正式設計メモ

#### 設計メモに含めた主な内容

- UXsim-adapted BATCHの位置づけ
- `earliest_arrival_timestep` の定義と計算式
- `t_trigger` と Level 0 / 1 / 2 の位置づけ
- BATCH候補集合、inlink方向別batch化、Nの定義
- residual batch、service unit、unresolved
- Time-value Transactionへの接続方針
- テスト方針、未解決事項

#### 関連コミット

- bb23372 phase 4-6: add batch processing design notes

#### 一時退避PDFメモの位置づけ

- チャット上限到達時に、phase 4-6A作業内容を一時退避用として `phase4-6A_batch_earliest_arrival_timestep_memo.pdf` を作成した。
- このPDFはUXsimリポジトリ外（Macデスクトップ）に保存されている。
- 今後の作業再開時は、更新済みの正式Markdown（本メモおよび `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md`）を優先して参照する。
- PDFは背景資料・一時退避用であり、リポジトリ内の正式記録ではない。

### フェーズ4-6A：earliest_arrival_timestep記録

完了済み。

#### 位置づけ

- BATCH形成そのものではなく、BATCH形成の基礎データとなる `earliest_arrival_timestep` の記録機能を実装した。
- 交通挙動は変更していない（記録処理の追加のみ）。

#### 実装内容

Vehicleに追加した属性：

- `order_control_earliest_arrival_timesteps = {}`
  - key：下流Nodeの `node.name`
  - value：timestep単位の `earliest_arrival_timestep`

Worldに追加した設定：

- `W.order_control_batch_tau_timesteps = 1`（初期値）
- `set_order_control_batch_tau_timesteps(tau_timesteps)`
  - intのみ許可、bool不可、0以上、不正値はValueError

Vehicleに追加したメソッド：

- `record_order_control_earliest_arrival_timestep_for_current_link()`

記録タイミング（いずれも `veh.link` 設定と `veh.link_arrival_time` 更新の直後）：

- origin `generation_queue` から最初のoutlinkへ実際に投入されたとき
- 標準 `Node.transfer` で次Linkへ移ったとき
- `transfer_fcfs_no_clearance` で次Linkへ移ったとき
- `transfer_fcfs_clearance` で次Linkへ移ったとき

記録しないタイミング：

- `addVehicle()` 直後
- `generation_queue` 待機中
- destination到着後の新規記録

計算式：

```
free_flow_travel_timesteps = ceil((link.length / link.u) / W.DELTAT)
link_entry_timestep = int(round(veh.link_arrival_time / W.DELTAT))
earliest_arrival_timestep = link_entry_timestep + free_flow_travel_timesteps + tau_timesteps
```

#### 今回あえて実装していないこと

- BATCH形成、trigger vehicle処理、candidate set形成
- service unit処理、residual batch
- `Node.transfer()` のbatch分岐
- Time-value Transaction本体

#### 追加テスト

- `tests_order_control_batch_earliest_arrival_timestep.py`

#### 関連コミット

- 94b05f2 phase 4-6: record batch earliest arrival timesteps

### フェーズ4-6B：BATCH状態コンテナの追加

完了済み。

#### 位置づけ

- BATCH Processing用の最小状態管理コンテナのみを追加した。
- 初期化のみであり、値の書き込み・交通挙動への接続は行っていない。

#### 実装内容

Vehicleに追加：

- `order_control_batch_assignments = {}`
  - key：`node.name`、value：そのNodeで将来割り当てられる `batch_id`
  - 対象Node名のkeyが存在しない場合、そのNodeでは未batch
  - 別Nodeでのみbatch化済みでも、対象Node名のkeyがなければ対象Nodeでは未batch

Nodeに追加：

- `order_control_batch_service_queue = deque()`（将来のservice unit処理順キュー）
- `order_control_batch_next_id = 0`（将来のbatch_id発行カウンタ）
- いずれも初期化のみ。queueへの追加・next_idの増加は行わない

#### 追加テスト

- `tests_order_control_batch_state_containers.py`

#### 関連コミット

- 28ed156 phase 4-6: add batch state containers

### フェーズ4-6C：BATCH trigger候補Vehicle識別ヘルパー

完了済み。

#### 位置づけ

- BATCH trigger候補Vehicleを決定的な順序で返す参照専用ヘルパーを追加した。
- trigger確定・保存、BATCH形成、service queue追加にはまだ接続していない。

#### 実装内容

追加メソッド：

- `Node.get_order_control_batch_trigger_candidates()`

対象Node条件（両方を満たす場合のみ候補抽出、それ以外は `[]` を返す）：

- `order_control_eligible is True`
- `order_control_type == "batch"`

Vehicle候補条件：

- `incoming_vehicles` に含まれる
- `route_next_link is not None`
- 対象Node名が `order_control_node_arrival_times` に存在
- 対象Node名が `order_control_node_arrival_tiebreakers` に存在
- 対象Node名が `order_control_batch_assignments` に**存在しない**（Node別判定）

候補順（FCFSと同じ）：

```
(arrival_time, tiebreaker, veh.id)
```

重要事項：

- 候補抽出メソッドは新しい乱数を生成しない
- `incoming_vehicles` をin-placeでsortしない（sorted済み新listを返す）
- 候補listの各Vehicleはすでに `incoming_vehicles` に入っており、Node端へ到着済みである
- BATCH形成処理を実行する時点では、返却listの先頭Vehicleを現在のBATCH形成を起動するtrigger vehicleとして使用する想定である
- ただし phase 4-6C の現段階では、trigger vehicleの確定・保存およびBATCH形成処理には未接続である
- 参照専用、副作用なし

#### 追加テスト

- `tests_order_control_batch_trigger_candidates.py`

#### 関連コミット

- 40d5ad7 phase 4-6: add batch trigger candidate helper

### フェーズ4-6D：t_trigger推定（Level 0 / Level 1）

完了済み。

#### 位置づけ

- trigger vehicleの予定通過タイムステップ `t_trigger` を推定するLevel 0 / Level 1の参照専用ヘルパーを追加した。
- BATCH形成、batch_id発行、service queue追加、`Node.transfer()` batch分岐にはまだ接続していない（**4-6M（§1F）で `Node.transfer()` 接続済み**）。

#### 実装内容

内部ヘルパー：

- `_validate_order_control_batch_t_trigger_inputs()`
- `_compute_order_control_batch_base_trigger_timestep()`

公開メソッド：

- `estimate_order_control_batch_t_trigger_level_0(trigger_vehicle)`
- `estimate_order_control_batch_t_trigger_level_1(trigger_vehicle)`

`t_trigger` の単位はtimestep。計算式に `W.T` は使用しない。

Level 0：

```
arrival_timestep = int(round(arrival_time_seconds / W.DELTAT))
first_transfer_timestep = arrival_timestep + 1
t_trigger = max(first_transfer_timestep, trigger_earliest_arrival_timestep)
```

Level 1：

- 上記 `base_trigger_timestep` を計算後、既存clearance状態を参照
- 直前通過なし、または同一inlink：`t_trigger = base_trigger_timestep`
- 異inlink：`t_trigger = max(base_trigger_timestep, last_entry + clearance + 1)`
- 不整合時はValueError（Level 0へ自動fallbackしない）
- 推定結果はNode/Vehicleへ保存しない

#### 追加テスト

- `tests_order_control_batch_t_trigger_estimation.py`（テスト関数21件）

#### 関連コミット

- d79db61 phase 4-6: add batch t_trigger estimators

### フェーズ4-6A〜4-6J：回帰確認

各実装後、以下のテストおよびサンプルがPASSしたことを確認済み。

BATCH関連：

- `tests_order_control_batch_earliest_arrival_timestep.py`
- `tests_order_control_batch_state_containers.py`
- `tests_order_control_batch_trigger_candidates.py`
- `tests_order_control_batch_t_trigger_estimation.py`
- `tests_order_control_batch_candidates_by_inlink.py`
- `tests_order_control_batch_candidate_group_ordering.py`
- `tests_order_control_batch_max_size_application.py`
- `tests_order_control_batch_service_unit_registration.py`
- `tests_order_control_batch_formation_integration.py`
- `tests_order_control_batch_node_settings.py`

FCFS / clearance関連：

- `tests_fcfs_order_control_clearance_0.py`
- `tests_fcfs_order_control_clearance_1.py`
- `tests_fcfs_order_control_clearance_xyz.py`
- `tests_fcfs_order_control_transfer.py`
- `tests_fcfs_order_control_behavior.py`
- `tests_fcfs_order_control_tiebreaker.py`
- `tests_order_control_node_arrival_times.py`
- `tests_order_control_clearance_settings.py`

baseline / example：

- `tests_order_exchange_baseline.py`
- `demos_and_examples/example_00en_simple.py`

主要交通結果（Phase 4-6A〜4-6J実装後も既知値と一致し、確認対象の主要指標に回帰は検出されなかった）：

`tests_order_exchange_baseline.py`：

- completed trips：48 / 48
- average speed：16.5 m/s
- total travel time：2928.0 s
- average travel time：61.0 s
- average delay：1.0 s
- delay ratio：0.017
- total distance traveled：48000.0 m

`demos_and_examples/example_00en_simple.py`：

- completed trips：735 / 810
- average speed：11.7 m/s
- total travel time：119475.0 s
- average travel time：162.6 s
- average delay：62.6 s
- delay ratio：0.385
- total distance traveled：1632250.0 m

### フェーズ4-6K：service queueに基づくVehicle実通過

#### 実装内容

- `Node.serve_order_control_batch_service_queue(s) -> int` を追加
- 登録済み `order_control_batch_service_queue` に従い、Vehicleをinlinkからoutlinkへ実際に移動
- BATCH形成（`form_order_control_batch()`）とは責任分離。本メソッドは新規BATCHを形成しない
- 戻り値は今回の呼出しでLink間遷移を完了したVehicleオブジェクト数（`W.DELTAN` を掛けた交通量ではない）
- Link間遷移は `transfer_fcfs_clearance()` と同じ処理を使用
- **`Node.transfer()` へは未接続**（Phase 4-6K時点の意図的な範囲外。**4-6M（§1F）で接続済み**）

- Vehicleごとの判断順：到着済み → clearance → 下流空間・各容量条件 → 通過
- 未到着・clearance未充足：後続service unitを確認せず、そのtimestepの処理全体を終了
- 0台通過時の通過不能：同inlink後続service unitはスキップ、異inlink後続service unitを確認
- 1台以上通過後：同一inlinkのみ処理。途中通過不能または異inlink到達で終了
- 作業用list（`service_units_to_check`）と正式service queueの使い分け
- residual部分は元service unit内にFIFO保持。未完了service unitは正式queueの元順序を維持（最後尾へ移動しない）
- 完了service unitは途中終了時も正式queueから削除

#### 追加テスト

- `tests_order_control_batch_service_queue_transfer.py`（テスト関数33件、`TESTS` 登録33件）
- 結果：`Order-control batch service-queue transfer tests passed.`

#### 回帰確認（Phase 4-6K実装後）

新規Phase 4-6Kテスト1本（テスト関数33件）、指定既存回帰テスト19本、example 1本がすべて exit code 0。baseline・exampleの主要交通結果は従来の既知値と一致（確認対象の主要指標に回帰は検出されなかった）。

`tests_order_exchange_baseline.py`：completed trips 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、delay ratio 0.017、total distance traveled 48000.0 m

`demos_and_examples/example_00en_simple.py`：completed trips 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、delay ratio 0.385、total distance traveled 1632250.0 m

#### コミット状況

- Phase 4-6Kの実装・テストは commit `12e8eae` 済み

### フェーズ4-6L：BATCH形成・実通過の統括メソッド

#### 実装内容

- `Node.transfer_batch(s) -> dict` を追加
- `form_order_control_batch()` を必ず1回呼び、続けて `serve_order_control_batch_service_queue()` を必ず1回呼ぶ統括メソッド
- 形成処理の中身や実通過処理の中身は再実装しない
- 呼出し引数：`t_trigger_level=s.order_control_batch_t_trigger_level`、`max_batch_size=s.batch_size`（Node属性から取得。`transfer_batch()` の引数ではない）
- 形成結果にかかわらず実通過処理へ進む（`"no_trigger_candidate"` でも既存service queueから通過し得る）
- 形成と実通過の**両方が正常終了した場合だけ** `incoming_vehicles = []`
- 形成時または実通過時に例外が発生した場合、`incoming_vehicles` は維持し、元の例外をそのまま伝播（`finally` による無条件clearなし）
- 戻り値：

```python
{
    "formation_result": formation_result,
    "transferred_vehicle_count": transferred_vehicle_count,
}
```

- `formation_result`：`"batch_formed"` または `"no_trigger_candidate"`
- `transferred_vehicle_count`：今回の呼出しでLink間遷移を完了したVehicleオブジェクト数を表すint。`W.DELTAN` を掛けた交通量ではない。

- **`Node.transfer()` へは未接続**（Phase 4-6L時点の意図的な範囲外。**4-6M（§1F）で接続済み**）

| メソッド | 責任 |
|----------|------|
| `form_order_control_batch()` | trigger候補取得〜service unit登録 |
| `serve_order_control_batch_service_queue()` | service queueに基づくVehicle実通過 |
| `transfer_batch()` | 上記2つを順に各1回呼び、正常終了後の `incoming_vehicles` 整理と結果返却 |

#### 時系列（単体テストで確認済み）

- UXsimでは `Node.transfer()` が `Vehicle.update()` より先に実行される
- timestep TにNode端へ到着するVehicleは、timestep Tの `Vehicle.update()` で同じNodeの `incoming_vehicles` へ登録される
- 最初の形成・通過判定は timestep T+1 の `transfer_batch()` 呼出し内（`first_transfer_timestep = arrival_timestep + 1`）
- 形成直後に同じ呼出し内で実通過判定を行い、余分な1 timestep待ちを避ける

#### 追加テスト

- `tests_order_control_batch_transfer.py`（テスト関数17件、`TESTS` 登録17件）
- 結果：`Order-control batch transfer tests passed.`

#### 回帰確認（Phase 4-6L実装後）

新規Phase 4-6Lテスト1本（テスト関数17件）、`tests_order_control_batch_service_queue_transfer.py`、`tests_order_control_batch_formation_integration.py`、`tests_order_control_batch_t_trigger_estimation.py`、`tests_order_exchange_baseline.py`、`example_00en_simple.py` がすべて exit code 0。baseline・exampleの主要交通結果は従来の既知値と一致（確認対象の主要指標に回帰は検出されなかった）。

`tests_order_exchange_baseline.py`：completed trips 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、delay ratio 0.017、total distance traveled 48000.0 m

`demos_and_examples/example_00en_simple.py`：completed trips 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、delay ratio 0.385、total distance traveled 1632250.0 m

#### コミット状況

- Phase 4-6Lの実装・テストは commit `e9f3ce9` 済み

### フェーズ4-6M：Node.transfer()へのBATCH分岐接続

#### 実装内容

- `Node.transfer()` 冒頭へBATCH分岐4行を追加（**本番コード変更はこの4行のみ**）

```python
if s.order_control_eligible and s.order_control_type == "batch":
    s.transfer_batch()
    return
```

- 分岐条件：`order_control_eligible` が True **かつ** `order_control_type == "batch"`（`order_control_type` だけでは分岐しない）
- 既存FCFS分岐の直後、標準UXsim transferの直前に配置
- `transfer_batch()` を1回呼び、直後に `return`（`return s.transfer_batch()` にはしない。`Node.transfer()` の戻り値は従来どおり `None`）
- FCFS分岐・標準UXsim transferの本体は変更していない
- `transfer_batch()` および配下の形成・実通過メソッドは変更していない

#### 分岐後にreturnする理由

`transfer_batch()` の後に `return` しない場合、同一Node・同一timestepでBATCH処理と標準UXsim transferの両方が実行されるおそれがある。同一timestepにBATCHと標準方式の両方でVehicleを移動させないため、`transfer_batch()` 呼出し後に `Node.transfer()` を終了する。

#### 実シミュレーション時系列（確認済み）

`World.exec_simulation()` では `Node.transfer()` が `Vehicle.update()` より先に実行される。

- timestep Tの `Node.transfer()`：VehicleはまだNode端への到着登録前 → BATCH形成されない
- timestep Tの `Vehicle.update()`：VehicleがNode端へ到着し、同じNodeの `incoming_vehicles` へ登録
- timestep T+1の `Node.transfer()`：BATCH分岐から `transfer_batch()` を呼び、形成・実通過可否確認・条件充足時は同timestepにLink間移動

`first_transfer_timestep = arrival_timestep + 1` と整合。

#### Vehicle引継ぎ（確認済み）

**batch assignment済みVehicle（Node端に残る場合）：**

- 下流空間・各容量条件により通過不能：BATCH形成済み、inlink上に残る、次timestepに既存service unitのFIFO先頭として再確認、新batch IDなし
- clearance未充足で通過しなかったbatch assignment済みVehicle：B1自身について異方向切替clearanceを確認し、clearance未充足で当該timestepの処理を終了。B1のassignmentと未完了service unitを維持し、`Vehicle.update()` で再登録。clearance充足後のtimestep 12で通過。新batch IDやservice unit重複登録なし
- service unit内の未到着Vehicleはもともと `incoming_vehicles` に存在しない（再登録対象ではない）

**到着済み・未batch Vehicle（今回のservice unitへ未登録）：**

- t_trigger候補範囲外、方向別N超過、trigger方向N到達による形成打切り（他方向）
- 共通：`transfer_batch()` 正常終了時に `incoming_vehicles` から削除 → 同timestep末の `Vehicle.update()` で再登録 → 次timestepのtrigger候補になり得る

#### 異方向同時到着・Level 0/Level 1（確認済み）

**3方向同時到着（batch_size=1、tiebreaker A1→B1→C1）：** A1がtrigger、1回の `Node.transfer()` で形成1回、A1のみ登録、B1・C1は形成打切りで未batch。

**A1・B1 2方向シナリオ（batch_size=1、clearance_timesteps=1）：**

| 項目 | 値 |
|------|-----|
| A1・B1のNode初回到着timestep | 10 |
| A1の形成・実通過timestep | 11 |
| B1のLevel 0 t_trigger | 11 |
| A1通過後のclearance下限 | 13 |
| B1のLevel 1 t_trigger | 13 |

#### N=1 BATCHとclearance付きFCFSの完全一致（確認済み）

- BATCH：`batch_size=1`、`order_control_batch_t_trigger_level=1`
- FCFS：`order_control_type="fcfs"`
- 共通：同一ネットワーク・OD（A1/B1/A2/B2/A3/B3、departure 0/20/40）・seed・clearance=1・容量・経路
- Vehicle単位（全6台）：Node初回到着時刻、outlink初回進入timestep、進入順序、通過inlink順序、trip終了timestep — **完全一致**
- 全6台のoutlink進入・trip終了記録の存在、全6台のtrip完了を明示確認（偽陽性防止）
- Node状態履歴（Link名で比較）、方向切替回数、clearance待機（少なくとも1回）— **一致**
- 集計値：completed trips、total/average travel time — **一致**
- total distanceはN=1比較から除外（誤った `travel_time * 20` 推定は使用しない）
- **最初の不一致なし**

#### 追加テスト

- `tests_order_control_batch_node_transfer_integration.py`（テスト関数13件、`TESTS` 登録13件）
- 結果：`Order-control batch Node.transfer integration tests passed.`

テスト範囲：BATCH/FCFS/標準UXsim分岐、実シミュレーション時系列、容量不足による再登録、clearance未充足Vehicleの再登録とclearance充足後の通過、未batch Vehicle引継ぎ（3分類）、3方向同時到着、Level 0/Level 1 t_trigger、N=1 BATCH・FCFS完全一致。

#### 回帰確認（Phase 4-6M実装後）

新規Phase 4-6Mテスト1本（13テスト関数）、指定既存回帰テスト21ファイル、example 1本がすべて exit code 0。N=1比較テストのレビュー修正後も、新規テスト・主要回帰テスト・baseline・exampleを再実行し成功。主要交通結果は従来の既知値と一致（確認対象の主要指標に回帰は検出されなかった）。

`tests_order_exchange_baseline.py`：completed trips 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、delay ratio 0.017、total distance traveled 48000.0 m

`demos_and_examples/example_00en_simple.py`：completed trips 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、delay ratio 0.385、total distance traveled 1632250.0 m

#### コミット状況

- Phase 4-6Mの実装・テストは commit `b03538c` 済み
- Phase 4-6Nのroute_next_link参照順修正は commit `05fa2d1` 済み
- Phase 4-6Nのclearance=0比較テスト3本は commit `f339b88` 済み
- Phase 4-6Nの比較・Node再訪診断の正式記録は commit `c06936c` 済み
- Phase 4-6Nの診断スクリプト分離は commit `0e35799` 済み
- **最新実装commit：** `b7159f9`（Phase 4-6T 小規模BATCH再訪end-to-end統合）
- Phase 4-6N Step 5：Node訪問単位の共通状態設計を設計メモ **§1H** に記録済み
- Phase 4-6O：commit `e3243e7` で完了（設計メモ **§1H.18**）
- Phase 4-6P：commit `b1b4d7f`（Step 1）・`b051c58`（Step 2）で完了（設計メモ **§1H.19**）
- Phase 4-6Q：commit `7c3c6d3`（Step 1）・`9100803`（Step 2）で完了（設計メモ **§1H.20**）
- Phase 4-6R：commit `cdd19be`（Step 1）・`30588a0`（Step 2）・`ae57e40`（Step 3）で完了（設計メモ **§1H.21**）
- Phase 4-6S：commit `5e26bc9` で完了（設計メモ **§1H.22**）
- Phase 4-6T：commit `b7159f9` で完了（設計メモ **§1H.23**）
- Phase 4-6U：high-demand再実行・検証完了（設計メモ **§1H.24**。本体変更なし。結果は設計メモ§1H.24に記録する）
- **最新実装commit：** `b7159f9`
- **直前の文書commit（Phase 4-6T）：** `aca6ce9`
- **次工程候補：** trip-end Vehicleとstale service unitの工程位置決定、Level 2、Time-value Transaction等（設計メモ **§1H.17**・**§1H.24**）

詳細設計・判断経緯は ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md **§1F**（接続）、**§1G**（診断）、**§1H**（訪問状態設計）を参照。

### フェーズ4-6N：比較テストとNode再訪状態の診断

#### commit済み作業

**commit `05fa2d1` — route_next_link参照順修正**

- `serve_order_control_batch_service_queue()` で、service unit FIFO先頭Vehicleについて `incoming_vehicles` 確認を `route_next_link` 参照より先に行うよう修正。
- 未到着Vehicleは `route_next_link` 属性をまだ持たない場合がある（正常状態）。AttributeErrorにしない。
- 到着済みで `route_next_link=None` は既存どおり `ValueError`。
- 回帰テスト `test_not_arrived_without_route_next_link_attribute` を追加。

**commit `f339b88` — clearance=0比較テスト3本**

- `tests_order_control_batch_vs_fcfs_vs_uxsim_standard_medium_network.py`
- `tests_order_control_batch_vs_fcfs_vs_uxsim_standard_grid_network.py`
- `tests_order_control_batch_vs_fcfs_vs_signalized_uxsim_standard_grid_network.py`
- 共通：BATCH Level 1（暫定）、N=10、clearance=0。Node再訪状態修正**前**の基準値。

#### Medium network比較結果（commit済みテスト）

- 500 Vehicle、corridor、eligible 10、同一seed。
- UXsim / FCFS / BATCH いずれも completed 383/500。
- BATCH/FCFS average travel time ratio **1.0003**（BATCHがごくわずかに長い）。

#### Unsignalized grid比較結果（commit済みテスト）

- 1000 Vehicle、6×6 grid、eligible 36。
- 全方式 completed 1000/1000。
- BATCH/FCFS average travel time ratio **1.0006**（+0.1 s/veh）。

#### Signalized grid比較結果（commit済みテスト）

- 1000 Vehicle、signal `[60,60]`、FCFS/BATCHはunsignalized gridと同一結果。
- FCFS/signalized ratio ≈ **0.500**、BATCH/FCFS ratio **1.0006**。

#### 診断スクリプトへ分離（clearance=1 high-demand）

- 診断スクリプト：`diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py`（`0e35799` commit済み）
- signalized all-red：`signal=[60, 1, 60, 1]`（phase 0=東西方向が青、phase 1=全赤、phase 2=南北方向が青、phase 3=全赤）、staggered offset
- 5,000台BATCHで prefix violation（`g_5_4`、`h_5_3_4`、`veh_1952`）。10,000台BATCH未実行。
- signalized all-red vs FCFSは再現：5000台 ratio ≈ 1.386、10000台 ≈ 1.142。

#### 診断スクリプトへ分離（clearance=0 high-demand再現）

- 診断スクリプト：`diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py`（`0e35799` commit済み）
- W.T=605で prefix violation（`g_4_1`、`v_5_4_1`、`veh_1619`）。
- **clearance=0でも再現。** clearance=1 queue滞留は必要条件ではない。

#### 診断スクリプトへ分離（batch ID 318 lifecycle）

- 診断スクリプト：`diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py`（`0e35799` commit済み）
- W.T=583：veh_1619がg_4_1を通過、service unit 318は**正常削除**、assignment 318のみ残存。
- W.T=604–605：別inlinkから再接近、prefix violation。
- **service unit誤削除ではない。**

#### 診断スクリプトへ分離（Node再訪）

- 診断スクリプト：`diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py`（`0e35799` commit済み）
- T≤605再接近：signalized 17 / 4207（約0.40%）、FCFS 10 / 4442（約0.23%）、BATCH 12 / 4412（約0.27%）。分母は各方式でT≤605までに1回以上Nodeへ接近したVehicle数（全5,000台ではない）
- 全期間：signalized **42.7%**、FCFS **23.0%** が再訪（BATCHはT=605で停止のため全期間未取得）。
- **Node再訪はBATCH固有ではない。**
- BATCH固有問題は過去assignmentの現在訪問への漏出。
- FCFSも過去到着状態の再利用可能性を検討する必要あり。

#### 根本原因（設計メモ §1G.12）

- `order_control_node_arrival_times`、`order_control_earliest_arrival_timesteps`、`order_control_batch_assignments` 等がNode名keyのみ。
- 訪問単位を区別できず、再訪時に過去状態が現状態として解釈される。
- assignment削除だけでは不十分であり、Node訪問単位の状態設計が必要。
- `visit_id` を用いる現在訪問状態の基盤は Phase 4-6O で実装済み（commit `e3243e7`）。FCFSの参照先変更は Phase 4-6Q で完了（commit `7c3c6d3`・`9100803`）。BATCH形成の参照先変更は Phase 4-6R で完了（commit `cdd19be`・`30588a0`・`ae57e40`）。assignmentの訪問対応は Phase 4-6S で予定（**その後Phase 4-6Sで完了。`5e26bc9`、§1H.22**）。

#### 未完了のhigh-demand BATCH性能比較（Phase 4-6N時点の記録）

- 5,000台・10,000台のBATCH clearance=0/1比較は prefix violationで未完了または未実行。性能結果は取得済みと記載しない。（**その後Phase 4-6Uで5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースを実行・検証完了。§1H.24**。10,000台・clearance=0は未実行）

#### コミット状況

- Phase 4-6Nの実装・比較テスト：`05fa2d1`、`f339b88` commit済み。
- Phase 4-6Nの正式記録：`c06936c` commit済み。
- Phase 4-6Nの診断スクリプト分離：`0e35799` commit済み（`diagnostics/order_control/`）。

### フェーズ4-6N Step 5：Node訪問単位の共通状態設計（設計記録済み）

Phase 4-6N Step 5として、FCFS・BATCH共通のNode訪問単位状態設計を検討し、設計メモ **§1H** に正式記録した。基盤（Phase 4-6O）と到着記録（Phase 4-6P）は実装済み。FCFSの参照先変更は Phase 4-6Q で実装済み。BATCH形成の参照先変更は Phase 4-6R で実装済み。

**要点：**

- `visit_id`：Vehicleごとのorder-control対象Node訪問番号（対象Node向けLink進入時のみ増加。詳細は **§1H.3** および下記4-6O実装前調査）。
- 現在訪問状態：order-control対象Nodeへの訪問のみ1件保持（visit_id、Node、inlink、earliest arrival、到着時刻、tiebreaker、現在assignment）。
- 既存の `order_control_node_arrival_times` 等は**初回分析履歴**として維持（再訪時に上書きしない）。FCFSは Phase 4-6Q で current visit を参照。BATCHは Phase 4-6R で current visit を参照する。
- FCFSは現在訪問状態を参照（4-6Q実装済み）。BATCHの current visit 参照は Phase 4-6R で実装済み。
- service unitへの `visit_id` 保存と、通過時の訪問対応更新は Phase 4-6S で実装予定（**その後Phase 4-6Sで完了。`5e26bc9`、§1H.22**）。
- service unit形式、BATCH履歴構造等の一部は未決定（§1H.16）。
- high-demand BATCH性能比較は未完了（prefix violationで停止または未実行）（**その後Phase 4-6Uで5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースを実行・検証完了。§1H.24**。10,000台・clearance=0は未実行）。

詳細は ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md **§1H** を参照。診断スクリプトは `diagnostics/order_control/README.md` を参照。

### フェーズ4-6O実装前調査（完了）

Phase 4-6O実装前の実コード調査を完了し、設計メモ **§1H** に反映した（後続のフェーズ4-6O実装記録へ続く）。

- `visit_id` はorder-control対象Nodeへの訪問時だけ増加する
- 対象外Nodeへ向かう場合は `order_control_current_visit = None` とし、`order_control_visit_id` は増やさない
- Originから最初に対象外Nodeへ向かう場合は `order_control_visit_id = 0`、`order_control_current_visit = None` を維持する
- 現在訪問状態はVehicle上の辞書（`order_control_current_visit`）とする
- Link進入処理はVehicle共通メソッド `begin_order_control_visit_on_link_entry()` に集約する
- Phase 4-6Oでは既存 `order_control_earliest_arrival_timesteps` の再訪時上書き挙動を維持する
- 初回分析履歴化は Phase 4-6R のBATCH参照先変更と同時に行う

詳細は設計メモ **§1H** を参照。

### フェーズ4-6O：現在訪問状態の共通基盤（実装済み）

Phase 4-6Oとして、FCFS・BATCH共通のNode訪問単位「現在訪問状態」基盤を実装し、専用テスト・回帰確認まで完了した。詳細は設計メモ **§1H.18** を参照。commit `e3243e7`。

**実装要点：**

- Vehicle属性：`order_control_visit_id`（初期 `0`）、`order_control_current_visit`（初期 `None`）
- Link進入共通メソッド：`begin_order_control_visit_on_link_entry()`（5経路から各1回呼び出し）
- earliest計算ヘルパー：`_compute_order_control_earliest_arrival_timestep_for_current_link()`
- 既存 `record_order_control_earliest_arrival_timestep_for_current_link()` は維持（既存辞書のみ更新）
- `visit_id` はorder-control対象Node訪問時のみ増加。対象外Nodeでは `current_visit = None`
- 既存 `order_control_earliest_arrival_timesteps` は再訪時上書きを維持。FCFS・BATCH参照先は未変更

**専用テスト：** `tests_order_control_current_visit_state.py`（15件、全PASS）

**回帰テスト：** 指定10本すべてPASS。baseline・exampleは既知値と一致、交通結果に変化なし。

**未実装（Phase 4-6O完了時点の記録）：** BATCH assignmentの訪問対応（4-6S）、service unit visit_id、訪問終了処理等（**その後Phase 4-6Sでassignment・visit_id・実通過照合を完了。`5e26bc9`、§1H.22**）。

**次工程（Phase 4-6O完了時点）：** Phase 4-6S（BATCH assignmentの訪問対応。設計メモ **§1H.17**・**§1H.21** 参照）（**完了。§1H.22**）

### フェーズ4-6P：Node端到着記録の訪問対応（実装済み）

Phase 4-6Pとして、current visitへの到着記録と独立乱数生成器を実装し、専用テスト・既存回帰・中規模sanity checkまで完了した。詳細は設計メモ **§1H.19**（設計記録 **§1H.19.1〜1H.19.6**、実装記録 **§1H.19.7**）を参照。

**commit：**

- Step 1：`b1b4d7f` — `phase 4-6P: add independent order-control random stream`
- Step 2：`b051c58` — `phase 4-6P: record initial and revisit arrivals and update BATCH integration setup`
- 設計記録（実装前）：`5846226`

**実装要点：**

- `World` に `W.order_control_rng` を追加（`W.rng` 初期化は変更なし）
- `Vehicle.record_order_control_node_arrival(node)` を追加
- 初回訪問：`W.rng` を1回使用し、current visitと初回履歴へ同値保存
- 再訪：`W.order_control_rng` を1回使用し、current visitのみへ保存。初回履歴は上書きしない
- 同一訪問中の再登録：上書き・乱数消費なし
- 対象Nodeで current visit 欠如、または到着情報の片側だけが `None` なら `ValueError`
- `Vehicle.update()` の2経路（taxi・通常リンク間移動）を新到着記録メソッドへ変更
- `record_order_control_node_first_arrival(node)` は維持（新メソッドからは呼ばない）
- `tests_order_control_batch_node_transfer_integration.py` に `_begin_arrived_current_visit_for_test(...)` を追加し、手動到着状態から `veh.update()` を呼ぶ6テスト・6車両のみ current visit を準備

**専用テスト：**

- `tests_order_control_rng.py`
- `tests_order_control_current_visit_arrival.py`

**回帰確認：** Phase 4-6P専用テスト、current visit・FCFS・BATCH既存テスト、order-control設定、Vehicle属性、車両リスト、baseline（48/48、16.5 m/s）、example（735/810、11.7 m/s）、中規模ネットワークsanity checkはいずれもPASS。診断スクリプトは通常回帰対象外のため未実行。

**Phase 4-6P完了時点で未実施（Phase 4-6Q・4-6Rへ継続）：** FCFSの参照先変更（4-6Q）、BATCH形成の参照先変更（4-6R）。いずれも完了済み（4-6Q：`7c3c6d3`・`9100803`、4-6R：`cdd19be`・`30588a0`・`ae57e40`）。

### フェーズ4-6Q：FCFSの参照先変更（実装済み）

Phase 4-6Qとして、FCFSの到着順位参照先を current visit へ変更し、専用テスト・回帰確認まで完了した。詳細は設計メモ **§1H.20** を参照。

**状態：** 実装・専用テスト・回帰確認・commit・push済み。

**commit：**

- 実装：`7c3c6d3` — `phase 4-6Q: rank FCFS by current visit and add revisit tests`
- 手動FCFS到着テストセットアップ修正：`9100803` — `phase 4-6Q: add current visit to manual FCFS arrival test setup`

**最新実装commit：** `9100803`

**実装要点：**

- `Vehicle.get_order_control_fcfs_rank_key(node)` を追加。current visitから `(arrival_time, arrival_tiebreaker, veh.id)` を返す（昇順）。初回履歴（`order_control_node_arrival_times` / `order_control_node_arrival_tiebreakers`）は参照しない
- `order_control_current_visit` 欠如、Node不一致、`arrival_time` または `arrival_tiebreaker` のいずれかが `None`（両方 `None` 含む）なら `ValueError`。`record_order_control_node_arrival(node)` とは異なり、FCFS順位読取時は到着記録済みが必須
- `Node.transfer_fcfs_no_clearance()` と `Node.transfer_fcfs_clearance()` を同じ current visit 順位仕様へ変更
- 候補抽出条件を `veh.route_next_link is not None` のみに変更。`node.name in veh.order_control_node_arrival_times` を削除
- 不整合Vehicleを黙って候補外にせず、順位キー取得時に `ValueError`
- 初回履歴は削除・改名・更新停止していない。BATCH本体は未変更（初回履歴参照のまま）

**専用テスト：**

- 新規 `tests_fcfs_order_control_revisit_ranking.py`（13テスト）：順位キー、初回履歴非参照、各種 `ValueError`、再訪順位、tiebreaker順位、`veh.id` fallback、同一訪問中の再登録、transfer経由の `ValueError`
- `tests_order_control_current_visit_state.py`：補助関数 `_sync_arrived_current_visit_for_test(...)` を追加し、6テストを current visit 到着同期へ更新

**既存テストセットアップ修正（commit `9100803`）：**

- `tests_order_control_batch_node_transfer_integration.py` の `test_fcfs_node_calls_fcfs_once` が回帰失敗（初回履歴のみで current visit 欠如）
- `_begin_arrived_current_visit_for_test()` を `_setup_arrived_vehicle()` 直後に呼び、`arrival_time` と `arrival_tiebreaker` を初回履歴と同値に同期。本体の `ValueError` 要件は緩和していない

**回帰確認（グループ1〜7、36ファイル相当、すべてPASS）：**

- Phase 4-6Q専用・小規模：`tests_fcfs_order_control_revisit_ranking.py`、`tests_order_control_current_visit_state.py`、`tests_order_control_current_visit_arrival.py`、`tests_order_control_node_arrival_times.py`、`tests_order_control_rng.py`、`tests_fcfs_order_control_tiebreaker.py`、`tests_fcfs_order_control_behavior.py`、`tests_fcfs_order_control_transfer.py`、`tests_fcfs_order_control_clearance_0.py`、`tests_fcfs_order_control_clearance_1.py`、`tests_fcfs_order_control_clearance_xyz.py`
- order-control設定・Vehicle周辺：`tests_order_control_clearance_settings.py`、`tests_order_control_eligibility.py`、`tests_node_order_control_attributes.py`、`tests_world_order_control_setters.py`、`tests_random_eligible_order_control.py`、`tests_vehicle_research_attributes.py`、`tests_load_vehicle_list_to_uxsim.py`
- BATCH単体・統合（BATCH本体未変更）：状態コンテナ、earliest arrival、trigger候補、t_trigger推定、inlink別候補、候補グループ順序、max batch size、service unit登録、service queue transfer、BATCH形成統合、BATCH transfer、BATCH `Node.transfer()` 統合。`test_fcfs_node_calls_fcfs_once` は修正後PASS。`test_n1_batch_vs_fcfs_equivalence` はPASS
- baseline：completed 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、total distance traveled 48000.0 m
- example：completed 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、total distance traveled 1632250.0 m
- 中規模ネットワーク（500 Vehicle）：FCFS/BATCH/standard いずれも completed 383/500、eligible Node数10、既存sanity checkすべてPASS（性能優劣は合否基準ではない）
- 1,000台グリッドネットワーク：全方式 completed 1000/1000、eligible Node数36、既存sanity checkすべてPASS（性能優劣は合否基準ではない）

**実行しなかったもの（通常回帰）：** 5,000台・10,000台のhigh-demand比較、signalized UXsimとのhigh-demand比較、`diagnostics/order_control/` 配下の診断スクリプト（Phase 4-6T〜4-6U・診断保存目的のため）

**次工程（Phase 4-6Q完了時点）：** Phase 4-6R（当時は未着手）

### フェーズ4-6R：BATCH形成の参照先変更（実装済み）

Phase 4-6Rとして、BATCHのtrigger候補順位および関連参照先を current visit へ変更し、legacy earliest辞書を初回訪問履歴化し、専用テスト・既存BATCHテスト更新・広い回帰確認まで完了した。詳細は設計メモ **§1H.21** を参照。

**状態：** 実装・専用テスト・既存テスト更新・広い回帰確認・commit・push済み。

**commit：**

- Step 1：`cdd19be` — `phase 4-6R: add BATCH current-visit accessors and preserve first earliest history`
- Step 2：`30588a0` — `phase 4-6R: use current-visit timing in BATCH formation and add revisit tests`
- Step 3：`ae57e40` — `phase 4-6R: add current visits to manual BATCH test vehicles, assert arrival errors, and exclude ineligible-node earliest`

**最新実装commit：** `ae57e40`

**実装要点：**

- `Vehicle._require_order_control_current_visit_for_batch(node)`、`get_order_control_batch_trigger_rank_key(node)`、`get_order_control_batch_earliest_arrival_timestep(node)` を追加
- `order_control_earliest_arrival_timesteps` を初回訪問分析履歴化（再訪時は上書きしない。対象外Nodeへは記録しない）
- BATCH trigger順位をcurrent visitの `arrival_time`・`arrival_tiebreaker` へ変更
- t_trigger Level 0・Level 1の入力をcurrent visitの `arrival_time`・`earliest_arrival_timestep` へ変更（Level 0/1の式自体は変更なし）
- inlink候補包含をcurrent visit `earliest_arrival_timestep` へ変更
- candidate group orderingのtrigger arrival参照をcurrent visitへ変更
- 不完全な到着情報を黙って除外せず `ValueError`（`route_next_link=None` は引き続き候補外）
- `Node.form_order_control_batch()` 自体は直接変更なし（委譲先がcurrent visit参照へ）

**専用テスト：**

- 新規 `tests_order_control_batch_revisit_ranking.py`（15テスト）
- `tests_order_control_batch_current_visit_accessors.py`、`tests_order_control_batch_earliest_arrival_timestep.py`（Step 1）

**既存BATCHテスト更新（Step 3、8ファイル）：** 7ファイルで手動Vehicle状態をcurrent visit対応へ更新し、1ファイル（`tests_order_control_batch_service_queue_transfer.py`）でorder-control対象外Node進入後のlegacy earliest非記録・current visit終了の期待値を更新。current visit対応の7ファイルはtrigger候補、t_trigger推定、inlink候補、候補グループ順序、BATCH形成統合、BATCH transfer、BATCH `Node.transfer()` 統合。trigger異常系を3テストへ分割。U1はtrigger候補外（`route_next_link=None`）。

**回帰確認（すべてPASS）：**

- Phase 4-6R直結6ファイル、BATCH単体・統合12ファイル（`test_fcfs_node_calls_fcfs_once`、`test_n1_batch_vs_fcfs_equivalence` 含む）
- FCFS回帰6ファイル、order-control共通9ファイル
- baseline・exampleは既知値と一致
- 中規模（500 Vehicle）・1,000台グリッドのsanity checkすべてPASS（性能優劣は合否基準ではない）

**実行しなかったもの（通常回帰）：** 5,000台・10,000台high-demand比較、signalized UXsim high-demand比較、`diagnostics/order_control/` 診断スクリプト（Phase 4-6T〜4-6U予定）

**Phase 4-6Sへ継続（Phase 4-6R完了時点の記録）：** `order_control_batch_assignments` のNode訪問対応、current visit `batch_assignment` のBATCH本体接続、service unit `visit_id`、実通過照合、既知prefix violation（Phase 4-6Rでは未解消）— **その後Phase 4-6Sで根本原因へ対応（通常回帰・縮小再現で確認。high-demand再確認は未実施。§1H.22）**

**次工程（Phase 4-6R完了時点）：** Phase 4-6S（当時は未着手）

### フェーズ4-6S：BATCH assignmentの訪問対応（実装済み）

Phase 4-6Sとして、BATCH assignment・service unit・実通過照合をNode訪問単位へ対応させ、専用テスト・既存テスト更新・広い回帰確認まで完了した。詳細は設計メモ **§1H.22** を参照。

**状態：** 実装・専用テスト・既存テスト更新・広い回帰確認・commit・push済み。

**実装commit：** `5e26bc9` — `phase 4-6S: move BATCH assignments to current visits and bind service units to per-vehicle visit IDs`

**最新実装commit：** `5e26bc9`

**実装要点：**

- current visit `batch_assignment` を現在BATCH制御の唯一のassignment参照先に変更
- `get_order_control_batch_assignment()`、`has_order_control_batch_assignment()`、`assign_order_control_batch_to_current_visit()` を追加
- trigger候補、t_trigger入力検証、inlink候補、prefix、candidate group orderingのassignment判定をcurrent visitへ変更
- `register_order_control_batch_service_units()` でcurrent visitへbatch ID設定、service unitへVehicleごとの `visit_ids` 保存
- `serve_order_control_batch_service_queue()` で実通過前にNode・visit_id・batch ID照合。正常な未到着と訪問不一致を区別
- 通過成功時に `vehicles` と `visit_ids` を同期削除
- registerロールバックをcurrent visit assignment対応
- legacy `order_control_batch_assignments` を現在制御から除外（初回訪問互換記録のみ維持）
- assignment由来の既知prefix violationの根本原因へ対応し、通常回帰・縮小再現テストで問題が再現しないことを確認した（high-demand実ネットワークでの再確認は未実施）

**専用テスト：**

- 新規 `tests_order_control_batch_visit_assignment.py`（32テスト）

**既存テスト更新（9ファイル）：** candidate group ordering、candidates by inlink、node transfer integration、service queue transfer、service unit registration、t_trigger estimation、transfer、trigger candidates、current visit state

**回帰確認（すべてPASS）：**

- BATCH限定：Step 1専用・current visit基盤、BATCH候補・形成、service queue・実通過（`test_fcfs_node_calls_fcfs_once`、`test_n1_batch_vs_fcfs_equivalence` 含む）
- FCFS回帰6ファイル、order-control共通9ファイル
- baseline・exampleは既知値と一致
- 中規模（500 Vehicle）・1,000台グリッドのsanity checkすべてPASS。Phase 4-6R参考値と交通結果が完全一致（性能優劣は合否基準ではない）

**実行しなかったもの（通常回帰）：** 5,000台・10,000台high-demand比較、signalized UXsim high-demand比較、`diagnostics/order_control/` 診断スクリプト

**後続工程へ残す課題：** trip-end VehicleのBATCH service unit対応、stale service unitの自動削除または回復方針、assignmentの正式な全訪問履歴、Level 2、Time-value Transaction

**次工程：** Phase 4-6U。high-demand再実行と、既知prefix violationが実ネットワークで再発しないことの確認。trip-end Vehicleとstale service unit処理の工程位置は未確定。assignment全訪問履歴は分析項目が明確になった後に横断的に設計する（設計メモ **§1H.17**・**§1H.23**）（**その後Phase 4-6Uで完了。§1H.24**）

#### 実装前の設計目標（過去記録）

以下はPhase 4-6S実装前の設計目標である。現在の実装結果は同じPhase 4-6S節の前半と、設計メモ **§1H.22** を参照する。「未着手」は当時の状態であり、現在は実装済みである。

- BATCH assignmentのNode訪問対応
- current visitの `batch_assignment` をBATCH形成・実通過へ接続
- service unitへ `visit_id` を保存
- service unitとVehicle current visitの訪問一致を確認
- 過去訪問assignmentが現在訪問を妨げない設計
- BATCH実通過・service queue完了時の訪問状態更新

### フェーズ4-6T：小規模BATCH再訪end-to-end統合（実装済み）

Phase 4-6Tとして、同一Vehicleが同じBATCH Nodeを二回訪問し、初回・再訪とも `Node.transfer()` 経由でBATCH形成・登録・実通過を完了する小規模end-to-end統合テストを追加し、BATCH関連回帰を確認した。詳細は設計メモ **§1H.23** を参照。

**状態：** 実装・回帰確認・commit・push済み。

**実装commit：** `b7159f9` — `phase 4-6T: verify initial and repeat BATCH service at the same node through Node.transfer`

**最新実装commit：** `b7159f9`

**新規テスト：**

- `tests_order_control_batch_revisit_integration.py`
- `test_same_vehicle_revisits_batch_node_and_completes_both_service_units`

**確認内容：**

- 同一Vehicle（`veh_revisit_batch`）がmergeを二回通過
- 初回・再訪とも `Node.transfer()` 経由（`transfer_batch()` → 形成・登録・service）
- `visit_id`：1 → 2
- batch ID：0 → 1（Node-local連続発行）
- legacy assignment：0を再訪後も維持
- service unit `visit_ids`：初回 `[1]`、再訪 `[2]`
- 初回・再訪とも実通過後にservice queueが空
- prefix `ValueError` は発生せず
- 本体変更なし

**回帰確認（19ファイル、すべてPASS）：**

- 再訪・current visit関連7ファイル
- BATCH候補・形成8ファイル
- BATCH service・統合3ファイル（`test_fcfs_node_calls_fcfs_once`、`test_n1_batch_vs_fcfs_equivalence` 含む）
- FCFS再訪1ファイル（`tests_fcfs_order_control_revisit_ranking.py`）

**実行しなかったもの（通常回帰）：** baseline、example、中規模比較、1,000台グリッド比較、5,000台・10,000台high-demand、signalized UXsim high-demand、`diagnostics/order_control/` 診断スクリプト

**後続工程へ残す課題：** trip-end VehicleのBATCH service unit対応、stale service unitの自動削除または回復方針、assignmentの正式な全訪問履歴、Level 2、Time-value Transaction

**次工程：** Phase 4-6U。high-demand再実行と、既知prefix violationが実ネットワークで再発しないことの確認。（**その後Phase 4-6Uで完了。§1H.24**）

#### 実装前の調査記録（過去記録）

Phase 4-6S完了時点では、再訪関連の単体・手動テストは実施済みだったが、同一Vehicleの初回から再訪二回目実通過までを通常 `Node.transfer()` 経路で一続きに確認する統合テストはなかった。その後Phase 4-6Tで完了した。

### フェーズ4-6U：high-demand再実行・既知prefix violation非再発確認（完了）

Phase 4-6Uとして、Phase 4-6S・4-6T後のNode再訪・BATCH assignment対応を、high-demand実ネットワークで再確認した。詳細は設計メモ **§1H.24** を参照。

**状態：** 再実行・検証完了。

**位置づけ：** 実行・検証フェーズ。本体・テスト・診断Pythonコード変更なし。新しい実装commitはない。

**最新実装commit：** `b7159f9`

**直前の文書commit（Phase 4-6T）：** `aca6ce9`

**文書更新前HEAD：** `aca6ce9`

**実行ケース：**

| ケース | ファイル | 条件 |
|--------|----------|------|
| U1 | `batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py` | 5,000台、c=0、signalized `[60,60]` |
| U2+U3 | `batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py` | U2：5,000台 c=1。U3：10,000台 c=1。all-red `[60,1,60,1]` |

**Case U1（5,000台 clearance=0）：**

- exit code 0、実行時間67秒、sanity check 20項目PASS
- signalized 5,000/5,000、avg TT 1,432.9 s、total distance 23,185,600.0 m
- FCFS 5,000/5,000、avg TT 821.2 s、total distance 18,424,000.0 m
- BATCH 5,000/5,000、avg TT 1,027.3 s、total distance 19,844,000.0 m、last completed 2,525.0 s
- BATCH/FCFS avg TT ratio 1.251、BATCH/signalized 0.717
- 既知W.T=605停止を越えて完走。prefix violationなし

**Case U2（5,000台 clearance=1）：**

- スクリプト総実行時間331秒（U2+U3）、Case U2 sanity check 24項目PASS
- signalized all-red 5,000/5,000、avg TT 1,102.0 s
- FCFS 5,000/5,000、avg TT 1,573.2 s
- BATCH 5,000/5,000、avg TT 1,147.1 s、last completed 2,348.0 s
- BATCH/FCFS avg TT ratio 0.729、BATCH/signalized 1.041
- 過去の5,000台BATCH prefix violation（g_5_4、veh_1952）は再発せず。Case U3へ進行

**Case U3（10,000台 clearance=1）：**

- 過去はCase U2停止のため10,000台BATCH未実行。今回初めて10,000台BATCH結果出力まで到達
- sanity check 24項目PASS
- signalized all-red 10,000/10,000、avg TT 2,699.0 s
- FCFS 10,000/10,000、avg TT 3,329.3 s
- BATCH 10,000/10,000、avg TT 3,011.9 s、last completed 5,382.0 s
- BATCH/FCFS avg TT ratio 0.905、BATCH/signalized 1.116
- prefix violationなし

**確認事項：**

- assignment prefix violation、visit_id mismatch、batch_assignment mismatch、service unit構造不正：すべてなし
- FCFS・BATCH eligible Node各36、集合一致
- 全方式completed ratio 1.000、unfinished 0
- 補助診断（318 lifecycle、node revisit）：未実行（U1〜U3すべてexit 0のため不要）
- 性能優劣は成功条件ではない

**実行しなかったもの：** 補助診断2本、FCFS high-demand単独テスト、baseline、example、中規模、1,000台グリッド、10,000台clearance=0、Level 2、Time-value Transaction

**次工程候補：** trip-end Vehicleとstale service unitの工程位置決定、Level 2仮想サービス推定、Level 2 unresolved時のLevel 1 fallback接続、assignment全訪問履歴（分析項目明確化後）、Time-value Transaction

**未実装課題：** trip-end VehicleのBATCH service unit対応、stale service unitの自動削除または回復方針、assignmentの正式な全訪問履歴、Level 2、Time-value Transaction

#### 実装前の調査記録（過去記録）

Phase 4-6T完了時点の次工程はPhase 4-6Uであった。その後Phase 4-6Uで完了した。

### フェーズ4-6V：zero-service追加形成修正とsize-one BATCHとFCFSの等価性回復

Phase 4-6Vとして、zero-service batch形成後に同一timestep内で追加batchを形成できない不具合を修正し、size-one BATCH（`batch_size=1`）とFCFSの交通結果一致を回復した。続けて診断スクリプトで等価性・batch size予備比較を確認した。技術設計の詳細は設計メモ **§1H.25** を参照。

**状態：** 本体修正・正式テスト・診断スクリプトともcommit・push済み。

**本体修正・正式テストcommit：** `2b10b08` — `phase 4-6 fix: reform BATCH after zero service and restore size-one BATCH equivalence with FCFS`

**診断スクリプトcommit：** `fe9e53e` — `phase 4-6 diagnostics: verify size-one BATCH equivalence with FCFS and recheck N=10 vs N=20`

**最新実装commit：** `2b10b08`

#### 発見されたsize-one BATCHとFCFSの不一致

size-one BATCH、すなわち `batch_size=1` のBATCHとFCFSについて、10,000台・自由経路・6×6 gridにおける時間的に最初の差を特定した。

**対象：**

- Vehicle：`veh_3573`
- Node：`g_3_4`
- inlink：`h_3_3_4`
- outlink：`h_3_4_5`
- FCFS：T=1103に `h_3_4_5` へ進入
- 修正前size-one BATCH：T=1104に `h_3_4_5` へ進入

**T=1103における確認結果：**

- FCFSとBATCHで到着状態は同一
- `incoming_vehicles` への登録状態は同一
- clearance状態は同一
- `veh_3573` のinlink先頭条件・capacity条件・outlink受入条件は同一
- 順位0の `veh_3551` はoutlink空間不足で通過不能
- 順位1の `veh_3573` は同一timestepに通過可能

**FCFS：**

- `veh_3551` を通過不能としてcontinueで飛ばす
- 同じT=1103に `veh_3573` を評価する
- `veh_3573` が通過する

**修正前size-one BATCH：**

- `veh_3551` だけをbatchとして形成・登録する
- `veh_3551` のservice unitはzero-serviceとなる
- `veh_3573` は形成・登録されない
- `veh_3573` は次のT=1104まで待機する

#### 直接原因

形成・登録したservice unitから実通過が0台だった場合でも、同一 `Node.transfer()` 呼出し・同一timestep内で、別inlinkに残る未割当trigger候補から追加batchを形成する処理がなかった。

#### 実装したzero-service追加形成の原則

N>=1のBATCHについて、次を満たす場合に、同一 `Node.transfer()` 呼出し・同一timestep内で追加batchを形成・登録・serveする処理を実装した。

- 直前のserve結果が0台
- clearance未充足による停止ではない
- queue先頭service Vehicleの未到着待ちではない
- 同一呼出し内でblockedと判定されたinlink以外のinlinkに、開始時snapshot内の未割当trigger候補が残る

**実装上の要点：**

- trigger候補snapshotは `transfer_batch()` 開始時に一度だけ固定する
- snapshotキーは `(vehicle.id, visit_id)` とする
- snapshotは同一 `transfer_batch()` 呼出し中に拡張しない
- `blocked_inlinks` は同一 `transfer_batch()` 呼出し内だけで保持する
- `blocked_inlinks` は次timestepへ持ち越さない
- clearance未充足は `blocked_inlinks` へ追加しない
- queue先頭service Vehicleが未到着の場合は `arrival_wait_stop` として追加形成を停止する
- blocked service unitをservice queueへ保持する
- blocked service unitのassignment・batch ID・visit IDを維持する
- 一度のserve処理内では、既存仕様どおり通過可能なVehicleを複数台処理できる
- serveで一台以上が実通過した場合、終了するのは次のform・register・serve追加反復であり、serveを最初の一台で打ち切るものではない
- 部分通過後に別batchを追加形成しない
- N上限へ到達したか、N上限未到達だったかは、追加形成の継続・終了条件に使用しない

**N上限を反復条件に使用しない理由：**

- triggerが変われば `t_trigger` も変わり得る
- 最初のtriggerでは候補外だったVehicleが、次のtriggerによる形成では候補になり得る
- N上限未到達だけでは、同一timestep内に新たに形成可能なVehicleが存在しないことを保証できない

#### 正式テスト

少なくとも次を記録する。

- size-one BATCHで順位0のblocked候補の後に順位1候補をFCFSと同一timestepに処理するテスト
- N>1で、最初のbatchがzero-serviceとなった後に別inlinkから追加batchを形成するテスト
- 一台以上が実通過した後は追加形成しないテスト
- clearance未充足時には追加形成しないテスト
- queue先頭service Vehicleが未到着の場合には追加形成しないテスト
- blocked service unit・assignment・batch ID・visit IDを維持するテスト
- 重複assignment・重複service unitが発生しないことの確認
- 限定回帰12ファイルがすべてPASS

#### size-one BATCHとFCFSの修正後診断

**200台固定route：**

- 6×6 grid
- horizontal-first fixed Manhattan route
- FCFS clearance=1
- size-one BATCH、Level 1、clearance=1
- completed：200/200
- completed ratio：1.0
- total travel time：33,613.0
- average travel time：168.065
- average delay：8.365
- total distance traveled：638,800.0
- unfinished：0
- last completed trip time：278
- eligible Node：36
- Vehicle別state・arrival_time・travel_time・traveled route・`log_t_link` が厳密一致

**10,000台自由経路：**

- 6×6 grid
- 同一vehicle plans
- FCFS clearance=1
- size-one BATCH、Level 1、clearance=1
- completed：10,000/10,000
- completed ratio：1.0
- total travel time：33,293,441.0
- average travel time：3,329.3441
- average delay：3,164.4481
- total distance traveled：39,892,000.0
- unfinished：0
- last completed trip time：6,492
- eligible Node：36
- 全10,000台のstate・arrival_time・travel_time・traveled route・`log_t_link` が厳密一致
- `veh_3573` はFCFS・size-one BATCHの両方で `h_3_4_5` へT=1103に進入
- 修正前のT=1103対T=1104の差は解消

これらは確認したnetwork・需要・seed・制御条件における完全一致であり、全ネットワーク・全需要に対する一般的理論証明とは表現しない。

#### 修正後N=10・N=20予備比較

**共通条件：**

- 10,000台
- 6×6 grid
- 自由経路
- signalなし
- clearance=1
- t_trigger Level 1
- World `random_seed=0`
- `DEMAND_GEN_SEED=42`
- 同一vehicle plans
- eligible Node=36
- 全10,000台完了

**修正後N=10：**

- total travel time：27,782,978.0
- average travel time：2,778.2978
- average delay：保存された完全精度値なし
- average delayの表示値：約2,613.4
- total distance traveled：39,962,400.0
- last completed trip time：4,971

**修正後N=20：**

- total travel time：35,221,107.0
- average travel time：約3,522.1
- average delay：約3,357.2
- total distance traveled：46,560,000.0
- last completed trip time：6,258

**修正後N=20 / N=10：**

- total travel time：約1.268
- average travel time：約1.268
- total distance traveled：約1.165
- last completed trip time：約1.259
- average delay比は、修正後N=10の完全精度値を保存していないため、厳密値として記録しない

以前報告したN=20 / N=10の約1.169は、zero-service修正前N=10を分母とした旧比較である。現行コードのN=20 / N=10比較では、average travel time比は約1.268である。

**修正前N=10：**

- total travel time：30,119,206.0
- average travel time：約3,011.9
- average delay：約2,847.0
- total distance traveled：40,996,000.0
- last completed trip time：5,382

修正前N=10値は、zero-service追加形成を行わない旧実装による履歴値であり、現行baselineとして使用しない。

N=20は、今回の固定需要・seed条件では修正前後でnetwork-wide集計値が一致した。これは次を証明するものではない。

- zero-service追加形成修正がN=20に適用されなかった
- N=20ではzero-service追加形成が一度も発生しなかった

正確には、「今回の固定需要・seed条件では、N=20について修正前後のnetwork-wide集計値の変化が観測されなかった」と記載する。

#### 旧signal設定（historical condition）

**設定：** `signal=[60,1,60,1]`

**設定時の意図：** green 60秒、all-red 1秒、green 60秒、all-red 1秒

**実際のtransfer判定上の完全phase長（現行UXsim離散実装、`DELTAT`=1秒）：**

- green：61 timesteps
- all-red相当：2 timesteps
- green：61 timesteps
- all-red相当：2 timesteps
- 実効transfer cycle：126 timesteps

**原因（UXsim本体は変更していない）：**

- `signal_control()` のphase切替条件が `signal_t > duration`（`>=` ではない）
- `Node.update()` でsignal phaseを更新した後に `Node.transfer()` が実行される
- 設定時間より1 transfer timestep長く作用するoff-by-one挙動

**offset（旧設定）：**

- 設定cycle length：122秒
- offset step：30.5秒
- offset値集合：{0.0, 30.5, 61.0, 91.5}
- 計算式は補正signalと同じ（cycle-length-based staggered offset）

**旧signal保存値（10,000台・同一需要・seed。historical exploratory result）：**

- total travel time：26,989,929.0秒
- 正確なaverage travel time：26,989,929.0 / 10,000 = **2,698.9929秒**
- average delay表示値：約2,534.1秒
- total distance traveled：50,367,200.0m
- last completed trip time：5,703
- completed：10,000/10,000

旧signal結果は削除しない。ただし、意図した実効60/1/60/1を実現していない **historical condition** として位置付け、現行の公平なFCFS/BATCH対signal比較baselineには使用しない。旧P2〜P4も補正前条件の探索履歴である。

#### 補正signal setting（corrected comparison setting）

**Case：** `S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1`

**診断スクリプト：** 診断スクリプトへ `--corrected-signal-baseline-only` を後続追加（比較条件訂正に伴う更新）

**設定：** `signal=[59,0,59,0]`（UXsim本体は変更せず、比較用signal settingを補正）

**signal group：**

- phase 0：east-west links
- phase 1：Link割当なし、all-red相当
- phase 2：north-south links
- phase 3：Link割当なし、all-red相当

**設定cycle length：** 118秒

**実効transfer phase長（実Nodeの `Node.update()` で確認）：**

- phase 0：60 timesteps
- phase 1：1 timestep
- phase 2：60 timesteps
- phase 3：1 timestep
- 実効transfer cycle：122 timesteps

**補正の根拠：** 現行UXsim実装では設定値59がtransfer判定上60 timesteps、設定値0が1 timestepとして作用する。意図した実効green 60秒・all-red 1 timestepを実現するため、API上は `[59,0,59,0]` を使用した。

**offset（補正signal。設計ルールは旧signalと同じ）：**

```
signal_offset = ((row + column) % 4) * (sum(signal_setting) / 4)
```

- offset step：29.5秒
- offset値集合：{0.0, 29.5, 59.0, 88.5}
- 全4 offset値について、実Nodeで定常完全phase長60/1/60/1を確認済み

**timing sanity check：**

- 実Nodeの `Node.update()` を使用
- zero-duration phase（設定0）は各1 timestep、phase skipなし

**Vehicle plan確認：** `_verify_vehicle_plan_invariants(vehicle_plans)` により、deterministic generator条件（`DEMAND_GEN_SEED=42`、10,000 plans、`veh_0`〜`veh_9999`、departure 0〜500、Manhattan distance ≥ 5）を検証

**共通simulation条件：**

- 10,000台、6×6 grid、自由経路、departure 0〜500、`TMAX`=50,000
- World `random_seed=0`、`DEMAND_GEN_SEED=42`
- `DELTAN`=1、`DELTAT`=1秒、単車線、internal signalized Node=36
- `free_flow_speed`=20 m/s、`jam_density`=0.2 veh/m
- `capacity_out`・`capacity_in`・Node `flow_capacity` 未指定

**補正signal確定結果：**

- exit code：0
- total travel time：28,535,318.0秒
- average travel time：2,853.5318秒
- average delay：2,688.6358秒
- total distance traveled：49,528,800.0m
- last completed trip time：5,900
- completed：10,000/10,000、unfinished：0
- simulation elapsed：約58.8秒、wall clock：約87秒

#### 修正後BATCH N=10対補正signal

**修正後BATCH N=10：**

- total travel time：27,782,978.0秒
- average travel time：2,778.2978秒
- average delay：完全精度値未保存（表示値約2,613.4秒）
- total distance traveled：39,962,400.0m
- last completed trip time：4,971
- completed：10,000/10,000

**補正signal / 修正後BATCH N=10：**

- total travel time：約1.027079
- average travel time：約1.027079
- total distance traveled：約1.239385
- last completed trip time：約1.186884

**BATCH N=10の平均旅行時間は、補正signalより75.2340秒、約2.64%短い。**

- average travel time差：2,853.5318 − 2,778.2978 = +75.2340秒（補正signalの方が長い）
- total distance：BATCH N=10の方が9,566,400m小さい
- last completed：BATCH N=10の方が929小さい
- average delay：補正signal 2,688.6358秒、BATCH N=10表示値約2,613.4秒（表示精度値比較。厳密比として扱わない）

今回の固定需要・1 seed条件では、average travel time・average delay表示値・total distance traveled・last completed trip timeのいずれでもBATCH N=10が小さい。一般的優位とは書かない。

#### 旧signalから補正signalへの変化（historical note）

| 指標 | 旧 [60,1,60,1] | 補正 [59,0,59,0] | 変化 |
|------|----------------|------------------|------|
| total travel time | 26,989,929.0 | 28,535,318.0 | +1,545,389.0（約+5.73%） |
| average travel time | 2,698.9929 | 2,853.5318 | +154.5389（約+5.73%） |
| average delay | 表示値約2,534.1 | 2,688.6358 | 表示精度比較で約+6.10% |
| total distance | 50,367,200.0 | 49,528,800.0 | −838,400.0（約−1.66%） |
| last completed | 5,703 | 5,900 | +197（約+3.45%） |

all-red短縮だけの因果効果とは書かない。green実効長・all-red実効長・設定cycle length・offset具体値・混雑・route choiceが連動して変化する。

#### BATCH対signalの順位反転

**旧signal（historical。公平baselineではない）：**

- BATCH N=10 average travel time：2,778.2978秒
- 旧signal正確average travel time：2,698.9929秒
- 差：+79.3049秒（BATCHが約2.9383%長い）

**補正signal：**

- BATCH N=10 average travel time：2,778.2978秒
- 補正signal average travel time：2,853.5318秒
- 差：−75.2340秒（BATCHが約2.6365%短い）

旧signalとの比較ではBATCH N=10が平均旅行時間で約2.94%長かったが、補正signalとの比較ではBATCH N=10が約2.64%短くなり、**順位が反転した**。相対差の変化は約−5.5748 percentage points。

#### FCFS参考比較（再実行なし・保存値）

FCFS clearance=1保存値（同一需要・seed。今回再実行していない）：

- total travel time：33,293,441.0秒
- average travel time：3,329.3441秒
- total distance traveled：39,892,000.0m
- last completed trip time：6,492

**補正signal / FCFS：**

- total travel time：28,535,318.0 / 33,293,441.0 ≈ 0.8571
- average travel time：2,853.5318 / 3,329.3441 ≈ 0.8571

**BATCH N=10 / FCFS：**

- total travel time：27,782,978.0 / 33,293,441.0 ≈ 0.8345
- average travel time：2,778.2978 / 3,329.3441 ≈ 0.8345

#### 旧signal比較のhistorical記録（現行baselineではない）

旧条件 `signal=[60,1,60,1]` に対する修正後N=10 BATCH比較（Phase 4-6U保存reference。historical exploratory result）：

- 修正後N=10 BATCH / 旧signal total travel time：約1.0294
- 旧signalの平均旅行時間は修正後N=10 BATCHより約2.9%短かった（表示値ベースの旧記録）
- この比較は意図した実効60/1/60/1を実現していない旧signalを用いるため、現行baselineではない

#### order-control clearance=1と補正signal all-red

**方向変更1回あたりの実効通過禁止timestep数（`DELTAT`=1秒）：**

| 方式 | T | T+1 | T+2 |
|------|---|-----|-----|
| FCFS/BATCH `order_control_clearance_timesteps=1` | 旧方向通過 | 別方向通過禁止 | 別方向通過可能 |
| 補正signal `[59,0,59,0]` | 旧方向green | all-red相当 | 新方向green |

補正signal条件では、order-control clearance=1と方向変更1回あたりの実効通過禁止timestep数が一致する。

ただし次は異なる：order-controlは実通過方向変更時にclearanceが発生する。signalは固定周期でall-red相当phaseが発生する。green継続時間、発生頻度、需要応答性、制御方式全体の動作は異なる。制御方式全体が同一とは書かない。

**旧signal `[60,1,60,1]` について：** 設定上all-red 1秒だが、実効2 timesteps。order-controlとの局所時系列対応は補正signalでは成立するが、旧signalでは成立しない（実効[61,2,61,2]）。

#### P2〜P4の扱い

- 旧default P1〜P4のP2〜P4は、旧signal builder（all-red設定値 `W.DELTAT`=1）により実行された **historical exploratory results**
- 意図した実効all-red 1 timestep条件ではない（現行離散実装では設定値1は実効2 timestepsとして作用する）
- 現行の正式signal timing感度分析には使用しない
- 今回は補正signal baseline 1ケース（`S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1`）のみ取得
- 補正signal settingによるP2〜P4は未実行であり、追加実行の要否と時期は別途判断する（Level 2設計前・Level 2後・実行しないかは未決定）

#### 解釈上の制約

今回の比較は、10,000台・1需要・1 seed・6×6 grid・自由経路・単車線・全内部Node同一signal setting・cycle-length-based staggered offsetにおける探索的結果である。

次を断定しない：

- BATCHまたはsignalの一般的優位
- 最適batch size、最適signal timing、最適offset
- Level 2の性能、時間価値取引の有効性
- 旧signalと補正signalの差の単一原因、all-red短縮だけの因果効果

#### 次の工程

- 追加のbatch size探索はここで終了
- 次はLevel 2仮想サービス推定の設計調査（**未実装**）
- Level 2 unresolved時はLevel 1 fallback
- 必要に応じてLevel 0 fallback
- trip-end Vehicleは研究対象外
- stale service unit回復は必要性が低ければ保留
- assignment全訪問履歴は後回し

#### 共通のLink容量・Node容量

今回のgridシミュレーションでは、Link作成時に `capacity_out` と `capacity_in` を明示指定していない。

**共通条件：**

- `free_flow_speed`：20 m/s
- `jam_density`：0.2 veh/m
- `number_of_lanes`：1
- `reaction_time`：1 s
- `DELTAN`：1
- `DELTAT`：`reaction_time`×`DELTAN`=1 s

UXsimの既定式によるLink基礎容量：

- 0.8 veh/s

`capacity_out`・`capacity_in` の未指定時既定値：

- inlink `capacity_out`：基礎容量の2倍、すなわち1.6 veh/s
- outlink `capacity_in`：基礎容量の2倍、すなわち1.6 veh/s

Nodeについては `flow_capacity` を明示指定していない。したがって：

- Node `flow_capacity`：`None`
- Node容量は実質的に無制限
- 今回のシミュレーションではNode容量は実効的な制約にならない

通過判定で実際に使用されるのは、各時点の次の残存容量である。

- `inlink.capacity_out_remain`
- `outlink.capacity_in_remain`
- `node.flow_capacity_remain`

Vehicle通過時には `DELTAN=1` が残存容量から差し引かれ、時間更新時に容量が補充される。

この容量設定はFCFS・BATCH・signalizedケースで共通である。

### フェーズ4-6W：模倣World型Level 2 t_trigger参照モデル

**位置付け：** Level 2 t_trigger estimatorの**本体実装ではない**。本体接続前に用いる、**模倣World型Level 2 t_trigger最小参照モデル**を確立した。Level 2の本体有効化・`form_order_control_batch()` への接続は**未実施**。

**目的：**

- Level 2の意味を小規模条件で固定する
- UXsim既存のBATCH serve規則（`_serve_order_control_batch_service_queue_internal()`）を再利用する
- capacity、clearance、outlink空間回復を含む仮想処理を確認する
- trigger Vehicle自身の仮想通過timestep（`t_virtual_trigger`）を得る
- 将来の本体用Level 2 estimatorまたはlocal virtual clock実装の比較基準を作る

**新規ファイル（本体未接続）：**

| 種別 | パス |
|------|------|
| 参照モデル | `diagnostics/order_control/level2_virtual_world_reference.py` |
| 専用テスト | `tests_order_control_batch_t_trigger_level_2_reference.py` |

**API：** `estimate_order_control_batch_t_trigger_level_2_reference(real_node, real_trigger_vehicle, t_level_1, virtual_horizon, *, mimic_random_seed=0)`

**暫定候補式（参照モデルで確認。本体未接続）：**

- 仮想計算成功時：`t_level_2_candidate = max(t_level_1, t_virtual_trigger)`
- 通常非適用時：`resolved=False`、`t_virtual_trigger=None`、`t_level_2_candidate=t_level_1`、`reason` 明示
- 重大不整合時：`ValueError` 等で停止（Level 1値へ代替しない）

**mimic World構造：**

```
dummy upstream Nodes → mimic inlinks → mimic order-control Node → mimic outlinks → sink Nodes
```

**real→mimic写像：** real Node / inlink / outlink / Vehicle を対応するmimicオブジェクトへ明示的に写像。service unitの所属inlink、`last_order_control_inlink`、capacity残量、FIFO順、clearance状態を再構築する。

**triggerの扱い：**

- triggerは現行trigger rank key（`arrival_time`・`arrival_tiebreaker`・Vehicle ID）で**選択済みの1台**を引数で受け取る（参照モデルは選び直さない）
- trigger後方の未assignment Vehicleはmimic Worldへ含めない
- triggerはreal Worldではbatch化しない。mimic World内だけでtrigger単独の疑似service unitをqueue末尾へ追加する

**route_next_link：** snapshot時点の値へ固定。仮想計算中は `route_next_link_choice()`・route search・DUO更新を行わない。意味は「trigger選択時点のroute_next_linkを固定した条件付き仮想サービス時刻」。実networkでは待機中にroute再選択され得る差異があるが、初期参照モデルでは予測条件を明確にするため固定している。

**capacity補充境界：**

- snapshot W.Tでは、当該timestepのLink.update()・Node.update()による補充済み残量をコピーし、**offset=0では再補充しない**
- offset≥1で新しいW.Tへ進み、UXsim既存式でLink・Node flow capacityを補充してからserveする

**outlink空間回復：**

- 関連outlink上の全Vehicleをmimic Worldへ複製し、car-followingで前進
- 入口空間回復（blocker x=0→前進→T=11でtrigger流入）とsink標準end-trip（T=10で到達・除去）を**分離して**確認

**virtual horizon：** triggerがhorizon内に通過しない場合は正常な非適用（`reason="virtual_horizon_exceeded"`）。研究上の正式値は未決定。

**診断trace：** `vehicle_transfer_timesteps`、`sink_end_trip_trace`（`outlink_removal_timestep`は`end_trip()`後の実除去確認後に記録）。

#### Phase名称管理上の失敗と再発防止規則

通常工程ではMarkdown上のPhase記号とコミット件名の `phase 4-6X:` 形式を対応させていた。修正期間中はコミット件名にPhase記号を使わない方針とした一方、Markdown内部ではPhase 4-6U・4-6Vを消費し、Gitコミット件名とMarkdown内部Phase連番の対応が失われた。これは工程名称管理上の失敗である。既存のpush済みコミット名・過去MarkdownのPhase名は変更しない。

**今後の規則：**

- Markdown上で正式Phase記号を使う通常工程では、関連コミット件名にも同じPhase記号を使う（Phase 4-6W関連は `phase 4-6W:`）
- コミット件名にPhase記号を使わない修正作業では、Markdown内部でも新しいPhase記号を消費しない
- Phase 4-6Wから通常運用へ復帰する

**状態：** 参照モデル・専用テストは実装・独立レビュー完了。本体Level 2へは未接続。関連コミット件名は `phase 4-6W:` を使用する（commit IDはGit履歴参照）。

#### テスト結果

**専用テスト：** 18/18 PASS（`tests_order_control_batch_t_trigger_level_2_reference.py`）

**基本4ケース（snapshot W.T=10）：**

| Case | 構成 | clearance | t_virtual_trigger |
|------|------|-----------|-------------------|
| 1 | service unit 1個 + trigger | 0 | 11 |
| 2 | service unit 1個 + trigger | 1 | 12 |
| 3 | 異inlink service unit 2個 + trigger | 0 | 12 |
| 4 | 異inlink service unit 2個 + trigger | 1 | 14 |

**その他確認：** offset=0でのcapacity非再補充、次timestepでの補充、同一timestep同一inlink複数台通過（A1・A2ともT=10）、outlink前進による入口空間回復、sink標準end-trip、trigger後方Vehicle除外、同時到着trigger rank key、virtual horizon到達、visit_id/assignment/inlink/prefix不一致、real World不変、real RNG不変、決定論性。

**限定既存テスト（5ファイル）：** すべてPASS。全テスト一括実行・10,000台/200台diagnosticは未実施。

**小規模fixture実行時間：** World構築を含む参照モデル1回あたり約9.69 ms（W.T=10、TMAX=200、少数Node・Link・Vehicle、virtual horizon=20）。大規模利用時間の確定値ではない。

#### 未解決事項

- 本体Level 2へ未接続
- Level 0・Level 1は未変更
- inlink未到着Vehicleの模倣は未対応
- 組合せ探索なし
- route_next_linkはsnapshot固定
- virtual horizon正式値未決定
- 大規模性能未評価
- signal制御との統合未評価
- local virtual clock未実装

> **更新注記（2026-08-24）：** 上記は Phase 4-6W 時点の未解決事項である。本体 Level 2 接続（4-6Y）後、Level 2 short TMAX 正式反映および TVT 向け全World baseline 性能調査を実施済み（設計メモ `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§23**）。`virtual horizon` 正式値・10,000 台全World baseline 実測は**未確定**（§23.16、§23.18）。

#### 次工程候補（断定しない）

1. Phase 4-6W参照モデルの適用範囲と性能測定計画を確定
2. 模倣Worldを本体で直接使うか、local virtual clockへ移植するかを比較
3. 本体Level 2接続仕様を確定
4. virtual horizonの扱いを決定
5. inlink未到着Vehicleへの対応要否を判断
6. 通常非適用時にLevel 1値を採用する処理を、本体接続時にどこへ置くか決定（参照モデルでは `t_level_2_candidate=t_level_1`。重大不整合はValueErrorで隠さない）

> **更新注記（2026-08-24）：** 上記は Phase 4-6W 時点の候補である。本体 Level 2 接続（4-6Y）および TVT 向け全World baseline 性能調査・Level 2 short TMAX 正式反映はその後実施済み（設計メモ `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§23**）。

技術詳細は設計メモ **§1H.26** を参照。

### フェーズ4-6X：未到着service-unit Vehicle対応（参照モデル内最小実装完了）

**位置付け：** Phase 4-6W模倣World型Level 2 `t_trigger`参照モデルを拡張する**参照モデル内のPhase 4-6X最小実装**。未到着service-unit Vehicleの仮想前進・仮想到着登録、Type A / Type B route分類、`acceptable_outlinks`へのVehicle ID剰余選択、参照モデル専用service処理を実装した。UXsim本体Level 2は**未接続**。`uxsim/uxsim.py`は変更していない。

**Phase 4-6Wで判明した制約：** Phase 4-6W参照モデルはsnapshot時点でNode端到着済みのservice-unit Vehicleを中心に検証した。現行BATCH形成では`earliest_arrival_timestep <= t_trigger`によりNode端未到着Vehicleもservice unitへ登録され得るが、Phase 4-6Wではinlink Vehicleを前進させないため、未到着の先頭Vehicleではarrival waitが解消せずvirtual horizon超過となり得る。Phase 4-6Xでこの範囲を参照モデル内で対応した。

**Phase 4-6Xで実装した内容（概要）：**

1. 未到着service-unit Vehicleのinlink上仮想前進とNode端仮想到着登録（`virtual_node_arrival_timesteps`）
2. snapshot時点の`route_next_link`確定（Type A）・未確定（Type B）の区別
3. Type Bについて、仮想transfer時点での楽観的仮想outlink選択（`acceptable_outlinks`へのVehicle ID剰余選択。全物理outlink循環探索方式は撤回・未実装）
4. 参照モデル専用service処理（`_serve_reference_batch_queue`）。停止理由の明示分類、`active_inlink`・`blocked_inlinks`・`SKIP_INLINK`、`service_stop_trace`
5. 最終コードレビュー：`stop_reason`をservice処理の最終終了理由、`blocked_inlinks`を途中でblockされたinlinkの記録として分離

**状態：**

- 参照モデル内の最小実装完了
- Phase 4-6X専用テスト **28/28 PASS**（`tests_order_control_batch_t_trigger_level_2_unarrived_reference.py`）
- Phase 4-6W既存テスト **18/18 PASS**（`tests_order_control_batch_t_trigger_level_2_reference.py`は変更していない）
- 限定既存テスト5ファイルすべてPASS
- `ast.parse` OK
- performance benchmark未実施
- network-wide simulation未実施
- 本Markdown更新は文書のみ。Markdown更新に伴うテスト再実行は行っていない

**実装ファイル：**

- 変更：`diagnostics/order_control/level2_virtual_world_reference.py`
- 新規：`tests_order_control_batch_t_trigger_level_2_unarrived_reference.py`

**次工程候補（決め打ちしない）：** 実装差分の最終レビュー・commit・push、小規模performance benchmark設計、模倣Worldとlocal virtual clockの比較、本体Level 2接続仕様の検討、virtual horizon正式値の判断。

技術詳細・実装結果・テスト結果・未解決事項は設計メモ **§1H.27**（§1H.27.25以降）を参照。

### フェーズ4-6Y：Level 2本体接続・実ネットワーク検証・N=1一致性確認・mimic World性能修正

**位置付け：** コミット `6e6a601` のLevel 2本体接続から、実ネットワーク診断・N=1 BATCH Level 2対FCFS一致性確認・mimic World Analyzer省略・5,000/10,000台追加検証までを含むフェーズ。設計メモ **§1H.27.42〜§1H.27.45**。

> **更新注記（2026-08-24）：** 以下の Analyzer 省略による性能改善記録は**当時の記録**である。その後、Level 2 mimic World の **short TMAX 正式反映**（§23.8）により forward コストが大幅に短縮された。全World baseline 経路の現在の主要ボトルネックは `World.copy()`（設計メモ §23.13）。`World.copy()` 軽量化は未着手・後回し（§23.14、§23.19）。

#### Phase名称と対象範囲

- フェーズ4-6Yはコミット `6e6a601` のLevel 2本体接続から始まる
- 対象は設計メモ **§1H.27.42**（Level 2本体接続、`6e6a601`）、**§1H.27.43**（未到着Vehicle route状態修正と5,000台Level 1対Level 2比較、`af0e037`）、**§1H.27.44**（N=1 BATCH Level 2対FCFS一致性とmimic World Analyzer省略）
- 本体接続作業開始時（`6e6a601`）には、フェーズ4-6Yという名称を利用者へ事前告知していなかった
- 今回の正式Markdown作成時に初めてフェーズ4-6Yという名称が提示され、利用者との確認後、Level 2本体接続から現在までの一連の作業をフェーズ4-6Yとして正式に確定した
- 技術的な作業内容やGit履歴は変更しない。フェーズ名の告知が遅れたことはフェーズ管理上の問題である

**Phase名称管理規則（再発防止）：**

1. 新しいフェーズを始める前に、フェーズ名を利用者へ明示する
2. フェーズの目的と対象範囲を明示する
3. 利用者の合意後に、そのフェーズ名を作業指示・コミット・Markdownへ使用する
4. 未使用のアルファベットがあることだけを理由に、新しいフェーズ名を自動的に割り当てない
5. 作業後のメモ作成段階で初めてフェーズ名を付けない
6. 利用者の事前合意なくStep番号や下位区分名を作らない
7. 未使用の番号があることだけを理由にStep番号を割り当てない
8. フェーズ4-6YではStep区分を使用しない
9. 後から整理が必要な場合は、利用者へ説明し、合意を得てから遡及的に確定する
10. 今回のフェーズ4-6Yは、利用者との確認により遡及的に確定した例外である

**Phase 4-6Xとの境界：** Phase 4-6X（§1H.27.1〜§1H.27.41）は本体未接続の参照モデル段階。フェーズ4-6Y（§1H.27.42以降）はLevel 2本体接続と実ネットワーク診断である。§1H.27.42、§1H.27.43、§1H.27.44は個別の実装・診断記録であり、Step区分は使用しない。

#### Level 2本体接続

- **コミット：** `6e6a601`
- **設計メモ：** §1H.27.42
- Level 2参照処理の本体側配置（`uxsim/order_control_batch_level_2_reference.py`）
- `order_control_batch_t_trigger_level=2` の正式受理
- `_resolve_order_control_batch_t_trigger()` への接続
- unresolved時の計算済みLevel 1値採用（Level 1二重計算防止）
- `order_control_batch_virtual_horizon` のNode設定（暫定既定値30）
- 4個の軽量カウンター（`call_count`、`resolved_count`、`unresolved_count`、`level_1_fallback_count`）
- 前回結果を保存しない方針
- 本体接続テスト22件、参照テスト20件、未到着参照テスト29件

#### 未到着Vehicle route状態修正と5,000台Level 1対Level 2比較

- **コミット：** `af0e037`
- **設計メモ：** §1H.27.43
- 最初の5,000台試験で `route_next_link` 属性欠如による `AttributeError`
- 最初のLink上の属性未作成、2本目以降の現在Link保持、明示的Noneの3状態区分
- `grid_level_1_vs_level_2_check.py` 追加（`af0e037`）
- 5,000台Level 1対Level 2比較完了（全車両完了、Level 2解決率91.52%、L2/L1≈270.8倍）
- **この記録時点では10,000台Level 1対Level 2は未実施。その後、§1H.27.45でh=30・h=50を実施済み**

#### N=1 BATCH Level 2対FCFS一致性とmimic World性能修正

- **コミット：** `5439cf3`、`639444f`、`4ab1b66`、`1a84132`
- **設計メモ：** §1H.27.44
- **診断スクリプト：** `diagnostics/order_control/grid_n1_level_2_vs_fcfs_check.py`

**目的：**

- N=1 BATCH Level 2がFCFSと集計・Vehicle単位まで一致するかを、6×6 grid・自由経路・高需要条件で確認する
- Level 2を実際に呼び出す（`batch_size=1` bypassは行わない）
- 大規模試験で発生したmimic World Analyzer初期化の性能問題を特定・解消する

##### 修正前200台診断（`5439cf3`）

| 項目 | FCFS | N1-L2 |
|------|------|-------|
| exec_simulation_seconds | 0.878 | 100.783 |
| completed_trips | 200/200 | 200/200 |

Level 2: `call_count=1,497`、全resolved、`comparison_class=exact_match`

##### 修正前5,000台の20時間超中断

- FCFS: 5,000/5,000完了、`exec_simulation_seconds=16.224`
- N1-L2: 20時間超未完了、CPUほぼ100%、Ctrl+C中断
- N1-L2最終結果・Level 2カウンターは未取得。5,000台一致性は未判定
- 無限ループの証明ではない。Level 2呼出しごとのmimic World `finalize_scenario()` と不要なAnalyzer初期化が重大な性能要因

##### Tracebackとsampleによるボトルネック

- Traceback: mimic World `finalize_scenario()` → Analyzer作成 → `matplotlib.font_manager.findSystemFonts()`
- macOS sample: メインスレッド約99%がフォント一覧構築処理内
- 20時間すべてがフォント探索だったとは断定しない

##### Analyzer省略設計（`639444f`）

- `World.finalize_scenario(W, tmax=None, *, create_analyzer=True)`
- 通常World: 既定値 `True`（従来どおりAnalyzer作成）
- mimic World: `mimic_W.finalize_scenario(create_analyzer=False)`
- Level 2交通計算・virtual horizon・fallback・実World/RNGは変更なし
- `get_font_for_matplotlib()` キャッシュは未追加

##### create_analyzer=Falseの利用制約

- `W.analyzer` 自体を作成しない（可視化無効化だけではない）
- 通常 `exec_simulation()` では `W.analyzer` を使用するため、一般用途では使わない
- Level 2 mimic Worldの限定仮想ループのみで使用

##### テスト結果

| テスト | 件数 |
|--------|------|
| Level 2参照 | 20 |
| 未到着参照 | 29 |
| Level 2本体接続 | 22 |
| **合計** | **71** |

追加: Analyzer作成/非作成確認、`findSystemFonts()` 0回、実World/RNG不変。単一Level 2参照呼出し 0.19 ms（診断値）。`tests_order_exchange_baseline.py` 48/48、`example_00en_simple.py` 成功。

##### 修正後200台

| 項目 | FCFS | N1-L2 |
|------|------|-------|
| completed_trips | 200/200 | 200/200 |
| exec_simulation_seconds | 15.390 | 4.760 |

`call_count=1,497`維持、`exact_match`。N1-L2: 100.783→4.760秒（約95.3%短縮、≈21.2倍）。FCFS時間変動はAnalyzer省略の影響ではない。

##### 1,000台（`4ab1b66`）

| 項目 | FCFS | N1-L2 |
|------|------|-------|
| completed_trips | 1,000/1,000 | 1,000/1,000 |
| exec_simulation_seconds | 17.711 | 42.389 |

`call_count=7,766`、全resolved、`exact_match`、N1-L2/FCFS比 2.3934

##### 修正後5,000台

| 項目 | FCFS | N1-L2 |
|------|------|-------|
| completed_trips | 5,000/5,000 | 5,000/5,000 |
| exec_simulation_seconds | 31.086 | 765.662 |

Level 2: `call_count=46,428`、`resolved=46,390`、`unresolved=38`、`fallback=38`。`exact_match`、N1-L2/FCFS比 24.6302。約12分46秒で完了（修正前20時間超未完了は解消）。

##### exact_matchの意味

診断スクリプトの集計・Vehicle単位比較がすべて一致。指定条件（6×6 grid、自由経路、seed、parameter）における実証結果であり、一般的証明ではない。

##### unresolved 38回とLevel 1 fallback 38回

5,000台で38回unresolved→38回Level 1値採用。fallbackを含むLevel 2本体経路でもFCFSと完全一致。交通上問題ないという一般化はしない。

##### 性能改善と残存コスト

- 200台N1-L2: 約21.2倍高速化（Analyzer省略）
- 5,000台: N1-L2はFCFSの約24.63倍。Level 2仮想計算本体の負荷は残る

> **更新注記（2026-08-24）：** 上記は Analyzer 省略後・**full TMAX 時代**の記録である。short TMAX 正式反映後の Level 2 mimic 構築コスト短縮と全World baseline 性能は設計メモ **§23.6、§23.12** を参照。Level 2「追加性能改善」の一部（TMAX 短縮）は実施済み。`World.copy()` 軽量化は未着手（§23.14）。

##### この記録時点で未実施だった項目

- 10,000台N=1 BATCH Level 2対FCFS診断
- その後、§1H.27.45で実施し、`exact_match`を確認済み

#### フェーズ4-6Y追加検証：5,000台・10,000台におけるBATCH関連の相互・相対比較

**位置付け：** フェーズ4-6Yで接続・修正したLevel 2について、5,000台と10,000台の6×6 grid条件で追加診断を実施した記録。設計メモ **§1H.27.45**。

**記録作成前HEAD：** `8dc83d9`。診断スクリプト2本とMarkdown3本は未コミット。commit後に新しいcommit IDが確定する。

**実行した追加診断：**

- 10,000台Level 1対Level 2、h=30
- 10,000台Level 1対Level 2、h=50
- 10,000台N=1 BATCH Level 2対FCFS
- 5,000台Level 1対Level 2、h=30再実行
- 5,000台Level 1対Level 2、h=50
- 5,000台補正signalized UXsim（`--corrected-signal-baseline-only --num-vehicles 5000`）

**変更した診断スクリプト（未コミット）：**

- `grid_level_1_vs_level_2_check.py`：`--virtual-horizon`（既定30、0以上の整数、負数はargparseで拒否）。Level 2ケースのみ適用。
- `grid_10000_batch_size_and_signal_timing_preliminary_check.py`：`--num-vehicles {5000,10000}`（既定10,000）。5,000台は`--corrected-signal-baseline-only`のみ。5,000台では10,000台historical referenceとのcross-scale数値比較をskip。

**5,000台Level 1・Level 2（主要結果）：**

| 指標 | Level 1 | Level 2 h=30 | Level 2 h=50 |
|------|--------:|-------------:|-------------:|
| completed trips | 5,000 / 5,000 | 5,000 / 5,000 | 5,000 / 5,000 |
| average travel time (s) | 1,147.1 | 1,137.6 | 1,168.6 |
| total distance (m) | 18,976,800 | 19,436,000 | 19,704,800 |
| exec simulation seconds | 28.773 | 180.196 | 196.705 |

**10,000台Level 1・Level 2（主要結果）：**

| 指標 | Level 1 | Level 2 h=30 | Level 2 h=50 |
|------|--------:|-------------:|-------------:|
| completed trips | 10,000 / 10,000 | 10,000 / 10,000 | 10,000 / 10,000 |
| average travel time (s) | 2,778.3 | 2,985.8 | 3,191.4 |
| total distance (m) | 39,962,400 | 42,358,400 | 43,370,400 |
| exec simulation seconds | 69.786 | 545.385 | 616.350 |

**virtual horizon 30対50（Level 2カウンター、5,000台）：**

| 指標 | h=30 | h=50 |
|------|-----:|-----:|
| resolved rate | 0.9152 | 0.9884 |
| unresolved count | 919 | 139 |
| exec seconds | 180.196 | 196.705 |

**virtual horizon 30対50（Level 2カウンター、10,000台）：**

| 指標 | h=30 | h=50 |
|------|-----:|-----:|
| resolved rate | 0.7827 | 0.9445 |
| unresolved count | 3,317 | 938 |
| exec seconds | 545.385 | 616.350 |

**10,000台N=1 BATCH Level 2対FCFS：** `comparison_class=exact_match`。`call_count=94,730`、`resolved_rate=0.9908`。N1-L2 exec 3,098.328 s、FCFS exec 65.310 s、比 47.4405。

**暫定判断：** virtual horizon 30を当面の暫定値として維持。horizon 50は採用しない。horizon 30を正式値または最適値とは確定しない。指定条件でhorizon 30対50の限定比較完了（体系的horizon感度分析完了ではない）。

**解釈上の制約：** 1 network、1 seed、自由経路。複数seed、別network、Vehicle別・Node別分析、統計的検定は未実施。詳細は設計メモ **§1H.27.45**。

#### フェーズ4-6Yの完了・未実施

**完了済み：**

- Level 2本体接続（`6e6a601`、§1H.27.42）
- unresolved時のLevel 1 fallback、4カウンター
- 未到着Vehicle route状態修正（`af0e037`、§1H.27.43）
- 5,000台Level 1対Level 2比較（§1H.27.43）
- N=1 BATCH Level 2対FCFSの200台・1,000台・5,000台・**10,000台**診断（§1H.27.44、§1H.27.45）
- mimic World Analyzer省略（`639444f`、§1H.27.44）
- 5,000台・10,000台N=1一致性確認（`exact_match`）
- **10,000台**Level 1対Level 2比較（h=30・h=50、§1H.27.45）
- **10,000台**Level 2カウンター確認・計算時間確認（§1H.27.45）
- 指定条件でのvirtual horizon 30対50限定比較（§1H.27.45）
- 5,000台補正signalized UXsim比較（§1H.27.45）

**未実施（フェーズ4-6Yの試験・評価）：**

- 複数seed、別network → Time-value Transaction実装後の共通評価へ繰り越し（§1H.27.46）
- 体系的horizon感度分析（30・50以外） → BATCH固有課題として保留（§1H.27.46）
- Vehicle別・Node別分析 → 共通評価へ繰り越し（§1H.27.46）
- Level 2仮想計算本体の追加性能改善 → 必要性確認後（§1H.27.46）。**2026-08-24 追記：** short TMAX 正式反映により mimic 構築コストは大幅短縮済み（設計メモ §23）。`World.copy()` 軽量化は未着手・後回し（§23.14）

**後続実装・保留：**

- Time-value Transaction（次の本体対象。Phase名・実装範囲は未決定）
- stale service unit対応は必要性が低ければ保留
- assignment全訪問履歴は後回し
- trip-end Vehicleは**現在の研究対象外**であり、将来研究対象を拡張する場合の課題

技術詳細は設計メモ **§1H.27.42**、**§1H.27.43**、**§1H.27.44**、**§1H.27.45**、**§1H.27.46** を参照。

#### BATCH関連の残作業整理とTime-value Transactionへの移行判断

- BATCH基本実装、Level 2接続、Level 1 fallback、主要診断、N=1一致性は指定条件で確認済み
- Time-value Transaction開始前に必要な既知BATCH修正は現時点でない
- BATCH関連の残作業は設計メモ§1H.27.46へ整理した
- 複数seed、別network、Vehicle別・Node別分析、統計的検定はTime-value Transaction実装後の共通評価へ繰り越す
- N感度、horizon 30・50以外の体系的探索、Level 2追加性能改善はBATCH固有課題として保留する（**2026-08-24 追記：** TMAX short 化は実施済み。`World.copy()` 軽量化は未着手。設計メモ §23.14）
- Level 0自動fallback、stale service unit、assignment全訪問履歴は必要性を確認してから対応する
- trip-end Vehicle、specified_route、taxi mode、signal統合は現在のBATCH研究対象外
- batch_size=10、通常Level 2、unresolved時Level 1 fallback、virtual horizon 30を暫定ベースラインとする
- horizon 30は正式値・最適値ではない
- horizon 50は今回の指定条件では採用しない
- BATCH単独の追加探索はいったん停止する
- 次の本体対象をTime-value Transactionとする
- Time-value TransactionのPhase名、詳細区分、実装範囲はまだ決めていない
- 詳細は設計メモ§1H.27.46を参照する

#### Time-value Transaction（TVT）制度・技術設計整理の開始

- BATCH Phase 4-6Y 後の次の本体対象として、TVT の制度・技術設計整理を開始した
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` を新規作成した
- この新規ファイルを **TVT 設計の正本**とする
- **TVT 本体はまだ未実装**
- FCFS 予想到着順位、割当権利行使順位、意思決定窓 6 timestep、全World baseline、局所候補評価、TVT-SB/MH/SP/MP、確定順位ブロック等の基本設計を整理した
- 主な保留事項は、非参加 Vehicle あり複数買い手一般形、RNG 設計、horizon 正式値
- ~~次の技術作業は**全World baseline 仮想計算の性能測定**~~ **2026-08-24 に性能測定・Level 2 short TMAX 正式反映を実施済み**（設計メモ §23）
- 詳細は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` を参照する

#### 2026-08-24：TVT全World baseline性能調査とLevel 2 short TMAX正式反映

- TVT 向け全World baseline 仮想計算の性能を調査した
- 初期の 5,000 台・50 timestep では copy 込み中央値が約 7.39 秒だった
- cProfile により、BATCH Level 2 mimic World が実World の `TMAX=30000` を引き継ぎ、過大な配列を毎回生成することが主要ボトルネックと判明した
- Level 2 mimic World の TMAX を `(real_W.T + 200) * real_W.DELTAT` へ短縮する方式を A/B 検証した
- 複数 snapshot timestep、virtual horizon 30・199・200、horizon 終端、large real TMAX 境界ケースで正本 full TMAX 方式との結果一致を確認した
- `uxsim/order_control_batch_level_2_reference.py` の TMAX 選択式 1 行を short TMAX 方式へ正式変更した
- 変更前 full TMAX 正本は `diagnostics/order_control/order_control_batch_level_2_full_tmax_reference_snapshot.py` へ保存した
- Level 2 関連 71 件、BATCH 統合等 81 件、合計 152 件のテストが成功した
- 全 pytest はデモスクリプトの表示待ちと思われる停止が続いたため完走せず、手動中止した
- 正式 short TMAX 実装で、5,000 台・50 timestep の copy 込み中央値は約 1.94 秒となった
- 現在の主要ボトルネックは `World.copy()` だが、copy 軽量化は後回しとし、TVT 実装を優先する
- 詳細は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` の「§23 全World baseline仮想計算の性能検証とLevel 2 short TMAX」を参照する

#### 2026-08-26：全World baselineのsnapshot固定集合と二段階観測設計

- 今回の設計更新直前の保存済み状態はコミット `3690a8c` であり、`feature/intersection-order-control` へpush済み
- 2026-08-26の今回の設計更新は、そのコミット後に行った未実装・未コミットの設計整理として記録する
- TVT候補Vehicleを、baseline開始時点ですでに対象inlink上にいるVehicleへ限定する方針を採用
- baseline開始後に対象inlinkへ入ったVehicleは今回の候補集合へ追加しない
- snapshot固定集合は到着済みAと未到着Bに概念分類するが、別保存構造を意味しない
- timestep T到着Vehicleは既到着Vehicleとの同着ではなく、T到着の後着Vehicleとして順位付けし、TVT起点から除外する
- T+1からT+6の到着Vehicleから権利保有車両を選ぶ
- T+6後も、権利保有車両の通過 `P` までBの到着記録を継続する
- 候補時間条件は `arrival <= P - 1`
- `route_next_link` を局所仮想計算に使用する方向
- 既存 `visit_id` を利用し、新しいvisit IDは作らない方向
- 初期実装では過去baseline結果を `real_W` へ蓄積しない
- TVT順位確定状態、collector、早期終了性能は未実装・未確認
- 詳細は設計メモ **§24** を参照する

#### 2026-08-27：全World baseline collectorの実装前設計

- 直前の保存済みコミットは `86313cc` でpush済み
- 今回の設計整理は未実装・未コミット
- dataclass形式の固定visit記録を第一候補とした
- 主索引、Vehicle別索引、Node別索引は同じ固定visit記録を参照する
- 通過は通過前確認と通過後設定に分ける
- BATCHはservice queue整理後に通過timestepをまとめて反映する
- 初期対応はBATCH、FCFS clearanceあり、通常transfer
- 読取機能はNode別と固定visit1件の2つ
- collector本体を独立モジュールへ置く方向
- 実装は3回に分ける想定
- 詳細は設計メモ **§25** を参照する
- 次回作業は設計メモ **§25.19** の第1回実装
- 第1回実装はcollector本体、World内部参照、collector単体テストまで
- UXsimの到着・通過通知接続は第2回実装
- 新しいチャットでは§24、§25、§25.19、最新Git状態を確認して再開する
- Cursor報告だけで確定せず、Terminal確認を行う
- コミットと`git push`は分ける

#### 2026-08-27：全World baseline collectorの第1回実装完了

（上記「実装前設計」記録の続き。設計メモ **§25.20** を参照。）

Git状態（本記録時点）：

- ブランチ：`feature/intersection-order-control`
- 直前の保存済みコミット：`59aeebd`
- コミット名：`Document pre-implementation design for the order-control baseline collector`
- リモートとの状態：作業開始時点では`origin/feature/intersection-order-control`と同期済み
- 現在の未追跡ファイル：`diagnostics/order_control.zip`
- 今回のcollector実装と本メモ更新は、まだ新しいコミットへ保存されていない

実装内容（Terminalでコード・差分・テスト結果を確認済み）：

- 新規作成：`uxsim/order_control_baseline_collector.py`、`tests_order_control_baseline_collector.py`
- `uxsim/uxsim.py`へ`W._order_control_baseline_collector = None`を追加（コメント1行＋初期化1行）
- 固定visit記録10項目、3索引（`_visit_records_by_primary_key`、`_visit_record_by_vehicle_name`、`_visit_records_by_node_name`）
- snapshot登録、B到着記録、通過前確認、通過後設定、Node別読取、固定visit1件読取
- `record_baseline_arrival`は固定集合外通知をpayload検証前に無視する最終処理順序へ修正済み
- 通過前確認と通過後設定を分離
- 新規単体テスト33件成功
- 既存テスト（`tests_order_control_rng.py`、`tests_order_control_current_visit_state.py`、`tests_order_control_current_visit_arrival.py`）および Level 2 body 22 tests 成功
- `python -m py_compile` および `git diff --check` 成功
- UXsimの到着・通過通知は未接続
- TVT制度、二段階観測、早期終了等は未実装
- 次は第2回実装（通知接続とUXsim接続テスト）

#### 2026-08-28：全World baseline collectorのUXsim通知接続と接続テスト

（上記「第1回実装完了」記録の続き。設計メモ **§25.21** を参照。）

Git状態（本記録時点）：

- ブランチ：`feature/intersection-order-control`
- 直前の保存済みコミット：`c2b36d6`
- コミット名：`Implement and document snapshot-fixed baseline visit records, arrival and passage handling, and collector tests`
- 直前コミットは`origin/feature/intersection-order-control`へpush済み
- 今回の変更は未コミット・未push
- 変更：`uxsim/uxsim.py`
- 新規：`tests_order_control_baseline_collector_uxsim.py`
- 未追跡ファイル：`diagnostics/order_control.zip`（今回触れていない）

実装内容（Terminalで差分・接続位置・テスト結果を直接確認済み）：

- B到着通知を`Vehicle.record_order_control_node_arrival()`へ接続
- BATCH、FCFS clearanceあり、通常`Node.transfer()`へ通過通知を接続
- 通過前`prepare_baseline_passage_recording()`と物理通過後`apply_baseline_passage_timestep()`を分離
- BATCHではservice queue整理後にapply
- 当初`uxsim.py`からcollector非公開索引`_visit_record_by_vehicle_name`を直接参照していたが、Terminal差分確認後に削除し、固定集合判定を`prepare_baseline_passage_recording()`へ集約
- collector無効時（既定`None`と明示`None`の2条件）で交通結果と`W.rng`・`W.order_control_rng`の状態が一致
- BATCH、FCFS、通常transferの3経路で固定集合外Vehicleを安全に処理
- BATCH不整合時に物理通過前に停止することを確認
- real_Wとfork_Wのcollector分離を確認
- 新規接続テスト11件成功
- 指定既存テスト群、Level 2 body 22 tests、構文確認、形式確認成功
- `grep -n '_visit_record_by_vehicle_name' uxsim/uxsim.py`は0件
- FCFS clearanceなしは未接続
- TVT制度、二段階観測、right_of_entry_vehicle選定、早期終了等は未実装
- 次は小規模fork診断とsnapshot固定集合構築用の最小補助処理を検討（§25.15の第3回実装相当。直ちに着手済みではない）

#### 2026-08-28：snapshot固定集合構築の具体設計とtimestep境界確認

（設計メモ **§25.22** を参照。Terminalによる実コード確認、小規模実測、Cursorへの訂正提示と再調査を経て確定した設計記録。実装は未着手。）

Git状態（本記録時点）：

- ブランチ：`feature/intersection-order-control`
- 直前の保存済みコミット：`bfb3933`（collector通知接続まで。`origin`へpush済み）
- 今回のメモ更新は未コミット・未push
- 未追跡ファイル：`diagnostics/order_control.zip`（触れていない）

確定した設計要点：

- Node集合は`set_order_control_for_nodes()`でtime_value設定時に得たNode一覧からNode名を一度だけ作り引き継ぐ。同じ集合を人が二度入力しない
- fork側ではNode名から`fork_W.get_node(node_name)`でfork自身のNodeを取得する
- 全対象Nodeを事前検証する。TVT対象は`order_control_eligible`かつ`order_control_type=="time_value"`のみ
- `none`は標準UXsim。signalized UXsimは独立したtypeではない
- snapshotは`fork_W.T == T`でtimestep T処理開始前（`W.T == T-1`解釈は誤り）。Tを1回処理後は`W.T == T+1`
- timestep T到着Vehicleはsnapshot時点でB。`baseline_arrival_timestep`はT、`was_arrived_at_snapshot`はFalse
- Aは正常なsnapshot境界ではincomingとinlinkの両方に存在。Aは`incoming_vehicles`から抽出
- Bは各`inlink.vehicles`から抽出。AがB走査で再び見つかるのは正常（Bとして重複登録しない）
- A未検出の到着済みinlink Vehicleは重大不整合（`ValueError`）
- 全候補を一時的な登録予定データ（dict list）へ作り、検証成功後にのみ`collector.register_snapshot_visit()`へ登録
- 第一候補：`uxsim/order_control_baseline_snapshot.py`の`register_snapshot_fixed_visits(fork_W, collector, *, target_node_names) -> int`

小規模実測（標準入力Python診断、ファイル変更なし）で確認：

- timesteps 0–9処理後`W.T==10`、timestep 10未処理
- timestep 10を1回処理後`W.T==11`
- 到着直後はincomingとinlinkの両方にVehicleが存在
- B登録Vehicleの`baseline_arrival_timestep==10`、`was_arrived_at_snapshot is False`
- 通過阻止後の正常exec終了時もincomingへ再登録され、inlink-only Aにはならない

次の作業：§25.22に従い`snapshot`補助処理と`tests_order_control_baseline_snapshot.py`を実装する（未着手）。

#### 2026-08-28：snapshot固定集合構築補助処理の実装・再レビュー・修正

（設計メモ **§25.23** を参照。§25.22の実装前設計に従い実装し、慎重な欠陥探索レビューとMajor相当2件の修正、Terminal最終確認を経た記録。）

Git状態（本記録時点）：

- ブランチ：`feature/intersection-order-control`
- 直前の保存済みコミット：`d09afe4`（`origin`へpush済み）
- 今回のコードとメモは未コミット・未push
- 未追跡ファイル：`uxsim/order_control_baseline_snapshot.py`、`tests_order_control_baseline_snapshot.py`、`diagnostics/order_control.zip`（zipには触れていない）

実装内容（新規2ファイル）：

- `uxsim/order_control_baseline_snapshot.py`
- `tests_order_control_baseline_snapshot.py`
- 既存ファイルは変更していない

公開関数：

- `register_snapshot_fixed_visits(fork_W, collector, *, target_node_names) -> int`
- fork Worldのsnapshot状態からTVT対象Nodeの固定visitを読み取り、collectorへ登録する

処理要点：

- TVT対象Node名を一括事前検証（`order_control_eligible`かつ`order_control_type=="time_value"`のみ）
- 到着済みVehicle（A）は各対象Nodeの`incoming_vehicles`から抽出
- 未到着Vehicle（B）は各`inlink.vehicles`をFIFO順に走査して抽出
- registration plan構築後、空の一時collectorへ全件登録し、collectorの正式`register_snapshot_visit()` validationを全件通過するか確認
- 全件成功後のみ、同じregistration planを実collectorへ登録
- 一時collectorのprivate索引は参照しない。一時collectorの内容を実collectorへコピーしない
- 正常なA再出現（同一Node・visit・inlinkの二重コンテナ）と異常な重複を区別
- 正常対象外Vehicle（end、abort、trip-end待ち、taxi、specified_route）は除外
- `participates_in_order_exchange=False`は交通予測のため含める

重複管理の修正経緯：

- 初回実装では未到着Vehicleまで`arrived_vehicle_names`へ加えており、別Node重複を黙ってスキップする可能性があった
- Terminal確認で検出し、`arrived_vehicle_names`（Aのみ）と`vehicle_name_to_planned_visit`（A/B全体）へ役割分離

レビュー後修正（Major相当2件）：

1. registration planにcollectorが拒否する値がある場合の実collector部分登録リスク → 一時collectorによる事前validationで防止
2. `get_node()`の予期しない例外までNode不存在に誤変換 → 現行`World.get_node()`のNode不存在メッセージ一致時のみValueErrorへ変換、それ以外は元例外を再送出

追加テスト：

- 通常`exec_simulation()`経路での到着済みVehicle（A）登録
- collector正式validation失敗時に実collectorが空のままであること
- Node不存在時の`__cause__`保持
- 予期しない`get_node`例外の非変換
- Bの別Node再出現が黙ってスキップされないこと（人工異常状態ではLink不一致で停止）

単体テスト：

- `tests_order_control_baseline_snapshot.py`：最終59件（`grep -c '^def test_'`と`grep -c '^    test_.*,$'`の両方が59。重複テスト名なし）
- 過去の54件・55件は途中時点または報告誤りであり、最終件数ではない

Terminal確認（すべて成功）：

- `python tests_order_control_baseline_snapshot.py`（59 tests）
- `python tests_order_control_baseline_collector.py`
- `python tests_order_control_baseline_collector_uxsim.py`
- `python tests_order_control_rng.py`
- `python tests_order_control_current_visit_state.py`
- `python tests_order_control_current_visit_arrival.py`
- `python tests_order_control_batch_revisit_integration.py`
- `python tests_order_control_batch_t_trigger_level_2_body.py`（22 tests）
- `python -m py_compile`（新規モジュール・テスト・collector・uxsim）
- `git diff --check`、新規2ファイルの`git diff --no-index --check`

欠陥探索レビュー結果：Critical 0、Major相当2（修正済み）、Minor 8（未対応分は正式driver設計時に再評価）

非空collectorについて残る制約：

- freshな空collectorに対して一度だけ呼ぶ前提
- 非空collectorや差し替えcollector実装固有の失敗については原子性を保証しない
- rollbackなし

未実装：正式driver、小規模fork診断の恒久ファイル、二段階観測、TVT制度処理、right_of_entry_vehicle選定、早期終了等

次の作業：小規模fork診断または最小driverの検討（§25.15第3回実装相当の残り。real_W→fork_W、collector設定、`register_snapshot_fixed_visits()`実行、fork進行、real_W不変確認、固定集合外Vehicle非追加確認）

#### 2026-08-29：snapshot固定集合の小規模fork統合診断

（設計メモ **§25.24** を参照。初回実装後のブロッカー修正、慎重な欠陥探索レビュー、outside Vehicle確認の補強、Terminal最終確認を経た記録。）

Git状態（本記録時点）：

- ブランチ：`feature/intersection-order-control`
- 直前の保存済みコミット：`ced04d5`（`origin/feature/intersection-order-control`へpush済み）
- 今回の診断ファイルとメモは未コミット・未push
- 未追跡：`diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`、`diagnostics/order_control.zip`（zipには触れていない）

診断ファイル：

- `diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`
- 回帰テストではなく、正式driver前の恒久統合診断
- real_W→fork_W、fork側のみcollector、`register_snapshot_fixed_visits()`、fork進行、baseline通知確認、固定集合外通知無視、real_W不変、参照分離
- TVT制度処理は実装しない

小規模World：

- 単一time_value Node（`orig --[in]--> junction --[out]--> dest`）、単車線、link長200・速度20、`SNAPSHOT_T=20`
- `set_order_control_for_nodes()`戻り値から`tvt_target_node_names`を一度だけ作成し引継ぎ

結果要点（Terminal最終確認）：

- 登録件数2
- A：arrival 10、passage 21
- B：arrival 21、passage 22
- outside：inlink進入・Node到着（timestep 30）・Node通過を通常経路で確認。到着・通過通知後もcollector非登録（export件数2のまま）
- real_W不変、参照分離、real outlink速度不変
- ブロッカー：初期実装の`VEHICLES_RUNNING`未登録・`x_next`不整合を修正。最終方式は`VEHICLES_RUNNING`登録＋診断用`user_function`で入口固定、fork側のみ解除。診断専用人工配置（標準Link進入非経由）
- fork 12 step、最終`fork_W.T==32`。ブロッカーは診断終了時`state=="end"`

再レビューと補強：

- 初回診断はoutsideがinlink進入だけで成功していた（到着・通過通知無視は未確認）
- 到着・通過後の主キーrecord不存在確認、進捗bool、終了条件を追加

Terminal確認（すべて成功）：

- `python diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`
- `python tests_order_control_baseline_snapshot.py`（59件）
- `python tests_order_control_baseline_collector.py`
- `python tests_order_control_baseline_collector_uxsim.py`
- `python -m py_compile`（診断・snapshot・collector・uxsim）
- `git diff --check`、新規診断ファイルの`git diff --no-index --check`

未確認：多Node、制御方式混在、二段階観測、TVT制度処理、性能等

次の作業：正式driver構造の設計（real_W/fork_W責任分離、collector設定、Node名引継ぎ、fork進行条件、baseline結果の受け渡し、real_W不変確認の範囲）

#### 2026-08-31：過去の会話記録からfull-World baseline早期終了設計を補修

- 情報源は、ユーザーが保存していた過去の M365 Copilot 会話記録 3 件（プロンプト 4、5、6）
- 時系列はプロンプト 4 → 5 → 6（古い → 新しい）
- 元ファイルは UXsim リポジトリ外のデスクトップにある
- Cursor は元ファイルを直接参照していない
- M365 Copilot が元ファイルを確認し、必要事項を本指示へ整理した
- Git 管理下の Markdown だけでは早期終了の詳細を十分確認できなかった
- 特にプロンプト 5 に詳細な早期終了設計が残っていた
- プロンプト 6 には collector と TVT 制度処理の責任分担が残っていた
- snapshot 固定集合、1 timestep 単位の進行、完全な timestep 境界での判定を記録した
- T から T+6 の意思決定窓、P 取得待ち、P 取得後の候補全員情報待ち（最新更新）を記録した
- Node 別完了状態、全 Node 集約による終了条件、horizon 終端時未解決を記録した
- collector は早期終了を判定しない
- 早期終了性能評価項目と未確定実装細部を記録した
- 詳細は設計メモ **§24.13.1 以降** を参照
- 初期正式 driver は固定 horizon 一括実行のまま
- Python 実装は変更していない
- テスト・診断は実行していない
- 本メモ更新は未コミット・未 push
- 最新保存済みコミットは `a6963aa` で origin へ push 済み
- `diagnostics/order_control.zip` には触れていない

#### 2026-08-31：正式全World baseline driverの実装前設計

- 正式 driver の最新設計を設計メモ **§25.25** へ記録した
- 初期 driver は固定 horizon 一括実行
- snapshot 固定集合 0 件は 0 step 正常終了
- horizon 内の情報不足は実行異常ではない
- 全固定 visit の通過完了を driver 成功条件にしない
- `P` 取得だけでは Node の baseline 情報取得完了ではない
- 候補 Vehicle 全員の必要情報を要求する
- 一部情報だけを使った部分的 TVT を禁止する
- 候補時間範囲を `P - 1` で固定し、再帰拡張しない
- 進行済み fork を後から延長しない
- World 作成時に baseline 用余白を確保する方向
- World 終端時に `simulation_terminated()` から `Analyzer.basic_analysis()` が実行されることを Terminal で確認した
- baseline 収集には不要な終了集計である
- 初期 driver は forward 終了後に 1 timestep 以上を残す
- World 終端ちょうどへの到達を許可しない
- 残り step 条件を次で確定した

```text
baseline_horizon_steps + 1 <= fork_W.TSIZE - fork_W.T
```

- 空固定集合は forward しないため、この余白検査を行わない
- World 作成時は最大 horizon に加えて 1 timestep 余白を確保する方向（`TSIZE >= T_evaluation_end + H_max + 1`、名称・境界は未確定）
- `T_evaluation_end` 等の名称・境界・評価設計は引き続き未確定
- result へ `target_node_names` を含める
- driver と後続制度処理の責任を分離する
- 早期終了の既存 §24.13 は今回変更していない
- 正式 driver の Python 実装と専用テストは未着手
- 次は正式 driver の実装前最終確認または実装指示作成
- 最新保存済みコミットは `b40cf23` で origin へ push 済み
- 本メモ更新は未コミット・未 push
- `diagnostics/order_control.zip` には触れていない

#### 2026-08-31：固定horizon正式driverの実装前残存設計を確定

- 関連コードと既存メモを読み取り、実装に必要な残存事項を確定した
- 最新正本は設計メモ **§25.25.28**
- 関数名は `run_snapshot_fixed_baseline_fork`
- `real_W` だけ positional。Node 一覧と horizon は keyword-only
- `real_W: World` 型注釈
- Node 一覧は `list` または `tuple` のみ。空 Node 一覧は入力エラー
- Node の意味的検証は snapshot へ委譲
- horizon は bool でない Python `int` で 1 以上
- horizon 余白不足は `ValueError`。入力・設定不整合は `ValueError`、内部不整合は `RuntimeError`
- copy、snapshot、forward の既存例外は原則伝播
- collector は copy 後の fork だけへ設定
- 登録直後と forward 後に件数照合
- 0 step 正常終了は **全対象 Node 合計** の登録件数が 0 の場合だけ。特定 Node だけ 0 件でも全体合計 ≥ 1 なら forward する
- 0 件時 result の各値と意味を確定した（§25.25.28.10、§25.25.28.16）
- 途中例外では部分 result を返さない
- `real_W` 軽量不変確認は正常終了時に行う。異常経路の `real_W` 不変は専用テストで確認
- result は既存 7 フィールド（非 frozen）
- snapshot docstring を実装時に明確化する（本体は変更しない）
- 新規 `uxsim/order_control_baseline_driver.py` と `tests_order_control_baseline_driver.py` を作成する
- `uxsim.py`、collector、`uxsim/__init__.py`、既存診断は変更しない
- 初期 driver は固定 horizon 一括実行のまま。早期終了は初期実装範囲外
- 次は driver 本体、専用テスト、snapshot docstring 修正の実装
- 最新保存済みコミットは `142d235`
- 本メモ更新は未コミット・未 push
- `diagnostics/order_control.zip` には触れていない

#### 2026-09-01：固定horizon正式driverを実装・検証・独立監査

- §25.25.28 に従って固定 horizon 正式 driver を実装した
- 新規 `uxsim/order_control_baseline_driver.py`（初回確認時 312 行。将来変わり得る）
- 新規 `tests_order_control_baseline_driver.py`
- `uxsim/order_control_baseline_snapshot.py` は **docstring のみ** 変更
- 公開 API：`OrderControlBaselineForkResult`（7 フィールド、非 frozen）、`run_snapshot_fixed_baseline_fork`
- `real_W` は変更せず `fork_W` だけ forward。collector は fork だけへ設定
- snapshot 登録は forward 前に 1 回（event list で `register` → `exec` を確認）
- 全対象 Node 合計 0 件だけ 0 step 正常終了。特定 Node だけ 0 件でも全体合計 ≥ 1 なら forward
- 全対象 Node 合計 0 件では余白不足でも 0 step 正常終了（`test_zero_total_registered_visits_skips_insufficient_margin_validation`）
- horizon 後の 1 timestep 余白：`baseline_horizon_steps + 1 <= TSIZE - T`
- `exec_simulation()` を 1 回だけ実行。早期終了なし
- 実行後に T 進行、World 終端、件数、`real_W` 不変を確認
- 途中例外時に result と部分 collector を返さない
- 初回専用テスト 56 件 → 初回レビュー後 60 件 → 独立監査後補修で **65 件**（すべて成功）
- 実装担当は Composer 2.5。独立監査は **同じ Cursor チャット内でモデルを Cursor Grok 4.6 へ変更**（新チャットではない）
- 独立監査は静的監査（過去の完了報告を根拠にせず §25.25.28 と実ファイルのみ照合）
- **Critical 問題なし、Major 問題なし**。本番 driver は §25.25.28 と一致
- Moderate 回帰テスト不足 Q1〜Q5 をコミット前に専用テストへ補強（本番 driver は変更していない）
- collector / snapshot / collector_uxsim 既存テスト、fork probe、py_compile、`git diff --check` 成功
- 現時点でコミットを妨げる Critical または Major 問題なし
- 詳細は設計メモ **§25.25.29**
- 次は差分と変更範囲の最終確認の後、同一コミットへ保存
- 最新保存済みコミットは `6d30a9f`（origin へ push 済み）
- 今回の実装・メモ更新は未コミット、未 push
- `diagnostics/order_control.zip` は未接触、コミット対象外

#### 2026-09-01：Node別TVT順位状態の実装前仕様を確定

- 正本は設計メモ **§25.25.30**
- **実装可能な仕様として確定したのは順位状態部品**であり、TVT 候補 Vehicle の選定・順位計算ではない
- 対象は確定順位ブロックと未確定 visit 集合
- 評価状態を分離（順位帳簿と評価制御情報を混在させない）
- 状態部品は制度判断を行わない
- 外部が決定した有序 VisitKey 列を保存する
- `K_confirmed_before` は先行確定（到着済み・先頭連続非参加）後に状態から再取得
- `K_confirmed_after` は最終確定列接続後の確定ブロック末尾
- 最終確定列には参加・非参加、取引順位、残余 baseline 順位が含まれ得る
- TVT 成立時の取引順位部分には、意思決定窓外の候補 visit が含まれ得る。状態部品は事前登録済みであれば意思決定窓内外を区別せず確定できる
- TVT 不成立の場合：先行確定後に残る意思決定窓内の未確定 visit が **1 件以上**あれば、baseline 順位による最終確定列を `K_confirmed_before` の後へ接続し、順位を確定する。残存 0 件なら接続対象の列は空である。空列の確定 API 呼出しは必須ではない。確定 API を呼ばずに処理を終了してよい。空列を渡した場合も no-op として正常に処理できる
- TVT 形成に必要な情報を取得できない場合：§14.4 に従い、先行確定後に残る意思決定窓内の未確定 visit が **1 件以上**あれば、baseline 順位による最終確定列を接続し、順位を確定する。残存 0 件なら接続対象の列は空である。空列の確定 API 呼出しは必須ではない。確定 API を呼ばずに処理を終了してよい。空列を渡した場合も no-op として正常に処理できる。意思決定窓外の未確定 visit は、情報未取得だけを理由に確定しない
- TVT 成立による窓外候補の確定と、情報未取得時の窓外非確定を区別する
- TVT 候補集合と最終確定 visit 列を作る制度処理は別途設計・実装が必要
- 意思決定窓内がすべて非参加の場合も専用アルゴリズムは設けない。意思決定窓内 baseline 順位の先頭から連続する非参加 visit を先行確定する共通処理を適用した結果、**意思決定窓内の全** visit が確定する。先行確定後の末尾を `K_confirmed_before` として再取得する。その後は**意思決定窓内に**未確定 visit と right_of_entry vehicle が存在しないため TVT を形成せず、後続の最終確定列は空であり、追加の確定順位列と制度処理上の `K_confirmed_after` を別途計算せずに処理を終了する。確定対象がないため `confirm_visits_in_order()` の呼出しは必須ではないが、空列を渡した場合も no-op として正常に処理できる。意思決定窓外の未確定 visit は残り得る
- 確定済み visit は状態存続中削除しない
- 独立クラス `OrderControlTvtNodeRankState` を将来の上位制御が Node 名別 dict で保持
- Node、World、`uxsim.py` へ今回は追加しない
- 状態は複数実 timestep をまたいで維持
- 実交通上の未確定 visit 登録タイミングは今回対象外
- VisitKey は `(vehicle_name, visit_id)`（collector / snapshot と同一）
- 公開 alias は `OrderControlTvtVisitKey`
- 状態クラスは `OrderControlTvtNodeRankState`
- 確定結果型は `OrderControlTvtConfirmResult`（frozen、3 フィールド）
- `confirmed_visit_keys` は採用しない
- 不採用理由：入力列との重複、不要な参照保持、コードの単純性と可読性
- mutable 通常クラスと list、dict、set を用いる
- `K_confirmed` は確定ブロック長から派生（別 mutable フィールドへ重複保存しない）
- 複数登録と一括確定は原子的更新（validation 失敗時は部分更新しない）
- 入力・要求不正は `ValueError`、内部不整合は `RuntimeError`
- 新規モジュール `uxsim/order_control_tvt_node_rank_state.py` と新規専用テスト `tests_order_control_tvt_node_rank_state.py` を予定
- 既存 baseline 関連コード（driver、collector、snapshot、`uxsim.py`）は変更しない
- 次は順位状態本体と専用テストの実装（それだけで TVT 候補順位計算が完成するわけではない）
- 最新保存済みコミットは `bd24ad1`（origin へ push 済み）
- 今回のメモ更新は未コミット、未 push
- `diagnostics/order_control.zip` は未接触、コミット対象外

#### 2026-08-29：TVT権利保有車両選定前の先頭非参加Vehicle先行確定の記録補修

- 過去に確定済みだった、意思決定窓内 baseline 到着順位の先頭に連続する非参加 Vehicle の先行確定が、設計メモに明文化されていなかった
- Terminal でリポジトリ内全 Markdown を検索し、処理順序の明示記載がないことを確認した
- 新 §4.5 を正本として処理順序を補修した（`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`）
- `n n p p n p n p p` の説明例を追加した
- 意思決定窓内 Vehicle がすべて非参加の場合は、全 Vehicle を baseline 到着順位のまま確定し、権利保有車両を選定せず、TVT 検討不要とすることを明記した
- 参加状態中立方式を維持し、参加・非参加を理由に同着順位の優劣を設けない
- 同着順位規則は、既到着未確定 Vehicle、意思決定窓内 Vehicle、意思決定窓外 TVT 候補 Vehicle に共通する
- §14.2 の `K_confirmed_before` を、既到着 Vehicle と先頭非参加 Vehicle の先行確定をすべて終えた後の確定順位ブロック末尾として整合させた（既到着の有無だけでは決めない）
- 意思決定窓内 Vehicle がすべて非参加の場合は、TVT による新たな順位列を接続しない
- 先頭非参加 Vehicle の先行確定後、それらを未確定範囲から除き、残る Vehicle の `baseline_rank` を 1 位から再構成することを明記した
- 全非参加時は先行確定だけで処理を終了し、`r_assigned` や `K_confirmed_after` を用いた TVT 順位列接続処理を行わないことを明記した
- §14.3 と §14.4 の既存確定範囲は変更していない
- 正式 driver 設計前の記録漏れ修復である
- 本記録時点では未コミット・未push
- 最新保存済みコミットは `3b3448f` で、origin へ push 済み
- `diagnostics/order_control.zip` には触れていない

### フェーズ4-6R設計目標（実装前・設計時点の記録）

（設計時点の目標。実装は上記フェーズ4-6R節・設計メモ **§1H.21** を参照。）

- BATCHのtrigger候補順位および関連参照先を current visit へ変更する
- `order_control_earliest_arrival_timesteps` の初回分析履歴化

### フェーズ4-6P設計調査記録（実装前・設計時点）

（設計時点の調査記録。実装は上記フェーズ4-6P節を参照。）

- Phase 4-6Oは commit `e3243e7` で完了
- 初回 tiebreaker は既存どおり `W.rng`
- 再訪 tiebreaker は独立 `order_control_rng`（`random_seed` から `SeedSequence` で派生）
- `W.rng` の既存乱数列は変更しない
- 詳細は設計メモ **§1H.19.1〜1H.19.6**

### フェーズ4-6設計議論：目的地Vehicle・比較対象Node・batch順序（設計確定、未実装）

設計メモ `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md` に正式反映済み。要点のみここに記録する。

#### 当面の研究シナリオ前提（実装ではなくシナリオ設計上の前提）

- 現行UXsimでは、`single_trip` Vehicleの `link.end_node == dest` の場合、通常のinter-link transfer requestとは異なるtrip-end処理経路を取る。
- したがって、比較対象内部交差点NodeをVehicleの目的地として使用しない。
- OD需要は原則としてネットワーク端点間に設定する。
- 標準UXsim、FCFS、BATCH、Time-value Transactionの比較では、ネットワークとOD需要を同一にする。
- この前提はBATCHだけに有利/不利な条件を置くためではなく、全比較方式で同一条件を維持するためである。

#### 保留した実装（将来課題）

以下は検討したが、現時点では実装しないことにした。

- `order_control_comparison_target` 属性
- 比較対象Node集合の共通管理setter/getter
- `validate_order_control_destination_assumptions()` 等の目的地前提自動検証
- `finalize_scenario()` / `exec_simulation()` への自動検証接続
- trip-end service unit

理由：比較Node選択方式がランダム選択以外は未実装であり、比較対象Node管理の共通層を今作ると過剰設計の可能性がある。当面は端点間ODでシナリオ側から回避可能。

#### 設計確定・未実装のBATCH候補・batch順序

- 候補包含条件：`recorded_earliest_arrival_timestep <= t_trigger`
- 候補はNode端到着済みだけでなく、全inlink上の未batch Vehicle
- `veh.state == "run"` を対象、`veh.v > 0` は条件にしない
- 同一inlink内は `inlink.vehicles` の物理FIFO順を維持（earliest arrivalや乱数で並べ替えない）
- trigger batch（trigger vehicleを含むinlink）を最初に処理
- その他inlink別batchの順序は、trigger到着時点のsnapshot estimated arrivalで決定（未実装）
- snapshot指標は `order_control_earliest_arrival_timesteps` とは別。tau_timestepsは加えない

## 現在までに追加した主なファイル

- tests_order_exchange_baseline.py
- tests_vehicle_research_attributes.py
- generate_vehicle_list_for_order_exchange.py
- tests_load_vehicle_list_to_uxsim.py
- tests_node_order_control_attributes.py
- tests_world_order_control_setters.py
- tests_order_control_eligibility.py
- tests_random_eligible_order_control.py
- tests_order_control_node_arrival_times.py
- ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md
- tests_fcfs_order_control_transfer.py
- tests_fcfs_order_control_behavior.py
- tests_fcfs_order_control_tiebreaker.py
- ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md
- tests_order_control_clearance_settings.py
- tests_fcfs_order_control_clearance_0.py
- tests_fcfs_order_control_clearance_1.py
- tests_fcfs_order_control_clearance_xyz.py
- tests_order_control_fcfs_vs_uxsim_standard_medium_network.py
  - corridor型 sanity check。コミット名には unsignalized と入っていないが、実態としては明示的信号制御なしのUXsim標準transferとの比較である。
- tests_order_control_fcfs_vs_uxsim_standard_grid_network.py
  - grid型 unsignalized UXsim standard transfer との比較。
- tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_network.py
  - grid型 signalized UXsim standard との比較（Step 4C：1000台）。
- tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py
  - high-demand grid型 signalized UXsim standard vs clearance-zero FCFS sanity check。
  - 5000台・10000台を0〜500 timestepに投入。
  - `clearance_timesteps=0` のFCFSを比較対象とする。
- tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand.py
  - high-demand grid型 signalized UXsim all-red vs clearance-one FCFS sanity check。
  - 5000台・10000台を0〜500 timestepに投入。
  - signalized側は `[60, W.DELTAT, 60, W.DELTAT]` の全赤付き4相信号。
  - FCFS側は `clearance_timesteps=1`。
- ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md
  - phase 4-6：BATCH Processing実装前正式設計メモ。
- tests_order_control_batch_earliest_arrival_timestep.py
  - phase 4-6A：`earliest_arrival_timestep` 記録の単体テスト。
- tests_order_control_batch_state_containers.py
  - phase 4-6B：BATCH状態コンテナの単体テスト。
- tests_order_control_batch_trigger_candidates.py
  - phase 4-6C：BATCH trigger候補識別ヘルパーの単体テスト。
- tests_order_control_batch_t_trigger_estimation.py
  - phase 4-6D：t_trigger Level 0/1推定の単体テスト（21テスト関数）。
- tests_order_control_batch_candidates_by_inlink.py
  - phase 4-6E：inlink別BATCH候補Vehicle抽出の単体テスト（22テスト関数）。
- tests_order_control_batch_candidate_group_ordering.py
  - phase 4-6F：trigger inlink優先・候補群順序付けの単体テスト（24テスト関数）。
- tests_order_control_batch_max_size_application.py
  - phase 4-6G：方向別最大batchサイズ適用の単体テスト（12テスト関数）。
- tests_order_control_batch_service_unit_registration.py
  - phase 4-6H：batch ID・assignment・service unit正式登録の単体テスト（18テスト関数）。
- tests_order_control_batch_formation_integration.py
  - phase 4-6I：BATCH形成統合メソッドの単体テスト（14テスト関数）。
- tests_order_control_batch_node_settings.py
  - phase 4-6J：`order_control_batch_t_trigger_level` とNode群一括設定の単体テスト（11テスト関数）。
- tests_order_control_batch_service_queue_transfer.py
  - phase 4-6K：登録済みservice queueに基づくVehicle実通過の単体テスト（33テスト関数）。

## uxsim/uxsim.py の主な変更

### Vehicleへの追加属性

- vot_true
- vot_declared
- payment_paid
- payment_received
- order_exchange_log
- participates_in_order_exchange
- order_control_node_arrival_times
- order_control_node_arrival_tiebreakers
- order_control_earliest_arrival_timesteps（phase 4-6A）
- order_control_batch_assignments（phase 4-6B）

Vehicleへの追加メソッド・処理：

- record_order_control_node_first_arrival(node) を追加
- order_control_node_arrival_times に、order-control対象Nodeへの初回到着時刻を記録する処理を追加
- order_control_node_arrival_tiebreakers に、初回到着時の固定tiebreaker値を記録する処理を追加
- record_order_control_earliest_arrival_timestep_for_current_link() を追加（phase 4-6A）
- Vehicle.update() 内で incoming_vehicles.append(s) の直後に初回到着時刻記録処理を呼ぶようにした

Vehicleの初回order-control Node到着記録：

- record_order_control_node_first_arrival(node) で、arrival_time と tiebreaker を初回のみ同時記録
- arrival_time は補正しない
- tiebreaker は s.W.rng.random() により生成
- 同一Vehicle・同一Nodeについて、arrival_time も tiebreaker も上書きしない

### Nodeへの追加属性

- order_control_type
- batch_size
- transaction_case
- order_control_eligible

Node.__init__(...) での追加チェック：

- order_control_eligible は bool のみ許可
- order_control_type!="none" の場合、order_control_eligible=True が必要
- order_control_type="none" は order_control_eligible=False でも許可

Nodeへの追加メソッド・処理：

- `transfer_fcfs_no_clearance()` を追加（フェーズ4-3の `transfer_fcfs()` を改名）
- `transfer_fcfs_clearance()` を追加（phase 4-5）
- `Node.transfer()` の冒頭に、`order_control_eligible=True` かつ `order_control_type=="fcfs"` の場合だけ `transfer_fcfs_clearance()` に分岐する処理
- `order_control_type="none"` のNodeでは標準 `Node.transfer()` の既存処理を維持

Node.transfer_fcfs_no_clearance()：

- クリアランスなしFCFS。回帰確認・デバッグ用。通常fcfs経路からは外れている
- FCFS候補Vehicleのソートキーは `(arrival_time, tiebreaker, veh.id)`

Node.transfer_fcfs_clearance()：

- クリアランスありFCFS。現在の通常fcfs経路で使用
- ソートキーは `(arrival_time, tiebreaker, veh.id)` を踏襲
- 異方向かつクリアランス未充足なら break、通過不能なら continue
- 通過成功後に `last_order_control_inlink` と `last_order_control_entry_timestep` を更新

Nodeへの追加属性（phase 4-5）：

- `order_control_clearance_timesteps`
- `last_order_control_inlink`
- `last_order_control_entry_timestep`

Nodeへの追加属性（phase 4-6B）：

- `order_control_batch_service_queue`
- `order_control_batch_next_id`

Nodeへの追加メソッド（Phase 4-6関連）：

- `get_order_control_batch_trigger_candidates()`（参照専用）
- `estimate_order_control_batch_t_trigger_level_0(trigger_vehicle)`（参照専用）
- `estimate_order_control_batch_t_trigger_level_1(trigger_vehicle)`（参照専用）
- 内部ヘルパー：`_validate_order_control_batch_t_trigger_inputs()`、`_compute_order_control_batch_base_trigger_timestep()`
- `Node.transfer()` のbatch分岐は **Phase 4-6Mで実装済み**（§1F）

### Worldへの追加属性

- order_control_eligibility_prepared
- order_control_clearance_timesteps（phase 4-5、デフォルト1）
- order_control_batch_tau_timesteps（phase 4-6A、デフォルト1）

### Worldへの追加メソッド

- set_order_control_for_nodes(...)
- infer_order_control_eligible_nodes(...)
- set_order_control_eligible_flag_for_nodes(...)
- set_order_control_for_randomly_selected_eligible_nodes(...)
- set_order_control_clearance_timesteps(clearance_timesteps)（phase 4-5）
- set_order_control_batch_tau_timesteps(tau_timesteps)（phase 4-6A）

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
- order_control_node_arrival_tiebreakers は、同時到着時の固定補助順位を保持する制御用状態である
- order_control_node_arrival_times への記録は、node.incoming_vehicles に入った時刻を到着時刻と定義する
- order_control_node_arrival_tiebreakers への記録は、初回到着時に s.W.rng.random() で生成した固定値とする
- 記録対象は order_control_eligible=True かつ order_control_type!="none" のNodeである
- 同じVehicle・同じNodeについて既に記録済みの場合は上書きしない
- arrival_time そのものは tiebreaker のために補正しない
- 現時点では node.name をキーにする
- 同一Vehicleが同一Nodeを複数回通る場合はキー設計の拡張が必要

### FCFS transfer 実装方針（ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md 参照）

- 標準 Node.transfer() は outlink起点、FCFSは Vehicle到着順起点として設計する
- フェーズ4-3で案A（クリアランスなしFCFS）の初期実装を完了した
- フェーズ4-3追加検証として、arrival-order behavior と blocked-outlink skip behavior の詳細検証テストまで追加済み
- フェーズ4-4で同時到着時の固定tiebreaker実装と検証テストまで追加済み
- フェーズ4-5設計として、案B（クリアランスありFCFS）の正式設計メモを追加済み
- フェーズ4-5実装として、クリアランスありFCFSの実装・接続・検証（Step 1〜Step 3D）まで完了済み
- 通常fcfs経路は `transfer_fcfs_clearance()` を呼ぶ。`transfer_fcfs_no_clearance()` は回帰確認・デバッグ用
- FCFS候補Vehicleのソートキーは `(arrival_time, tiebreaker, veh.id)` である
- 標準 Node.transfer() との共通ヘルパー化は行っていない。order-control系共通ヘルパー化は将来必要性が明確になった段階で検討する

### クリアランスありFCFS設計方針（ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md 参照）

- phase 4-5では、クリアランスありFCFSを実装・接続・検証した
- 研究上のFCFSモデルは、原則としてクリアランスありFCFSである
- クリアランスなしFCFS（`transfer_fcfs_no_clearance()`）は、検証用・デバッグ用・退避用として残す
- inlinkを方向代理変数とし、inlinkが異なれば異方向切替とみなす
- 異方向切替時には `clearance_timesteps` に基づく制約を課す
- 異方向かつクリアランス未充足のVehicleは、既存FCFSの通過可否判定を見る前に break する
- クリアランス不要またはクリアランス充足後に、既存FCFSの通過可否判定で通れないVehicleは continue できる
- `clearance_timesteps=0/1` の基本テストおよび X/Y/Z問題6テストで挙動を確認済み
- corridor型・grid unsignalized型・grid signalized型のsanity check（Step 4A〜4C）および高需要grid sanity check（Step 4D clearance=0、Step 4E clearance=1）でも極端な破綻は確認されなかった
- 標準UXsim挙動を壊さない方針は引き続き最重要である

### BATCH Processing設計・実装方針（ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md 参照）

- phase 4-6A〜4-6Jまで、BATCH準備データ・状態コンテナ・trigger候補識別・t_trigger推定（Level 0/1）・全inlink候補抽出・処理順決定・方向別N適用・正式登録・統合メソッド・Node群設定を実装済み
- **phase 4-6K：** `serve_order_control_batch_service_queue()` により、登録済みservice queueに基づくVehicle実通過を実装済み（commit `12e8eae`、単体）。新規Phase 4-6Kテスト1本（33テスト関数）
- **phase 4-6L：** `transfer_batch()` により、BATCH形成と実通過を各1回呼ぶ統括メソッドを実装済み（commit `e9f3ce9`）。新規Phase 4-6Lテスト1本（17テスト関数）
- **phase 4-6M：** `Node.transfer()` へのBATCH分岐接続、実シミュレーション時系列、Vehicle引継ぎ、N=1 BATCHとclearance付きFCFSの完全一致を実装・テスト済み（commit `b03538c`）。新規Phase 4-6Mテスト1本（13テスト関数）
- **phase 4-6N：** route_next_link参照順修正（`05fa2d1`）、clearance=0比較テスト3本（`f339b88`）、正式記録（`c06936c`）、診断スクリプト分離（`0e35799`）。Node訪問単位の共通状態設計は **§1H** に記録済み
- **phase 4-6O：** 現在訪問状態基盤（`e3243e7`）
- **phase 4-6P：** 到着記録・独立乱数（`b1b4d7f`・`b051c58`）
- **phase 4-6Q：** FCFSのcurrent visit参照（`7c3c6d3`・`9100803`）
- **phase 4-6R：** BATCH形成のcurrent visit参照（`cdd19be`・`30588a0`・`ae57e40`）
- **phase 4-6S：** BATCH assignmentの訪問対応（`5e26bc9`）
- **phase 4-6T：** 小規模BATCH再訪end-to-end統合（`b7159f9`）
- **phase 4-6U：** high-demand再実行・検証完了（§1H.24。本体変更なし）
- **phase 4-6W：** 模倣World型Level 2 t_trigger参照モデル確立（**§1H.26**。参照モデル・専用テスト実装・独立レビュー完了。commit IDはGit履歴参照）
- **phase 4-6Y：** Level 2本体接続・実ネットワーク検証・N=1一致性確認・mimic World性能修正・5,000/10,000台追加検証（**§1H.27.42〜§1H.27.45**。開始 `6e6a601`、記録作成前HEAD `8dc83d9`）
- **現時点の主要課題：** Time-value Transactionの設計・実装（Phase名・実装範囲は未決定）。BATCH残作業は§1H.27.46へ整理済み。複数seed、別network、Vehicle別・Node別分析、統計的検定は共通評価段階へ繰り越し。BATCH固有のN・horizon感度分析は保留。**Level 2 mimic TMAX short 化は 2026-08-24 に正式反映済み**（設計メモ §23）。`World.copy()` 軽量化は未着手
- フェーズ4-6Y完了：Level 2本体接続、fallback、4カウンター、未到着route修正、5,000/10,000台L1/L2（h=30・h=50）、200/1,000/5,000/10,000台N=1一致性、Analyzer省略、指定条件horizon 30対50限定比較、5,000台補正signalized UXsim。virtual horizon 30を暫定維持（正式値・最適値ではない）。Time-value Transactionは未実装。trip-end Vehicleは現在の研究対象外
- `earliest_arrival_timestep` はリンク進入時に記録し、候補包含条件に使用する（実装済み）
- `t_trigger` Level 0/1推定は参照専用ヘルパーとして実装済み。計算式に `W.T` は含めない
- Level 2は研究上の通常推定方式。**本体接続済み**（`6e6a601`、§1H.27.42）。Phase 4-6W参照モデル（§1H.26）は本体接続前の比較基準
- snapshot estimated arrivalによるinlink別batch間順序決定は phase 4-6F で実装済み
- **batch_sizeの基本値：** 10（`set_order_control_for_nodes()` で明示指定。Node既定値は1）
- **t_trigger推定の研究基本設計：** 通常方式はLevel 2。Level 2でunresolvedの場合はLevel 1へfallback。Level 2本体接続済み（§1H.27.42）
- **現時点の暫定比較設定：** `order_control_batch_t_trigger_level=1`（Level 1比較用。研究の通常方式はLevel 2）
- 当面の研究シナリオでは、比較対象内部交差点Nodeを目的地としない端点間ODを使用する
- 比較対象Node共通管理・目的地自動検証は将来課題として保留
- 次工程：Time-value Transactionの設計・実装（Phase名・実装範囲は未決定）。BATCH単独の追加探索はいったん停止。BATCH暫定ベースラインは§1H.27.46参照
- 詳細設計・判断経緯は ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md **§1C**（形成・登録）、**§1D**（実通過）、**§1E**（統括）、**§1F**（`Node.transfer()` 接続）、**§1G**（比較・診断）、**§1H**（訪問状態設計）を参照

### テスト追加方針

- 新しい挙動テストを追加する際も、まずはテストのみを追加し、uxsim/uxsim.py を勝手に変更しない方針を維持する

### GitHub運用

- feature/intersection-order-control ブランチは origin/feature/intersection-order-control とtracking済み
- 重要な区切りごとに git push して GitHub へ退避する
- 現時点では HTTPS + PAT による認証。長期運用では SSH 移行を検討する余地がある

## 次に進む予定

> **更新注記（2026-08-24）：** 以下は §1H.27.46 整理時点の予定を含む。Level 2 short TMAX 正式反映および TVT 向け全World baseline 性能基盤確認は実施済み（設計メモ `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§23**）。次の本体作業は TVT 制度ロジックと baseline 情報設計。

**BATCH関連（§1H.27.46）：**

- BATCH基本実装、Level 2接続、主要診断、N=1一致性は指定条件で確認済み
- Time-value Transaction開始前に必要な既知BATCH修正は現時点でない
- BATCH単独の追加探索はいったん停止。virtual horizon 30を暫定維持
- 複数seed、別network、Vehicle別・Node別分析、統計的検定はTime-value Transaction実装後の共通評価へ繰り越す
- BATCH固有課題（N感度、horizon探索、Level 2追加性能改善等）は§1H.27.46参照（**2026-08-24 追記：** short TMAX 反映済み。copy 軽量化は未着手。設計メモ §23）

**次の本体対象：**

- Time-value Transactionの設計・実装（Phase名、詳細区分、実装範囲は未決定）
- **2026-08-24：** Level 2 short TMAX 正式反映済み。TVT 向け全World baseline の性能基盤確認済み（設計メモ §23）。次は TVT 制度ロジックと baseline 情報設計

**完了済み（フェーズ4-6Y）：**

- Level 2本体接続（`6e6a601`、§1H.27.42）
- unresolved時のLevel 1 fallback、Level 2の4カウンター
- 未到着Vehicle route状態修正（`af0e037`、§1H.27.43）
- 5,000台・10,000台Level 1対Level 2比較（h=30・h=50、§1H.27.43・§1H.27.45）
- N=1 BATCH Level 2対FCFS診断：200台・1,000台・5,000台・10,000台（§1H.27.44・§1H.27.45）
- mimic World Analyzer省略による性能修正（`639444f`、§1H.27.44）
- 5,000台・10,000台N=1 BATCH Level 2対FCFS一致性確認（`exact_match`、§1H.27.45）
- 指定条件でのvirtual horizon 30対50限定比較（§1H.27.45）
- 5,000台補正signalized UXsim比較（§1H.27.45）

**未実施（フェーズ4-6Yの試験・評価）：**

- 複数seed、別network → Time-value Transaction実装後の共通評価へ繰り越し（§1H.27.46）
- 体系的horizon感度分析（30・50以外） → BATCH固有課題として保留（§1H.27.46）
- Vehicle別・Node別分析 → 共通評価へ繰り越し（§1H.27.46）
- Level 2仮想計算本体の追加性能改善 → 必要性確認後（§1H.27.46）。**2026-08-24 追記：** short TMAX 正式反映により mimic 構築コストは大幅短縮済み（設計メモ §23）。`World.copy()` 軽量化は未着手・後回し（§23.14）

**後続実装・保留：**

- Time-value Transaction（次の本体対象。Phase名・実装範囲は未決定）
- stale service unit対応は必要性が低ければ保留
- assignment全訪問履歴は後回し
- trip-end Vehicleは**現在の研究対象外**（将来研究対象を拡張する場合の課題）

**記録作成前HEAD：** `8dc83d9`（診断スクリプト2本とMarkdown3本は未コミット）

現在の進捗（過去フェーズの詳細）：

- phase 4-5では、クリアランスありFCFSの実装・接続・基本検証・X/Y/Z問題検証まで完了済み。
- Step 4A〜4Eとして、FCFS sanity check比較を追加済み。
- phase 4-6A〜4-6M：BATCH形成〜`Node.transfer()` 接続まで実装・commit済み（4-6Mは `b03538c`）。
- **phase 4-6N（commit済み）：**
  - `05fa2d1`：route_next_link参照順修正
  - `f339b88`：clearance=0比較テスト3本
  - `c06936c`：比較結果・Node再訪診断の正式記録
  - `0e35799`：診断スクリプトを `diagnostics/order_control/` へ分離
- **phase 4-6N Step 5：** Node訪問単位の共通状態設計を **§1H** に記録済み。基盤（4-6O）・到着記録（4-6P）・FCFS参照先変更（4-6Q）は実装済み
- clearance=0ではBATCHとFCFSはほぼ同等（medium ratio 1.0003、grid ratio 1.0006）
- high-demand BATCH比較は、5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースをPhase 4-6Uで実行・検証完了（§1H.24）
- Phase 4-6N当時の最新commit：`0e35799`（診断スクリプト分離）
- Phase 4-6Q：commit `7c3c6d3`・`9100803` で完了
- Phase 4-6R：commit `cdd19be`・`30588a0`・`ae57e40` で完了
- Phase 4-6S：commit `5e26bc9` で完了
- Phase 4-6T：commit `b7159f9` で完了

次工程（設計メモ **§1H.17**）：

1. route_next_link確認順修正 — **完了**（`05fa2d1`）
2. clearance=0比較3本 — **完了**（`f339b88`）
3. 正式Markdown記録 — **完了**（`c06936c`）
4. 診断スクリプト分離 — **完了**（`0e35799`）
5. Node訪問単位の状態設計 — **完了**（**§1H**、commit `7c35335`）
6. §1H設計レビュー — **完了**
7. 実コード・既存テスト調査 — **完了**
8. Phase 4-6O実装・テスト — **完了**（`e3243e7`）
9. Phase 4-6P実装・テスト — **完了**（`b1b4d7f`・`b051c58`）
10. FCFSの参照先変更（Phase 4-6Q） — **完了**（`7c3c6d3`・`9100803`）
11. BATCH形成の参照先変更（Phase 4-6R） — **完了**（`cdd19be`・`30588a0`・`ae57e40`）
12. BATCH assignmentの訪問対応（Phase 4-6S） — **完了**（`5e26bc9`）
13. 小規模BATCH再訪end-to-end統合（Phase 4-6T） — **完了**（`b7159f9`）
14. Phase 4-6Uとしてhigh-demand再実行・既知prefix violationの実ネットワーク再確認 — **完了**（§1H.24）

その後の後続フェーズ候補：

- Time-value Transactionの設計・実装（次の本体対象。Phase名・実装範囲は未決定）
- 複数seed、別network、Vehicle別・Node別分析、統計的検定（共通評価段階。§1H.27.46）
- BATCH固有のN・horizon感度分析、Level 2追加性能改善（保留。§1H.27.46）。**2026-08-24 追記：** short TMAX 反映済み。copy 軽量化は未着手（設計メモ §23.14）

後続実装・保留：

- stale service unit対応は必要性が低ければ保留
- assignment全訪問履歴は後回し
- trip-end Vehicleは現在の研究対象外（将来研究対象を拡張する場合の課題）

将来課題（設計確定・未実装）：

- 比較対象Node集合の独立管理（`order_control_comparison_target` 等）
- 目的地前提の自動検証
- trip-end Vehicleを含むservice unit設計
- Time-value Transaction、支払い処理

## 新しいチャットで再開する場合

新しいチャットでは、以下を伝える。

- ORDER_EXCHANGE_PROGRESS.md を読んでください
- ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md を読んでください（**§1H** を優先参照。診断は **§1G**）
- ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md を読んでください
- tests_order_control_batch_earliest_arrival_timestep.py を読んでください
- tests_order_control_batch_state_containers.py を読んでください
- tests_order_control_batch_trigger_candidates.py を読んでください
- tests_order_control_batch_t_trigger_estimation.py を読んでください
- tests_order_control_batch_candidates_by_inlink.py を読んでください
- tests_order_control_batch_candidate_group_ordering.py を読んでください
- tests_order_control_batch_max_size_application.py を読んでください
- tests_order_control_batch_service_unit_registration.py を読んでください
- tests_order_control_batch_formation_integration.py を読んでください
- tests_order_control_batch_node_settings.py を読んでください
- tests_order_control_batch_service_queue_transfer.py を読んでください
- tests_order_control_batch_transfer.py を読んでください
- tests_order_control_batch_node_transfer_integration.py を読んでください
- tests_order_control_batch_vs_fcfs_vs_uxsim_standard_medium_network.py を読んでください
- tests_order_control_batch_vs_fcfs_vs_uxsim_standard_grid_network.py を読んでください
- tests_order_control_batch_vs_fcfs_vs_signalized_uxsim_standard_grid_network.py を読んでください
- tests_fcfs_order_control_clearance_0.py を読んでください
- tests_fcfs_order_control_clearance_1.py を読んでください
- tests_fcfs_order_control_clearance_xyz.py を読んでください
- tests_order_control_fcfs_vs_uxsim_standard_medium_network.py を読んでください
- tests_order_control_fcfs_vs_uxsim_standard_grid_network.py を読んでください
- tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_network.py を読んでください
- tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py を読んでください
- tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand.py を読んでください
- 現在のブランチは feature/intersection-order-control です
- feature/intersection-order-control ブランチは origin/feature/intersection-order-control とtracking済みで、GitHubへpush済みです
- 現在の通常fcfs経路は `transfer_fcfs_clearance()` を呼ぶ
- `transfer_fcfs_no_clearance()` は回帰確認・デバッグ用に残っている
- Phase 4-6A〜4-6Mまで完了（実装・テスト・commit済み。4-6Mは `b03538c`）
- Phase 4-6N（commit済み）：`05fa2d1`、`f339b88`、`c06936c`、`0e35799`
- Phase 4-6O：`e3243e7` 完了
- Phase 4-6P：`b1b4d7f`・`b051c58` 完了
- Phase 4-6Q：`7c3c6d3`・`9100803` 完了
- Phase 4-6R：`cdd19be`・`30588a0`・`ae57e40` 完了
- Phase 4-6S：`5e26bc9` 完了
- Phase 4-6T：`b7159f9` 完了
- Phase 4-6U：high-demand再実行・検証完了（§1H.24）
- Phase 4-6W：模倣World型Level 2 t_trigger参照モデル確立（**§1H.26**。参照モデル・専用テスト実装・独立レビュー完了）
- Phase 4-6Y：Level 2本体接続・実ネットワーク検証・N=1一致性確認・mimic World性能修正・5,000/10,000台追加検証・BATCH残作業整理とTime-value Transaction移行判断（**§1H.27.42〜§1H.27.46**。開始 `6e6a601`）
- **現在の最新コミット：** `66e4b11` Phase 4-6Y: Document 5,000/10,000-vehicle BATCH-related comparisons across levels, Level 2 horizons, signalized UXsim, and FCFS
- **直前の診断スクリプトコミット：** `c8107f3` Phase 4-6Y: Extend grid diagnostics for 5,000/10,000 vehicles and Level 2 horizons 30/50
- **`66e4b11`までorigin/feature/intersection-order-controlへpush済み**
- **今回のBATCH残作業整理Markdown 2ファイルは未コミット**
- **現時点の主要課題：** Time-value Transactionの設計・実装（Phase名・実装範囲は未決定）。BATCH残作業は§1H.27.46へ整理済み。複数seed、別network、詳細分析は共通評価段階へ繰り越し
- フェーズ4-6Y完了：Level 2本体接続（`6e6a601`）、5,000/10,000台Level 1対Level 2（§1H.27.43・§1H.27.45）、200/1,000/5,000/10,000台N=1 BATCH Level 2対FCFS（§1H.27.44・§1H.27.45）、指定条件horizon 30対50限定比較、5,000台補正signalized UXsim。virtual horizon 30を暫定維持。BATCH単独の追加探索はいったん停止
- trip-end Vehicleは現在の研究対象外。stale service unit・assignment全訪問履歴は後続保留
- Node再訪はBATCH固有ではない（signalized全期間42.7%、FCFS 23.0%）
- high-demand BATCH比較は、5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースをPhase 4-6Uで実行・検証完了（U1〜U3すべてexit 0、prefix violationなし。10,000台・clearance=0は未実行）
- 次工程：Time-value Transactionの設計・実装（Phase名・実装範囲は未決定）。BATCH単独の追加探索はいったん停止。BATCH暫定ベースラインは§1H.27.46参照
- ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md の **§1H** を優先参照。Phase 4-6Q実装記録は **§1H.20**、Phase 4-6R実装記録は **§1H.21**、Phase 4-6S実装記録は **§1H.22**、Phase 4-6T実装記録は **§1H.23**、Phase 4-6U実行記録は **§1H.24**、Phase 4-6W参照モデル記録は **§1H.26**、Level 2本体接続は **§1H.27.42**、Level 2未到着Vehicle修正・5,000台Level 1対Level 2は **§1H.27.43**、N=1 BATCH Level 2対FCFS・Analyzer省略は **§1H.27.44**、5,000/10,000台追加検証は **§1H.27.45**、BATCH残作業整理とTime-value Transaction移行判断は **§1H.27.46**
- 次に読む実装：`Vehicle.order_control_current_visit`、`current visit` の `batch_assignment`、`Vehicle.get_order_control_batch_assignment()`、`Vehicle.has_order_control_batch_assignment()`、`Vehicle.assign_order_control_batch_to_current_visit()`、`Vehicle.order_control_batch_assignments`、`Node.get_order_control_batch_trigger_candidates()`、`Node.get_order_control_batch_candidates_by_inlink()`、`Node.register_order_control_batch_service_units()`、`Node.serve_order_control_batch_service_queue()`、`Node.transfer_batch()`、`Node.transfer()`
- 次に読むテスト：`tests_order_control_batch_revisit_integration.py`、`tests_order_control_batch_visit_assignment.py`、`tests_order_control_batch_revisit_ranking.py`、`tests_order_control_batch_service_unit_registration.py`、`tests_order_control_batch_service_queue_transfer.py`、`tests_order_control_batch_transfer.py`、`tests_order_control_batch_node_transfer_integration.py`
- 診断スクリプト（`diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py`、`diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py`、`diagnostics/order_control/README.md`）は通常回帰ではなくhigh-demandでの既知問題の再確認資料として参照
- 目的地Vehicleの扱いは端点間OD前提で保留。比較対象Node共通管理・目的地自動検証は将来課題
- 一時退避PDF `phase4-6A_batch_earliest_arrival_timestep_memo.pdf` はリポジトリ外。正式Markdownを優先参照
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md、ORDER_EXCHANGE_RESEARCH_CONTEXT.md、ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md も必要に応じて参照してください
- git log --oneline -20 と git status の結果を貼ります
- GitHub運用は現在 HTTPS + PAT。将来的にSSH移行を検討する余地があります
