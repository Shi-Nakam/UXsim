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
- TVT 成立時の取引順位部分には、意思決定窓外の候補 visit が含まれ得る。状態部品は順位未確定集合に事前登録済みであれば意思決定窓内外を区別せず確定できる
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

#### 2026-09-02：Node別TVT順位状態を実装・検証し、独立監査後補強とCopilot確認まで完了

- 正本は設計メモ **§25.25.31**。実装前仕様は **§25.25.30**
- 新規本番ファイル：`uxsim/order_control_tvt_node_rank_state.py`
- 新規専用テスト：`tests_order_control_tvt_node_rank_state.py`
- 公開型：`OrderControlTvtVisitKey = tuple[str, int]`。状態クラス：`OrderControlTvtNodeRankState`
- `OrderControlTvtConfirmResult` は frozen、3 フィールド（`k_confirmed_before`、`k_confirmed_after`、`newly_confirmed_count`）。`confirmed_visit_keys` なし
- **確定する順番どおりに並べた VisitKey の list または tuple**を受け取り、入力順がそのまま確定順位になる。sort しない
- 原子的更新（下書き帳簿検査後に本物をまとめて置換）。`ValueError` 時・`RuntimeError` 時ともに正式状態不変
- `export_state()` は 4 キー（`node_name`、`k_confirmed`、`confirmed_visits`、`undetermined_visits`）。未確定は `vehicle_name`・`visit_id` の 2 段階 sort
- 意思決定窓外 visit も順位未確定集合に事前登録済みなら確定可能。候補選定や順位計算は未実装
- `uxsim.py`、baseline driver、collector、snapshot、`uxsim/__init__.py`、既存テスト、既存診断は変更していない

**専用テスト：**

- 初回実装完了時 **52 件**成功
- **Cursor Grok 4.6** による静的独立監査（同じ Cursor チャット内でモデル切替。新チャットではない）。Critical なし、Major なし、Moderate 2 件
- 独立監査後も**本番コード変更なし**。監査後に専用テスト 2 件を追加 → **54 件**
  - `test_confirm_runtime_error_during_candidate_verification_leaves_state_unchanged`
  - `test_export_undetermined_visits_sorts_same_vehicle_by_visit_id`
- **Copilot 自身**も本番コード全文と専用テスト全文を Terminal 表示で確認（Cursor や Grok の報告だけを直接確認と同一視しなかった）
- Copilot 確認で `test_confirm_leaves_state_unchanged_when_middle_key_already_confirmed` のテスト名と入力位置の不一致を 1 件発見。確定済み visit を 3 件中の 2 件目へ移して補強。補強後も専用テスト **54 件**成功
- TESTS 一覧 54 件。AST 照合で漏れ・余分・重複なし

**既存回帰テストと診断（初回実装・監査後補強時に実施）：**

- collector、snapshot、baseline driver（65 件）、collector_uxsim、fork probe、py_compile、`git diff --check` 成功
- Copilot 確認後の既存 1 件補強では本番コード未変更のため、既存回帰テストと診断は再実行せず専用テストのみ再実行

**Git 状態：**

- 最新保存済みコミットは **`f2c87a0`**（origin へ push 済み）
- 今回の 4 ファイル（本番、専用テスト、設計メモ、進捗メモ）は未コミット、未 push
- `diagnostics/order_control.zip` は未接触、コミット対象外
- 次はコミット前最終確認（差分確認、メモとの照合、コミット）

#### 2026-09-03：非参加VehicleなしTVT取引順位計算の中間設計を記録

- 正本参照先は設計メモ **§25.25.32**
- まだ**中間設計**であり、実装前仕様は未完成
- 今回の対象は**非参加 Vehicle なし**の**一候補分**の順位計算（候補生成ではない）
- collector は baseline 情報源として使用する。§11 関数は collector へ直接依存しない
- `baseline_order` を唯一の baseline 順位入力とする。`baseline_rank` は内部派生
- inlink 別物理順は候補生成側で別途扱う
- `buyers` は候補生成済みの一候補分。関数内部で `baseline_order` に従い `buyers_sorted` を作る
- 買い手間・売り手間の baseline 相対順を**確実に**維持する
- 売り手は自分より baseline で後ろにいた買い手数だけ後退（§11.3・§11.6）
- 結果へ含める 5 項目：`buyers_sorted`、`sellers_sorted`、`last_buyer_rank`、`trade_rank`、`trade_order`
- 結果へ含めない 3 項目：`baseline_order`、`baseline_rank`、`trade_scope`
- 合意した命名：`OrderControlTvtNoNonparticipantTradeRankResult`、`build_tvt_trade_rank_without_nonparticipants`
- 結果型の具体構造、FIFO 境界は未確定
- 残る検討は 4 項目（結果型、例外、FIFO 境界、専用テスト契約）
- 将来の非参加あり一般形が非参加 0 件を包含する可能性は**推測**であり未確定
- 最新保存済みコミットは **`88cfc05`**（origin へ push 済み）
- `diagnostics/order_control.zip` は未接触、対象外
- コード変更なし

**2026-09-03 追記（結果型の最終構造確定）：**

- 結果型の最終構造を **§25.25.32.16** で確定
- 専用通常クラス（`OrderControlTvtNoNonparticipantTradeRankResult`）。通常の公開 API から読取専用
- 内部順位 dict（`_trade_rank_by_visit_key`）は防御コピー。mutable な順位 dict を直接公開しない
- `assigned_rank()` で特定 visit の順位を取得。結果に存在しない VisitKey は `None` ではなく `ValueError`
- `trade_rank_items()` で順位順の変更不能 tuple を取得
- 公開列（`buyers_sorted`、`sellers_sorted`、`trade_order`）は tuple。更新用公開メソッドなし
- `export_state()` / `to_dict()` は初期実装へ追加しない
- 第 1 項目「結果型の最終構造」完了。残る検討は 3 項目。次は例外と内部不変条件

**2026-09-03 追記（例外と内部不変条件確定）：**

- 例外と内部不変条件を **§25.25.32.17** で確定
- 入力契約違反は `ValueError`、計算後の重大な内部不整合は `RuntimeError`
- FIFO 違反は `RuntimeError` にしない
- 入力確認後、ローカル変数だけで順位を計算。内部整合確認成功後に結果オブジェクトを一度だけ作る
- 失敗時は結果オブジェクトを返さない。部分的な結果を返さない
- 既存の順位帳簿、collector、World、Node、Vehicle は変更しない。rollback 処理は不要
- 合意済みの売り手後退式も内部確認対象
- 第 2 項目「例外と内部不変条件」完了。残る検討は 2 項目。次は FIFO 検査との責任境界

**2026-09-03 追記（FIFO検査との責任境界確定）：**

- FIFO 検査との責任境界を **§25.25.32.18** で確定
- 順位計算と FIFO 検査は分離（別公開関数）
- FIFO 検査範囲は `trade_scope`（未確定範囲全体を検査する案は不採用）
- 取引前は `trade_scope`、取引後は `trade_order` 先頭から `last_buyer_rank` 件
- 検査対象 inlink は `trade_scope` から特定。inlink 情報は上位処理が渡す
- 順位計算結果型へ inlink 情報を追加しない
- FIFO 維持は `True`、FIFO 違反は `False`（正常な候補棄却。例外ではない）
- 同じ候補の順位を作り直さない。確定順位ブロックとの接続部は追加検査しない
- 棄却数・棄却率などは上位評価・診断側
- 第 3 項目「FIFO 検査との責任境界」完了。残る検討は専用テスト契約と実装配置だけ。次の直接作業も同項目

**2026-09-03 追記（専用テスト契約と完成実装前仕様）：**

- 最後の残作業を **§25.25.32.19** で確定
- 本番モジュール `uxsim/order_control_tvt_trade_rank.py`、専用テスト `tests_order_control_tvt_trade_rank.py`
- 公開クラス `OrderControlTvtNoNonparticipantTradeRankResult`、順位計算 `build_tvt_trade_rank_without_nonparticipants`、FIFO `preserves_inlink_fifo`
- VisitKey 型は既存モジュールから共有。private helper は共有しない
- NumPy 整数拒否。余分な inlink 情報は無視
- 複数 inlink のうち 1 本でも逆転なら `False`
- 内部異常時に壊れた結果を返さないテスト（少なくとも 1 件は公開関数経由）
- **§25.25.32.20** を自己完結型の唯一の最新実装正本として追加
- 実装者は中間記録から推測しない。全設計項目完了
- Python コードは未変更。次は実装前の最終照合
- 最新保存済みコミット **`88cfc05`**。Markdown 2 ファイルは未コミット・未 push。ZIP 未接触・対象外

**2026-09-03 追記（コンストラクター契約補修）：**

- Copilot 確認でコンストラクター契約不足を発見。**§25.25.32.20** を補修
- キーワード専用コンストラクター、列は tuple として保持、順位 dict は防御コピー
- コンストラクターは最低限の型・形式確認。完全な内部整合確認は構築前 helper の責任
- `sellers_sorted` の空 tuple を認める
- 結果型固有テストでは直接構築可。順位計算テストは公開関数経由
- 次は補修後の完成仕様再確認。Python コードはまだ変更していない

- 次は補修後の完成仕様再確認。Python コードはまだ変更していない

#### 2026-09-03：非参加VehicleなしTVT取引順位計算とFIFO検査を実装

- 正本参照先は設計メモ **§25.25.33**（実装結果）。実装前仕様は **§25.25.32.20**
- 新規本番モジュール `uxsim/order_control_tvt_trade_rank.py`
- 新規専用テスト `tests_order_control_tvt_trade_rank.py`
- 公開結果クラス `OrderControlTvtNoNonparticipantTradeRankResult`
- 公開順位計算関数 `build_tvt_trade_rank_without_nonparticipants`
- 公開 FIFO 関数 `preserves_inlink_fifo`
- `baseline_order` から `baseline_rank` を内部生成
- `buyers_sorted[-1]` から最後の買い手を取得（`max(...)` 生成式は使用しない）
- 売り手後方買い手数は明示的 for ループ（`sum(...)` 生成式は使用しない）
- 売り手後退式：売り手 baseline 順位 + 後方買い手数
- 取引範囲外 visit の baseline 順位不変
- 結果クラスの防御コピー、キーワード専用コンストラクター、tuple 専用入力契約
- 外部入力不正は `ValueError`、内部不整合は `RuntimeError`、FIFO 違反は `False`
- FIFO 検査は順位計算と別公開関数
- 専用テスト **115 件**成功。`TESTS` 登録 115 件、一意 115 件。AST による一覧確認あり
- 指定した既存回帰テストすべて成功。fork probe 成功
- Copilot の実ファイル確認で見つけた仕様不一致（list 誤受理、内部順位の例外区分）と可読性上の問題を修正
- テストが別の異常で先に停止する問題を修正（売り手後退式・取引範囲外の狙い撃ち検証）
- 不足していたコンストラクター契約テストと FIFO `trade_order` 重複テストを追加
- **独立静的監査は実施していない。** Copilot 直接確認と全テスト結果を踏まえ、追加効果が限定的と判断して今回は省略した（**§25.25.33.15**）
- 候補生成側は未実装。TVT 全体として全候補を評価可能な状態ではない
- 既存 Python、既存テスト、既存診断は未変更
- `diagnostics/order_control.zip` は未接触・対象外
- 最新保存済み・push 済みコミットは **`050d3c9`**（実装前仕様）
- 新規 Python 2 ファイルと Markdown 2 ファイルは未コミット
- 次は **§25.25.33** と本進捗記録の確認、変更対象 4 ファイルの確認、メモを含む `document` コミット

#### 2026-09-05：TVTの三つの計算世界と局所候補未解決時の扱いを整理

詳細正本は設計メモ **§25.25.34**。以下は要点。将来の実装で必要な処理関係、場合分け、誤解の訂正、未確定事項の詳細は **§25.25.34** を参照する。

- 全 World baseline、候補別局所仮想計算、実 World を明確に区別した
- 全 World baseline は、時点 `T-1` までの TVT 結果を引き継ぎ、時点 `T` の新規 TVT を追加しない世界である（過去 TVT を消去する世界ではない）
- 全 World baseline は全 Node を一度まとめて計算し、各 Node が共通 baseline から自 Node の情報を取得して TVT を検討する
- baseline 情報の対象は意思決定窓内 Vehicle だけではない。TVT 候補 Vehicle 全体の baseline 通過情報等も取得対象である
- 全 World baseline と局所仮想計算の双方に有限 horizon がある
- baseline 順位は候補形成と、候補別局所仮想計算へ渡す取引後順位の構築の両方に関係する
- 一つの具体的候補ごとに、取引後順位を前提とする局所仮想計算が必要である
- baseline 通過情報と局所通過情報の差から経済条件を計算する
- 全 Node の最終候補選択後に実 World へ反映する。実 World は二種類の仮想計算とは異なる
- 実 World の結果を TVT 形成判断へ事後的に持ち込まない
- 全 World baseline で必要情報不足なら、その Node では TVT を検討しない。取得済み Vehicle だけで部分的 TVT を作らない
- 局所仮想計算で一部候補だけ未解決なら、その候補だけを比較対象から除外し、解決済み候補をすべて捨てない
- 評価可能候補の中から成立要件を満たす最良候補を選ぶ。未解決候補を経済的不成立とは断定しない
- 評価可能候補数が 1 以上で成立候補なしの場合は経済条件による不成立
- 評価可能候補数が 0 の場合は局所仮想計算未解決による不成立
- 上記 2 種類の不成立理由を内部記録で区別する方針を確定した
- local horizon 内で解決しやすい候補へ選択が偏る可能性がある
- 将来、生成候補数、FIFO 棄却数、解決済み数、未解決数等を計測する方向を記録した（未実装）
- `participates_in_order_exchange` は order-exchange 参加用の既存属性（既定値 `False`）
- 最初の上位処理は全参加ケースを対象とし、対象 Vehicle へ `True` を明示できる
- 既定値を `True` へ変えるかは保留。今回 `uxsim.py` は変更しない
- 権利保有車両選定と候補生成の上位処理は未実装
- 今回訂正した Copilot の誤解（非候補 Vehicle、実 World 混同、`T-6`/`T+6` の誤説明、baseline 単純化）を設計メモ **§25.25.34.23** に詳細記録
- `T+6` 処理境界は過去に確定しておらず、次に新たに検討する（**§25.25.34.24**）
- 最新保存済み・push 済みコミットは **`767aa04`**
- 今回は Markdown 2 ファイルだけを変更
- `diagnostics/order_control.zip` は未接触・対象外
- 次は **§25.25.34** の確認後、全 World baseline の意思決定窓終端 `T+6` 処理境界へ戻る

**2026-09-05 追記（意思決定窓境界の訂正）：** 詳細正本は設計メモ **§25.25.34.28**。

- 意思決定窓は `T < baseline予想到着timestep <= T+6`
- `T+6` 到着予定 Vehicle を意思決定窓内に含める
- `T+6` 到着予定 Vehicle は到着済み Vehicle ではない
- 順位未確定なら権利保有車両になり得る
- 先に順位確定する対象は、`baseline予想到着timestep <= T` かつ現在の Node 別順位状態で順位未確定の Vehicle
- 前回の意思決定窓内 Vehicle は、TVT 成立・不成立にかかわらず順位確定される
- 前回の意思決定窓内 Vehicle は、次回の到着済みかつ順位未確定 Vehicle の発生原因ではない
- 意思決定窓外 Vehicle でも、権利保有車両の baseline 予想通過 timestep の 1 timestep 前までに到着予定なら TVT 候補 Vehicle になり得る
- 意思決定窓外 Vehicle が成立した具体的 TVT の買い手または売り手になれば順位確定される
- 意思決定窓外 Vehicle が TVT 候補 Vehicle にならなかった場合は、順位未確定のまま残り得る
- 意思決定窓外 Vehicle が TVT 候補 Vehicle にはなったが、成立した具体的 TVT の買い手にも売り手にもならなかった場合も、順位未確定のまま残り得る
- 前回の意思決定窓外だったことだけでは、順位未確定で残ったとは判断できない
- 順位確定には従来の `K_fixed` を含む既存ルールをそのまま用いる（`K_fixed = max(K_last_buyer, K_decision_window)` を変更しない）
- 今回だけ別の順位確定アルゴリズムを設けない。`K_fixed` を変更・停止・例外化しない
- 今回は前回の意思決定窓外 Vehicle が順位未確定で残る発生経路だけを説明している
- 前回の意思決定窓内 Vehicle は既存ルールで順位確定済みであり、今回の到着済み・順位未確定の発生経路の説明対象外である
- 意思決定窓内 Vehicle も含む `K_fixed` の一般論自体は正しいが、その一般論を今回の限定的説明へ別の第三経路として重ねない（説明対象を分けるためであり、実際の順位確定ルールを変更するものではない）
- 実装上の最終判定は、現在の Node 別順位状態で本当に順位未確定かを確認する
- 2 または 3 timestep 間隔では、到着済みかつ順位未確定の Vehicle が現れる可能性が毎 timestep 確認より高くなり得る
- 毎 timestep 確認でも絶対に発生しないとはまだ保証しない
- `T+6` は horizon 30 または 50 等の途中
- `T+6` で仮想計算を停止する前提の特別な境界は設けない
- 次は通常 horizon 実行後に `T+6` 到着記録が collector へ保持されるか確認する
- Copilot の誤説明（`T+6` を到着済みと扱う、前回窓内 Vehicle が順位未確定で残る、窓外＝順位未確定の単純化）を **§25.25.34.28** に詳細記録

##### 2026-09-05追記：T+6到着記録の通常horizon後の保持を確認

詳細正本は設計メモ **§25.25.34.29**。

- 意思決定窓は `T` より大きく `T+6` 以下
- `T+6` 到着予定 Vehicle は意思決定窓内の未到着 Vehicle
- `T+6` 到着予定 Vehicle は権利保有車両になり得る
- `T+6` は horizon 30 または 50 等の途中
- 特別な `T+6` 停止境界は設けない
- baseline driver は固定 horizon を 1 回の `exec_simulation()` で実行
- horizon `H` では `T` から `T+H-1` を処理し、終了後の `fork_W.T` は `T+H`
- horizon 30 または 50 では `T+6` を処理する
- `T+6` 到着時に collector へ `baseline_arrival_timestep == T+6` として記録される
- 後続 timestep で記録を消去する処理は確認されていない
- 同じ collector が結果として返される
- ファイル非変更診断で `snapshot_T=5`、`x_position=60.0`、`horizon=30` により `arrival=11` を確認
- `final_fork_timestep` は `35`
- 専用回帰テストを 1 件追加
- テスト名は `test_preserves_t_plus_6_arrival_record_after_full_horizon`
- baseline driver テストは 65 件から 66 件へ増加
- 専用テスト成功
- 全 66 件成功
- `py_compile` 成功
- `git diff --check` 問題なし
- 本番コード変更不要
- 次は権利保有車両選定前段へ戻る
- 次回は候補生成 API や局所仮想計算 API へまだ進まない
- 最新保存済み・push 済みコミットは **`767aa04`**
- Git 変更はテスト 1 ファイルと Markdown 2 ファイル
- `diagnostics/order_control.zip` は未接触・対象外
- git add、git commit、git push は未実行

##### 2026-09-06追記：Node別baseline collector記録とNode別順位台帳の照合第1部品を実装

詳細正本は設計メモ **§25.25.34.30** の「実装完了記録」。

- 全 World baseline 仮想計算で今回調べた Visit を、実 World 側の順位台帳と照合し、次の 3 種類へ整理する独立部品を実装した
  1. 順位未確定で、対象 Node への到着予測が得られた Visit
  2. 順位未確定で、仮想計算期間内に対象 Node への到着予測が得られなかった Visit
  3. collector には存在するが、順位台帳へ登録されていない Visit
- 新規本番ファイル：`uxsim/order_control_tvt_baseline_alignment.py`
- 新規専用テスト：`tests_order_control_tvt_baseline_alignment.py`
- 実装した frozen dataclass：`OrderControlTvtResolvedUndeterminedVisit`、`OrderControlTvtSnapshotUndeterminedAlignmentResult`
- 実装した関数：`align_snapshot_undetermined_visits_with_node_baseline`
- 処理起点は今回の Node 別 collector 記録である
- 順位台帳の未確定集合全体を起点にしていない
- 正式な到着順は次の 3 キー昇順である
  1. `baseline_arrival_timestep`
  2. `arrival_tiebreaker`
  3. `vehicle_id`
- 確定済み Visit は結果へ含めない
- 順位台帳にのみ存在する Visit は結果へ含めない
- 台帳未登録 Visit は `unregistered_collector_visit_keys` へ分ける
- B 型 Visit で到着 2 項目が両方 `None` の場合は正常な未解決として扱う
- A 型 Visit で到着 2 項目が両方 `None` の場合は異常として扱う
- 到着 2 項目の片方だけが `None` の場合は異常として扱う
- 入力 record と順位台帳を変更しない副作用のない処理である
- 順位登録、順位確定、意思決定窓抽出、権利保有車両選定は行わない
- 未確定 Visit 登録タイミングは未確定のままである
- `unregistered_collector_visit_keys` を正常な一時状態とみなすか、ブロッキング条件とするかは未確定である
- `python tests_order_control_tvt_baseline_alignment.py` — **25 tests passed**
- `python tests_order_control_tvt_node_rank_state.py` — **54 tests passed**
- `python tests_order_control_baseline_collector.py` — **全件 passed**
- 新規 2 ファイルの `py_compile` 成功
- `pytest` による新規専用テスト 25 件成功
- 新規 2 ファイルに対する `git diff --no-index --check` は問題なし
- 既存ファイルは変更されていない
- `diagnostics/order_control.zip` は既存未追跡、未接触
- 最新保存済み・push 済みコミットは **`ffb5068`**
- 新規 Python 2 ファイルは未コミット
- git add、git commit、git push は未実行

**次の再開地点（実装完了後）：**

到着済み相当 Visit の先行順位確定を、直ちに実装する前提とはしない。

**今回の第 1 部品が直接報告する未解決の範囲**

今回の第 1 部品が直接報告するのは、次の条件をすべて満たす Visit について、対象 Node への到着予測が得られなかったという事実である。

- 今回の Node 別 collector 記録に含まれる
- 順位台帳で未確定である
- snapshot 時点では未到着の B 型 Visit である
- `baseline_arrival_timestep` と `arrival_tiebreaker` が両方 `None` である

これらは `unresolved_undetermined_visits` として返される。

**第 1 部品の未解決と研究全体の TVT 中止方針の接続**

研究全体では、全 World baseline 仮想計算から TVT 検討に必要な情報が 1 件でも得られない場合、その Node では TVT 検討を進めない。

今回の第 1 部品が返す `unresolved_undetermined_visits` は、その研究全体の中止判断で確認すべき未解決情報の一種類である。

今回の第 1 部品だけで、TVT 検討に必要な全 World baseline 情報のすべてが解決したかを判定するわけではない。

**上位処理で次に確認する内容**

上位処理では、少なくとも次を区別して扱う必要がある。

- `unresolved_undetermined_visits` が 1 件以上ある場合
  - 今回の collector 対象かつ順位未確定の Visit について、対象 Node への到着予測が得られていない
  - したがって、当該 Node の TVT 検討を進めない判断へ接続する
- `unregistered_collector_visit_keys` が 1 件以上ある場合
  - 順位台帳への未確定 Visit 登録タイミングが未確定であるため、現段階では直ちに正常または異常と決めない
  - 登録タイミングの制度設計後に、TVT 検討を妨げる条件とするか判断する
- 上記以外の全 World baseline 必要情報
  - `route_next_link_name` や `baseline_passage_timestep` など、後続の TVT 検討で必要となる別の情報については、対応する後続処理で未解決の有無を確認する
  - 今回の第 1 部品の `all_collector_undetermined_arrivals_resolved` だけで、全必要情報が揃ったとは判断しない

**`all_collector_undetermined_arrivals_resolved` の限定された意味（再確認）**

この property は、今回の Node 別 collector 記録に含まれ、順位台帳で未確定である Visit について、対象 Node への到着予測がすべて得られたかだけを示す。

この property は、次を意味しない。

- 全 World baseline 仮想計算で必要な情報がすべて得られた
- 当該 Node で TVT 検討を続けてよい
- 台帳未登録 Visit が存在しない
- passage 予測や `route_next_link` 情報がすべて得られた

**補修後の再開順序**

1. 第 1 部品が返す `unresolved_undetermined_visits` を、上位処理の TVT 検討中止判断へどう接続するか確認する
2. `unregistered_collector_visit_keys` の扱いが未確定 Visit 登録タイミングに依存することを保持する
3. 今回の第 1 部品だけで全 World baseline 必要情報の完全解決を判定しない
4. この確認の後、到着済み相当・順位未確定 Visit の抽出と先行順位確定へ進めるか判断する

##### 2026-09-07追記：snapshot固定時の未確定Visit登録タイミングと接続原則を確定

詳細正本は設計メモ **§25.25.34.31**。

- これは**実装前**の制度・接続原則の確定記録である
- 権利保有 Visit を正しく選定するには、今回の snapshot 固定集合に含まれる Visit を、全 World baseline の結果と照合する**前**に、実 World 側の Node 別 TVT 順位台帳へ順位未確定 Visit として登録する必要がある
- 未確定 Visit 登録は、正式 baseline 順位を付ける処理**ではない**
- snapshot 固定集合への包含順、collector 登録順、inlink 走査順から割当権利行使順位を**決めない**
- 同じ snapshot 固定 Visit 集合を、順位台帳登録と collector 登録で**共有**する必要がある

**概念上の接続順**

1. snapshot 固定 Visit 登録計画を構築・検証する
2. その計画から、実 World 側の Node 別順位台帳へ未登録 Visit を順位未確定として登録する
3. 同じ計画を fork 側 collector へ登録する
4. 全 World baseline 仮想計算を実行する
5. baseline 結果と順位台帳を照合する

- collector に存在する先着 Visit が順位台帳へ未登録のままでは、権利保有 Visit を本来より後方の Visit から誤選定する可能性がある
- 既存の alignment 第 1 部品自体は変更せず、上位接続によって未登録状態を解消する方針
- **§25.25.34.31** の記録時点では、prepare/apply 分割、順位台帳登録 helper、baseline driver 接続は**後続作業**だった
- その後の実装は、既存の進捗記録と **§25.25.34.32** 以降を参照する

##### 2026-09-07追記：snapshot固定Visit登録計画のprepare/apply分割を実装

詳細正本は設計メモ **§25.25.34.32** の「実装完了記録」。

- snapshot 固定 Visit 登録処理を **prepare** と **apply** へ分割した
- 変更不能な `OrderControlBaselineSnapshotVisitEntry` と `OrderControlBaselineSnapshotRegistrationPlan` を実装した
- snapshot 固定 Visit 集合を**一度だけ**構築する
- 同じ `plan` を、後続の順位台帳登録と collector 登録で**共有できる**構造にした
- 現時点では collector 登録にだけ **apply** を使用している
- 従来の `register_snapshot_fixed_visits` の外部契約と返り値 **int** を維持した
- baseline driver は変更せず、既存 **66 テスト**が成功した
- prepare/apply 関連 **24 件**を追加し、snapshot テストは合計 **83 件**成功した
- `pytest` では関連 3 ファイル合計 **182 件**成功した
- 順位台帳登録 helper と driver 接続は**未実装**
- 次は順位台帳登録 helper の責務と配置を検討する

**実装した公開 API**

