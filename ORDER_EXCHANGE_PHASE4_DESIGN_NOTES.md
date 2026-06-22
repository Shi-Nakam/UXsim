# UXsim Order Exchange フェーズ4設計メモ

## 位置づけ

このファイルは、フェーズ3-5完了後に行ったフェーズ4着手前の設計議論をまとめたものです。

既存の進捗メモ：

- ORDER_EXCHANGE_PROGRESS.md

には、フェーズ3-5までの完了済み実装が記録されています。

本ファイルでは、まだ実装していないが、今後のフェーズ4以降で重要になる設計判断・未決論点を記録します。

## 前提：フェーズ3-5までの完了内容

フェーズ3-5までに、以下が実装済みです。

- Nodeに order_control_type, batch_size, transaction_case を追加
- Nodeに order_control_eligible を追加
- World.set_order_control_for_nodes(...) を追加
- World.infer_order_control_eligible_nodes(...) を追加
- World.set_order_control_eligible_flag_for_nodes(...) を追加
- World.set_order_control_for_randomly_selected_eligible_nodes(...) を追加
- order_control_eligible の自動判定条件は以下：
  - len(node.inlinks) >= 2
  - len(node.outlinks) >= 1
- ランダム選択は order_control_eligible=True のNode集合から行う
- 補助Node除外などは、set_order_control_eligible_flag_for_nodes(..., False) で事前に行う
- FCFS, Batch Processing, Time-value Transaction の実制御ロジックはまだ未実装

## フェーズ4へ進む理由

設定系の機能はフェーズ3-5まででかなり整ったため、次は制御ロジック本体に入る方向を検討する。

当初のロードマップでは、フェーズ4付近で以下を扱う想定だった。

- 検知領域
- 候補車両抽出
- FCFS / Batch Processing / Time-value Transaction のための準備

ただし、議論の結果、単純に「検知領域内の車両を候補にする」だけでは不十分であることが分かった。

## 検知領域だけでは不十分である理由

検知領域に入っていることは、順序交換や順序制御の必要条件にはなり得るが、十分条件ではない。

特に Batch Processing や Time-value Transaction では、本当に重要なのは交差点到着予定時刻ではなく、交差点通過予定時刻である。

理由：

- 車両が交差点に10秒後に到着しても、7秒待機するなら通過は17秒後になる
- 順序交換で扱うべきなのは、実際に交差点を通過する順序である
- 自由流到着時刻だけでは、待ち行列や下流詰まりを反映できない
- 順序交換が意味を持つのは、むしろ待機や競合がある状況である

したがって、Batch Processing や Time-value Transaction の候補車両抽出では、将来的に通過予定時刻またはそれに相当する状態量を設計する必要がある。

## FCFSの再定義

FCFSについては、検知領域に入った順ではなく、交差点到着順で定義する方が自然である。

理由：

- 検知領域に先に入っても、その後渋滞に巻き込まれて交差点到着が遅れる可能性がある
- 逆に、後から検知領域に入っても、スムーズに交差点へ到着する車両があり得る
- First-Come, First-Served の “come” は、検知領域進入ではなく、交差点通過待ち状態への到着と解釈する方が自然

UXsim上では、Vehicleが現在Linkの下流端に到達し、Node通過・次Link進入の処理待ちになると、end_node.incoming_vehicles に追加される。
このタイミングが、FCFSでいう交差点到着時刻に近い。

ただし、到着が早い車両が必ず先に通過できるとは限らない。
たとえば、その車両の進みたい outlink が満杯なら、その車両は通れず、後から来た別車両が先に進むことはあり得る。

したがって、FCFSは以下のように定義するのが自然である。

- 対象Nodeへ到着した時刻が早い車両を優先する
- ただし、容量制約、先頭車両制約、outlink受入制約などを満たさない車両はその時点では通れない
- 通れない車両はスキップされ、次の優先順位の車両を検討する
- 同時到着時の扱いは未決定

## Node.transfer() の依存関係調査結果

UXsimの Node.transfer() は、標準状態では outlink 起点の構造になっている。

標準UXsimの大まかな流れ：

1. incoming_vehicles から route_next_link を持つ車両を見て outlink候補を作る
2. outlinkごとに受け入れ可能性を確認する
3. そのoutlinkへ進みたい車両を集める
4. merge_priority に基づいて1台を選ぶ
5. 選ばれた車両を次Linkへ移す

一方、FCFSとして自然なのは vehicle到着順起点である。

FCFSの理想的な流れ：

1. incoming_vehicles の中の車両を到着時刻順に見る
2. 注目している車両の route_next_link を確認する
3. その outlink に入れるか確認する
4. 入れるなら通す
5. 入れないなら、次に到着時刻が早い車両を見る

