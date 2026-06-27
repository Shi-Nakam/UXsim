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

- `transfer_fcfs()` を追加
- `Node.transfer()` の冒頭に、`order_control_eligible=True` かつ `order_control_type=="fcfs"` の場合だけ `transfer_fcfs()` に分岐する処理を追加
- `order_control_type="none"` のNodeでは標準 `Node.transfer()` の既存処理を維持

Node.transfer_fcfs()：

- FCFS候補Vehicleのソートキーを `(arrival_time, tiebreaker, veh.id)` に変更
- tiebreakerは同時到着時の固定補助順位
- veh.id は tiebreaker同値時の決定的な最終タイブレーク
- FCFSの通過可否判定や blocked-outlink skip 本体は変更していない

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
- FCFS候補Vehicleのソートキーは `(arrival_time, tiebreaker, veh.id)` である
- 方向切替・クリアランス制約は後続フェーズで扱う
- 標準 Node.transfer() との共通ヘルパー化は行っていない。order-control系共通ヘルパー化は将来必要性が明確になった段階で検討する

### テスト追加方針

- 新しい挙動テストを追加する際も、まずはテストのみを追加し、uxsim/uxsim.py を勝手に変更しない方針を維持する

### GitHub運用

- feature/intersection-order-control ブランチは origin/feature/intersection-order-control とtracking済み
- 重要な区切りごとに git push して GitHub へ退避する
- 現時点では HTTPS + PAT による認証。長期運用では SSH 移行を検討する余地がある

## 次に進む予定

現在の進捗：

- フェーズ4-4として、FCFS同時到着時の固定tiebreaker実装とテスト追加まで完了済み

次に進む候補：

- 案B：クリアランスありFCFSに進む前の設計検討
- 案Bでは、inlinkが異なる場合を異方向切替とみなし、クリアランス制約をどう導入するかを検討する必要がある
- クリアランスありFCFSでは、クリアランス待ちによる通過不能と容量・物理制約による通過不能を区別する必要がある
- 先順位Vehicleがクリアランス待ちの場合に、後順位Vehicleが先順位Vehicleを追い越せないようにするルールをどう実装するかが重要論点である
- Batch Processing、Time-value Transaction、支払い処理は後続フェーズで扱う
- 標準UXsim挙動を壊さない方針は引き続き最重要である
- 新しい挙動テストを追加する際も、まずはテストのみを追加し、uxsim/uxsim.py を勝手に変更しない方針を維持する
- 重要な区切りごとに git push して GitHub へ退避する運用を継続する

## 新しいチャットで再開する場合

新しいチャットでは、以下を伝える。

- ORDER_EXCHANGE_PROGRESS.md を読んでください
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md を読んでください
- ORDER_EXCHANGE_RESEARCH_CONTEXT.md を読んでください
- ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md を読んでください
- 現在のブランチは feature/intersection-order-control です
- feature/intersection-order-control ブランチは origin/feature/intersection-order-control とtracking済みで、GitHubへpush済みです
- フェーズ4-4まで完了済みです
- d3f3c4d phase 4-4: add FCFS arrival tiebreakers and tests まで完了・push済みです
- フェーズ4-4として、FCFS同時到着時の固定tiebreaker実装と検証テストが完了しています
- フェーズ4-3実装に対する詳細検証として、arrival-order behavior と blocked-outlink skip behavior は確認済みです
- order_control_eligible の自動判定条件は、len(node.inlinks) >= 2 かつ len(node.outlinks) >= 1 に修正済みです
- git log --oneline -20 と git status の結果を貼ります
- 次は、案B：クリアランスありFCFSに進む前の設計検討を行う段階です
- 案Bでは、inlinkが異なる場合を異方向切替とみなし、クリアランス制約、クリアランス待ち時の優先権保持、容量制約との区別を検討する必要があります
- GitHub運用は現在 HTTPS + PAT。将来的にSSH移行を検討する余地があります