- `prepare_snapshot_fixed_visit_registration_plan(fork_W, *, target_node_names) -> OrderControlBaselineSnapshotRegistrationPlan`
- `apply_snapshot_fixed_visit_registration_plan(plan, collector) -> int`
- `register_snapshot_fixed_visits(...)` — 内部で prepare → apply の薄いラッパー（外部契約維持）

**変更ファイル**

- `uxsim/order_control_baseline_snapshot.py`
- `tests_order_control_baseline_snapshot.py`

**テスト結果**

| 実行 | 結果 |
|------|------|
| `python -m py_compile` | 成功 |
| `python tests_order_control_baseline_snapshot.py` | 83 テスト成功 |
| `python tests_order_control_baseline_driver.py` | 66 テスト成功 |
| `python tests_order_control_baseline_collector.py` | 成功 |
| `pytest`（上記 3 ファイル） | 182 passed |
| `git diff --check` | 問題なし |

**今回実装していないもの**

- 実 World 側順位台帳への登録 helper
- baseline driver への `RegistrationPlan` 受渡し
- 上位 TVT 制御、callback/hook、rollback
- 権利保有車両選定以降のすべて

**Git 状態**

- 作業開始時点の最新保存済み・push 済みコミットは **`9327344`**
- Python 2 ファイルは未コミットの作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**次の再開地点**

検証済み `RegistrationPlan` の Node 名と VisitKey を使い、実 World 側 Node 別順位台帳へ未登録 Visit を一括登録する薄い helper の責務と配置を検討する。baseline driver への実接続はその後に別途検討する。

##### 2026-09-07追記：snapshot固定Visit計画からNode別順位台帳への未登録Visit登録helperを実装

詳細正本は設計メモ **§25.25.34.33** の「実装完了記録（§25.25.34.33）」。

- 新規本番モジュール `uxsim/order_control_tvt_snapshot_undetermined_registration.py` を追加した
- 新規専用テスト `tests_order_control_tvt_snapshot_undetermined_registration.py` を追加した
- 検証済み snapshot 固定 Visit 計画に含まれる Visit を Node ごとに確認し、**未登録 Visit だけ**を順位未確定として台帳へ登録する
- 順位未確定集合に登録済みの Visit（`is_undetermined` が `True`）と、順位確定済みの Visit（`is_confirmed` が `True`）は、**別々の除外条件**として新規登録対象から除外する
- Node ごとに `register_undetermined_visits` を 1 回だけ呼び、一括登録する
- 順位確定は行わない
- 戻り値は全 Node 合計の新規登録件数 `int`
- 専用テスト **25 件**成功
- `tests_order_control_tvt_node_rank_state.py`（54 件）、`tests_order_control_baseline_snapshot.py`、`tests_order_control_tvt_baseline_alignment.py`（25 件）も成功
- baseline driver への接続は**未実装**
- 次は prepare、helper、apply、仮想計算の接続方法を検討する
- 権利保有車両選定には**まだ進まない**

**実装した公開 API**

- `register_undetermined_visits_from_snapshot_plan(plan, rank_states_by_node_name) -> int`

**変更ファイル**

- `uxsim/order_control_tvt_snapshot_undetermined_registration.py`（新規）
- `tests_order_control_tvt_snapshot_undetermined_registration.py`（新規）

**テスト結果**

| 実行 | 結果 |
|------|------|
| 新規本番・専用テストの `python -m py_compile` | 成功 |
| `python tests_order_control_tvt_snapshot_undetermined_registration.py` | 25 テスト成功 |
| `pytest tests_order_control_tvt_snapshot_undetermined_registration.py` | 25 passed |
| `python tests_order_control_tvt_node_rank_state.py` | 54 テスト成功 |
| `python tests_order_control_baseline_snapshot.py` | 成功 |
| `python tests_order_control_tvt_baseline_alignment.py` | 25 テスト成功 |
| `git diff --check` | 問題なし |

**今回実装していないもの**

- baseline driver への実接続
- prepare、順位台帳登録 helper、apply、仮想計算をつなぐ上位処理
- 上位 TVT 制御、権利保有車両選定以降のすべて

**Git 状態**

- 作業開始時点の最新保存済み・push 済みコミットは **`434306e`**
- 新規 Python 2 ファイルは未コミットの作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**次の再開地点**

helper の実装、専用テスト、設計メモの整合を最終確認した後、prepare、順位台帳登録 helper、apply、baseline 仮想計算を接続する最小の処理方法を検討する。baseline driver をどのように拡張または利用するかは、その接続検討で決める。権利保有車両選定にはまだ進まない。

##### 2026-09-07追記：TVT順位台帳登録付きsnapshot固定baseline fork実行経路を実装

**位置づけ**

- 実装前仕様の正本は設計メモ **§25.25.34.34**
- 実装結果、検証結果、当時の再開地点の正本は **§25.25.34.35**
- **§25.25.34.34** は実装前の歴史的記録として残っている。実装済み事実について差がある場合は **§25.25.34.35** を参照する

**非技術的な目的**

- snapshot 固定集合を**一度だけ**作り、その**同じ計画**を使って、実 World 側順位台帳への未確定登録と fork 側 collector への登録を行う
- 順位台帳登録を全 World baseline 仮想計算より**前**に済ませ、baseline 結果との照合時に正常な対象 Visit が未登録扱いになることを防ぐ

**実装前仕様（§25.25.34.34）の要点**

- 既存 `run_snapshot_fixed_baseline_fork` の外部シグネチャと従来動作は維持する
- TVT 順位台帳登録を伴う**新しい公開関数**を `order_control_baseline_driver.py` へ追加する
- `RegistrationPlan` を **1 回だけ** prepare し、**同じ** plan を順位台帳登録 helper と collector apply の**両方**へ渡す
- callback、hook、rollback は追加しない

**実装した処理順（§25.25.34.35）**

1. `_prepare_baseline_fork`（入力検証、`real_W` 状態保存、`fork_W` 作成、空 collector を `fork_W` 側だけへ設定）
2. `prepare_snapshot_fixed_visit_registration_plan`
3. `register_undetermined_visits_from_snapshot_plan`（既存 helper を利用。重複実装しない）
4. `apply_snapshot_fixed_visit_registration_plan`
5. `_complete_baseline_fork_after_registration`（登録件数照合、0 件時の空結果、残り timestep 検証）
6. 登録件数が **1 件以上**の場合だけ `fork_W.exec_simulation`（固定 horizon 一括実行）

**実装内容**

- 変更本番モジュール：`uxsim/order_control_baseline_driver.py`
- 新規専用テスト：`tests_order_control_tvt_baseline_driver_registration.py`
- 新規公開関数：`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration(real_W, *, target_node_names, baseline_horizon_steps, rank_states_by_node_name) -> OrderControlBaselineForkResult`
- 既存固定 horizon baseline driver を無理に変更せず、TVT 順位台帳登録を伴う**専用実行経路**を追加した
- 内部共通化：`_BaselineForkPrepared`、`_prepare_baseline_fork`、`_complete_baseline_fork_after_registration`（内部 API。公開しない）
- 既存 `run_snapshot_fixed_baseline_fork` は `register_snapshot_fixed_visits` を 1 回呼ぶ従来経路を維持
- `OrderControlBaselineForkResult` は変更していない
- 順位確定、権利保有 Visit 選定、TVT 候補生成、alignment 実行は**行わない**

**結果と副作用**

- 順位台帳へ登録するのは、snapshot 固定計画にある**未登録** Visit だけ
- 登録済み未確定 Visit と確定済み Visit を新規登録しない
- 順位台帳への登録順から順位を付けない
- collector は `fork_W` 側**だけ**に設定する
- `real_W` は forward しない。例外時も `real_W` の `T`、`TIME`、`order_control_baseline_collector` は変更しない
- helper 失敗時は apply と exec を行わない。apply 失敗時は exec を行わない
- driver は順位未確定登録を **rollback しない**。正常登録済みの順位未確定 Visit は後続失敗後も残る
- 0 件時も helper と apply を各 1 回実行し、`exec_simulation` は省略する
- upstream 処理を再実行しない

**テスト結果（§25.25.34.35）**

| 実行 | 結果 |
|------|------|
| `tests_order_control_tvt_baseline_driver_registration.py` の `python -m py_compile` | 成功 |
| `python tests_order_control_tvt_baseline_driver_registration.py` | **30 tests passed** |
| `pytest tests_order_control_tvt_baseline_driver_registration.py` | **30 passed** |
| `python tests_order_control_baseline_driver.py` | **66 tests passed** |
| `tests_order_control_baseline_snapshot.py` | 実装完了時に成功 |
| `tests_order_control_tvt_snapshot_undetermined_registration.py` | 実装完了時に **25 tests passed** |
| `tests_order_control_tvt_node_rank_state.py` | 実装完了時に **54 tests passed** |
| `git diff --check` | 問題なし |

**Git 状態（§25.25.34.35 記録時点）**

- 作業開始時点の最新保存済み・push 済みコミットは **`f7052b1`**
- `uxsim/order_control_baseline_driver.py` と `tests_order_control_tvt_baseline_driver_registration.py` は未コミットの作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**当時の次の再開地点**

- 仮想計算**完了後**に、`order_control_tvt_baseline_alignment` を正確に 1 回実行する上位処理を接続し、`unregistered_collector_visit_keys` が空であることを確認する（権利保有 Visit 選定より前）
- この alignment 接続は後に **§25.25.34.36** と **§25.25.34.37** で設計・実装された。**詳細は後続の補填で記録する**

##### 2026-09-08追記：baseline fork後のNode別alignment接続を実装

**位置づけ**

- 実装前仕様の正本は設計メモ **§25.25.34.36**
- 実装結果、検証結果、当時の再開地点の正本は **§25.25.34.37**
- **§25.25.34.36** は実装前の歴史的記録として残っている。実装済み事実について差がある場合は **§25.25.34.37** を参照する

**非技術的な目的**

- 順位台帳登録付きの全 World baseline 仮想計算が正常終了した後、各対象 Node について collector 記録と実 World 側順位台帳を照合する
- 正常な snapshot 固定 Visit が順位台帳へ未登録のまま残っていないことを、権利保有 Visit 選定より前に確認する
- 後続処理へ、到着予測を取得できた未確定 Visit と、取得できなかった未確定 Visit を Node 別に渡す

**実装前仕様（§25.25.34.36）の要点**

- 上位公開関数は **§25.25.34.35** の baseline driver を 1 回呼び、正常完了後に Node 別 alignment を接続する（alignment 段階で baseline fork を再実行しない）
- `target_node_names` 順に各 Node を処理する
- 既存 Node 単位 alignment 第 1 部品 `align_snapshot_undetermined_visits_with_node_baseline` を再利用する
- `unregistered_collector_visit_keys` が空であることを上位接続で要求する。非空なら権利保有 Visit 選定へ進まず `RuntimeError` で停止する
- `unresolved_undetermined_visits` は正常な情報未解決として結果に保持する。この alignment 接続自体の `RuntimeError` にはしない
- 順位登録、順位確定、意思決定窓抽出、権利保有 Visit 選定は行わない

**実装内容（§25.25.34.37）**

- 新規本番モジュール：`uxsim/order_control_tvt_baseline_fork_alignment.py`
- 新規専用テスト：`tests_order_control_tvt_baseline_fork_alignment.py`
- 新規公開結果型：`OrderControlTvtBaselineForkAlignmentResult`（frozen dataclass）
  - `fork_result: OrderControlBaselineForkResult`（既存型。変更なし）
  - `alignment_results: tuple[OrderControlTvtSnapshotUndeterminedAlignmentResult, ...]`（`fork_result.target_node_names` と**同じ Node 順**）
- 新規公開関数：`run_snapshot_fixed_baseline_fork_and_align_undetermined_visits(real_W, *, target_node_names, baseline_horizon_steps, rank_states_by_node_name) -> OrderControlTvtBaselineForkAlignmentResult`
- 既存 `run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration` を 1 回呼び、正常完了後に Node ごとに collector export と alignment 第 1 部品を各 1 回実行する
- 既存 Node 単位 alignment 関数を再利用し、同じ分類処理を重複実装していない
- `target_node_names` と `alignment_results` の Node 名・順序を照合する
- rank state、collector、real_W、fork_W を変更しない。upstream baseline fork を再実行しない（上位関数 1 回の呼出し内で driver を 1 回呼ぶ）
- callback、hook、rollback は導入していない

**status と未解決**

- `unresolved_undetermined_visits` が存在しても、この alignment 接続自体は `RuntimeError` にしない。その Node で TVT 検討を進めない判断は後続処理の責務
- `unregistered_collector_visit_keys` が非空なら `RuntimeError`。正常な情報未解決と重大不整合を混同しない
- 0 件時（`registered_visit_count == 0`）も Node ごとに alignment を省略しない

**テスト結果（§25.25.34.37）**

| 実行 | 結果 |
|------|------|
| `uxsim/order_control_tvt_baseline_fork_alignment.py` と専用テストの `python -m py_compile` | 成功 |
| `python tests_order_control_tvt_baseline_fork_alignment.py` | **24 tests passed** |
| `pytest tests_order_control_tvt_baseline_fork_alignment.py` | **24 passed** |
| `python tests_order_control_baseline_driver.py` | **66 tests passed** |
| `python tests_order_control_tvt_baseline_driver_registration.py` | **30 tests passed** |
| `python tests_order_control_tvt_baseline_alignment.py` | **25 tests passed** |
| `git diff --check` | 問題なし |

**Git 状態（§25.25.34.37 記録時点）**

- 作業開始時点の最新保存済み・push 済みコミットは **`b67c53d`**
- 新規本番モジュールと専用テストは未追跡の作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**当時の次の再開地点**

- baseline 開始時点 **T** までに到着し、かつ順位未確定の Visit を正式 baseline 順のまま先行順位確定する処理
- その処理は後に **§25.25.34.38** と **§25.25.34.39** で設計・実装された。**詳細は直後の補填記録を参照する**

##### 2026-09-08追記：既到着かつ順位未確定Visitの先行順位確定を実装

**位置づけ**

- 実装前仕様の正本は設計メモ **§25.25.34.38**
- 実装結果、検証結果、当時の再開地点の正本は **§25.25.34.39**
- **§25.25.34.38** は実装前の歴史的記録として残っている。実装済み事実について差がある場合は **§25.25.34.39** を参照する
- 本体制度ルールは設計メモ **§5** を参照する

**非技術的な目的**

- baseline 開始時点 **T** までに対象 Node へ到着すると予測され、現在も順位未確定である Visit は、新しい TVT の起点にしない
- それらを正式 baseline 順のまま先に順位確定し、その後に未到着 Visit について意思決定窓と TVT を検討できる状態にする

**正式な既到着定義**

- `baseline_arrival_timestep <= T`（`T` は `alignment_fork_result.fork_result.baseline_timestep_T`）
- **T ちょうど**に到着する Visit も既到着として扱う
- 参加・非参加を問わず同じ定義を適用する

**実装前仕様（§25.25.34.38）の要点**

- baseline fork 後の Node 別 alignment 結果 `OrderControlTvtBaselineForkAlignmentResult` を入力する
- 各 Node の `resolved_undetermined_visits` から `baseline_arrival_timestep <= T` を抽出する
- `was_arrived_at_snapshot` や参加属性を抽出条件に使用しない
- `resolved_undetermined_visits` の既存順（正式 baseline 順）を維持し、再ソートしない
- `confirm_visits_in_order` へ一括渡す。既到着 0 件の Node でも空 tuple で 1 回呼ぶ
- `unresolved_undetermined_visits` が非空でも、resolved 列の到着タイムステップ **T 以下**の Visit は確定する。TVT 続行・中止判断は行わない
- 先頭非参加 Visit 処理、権利保有 Visit 選定、TVT 候補生成は行わない

**実装内容（§25.25.34.39）**

- 新規本番モジュール：`uxsim/order_control_tvt_arrived_undetermined_confirmation.py`
- 新規専用テスト：`tests_order_control_tvt_arrived_undetermined_confirmation.py`
- 新規 Node 別結果型：`OrderControlTvtNodeArrivedUndeterminedConfirmationResult`（frozen dataclass）
  - `node_name`
  - `confirmed_arrived_visit_keys`（今回 `confirm_visits_in_order` へ渡した `VisitKey` tuple）
  - `confirm_result: OrderControlTvtConfirmResult`
- 新規全体結果型：`OrderControlTvtArrivedUndeterminedConfirmationResult`（frozen dataclass）
  - `alignment_fork_result`（入力と同じオブジェクトを保持）
  - `node_confirmation_results`（`fork_result.target_node_names` と**同じ Node 順**）
- 新規公開関数：`confirm_already_arrived_undetermined_visits(alignment_fork_result, *, rank_states_by_node_name) -> OrderControlTvtArrivedUndeterminedConfirmationResult`
- `T` は別引数にせず `alignment_fork_result.fork_result.baseline_timestep_T` から取得する。`real_W` は受け取らない
- `fork_result.target_node_names` 順に Node を処理し、期待 Node 名と `alignment_result.node_name` の不一致は confirm 前に `RuntimeError`
- 既存 `OrderControlTvtNodeRankState.confirm_visits_in_order` を Node ごとに 1 回使用する
- baseline fork、alignment、collector を再実行しない。rollback や独自順位台帳更新は追加していない

**Node 別の処理結果（status フィールドは持たない）**

- 既到着・順位未確定 Visit が 0 件：`confirm_visits_in_order` を no-op で 1 回呼び、`newly_confirmed_count == 0`
- 1 件以上：抽出順のまま先行確定し、`confirm_result` に `k_confirmed_before` / `k_confirmed_after` を保持
- `unresolved_undetermined_visits` 非空：resolved 列の **T 以下** Visit は通常どおり確定。unresolved 自体は未確定のまま

**副作用と責任境界**

- 変更するのは、先行確定対象が存在する Node の順位状態だけ
- collector、baseline fork 結果、alignment 結果、real_W、fork_W を変更しない
- 先頭連続非参加 Visit の先行確定、権利保有 Visit 選定、TVT 候補生成は**まだ実行しない**

**テスト結果（§25.25.34.39）**

| 実行 | 結果 |
|------|------|
| `py_compile` | 成功 |
| `python tests_order_control_tvt_arrived_undetermined_confirmation.py` | **30 tests passed** |
| `pytest tests_order_control_tvt_arrived_undetermined_confirmation.py` | **30 passed** |
| `python tests_order_control_tvt_node_rank_state.py` | **54 tests passed** |
| `python tests_order_control_tvt_baseline_alignment.py` | **25 tests passed** |
| `python tests_order_control_tvt_baseline_fork_alignment.py` | **24 tests passed** |
| `git diff --check` | 問題なし |

主な確認内容：到着 `< T` / `== T` / `> T`、参加・非参加中立、同着順位、既到着 0 件の no-op confirm、unresolved 非空時の既到着確定、複数 Node、読取入力不変、upstream 非再実行、途中失敗時の先行 Node 確定残存

**Git 状態（§25.25.34.39 記録時点）**

- 作業開始時点の最新保存済み・push 済みコミットは **`47173e1`**
- 新規本番モジュールと専用テストは未追跡の作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**当時の次の再開地点**

- 既到着 Visit 先行確定後の意思決定窓内正式 baseline 順位について、先頭から連続する非参加 Visit を先行確定する処理
- その処理は後に **§25.25.34.40** と **§25.25.34.41** で設計・実装された。**詳細は後続の補填で記録する**

##### 2026-09-08追記：先頭連続非参加Visitの先行順位確定を実装

**位置づけ**

- 実装前仕様の正本は設計メモ **§25.25.34.40**
- 実装結果、検証結果、当時の再開地点の正本は **§25.25.34.41**
- **§25.25.34.40** は実装前の歴史的記録として残っている。実装済み事実について差がある場合は **§25.25.34.41** を参照する
- 本体の制度ルールは設計メモ **§4.5** を参照する
- **2026-08-29** の既存進捗記録（直後）は **§4.5** の制度記録補修であり、本項のコード実装記録とは別である（詳細正本：**§25.25.34.40** / **§25.25.34.41**）

**非技術的な目的**

- 既到着 Visit の先行確定後、意思決定窓内の正式 baseline 順位を先頭から確認する
- 最初の参加 Visit より前に連続する非参加 Visit を、baseline 順位のまま先に順位確定する
- その後に残る最上位の参加 Visit を、後続の権利保有 Visit 選定候補にできる状態にする
- 意思決定窓内がすべて非参加なら、その全 Visit を同じ共通処理で先行確定し、TVT 検討不要となる状態を作る

**実装前仕様（§25.25.34.40）の要点**

- **§25.25.34.39** の既到着 Visit 先行確定結果 `OrderControlTvtArrivedUndeterminedConfirmationResult` を入力する
- 意思決定窓は **`T < baseline_arrival_timestep <= T + 6`**（`T` は `fork_result.baseline_timestep_T`）
- `configured_horizon_steps >= 6` を処理開始時に確認する
- 正式 baseline 順は `resolved_undetermined_visits` の既存順を使用する。参加状態による並べ替えを行わない
- 意思決定窓内列の先頭から連続する非参加 Visit だけを抽出する。最初の参加 Visit より後方の非参加 Visit は確定しない
- 意思決定窓内がすべて非参加なら全件が先行確定対象となる
- 権利保有 Visit の最終選定、TVT 候補生成、取引評価は行わない

**実装内容（§25.25.34.41）**

- 新規本番モジュール：`uxsim/order_control_tvt_leading_nonparticipating_confirmation.py`
- 新規専用テスト：`tests_order_control_tvt_leading_nonparticipating_confirmation.py`
- 新規 Node 別結果型：`OrderControlTvtNodeLeadingNonparticipatingConfirmationResult`（frozen dataclass）
  - `node_name`
  - `decision_window_visit_keys`（意思決定窓内の正式 baseline 順位）
  - `confirmed_leading_nonparticipating_visit_keys`（今回 confirm へ渡した先頭連続非参加 Visit 列）
  - `remaining_decision_window_visit_keys`（先頭非参加 prefix を除いた残り）
  - `confirm_result: OrderControlTvtConfirmResult`
- 新規全体結果型：`OrderControlTvtLeadingNonparticipatingConfirmationResult`（frozen dataclass）
  - `arrived_confirmation_result`（入力と同じオブジェクトを保持）
  - `node_confirmation_results`（`fork_result.target_node_names` と**同じ Node 順**）
- 新規公開関数：`confirm_leading_nonparticipating_decision_window_visits(arrived_confirmation_result, *, rank_states_by_node_name, participates_by_visit_key) -> OrderControlTvtLeadingNonparticipatingConfirmationResult`
- `participates_by_visit_key` は呼出側所有。意思決定窓内 Visit **全件**について `type(value) is bool` を検証する
- status フィールドは**持たない**（実コード確認済み）
- baseline fork、alignment、既到着先行確定、collector export を再実行しない

**順位確定**

- 先頭連続非参加 Visit だけを `confirm_visits_in_order` へ渡す。空 tuple でも Node ごとに 1 回呼ぶ
- 入力順を維持し、参加状態による再ソートを行わない
- 先頭が参加または全参加の場合は no-op confirm（`remaining` は意思決定窓内全件）
- 全非参加の場合は意思決定窓内全件を confirm し、`remaining` は空
- 途中失敗時：先行 Node の正常確定は rollback しない。失敗 Node 内は confirm API の原子性を利用する

**責任境界**

- 変更するのは、先行確定対象が存在する Node の順位状態だけ
- collector、baseline fork 結果、alignment 結果、既到着先行確定結果、real_W、fork_W を変更しない
- upstream 処理を再実行しない
- 権利保有 Visit をこの関数内で選定しない。TVT 候補 Visit 集合を作らない

**テスト結果（§25.25.34.41）**

| 実行 | 結果 |
|------|------|
| `py_compile` | 成功 |
| `python tests_order_control_tvt_leading_nonparticipating_confirmation.py` | **23 tests passed** |
| `pytest tests_order_control_tvt_leading_nonparticipating_confirmation.py` | **23 passed** |
| `python tests_order_control_tvt_arrived_undetermined_confirmation.py` | **30 tests passed** |
| `python tests_order_control_tvt_node_rank_state.py` | **54 tests passed** |
| `python tests_order_control_tvt_baseline_alignment.py` | **25 tests passed** |
| `python tests_order_control_tvt_baseline_fork_alignment.py` | **24 tests passed** |
| `git diff --check` | 問題なし |

主な確認内容：先頭非参加 0 件、先頭非参加 1 件以上、`n n p p n p n p p` の制度例、最初の参加 Visit より後方の非参加 Visit を確定しない、意思決定窓内全件が非参加、参加状態中立の baseline 順位、意思決定窓外 Visit を先行確定しない、複数 Node、読取入力不変、upstream 非再実行

**Git 状態（§25.25.34.41 記録時点）**

- 作業開始時点の最新保存済み・push 済みコミットは **`153006c`**
- 新規本番モジュールと専用テストは未追跡の作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**当時の次の再開地点**

- 先頭連続非参加 Visit 先行確定後の残列から権利保有 Visit を選定する処理
- その処理は後に **§25.25.34.42** と **§25.25.34.43** で設計・実装された。**詳細は直後の補填記録を参照する**

##### 2026-09-08追記：先頭連続非参加Visit先行確定後の権利保有Visit選定を実装

**位置づけ**

- 実装前仕様の正本は設計メモ **§25.25.34.42**
- 実装結果、検証結果、当時の再開地点の正本は **§25.25.34.43**
- **§25.25.34.42** は実装前の歴史的記録として残っている。実装済み事実について差がある場合は **§25.25.34.43** を参照する
- 制度上の権利保有車両は設計メモ **§4.5** と **§8** を参照する

**非技術的な目的**

- 既到着 Visit と先頭連続非参加 Visit の先行確定が終わった後、意思決定窓内に残る未確定 Visit 列を確認する
- 正常に TVT 検討を続けられる場合、その残列の先頭にいる参加 Visit を権利保有 Visit として選定する
- 情報未解決、残列なし、全非参加処理済みなどを区別し、権利保有 Visit が存在しない正常状態と重大不整合を混同しない

**実装前仕様（§25.25.34.42）の要点**

- **§25.25.34.41** の先頭連続非参加 Visit 先行確定結果 `OrderControlTvtLeadingNonparticipatingConfirmationResult` を入力する
- `target_node_names` 順に Node を処理する
- `unresolved_undetermined_visits` が非空の Node では TVT 検討を進めない（`UNRESOLVED_BASELINE_ARRIVALS`）
- 先行確定後の `remaining_decision_window_visit_keys` が空なら権利保有 Visit なし（`NO_RIGHT_OF_ENTRY`）
- 残列が非空なら先頭 VisitKey を権利保有 Visit とする。後方 Visit へ繰り上げない
- P 取得、TVT 候補 Visit 生成、買い手・売り手選定は行わない

**実装内容（§25.25.34.43）**

- 新規本番モジュール：`uxsim/order_control_tvt_right_of_entry_selection.py`
- 新規専用テスト：`tests_order_control_tvt_right_of_entry_selection.py`
- 新規 status Enum：`OrderControlTvtRightOfEntrySelectionStatus`
  - `SELECTED` — `unresolved` が空で `remaining` が非空。`right_of_entry_visit_key` は非 `None`
  - `NO_RIGHT_OF_ENTRY` — `unresolved` が空で `remaining` が空。`right_of_entry_visit_key` は `None`
  - `UNRESOLVED_BASELINE_ARRIVALS` — `unresolved_undetermined_visits` が非空。`right_of_entry_visit_key` は `None`