つまり、標準UXsimは outlink起点、FCFSは vehicle起点である。

## 依存関係調査で確認したこと

### incoming_vehicles

- Vehicle.update() で end_node.incoming_vehicles に追加される
- Node.transfer() で処理される
- Node.transfer() の最後で空にされる
- 実質的に、そのタイムステップのNode進入要求リストとして使われている
- Node.transfer() 周辺にかなり閉じた構造である

### route_next_link

- Vehicle.update() 内で route_next_link_choice() により決まる
- Node.transfer() 前には veh.route_next_link が設定されている
- FCFSでも、veh.route_next_link を使って、その車両が進みたい outlink を確認できる見込み

### capacity_in_remain

- Link.update() 側で回復する
- Node.transfer() 内で outlink への流入時に消費される
- FCFSでも、各Vehicleの route_next_link に対して確認・消費できそう

### capacity_out_remain

- Link.update() 側で回復する
- Node.transfer() 内で inlink から退出する際に消費される
- FCFSでも、veh.link.capacity_out_remain を見ることで扱えそう

### flow_capacity_remain

- Node.update() 側で回復する
- Node.transfer() 内で車両通過時に消費される
- FCFSでも、node.flow_capacity_remain を確認・消費できそう

### merge_priority

- 実質的な車両選択ロジックとしては Node.transfer() 内で使用されている
- FCFSでは merge_priority を使わない可能性が高い

### signal_group / signal_phase

- 実質的な通過可否条件としては Node.transfer() 内で使われている
- FCFSでは信号を使わないため、この条件はFCFS用処理では外す必要がある

## Node.transfer() の今後の設計方針

Node.transfer() を将来的に方式別に分ける可能性がある。

概念的には：

- order_control_type="none"
  - 現行UXsim標準の transfer 処理を使う

- order_control_type="fcfs"
  - FCFS用の vehicle到着順起点の処理を使う

- order_control_type="batch"
  - 将来Batch Processing用の処理を使う

- order_control_type="time_value"
  - 将来Time-value Transaction用の処理を使う

ただし、すべてを丸ごと別実装にすると危険である。

理由：
Node.transfer() 内には、車両選択だけでなく以下の副作用が含まれている。

- cum_departure / cum_arrival 更新
- traveltime_actual 更新
- capacity_out_remain / capacity_in_remain / flow_capacity_remain の減算
- inlink.vehicles.popleft()
- veh.link = outlink
- veh.x = 0
- leader / follower 更新
- lane 更新
- move_remain 処理
- outlink.vehicles.append(veh)
- incoming_vehicles.remove(veh)
- incoming_vehicles のクリア
- トリップ終了待ち車両の処理

したがって、将来的には以下のように分けるのが望ましい。

- 車両選択ロジック
  - 標準UXsim
  - FCFS
  - Batch Processing
  - Time-value Transaction

- 実際に選ばれたVehicleを次Linkへ移す処理
  - できる限り共通化する

## FCFSの同時到着問題

FCFSで同時到着した車両が複数ある場合の扱いは未決定である。

当初はランダム選択が自然に見えたが、次の問題がある。

- 現実の交差点では、直前に通した車両と同じ方向の車両を続けて通した方が効率が良い場合がある
- しかし、UXsim標準のNodeモデルが、同方向連続通過と異方向交互通過の効率差を表現しているかは不明
- もしUXsimでその差が出ないなら、Batch Processingが方向をまとめることで効率を上げる効果も表現されにくい

したがって、将来的に以下のような共通制約を設計する必要がある可能性がある。

## 方向切替・クリアランス制約の必要性

UXsim標準では信号制御により、方向ごとの通行タイミングが制御される。
信号を使わないFCFS / Batch / Time-valueでは、それに代わる交差点内の安全・競合制約が必要になる可能性がある。

検討中のルール案：

- 直前に通した車両と同じinlinkから来る車両は、次のタイムステップでも通過可能
- 直前に通した車両と異なるinlinkから来る車両は、1タイムステップ分のクリアランス待ちを必要とする
- ただし、後続車が直後に来ていない場合は、余計な待ちを発生させる必要はない

このルールを全方式に共通適用すれば、Batch Processingが同方向車両をまとめることで方向切替回数を減らし、効率向上を生む余地が出る。

この点は、FCFS実装前に重要な設計論点として残す。

## 制御用状態と分析ログは分ける

UXsim標準にはVehicleログが存在する。

主な標準ログ：

- log_t
- log_state
- log_link
- log_x
- log_s
- log_v
- log_lane
- log_t_link

