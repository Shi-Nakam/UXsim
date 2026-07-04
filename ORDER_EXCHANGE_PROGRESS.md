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

### フェーズ4-5追加検証：UXsim標準挙動とFCFS(clearance=0)のsanity check比較

完了済み。

#### 全体概要

- phase 4-5のFCFS(clearance=0)実装について、小規模単体テスト・X/Y/Z問題テストに加えて、中規模・grid型ネットワークでのsanity check比較を実施した。
- 比較対象は以下の4種類（Step 4Dで高需要 signalized grid を追加）。
  - corridor型ネットワークにおけるunsignalized UXsim標準transfer vs FCFS(clearance=0)
  - grid型ネットワークにおけるunsignalized UXsim標準transfer vs FCFS(clearance=0)
  - grid型ネットワークにおけるsignalized UXsim標準transfer vs FCFS(clearance=0)（Step 4C：1000台）
  - grid型ネットワークにおけるsignalized UXsim標準transfer vs FCFS(clearance=0)（Step 4D：高需要5000台・10000台）
- 目的は研究上の性能評価ではなく、FCFS実装が中規模・複数経路ネットワークで極端に破綻しないことを確認する sanity check である。
- FCFSがUXsim標準より常に良い、または常に悪いと主張するものではない。
- ケースによってFCFSが良い場合も悪い場合もあり得る。
- 重要なのは、完了台数・平均旅行時間・総旅行時間・総走行距離などが極端に乖離しないかを確認すること。
- Step 4A〜4Dはいずれも `uxsim/uxsim.py` を変更せず、新規テストファイルのみ追加した。

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
- 本格的には、さらに高需要、`clearance_timesteps=1`、信号offset、サイクル長、需要分布、ネットワークサイズなどを変えた体系的検証が必要。

#### 比較結果の解釈

- Step 4A〜4Dにより、FCFS(clearance=0)は中規模corridor型、grid unsignalized型、grid signalized型（中需要・高需要）のいずれでも、完了台数・総走行距離・旅行時間指標において極端な破綻を示さなかった。
- corridor型ではFCFSが約4.3%遅かった。
- unsignalized grid型ではFCFSが約1.1%遅かった。
- signalized grid型（Step 4C：1000台）ではFCFSが約50%の平均旅行時間となり、固定2相信号よりかなり短かった。
- signalized grid型（Step 4D：5000台・10000台）では、高需要化に伴いFCFS/signalized ratioが0.500→0.581→0.665と縮小したが、依然としてFCFSの方が短い旅行時間だった。
- unsignalized grid型でほぼ同等だったことは、信号がないUXsim標準transferとFCFS(clearance=0)が大きく乖離しないことの確認になる。
- signalized grid型でFCFSが大幅に短い旅行時間となったことは、固定2相信号の信号待ちが強く効いたためと解釈できる。Step 4Dでは高需要によりこの差は縮小した。
- ただし、これは研究上の性能評価ではなく、まだ sanity check の段階である。
- 特に、`signal=[60,60]` は固定2相信号であり、渋滞時には有効に働く可能性がある一方、低〜中需要時には信号待ちが過剰になる可能性がある。
- 本格的な性能比較には、需要条件、信号設定、オフセット、信号最適化、クリアランス値、ネットワーク構造などを体系的に変えた実験設計が必要。

#### 現在の理解

- FCFS(clearance=0)の単体・X/Y/Z問題テストに加え、corridor型・grid unsignalized型・grid signalized型（中需要・高需要）のsanity checkでも極端な破綻は見られなかった。
- unsignalized UXsim standard transfer との比較では、FCFSはおおむね同等〜やや遅い程度だった。
- signalized UXsim standard（固定2相 `[60,60]`）との比較では、Step 4Cの需要条件下ではFCFSの方が旅行時間が短かった。Step 4Dでは高需要化に伴いratioが0.500→0.581→0.665と縮小したが、5000台・10000台でもFCFSの方が短い旅行時間だった。これは信号待ちの影響が大きいためであり、性能優位の一般結論ではない。
- Step 4Dは clearance-zero FCFS の高需要比較であり、clearance-one FCFS の高需要比較はまだ未実施。
- Step 4A〜4Dはすべて新規テストファイルのみの追加であり、`uxsim/uxsim.py` は変更していない。

#### 実行済みテスト

以下を実行済みで、すべて成功した。

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

これらは origin/feature/intersection-order-control に push 済みである。

#### 後続事項

- Step 4Dの結果を踏まえた簡易分析メモの作成。
- `clearance_timesteps=1` の高需要 signalized grid 比較。
- signal offset や signal cycle を変えた比較。
- さらに高需要条件、または異なるネットワークサイズでの比較。
- signalized UXsim standard と FCFS の比較条件をより体系化した実験設計。
- signal offset、signal cycle、需要条件、network size、`clearance_timesteps` を変えた実験計画。
- Batch Processing、Time-value Transaction、支払い処理は引き続き未実装。

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