- 新規 Node 別結果型：`OrderControlTvtNodeRightOfEntrySelectionResult`（frozen dataclass）
  - `node_name`
  - `selection_status`
  - `right_of_entry_visit_key: OrderControlTvtVisitKey | None`
  - `k_confirmed_before`（選定時点の `rank_state.k_confirmed()` の snapshot。全 status で保存）
- 新規全体結果型：`OrderControlTvtRightOfEntrySelectionResult`（frozen dataclass）
  - `leading_confirmation_result`（入力と同じオブジェクトを保持）
  - `node_selection_results`（`fork_result.target_node_names` と**同じ Node 順**）
- 新規公開関数：`select_right_of_entry_decision_window_visits(leading_confirmation_result, *, rank_states_by_node_name, participates_by_visit_key) -> OrderControlTvtRightOfEntrySelectionResult`
- 読取専用。`confirm_visits_in_order` を呼ばず、順位台帳を変更しない
- baseline fork、alignment、既到着先行確定、先頭非参加先行確定、collector を再実行・再照会しない

**選定契約**

- `unresolved` 非空を `remaining` の空・非空より優先して判定する
- 正常選定時は `remaining_decision_window_visit_keys` の先頭 VisitKey を使用する
- 先頭が非参加（`participates_by_visit_key` が `False`）なら上流契約違反として `RuntimeError`
- 選定候補が確定済みまたは未登録なら `RuntimeError`（`NO_RIGHT_OF_ENTRY` へ変換しない）
- `K_confirmed_before` は既到着・先頭非参加の古い `ConfirmResult` 値を流用せず、選定時点の `k_confirmed()` から取得する

**責任境界**

- 順位台帳、collector、baseline fork 結果、alignment 結果、先行確定結果、real_W、fork_W を変更しない
- upstream 処理を再実行しない
- P を取得しない。TVT 候補集合を作らない。局所仮想計算・経済評価は行わない

**テスト結果（§25.25.34.43）**

| 実行 | 結果 |
|------|------|
| `py_compile` | 成功 |
| `python tests_order_control_tvt_right_of_entry_selection.py` | **16 tests passed** |
| `pytest tests_order_control_tvt_right_of_entry_selection.py` | **16 passed** |
| `python tests_order_control_tvt_leading_nonparticipating_confirmation.py` | **23 tests passed** |
| `python tests_order_control_tvt_arrived_undetermined_confirmation.py` | **30 tests passed** |
| `python tests_order_control_tvt_node_rank_state.py` | **54 tests passed** |
| `python tests_order_control_tvt_baseline_alignment.py` | **25 tests passed** |
| `python tests_order_control_tvt_baseline_fork_alignment.py` | **24 tests passed** |
| `git diff --check` | 問題なし |

主な確認内容：通常選定、先頭非参加確定後の最初の参加 Visit、権利保有 Visit なし、unresolved、全非参加処理後、先頭が非参加で残る重大不整合、順位状態との不一致、複数 Node、`K_confirmed_before`、入力不変、upstream 非再実行

**Git 状態（§25.25.34.43 記録時点）**

- 作業開始時点の最新保存済み・push 済みコミットは **`3012524`**
- 新規本番モジュールと専用テストは未追跡の作業ツリーに存在する
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**当時の次の再開地点**

- 権利保有 Visit の baseline 予想通過タイムステップ **P** を取得し、P − 1 条件から TVT 候補 Visit 母集団を作り、baseline 情報充足を判定する処理
- その処理は **§25.25.34.44** と **§25.25.34.45** で設計・実装された。**詳細は次の過去補填で記録する**

##### 2026-09-09追記：権利保有VisitのP取得とP - 1候補母集団・baseline情報充足判定を実装

**位置づけ**

- 実装前仕様の正本は設計メモ **§25.25.34.44**
- 実装結果、検証結果、当時の再開地点の正本は **§25.25.34.45**
- **§25.25.34.44** は実装前の歴史的記録として残っている。実装済み事実について差がある場合は **§25.25.34.45** を参照する
- 権利保有 Visit 選定の実装完了は **§25.25.34.43** を参照する
- 制度上の P − 1 条件は設計メモ **§7**、**§8**、**§9** を参照する
- 本項は **§25.25.34.45 時点**の実装を記録する。可変上限 N（**§25.25.34.46** 以降）は**含まない**

**非技術的な目的**

- 権利保有 Visit が取引なし baseline で通過すると予測された時点 **P** を取得する
- P の 1 タイムステップ前までに対象 Node へ到着すると予測された、snapshot 固定集合内かつ現在順位未確定の Visit を、今回の TVT 候補母集団として確定する
- その候補**全員**について、後続の TVT 形成に必要な baseline 通過情報が揃っているかを判定する
- 候補の一部だけで部分的な TVT を形成しない

**§25.25.34.45 時点の候補母集団の範囲**

- P − 1 条件を満たす Visit を**全件** `candidate_visits` へ含めていた
- この時点では**可変上限 N を適用していない**

**実装前仕様（§25.25.34.44）の要点**

- **§25.25.34.43** の権利保有 Visit 選定結果 `OrderControlTvtRightOfEntrySelectionResult` を入力する
- `target_node_names` 順に Node を処理する
- `SELECTED` 以外の Node は候補集合を構築しない
- 権利保有 Visit の collector 記録から `baseline_passage_timestep` を **P** として取得する。P が `None` なら通過情報未解決として扱う
- B 型かつ現在順位未確定で `baseline_arrival_timestep <= P - 1` を満たす Visit を候補母集団とする
- A 型・確定済み Visit を候補から除外する。参加状態を候補抽出または baseline 順位決定に使用しない
- 権利保有 Visit が候補母集団に正確に 1 件含まれることを確認する
- 候補全員の `baseline_passage_timestep` が非 `None` なら情報取得完了。1 件でも `None` なら情報未解決
- baseline fork、alignment、先行確定、権利保有選定を再実行しない

**実装内容（§25.25.34.45）**

- 新規本番モジュール：`uxsim/order_control_tvt_candidate_visit_set.py`
- 新規専用テスト：`tests_order_control_tvt_candidate_visit_set.py`
- 新規 status Enum：`OrderControlTvtCandidateVisitSetStatus`
  - `NOT_BUILT_NO_RIGHT_OF_ENTRY` — 上流 `NO_RIGHT_OF_ENTRY`。`right_of_entry_visit_key` / P は `None`、`candidate_visits` は空
  - `NOT_BUILT_UNRESOLVED_ARRIVALS` — 上流 `UNRESOLVED_BASELINE_ARRIVALS`。同上
  - `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE` — 権利保有 Visit 選定済みだが P が `None`。`right_of_entry_visit_key` は非 `None`、`candidate_visits` は空
  - `UNRESOLVED_CANDIDATE_PASSAGES` — P と候補母集団は確定済みだが、候補の 1 件以上で passage が `None`。母集団**全体**を保持
  - `BASELINE_INFORMATION_COMPLETE` — P、候補母集団、候補全員の passage が取得済み
- 新規候補要素型：`OrderControlTvtCandidateVisit`（frozen dataclass）
  - `visit_key`、`vehicle_id`、`inlink_name`、`baseline_arrival_timestep`、`arrival_tiebreaker`、`route_next_link_name`、`baseline_passage_timestep`
- 新規 Node 別結果型：`OrderControlTvtNodeCandidateVisitSetResult`（frozen dataclass）
  - `node_name`、`build_status`、`right_of_entry_visit_key`、`right_of_entry_baseline_passage_timestep`、`k_confirmed_before`、`candidate_visits`
- 新規全体結果型：`OrderControlTvtCandidateVisitSetResult`（frozen dataclass）
  - `right_of_entry_selection_result`（入力と同じオブジェクトを保持）
  - `node_candidate_set_results`（`fork_result.target_node_names` と**同じ Node 順**）
- 新規公開関数：`build_tvt_candidate_visit_set(right_of_entry_selection_result, *, rank_states_by_node_name) -> OrderControlTvtCandidateVisitSetResult`
- `participates_by_visit_key` は受け取らない。`k_confirmed_before` は上流選定結果の snapshot 値を使用し、`rank_state.k_confirmed()` を再取得しない
- 読取専用。順位台帳、collector、World を変更しない

**候補集合の正式条件（§25.25.34.45 時点）**

候補に含む：snapshot 固定集合内の **B 型**、対象 Node で**現在順位未確定**、`baseline_arrival_timestep <= P - 1`（**P − 1 を含み、P 到着は除外**）

候補から除外：A 型、確定済み Visit、`baseline_arrival_timestep > P - 1`、snapshot 固定集合外 Visit

正式 baseline 順：`baseline_arrival_timestep` → `arrival_tiebreaker` → `vehicle_id` の昇順で明示ソート（collector export 順は使用しない）

**情報充足判定（§25.25.34.45 時点）**

- P − 1 該当候補**全件**を対象としていた（候補数上限は**適用しない**）
- 候補全員の `baseline_passage_timestep` が非 `None` なら `BASELINE_INFORMATION_COMPLETE`
- 1 件でも `None` なら `UNRESOLVED_CANDIDATE_PASSAGES`。未解決 Visit を `candidate_visits` から除外しない
- 情報取得済み Visit だけを使う部分的 TVT を作らない

**責任境界**

- collector、baseline fork 結果、alignment 結果、先行確定結果、権利保有選定結果、real_W、fork_W を変更しない
- upstream 処理を再実行しない。fork を延長・再実行しない
- TVT-SB、TVT-MH、TVT-SP、TVT-MP の買い手集合を生成しない
- 売り手選定、trade rank、局所仮想計算、経済評価、最終順位確定を行わない

**テスト結果（§25.25.34.45 時点）**

| 実行 | 結果 |
|------|------|
| `py_compile` | 成功 |
| `python tests_order_control_tvt_candidate_visit_set.py` | **15 tests passed** |
| `pytest tests_order_control_tvt_candidate_visit_set.py` | **15 passed** |
| `python tests_order_control_tvt_right_of_entry_selection.py` | **16 tests passed** |
| `python tests_order_control_tvt_leading_nonparticipating_confirmation.py` | **23 tests passed** |
| `python tests_order_control_tvt_arrived_undetermined_confirmation.py` | **30 tests passed** |
| `python tests_order_control_tvt_node_rank_state.py` | **54 tests passed** |
| `python tests_order_control_tvt_baseline_alignment.py` | **25 tests passed** |
| `python tests_order_control_tvt_baseline_fork_alignment.py` | **24 tests passed** |
| `git diff --check` | 問題なし |

主な確認内容：5 status、P − 1 境界（P 到着の除外）、A 型・確定済み除外、非参加 Visit を候補に含める、正式 baseline 順・同着順位、passage 未解決時の母集団全体保持、権利保有 Visit の通常条件による包含、複数 Node、読取入力不変、upstream 非再実行、`passage >= arrival + 1` の時系列整合、重大不整合

**Git 状態（§25.25.34.45 記録時点）**

- 作業開始時点の最新保存済み・push 済みコミットは **`fd807ff`**
- 新規本番モジュールと専用テストは未追跡の作業ツリーに存在する
- **§25.25.34.44** の設計メモ変更は未コミットで維持されている
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

**当時の次の再開地点**

- §25.25.34.45 時点では、具体的買い手集合生成へ直行せず、TVT 候補 Visit 数の上限を制度・実装上どう適用するかを整理することが次の設計対象になった
- その整理は **§25.25.34.46** で行われた。**詳細と実装結果は今回の最新作業として別途記録する**

##### 2026-09-09追記：TVT候補Visit母集団へTVT固有可変上限Nを実装

**位置づけ**

- 詳細正本は設計メモ **§25.25.34.47**
- 実装前仕様は **§25.25.34.46**
- **§25.25.34.45** は可変上限適用前の上限なし版の歴史的実装記録
- **§25.25.34.47** は、可変上限 N 適用後の実装結果、検証結果、未実装境界、次の再開地点の最新正本
- 既存の候補集合処理を破棄せず、前向きに拡張した

**非技術的な目的**

- 権利保有 Visit の通過予測時点 P の 1 タイムステップ前までに到着すると予測される Visit を正式 baseline 順へ並べ、その先頭から最大 N 件だけを今回の TVT 候補 Visit とする処理を実装した
- N は固定値 10 ではなく、基本値 10、感度分析値 15・20 などを呼出側から変更できる
- 非参加 Visit も N 件に数える
- 上限内候補に不足情報があっても、情報取得済みの後順位 Visit を繰り上げない
- 情報充足判定は、上限適用後の候補 Visit だけを対象とする

**変更内容**

- 変更本番モジュール：`uxsim/order_control_tvt_candidate_visit_set.py`
- 更新専用テスト：`tests_order_control_tvt_candidate_visit_set.py`
- 公開関数：`build_tvt_candidate_visit_set`
- 追加必須 keyword-only 引数：`max_tvt_candidate_visit_count`

**重要な契約**

- default 値なし。1 回の呼出しで全 target Node へ同じ上限を適用する
- Node 別 `Mapping` は受け取らない
- `type(value) is int` かつ 1 以上を要求する。`bool`、`0`、負数、`float`、文字列、`None` は `ValueError`
- 不正値では collector 照会前に停止する
- BATCH の `batch_size`、`max_batch_size` 等を再利用しない
- World、Node、順位状態へ新しい上限属性を追加していない

**候補選定と情報充足**

- P − 1 条件を満たす現在順位未確定の B 型 Visit を、到着タイムステップ、固定 tiebreaker、Vehicle ID の順に並べる
- 正式 baseline 順位の先頭から最大 `max_tvt_candidate_visit_count` 件を `candidate_visits` とする
- 権利保有 Visit と非参加 Visit も上限に数える。参加状態による繰上げを行わない
- N + 1 位およびそれより後順位は `candidate_visits` へ含めない
- 上限外 Visit の passage 不足は今回の情報充足判定へ影響させない
- 上限内 Visit の passage が不足していても、その Visit を除外して後順位 Visit を繰り上げない
- 上限内候補の 1 件でも passage が `None` なら `UNRESOLVED_CANDIDATE_PASSAGES`
- 上限内候補全員の passage が非 `None` なら `BASELINE_INFORMATION_COMPLETE`
- 既存 5 status は変更していない。上限専用 status は追加していない

**二段階検証（要点）**

- 第 1 段階：P − 1 該当 Visit 全件について、先頭 N 件を正しく選ぶための順位材料を検証する
- 第 2 段階：正式 baseline 順の先頭 N 件だけを完全な候補要素へ変換し、passage や `route_next_link_name` 等を検証する
- 上限外 Visit の候補情報不足を今回の候補処理へ不要に影響させず、順位選定に必要な情報の異常は上限外でも検出する
- 詳細は設計メモ **§25.25.34.47** を参照する

**結果型の変更**

- `OrderControlTvtCandidateVisitSetResult`：`max_tvt_candidate_visit_count: int`（今回の関数呼出しで全 target Node へ使用した上限。感度分析と結果再現のため全体結果へ保持）
- `OrderControlTvtNodeCandidateVisitSetResult`：`p_minus_one_eligible_visit_count_before_limit: int | None`（P − 1 条件を満たした Visit の上限適用前件数。P 取得前 status では `None`、P 取得済み status では非負 `int`。上限適用後件数は `len(candidate_visits)` で確認できる）
- 内部実装：`_PMinusOneRankEntry` を内部 frozen dataclass として追加（公開結果型ではない。collector が返した record コピーを一時保持し、公開結果へ残さない）

**テスト修正で発見した問題**

- 専用テストは **15 件から 21 件**へ増加した
- 当初の `test_nth_unresolved_candidate_does_not_promote_later_visit` は `N=3`、候補 3 件のため、3 位が N + 1 位になっておらず繰上げ禁止を検証できていなかった
- 実際のテスト本文確認により問題を発見し、当該テストだけを `N=2` へ修正した
- 修正後：1 位と未解決の 2 位だけが候補、passage 取得済みの 3 位を繰り上げない、`UNRESOLVED_CANDIDATE_PASSAGES`
- このテスト修正では本番コードを変更していない

**型注釈修正**

- `_verify_right_of_entry_record` の戻り値型を `tuple[int, int]` から `tuple[int, int | None]` へ修正した
- 権利保有 Visit の baseline passage は未解決時に `None` となり得る。処理動作の変更ではない

**確認とテスト結果（§25.25.34.47）**

- §25.25.34.46、本番モジュール全文、追加テスト本文を確認した
- 戻り値型注釈の不一致を発見して修正した
- 当初の繰上げ禁止テストが N + 1 位を構成していないことを発見し、`N=2` 修正後の本文を確認した
- §25.25.34.46 との不一致や実装を止める問題は残っていない

| 実行 | 結果 |
|------|------|
| `py_compile` | 成功 |
| `python tests_order_control_tvt_candidate_visit_set.py` | **21 tests passed** |
| `pytest tests_order_control_tvt_candidate_visit_set.py` | **21 passed** |
| `python tests_order_control_tvt_right_of_entry_selection.py` | **16 tests passed** |
| `python tests_order_control_tvt_leading_nonparticipating_confirmation.py` | **23 tests passed** |
| `python tests_order_control_tvt_arrived_undetermined_confirmation.py` | **30 tests passed** |
| `python tests_order_control_tvt_node_rank_state.py` | **54 tests passed** |
| `python tests_order_control_tvt_baseline_alignment.py` | **25 tests passed** |
| `python tests_order_control_tvt_baseline_fork_alignment.py` | **24 tests passed** |
| `git diff --check` | 問題なし |

**未実装境界**

- snapshot 時点の inlink 内物理順の独立保存、snapshot physical order 結果型、inlink 別候補列、買い手 prefix
- TVT-SB、TVT-MH、TVT-SP、TVT-MP の具体的買い手集合生成
- 参加 Mapping による買い手選定、trade scope、売り手選定
- 局所仮想計算、経済評価、最終順位確定の上位接続、上位 TVT 制御
- collector 登録順や export 順へ snapshot 物理順の意味を追加していない
- 現時点では単車線研究を正式対象とし、複車線への完全対応を現段階で作り込まない

**次の再開地点**

- TVT 候補 Visit 母集団への可変上限 N 適用は実装・検証済み
- 次は、snapshot 時点の inlink 内物理順を独立した固定情報としてどの結果型へ保存し、後続へ渡すかを設計する
- 物理順保存後、上限適用済み `candidate_visits` と照合して inlink 別候補列を構築する
- 具体的買い手集合生成はその後。局所仮想計算と経済評価にはまだ進まない

**Git 状態（§25.25.34.47 記録時点）**

- HEAD は **`0c7c144`**
- 未コミット変更：`uxsim/order_control_tvt_candidate_visit_set.py`、`tests_order_control_tvt_candidate_visit_set.py`、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`、本進捗メモ（`ORDER_EXCHANGE_PROGRESS.md`）
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

##### 2026-09-09追記：snapshot時点のinlink内物理順の保存・受渡し実装前設計を確定

**詳細正本：** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§25.25.34.48**

**設計の経緯**

- Composer 2.5 の一次調査、Grok 4.6 の反証レビュー、実コードと既存設計メモの直接確認を実施した
- `RegistrationPlan` で物理順を構築し、baseline fork 後は物理順だけを `OrderControlBaselineForkResult` へ残す設計を確定した
- `RegistrationPlan` 全体は保持しない

**確定した保存・受渡し設計**

- 単車線 inlink の `inlink.vehicles` deque 順を正本とする
- index 0 が対象 Node に最も近い物理先頭である
- Node 名、inlink 名、先頭から後方へ並べた VisitKey tuple を保存する
- 整数順位、Vehicle、Link、Node、World オブジェクト参照、`Vehicle.x` は保存しない
- A 型と B 型を同一 inlink 内物理順へ統合する
- 非参加 Visit も物理順へ含める
- snapshot 固定 Visit が 0 件の inlink は `inlink_physical_orders` から省略する
- snapshot 固定 Visit を 1 件以上含む inlink だけ `number_of_lanes == 1` を要求する
- 対象 Node の全 inlink を無条件に複車線拒否しない
- 研究対象外 Vehicle 向けの追加 blocker 処理は作らない
- 可変上限 N の選択基準は変更しない
- `candidate_visits` との照合、inlink 別候補列、prefix 生成は未実装である

**主要本文の更新**

- 詳細設計メモの **§1.2**、**§7**、**§9**、**§24**、**§25.25** に実装前設計確定の更新注記を追加した

**今回の作業範囲**

- 今回は Markdown 2 ファイルだけを変更した
- Python コードとテストは未変更である
- snapshot 物理順の Python 実装は未着手である

**次の再開地点**

- **§25.25.34.48** の実装前仕様と、実コードの型定義・結果生成・直接コンストラクター利用箇所を最終照合する
- その後、snapshot モジュールと baseline driver へ物理順保存・受渡しを実装する
- 実装完了時にも、詳細正本・主要本文・本進捗メモを同時更新する
- 物理順保存完了後、`candidate_visits` との照合による inlink 別候補列の設計へ進む
- 具体的買い手集合生成はさらにその後である
- 局所仮想計算と経済評価にはまだ進まない

**Git 状態（§25.25.34.48 記録時点）**

- HEAD は **`0e4084c`**
- 今回の変更：`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`、本進捗メモ（`ORDER_EXCHANGE_PROGRESS.md`）
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

##### 2026-09-09追記：snapshot時点のinlink内物理順の保存・受渡しを実装

**詳細正本：** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§25.25.34.49**

**実装前仕様：** **§25.25.34.48**

**変更した本番（2 ファイル）：**

- `uxsim/order_control_baseline_snapshot.py`
- `uxsim/order_control_baseline_driver.py`

**実装内容（要約）：**

- 新しい物理順型 `OrderControlBaselineSnapshotInlinkPhysicalOrder` を追加した
- `OrderControlBaselineSnapshotRegistrationPlan.inlink_physical_orders` と `OrderControlBaselineForkResult.inlink_physical_orders` を必須フィールドとして追加した（default なし）
- `inlink.vehicles` の index 0 から snapshot 固定 Visit を保存する
- A 型・B 型を統合し、非参加 Visit も含める
- 固定 Visit 0 件の inlink は省略する
- 固定 Visit を含む inlink だけ単車線検証する
- 一般 driver と TVT driver で同じ tuple を `ForkResult` へ渡す
- `RegistrationPlan` 全体、collector、candidate 結果型へは保存しない
- 可読性重視で物理順収集・単車線検証・集合照合・全体構築を helper へ明示分割した

**検証結果：**

- py_compile：本番 2 ファイルとテスト 9 ファイルすべて成功
- 直接実行：`tests_order_control_baseline_snapshot.py` 直接実行成功（`TESTS` 件数 100）、`tests_order_control_baseline_driver.py` 69 tests passed、`tests_order_control_tvt_snapshot_undetermined_registration.py` 25 tests passed、`tests_order_control_tvt_baseline_driver_registration.py` 32 tests passed、`tests_order_control_tvt_baseline_fork_alignment.py` 25 tests passed、`tests_order_control_tvt_arrived_undetermined_confirmation.py` 30 passed、`tests_order_control_tvt_leading_nonparticipating_confirmation.py` 23 passed、`tests_order_control_tvt_right_of_entry_selection.py` 16 passed、`tests_order_control_tvt_candidate_visit_set.py` 21 passed
- pytest：上記 9 ファイル 341 passed
- git diff --check：問題なし

**未実装：**

- `candidate_visits` との照合、inlink 別候補列、prefix

**次の再開地点：**

- 上限適用済み `candidate_visits` と保存済み `inlink_physical_orders` の照合による inlink 別候補列の実装前設計

**Git 状態（§25.25.34.49 記録時点）：**

- 実装完了記録追加前の HEAD は **`1eb3f87`**
- 実装完了記録追加前の変更：本番 2 ファイル、テスト 9 ファイル
- 今回の変更：本設計メモ（`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`）、本進捗メモ（`ORDER_EXCHANGE_PROGRESS.md`）のみ
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

##### 2026-09-10追記：TVT候補VisitのNode別・inlink別snapshot物理順整理の実装前設計を確定

**詳細正本：** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§25.25.34.50**

**設計の要点：**

- 上限適用済み `candidate_visits` を Node 別・inlink 別へ整理する読取専用部品を設計した
- 各 inlink 内は snapshot 物理順（Node へ近い側から後方へ）である
- inlink 上の物理的な前後順であり、対象 Node における全 inlink 横断の正式 baseline 順位番号の連続を意味しない
- 権利保有 inlink も結果へ含める
- この段階では買い手・売り手・prefix を決めない
- 権利保有車両と同じ inlink から買い手を選ばない処理は後続の買い手生成時とする
- 売り手は所属 inlink ではなく trade_scope の共通規則で決まる

**新規モジュール候補：**

- `uxsim/order_control_tvt_inlink_candidate_physical_order.py`
- `tests_order_control_tvt_inlink_candidate_physical_order.py`

**既存処理は変更しない：**

- `build_tvt_candidate_visit_set` の候補選定
- 可変上限 N
- snapshot 物理順保存（`order_control_baseline_snapshot.py` / `order_control_baseline_driver.py`）

**今回の作業範囲：**

- 今回は Markdown 2 ファイルだけを変更した
- Python コードとテストは未変更である

**次の再開地点：**

- **§25.25.34.50** の実装前仕様と実コードの最終照合
- 新規読取専用モジュールと専用テストの実装
- 実装完了時にも詳細正本・主要本文・本進捗メモを同時更新する

**Git 状態（§25.25.34.50 記録時点）：**

- HEAD は **`751a146`**
- 今回の変更：本設計メモ（`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`）、本進捗メモ（`ORDER_EXCHANGE_PROGRESS.md`）のみ
- `diagnostics/order_control.zip` は既存未追跡、未接触、対象外
- git add、git commit、git push は未実行

##### 2026-09-11追記：TVT候補VisitのNode別・inlink別snapshot物理順整理を実装

**詳細正本：** `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md` **§25.25.34.51**

**実装前仕様：** **§25.25.34.50**

**実装内容：**

- 新規本番モジュール `uxsim/order_control_tvt_inlink_candidate_physical_order.py` と専用テスト `tests_order_control_tvt_inlink_candidate_physical_order.py`
- 3 つの frozen 結果型（`OrderControlTvtInlinkCandidateVisitPhysicalOrder`、`OrderControlTvtNodeInlinkCandidatePhysicalOrderResult`、`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`）
- 公開関数 `build_tvt_inlink_candidate_physical_orders`
- 上限適用済み `candidate_visits` を inlink 別 snapshot 物理順へ整理（対象 Node における全 inlink 横断の正式 baseline 順位番号とは別）
- 権利保有 inlink、権利保有 Visit、非参加 Visit を含める
- A 型 Visit と上限外 Visit は含めない
- status 別処理（正当な非構築 status は空結果、候補集合確定済み status は整理）
- 想定外 `build_status` は `RuntimeError`（正常な空結果として隠さない）
- 読取専用（upstream 再実行・入力変更なし）
- 買い手、売り手、prefix は未実装
- 可読性重視の helper 分割と明示的な途中変数

**検証：**

- py_compile 成功
- 専用テスト 25 件成功（`TESTS` 重複なし）
- 既存回帰 316 件成功
- 合計 341 件成功
- git diff --check 問題なし

**次の再開地点：**

- 買い手候補 inlink 抽出と買い手 prefix の実装前設計

**Git 状態（§25.25.34.51 記録時点）：**

- HEAD は **`9996b0b`**
- 実装完了記録追加前の変更：新規本番・専用テスト（未コミット）
- 今回の変更：本設計メモ、本進捗メモのみ
- `diagnostics/order_control.zip` は未接触、対象外
- git add、git commit、git push は未実行

##### 2026-09-14追記：TVT設計メモ継続版とTVT-MP一般形最新正本を作成

**位置づけ**

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`を、既存の`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`の継続版として新規作成した。
- 新メモはTVT-MPだけの専用メモではなく、今後のTVT設計・実装記録の主要な追加先である。
- 非参加Visitの有無を統一して扱うTVT-MP一般形アルゴリズムについては、新メモを最新正本とする。
- 旧メモは歴史的記録および実装済み事実の記録として維持する。
- 旧メモ§25.25.34.51までの実装済み事実は引き続き有効である。