特に log_t_link は、Vehicleが新しいLinkに入った時刻とLinkを記録する。
UXsimではNode内移動時間が明示的にモデル化されていないように見えるため、outlinkに入った時刻は、UXsim実装上のNode通過時刻として扱える可能性が高い。

ただし、標準ログは基本的に「起こったことの記録」である。

一方、FCFSで必要な対象Nodeへの到着時刻は、次にどの車両を通すかを決めるための制御用状態であり、単なる事後ログではない。

したがって、以下を分けて設計する必要がある。

- 制御用状態
  - FCFSなどの制御ロジックが実際に参照する情報

- 分析用ログ
  - あとで標準UXsim / FCFS / Batch / Time-valueを比較するための記録

## 当面の設計方針：Vehicle側に到着時刻を持たせる

最初の実装では、制御用状態として以下をVehicleに追加する方針。

- order_control_node_arrival_times

これは辞書とする。

用途：

- order control対象Nodeへの初回到着時刻を記録する
- 現在は主にFCFS順序決定に使う想定
- 将来、Batch Processing や Time-value Transaction でも再利用する可能性がある

現時点では、以下はまだ追加しない。

- order_control_node_arrival_orders
- Node側の arrival_order_counter
- order_control_node_passage_log
- 到着予定時刻
- 通過予定時刻
- 進入順序ログ

理由：

- FCFSの同時到着時タイブレークは未決定
- 到着順序番号を先に固定すると、後で同時到着処理を変えにくくなる
- まずは初回到着時刻だけを制御用状態として持たせるのが安全

## order_control_node_arrival_times の想定仕様

- Vehicle側に持たせる
- dict とする
- 現時点では node.name をキーにする
- 値は、Vehicleが対象Nodeの incoming_vehicles に初めて入った時刻
- 時刻は秒単位、つまり W.T * W.DELTAT を想定する
- 同一Vehicleが同一Nodeを複数回通る場合には、node.name だけをキーにする設計は不十分になる可能性がある
- ただし、現在想定している単純ネットワーク・単純ODでは、同一Vehicleが同一Nodeを複数回通らないため、この設計で十分と考える

重要：

- 到着時刻は初回のみ記録する
- そのVehicleが通過できず、次ステップ以降も incoming_vehicles に入り直しても、到着時刻は上書きしない
- これはFCFSで、最初に交差点通過待ち状態になった時刻を保持するために必要

## 次に進む候補

フェーズ4に入る前に、以下2系統の設計・実装候補がある。

### A. 交差点進入制約の設計

order control対象Nodeでは、信号を使わない代わりに、交差点内の安全・競合制約を独自に定義する必要がある可能性がある。

検討事項：

- 同方向・異方向を何で判定するか
  - inlinkベース
  - movement = inlink→outlink ベース
- 異方向切替時の待ち時間を何ステップにするか
  - 初期値は1 timestepが候補
- この制約をFCFS / Batch Processing / Time-value Transactionすべてに共通適用するか
- Nodeにどの状態変数を持たせるか
  - last_order_control_inlink
  - last_order_control_movement
  - last_order_control_entry_timestep
  - order_control_clearance_timesteps
- 標準UXsimの order_control_type="none" には影響させない

### B. 最初の安全な実装小フェーズ

上記の交差点進入制約は重要だが、設計論点が大きい。

一方で、FCFSや後続手法の基礎として、Vehicle側に order_control_node_arrival_times を追加する小フェーズは比較的安全に実装できる。

フェーズ4-1候補：

- Vehicle.__init__() に order_control_node_arrival_times = {} を追加
- これは order control対象Nodeへの初回到着時刻を保持する制御用状態
- 現在は主にFCFS順序決定に使う想定
- 将来Batch ProcessingやTime-value Transactionでも再利用する可能性がある
- 現時点では node.name をキーにする
- 同一Vehicleが同一Nodeを複数回通る場合はキー設計の拡張が必要

この段階ではまだ以下は行わない。

- 実際に到着時刻を記録する処理
- Node.transfer() のFCFS分岐
- 通過ログ
- Batch Processing
- Time-value Transaction

## 新しいチャットで再開する場合

新しいチャットでは以下を伝える。

- ORDER_EXCHANGE_PROGRESS.md を読んでください
- ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md も読んでください
- 現在のブランチは feature/intersection-order-control です
- フェーズ3-5まで実装・コミット済みです
- フェーズ4に入る前の設計議論として、このファイルにNode.transfer()依存関係調査、FCFSの定義、方向切替制約、制御用状態と分析ログの分離方針をまとめています
- 次は、A. 交差点進入制約の設計をさらに詰めるか、B. Vehicleに order_control_node_arrival_times を追加する小フェーズから始める候補があります