Vehicleへの追加メソッド・処理：

- record_order_control_node_first_arrival(node) を追加
- order_control_node_arrival_times に、order-control対象Nodeへの初回到着時刻を記録する処理を追加
- order_control_node_arrival_tiebreakers に、初回到着時の固定tiebreaker値を記録する処理を追加
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

### Worldへの追加属性

- order_control_eligibility_prepared
- order_control_clearance_timesteps（phase 4-5、デフォルト1）

### Worldへの追加メソッド

- set_order_control_for_nodes(...)
- infer_order_control_eligible_nodes(...)
- set_order_control_eligible_flag_for_nodes(...)
- set_order_control_for_randomly_selected_eligible_nodes(...)
- set_order_control_clearance_timesteps(clearance_timesteps)（phase 4-5）

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
- corridor型・grid unsignalized型・grid signalized型のsanity check（Step 4A〜4C）および高需要grid sanity check（Step 4D）でも極端な破綻は確認されなかった
- 標準UXsim挙動を壊さない方針は引き続き最重要である

### テスト追加方針

- 新しい挙動テストを追加する際も、まずはテストのみを追加し、uxsim/uxsim.py を勝手に変更しない方針を維持する

### GitHub運用

- feature/intersection-order-control ブランチは origin/feature/intersection-order-control とtracking済み
- 重要な区切りごとに git push して GitHub へ退避する
- 現時点では HTTPS + PAT による認証。長期運用では SSH 移行を検討する余地がある

## 次に進む予定

現在の進捗：

- phase 4-5では、クリアランスありFCFSの実装・接続・基本検証・X/Y/Z問題検証まで完了済み。
- Step 4A〜4Cとして、corridor/gridのsanity check比較を追加済み。
- Step 4Dとして、高需要grid型 signalized UXsim standard vs clearance-zero FCFS sanity checkを追加済み。
- phase 4-5 の実装・テスト側の最新コミットは 1ef9f9a phase 4-5: add high-demand grid clearance-zero FCFS vs signalized UXsim sanity test。
- この progress memo 更新コミットが後に続くため、作業再開時の最新コミットは git log で確認すること。
- feature/intersection-order-control は origin/feature/intersection-order-control と同期済み。
- 1ef9f9a 時点では作業ツリーはcleanであった。この progress memo 更新後は、コミット・push後に `git status` で作業ツリーがcleanであることを確認する。

次に進む候補：

- Step 4Dの結果を踏まえた簡易分析メモの作成。
- `clearance_timesteps=1` の高需要 signalized grid 比較。
- signal offset や signal cycle を変えた比較。
- さらに高需要条件、または異なるネットワークサイズでの比較。
- Batch Processing の設計・実装検討。
- Time-value Transaction の設計・実装検討。
- 支払い処理の設計・実装検討。

## 新しいチャットで再開する場合

新しいチャットでは、以下を伝える。

- ORDER_EXCHANGE_PROGRESS.md を読んでください
- ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md を読んでください
- tests_fcfs_order_control_clearance_0.py を読んでください
- tests_fcfs_order_control_clearance_1.py を読んでください
- tests_fcfs_order_control_clearance_xyz.py を読んでください
- tests_order_control_fcfs_vs_uxsim_standard_medium_network.py を読んでください
- tests_order_control_fcfs_vs_uxsim_standard_grid_network.py を読んでください
- tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_network.py を読んでください
- tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py を読んでください
- 現在のブランチは feature/intersection-order-control です
- feature/intersection-order-control ブランチは origin/feature/intersection-order-control とtracking済みで、GitHubへpush済みです
- 現在の通常fcfs経路は `transfer_fcfs_clearance()` を呼ぶ
- `transfer_fcfs_no_clearance()` は回帰確認・デバッグ用に残っている
- `clearance_timesteps=0/1`、X/Y/Z問題、corridor/grid sanity checks、高需要grid sanity check（Step 4D）はテスト済み
- corridor型 sanity check（`tests_order_control_fcfs_vs_uxsim_standard_medium_network.py`）はコミット名に unsignalized とないが、実態は unsignalized UXsim標準transfer との比較である
- Step 4Dは clearance-zero FCFS の高需要比較であり、clearance-one FCFS はまだ未比較
- phase 4-5 の実装・テスト側の最新コミットは 1ef9f9a phase 4-5: add high-demand grid clearance-zero FCFS vs signalized UXsim sanity test
- ただし、その後に progress memo 更新コミットがある可能性があるため、git log --oneline -20 で最新状態を確認する
- 次は Step 4D結果の分析メモ、`clearance_timesteps=1` 高需要比較、信号設定の体系化、Batch Processing / Time-value Transaction / 支払い処理へ進む候補
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md、ORDER_EXCHANGE_RESEARCH_CONTEXT.md、ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md も必要に応じて参照してください
- git log --oneline -20 と git status の結果を貼ります
- GitHub運用は現在 HTTPS + PAT。将来的にSSH移行を検討する余地があります