**今回確定した一般形の中核**

- 各買い手候補inlinkについて、空prefixから最大prefixまでの全prefixを生成する。
- 最前方の非参加Visitが存在する場合、そのVisitが最大prefix長を制限する。
- 各inlinkのprefix直積から、全空組合せだけを除外して具体的買い手候補集合を作る。
- `trade_scope`の日本語表記を「取引候補別順位再構成範囲」とする。
- 非参加Visitのbaseline局所順位を固定し、残る空き順位の先頭側へ買い手、その後へ売り手をbaseline相対順で配置する。
- この空き順位枠方式は、非参加Visitが0件の場合にも同じ一般形として使用する。
- TVT-MP一般形を直接実装し、TVT-SB、TVT-MH、TVT-SPは当面実装しない。
- `surplus`が同値の場合は取引当事者総数ではなく買い手数が多い候補を優先し、買い手数も同じ場合はランダムに選ぶ。
- ランダム選択に使用する具体的RNGは未確定である。
- `UNRESOLVED_CANDIDATE_PASSAGES`ではinlink別snapshot物理順を保持するが、prefixおよび具体的買い手候補集合を生成しない。

**実装状態**

- `candidate_visits`の構築、TVT固有可変上限N、inlink別snapshot物理順整理は実装済みである。
- 非参加Visitなしの一具体的候補に対する順位計算部品と`preserves_inlink_fifo()`は実装済みである。
- 買い手候補inlink、買い手prefix、具体的買い手候補集合、非参加Visitあり・なしを統一する一般形順位再構成、および後続の上位接続は未実装である。
- 今回はMarkdownメモだけを変更し、Pythonとテストは変更していない。

**次の作業開始点**

- 新メモの「次の作業開始点」を最新の再開情報とする。
- 次の直接作業は、具体的買い手候補集合生成部品の実装前仕様を、既存の公開型と接続できる形で確定することである。
- 一般形順位再構成の実装は、その次とする。

**Git状態**

- 記録作成前の最新保存済み・push済みコミットは`b5af3da`である。
- 新規メモと今回の相互参照は、まだ`git add`、`git commit`、`git push`していない。
- `diagnostics/order_control.zip`は既存未追跡、未接触、対象外である。
- Git操作は利用者がTerminalで実行し、コミットとpushを分ける。
- メモを含むコミット名には`document`を含める。

##### 2026-09-14追記：TVT-MP具体的買い手候補集合生成部品の実装前仕様を確定

**最新正本**

- 最新正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「具体的買い手候補集合生成部品の実装前仕様」である。
- TVT-MP一般形を直接実装する。
- TVT-SB、TVT-MH、TVT-SPは当面実装しない。
- 旧メモは歴史的記録として維持し、今回は変更していない。

**公開APIとファイル候補**

- 入力は`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`である。
- 参加Mappingは`participates_by_visit_key`である。
- 公開関数候補は`build_tvt_mp_concrete_buyer_candidate_sets`である。
- 新規本番候補は`uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py`である。
- 新規専用テスト候補は`tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`である。
- 公開結果型は次の4つのfrozen dataclassである。
  - `OrderControlTvtMpInlinkBuyerPrefixResult`
  - `OrderControlTvtMpConcreteBuyerCandidateSet`
  - `OrderControlTvtNodeMpConcreteBuyerCandidateSetResult`
  - `OrderControlTvtMpConcreteBuyerCandidateSetResult`

**生成規則**

- 権利保有inlinkを買い手候補から除外する。
- 最前方非参加Visitで最大prefixを打ち切る。
- 各買い手候補inlinkに空prefixから最大prefixまでの全prefixを作る。
- prefix直積の全空組合せだけを除外する。
- 具体的買い手候補集合を、`candidate_visits`内の対象Nodeへ向かう全inlink横断の正式baseline相対順へ並べる。
- `max_prefix`を別フィールドへ重複保存しない。
- 権利保有inlink名を結果へ重複保存しない。
- 本番処理で重複除去や重複検出用seen setを追加しない。

**status**

- `BASELINE_INFORMATION_COMPLETE`だけで生成する。
- 他の正式statusでは空結果とする。
- 想定外statusは`RuntimeError`とする。
- `UNRESOLVED_CANDIDATE_PASSAGES`ではprefixも具体的買い手候補集合も生成しない。

**実装状態**

- Python実装とテストは未着手である。
- 今回はMarkdownだけを変更し、Pythonとテストは変更していない。
- 次は新規本番モジュールと専用テストの実装である。
- その後、一般形順位再構成の実装前仕様へ進む。
- 局所仮想計算と経済性評価にはまだ進まない。

**Git状態**

- HEADは`9477c73`である。
- `diagnostics/order_control.zip`は未接触、対象外である。
- git add、git commit、git pushは未実行である。

##### 2026-09-15追記：TVT-MP具体的買い手候補集合生成部品を実装・検証

**位置づけ**

- 実装前仕様はコミット`8d57cd9`に保存・push済みであった（documentメモ）。
- その保存済み仕様に従い、新規本番`uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py`と専用テスト`tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`を実装した。
- 既存Python、既存テスト、旧メモ`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`は変更していない。
- 実装完了記録の正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「具体的買い手候補集合生成部品の実装完了記録」である。実装前仕様節は維持する。

**公開API**

- 公開関数`build_tvt_mp_concrete_buyer_candidate_sets`。
- 入力`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`と`participates_by_visit_key`。
- 公開frozen dataclass 4つ（`OrderControlTvtMpInlinkBuyerPrefixResult`、`OrderControlTvtMpConcreteBuyerCandidateSet`、`OrderControlTvtNodeMpConcreteBuyerCandidateSetResult`、`OrderControlTvtMpConcreteBuyerCandidateSetResult`）。
- 全体結果は入力`inlink_candidate_physical_order_result`を同一オブジェクト参照で保持する。

**実装内容の要点**

- `BASELINE_INFORMATION_COMPLETE`だけでprefixと具体的買い手候補集合を生成する。
- 正式非生成4 statusでは参加Mappingを検証せず、両結果tupleを空とする。
- `UNRESOLVED_CANDIDATE_PASSAGES`では部分的TVTを防ぎ、生成しない。
- 権利保有inlinkをprefixと直積から除外する。
- 最大prefix、全prefix、`itertools.product`、全空組合せのみ除外、対象Nodeへ向かう全inlink横断の正式baseline相対順への並べ替えを実装した。
- 必要最小限の`ValueError`と`RuntimeError`のみ。重複除去とseen setは行わない。
- 読取専用。上流再実行なし。

**確認済みテスト（Copilotと利用者がTerminalで確認）**

- 新規2ファイル`py_compile`成功。
- 新規専用テスト：直接実行およびpytestで各63 passed、収集63、定義`test_`63、`TESTS`63（重複・漏れ・未知参照なし）。
- 既存回帰5ファイル：200 passed。
- 合計263件成功。

**現在地（未実装境界）**

- 買い手候補inlink抽出、買い手prefix、具体的買い手候補集合は実装済み。
- 引き続き未実装：非参加Visitあり・なしを統一した一般形順位再構成、一般形順位再構成の結果型、`trade_scope`の一般形実装、3分類、非参加Visitのbaseline局所順位枠固定、空き順位枠方式のPython実装、一般形`trade_rank`/`trade_order`、候補別FIFO接続、局所仮想計算、経済性評価、成立候補選択、支払いと補償、各場合の最終確定列、確定順位ブロックへの上位接続、上位TVT制御、TVT-SB/MH/SP、性能最適化。

**次の作業開始点**

- 一般形順位再構成を直ちにコーディングしない。
- 既存非参加Visitなし順位計算部品と`preserves_inlink_fifo()`の契約を再確認し、確定済み空き順位枠方式を基礎に一般形順位再構成部品の**実装前仕様**を確定する。

**Git状態（記録時点）**

- 実装前仕様メモの保存済みコミットは`8d57cd9`（push済み）。
- 新規本番・新規専用テスト・本進捗追記・継続版メモ追記は、まだ`git add`、`git commit`、`git push`していない。
- 未追跡：`uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py`、`tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`、`diagnostics/order_control.zip`（対象外）。
- `diagnostics/order_control.zip`は未接触、対象外である。

##### 2026-09-15追記：TVT-MP一般形順位再構成部品の実装前仕様を確定

**最新正本**

- 詳細正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP一般形順位再構成部品の実装前仕様」である。
- 空き順位枠方式の制度ロジックは継続版メモで既に確定済みである。今回確定したのは、その制度ロジックを実装・検証済みの具体的買い手候補集合生成部品および既存の非参加Visitなし順位計算部品へ接続する完全な実装前仕様である。
- 具体的買い手候補集合生成部品の保存済み実装コミットは`2764f0c`である。このhashを一般形順位再構成の実装コミットとして扱わない。
- 旧メモは変更していない。

**公開APIとファイル候補**

- 新規本番候補は`uxsim/order_control_tvt_mp_general_trade_rank.py`である。
- 新規専用テスト候補は`tests_order_control_tvt_mp_general_trade_rank.py`である。
- 入力は`OrderControlTvtMpConcreteBuyerCandidateSetResult`と`participates_by_visit_key`である。
- 公開関数候補は`build_tvt_mp_general_trade_ranks`である。
- 一般形専用結果型を新設する。一候補結果は読取専用クラス、対象Node別結果と全体結果はfrozen dataclassである。

**生成規則の要点**

- 非参加Visitあり・なしを空き順位枠方式で統一する。
- `trade_scope`と`nonparticipating_visits_sorted`を一候補結果に保存する。
- `trade_rank`をprivateな防御コピーとして保持し、`assigned_rank`と`trade_rank_items`で読み取る。
- FIFO検査は後続責務であり、この部品では`preserves_inlink_fifo`を呼ばない。
- 非参加Visit0件では既存部品との同値性を専用テストで確認する。
- 既存順位計算部品と`preserves_inlink_fifo`は変更しない。

**実装状態**

- Python実装と専用テストはまだ未着手である。
- 次の直接作業は、この保存済み実装前仕様に従う新規本番と専用テストの実装である。
- 局所仮想計算、経済性評価、FIFO実行にはまだ進まない。
- git add、git commit、git pushはまだ行っていない。

**Git状態（記録時点）**

- 具体的買い手候補集合生成部品の保存済み・push済みコミットは`2764f0c`である。
- 本実装前仕様のMarkdown追記は、まだ`git add`、`git commit`、`git push`していない。
- `diagnostics/order_control.zip`は対象外の未追跡ファイルのままである。

##### 2026-09-15追記：TVT-MP一般形順位再構成部品を実装・検証

**正本と前提**

- 一般形順位再構成部品の実装前仕様は、コミット`3932f21`へ保存・push済みであった。
- 詳細正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP一般形順位再構成部品の実装前仕様」および同ファイルの「TVT-MP一般形順位再構成部品の実装完了記録」である。
- 保存済み仕様に従い、新規本番`uxsim/order_control_tvt_mp_general_trade_rank.py`と新規専用テスト`tests_order_control_tvt_mp_general_trade_rank.py`を実装した。

**実装の要点**

- 公開関数`build_tvt_mp_general_trade_ranks`と3結果型（一候補読取専用クラス、対象Node別frozen dataclass、全体frozen dataclass）。
- 確定済み空き順位枠方式、`trade_scope`、買い手・売り手・非参加Visitの3分類、非参加Visitのbaseline局所順位固定、`trade_rank`正本と`trade_order`派生。
- 非参加Visit0件では、既存`build_tvt_trade_rank_without_nonparticipants`と専用テストで同値性を確認した（本番からは既存関数を呼ばない）。
- FIFO検査の実行は未実装であり、後続のFIFO検査接続部品の責務である。

**独立反証レビューとテスト補強**

- Cursor Grok 4.6による独立反証レビューで、重大0・要修正0であった（軽微6件は仕様違反ではなく任意改善またはテスト弱点）。
- 反証後は本番の制度ロジックは変更せず、専用テストを補強した（keyword-only、`trade_scope`外非参加Visit、結果クラスコンストラクター契約など）。
- 正常な上流制度契約を破る売り手0件の公開関数経由テスト2件（`test_zero_sellers`、`test_zero_nonparticipants_zero_sellers_matches_existing`）を削除した。結果クラス単体の空`sellers_sorted`形式契約は別テストとコメントで区別している。

**確認済みテスト**

- 新規専用132件、既存回帰6ファイル263件、合計395件成功。
- Copilotと利用者が本番コード、中核テスト、Terminal結果を確認済みである。

**未実装境界（概略）**

- 候補別FIFO接続（`preserves_inlink_fifo()`への接続と違反候補棄却）、局所仮想計算、経済性評価、成立候補選択、支払い・補償、各場合の最終確定列、確定順位ブロックへの上位接続、上位TVT制御、TVT-SB/MH/SP、性能最適化。

**次の作業開始点**

- `trade_scope`と`trade_order[:last_buyer_rank]`を既存`preserves_inlink_fifo()`へ接続するFIFO検査接続部品の実装前仕様。一般形実装の再考や`preserves_inlink_fifo()`の変更は行わない。

**Git状態（記録時点）**

- 実装前仕様の保存済み・push済みコミットは`3932f21`のみをそのように記載する（新しい実装コミットhashは推測しない）。
- 新規本番・新規専用テスト・本進捗追記・継続版メモの実装完了記録追記は、まだ`git add`、`git commit`、`git push`していない。
- `diagnostics/order_control.zip`は対象外の未追跡ファイルである。

##### 2026-09-15追記：TVT-MP FIFO検査接続部品の実装前仕様を確定

**最新正本**

- 詳細正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP FIFO検査接続部品の実装前仕様」である。
- FIFO検査の制度ロジックは継続版メモ§20、§21で既に確定済みである。今回確定したのは、実装済み一般形順位再構成結果と既存`preserves_inlink_fifo()`へ接続する完全な実装前仕様である。
- 一般形順位再構成部品の保存済み・push済み実装コミットは`1e23174`である。このhashをFIFO検査接続部品の実装コミットとして扱わない。
- 旧メモは変更していない。

**公開APIとファイル候補**

- 新規本番候補は`uxsim/order_control_tvt_mp_fifo_inspection.py`である。
- 新規専用テスト候補は`tests_order_control_tvt_mp_fifo_inspection.py`である。
- 入力は`OrderControlTvtMpGeneralTradeRankSetResult`である。
- `participates_by_visit_key`は不要である。
- 公開関数候補は`build_tvt_mp_fifo_inspection_results`である。
- 一候補、対象Node別、全体の3結果型は公開frozen dataclassである。

**接続規則の要点**

- 取引前は`trade_scope`、取引後は`trade_order[:last_buyer_rank]`を既存`preserves_inlink_fifo()`へ渡す。
- FIFO違反は`False`として結果へ残す正常な候補棄却である。例外ではない。
- FIFO違反候補を結果から削除せず、上流候補順と一対一対応を維持する。
- `preserves_inlink_fifo()`が`ValueError`を出した場合は重大不整合として`RuntimeError`へ変換する。
- `False`は例外変換しない。Python `bool`以外の戻り値は`RuntimeError`とする。

**実装状態**

- Python実装と専用テストはまだ未着手である。
- 次の直接作業は、この保存済み実装前仕様に従う新規2ファイルの実装である。
- 局所仮想計算、経済性評価、成立候補選択にはまだ進まない。
- git add、git commit、git pushはまだ行っていない。

**Git状態（記録時点）**

- 一般形順位再構成部品の保存済み・push済みコミットは`1e23174`である。
- 本実装前仕様のMarkdown追記は、まだ`git add`、`git commit`、`git push`していない。
- `diagnostics/order_control.zip`は対象外の未追跡ファイルのままである。

##### 2026-09-15追記：TVT-MP FIFO検査接続部品を実装・検証

- 実装前仕様はコミット`25764b8`へ保存・push済みであった。保存済み仕様に従い、新規本番`uxsim/order_control_tvt_mp_fifo_inspection.py`と新規専用テスト`tests_order_control_tvt_mp_fifo_inspection.py`を実装した。
- 公開関数は`build_tvt_mp_fifo_inspection_results`。公開frozen dataclassは`OrderControlTvtMpCandidateFifoInspectionResult`、`OrderControlTvtNodeMpFifoInspectionResult`、`OrderControlTvtMpFifoInspectionSetResult`の3つである。
- FIFO材料は取引前`trade_scope`、取引後`trade_order[:last_buyer_rank]`である。`inlink_name_by_visit_key`は対象Node単位で`candidate_visits`から一度だけ構築する。
- 各候補について既存`preserves_inlink_fifo()`を1回だけ呼び、結果フィールド`preserves_inlink_fifo`に厳密なPython `bool`を保存する。False候補を結果から削除せず、上流候補順と一対一対応を維持する。Falseは正常なFIFO違反であり、例外ではない。
- 接続部品が組み立てた材料に対する`preserves_inlink_fifo()`の`ValueError`は`RuntimeError`へ変換する（例外チェーン維持）。非bool戻り値は`RuntimeError`とする。
- 新規専用テスト66件成功（直接実行・pytest収集・`TESTS`登録66件、重複・漏れ・未知参照なし）。既存回帰395件と合わせ461件成功。新規2ファイルに空白エラーなし。
- Copilotと利用者が本番コード、主要テスト、Terminal結果を確認済みである。
- **未実装境界（概略）：** 局所仮想計算、経済性評価、成立候補選択、支払い・補償、最終確定列、確定順位ブロック接続、上位TVT制御、TVT-SB/MH/SP、性能最適化。詳細は継続版メモの実装完了記録と未実装境界更新注記を参照。
- **次の作業開始点：** `preserves_inlink_fifo=True`候補向けの候補別局所仮想計算接続部品の実装前仕様。FIFO検査接続・`preserves_inlink_fifo()`・一般形順位再構成は再考しない。直ちに局所仮想計算は実装しない。まず既存の局所仮想計算関係の設計・部品・入力要件を確認する。
- 新規2ファイルと本進捗追記・継続版メモの実装完了記録追記は、まだ`git add`、`git commit`、`git push`していない。実装前仕様の保存済み・push済みコミットとして記載するのは`25764b8`のみである。
- `diagnostics/order_control.zip`は対象外である（触れていない）。

##### 2026-09-18追記：TVT-MP候補別局所仮想計算の設計検討を開始

- FIFO検査接続の実装コミット`33e6101`は保存・push済みである。次の対象は`preserves_inlink_fifo=True`候補の局所仮想計算である。
- BATCH Level 2とFCFSの既存規則を調査した。BATCHはtrigger 1台の通過時刻と早期終了が主目的、TVTは経済評価に必要な複数Visitの通過時刻取得が目的であり、終了条件が異なる。
- 全Worldではなく局所計算とする制度上の理由は、同じ時点Tに他NodeのTVT結果が未確定であり、候補別全World計算が実際の将来Worldを表さないためである。計算負荷削減だけが理由ではない。
- `trade_order`を通過試行順とする基本方針を採用した。未到着・物理・容量制約は一時スキップ、クリアランス未充足は走査終了。一時スキップは正式順位の変更ではない。
- **2026-09-21注記：** 通過試行のskip/break規則は維持する。拘束対象を`trade_order`全体とする当時の方針は、後続の途中確定記録で`K_fixed`に基づく完全な局所拘束順位列へ更新した。完全な拘束順位列は`trade_order`の必要部分を材料に含み得るが、`trade_order`の単純prefixと同一とは限らない。最新は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」。
- baseline保存済み`route_next_link_name`を使用し、局所計算中に`route_next_link_choice()`を呼び直さない。
- 局所mimic Worldへ対象Nodeの全inlink・全outlinkとsnapshot時点の全Vehicleを含める案が有力。候補Visitだけを含める案は第一候補ではない。
- horizonは可変である。30や50に限定せず、計算負荷が許せば100以上も試す。一つの実験条件ではbaselineと局所計算で同じhorizonを使う。
- inlink始端の新規流入は未確定。BATCH式単純sinkはTVTでは保留。
- outlink終端の条件付き平均境界サービス案、流出許可残高の無期限繰越し、outlink流出容量と終端Node容量によるtimestep別物理制限が有力。active timestep 0では下流Link流入容量を使わない制約付きsink案。
- baseline境界観測機能はまだ存在せず、保存場所と観測位置は未確定。
- Python実装とテストは未着手。完全な実装前仕様は未作成。
- 次の直接作業は、baseline実行中の終端境界観測位置の調査。この調査が終わるまで実装前仕様を作らない。
- 今回のMarkdown追記は未コミット。`diagnostics/order_control.zip`は対象外である。

##### 2026-09-19追記：TVT下流境界観測の基本設計を確定

- 前回の設計検討記録はコミット`5dd4be9`（`Document the TVT-MP candidate local virtual calculation design study`）で保存・push済みである。
- Cursor Grok 4.6の報告だけで確定せず、既存コードとTerminal出力で独立確認した。
- TVTの初期研究範囲では`DELTAN=1`を制度上の前提とする。一つのVehicleオブジェクトを一台として扱う。検証位置と例外文は未確定。timestepごとの重複検証はしない方向。
- 下流境界は終端`Node.transfer()`の直前・直後で、`World.exec_simulation()`の共通呼出位置から観測する。標準・FCFS・BATCHの個別transferへ重複実装しない。
- activeは途中通過Vehicleの待機状態である。終端`incoming_vehicles`のうち`vehicle.link is monitored_outlink`が1台以上。
- 実流出台数は、transfer前に保持したVehicleがtransfer後に元のoutlinkを離れた数である。
- `cum_departure`差は正式台数の正本にしない。補助確認の余地は残す。
- 目的地到着Vehicleは平均境界集計対象外。途中通過Vehicleだけを集計対象にする。
- Nodeを端点・内部で一律分類せず、Vehicleごとの目的地判定を使う。端点Nodeもコード上は途中通過され得る。
- 一方通行限定ではなく、実在する有向Linkだけを扱う。存在しない逆方向Linkを補完しない。
- 下流境界専用observerをfork Worldだけで動かす方向。結果はbaseline結果の独立した読取専用情報とする方向。正式名称とフィールド名は未確定。
- 端点Nodeが誤ってorder control対象になる特殊構造は想定しないが、ネットワーク構築上の留意事項である。この誤設定を防ぐ新しい実行時検査は追加しない方向。
- Python実装とテストは未着手。完全な局所仮想計算実装前仕様は未作成。
- 次は実装前仕様に必要な残る設計判断を整理する。inlink始端新規流入、局所mimic World全体、経済性評価にはまだ進まない。
- 今回のMarkdown追記は未コミット。
- `diagnostics/order_control.zip`は対象外である。

##### 2026-09-19追記：TVT下流境界観測部品の完全実装前仕様を確定

- 基本設計コミット`c2c98c0`（`Document the TVT downstream boundary observation basic design`）は保存・push済みである。
- 下流境界観測部品の完全実装前仕様を確定した。Python実装とテストは未着手である。
- observer正式名は`OrderControlBaselineDownstreamBoundaryObserver`。World属性は`_order_control_baseline_downstream_boundary_observer`。
- 正式APIは`register_target_node_outlinks()`、`capture_before_transfer()`、`commit_after_transfer()`、`clear_pending()`、`export_result()`。
- 結果は3段frozen構造。outlink / 対象Node / 全体。`ForkResult`必須フィールドは`downstream_boundary_result`。
- 空baselineは`None`。観測済み0と未観測を区別する。
- 対象Nodeは`target_node_names`順。各Nodeのoutlinkはネットワーク登録順。同一終端Nodeを共有するoutlinkも独立結果。
- 同一outlink二重登録は`ValueError`。countだけを保存し、平均率は後段。
- transfer例外ではbaseline停止。部分結果なし。原因修正後は実Worldシミュレーションを最初から手動でやり直す。
- `DELTAN=1`はFCFS、BATCH、TVT共通。Node作成時と`set_order_control_for_nodes()`でだけ確認。timestep、baseline、observerでは再確認しない。処理名は`_validate_order_control_deltan`。
- 実装はobserver単体から開始する。新規モジュールは`uxsim/order_control_baseline_downstream_boundary.py`、専用テストは`tests_order_control_baseline_downstream_boundary.py`。
- 条件付き平均率、流出許可残高、局所mimic World、inlink始端、経済評価は対象外である。
- 今回のMarkdown追記は未コミット。
- `diagnostics/order_control.zip`は対象外である。

##### 2026-09-20追記：TVT下流境界observerの本体・hook・baseline driver正式接続を完了

- observer本体を専用モジュール`uxsim/order_control_baseline_downstream_boundary.py`へ実装済み（コミット`f475294`）。専用単体テスト`tests_order_control_baseline_downstream_boundary.py`。
- UXsimの共通transfer loop（`World.exec_simulation()`内）へhook済み（コミット`c72e38a`）。専用テスト`tests_order_control_baseline_downstream_boundary_uxsim.py`。
- FCFS、BATCH、TVTに共通するorder control設定時の`DELTAN=1`検査を実装済み（コミット`7c1d5a4`、`_validate_order_control_deltan`）。専用テスト17件成功。
- 全World baseline driver（`uxsim/order_control_baseline_driver.py`）へ正式接続済み（コミット`7f00520`）。専用統合テスト`tests_order_control_baseline_downstream_boundary_driver.py`（15件）。
- `OrderControlBaselineForkResult`へ必須フィールド`downstream_boundary_result`を追加済み（デフォルトなし）。
- 空baseline（`registered_visit_count == 0`）は`downstream_boundary_result = None`。`exec_simulation()`は呼ばない。
- 完了baselineは、全countが0でも観測済みfrozen結果を返す。未観測`None`と区別する。
- observerはfork Worldの`_order_control_baseline_downstream_boundary_observer`へだけ接続する。
- real Worldのobserver属性は開始前後とも`None`（開始前非`None`は`ValueError`、copy直後fork非`None`は`RuntimeError`）。
- observer登録失敗時はforwardを開始しない。部分observerをforkへ接続しない。
- forward失敗時は`export_result()`も完了結果作成も行わない。部分`ForkResult`を返さない。自動再試行しない。
- 結果順序：`target_node_names`順、`node.outlinks`登録順。同一終端Node共有outlinkを統合しない。
- 実装コミット：`7c1d5a4`、`c72e38a`、`7f00520`（およびobserver本体`f475294`）。
- `7f00520`は`origin/feature/intersection-order-control`へpush済み。
- Terminalで関連テスト493件を群ごとに確認し、すべて成功。`7f00520`で変更した8ファイルの`py_compile`成功。
- 存在しない`tests_order_control_fcfs_transfer.py`指定による最初のコマンド停止はテスト失敗ではない。Terminalで実在する正式な関連テストファイル名を再確認し、次の6ファイルを再実行して209件すべて成功した：`tests_order_control_baseline_collector.py`、`tests_order_control_baseline_collector_uxsim.py`、`tests_order_control_baseline_snapshot.py`、`tests_order_control_batch_node_transfer_integration.py`、`tests_order_control_batch_service_queue_transfer.py`、`tests_order_control_batch_transfer.py`。
- 条件付き平均流出率、流出許可残高、制約付きsink、局所mimic World、inlink始端新規流入、候補別局所仮想計算、経済性評価、成立候補選択、実WorldへのTVT反映は未実装。
- 次の再開地点：候補別局所仮想計算へ進むために必要な残る入力・境界設計の整理（本追記では新規制度確定しない）。
- 詳細は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「全World baseline下流境界観測部品の実装完了記録」を参照。
- `diagnostics/order_control.zip`は対象外である。

##### 2026-09-21追記：TVT-MP候補別局所仮想計算の入力・境界・順位拘束を途中確定

- 下流境界observerまでの実装は完了済みである。候補別局所仮想計算は未実装である。
- 今回、入力、下流境界、horizon、早期終了、順位拘束範囲について途中確定した。完全な実装前仕様ではない。
- 条件付き平均流出率方式を正式採用した。観測countを正本とし、局所計算側で必要時に算出する。baseline結果へ平均率を新たに保存しない。
- 流出許可残高の小数部分と未使用整数部分の繰越しを採用した。残高は具体的候補別、outlink別に独立する。初期残高は0。人工的な上限は設けない。残高は物理的に貯蔵された容量ではない。
- `active=0`は制約付きsinkへ分岐するが、具体実装は未確定である。`active=0`を無混雑の直接観測としない。
- 時点`T`以後の新規流入なしを初期実装方針として採用した。影響が存在しないとは主張しない。局所予測が楽観的になり得る。
- `configured_horizon_steps`をlocal horizon上限とする。別の自由入力horizonは設けない。全buyerと全sellerの必要情報が揃えば早期終了する。
- buyerとsellerは別に識別する。buyerだから短縮、sellerだから遅延とは決めつけない。時間差を局所結果側で計算するか経済評価側で計算するかは未確定である。
- `trade_order`全体を局所拘束順位として使用しない。局所仮想計算では、`K_fixed`制度に基づいて構築される完全な拘束順位列を使用する。この完全な拘束順位列は、`trade_order`の必要部分を材料に含み得るが、`N+1`位以降の意思決定窓内Visitも含み得るため、`trade_order`の単純prefixとは限らない。完全な拘束順位列を構築するための公開材料と接続方法は、次の直接調査事項である。それより後方のVehicleへbaseline順位を強制しない。
- `candidate_visits`、意思決定窓、`trade_scope`は別概念である。一般形順位の制度ロジックと順位アルゴリズム、FIFO検査接続は再考しない。ただし、既存の公開結果型を含めて一切変更不要であるとは確定しない。
- 拘束順位外Vehicleは標準transfer相当処理を用いる方向だが、詳細は未確定である。既存`Node.transfer()`を局所loop後段でそのまま呼ばない。
- 局所mimic Worldは対象Nodeと全inlink・全outlink、時点`T`に存在する全Vehicleを含む。候補Visitだけを抜き出す方式は採用しない。含めた全VehicleへTVT順位を付与しない。
- Python実装と専用テストは未着手である。
- 詳細正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」。
- 次の直接作業は、`K_fixed`に従う完全な局所拘束順位列を構築するために、現行の上流結果から取得可能なVisitと情報を調査し、不足する公開材料と最小の接続方法を確定することである。拘束順位を持たないVehicleへ適用するUXsim標準transfer相当処理の詳細設計は、その次の作業である。その後、制約付きsink、公開API、結果型、例外契約、専用テスト契約、完全な実装前仕様へ進む。
- 今回のMarkdown追記は未コミットである。
- `diagnostics/order_control.zip`は対象外である。

**2026-09-21注記（最新参照先）：** 上記「次の直接作業」は、当該途中確定記録作成時点の歴史的記録である。その後、完全な局所拘束順位列の4区分、順位確定時の正式進路保存、原子的確定、原因別最終分岐を追加途中確定した。最新正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録」。現在の直接作業は拘束順位外Vehicleの対象Node向け進路と処理方式の確定である。下記「2026-09-21追記（完全局所拘束順位列・正式進路・最終分岐）」を参照する。

##### 2026-09-21追記（完全局所拘束順位列・正式進路・最終分岐）

**現在状態**

- FIFO検査接続まで実装・検証済みである。
- 全World baseline下流境界observerまで実装・検証済みである。
- 候補別局所仮想計算は未実装である。
- Python実装と専用テストは未着手である。
- 候補別局所仮想計算全体の完全な実装前仕様は未確定である。
- 今回は、完全な局所拘束順位列、順位確定時の正式進路保存、最終分岐について追加の途中確定を行った。
- 詳細正本は、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の次の節である。「TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録」。

**完全な局所拘束順位列の4区分**

- **区分1：** 今回のbaseline開始前から順位確定済みで、局所計算開始時点で対象Nodeをまだ通過していないVisit。
- **区分2：** 今回のbaseline結果により、TVT候補形成前に先行確定するVisit。含むもの：baseline到着timestepがT以下と判明したVisit、意思決定窓先頭の連続する非参加Visit。
- **区分3：** 今回の具体的候補の`trade_scope`内のVisit。buyerとsellerには取引後順位。非参加Visitには固定されたbaseline順位枠。
- **区分4：** `trade_scope`外だが`K_fixed`内にあり、baseline順位で追加確定されるVisit。
- 完成順：区分1 → 区分2 → 区分3 → 区分4。
- 区分1はbaseline開始前の確定台帳から取得する。区分2は今回の先行確定処理結果を直接使用する。区分3は具体的候補の`trade_scope`内の取引後順位を使用する。区分4は`trade_scope`外かつ`K_fixed`内の正式baseline順位を使用する。
- `trade_order`全体を完全な局所拘束順位列として使用しない。`trade_order`の単純prefixだけで完全列を作れるとも扱わない。N+1位以降の意思決定窓内Visitも`K_fixed`内に含まれ得る。
- VisitはVehicle名だけでなく`VisitKey = (vehicle_name, visit_id)`で識別する。
- 4区分内および区分間の重複を認めない。重複や正式進路欠落を自動修正せず、不整合として停止する。

**正式進路**

- 定義：「そのVisitの順位確定をもたらした全World baselineにおいて、対象Nodeへの到着時にcollectorへ記録された`route_next_link_name`」。
- 単なる最新の`route_next_link`ではない。最初に予測された`route_next_link`でもない。
- baseline終了時のVehicleオブジェクトが現在保持する`route_next_link`を使用しない。
- 対象Node通過後に下流Nodeで選ばれた別の進路を使用しない。
- 候補ごとに`route_next_link_choice()`を呼び直さない。
- collectorはbaseline forkごとの寿命であり、確定時進路をサイクル間で保持できない。
- 現在の`OrderControlTvtNodeRankState`は正式進路を保持していない。
- 正式進路を`OrderControlTvtNodeRankState`へ確定順位と一体で保存する方針を採用した。
- 永続保存する最小情報はVisitKey、assigned rank、`route_next_link_name`である。
- 区分1は過去の確定時に保存した正式進路を使用する。区分2から4のうち今回正式確定するVisitは、今回baselineで記録された正式進路を使用する。

**原子的確定**

- 順位を正式に確定するすべてのVisitについて、確定順位と対象Node向け正式進路を同時に保存する。
- 区分1は過去に保存済みなので、今回改めて保存しない。
- 今回新たに確定するVisitは、全件検証後に順位と正式進路を一括反映する。一件でも不整合があれば、順位も進路も一件も反映しない。
- 順位だけ確定し、進路だけ欠ける部分更新を認めない。
- 既存`confirm_visits_in_order()`は直ちに削除しない。今後の本番TVT確定経路は、新しい進路付き原子的確定APIへ移行する方向である。
- rank state自身はcollectorを直接参照しない。
- 正式API名と入力型は未確定である。
- 順位と正式進路を保存する処理に限れば、`baseline_passage_timestep`は必須入力ではない。`baseline_passage_timestep`が候補形成、局所評価、経済評価等の別目的で必要になる可能性は維持する。

**順位表構築と正式確定の分離**

- 候補別の完全な局所拘束順位表を作る処理は読取専用である。
- 候補評価中に順位台帳を変更しない。不採用候補の順位と進路を保存しない。
- 正式確定は最終結果決定後の別処理である。
- 採用候補が決定した場合、評価に使用した検証済み順位表を正式確定にも使用する。採用後に同じ順位表を再構築しない。
- 区分2は候補形成前に順位と正式進路を原子的に確定する。区分3と区分4は候補評価中には順位台帳へ保存しない。

**最終分岐**

「TVT検討なし」を一括表現として使用しない。原因別分岐：

1. **採用候補がある場合：** `trade_scope`内を採用候補の順位で確定する。`trade_scope`が意思決定窓より小さい場合、残る意思決定窓内Visitをbaseline順位で確定する（「残る意思決定窓内Visit」）。順位と正式進路を一括保存する。
2. **候補を評価した結果、全候補が却下された場合：** 全候補不採用、全候補未解決、不採用・未解決混在で採用0をすべて含む。意思決定窓内Visit全体をbaseline順位で確定する（「意思決定窓内Visit全体」）。
3. **必要なbaseline情報不足により候補形成・評価へ進めない場合：** TVT候補の形成と評価自体を行わない。不足の中心は通過情報。意思決定窓内Visitの到着情報と対象Node向け進路情報は取得される。意思決定窓内Visit全体をbaseline順位で確定し、順位と正式進路を一括保存する。
4. **意思決定窓内Visitが0件の場合：** TVT検討を行わない。確定対象も存在しない。「意思決定窓内Visit全体をbaseline順位で確定する」とは表現しない。

**K_fixed順位列構築部品**

- 完全な`K_fixed`拘束順位列を構築する独立部品を新設する方向を採用した。
- 局所仮想計算用と将来の最終確定処理用に別々の`K_fixed`ロジックを実装しない。同じ制度ロジックを共有する。
- 一般形順位再構成へ`K_fixed`後方列の責務を戻さない。
- 正式モジュール名、結果型、フィールド名、公開APIは未確定である。

**拘束順位外Vehicle（調査済みだが正式未確定）**

確認済み：

- 既存`Node.transfer()`を局所loop後段でそのまま呼ばない。
- 拘束順位Vehicleを後段で再評価しない。
- 同一timestep内では、拘束順位処理後に容量が残り、clearance breakがなければ、拘束順位外Vehicle処理へ進む構想である。
- 拘束順位Vehicle全員が将来通過し終わるまで待つ意味ではない。
- 拘束順位処理後の残容量だけを使う。同一timestepに容量を再充填しない。
- `incoming_vehicles`を全消去しない方向である。通過Vehicleだけを除く方向である。

BATCH Level 2から確認した参考情報：

- 進路状態A：対象Nodeからの進路が決定済みであり、その固定進路を使用する。
- 進路状態B：対象Nodeからの進路が未決定であり、Vehicle IDによる決定的方法で仮想進路を選ぶ。状態BではUXsim本来の`route_next_link_choice()`を呼ばない。
- Vehicle ID方式はBATCH Level 2の局所近似であり、UXsim本来の進路選択の再現ではない。この方式をTVTへ採用したとは扱わない。

未確定：拘束順位外Vehicleの対象Node向け進路の取得方法、進路未決定Vehicleの扱い、FCFS clearance相当処理の採用、merge_priority、乱数または局所RNG、clearanceの正式契約、trip-end待ち処理、専用物理移動helper、正式な結果型と診断情報。

**active=0**

- active=0時の制約付きsinkは未確定である。拘束順位外Vehicleの正式契約が確定した後に検討する。

**次の直接作業**

「拘束順位外Vehicleについて、対象Node向け進路をどこから取得し、進路未決定Vehicleをどう扱うかを確定する。その結果を踏まえ、同一timestep内の拘束順位外Vehicleの選択順、clearance、merge_priority、乱数、incoming保持、物理移動処理を正式確定する。」

この論点の後に、active=0時の制約付きsinkへ進む。

- 今回のMarkdown追記は未コミットである。
- `diagnostics/order_control.zip`は対象外である。

**2026-09-22注記（最新参照先）：** 上記「次の直接作業」と「拘束順位外Vehicleは正式未確定」「active=0は未確定」は、保存済みcommit `1613eb9`時点の歴史的記録である。その後、進路4分類、一時的FCFS、clearance、制約付きsink、統合仕様を確定した。最新正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」。現在の直接作業は完全な実装前仕様の作成である。下記「2026-09-22追記」を参照する。上記の未確定記述を現在の作業指示として読まない。

##### 2026-09-22追記：TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様を確定

**現在地点**

- FIFO検査接続まで実装・検証済みである。
- 全World baseline下流境界observerまで実装・検証済みである。
- 候補別局所仮想計算のPython実装と専用テストは未着手である。候補別局所仮想計算は未実装である。
- 保存済みcommit `1613eb9`までは、完全な局所拘束順位列の4区分、順位確定時の対象Node向け正式進路、順位と正式進路の原子的保存、候補別順位表構築と正式確定の分離、採用候補あり・全候補却下・baseline情報不足・意思決定窓内Visit 0件の原因別分岐を記録済みである。同commit時点では、拘束順位外Vehicleの処理とactive=0時の制約付きsinkは未確定であった。BATCH Level 2の進路状態A/Bは参考情報として記録されていた。
- 今回（2026-09-22）は、`1613eb9`以後に確定した未記録事項を追記した。実装完了記録ではない。制度設計および次の実装前仕様に向けた確定記録である。
- 制度設計上の主要採否判断は、本追記の範囲で完了した。公開API、結果型、helper名、診断のPython型を含む完全な実装前仕様は、まだ作成していない。
- 詳細正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」。
- Pythonファイルとテストファイルは今回変更していない。

**今回確定した拘束順位列と拘束順位外の関係**

- 完全な拘束順位列は、前回どおり区分1→区分2→区分3→区分4である。本追記で4区分の中身は変えない。
- 拘束順位列内のVisitがすべて到着する前に、拘束順位外Vehicleが対象Nodeへ到着し得る。
- 各仮想timestepでは、完全な拘束順位列を先に走査し、その後に拘束順位外Vehicleを置く。
- 拘束順位Vehicle全員が将来通過し終わるまで、拘束順位外Vehicleを待たせない。
- 拘束順位Visitが未到着、物理先頭でない、または通常の物理・容量条件で一時スキップされても、clearance停止がなく残容量があれば、同じ仮想timestepに拘束順位外処理へ進み得る。
- 通常の通過不能だけでは拘束順位外処理を禁止しない。clearance未充足のときだけ、そのtimestepの残り通過処理を終える。拘束順位走査中のclearance停止では、拘束順位外処理へ進まない。

**今回確定した対象Node向け進路の4分類**

分類番号は拘束順位列の区分番号とは別である。

- **分類1：** snapshot時点で対象Node向け進路が決定済み。局所計算ではsnapshot進路を固定する。受入不能でも別outlinkへ変えない。実Worldの進路は強制しない。
- **分類2：** snapshot時点では未決定だが、今回baselineで対象Node向け進路が判明し、完全な拘束順位列に含まれるVisit。順位確定をもたらしたbaselineの対象Node到着時進路を使う。候補評価中は読取専用である。順位台帳は評価中に変更しない。最終的にそのVisitが今回の正式確定対象になったときだけ、確定順位と正式進路を原子的に保存する。実Worldへは強制しない。受入不能でも別outlinkへ変えない。
- **分類3：** snapshot時点では未決定だが、今回baselineで進路が判明した拘束順位外Vehicle。baseline進路を当該候補の局所計算内で読取専用として一時使用する。順位台帳へ保存しない。正式進路とは呼ばない。実Worldへは強制しない。受入不能でも別outlinkへ変えない。
- **分類4：** snapshotでも今回baselineでも対象Node向け進路が未判明の拘束順位外Vehicle。仮想通過を実際に試す時点で、BATCH Level 2型の仮想進路を割り当てる。仮想到着時点では割り当てない。順位台帳へ正式進路として保存しない。実Worldへは強制しない。

分類2と分類3は、候補評価中はどちらも読取専用の一時使用である。相違は、最終結果決定後に正式保存対象になり得るかどうかである。分類2のうち今回確定対象になったVisitだけが原子的保存の対象になり得る。分類3はこの局所計算を理由に順位台帳へ保存しない。

**分類4の仮想進路**

- 通過を試す時点で、`capacity_in_remain >= DELTAN`かつ入口空間があるoutlinkだけを`acceptable_outlinks`とする。
- `outlink.id`昇順に並べ、`selection_index = real_vehicle.id % len(acceptable_outlinks)`で選ぶ。
- 選んだ処理内で直ちに仮想通過させる。
- 実Worldの`W.rng`、局所乱数、`route_next_link_choice()`は使わない。
- 空ならそのtimestepでは進路を割り当てず、通過させず、次timestepで再評価し得る。
- これは将来進路の予測ではない。楽観的な仮想流入先への決定論的な分散である。同じ入力なら同じ結果になる。最適分散は保証しない。UXsim本来の経路選択の再現ではない。候補ごとに`acceptable_outlinks`が違えば、同じVehicleでも候補ごとに異なる仮想進路になり得る。その差は許容する。
- 選択結果は候補別診断に残す。順位台帳へは保存しない。
- 全物理outlinkへ剰余を適用してから循環探索する旧案は、受入不能outlinkの直後へ偏り得るため撤回済みである。現行方式は最初から受入可能集合だけを使う。

**拘束順位外の一時的試行順**

- 各仮想timestepの対象は、その時点までに到着済み、未通過、完全な拘束順位列に含まれない、trip-endではないVehicleである。
- 次timestepでは、残留未通過Vehicleと新規到着Vehicleから対象集合を作り直す。
- 一時的走査順は、現在Visitの対象Node到着時刻、固定`arrival_tiebreaker`、Vehicle IDの昇順である。
- この順は正式なbaseline順位でもTVT順位でもない。順位台帳へ保存しない。`merge_priority`も乱数も使わない。

**通過不能とclearance**

- 未到着、物理先頭でない、保存進路の入口空間不足、`capacity_in_remain`不足、`capacity_out_remain`不足、`flow_capacity_remain`不足、分類4の`acceptable_outlinks`空は、通常の物理・容量条件である。当該Vehicleを止め、別inlinkの後続は確認できる。同じinlinkの後続は追い越せない。拘束順位列は変えない。
- clearance未充足は、そのtimestepの残り通過処理を終了する。拘束順位走査中なら拘束順位外へ進まない。拘束順位外走査中なら以降の候補を見ない。
- clearance待ち専用の新しい制御状態は必須としない。`last_order_control_inlink`、`last_order_control_entry_timestep`、`order_control_clearance_timesteps`、残っている`incoming_vehicles`から毎timestep再判定する。
- 充足条件は`current_virtual_timestep - last_order_control_entry_timestep > order_control_clearance_timesteps`である。
- 実際に通過した場合だけclearance履歴を更新する。両走査は同じ履歴と残容量を共有する。

**状態更新**

- `incoming_vehicles`はtimestep末に全消去しない。通過成功Vehicleだけを除く。未通過は残す。新規到着は重複なく追加する。通常Worldの全消去後再登録には依存しない。
- 最初の局所timestepはsnapshot残容量を使う。2つ目以降はtransfer前に補充する。同一timestepの途中、および拘束順位処理の後には再補充しない。`flow_capacity_remain < DELTAN`でそのtimestepの通過処理を終える。
- 通過成功時は、既存UXsimのLink間移動と同じ交通上の意味になるよう、累積流出・流入、旅行時間関連、残容量、物理先頭からの削除、outlink追加、`Vehicle.link`、`link_arrival_time`、`x`、`v`、`lane`、leader、follower、`move_remain`、`vehicles_enter_log`、新しいorder-control Visit、`incoming_vehicles`からの削除、`last_order_control_inlink`、`last_order_control_entry_timestep`を更新する。
- 同一仮想timestep内の次Vehicleは、先行Vehicle移動後の最新状態を使う。Vehicleごとに仮想時刻を進めない。
- 単車線を前提とする。対象Nodeが目的地のtrip-end Vehicleは通過候補に含めない。signal条件は局所通過判定に入れない。
- 局所計算から実World baseline collectorへは書き込まない。

**下流境界の3分岐**

下流のsignal、標準transfer、FCFS、BATCH、TVTは局所Worldで個別再現しない。baseline観測countを正本とし、平均率は局所側で算出する。途中通過Vehicleだけを観測対象とする。

- **`active > 0`かつ総実流出台数 `> 0`：** 条件付き平均流出率を候補別・outlink別の流出許可残高へ毎timestep加算する。小数と未使用整数を繰り越す。実際の流出は、残高の整数台数分だけでなく、終端待機Vehicle数、物理FIFO、`outlink.capacity_out_remain`、終端Nodeの`flow_capacity_remain`、`DELTAN=1`、その他のUXsim物理条件がすべて許す範囲である。人工的なburst上限は新設しない。大きな残高は保存された物理容量ではなく、平均的な境界サービス機会の再配分近似である。
- **`active > 0`かつ総実流出台数 `= 0`：** 共通horizon内の境界サービス率を0とし、同じlocal horizon内は境界閉塞として扱う。horizon後も永続閉塞とは断定しない。
- **`active = 0`：** 下流待ちが一度も観測されなかったことを意味し、無混雑とは断定しない。平均率と流出許可残高は使わない。無制約sinkではない。制約付きsinkとする。終端に到達した物理FIFO先頭から、終端待機数、物理FIFO、`outlink.capacity_out_remain`、終端Node容量、`DELTAN=1`、その他必要なUXsim物理条件が許す範囲で`end_trip()`により局所Worldから除く。流出成功時はoutlink流出容量と終端Node容量を消費する。下流Linkの`capacity_in_remain`は使わない。人工的な最大1台制限は設けない。同一timestepの複数台は、人工上限ではなく既存の容量・物理・FIFOで決まる。局所Worldの`end_trip()`は実Worldの本来の旅行終了を意味しない。

**BATCH Level 2単純sinkとの差**

- BATCH Level 2のsinkは、物理FIFO先頭と終端到達の後に`end_trip()`する単純sinkである。sink流出時に`outlink.capacity_out_remain`と終端Nodeの`flow_capacity_remain`を確認・消費しない。
- TVT-MPの`active = 0`は、その単純sinkをそのまま使わない。FIFOに加えてoutlink流出容量と終端Node容量等を確認・消費する制約付きsinkである。
- この差を実装で消さない。

**実装境界**

- 局所計算から`Node.transfer()`、`transfer_fcfs_clearance()`、BATCHのservice queue処理全体を直接呼ばない。理由は再評価、`incoming_vehicles`全消去、対象外状態変更、二重評価、TVT契約との不整合である。
- 責務は、通過試行統括（拘束順位走査、一時FCFS、clearance停止、後続確認、timestep終了）と、1台分の物理移動に分ける。
- `Node.transfer()`から大規模共通helperを直ちに抽出しない。TVT局所モジュール内に、BATCH Level 2の`_transfer_vehicle_reference()`相当の局所専用処理を設ける方向である。関数名、シグネチャ、モジュール名は未確定である。
- 候補ごとに独立したmimic状態を使う。実WorldのVehicle、Link、Node、乱数、正式順位台帳、baseline collector、他候補の状態は、候補評価中に変更しない。
- 候補別結果には、候補識別、resolved / unresolved、理由、対象Node仮想通過timestep、拘束順位内か外か、使用進路の種類（snapshot、拘束順位内baseline、拘束順位外の一時baseline、Vehicle ID仮想進路）、Vehicle ID方式の選択outlink、timestepごとの通過Vehicle、clearance待ち、進めたtimestep数、outlink別平均率と残高推移、境界閉塞、制約付きsink使用、境界流出Vehicle、horizon末状態を残す。型名は未確定である。これらを順位台帳、実collector、実World、他候補へは書かない。
- 正常なunresolvedは、horizon内に必要Vehicleが通過しない、境界閉塞が解消しない、`active > 0`かつ流出0がhorizonまで影響する、clearanceまたは容量不足が継続する、分類4に`acceptable_outlinks`が得られない、下流境界で必要情報が揃わない、である。全buyerと全sellerの必要通過timestepが揃えばhorizon上限前でも早期終了してresolvedとする。
- VisitKey重複、拘束順位内の進路欠落、対象Nodeのoutlinkでない進路、VisitとVehicleの対応不整合、同一timestep二重通過、負の容量、物理先頭でない移動、必須状態欠落は、推測修復せず例外停止する。

**統合仕様**

候補別独立状態、拘束順位列を先に走査し余力があれば一時FCFS、両走査の状態共有、下流境界3分岐、`active > 0`かつ流出ありでは残高に加えてUXsimの容量と物理条件をすべて適用、`active = 0`は制約付きsink、必要情報が揃えば早期resolved、揃わなければ理由付きunresolved、評価中は実Worldと台帳とcollectorと乱数と他候補を変更しない、評価後にだけ今回確定するVisitの順位と正式進路を原子的保存、の10点を採用済みとする。統合後に新たな制度上の論理矛盾は確認されていない。前回の原因別最終分岐は変更しない。

**実装時の可読性方針**

正しく動くことを最優先する。巧妙さや短さより、初学者が処理段階と判断理由を追える明示的な実装を選ぶ。条件分岐と状態更新を過度に圧縮しない。複雑な内包表記と暗黙の副作用を避ける。名前は長くても、Vehicle、Visit、Node、inlink、outlink、timestep、順位、進路、境界観測、流出許可残高を混同しないものにする。登録時に保証済みの不変条件を実行時に重複検証しない。実行時検証は、変化し得る状態と重大不整合に限る。確定済み制度を実装の都合で簡略化、再解釈、変更しない。コメントとdocstringでは交通上の意味も書く。

**撤回済みであり再採用しない案**

- `active = 0`の境界流出完全停止
- `active = 0`の人工的な最大1台／timestep
- `active = 0`の未使用sink枠を繰り越さない案
- `active = 0`で同一timestepの2台以上を無条件禁止する案
- BATCH Level 2単純sinkをTVTの`active = 0`へそのまま適用する案
- `route_pref`と局所仮想乱数による進路選択
- 分類3のbaseline進路を捨てて分類3もVehicle ID方式にする案
- 全物理outlinkへのVehicle ID剰余と、受入不能時の循環探索

`route_pref`案は、未確定候補としても復活させない。

**まだ確定しない実装契約**

公開API名、公開結果型名、private helper名、新規本番モジュール名、専用テストファイル名、診断フィールドのPython型、unresolved reasonのEnumまたは文字列名、helperシグネチャ、上流結果型へ足す具体フィールド、拘束順位列の受け渡しAPI、mimic状態のクラス構成、実装単位の分割順、性能最適化、複数車線、`DELTAN`が1以外の一般化。これらは次の完全な実装前仕様で確定する。制度採否が未了という意味ではない。

**次の直接作業**

公開API、結果型、helper責務、診断型、例外契約、モジュール構成、専用テスト契約、既存上流結果との接続を含む、完全な実装前仕様を作成する。

その仕様が確定するまで、Python実装と専用テストには着手しない。本追記の制度を簡略化しない。撤回済み案を採用候補へ戻さない。

- 今回のMarkdown追記は未commitである。
- Git操作は利用者がTerminalで行う。
- `diagnostics/order_control.zip`は対象外である。

**2026-09-22注記（最新参照先の更新）：** 上記「完全な実装前仕様はまだ作成していない」と「次の直接作業は完全な実装前仕様の作成」は、拘束順位外処理・下流境界・統合仕様を記録した時点の歴史的記録である。完全な実装前仕様は後続の「2026-09-22追記（完全な実装前仕様）」で確定した。最新正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP候補別局所仮想計算の完全な実装前仕様」である。現在の直接作業は、その追記の独立確認、利用者によるMarkdownのcommitとpushのあと、最初の実装区分の目的と範囲を提示し、合意後にその区分だけへ着手することである。直ちにPython実装へ進む指示ではない。上記を現在の作業指示として読まない。2026-09-24注記: その後、局所前進まで実装済みである。最新は2026-09-24追記「TVT-MP候補別局所仮想計算の実装進捗・メモ未更新分の統合記録」を参照すること。

##### 2026-09-22追記（完全な実装前仕様）

**現在地点**

- 2026-09-22に、TVT-MP候補別局所仮想計算の完全な実装前仕様を確定した。これは実装完了記録ではない。保存済みcommit `5235089` までの制度と、現行コード接続調査と、それに基づく実装前仕様案を、公開API、結果型、helper責務、例外、診断、モジュール、テスト、実装区分へ落とした記録である。
- 詳細正本は`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`の「TVT-MP候補別局所仮想計算の完全な実装前仕様」。
- 候補別局所仮想計算のPython実装と専用テストは未着手である。この記録と同時に実装を開始しない。
- 既存の候補形成、一般形順位、FIFO検査、baseline collector、下流境界observerは維持する。`trade_order` を完全な拘束順位列へ改造しない。

**追加する主要モジュール**

- 既存`uxsim/order_control_tvt_node_rank_state.py`を正式進路付き順位台帳へ拡張する。別台帳は作らない。
- 新規`uxsim/order_control_tvt_mp_local_binding_rank_sequence.py`は、既存結果と台帳から4区分の読取専用列を作る。車両は動かさない。台帳は変更しない。
- 新規`uxsim/order_control_tvt_mp_candidate_local_state.py`は、時点Tの`real_W.copy()`で候補ごとのWorld全体のコピーを作る。対象外のNode、Link、Vehicleは削除せず、更新もしない。
- 新規`uxsim/order_control_tvt_mp_candidate_local_virtual_calculation.py`は、公開入口、仮想timestep、1台通過、終端3分岐、結果作成を持つ。
- 候補別局所状態と候補別結果は、拘束順位列を構築するためのものではない。完成済みの拘束順位列を使って計算し、通過時刻と診断を返すためのものである。

**正式進路付き順位台帳と原子的確定**

- 確定済み1件はVisitKey、`assigned_rank`、`formal_route_next_link_name`を持つ。未保存の進路は`None`であり、空文字ではない。
- 本番の確定APIは`confirm_visits_and_formal_target_node_routes_atomically`である。全件検証のあとだけ一括反映する。1件でも不整合なら順位も進路も変更しない。入力不整合は`ValueError`、代入前の内部整合失敗は`RuntimeError`とし、どちらも無変更である。
- 候補評価中はこのAPIを呼ばない。呼ぶのは、候補形成前の区分2先行確定と、最終結果決定後の既定の原因別分岐である。
- 既存`confirm_visits_in_order()`は削除しない。既存テストと互換のため残す。このAPIで確定した正式進路は`None`である。新しいTVT-MP本番経路では使わない。
- 区分1として必要になったVisitについて、台帳から局所通過に必要な正式進路が得られず、snapshot進路の規則にも該当しないときだけ、補完せず重大不整合として止める。collector進路や現在の`Vehicle.route_next_link`では補わない。古いAPIで確定したVisitのすべてを、それだけで重大不整合とはしない。

**完全な拘束順位列**

- 構築関数は`build_tvt_mp_local_binding_rank_sequence`である。結果型は`OrderControlTvtMpLocalBindingRankSequence`、要素型は`OrderControlTvtMpLocalBindingRankVisit`である。
- 区分名は`confirmed_before_this_baseline`、`preconfirmed_by_this_baseline`、`trade_scope_of_this_candidate`、`outside_trade_scope_inside_k_fixed`である。番号では持たない。進路4分類の名前とも分ける。
- 区分3の通過順は`trade_order`の先頭`last_buyer_rank`件である。`trade_scope`のbaseline順ではない。
- `k_last_buyer`は既存`last_buyer_rank`、`k_decision_window`は`remaining_decision_window_visit_keys`の件数、`k_fixed`は両者の最大値である。
- `k_last_buyer`が窓の件数より小さいとき、区分4は`remaining_decision_window_visit_keys[k_last_buyer:]`である。1始まり順位の先頭`k_last_buyer`件を除くため、0始まりの開始indexは`k_last_buyer`である。N+1位以降と、P-1対象外の遅い窓内Visitが入り得る。
- 以上なら区分4は空である。完成列は4区分の連結である。重複と進路欠落は自動修復しない。
- 評価に使った構築済み列を候補結果へ保持し、採用後に再計算しない。

**公開入口と局所計算**

- 公開入口は`evaluate_tvt_mp_candidate_local_virtual_calculations`である。引数は時点Tの`real_W`、FIFO検査結果、Node別順位台帳である。戻り値は`OrderControlTvtMpLocalVirtualCalculationSetResult`である。
- FIFOを通過した候補だけを、候補ごとに独立した写しで評価する。FIFO却下と、候補未形成のNodeは実行しない。
- `real_W.T`が`baseline_timestep_T`と違う場合は推測復元せず`ValueError`とする。
- 評価中に変えてよいのは候補ごとの写しだけである。実World、実World乱数、台帳、collector、下流境界結果、他候補は変えない。原子的確定APIは呼ばない。
- 仮想時刻はTから、最大`configured_horizon_steps`までである。最初の時刻はsnapshot残容量、2時刻目以降は通過前にだけ補充する。拘束順位列を先に走査し、clearanceで止まらず容量が残れば、到着時刻、tiebreaker、Vehicle IDの一時順で順位外を見る。`incoming_vehicles`は全消去しない。
- 全buyerと全sellerの局所対象Node通過時刻が揃えば早期resolvedとする。buyerだから短縮、sellerだから遅延とは決めない。経済性評価はしない。揃わなければ理由列付きの正常なunresolvedとする。複数理由は1件に潰さない。
- **2026-09-23補修（resolvedとなる仮想timestepの完了契約）：** 必要な通過timestepが揃った場合でも、対象Node通過処理の直後に候補計算を終了しない。その仮想timestepのinlink前進、到着登録、outlink前進、outlink終端境界処理、容量・状態・診断の更新を完了した後に `resolved` とする。BATCH Level 2のtrigger早期終了は採用しない。詳細はNOTES_2の完全な実装前仕様「仮想timestep loop」。
- 候補結果型は`OrderControlTvtMpCandidateLocalVirtualCalculationResult`である。構築済み拘束順位列、通過時刻、進路分類、境界分岐、残高推移、horizon末状態を、無名の巨大dictではなく読取専用の型で持つ。

**進路4分類**

- `snapshot_route_already_decided`は拘束順位の内外の両方にあり得る。snapshot進路を固定し、受入不能でも別outlinkへ変えない。
- `baseline_route_inside_binding_sequence`は拘束順位列の中であり、評価中は読取専用である。最終結果後に今回確定するVisitだけが正式保存の対象になり得る。
- `baseline_route_outside_binding_sequence_temporary`は拘束順位外の一時使用である。正式進路とは呼ばず、台帳へ保存しない。
- `vehicle_id_among_acceptable_outlinks`は、進路未判明の拘束順位外だけに使う。通過を試す時点で、入れるoutlinkをid昇順にし、`real_vehicle.id % 件数`で選んですぐ通過させる。空ならその時刻は通過させない。
- `route_pref`、局所乱数、実World乱数、`route_next_link_choice()`は使わない。

**下流境界3分岐**

- `downstream_boundary_result is None`は空baselineであり、`active = 0`ではない。候補評価中に`None`なら不整合として停止する。
- 分岐Aは`active_timestep_count > 0`かつ`transferred_vehicle_count > 0`である。平均率は局所側で、後者を前者で割って求める。候補別・outlink別の残高へ毎時刻加算し、小数と未使用整数を繰り越す。実流出は、残高の整数、終端待ち、物理FIFO、`capacity_out_remain`、終端Node容量、`DELTAN=1`、その他の物理条件がすべて許す範囲である。人工的なburst上限はない。
- 分岐Bは待ちが観測されたが流出台数が0である。同じlocal horizonの間は境界閉塞とする。永久閉塞とは断定しない。
- 分岐Cは`active_timestep_count == 0`である。平均率と残高は使わない。BATCH Level 2の単純sinkは使わない。物理FIFO、終端到達、outlink流出容量、終端Node容量を確認し、成功時に消費する制約付きsinkである。下流Linkの流入容量は使わない。人工的な最大1台制限はない。`end_trip()`は写しからの除去であり、実Worldの旅行終了ではない。
- BATCH Level 2のsinkは、終端到達後に流出容量と終端Node容量を確認せず`end_trip()`する。TVTの分岐Cとは別契約である。

**可読性**

正しく動くことを最優先する。初学者が処理順を追える明示的な実装を、短さや巧妙さより優先する。名前は長くても、Vehicle、Visit、Node、inlink、outlink、timestep、順位、進路、境界状態を混同しない。確定済み制度を実装の都合で簡略化しない。性能最適化は、正しい基本実装とテストの後にする。

**実装区分**

番号付きの作業管理Stepとしては確定しない。内容名は次である。事前合意なく新しいStep体系へ変えない。各区分の着手前に、名称、目的、対象範囲を利用者へ提示し、合意後にその区分だけを実装する。

- 正式進路付き順位台帳と原子的確定
- 既到着Visitと先頭連続非参加Visitの原子的先行確定接続
- 完全な拘束順位列の構築
- 候補別局所状態の構築
- 1台分の対象Node通過
- 拘束順位と拘束順位外の同一timestep統括
- outlink終端境界3分岐
- 公開入口、早期resolved、理由付きunresolved
- 最終結果後の正式確定接続

最後の区分は、採用、全候補却下、baseline情報不足、意思決定窓0件の既定分岐に従って原子的確定APIを呼ぶ接続である。経済性評価と実Worldへの反映は含めない。採用時は評価に使った構築済み列を再利用する。区分2は、この最後の区分では再保存しない。区分2の保存は、候補形成前の先行確定接続で終える。

最初の台帳区分の完了条件に、新しい本番経路が`confirm_visits_in_order()`を呼ばないことは含めない。その確認は、先行確定接続の完了条件である。

**2026-09-23補修（コード確認後）**

独立レビューの3点を、現行コードで確認してから仕様へ補った。制度の採否は変えていない。詳細はNOTES_2の完全な実装前仕様にある2026-09-23補修である。

区分2の現行経路は、`confirm_already_arrived_undetermined_visits` が先に、`confirm_leading_nonparticipating_decision_window_visits` が後に、それぞれ `confirm_visits_in_order()` をNodeごとに1回呼ぶ。この2関数より上の本番統括関数は無い。本番コードで旧APIを呼ぶのはこの2関数だけである。進路は、その呼出位置の `fork_result.collector.get_baseline_visit_snapshot` の `route_next_link_name` で取得できる。alignment結果自体は進路を持たない。outlink名集合は現行引数に無く、時点Tの実Worldの対象Nodeから呼出側が渡す。返すVisitKey列は変えない。したがって、新しいTVT-MP本番経路の区分2は原子的確定APIへ移行できる。旧APIはテストと互換のために残す。

Worldの写しは、`World.copy()` がpickleによる全体複製であることを確認した。採用するのは、候補ごとにWorld全体をコピーし、対象外オブジェクトを削除せず、TVT専用loopの更新対象だけを対象Node、全inlink、全outlink、それらに属するVehicleに固定する方式である。`exec_simulation()` と、コピー全体への `Node.update()`、`Link.update()`、`Vehicle.update()` は呼ばない。対象外を削除する方式と、BATCH Level 2型の小規模mimicを新規構築する方式は採用しない。対象外がコピー内に残ることと、対象外を走行させることは別である。

horizonは、BATCH Level 2の `for offset in range(virtual_horizon + 1)` に合わせる。`configured_horizon_steps` が2のとき、通過試行する時刻はT、T+1、T+2である。`simulated_timestep_count` はTから時計を進めた回数なので、Tで揃えば0、T+2まで進めると2である。必要通過timestepが揃ったかの記録は各時刻の対象Node通過走査の後である。候補計算の終了と `resolved` の設定は、その仮想timestepの時刻末処理完了後である。T+2の試行で揃えば、そのtimestep末処理の後にresolvedとする。T+2の時刻末処理の後も不足ならunresolvedである。baselineの `final_fork_timestep` は `T + configured_horizon_steps` だが、baselineがその時刻の交通を実行したという意味ではない。baselineが実行するのはTから `T + configured_horizon_steps - 1` までである。局所loopはBATCHの端点に合わせ、`T + configured_horizon_steps` も試行する。

> 2026-09-25更新注記: 本記録は、BATCH Level 2のvirtual_horizon端点と候補別局所仮想計算の端点をそろえる案を採用した当時の途中設計である。その後、旧正本のWorld baseline正式driver契約と実コードを再確認した。World baselineはconfigured horizon Hに対してtimestep TからT+H-1までH回の交通処理を行い、処理後のWorld.TがT+Hとなる。T+Hの交通処理は行わない。利用者判断により、一候補局所仮想計算もWorld baselineと同じH回処理へ統一した。最新の実装前仕様は、2026-09-25の「TVT-MP候補別局所仮想計算の一候補統括loop完全実装前仕様」を参照すること。offset 0でvirtual time one-stepを行わず、offset 1以降の各処理時刻冒頭でone-stepを行う容量補充契約自体は維持する。

**2026-09-23補修（resolved終了契約・仮想timestep内の処理順）**

各仮想timestepの全体順序（1仮想timestep内部の番号であり、作業管理Stepではない）は次である。

1. `offset > 0` のときだけ仮想時刻を進め容量を補充する
2. 累積配列を現在の仮想時刻まで延長する
3. 完全な拘束順位列を走査する
4. clearance停止がなく余力があれば、拘束順位外Vehicleを一時的FCFS順で走査する
5. 対象Node通過成功Vehicleの通過timestepを記録する
6. buyerとsellerの必要通過timestepが揃った場合は、この仮想timestep末でresolved終了することを記録する（ここでは終了しない）
7. inlink上の局所対象Vehicleを前進させる
8. 新たな対象Node端到着Vehicleを `incoming_vehicles` へ重複なく追加する
9. outlink上の局所対象Vehicleを前進させる
10. outlink終端へ到達したVehicleについて、下流待ちあり・実流出あり、下流待ちあり・実流出なし、下流待ち観測なしの制約付きsinkのいずれかの下流境界処理を行う
11. 容量、流出許可残高、累積台数、Vehicle状態、境界流出、診断を完成させる
12. 手順6でresolved終了が決まっていれば、ここで候補計算を終了する
13. resolvedでなく最終許容時刻で不足なら理由付きunresolvedとする
14. それ以外は次の仮想timestepへ進む

resolvedとなる仮想timestepでも、対象Node通過および境界処理に伴う容量・累積台数・流出許可残高・Vehicle状態を通常どおり更新する。同じ仮想timestep内では、容量の再補充、拘束順位列の再走査、新着 `incoming_vehicles` の通過、対象Node通過処理への復帰、次timestepへの進行を行わない。clearance未充足またはNode容量不足で通過走査が終わっても、前進と境界処理は継続する。

> 2026-09-24注記: 前進と境界処理を続ける部分は維持する。保存済みの拘束順位走査では、Node流量不足は走査終了ではなく一時スキップである。走査終了はclearance未充足だけである。詳細は2026-09-24追記を参照すること。

**テスト契約（resolved完了契約の追加分）**

- 最後のbuyerまたはseller通過後も、そのtimestepのinlink前進・到着登録・outlink前進・境界処理が実行される
- resolved時も通過に伴う容量消費が反映される
- 下流待ちあり・実流出ありで実流出分の残高と流出容量が更新される
- 下流待ちあり・実流出なしでは流出しない
- 下流待ち観測なしの制約付きsinkで成功時に容量を消費する
- 入口空間回復後も同timestepの対象Node通過へ戻らない
- 新着 `incoming_vehicles` を同timestepに通過させない
- clearanceまたはNode容量停止後も前進と境界処理が実行される
- resolved診断が最終仮想timestep末まで記録される
- BATCH Level 2 trigger早期終了と異なること
- buyerとsellerの対象Node通過timestepは時刻末処理で変わらないこと

下流境界3状態の新規記述では、内容が分かる名称（下流待ちあり・実流出あり、下流待ちあり・実流出なし、下流待ち観測なしの制約付きsink）を原則として用いる。歴史的本文の説明用「分岐A・B・C」だけを新しい正式名称として固定しない。

**次の直接作業**

本追記と2026-09-23補修（独立レビュー3点およびresolvedとなる仮想timestepの完了契約）を独立確認する。Markdownのcommitとpushは利用者がTerminalで行う。その後、最初の実装区分「正式進路付き順位台帳と原子的確定」の目的と範囲を利用者へ提示し、合意後にその区分だけへ着手する。その完了では、本番経路が旧確定APIを使わないことまでは確認しない。直ちにPython実装へ進まない。全区分を一度に実装しない。

> 2026-09-24注記: これは当時の再開情報である。最新の実装済み範囲、未実装事項、および次の直接作業は、2026-09-24追記「TVT-MP候補別局所仮想計算の実装進捗・メモ未更新分の統合記録」を参照すること。
>
> 2026-09-24追加注記: outlink終端境界処理はcommit `42bfb62`で実装、テスト、push済みである。最新の未実装範囲および次の再開地点は、同日の実装完了追記「outlink終端境界処理本体の実装完了（commit 42bfb62）」を参照すること。統合記録本文の「次の直接作業はoutlink終端境界処理」は、その時点の再開情報として残す。

- 今回のMarkdown追記は未commitである。
- Git操作は利用者がTerminalで行う。
- `diagnostics/order_control.zip`は対象外である。

##### 2026-09-24追記：TVT-MP候補別局所仮想計算の実装進捗・メモ未更新分の統合記録

**1. 今回の記録理由**

- Markdownの最終更新commitは `c35f944` である。その後、HEAD `d23a385` までに、TVT-MP候補別局所仮想計算の複数区分が実装され、commitされている。
- 設計・実装の節目で、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md` と本ファイルが更新されていなかった。
- この追記は、`d23a385` までの実装済み内容と、outlink終端境界へ追加した設計判断を、一箇所にまとめる。
- 今回、Pythonとテストは変更しない。詳細な契約は、設計メモ本文の「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」に書いた。

**2. 実装済みコミット一覧**

各commitの作成時に、その区分の専用テストと関連する回帰テストを確認した。今回の文書更新では再実行していない。

- `df3e27c`：順位と正式進路を、`confirm_visits_and_formal_target_node_routes_atomically` で一緒に保存する。失敗時は台帳を変えない。古い `confirm_visits_in_order()` は互換のため残し、新しい本番経路の正式進路付き確定では使わない。
- `a6285e3`：既到着Visitを先に、先頭連続非参加Visitをその後に、原子的確定へ接続する。正式進路はcollectorの対象Node到着時進路である。`real_W.T` が baseline開始時刻と違うときは確定しない。結果型は変えていない。
- `2052674`：完全な拘束順位列を、4区分の連結として構築する。車も台帳も動かさない。
- `4916556`：その列へ `baseline_timestep_T` を保存する。局所状態が、コピー前に実Worldの時刻と照合できる。
- `03aed6a`：候補ごとに `real_W.copy()` でWorld全体をコピーする。対象外は削除しない。更新してよいNode、Link、Vehicleを明示する。
- `07ca0d9`：仮想時計を追加する。offset 0はsnapshot残容量のまま、累積台数だけ現在時刻の枠まで延長する。2時刻目以降は、対象範囲の容量を1段だけ補充する。
- `dfdd0d6`：拘束順位の対象Node通過を追加する。通常の理由は一時スキップであり、走査終了はclearance未充足だけである。同じinlinkに複数の既到着Vehicleがいても、先頭通過後に次の物理先頭を同じ仮想時刻で通せる。
- `d23a385`：対象Link上のVehicleを1回前進し、今回新着した車だけをincomingへ足す。到着記録や乱数の途中失敗は、その呼出の更新をすべて戻す。

**3. 現在実装済みの局所計算範囲**

呼出側が守る順は、次である。統括loopはまだ無い。

1. 候補別局所状態を構築する。
2. offset 0の仮想時計を初期化する。
3. その仮想時刻で、拘束順位の対象Node通過を走査する。
4. 局所Vehicleを1回前進させる。
5. 対象inlink終端へ今回着いた車を、incomingへ登録する。

outlink終端境界処理以降は未実装である。outlink終端へ着いた車は、境界処理の前まで、そのoutlinkの上に残る。

> 2026-09-24実装完了注記: 上記「outlink終端境界処理以降は未実装」は、`d23a385` までの記録である。outlink終端境界処理は commit `42bfb62` で実装済みである。統括loopはまだ無い。現在の呼出順と未接続の制約は、同日の「outlink終端境界処理本体の実装完了（commit 42bfb62）」を参照すること。

**4. 重要な最新契約**

- 一時スキップは6理由である。未到着、inlink物理先頭でない、inlink流出容量不足、outlink流入容量不足、Node流量容量不足、outlink入口空間不足。
- その仮想時刻の拘束順位走査を途中で終えるのは、clearance未充足だけである。
- Node流量容量不足も一時スキップである。走査終了ではない。`binding_sequence_completed` は、Node流量が残っているという意味ではない。
- 同じinlinkから、同じ仮想時刻に複数台が通過できる。先頭が通ったあと、新しい物理先頭を同じ走査で通せる。clearanceは、同じinlinkの連続通過を止めない。
- 既存の `incoming_vehicles` には、同じinlinkの車が複数いてよい。縮約しない。再記録しない。
- 今回新着した車は、次の仮想時刻ではじめて対象Node通過の評価を受ける。同じ仮想時刻には通さない。
- 拘束順位走査は、原則として1仮想時刻に1回である。走査関数自体は、同じ時刻の再呼出を拒否しない。再呼出すると、一時スキップしたVisitを再試行する。
- 局所前進は、同じ仮想時刻の2回目を `RuntimeError` で拒否し、状態を変えない。
- 新着の到着記録は `record_order_control_node_arrival()` を使う。途中で失敗したときは、位置、incoming、Visit、初回到着辞書、両乱数、collectorがあるときの到着3項目を戻す。完了記録は、全件成功のあとだけ増やす。
- outlink終端の車は、終端へ揃えてoutlink上に残す。下流Nodeのincomingへ入れない。`end_trip()` しない。

`simulated_timestep_count` は、時刻Tから時計を進めた回数である。offset 0では0である。

**5. downstream boundary受渡し**

- 観測結果の公開経路は、`OrderControlBaselineForkResult.downstream_boundary_result` だけである。
- 境界状態の初期化には、対象Nodeの既存 `OrderControlBaselineDownstreamBoundaryNodeResult` を明示的に渡す。新しいprofile型は作らない。fork結果全体は渡さない。
- `None` は、空baselineにより観測していない状態である。`active_timestep_count == 0` へ変換しない。
- 候補評価の経路で `None` が現れたら `RuntimeError` である。正常なunresolvedではない。上の3状態にも入れない。
- 流出許可残高は、候補別・outlink別に0から始める。共有の観測結果は書き換えない。
- Node名とoutlinkの順序を、局所状態と照合する。欠落を0で補わない。終端Node名は、コピーWorldの `outlink.end_node` と照合する。

**6. outlink終端境界の追加設計**

3状態の主表記は意味名である。歴史的本文の「分岐A・B・C」は残すが、この追記の主表記にはしない。境界処理本体は未実装である。

> 2026-09-24実装完了注記: この節を書いた時点では境界処理本体は未実装である。commit `42bfb62` で3状態、専用境界退出、制約付きsink、outlink単位rollback、outlink別完了と同一時刻再開を実装済みである。現在の未実装としては読まない。

- 下流待ちあり・実流出あり：`active_timestep_count > 0` かつ `transferred_vehicle_count > 0`。率は局所側で割って求める。残高は毎仮想時刻その率を足し、小数と未使用の整数を繰り越す。専用境界退出は、2026-09-24に採用した新しい確定判断であり、まだ未実装である。`end_trip()` は使わない。outlinkから除き、有限な終端Node容量と流出容量を `DELTAN` 消費し、`VEHICLES_RUNNING` と `VEHICLES_LIVING` から除き、`vehicle.link = None`、`vehicle.state = "end"` とする。`arrival_time` を実旅行完了としては記録しない。`record_log()` を旅行終了としては呼ばない。
- 下流待ちあり・実流出なし：待ちは観測されたが、実流出は0である。local horizonの間は出さない。率も残高も使わない。車はoutlinkに残し、容量を消費しない。永久閉塞ではない。
- 下流待ち観測なしの制約付きsink：`active_timestep_count == 0`。これは観測済みの0であり、`None` ではない。率と残高は使わない。容量を確認して消費したあと、コピーWorld上で `end_trip()` する。実Worldの旅行終了ではない。BATCHの単純sinkは使わない。

downstream boundary結果なしは、この3状態ではない。候補評価では重大不整合である。

専用境界退出で未確定のまま残すものは、`cum_departure` のindex、`traveltime_actual` の式、`arrival_time` を無変更にするか、`World.VEHICLES` へ残すか、leaderとfollowerを外す順、退出理由と結果型の名前である。これらが決まる前に、境界処理本体は実装しない。`end_trip()` の式を、この専用退出へ流用しない。

> 2026-09-24追加確定: 上記の未確定一覧は、この追記を書いた時点の記録である。削除しない。最新契約は、設計メモ本文の「19. 専用outlink境界退出のフィールド単位確定契約」である。これらの項目は、現在の未確定としては読まない。

**専用outlink境界退出の残存契約確定（2026-09-24）**

専用境界退出は、まだ未実装である。詳細式とfield一覧は、設計メモ本文の「19. 専用outlink境界退出のフィールド単位確定契約」を正本とする。進捗上の確定事項は、次である。

> 2026-09-24実装完了注記: 上記「まだ未実装」は、この残存契約を書いた時点の記録である。専用境界退出を含むoutlink終端境界処理は commit `42bfb62` で実装済みである。field契約は未確定へ戻さない。

- 累積流出台数は、退出成功1台ごとに `outlink.cum_departure[-1] += local_world.DELTAN` である。反映前に `len(outlink.cum_departure) == local_world.T + 1` を要求する。不一致は `RuntimeError` であり、別indexへ補正しない。
- outlink旅行時間は、Vehicle前進後の時刻末退出として、`traveltime_actual[start_timestep:]` へ `(local_world.T + 1) * local_world.DELTAT - vehicle.link_arrival_time` を書く。`start_timestep` は `int(vehicle.link_arrival_time / local_world.DELTAT)` である。UXsim本体の `(T + 1)` にTODOがあることは注意として残し、TVT-MPだけ `T` へ変えない。
- `arrival_time`、`travel_time`、`link_arrival_time`、order-control Visitの到着2項目は変更しない。退出時刻秒は、除去記録の `boundary_exit_time_seconds = (local_world.T + 1) * local_world.DELTAT` へ書く。
- `World.VEHICLES` には残す。`VEHICLES_RUNNING` と `VEHICLES_LIVING` から除く。新しいWorld共通登録列は作らない。
- `state = "end"`、`link = None`、`leader = None`、`follower = None` とする。`x`、`x_old`、`x_next`、`v`、`move_remain` は終端値のまま残す。`end_trip()` の `x = 0` は流用しない。
- 物理先頭は `outlink.vehicles[0]` である。検証のあと、`follower.leader = None`、退出Vehicleの `follower` と `leader` を `None`、`popleft()`、RUNNINGとLIVINGから除去、`link = None`、`state = "end"`、除去記録、の順である。
- 同一outlinkはFIFOで、条件を満たす限り複数退出できる。通常待ちでは、先行成功を維持し、後続を飛ばさない。
- 原子性は一台単位とoutlink単位である。通常待ちの2台目で1台目は戻さない。重大不整合は、そのoutlinkの最初の書込み前に検出し、当該outlinkを無変更で `RuntimeError` とする。反映中の予期しない例外では、当該outlinkだけ呼出前へ戻す。別outlinkの正常完了は戻さない。全outlinkの一括transactionにはしない。
- 境界状態Enumは `OrderControlTvtMpOutlinkBoundaryMode` である。memberは `OBSERVED_WAIT_WITH_OUTFLOW`、`OBSERVED_WAIT_WITHOUT_OUTFLOW`、`NO_OBSERVED_WAIT_CONSTRAINED_SINK` である。
- 除去理由Enumは `OrderControlTvtMpOutlinkBoundaryRemovalKind` である。memberは `OBSERVED_OUTFLOW_BOUNDARY_EXIT` と `CONSTRAINED_SINK_END_TRIP` である。
- 状態型は `OrderControlTvtMpCandidateOutlinkBoundaryState` と `OrderControlTvtMpCandidateOutlinkBoundaryLinkState` である。結果型は `OrderControlTvtMpOutlinkBoundaryProcessResult` と `OrderControlTvtMpOutlinkBoundaryLinkProcessResult` である。除去記録型は `OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord` である。
- Vehicle除去記録は `vehicle_name` を必須識別子とする。正式fieldは `vehicle_name`、`outlink_name`、`terminal_node_name`、`virtual_timestep`、`boundary_exit_time_seconds`、`removal_kind` の6つである。VisitKey fieldは設けない。境界退出時に `order_control_current_visit` が `None` である正常状態へ対応するためである。`order_control_visit_id` の残存値や拘束順位列からVisitKeyを推測しない。除去記録へ `visit_key` を載せる案は後続検討で撤回済みである。
- 下流待ちあり・実流出ありだけが専用境界退出である。`end_trip()` は呼ばない。下流待ち観測なしの制約付きsinkは、容量確認と消費のあとコピーWorld上で `end_trip()` を使い、`removal_kind` は `CONSTRAINED_SINK_END_TRIP` である。
- 候補コピーWorldへ、通常Analyzerの旅行完了統計を適用しない。`state == "end"` だけでは通常旅行完了と読まない。
- 実装時命名として残すのは、共通helperの関数分割だけである。上のfield契約は未確定に戻さない。

> 2026-09-24実装完了注記: 共通helperの関数分割は、commit `42bfb62` の本番モジュール内private関数として実装済みである。現在の未確定としては読まない。関数名は実装時命名であり、制度は変えていない。

**7. 未実装**

outlink終端境界処理、拘束順位外の一時的FCFS、仮想timestepの統括loop、buyerとsellerの通過時刻、resolved、時刻末完了、horizon終了、unresolved診断、候補結果型、経済性評価、採用と却下、最終確定接続、上位driver統合。

仮想時計、拘束順位通過、局所前進は、未実装に含めない。

> 2026-09-24実装完了注記: 上記一覧の先頭「outlink終端境界処理」は、この節を書いた時点の未実装である。commit `42bfb62` で実装済みであり、現在の未実装一覧からは外す。現在の未実装は、拘束順位外の一時的FCFS、仮想timestepの統括loop、buyerとsellerの通過時刻、resolved、時刻末完了、horizon終了、unresolved診断、候補結果型、経済性評価、採用と却下、最終確定接続、上位driver統合である。仮想時計、拘束順位通過、局所前進、outlink終端境界処理は、現在の未実装に含めない。

> 2026-09-24実装完了注記: 上記「現在の未実装は、拘束順位外の一時的FCFS」は、outlink終端境界処理完了時点の一覧である。拘束順位外Vehicle一時的FCFS走査はcommit `7926d43`で実装済みであり、現在の未実装としては読まない。最新の未実装範囲は、同日の実装完了追記「拘束順位外Vehicle一時的FCFS走査の実装完了（commit 7926d43）」を参照すること。

**8. 次の直接作業**

境界処理を実装する前に、専用境界退出の未確定細部を文章で確定する。その後、outlink終端境界処理を、新規モジュールと専用テストで実装する。

> 2026-09-24追加確定: 上記「未確定細部を文章で確定する」は完了した。現在の次の直接作業としては読まない。

現在の次の直接作業は、outlink終端境界処理本体を新規モジュールとして実装し、専用テストを新規作成することである。入力は、local vehicle advance state、local vehicle advance result、対象Nodeの `OrderControlBaselineDownstreamBoundaryNodeResult` の3つである。downstream boundary結果なしは `RuntimeError` である。3種類は意味名で扱う。下流待ちあり・実流出ありでは、第19節の専用境界退出を使う。下流待ちあり・実流出なしでは、local horizon内に流出させない。下流待ち観測なしの制約付きsinkでは、容量確認と消費のあと `end_trip()` を使う。境界処理後に、同じ仮想timestepの binding transfer へ戻らない。

予定する入力は、local vehicle advance state、local vehicle advance result、対象Nodeの `OrderControlBaselineDownstreamBoundaryNodeResult` である。

境界処理のあとにも、仮想timestepの統括loop、拘束順位外走査、resolved、unresolved、最終確定接続は残る。

> 2026-09-24追加注記: outlink終端境界処理はcommit 42bfb62で実装、テスト、push済みである。最新の未実装範囲および次の再開地点は、同日の実装完了追記を参照すること。

**9. テスト記録**

- 各実装commitの作成時に、その区分の専用テストと関連する回帰テストを確認した。
- 今回のMarkdown棚卸しと更新では、テストを再実行していない。
- 現行の専用テストファイルは存在する。
- 棚卸し時に数えた `def test_` の数は、成功件数として書かない。設計メモ本文のcommit表に、件数である旨を付けて残した。

**10. Gitおよび作業ツリー**

このMarkdown更新を始める前のHEADは `d23a385` である。

既存の未追跡ファイル `diagnostics/order_control.zip` は対象外である。内容には触れない。

**outlink終端境界処理本体の実装完了（commit 42bfb62）**

**記録日：2026-09-24**

commit `42bfb62`（`Complete resumed implementation of three-mode TVT-MP outlink terminal boundary processing with per-outlink atomic rollback`）で、outlink終端境界処理本体を実装し、テストし、commitし、originへpushした。直前の設計記録commitは `4578239` と `016593d` である。詳細な型、field、式、例外、rollback範囲の正本は、設計メモ本文の「TVT-MP候補別局所仮想計算のoutlink終端境界処理実装完了記録」である。本小節は、その要約である。実装状況、重要契約、未実装、再開地点は省略しない。

本番は `uxsim/order_control_tvt_mp_candidate_outlink_boundary.py` である。専用テストは `tests_order_control_tvt_mp_candidate_outlink_boundary.py` である。現行の専用テスト関数数は21件である。これは `def test_` の棚卸し件数であり、この文書更新で再実行した成功件数ではない。

commit作成時のCursor報告では、専用境界21件、局所前進14件、binding transfer 15件、仮想時刻12件、局所状態14件、拘束順位列46件、Node順位台帳71件、BATCH Level 2参照20件、downstream boundary本体52件、UXsim hook 16件、driver 15件、`py_compile`、`git diff --check` が成功している。今回のMarkdown更新では、これらを再実行していない。

公開Enumは、次である。

- `OrderControlTvtMpOutlinkBoundaryMode`: `OBSERVED_WAIT_WITH_OUTFLOW`、`OBSERVED_WAIT_WITHOUT_OUTFLOW`、`NO_OBSERVED_WAIT_CONSTRAINED_SINK`。
- `OrderControlTvtMpOutlinkBoundaryRemovalKind`: `OBSERVED_OUTFLOW_BOUNDARY_EXIT`、`CONSTRAINED_SINK_END_TRIP`。

意味名との対応は、次である。

- 下流待ちあり・実流出あり: `active_timestep_count > 0` かつ `transferred_vehicle_count > 0`。
- 下流待ちあり・実流出なし: `active_timestep_count > 0` かつ `transferred_vehicle_count == 0`。
- 下流待ち観測なしの制約付きsink: `active_timestep_count == 0` かつ `transferred_vehicle_count == 0`。
- `active_timestep_count == 0` かつ `transferred_vehicle_count > 0` は `RuntimeError` である。
- `downstream_boundary_node_result is None` は、3状態ではない。`active == 0` へ変換しない。候補評価では `RuntimeError` である。正常なunresolvedではない。

可変状態は `OrderControlTvtMpCandidateOutlinkBoundaryState` と `OrderControlTvtMpCandidateOutlinkBoundaryLinkState` である。frozen結果は `OrderControlTvtMpOutlinkBoundaryProcessResult` と `OrderControlTvtMpOutlinkBoundaryLinkProcessResult` である。frozen除去記録は `OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord` である。順序を持つ公開列はtupleである。baseline結果は読取専用で保持し、変更しない。

Vehicle除去記録の正式fieldは6つである。`vehicle_name`、`outlink_name`、`terminal_node_name`、`virtual_timestep`、`boundary_exit_time_seconds`、`removal_kind`。`visit_key` と `current_visit_key_at_removal` は実装していない。必須識別子は `vehicle_name` である。`order_control_current_visit is None` は、終端Nodeがorder-control対象外のときの正常状態であり、境界処理を止めない。`order_control_visit_id`、拘束順位列、通過済みVisit列からVisitKeyを推測しない。

公開APIは、次である。

- `initialize_tvt_mp_candidate_outlink_boundary_state(local_vehicle_advance_state, downstream_boundary_node_result)`
- `process_tvt_mp_candidate_outlink_boundaries_at_current_timestep(outlink_boundary_state, local_vehicle_advance_result)`

初期化は、対象Nodeの `OrderControlBaselineDownstreamBoundaryNodeResult` を明示的に受ける。新しい正規化profile型は作っていない。fork結果全体は渡さない。Node名、outlink数、登録順、`outlink_name`、`terminal_node_name` とコピーWorldの `outlink.end_node.name` を照合する。不一致は `RuntimeError` である。並べ替えない。欠落を0で補わない。交通状態は変えない。countはboolではない0以上のintである。

処理APIの前段条件は、advance resultのNodeと仮想時刻が対象と一致し、local vehicle advanceがその時刻を完了済みであり、`local_world.T` と `current_virtual_timestep` が一致し、候補全体がその時刻をまだ完了していないことである。処理順は `candidate_local_state.outlinks` の登録順である。完了済みoutlinkは保存済み結果を返し、再処理しない。全outlink完了後だけ、候補全体をその時刻で完了にする。binding transfer、local vehicle advance、仮想時刻進行、容量補充、下流 `incoming_vehicles`、下流 `capacity_in_remain`、拘束順位外のNode通過、resolved、unresolvedは行わない。

候補別・outlink別の `flow_allowance` は初期値0である。下流待ちあり・実流出ありだけ、未完了のその時刻に `transferred_vehicle_count / active_timestep_count` を1回加算する。小数部と未使用整数部を繰り越す。人工上限はない。専用退出1台ごとに1を消費する。`DELTAN` はallowanceから引かない。

専用境界退出は、下流待ちあり・実流出ありだけである。`end_trip()` も `record_log()` も呼ばない。`cum_departure[-1] += local_world.DELTAN` は、`len(outlink.cum_departure) == local_world.T + 1` のときだけである。不一致は `RuntimeError` であり、別indexへ補正しない。`traveltime_actual[start_timestep:]` は `(local_world.T + 1) * local_world.DELTAT - vehicle.link_arrival_time` である。`start_timestep` は `int(vehicle.link_arrival_time / local_world.DELTAT)` である。`boundary_exit_time_seconds` は `(local_world.T + 1) * local_world.DELTAT` である。退出後は `state == "end"`、`link is None`、`leader is None`、`follower is None` である。`World.VEHICLES` には残す。`VEHICLES_RUNNING` と `VEHICLES_LIVING` からは除く。`arrival_time`、`travel_time`、`link_arrival_time`、`x`、`x_old`、`x_next`、`v`、`move_remain`、`route_next_link`、`flag_waiting_for_trip_end`、`order_control_current_visit`、`order_control_visit_id`、Visit履歴は変更しない。有限な終端Node容量（`flow_capacity is not None`）だけ `DELTAN` 消費する。無制限（`flow_capacity is None`、remain `10e10`）は減算しない。下流Linkの `capacity_in_remain` は使わない。候補コピーWorldを通常Analyzerの旅行完了統計へ使わない。

下流待ちあり・実流出なしは、local horizon内で退出させない。率は `None` である。allowanceを加算しない。容量、`cum_departure`、`traveltime_actual`、Vehicle登録を変えない。永久閉塞ではない。終端待ちVehicleは結果へ記録する。

制約付きsinkは、率もallowanceも使わない。物理FIFO、outlink流出容量、有限終端Node容量を確認する。成功順は、6 fieldを控える、流出容量を `DELTAN` 消費する、有限終端Node容量を `DELTAN` 消費する、コピーWorldで `end_trip()` を1回呼ぶ、`CONSTRAINED_SINK_END_TRIP` を追加する、累積Vehicle名列へ追加する、である。`end_trip()` が更新する `cum_departure`、`traveltime_actual`、旅行完了field、Vehicle登録、`Link.vehicles`、`record_log` は境界側で二重更新しない。容量不足と先頭未到着は正常待ちである。

物理先頭は `outlink.vehicles[0]` である。除去は `popleft()` である。条件を満たす限り、同じ仮想時刻に複数台を処理する。人工的な最大1台制限はない。先頭未到着または通常待ちでは、後続を飛ばさない。それ以前の正常退出は維持する。物理先頭の `leader` は `None` である。followerがあれば `follower.leader` を外してから `popleft` する。

原子性はoutlink単位である。最初の書込み前の登録不一致、物理順不一致、`cum_departure` 長不一致、負の容量、負のallowanceは `RuntimeError` で、当該outlinkは無変更である。数でない容量、allowance、`link_arrival_time`、`DELTAT` は `ValueError` である。`DELTAT <= 0` は `RuntimeError` である。反映中の予期しない例外は、当該outlinkの開始時snapshotへ戻し、元例外を再送出する。rollback失敗時は、元例外を原因に持つ `RuntimeError` である。別outlinkの正常完了は戻さない。全outlinkの一括transactionにはしない。rollback対象には、vehicles、容量、`cum_departure`、`traveltime_actual`、終端Node容量、allowance、累積Vehicle名、除去記録、Vehicle field、RUNNING、LIVING、leader、follower、`end_trip()` が変えるログfield、`analyzer.average_speed`、`analyzer.average_speed_count`、そのoutlinkの完了時刻と保存済み結果を含む。

`OrderControlTvtMpCandidateOutlinkBoundaryLinkState` は、内部に `_completed_virtual_timesteps` と `_completed_process_results_by_virtual_timestep` を持つ。外部はtupleの `completed_virtual_timesteps` と `completed_process_result(virtual_timestep)` である。退出0台でも正常完了である。後続outlinkが失敗しても、先行outlinkは完了済みのままである。失敗outlinkは未完了である。候補全体は未完了である。同じ仮想時刻の再実行は、完了済みoutlinkをスキップし、保存済み結果をそのまま返す。allowanceの再加算、容量の再消費、累積と旅行時間の再更新、追加除去、除去記録の重複はない。交通状態から結果を再構成しない。全outlink完了後だけ候補全体を完了にする。その後の同じ時刻の再実行は `RuntimeError` であり、状態は無変更である。

テストが固定した重要事項は、VisitKeyなしの6 field、3 mode、`None` と `active == 0` の区別、outlink順序、allowanceの小数と整数の繰越、専用境界退出、制約付きsink、FIFO、同一outlink複数Vehicle、有限と無限の終端Node容量、`cum_departure` 長不一致、outlink単位rollback、`end_trip()` 失敗のrollback、後続outlink失敗後の同一時刻再開、完了済みoutlinkの二重処理防止、退出0台の完了、完了記録失敗のrollback、実Worldとbaseline結果の不変である。

現在の未実装は、次である。outlink終端境界処理は含めない。

- 仮想timestep全体の統括loop
- 拘束順位外Vehicleの一時的FCFS走査
- buyerとsellerの通過時刻の収集
- resolved判定と、resolvedとなる時刻末の完了処理
- horizon終了
- unresolved理由と診断
- 候補別局所計算結果型の完成
- 経済性評価
- 候補の採用と却下
- 最終順位と正式進路の確定接続
- 上位driver統合

> 2026-09-24実装完了注記: 上記一覧の「拘束順位外Vehicleの一時的FCFS走査」は、outlink終端境界処理完了時点の未実装である。commit `7926d43` で実装済みであり、現在の未実装としては読まない。現在の未実装一覧は、同日の実装完了追記「拘束順位外Vehicle一時的FCFS走査の実装完了（commit 7926d43）」を参照すること。

`42bfb62` の境界処理契約は未確定へ戻さない。helper関数分割も実装済みであり、現在の未確定から外す。残る未確定は、拘束順位外FCFSの具体的実装契約（統括loop接続前の独立部品としての細部）、buyerとsellerの通過時刻を持つ正式結果型とfield、resolved判定の統括loop内位置、unresolved理由の複数保持、最終確定接続への評価済み列の受渡し、Node流量不足後に拘束順位外走査へ進むかの統括判定である。進路4分類の制度と分類4の適用範囲は、正本監査により2026-09-24補修で明示した。

> 2026-09-24追加注記: 各仮想timestepでunbound FCFS APIを必ず1回呼ぶ方針を採用したため、Node流量不足時にAPIを呼ぶかどうかは確定済みである。開始前Node流量不足時は既存unbound部品が空完了する。未確定なのは、Node流量不足をhorizon終了時のunresolved理由へ反映する条件と診断規則である。

> 2026-09-25追加注記: 利用者判断により、unresolved理由は観測可能な事実だけから付与し、因果関係を推測しない方針を採用した。Node流量不足は、到着後の判定期間全体で継続した容量阻害として `CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON` に含まれ得る。1回だけの阻害では付けない。6番目reasonは現段階で自動付与しない。最新の完全仕様は同日の一候補統括loop完全実装前仕様を参照すること。

> 2026-09-24実装完了注記: 上記「拘束順位外FCFSの具体的実装契約」は、outlink終端境界処理完了時点の未確定である。独立部品としての順位外FCFSは commit `7926d43` で実装済みであり、統括loop接続前の細部としての未確定へは戻さない。残る未確定は、統括loopの入力、出力、停止理由、結果型である。最新は同日の実装完了追記を参照する。

> 2026-09-24追加注記: 独立検証と利用者判断により、最終結果のlive state非保持・終了時frozen記録、およびunbound FCFSの毎仮想timestep 1回呼出しを採用した。最新詳細は同日の途中確定記録を参照すること。

**分類4の適用範囲と進路制度（2026-09-24補修要約）**

- 分類4の対象は、snapshot固定集合に登録済みのVisitに限る。対象Nodeごとにsnapshot固定集合とbaseline collector登録集合は同一である。baseline中にcollectorへ新しいVisitKeyを追加しない。
- snapshot固定集合外のVehicleまたはVisitを分類4として扱わない。collector記録が無いVisitを、記録の無い分類4として扱わない。
- 分類1はsnapshot固定集合内で、snapshot時点の対象Node向け進路を固定使用する。
- 分類3はsnapshot固定集合内で、baseline対象Node到着時の `route_next_link_name`（`get_baseline_visit_snapshot`）を一時使用する。受入不能でも分類4へ変更しない。
- 分類4は、snapshot固定集合内、拘束順位外、snapshot進路なし、baseline到着時進路（`route_next_link_name`）も記録されなかった場合に限り、仮想通過試行時に決定論的な仮想進路を選ぶ。
- collector記録そのものが無い（`get_baseline_visit_snapshot` が `None`）: 分類4ではない。重大不整合として `RuntimeError` で停止する。コピーWorldの `route_next_link`、Vehicle ID方式、別Visitの流用、Vehicle名だけの探索は行わない。
- collector記録はあるが `route_next_link_name` が無い（未到着または到着時進路未記録）: 分類4の条件になり得る。両者を混同しない。
- 分類4のVehicle ID方式（2026-09-22確定を維持）: 受入可能なoutlinkだけを抽出し、`outlink.id` 昇順、`selection_index = real_vehicle.id % len(acceptable_outlinks)` で選び、同じ通過試行で直ちに通過する。`acceptable_outlinks` が空は通常の通過不能。乱数、`route_next_link_choice()`、`merge_priority`、全物理outlinkの循環探索は使わない。分類1・分類3の保存済み進路が受入不能でもVehicle ID方式へ変更しない。

> 2026-09-24実装完了注記: 分類4の `real_vehicle.id` は、candidate local state構築時に `real_W.VEHICLES[name].id` から保存した実Vehicle IDである。コピーVehicle IDではない。実装の読取APIは `candidate_local_state.real_vehicle_id(vehicle_name)` である。commit `7926d43`。詳細は設計メモの「TVT-MP候補別局所仮想計算の拘束順位外一時的FCFS走査実装完了記録」を参照する。

正本の詳細は、設計メモ「拘束順位外処理・下流境界・統合仕様の確定記録」の第2.5節（2026-09-24補修）である。

次の正式実装区分は未確定である。次の実装候補は、拘束順位外Vehicleの一時的FCFS走査と、仮想timestep全体の統括loopの2つである。どちらを正式に先行するかは、まだ決めていない。

拘束順位外Vehicleの一時的FCFS走査には、具体的な実装契約の未確定事項が残る。仮想timestep全体の統括loopは、処理順に未実装の拘束順位外走査を含む予定である。そのため、統括loopを先に実装すると、拘束順位外走査の未確定部分を仮定で埋める危険がある。一方で、拘束順位外走査を独立部品として先に実装するかどうかは、まだ正式な設計判断を行っていない。「拘束順位外走査を先に実装する」とも、「統括loopを先に実装する」とも、本追記では確定しない。

現時点の次の直接作業は、両候補の依存関係、入力、出力、責務分離を確認し、実装順を決定することである。実装順を決定するまでは、どちらのPython実装も開始しない。完全な実装前仕様の「実装区分」は、番号付き作業順を確定していない。

> 2026-09-24実装順確定注記: 上記「未確定」「実装順を決定する」は、依存関係確認待ちの当時の再開情報として残す。後続の正本監査、コード準拠監査、独立確認により、実装順を正式採用した。拘束順位外Vehicleの一時的FCFS走査を独立部品として先行実装し、その後仮想timestep全体の統括loopへ接続する。理由は、統括loopが順位外FCFSを内部で必要とし、未実装の空処理が容量・clearance・通過結果を変えること、およびbinding transfer stateとscan resultで順位外部品を単独テストできることである。正本は設計メモのoutlink終端境界実装完了記録第20節である。

**実装順（2026-09-24正式採用）**

1. 拘束順位外Vehicleの一時的FCFS走査を、新規独立モジュールと専用テストとして実装する。
2. その後、仮想timestep全体の統括loopへ接続する。

**次の直接作業（最新）**

拘束順位外Vehicleの一時的FCFS走査を、新規独立モジュールと専用テストとして実装する。順位外FCFSの実装には、local vehicle advance、outlink終端境界、virtual time進行、buyer・seller通過時刻の最終収集、resolved、unresolved、horizon終了、経済性評価、最終順位確定、上位driver統合を含めない。完了後の次の直接作業は、仮想timestep統括loopへの接続である。

> 2026-09-24追加注記: 拘束順位外Vehicle一時的FCFS走査はcommit 7926d43で実装、テスト、push済みである。最新の未実装範囲および次の再開地点は、同日の実装完了追記を参照すること。

再開時に守る制約は、次である。

- outlink終端境界処理は `42bfb62` で実装済みである。
- まだ単独部品であり、仮想timestep統括loopへ未接続である。
- binding transfer、local vehicle advance、outlink boundaryを正しい順で呼ぶ統括処理は未実装である。
- outlink boundaryは local vehicle advance result を入力に取る。初期化には対象Nodeの downstream boundary Node結果を明示的に渡す。
- 後続統括処理は、同じ仮想時刻の binding transfer へ戻ってはならない。
- 次時刻へ進む場合は、`advance_tvt_mp_candidate_virtual_time_one_step` を明示的に呼ぶ必要がある。境界処理自身は時計を進めず、容量を補充しない。

**拘束順位外Vehicle一時的FCFS走査の実装完了（commit 7926d43）**

**記録日：2026-09-24**

commit `7926d43`（`Implement TVT-MP unbound FCFS transfer with persisted real vehicle IDs`）で、拘束順位外Vehicleの一時的FCFS走査を実装し、テストし、commitし、originへpushした。直前の文書commitは `308256e` である。詳細な型、API、field、対象集合、例外、補修履歴の正本は、設計メモ本文の「TVT-MP候補別局所仮想計算の拘束順位外一時的FCFS走査実装完了記録」である。本小節は、その要約である。実装状況、重要契約、未実装、再開地点は省略しない。

変更4ファイル:

- 新規本番 `uxsim/order_control_tvt_mp_candidate_unbound_fcfs_transfer.py`
- 新規専用テスト `tests_order_control_tvt_mp_candidate_unbound_fcfs_transfer.py`
- 既存本番 `uxsim/order_control_tvt_mp_candidate_local_state.py`
- 既存テスト `tests_order_control_tvt_mp_candidate_local_state.py`

`diagnostics/order_control.zip` は既存未追跡のまま対象外である。

**candidate local stateへの実Vehicle ID保存**

`OrderControlTvtMpCandidateLocalState` へ、内部field `_real_vehicle_id_by_real_vehicle_name` と公開読取API `real_vehicle_id(real_vehicle_name)` を追加した。保存値の取得元は `real_W.VEHICLES[real_vehicle_name].id` である。コピーVehicle IDから作らない。実World全体も実Vehicle objectも状態へ保持しない。`MappingProxyType` で保護する。候補構築後にlocal Vehicle IDが変わっても、保存済み実IDは変わらない。実Worldを再参照しない。候補間で同じ実Vehicle IDを保持する。local Vehicle objectは候補ごとに独立である。空でないstrを要求する。未登録名は `RuntimeError`、空文字または非strは `ValueError`、`bool` はVehicle IDとして許可しない。Python `int` だけを返す。可変dictを外部へ返さない。保存対象は順位外Vehicleだけに限定せず、対象inlink、対象outlink、incomingの和として構成された `local_vehicles` の正式対応範囲である。

**順位外FCFSの独立モジュール**

公開Enumは `OrderControlTvtMpUnboundRouteClassification`、`OrderControlTvtMpUnboundTemporarySkipReason`、`OrderControlTvtMpUnboundFcfsStopReason` である。進路分類は `SNAPSHOT_FIXED_ROUTE`（分類1）、`BASELINE_ARRIVAL_ROUTE`（分類3）、`DETERMINISTIC_VIRTUAL_ROUTE`（分類4）である。分類2は完全な拘束順位列内のため対象外である。frozen結果型は `OrderControlTvtMpUnboundVehicleTransferRecord`、`OrderControlTvtMpUnboundTemporarySkip`、`OrderControlTvtMpUnboundFcfsTransferResult` である。可変状態型は `OrderControlTvtMpCandidateUnboundFcfsTransferState` である。順序を持つ公開列はtupleである。

初期化APIは2引数である。

```text
initialize_tvt_mp_candidate_unbound_fcfs_transfer_state(
    binding_transfer_state,
    baseline_collector,
)
```

`real_W` は渡さない。真正な実Vehicle IDはcandidate local state構築時に保存済みだからである。順位外FCFS側で別Worldを受け取り、コピー元かどうかを後から推測しない。初期化時は交通状態、collector、順位台帳を変更しない。snapshot固定VisitKeyを状態へ保存する。

処理APIは次である。

```text
scan_and_transfer_tvt_mp_unbound_fcfs_vehicles_at_current_timestep(
    unbound_fcfs_transfer_state,
    binding_transfer_scan_result,
)
```

1回の呼出しは、現在の仮想timestepについて順位外Vehicleを一時的FCFS順で走査する。virtual time進行、容量補充、local vehicle advance、新着incoming登録、outlink終端境界、buyer・seller通過時刻の最終収集、resolved、unresolved、horizon終了、正式順位保存、順位台帳更新、経済性評価、最終確定接続は行わない。

**snapshot固定集合内だけが対象**

対象Vehicleは、その仮想timestepに `target_node.incoming_vehicles` に存在し、対象Nodeへ到着済み、未通過、現在Visitが対象Node、VisitKeyがsnapshot固定集合内、完全な拘束順位列に含まれない、transferred binding Visitではない、trip-endでも研究対象外でもない。研究対象外の正常除外は、`state` が `end` または `abort`、`flag_waiting_for_trip_end`、taxi、`specified_route`、対象Nodeが目的地となるVehicleである。binding走査で一時スキップされた拘束Visitは順位外へ移さない。通過済みbinding Visitも再処理しない。incoming内の同一Vehicle object重複、および既に順位外通過済みのVehicleがincomingへ残っている場合は `RuntimeError` である。

**snapshot固定集合外とcollector欠落は重大不整合**

通常の研究対象Vehicleがincomingに存在し、現在Visitが対象Node向けで拘束順位外であるにもかかわらず、VisitKeyがsnapshot固定集合外なら `RuntimeError` である。分類4へ回さない。Vehicleを移動しない。容量、incoming、完了時刻、通過済み名を変更しない。コピーVehicleの現在進路で補完しない。Vehicle名だけで別Visitを探さない。別 `visit_id` を使わない。collector記録欠落も同様に重大不整合である。collector記録なしと、collector記録ありで `route_next_link_name` なしとを混同しない。後者は分類4の条件になり得る。

**FCFS順**

候補集合を、現在Visitの対象Node到着時刻、固定 `arrival_tiebreaker`、candidate local stateに保存された実Vehicle IDの昇順で並べる。第3条件にlocal Vehicle IDを使わない。毎仮想timestep、その時点の対象集合から作り直す。前時刻の順を持ち越さない。正式順位、TVT順位、`merge_priority`、乱数、`World.rng`、`order_control_rng`、`route_next_link_choice()` は使わない。

**分類1、分類3、分類4**

分類1は、collector記録あり、`was_arrived_at_snapshot is True`、`route_next_link_name` ありである。snapshot時進路を固定使用する。受入不能でも別outlinkへ変更しない。分類4へ切り替えない。formal routeを新規保存しない。snapshot時点で既到着なのに進路が無い場合は `RuntimeError` である。

分類3は、collector記録あり、`was_arrived_at_snapshot is False`、`route_next_link_name` が空でない文字列である。collectorに保存されたbaseline対象Node到着時進路を一時使用する。コピーVehicleの現在 `route_next_link` を採用しない。local Vehicleの `route_next_link` を書き換えない。formal routeとは呼ばない。受入不能でも分類4へ切り替えない。既存の1台通過helperへ選択したoutlinkを明示的に渡すため、`route_next_link` 書換えは不要だった。

分類4は、collector記録あり、未到着、`route_next_link_name` が `None` または空、snapshot固定集合内、拘束順位外である。通過試行時に、target Nodeのoutlinkのうち `capacity_in_remain` が `DELTAN` 以上かつ入口空間があるものだけを `outlink.id` 昇順で並べ、`selection_index = candidate_local_state.real_vehicle_id(vehicle_name) % len(acceptable_outlinks)` で選び、同じ通過試行で直ちに通過させる。`acceptable_outlinks` が空は正常な一時待ち `ACCEPTABLE_OUTLINKS_EMPTY` である。循環探索、乱数、`merge_priority`、`route_next_link_choice()` は使わない。

**clearanceとNode流量停止**

binding走査がclearance未充足で停止していた場合、順位外候補を抽出せず、交通状態を変更せず、`BINDING_CLEARANCE_STOPPED_NOT_STARTED` で完了時刻を追加する。順位外走査開始前にNode流量容量が `DELTAN` 未満なら、同様に抽出せず `NODE_FLOW_CAPACITY_UNAVAILABLE_BEFORE_START` で完了する。0台でも正式な処理完了である。走査中のclearance未充足は `CLEARANCE_NOT_SATISFIED`、走査中のNode流量不足は `NODE_FLOW_CAPACITY_UNAVAILABLE` である。そのVehicle以降を確認せず、先行成功は維持し、`stopped_vehicle_name` を記録する。signalは使用しない。

**一時スキップ**

通常の一時スキップは、inlink物理先頭でない、inlink流出容量不足、分類1または分類3の固定outlink流入容量不足、同固定outlink入口空間不足、分類4で `acceptable_outlinks` が空である。そのVehicleを通さず、temporary skip記録を残し、後続候補を確認する。同じinlinkの後続Vehicleは物理先頭条件で通さない。別inlinkの候補は確認可能である。

**通過更新**

既存binding transferの1台通過helper `_transfer_one_vehicle_like_uxsim` を使う。成功時は `cum_departure`、`cum_arrival`、`traveltime_actual`、inlink流出容量、outlink流入容量、finite Node流量、inlinkとoutlinkの `vehicles`、incoming、`vehicles_enter_log`、Vehicleのlink、到着時刻、位置、速度、lane、leader、follower、`move_remain`、`begin_order_control_visit_on_link_entry()`、clearance履歴を更新する。順位台帳、collector、binding sequence、binding通過済みVisit列は変更しない。

**1台単位処理と二重実行防止**

1台ずつ通過条件を確認し、既存helperで反映する。通常待ち、後続clearance停止、Node容量不足では先行成功を戻さない。全順位外Vehicleを一括transactionにはしない。通過成功したVehicle名は `transferred_unbound_vehicle_names` へ追加する。同じ仮想timestepの正常な2回目呼出しは `RuntimeError` で状態無変更である。処理完了後だけ `completed_virtual_timesteps` へ現在時刻を追加する。重大不整合で例外になった場合は完了時刻を追加しない。公開結果の必須識別子は `vehicle_name` である。VisitKeyは内部のsnapshot固定集合照合に使うが、公開結果の必須識別子にはしない。

**実装中に見つかった誤りと最終補修**

初期実装の誤りは、snapshot固定集合外の通常Vehicleを黙って除外していたこと、分類4でコピーVehicle IDを使っていたこと、snapshot固定集合外を正常無視する誤ったテストがあったこと、`or True` 等の常に成功するassertがあったこと、順位外FCFS初期化へ `real_W` を追加したが真正なコピー元Worldであることを証明できなかったことである。最終補修は、snapshot固定集合外とcollector記録欠落を `RuntimeError` とし、候補別局所状態の構築時に実Vehicle IDを保存し、順位外FCFSへ `real_W` を渡さず、FCFS順と分類4で保存済み実IDを使い、無効assertを削除し、コピーIDと実IDを意図的に異ならせる反証テストを追加し、最新4ファイルを独立レビュー後にcommitしたことである。これらは最終契約であり、同種の誤りを再導入してはならない。

**テスト記録**

candidate local state専用テストは17件、順位外FCFS専用テストは18件である。commit `7926d43` 作成時のCursor報告上、candidate local state 17件、unbound FCFS 18件、binding transfer 15件、local vehicle advance 14件、outlink boundary 21件、virtual time 12件、binding rank sequence 46件、node rank state 71件、BATCH Level 2 reference 20件、baseline collector、baseline snapshot、`py_compile`、`git diff --check` が成功している。今回のMarkdown更新時には、これらを再実行していない。

テストが固定した重要事項は、実World由来のVehicle ID保存、`MappingProxyType`、local ID変更後も実ID不変、FCFS第3条件が実ID、分類4の剰余が実ID、snapshot固定集合外は `RuntimeError`、collector記録欠落は `RuntimeError`、分類1、分類3、分類4、binding Visitを順位外へ移さないこと、clearance停止、Node容量停止、same-inlink FIFO、同一仮想timestepの複数通過、通過更新、実World不変、collector不変、順位台帳不変、binding状態不変、二重実行拒否、乱数不変である。

**未実装一覧**

拘束順位外FCFS走査はこの一覧に含めない。

- 仮想timestep全体の統括loop
- buyerとsellerの通過時刻の最終収集
- resolved判定
- resolvedとなる仮想時刻の時刻末完了処理
- horizon終了
- unresolved理由と診断
- 候補別局所計算結果型の完成。仕様上の名前はある。クラスは無い。
- 経済性評価
- 候補の採用と却下
- 最終順位と正式進路の確定接続
- 上位driver統合

仮想時計、拘束順位の対象Node通過、局所Vehicle前進と新着incoming登録、outlink終端境界処理、拘束順位外Vehicleの一時的FCFS走査は、未実装に含めない。順位外FCFSはまだ単独部品であり、統括loopへ未接続である。

**現在残る未確定事項**

独立部品としての順位外FCFS契約は未確定へ戻さない。残る未確定は、buyer・seller通過時刻を持つ正式結果型とfield、resolved判定の統括loop内位置、unresolved理由の複数保持と付与規則、horizon終了結果、候補別局所計算結果型、時刻末の結果保存である。Node流量不足時もunbound FCFS APIを毎時刻1回呼ぶことは確定済みである。一方、Node流量不足をhorizon終了時のunresolved理由へ反映する条件と診断規則（`clearance_or_capacity_blocked_through_horizon` 等の正式な付与規則を含む）は未確定である。上記の未確定項目は、正本から一意に決まらない。

> 2026-09-24追加注記: 独立検証と利用者判断により、最終結果のlive state非保持・終了時frozen記録、およびunbound FCFSの毎仮想timestep 1回呼出しを採用した。最新詳細は同日の途中確定記録を参照すること。

> 2026-09-25追加注記: 利用者判断により、unresolved理由は観測可能な事実だけから付与し、因果関係を推測しない方針を採用した。終了時Vehicle記録はVehicle名、Link名、位置x、state、current VisitKey、current Visit Node名に限定する。最新の完全仕様は同日の一候補統括loop完全実装前仕様を参照すること。上記「付与規則未確定」「Vehicle追加field未確定」相当の記録は、2026-09-24時点の状態である。

**次の直接作業**

仮想timestep統括loopの入力、出力、停止理由、結果型の設計確定である。統括loop本体のPython実装は、その設計確定の前に開始しない。独自に仮の結果型を置かない。

少なくとも次の処理順を再開情報として残す。結果型が決まるまでPythonには落とさない。

1. `offset > 0` の場合だけ virtual time one-step
2. binding transfer
3. unbound FCFS transfer
4. buyer・seller通過時刻記録
5. local vehicle advanceと新着incoming登録
6. outlink終端境界処理
7. resolved、最終時刻unresolved、または次時刻

同じ仮想timestepのbinding transferへ戻らない。入口空間が回復しても戻らない。

> 2026-09-24追加注記: 上記処理順の3は、binding transferの結果にかかわらず、各仮想timestepでunbound FCFS APIを必ず1回呼ぶ契約である。同じ仮想timestepのunboundへは戻らない。最終結果はliveな統括state、candidate local state、local Worldを保持しない。最新詳細は直後の途中確定記録を参照すること。

**TVT-MP候補別局所仮想計算の結果保持・unbound呼出契約を途中確定（2026-09-24）**

独立検証後、利用者が次の2件を正式採用した。詳細正本は設計メモ本文の「TVT-MP候補別局所仮想計算の統括loop結果保持・unbound呼出契約の途中確定記録」である。本小節はその要約である。統括loop全体の完全な実装前仕様ではない。

**採用事項1**

最終frozen結果は、liveな統括state、candidate local state、local World、Node、Link、Vehicleへの参照を保持しない。終了時に必要な交通状態は、名前と数値を中心とする独立したfrozen記録として候補結果へ保存する。World全体の複製やsnapshotは作らない。正本が要求する終了時のLink名、Vehicle位置、容量、境界状態等を、局所対象に限定して残す。

既存のbinding、unbound、advance、boundaryのfrozen結果は、可変交通objectを保持しない。名前、VisitKey、数値、Enum、frozen recordのtupleを保持する。ただし、既存per-timestep結果だけでは終了時Vehicle位置 `x` を含む終了状態全体を再構成できない。per-timestep結果は「その時刻に各部品が何を行ったか」、終了時frozen記録は「候補計算終了時に交通状態がどうなっていたか」である。candidate local stateはfrozen dataclassだが、内部に可変local Worldを保持する作業用stateである。frozen dataclassであることは、内部WorldやVehicleが凍結されることを意味しない。

**採用事項2**

各仮想timestepで、binding transfer直後にunbound FCFS APIを必ず1回呼ぶ。bindingがclearance停止した時も呼ぶ。unbound開始前にNode流量が不足している時も呼ぶ。順位外候補が0台の時も呼ぶ。開始不能時は既存unbound部品が交通を動かさず空完了し、当該時刻を処理済みとして記録する。統括loopはunboundの開始条件を重複実装しない。同一仮想timestepでは2回呼ばない。

binding側のNode流量不足はstop reasonではなく、一時スキップ理由 `NODE_FLOW_CAPACITY_UNAVAILABLE` である。bindingは流量不足のVisitをスキップし、後続Visitを確認する。`BINDING_SEQUENCE_COMPLETED` だけではNode流量残を判断できない。clearance停止時の空完了は `BINDING_CLEARANCE_STOPPED_NOT_STARTED`、開始前Node流量不足時の空完了は `NODE_FLOW_CAPACITY_UNAVAILABLE_BEFORE_START` である。いずれの空完了でも `completed_virtual_timesteps` へ当該時刻を追加する。候補0台は `CANDIDATES_COMPLETED` として完了する。完了済み時刻の2回目は `RuntimeError` である。bindingには同一時刻二重実行防止がないため、統括loop側がbinding transferも各時刻1回に制限する必要がある。

**処理順の該当部分**

1. `offset > 0` の場合だけ virtual time one-step
2. binding transferを1回
3. unbound FCFS transferを必ず1回
4. buyer・seller通過時刻記録
5. local vehicle advanceと新着incoming登録
6. outlink終端境界処理
7. 時刻末のresolved、最終時刻unresolved、または次時刻

**不採用案**

最終結果へ統括stateまたはlocal Worldを参照保持する案、終了時状態を何も保存せず既存per-timestep結果だけにする案、binding clearanceまたはNode流量不足時に統括loopがunbound呼出しを省略する案は、採用しない。

**今回まだ未確定の事項**

終了時frozen記録の正式型名と全field、passage recordの正式型名と全field、統括stateの正式field、一時刻結果型と最終結果型の全field、resolved判定の完全実装仕様、unresolved理由の付与規則、horizon終了結果、stop reasonの最終Enum、全候補集合型、経済性評価との具体的API接続は、今回確定しない。Node流量不足時もunbound FCFS APIを毎時刻1回呼ぶことは確定済みである。一方、Node流量不足をhorizon終了時のunresolved理由へ反映する条件と診断規則は未確定である。

> 2026-09-25追加注記: 利用者判断により、unresolved理由は観測可能な事実だけから付与し、因果関係を推測しない方針を採用した。終了時Vehicle記録はVehicle名、Link名、位置x、state、current VisitKey、current Visit Node名に限定する。一候補統括loopの型、API、処理順、resolved、horizon、stop reason、unresolved付与規則は、直後の完全実装前仕様で確定した。全候補集合型と経済性評価接続は、引き続き後続構想である。上記「今回まだ未確定」は、2026-09-24途中確定時点の記録である。

**次の直接作業**

終了時frozen記録の必要最小限の型とfield、passage recordの型とfield、resolved判定位置、unresolved理由の保持と付与規則、horizon終了契約、一候補統括state、one-timestep結果、最終結果の完全なfield、初期化API、one-timestep API、run-to-completion API、専用テスト契約を確定し、統括loop全体の完全な実装前仕様として正本へ記録する。Python実装は、その完全仕様の確定と文書保存後に開始する。

> 2026-09-25追加注記: 上記「次の直接作業」は、2026-09-24途中確定時点の再開情報である。完全仕様の記録は完了した。現在の次の直接作業としては読まない。直後の2026-09-25追記を参照すること。

今回のMarkdown更新では、Pythonとテストを変更していない。テストも再実行していない。Git操作は行っていない。`diagnostics/order_control.zip` は既存未追跡のまま対象外である。

**TVT-MP候補別局所仮想計算の一候補統括loop完全実装前仕様を確定（2026-09-25）**

一候補統括loopの完全な実装前仕様を正本へ記録した。詳細は設計メモ本文の「TVT-MP候補別局所仮想計算の一候補統括loop完全実装前仕様」である。本小節はその要約である。commit `86ac06f` までの途中確定契約を包含する。horizon契約はWorld baselineと一致させ、H回の交通処理、処理時刻TからT+H-1とする。Python実装はまだ行っていない。全候補集合入口、経済性評価、最終確定接続は対象外である。

**新規予定2ファイル**

- `uxsim/order_control_tvt_mp_candidate_local_virtual_calculation.py`
- `tests_order_control_tvt_mp_candidate_local_virtual_calculation.py`

**責務**

一候補について、実装済み部品を正しい順序で実行する。offset管理、仮想時刻進行、binding transfer、unbound FCFS、required buyer / seller passage記録、local vehicle advance、新着incoming登録、outlink終端境界、時刻末resolved判定、horizon終了判定、unresolved診断、終了時frozen記録、最終frozen結果構築である。FIFO検査、general trade rank、concrete buyer candidate、全候補列挙、経済性評価、`G`、`R`、surplus、payment、compensation、候補採用または却下、最終順位確定、formal route保存、順位台帳更新、上位driver、実World交通反映は責務外である。

**3つの公開API**

- `initialize_tvt_mp_candidate_local_virtual_calculation_state(candidate_local_state, baseline_collector, downstream_boundary_node_result, configured_horizon_steps)`
- `run_tvt_mp_candidate_local_virtual_calculation_one_timestep(calculation_state)`
- `run_tvt_mp_candidate_local_virtual_calculation(calculation_state)`

`configured_horizon_steps` はPython `int` かつ1以上である。bool、0、負値は `ValueError`。対応するbaseline `ForkResult.configured_horizon_steps` をそのまま渡す。horizon 0は拒否する。horizon 0でTを1回処理する契約、交通処理0回、初期状態だけのresolved判定は設けない。buyers空は拒否する。sellers空は許可する。可変統括stateは `OrderControlTvtMpCandidateLocalVirtualCalculationState` である。公開読取の順序付き列はtupleである。

**required buyer / seller**

required buyerは `concrete_buyer_candidate_set.buyers_sorted`。空不可。required sellerは `trade_scope_of_this_candidate_visits` のうち `SELLER`。空可。追跡単位はVisitKeyである。Vehicle名だけでは追跡しない。NONPARTICIPATING、OUTSIDE_TRADE_SCOPE、confirmed_before、preconfirmedはrequiredではない。

**passage record**

型は `OrderControlTvtMpCandidatePassageRecord`。fieldは visit_key、vehicle_name、trade_role、binding_partition、binding_rank、baseline_passage_timestep、candidate_passage_timestep、route_next_link_name、route_origin、inlink_name である。初期化時に全required Visit分を作り、`candidate_passage_timestep = None` とする。取得源は当該時刻の `binding_transfer_result.transferred_binding_visit_keys` とrequired集合の積である。unbound結果のVehicle名は使わない。処理順4で確定し、時刻末で書き換えない。baselineとcandidateのpassage最大はどちらもT+H-1である。T+Hのcandidate passageは許可しない。

**処理順**

1. offset > 0の場合だけ virtual time one-step
2. binding transferを1回
3. unbound FCFS transferを必ず1回
4. required buyer / seller passageを記録
5. local vehicle advanceと新着incoming登録
6. outlink終端境界処理
7. 時刻末にresolved、最後の許可処理offset H-1のunresolved、または次時刻を判断

binding clearance停止時も、開始前Node流量不足時も、順位外候補0台時もunbound APIを必ず1回呼ぶ。開始不能時は既存部品が空完了する。空完了も `completed_virtual_timesteps` へ当該時刻を追加する。統括completed_virtual_timestepsは、その仮想timestepの全7手順が正常完了したことだけを表す。

**resolved**

全required buyerおよび全required sellerについて `candidate_passage_timestep` を取得済みであること。sellers空は充足。Hは1以上。offset 0は最初の許可処理時刻Tであり、そこで成立可能である。binding直後に揃っても、unbound、advance、boundaryを行い、時刻末に確定する。unrelated、unbound、boundary待機の残存はresolvedを妨げない。required通過が揃っていればboundary閉塞残存も妨げない。

**horizon**

horizon HはH回の交通処理である。処理offsetは0以上H-1以下。処理時刻はTからT+H-1。horizon 1はTのみ。horizon 2はT、T+1。horizon 3はT、T+1、T+2。T+Hでは交通処理しない。T+H-1でも全7手順を最後まで実行する。candidate passageの最大はT+H-1。baselineとcandidateは同じ処理範囲である。horizon 0は拒否する。最後の処理後にone-stepを呼ばない。既存one-stepを終端時計送りに使わない。

horizon完走時:

- `final_virtual_timestep = T+H-1`
- `final_offset = H-1`
- `simulated_timestep_count = H-1`
- `len(timestep_results) = H`

`simulated_timestep_count` は時計進行回数であり、交通処理回数ではない。`terminal_virtual_timestep` は追加しない。T+Hという終端ラベルが必要なら `baseline_timestep_T + configured_horizon_steps` から派生する。

**stop reason**

2値だけである。

- `RESOLVED`
- `HORIZON_EXHAUSTED_UNRESOLVED`

`HORIZON_EXHAUSTED_UNRESOLVED` は、最後の許可処理offset H-1の時刻末でrequired passageが不足したことである。T+Hを処理してからの未解決ではない。

**unresolved理由**

正本の6名称を維持する。resolved時は空tuple。unresolved時は少なくとも1件。重複なし。正本順。1件へ潰さない。

利用者採用方針: 観測できた事実だけを記録する。因果関係を推定しない。同時に起きた事象を直接原因と断定しない。分類4のacceptable outlink空がbuyer・seller未通過の直接原因だったとは推定しない。診断reasonは交通挙動や経済性評価を変えない。

- `REQUIRED_BUYER_OR_SELLER_DID_NOT_PASS_WITHIN_HORIZON`: 最後の交通処理時刻 T+H-1 の時刻末に未通過requiredが1件以上。正常unresolvedでは必ず付与する。
- `DOWNSTREAM_BOUNDARY_HAD_WAITING_VEHICLES_BUT_NO_TRANSFER`: baseline分岐B観測。直接原因とは断定しない。
- `DOWNSTREAM_BOUNDARY_REMAINED_BLOCKED_WITHIN_HORIZON`: 最後の交通処理時刻 T+H-1 のboundaryで閉塞と待機残存。直接原因とは断定しない。
- `CLEARANCE_OR_CAPACITY_BLOCKED_THROUGH_HORIZON`: 未通過requiredが、到着後に実際に処理した時刻全体でclearanceまたは容量阻害により通過できなかった継続事実。1回だけでは付けない。判定期間が1仮想timestepなら付けない。T+Hは観測対象にしない。
- `NO_ACCEPTABLE_OUTLINK_FOR_ROUTE_UNDETERMINED_VEHICLE_WITHIN_HORIZON`: いずれかの時刻でunbound `ACCEPTABLE_OUTLINKS_EMPTY` が1件以上。直接原因とは断定しない。
- `DOWNSTREAM_BOUNDARY_PREVENTED_REQUIRED_PASSAGE_INFORMATION`: Enum memberは残す。現段階では自動付与しない。境界閉塞とrequired未通過の併存だけでは因果を証明できないためである。

**最終結果**

型は `OrderControlTvtMpCandidateLocalVirtualCalculationResult`。liveな統括state、candidate local state、local World、Node、Link、Vehicleを持たない。終了時交通状態は独立frozen記録である。World全体の複製は作らない。per-timestep結果の型は `OrderControlTvtMpCandidateVirtualTimestepResult` である。unbound resultは常に存在し、`None` にしない。`final_virtual_timestep` は最後の処理時刻、`final_offset` は最後の処理offset、`simulated_timestep_count` は時計進行回数である。処理件数は `len(timestep_results)`。`terminal_virtual_timestep` は追加しない。

終了時Vehicle記録の型は `OrderControlTvtMpCandidateFinalVehicleRecord`。fieldは `vehicle_name`、`current_link_name`、`position_x`、`state`、`current_visit_key`、`current_visit_node_name` である。`v`、lane、leader、follower、`move_remain`、`link_arrival_time`、`x_old`、`x_next`、current Visit dictは保存しない。対象は終了時の対象inlink、対象outlink、target Node incomingの和集合である。

Link記録の型は `OrderControlTvtMpCandidateFinalLinkRecord`。inlinkとoutlinkを別tupleにし、登録順、物理順Vehicle名、容量残を持つ。Node記録の型は `OrderControlTvtMpCandidateFinalNodeRecord`。target Nodeのincoming、流量残、clearance履歴を持つ。boundary記録の型は `OrderControlTvtMpCandidateFinalOutlinkBoundaryRecord`。最終timestep結果と累積公開情報から構築し、baseline result自体は参照保持しない。詳細fieldは設計メモ第19節から第22節を参照する。

**二重実行防止と原子性**

統括 `completed_virtual_timesteps` で同時刻を1回に制限する。bindingとvirtual time one-stepの既存二重実行防止がないため、統括側で防ぐ。統括全体の一括rollbackは行わない。例外時はpartial timestep resultもfinal resultも返さない。先行部品の交通反映は戻さない。呼び出し側が当該候補local stateを破棄する。

**専用テスト契約**

公開型、初期化、horizon 0をValueError、horizon 1はTだけ、horizon 2はTとT+1、horizon 3はTとT+1とT+2、結果件数はH、passage最大はT+H-1、final_virtual_timestepはT+H-1、final_offsetはH-1、simulated_timestep_countはH-1、T+Hのbinding/unbound/advance/boundaryなし、最後の処理後にone-stepしない、baselineとcandidateの処理時刻範囲一致、early resolvedでも最後の処理時刻の全7手順完了、処理順、毎時刻unbound 1回、空完了、passage、resolved、unresolved付与、6番目reason非自動付与、終了記録の最小field、二重実行、不変性、例外を専用テストで固定する。詳細は設計メモ第26節である。

**実装対象外**

全候補集合入口、集合結果型の本番接続、経済性評価、expected time saving、waiting increase、`G`、`R`、surplus、utility、payment、compensation、候補採用・却下、最終順位確定、formal route保存、順位台帳更新、上位driver、実World交通反映、strategy-proofness検証。

**次の直接作業**

horizon端点補修後の独立確認と文書保存のあと、新規一候補統括モジュールと新規専用テストを実装する。実装前に新しい設計判断を追加しない。2026-09-23のBATCH端点記録は削除せず、更新注記を付けた。

今回のMarkdown更新では、Pythonとテストを変更していない。テストも再実行していない。Git操作は行っていない。`diagnostics/order_control.zip` は既存未追跡のまま対象外である。

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
