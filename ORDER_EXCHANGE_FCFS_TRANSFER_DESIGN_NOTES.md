# UXsim Order Exchange FCFS Transfer 設計メモ

## 位置づけ

このファイルは、フェーズ4-2完了後、FCFS用 `Node.transfer()` 分岐の実装に入る直前の詳細設計メモです。

既存の設計メモとの関係：

| ファイル | 位置づけ |
|----------|----------|
| [ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md) | フェーズ3-5完了後、フェーズ4の制御ロジック本体に入る前の大枠設計メモ |
| 本ファイル | フェーズ4-2完了後、FCFS用 `Node.transfer()` 分岐の詳細設計メモ |

進捗の詳細は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照してください。

## 現在までの前提（フェーズ4-2完了時点）

- `Vehicle` に `order_control_node_arrival_times` を追加済み
- order-control対象Nodeへの初回到着時刻を記録する処理を追加済み
- `Vehicle.update()` 内で、Vehicleが対象Nodeの `incoming_vehicles` に入った直後に初回到着時刻を記録している
- 記録対象は `order_control_eligible=True` かつ `order_control_type!="none"` のNode
- 同一Vehicle・同一Nodeについて、初回到着時刻は上書きしない
- FCFS、Batch Processing、Time-value Transaction の実際の `Node.transfer()` 制御ロジックはまだ未実装

---

## 1. 標準 `Node.transfer()` の構造

標準UXsimの `Node.transfer()` は、概ね以下の構造である。

1. `incoming_vehicles` から、各Vehicleの `route_next_link` を見て、outlink候補を作る
2. outlinkごとに、受入可能性を確認する
3. そのoutlinkに進みたいVehicleを `incoming_vehicles` から抽出する
4. 抽出されたVehicleの中から、`merge_priority` に基づいて1台を選ぶ
5. 選ばれたVehicleを次Linkへ移す
6. 各種容量、累積台数、leader/follower、lane、`move_remain` 等を更新する
7. 処理後、`incoming_vehicles` をクリアする

**つまり、標準 `Node.transfer()` は outlink起点 の車両選択構造である。**

一方、FCFSでは、自然な処理順序は以下である。

1. Nodeに先に到着したVehicleを見る
2. そのVehicleが進みたい `route_next_link` を確認する
3. 通過可能なら通す
4. 通過不能なら、その時点ではスキップし、次の到着順Vehicleを見る

**つまり、FCFSは Vehicle到着順起点 の車両選択構造である。**

このため、FCFSは標準 `Node.transfer()` の小修正ではなく、**専用の分岐処理として実装するのが自然**である。

---

## 2. FCFS用 `Node.transfer()` の基本方針

FCFS用の処理を適用する対象Nodeは、以下の条件を満たすNodeとする。

```
node.order_control_eligible is True and node.order_control_type == "fcfs"
```

それ以外のNodeでは、標準UXsimの `Node.transfer()` 処理を維持する。

**重要：** `order_control_type="none"` の場合に、標準UXsim挙動を変えないこと。

---

## 3. FCFSで使う到着順序

FCFSでは、Vehicleに記録済みの以下を参照する。

```python
veh.order_control_node_arrival_times[node.name]
```

これは、Vehicleが当該order-control対象Nodeの `incoming_vehicles` に初めて入った時刻である。

- FCFSの基本順序は、`veh.order_control_node_arrival_times[node.name]` が**早いVehicleを優先**する
- この値は、同一Vehicle・同一Nodeについて初回のみ記録され、以後上書きされない
- Vehicleが通過できずに次タイムステップ以降も再び `incoming_vehicles` に入った場合でも、FCFS上の到着順が後ろへずれることはない

---

## 4. FCFSで見る候補車両

FCFS処理で見る候補は、基本的に標準UXsimと同じく `node.incoming_vehicles` である。

ただし、候補Vehicleに対して、少なくとも以下の条件を確認する必要がある。

| 条件 | 内容 |
|------|------|
| 経路 | `veh.route_next_link` が `None` ではない |
| 先頭車両 | `veh` が現在の `veh.link` の先頭Vehicleである |
| outlink受入 | `veh.route_next_link` に物理的な受入余地がある |
| 流入容量 | `veh.route_next_link.capacity_in_remain >= W.DELTAN` |
| 流出容量 | `veh.link.capacity_out_remain >= W.DELTAN` |
| ノード容量 | `node.flow_capacity_remain >= W.DELTAN` |

標準UXsimでは信号条件として、`node.signal_phase in veh.link.signal_group` に相当する判定が含まれる。

**FCFSでは信号制御を使わない方針であるため、FCFS分岐ではこの信号条件は使わない。**

---

## 5. 初期実装方針：案Aを先に実装する

初回実装として採用する **案A** と、将来拡張として位置づける **案B** を区別する。

| 案 | 名称 | 概要 |
|----|------|------|
| 案A | クリアランスなしFCFS | 到着順 + 容量制約・先頭車両制約・outlink受入制約のみ |
| 案B | クリアランスありFCFS | 案Aに加え、異方向切替時のクリアランス制約 |

**現時点では、まず案A（クリアランスなしFCFS）を実装する方針である。**

### 案Aの長所

- 実装が小さい
- まずFCFS分岐そのものを検証できる
- `Node.transfer()` の分岐が標準挙動を壊さないか確認しやすい
- 不具合発生時に原因を切り分けやすい

### 案Aの短所

- 最終的な研究設計における安全・交錯制約はまだ表現できない
- Batch Processingの方向まとめ効果との接続はまだ弱い
- 後でクリアランス制約を追加する必要がある

### 案Bについて

案Bは最終的な研究設計に近いが、実装が一気に複雑になる。そのため、現時点では案Bをすぐには実装せず、まず案Aを実装する。

**ただし、案Aを捨て実装にしない。** 後で案Bへ移行しやすいように、以下をできるだけ分けて設計する。

- FCFS候補Vehicleの優先順位作成
- Vehicleが通過可能かどうかの判定
- 実際にVehicleを次Linkへ移す処理

---

## 6. 案A：クリアランスなしFCFSの基本処理案

クリアランスなしFCFSの処理は、概念的には以下とする。

1. `incoming_vehicles` のうち、`route_next_link` があるVehicleを集める
2. 各Vehicleについて、当該Nodeへの初回到着時刻を取得する
3. 到着時刻が早い順にVehicleを並べる
4. 到着順にVehicleを1台ずつ見る
5. 注目Vehicleについて、通過可能条件を確認する
6. 通過可能なら、そのVehicleを `route_next_link` へ移す
7. 通過不能なら、そのVehicleはその時点ではスキップし、次の到着順Vehicleを見る
8. Node容量・outlink容量・候補Vehicleが尽きるまで繰り返す
9. 最後に標準UXsimと同様、trip end待ちVehicleの処理を行う
10. 最後に `incoming_vehicles` をクリアする

---

## 7. 通過不能な先着Vehicleの扱い

FCFSでは、先に到着したVehicleを優先することが原則である。

しかし、先に到着したVehicleが以下の理由で通過できない場合がある。

- outlinkが満杯
- outlinkの `capacity_in_remain` が不足
- inlinkの `capacity_out_remain` が不足
- nodeの `flow_capacity_remain` が不足
- 当該Vehicleがinlinkの先頭Vehicleではない

この場合、先着Vehicleを無理に待つと、**別のoutlinkへ進めるVehicleまで停止させてしまう**。

したがって、クリアランスなしFCFSの初期実装では、到着順にVehicleを見るが、物理・容量制約により通れないVehicleは、その時点ではスキップし、次の到着順Vehicleを検討する。

---

## 8. 将来拡張としての案B：クリアランスありFCFS

クリアランスありFCFSでは、単に「通れるVehicleを到着順に探す」だけでは不十分である。

特に重要なのは、**先順位Vehicleがクリアランス待ちで通れない場合、後順位Vehicleを同じタイムステップで先に通してはいけない**、という点である。これはFCFSの公平性を維持するために重要である。

### 例

- `t = 0` に北方向VehicleがNodeに進入したとする
- `t = 1` に東方向Vehicle A と 北方向Vehicle B が候補になり、FCFS優先順位が以下であるとする
  - 1位: 東方向Vehicle A
  - 2位: 北方向Vehicle B

この場合、直前に通したVehicleは北方向である。したがって、`t=1` において東方向Vehicle Aは、異方向切替に伴うクリアランス制約により進入できない。

このとき、北方向Vehicle Bは直前Vehicleと同方向であり、物理的には進入可能かもしれない。しかし、FCFS優先順位ではAがBより上位である。**このため、`t=1` ではAをBが抜かしてはいけない。よって、このタイムステップでは誰も進入しない。**

`t = 2` では、クリアランス時間が経過済みであるため、Aを再評価する。Aが容量等の条件を満たせばAが進入する。Aが容量等の条件を満たさなければ、次順位のBを検討する。

---

## 9. クリアランス待ちと容量制約による通過不能の区別

クリアランスありFCFSでは、通過不能の理由を区別する必要がある。

### 1つ目：クリアランス制約により通れない場合

- 先順位Vehicleを後順位Vehicleが抜かしてはいけない
- 先順位Vehicleがクリアランス待ちなら、後順位Vehicleを検討せず、そのタイムステップは待つ

### 2つ目：クリアランスは満たしているが、容量等で通れない場合

たとえば以下で通れない場合である。

- outlinkが満杯
- `capacity_in_remain` 不足
- `capacity_out_remain` 不足
- `flow_capacity_remain` 不足
- inlink先頭Vehicleではない

この場合は、当該Vehicleは物理的・容量的にその時点で進めない。したがって、**次順位Vehicleを検討する**。

---

## 10. クリアランスありFCFSで必要になりそうなNode状態

将来、クリアランスありFCFSを実装する場合、少なくとも以下のNode状態が必要になる可能性がある。

| 属性 | 意味 |
|------|------|
| `last_order_control_inlink` | 直前にorder-control対象Nodeを通過したVehicleのinlink |
| `last_order_control_entry_timestep` | 直前にorder-control対象NodeへVehicleが進入したタイムステップ |
| `order_control_clearance_timesteps` | 異方向切替時に必要なクリアランス時間（タイムステップ単位） |

`order_control_clearance_timesteps` の初期候補は **1 timestep** とする。

ただし、これは案B以降で導入する想定である。案AのクリアランスなしFCFSでは必須ではない。

---

## 11. 同時到着時の固定ランダム順序

FCFSでは、同じタイムステップに複数Vehicleが同時到着する場合がある。この場合、到着時刻だけでは順序が決まらない。

### 検討されていた案

同時到着Vehicleの到着時刻そのものを前後に補正する案が検討された。

たとえば、5台が7.0秒に同時到着した場合、ランダム順序に従って、6.5秒、6.75秒、7.0秒、7.25秒、7.5秒のような補正時刻を割り振る案である。

この案の本質は、**同時到着Vehicleに一度だけランダム順序を与え、その順序を以後も固定する**、という点である。この考え方自体は有用である。

### 実到着時刻を書き換えない理由

しかし、実際の到着時刻である `order_control_node_arrival_times` を書き換えるのは避けるべきである。

- 実際には7.0秒に到着したVehicleが、6.5秒到着扱いになる
- 実到着時刻とFCFS優先順位用の値が混ざる
- 後で分析するときに、実際の到着時刻が分からなくなる
- 制御用優先順位と分析用状態の区別が曖昧になる

**したがって、実到着時刻は `veh.order_control_node_arrival_times[node.name]` に保持する。**

同時到着時の補助順位は、将来的に別の値として保持する方が安全である。

候補：

```python
veh.order_control_node_arrival_tiebreakers[node.name]
```

---

## 12. tiebreakerの意味

`tiebreaker` は、同時到着Vehicle同士の順序を決めるために、**一度だけ与えるランダムな補助値**である。

### 例

| Vehicle | arrival_time | tiebreaker |
|---------|--------------|------------|
| A | 7.0 | 0.314 |
| B | 7.0 | 0.872 |
| C | 7.0 | 0.105 |

3台はいずれも実到着時刻は7.0秒である。しかし、同着の中では tiebreaker の小さい順に並べる。したがって、順序は **C → A → B** になる。

Pythonでは、タプルでソートすると、左の要素から順に比較される。したがって、`(arrival_time, tiebreaker)` でソートすると、まず到着時刻が比較され、到着時刻が同じVehicle同士についてのみ、tiebreaker が比較される。

**意味の整理：**

- **第1キー:** 実際の初回到着時刻
- **第2キー:** 同時到着時の固定ランダム補助順位

---

## 13. tiebreakerをいつ実装するか

固定tiebreakerは、最終的には重要である。

特に、クリアランスありFCFSでは、同時到着時の順位が毎タイムステップ変わると、以下のような問題が起きる。

- `t=1` ではAがBより優先
- `t=2` ではBがAより優先

このように順位が変動すると、クリアランス待ち時の優先権保持が不安定になる。

**したがって、案Bの前には固定tiebreakerが必要になる可能性が高い。**

ただし、最初の案A（クリアランスなしFCFS）では、必須ではない。初回FCFS実装では、固定tiebreakerは後回しでもよい。

ただし、実装設計上は、**将来tiebreakerを追加しやすいようにしておくことが望ましい**。

---

## 14. 実際のリンク間移動処理の共通化

FCFS実装で最も危険なのは、Vehicleを次Linkへ移す処理を複製して壊すことである。

標準 `Node.transfer()` には、Vehicle選択後に以下の副作用が含まれる。

- `cum_departure` 更新
- `cum_arrival` 更新
- `traveltime_actual` 更新
- `link_arrival_time` 更新
- `capacity_out_remain` 減算
- `capacity_in_remain` 減算
- `flow_capacity_remain` 減算
- `inlink.vehicles.popleft()`
- `outlink.vehicles_enter_log` 更新
- `veh.link = outlink`
- `veh.x = 0`
- follower / leader 更新
- lane 更新
- `move_remain` 処理
- `outlink.vehicles.append(veh)`
- `incoming_vehicles.remove(veh)`
- trip end待ちVehicleの処理

これらはFCFSでも同様に必要である。

したがって、理想的には、将来的に `s._execute_vehicle_transfer(veh, outlink)` のような共通ヘルパーへ切り出すことが望ましい。

ただし、これはリファクタリング要素が強い。初回FCFS実装で一気に大規模リファクタリングすると、標準挙動を壊すリスクがある。**そのため、初回実装でどこまで共通化するかは慎重に判断する。**

---

## 15. 初回FCFS実装で最低限決める事項

初回FCFS実装前に、最低限以下を決める。

| 項目 | 決定内容 |
|------|----------|
| 実装範囲 | まずクリアランスなしFCFSを実装する |
| 対象Node | `node.order_control_eligible is True` かつ `node.order_control_type == "fcfs"` |
| 車両順序 | `veh.order_control_node_arrival_times[node.name]` の早い順 |
| 同時到着 | 固定tiebreakerは初回実装では後回しにしてよい |
| 通過不能先着車 | 物理・容量制約で通れない場合はスキップし、次の到着順Vehicleを検討 |
| 信号 | FCFS分岐では標準UXsimの信号条件は使わない |
| 判定の整理 | 通過可否判定は、可能な限り一箇所にまとめる |
| 標準挙動 | `order_control_type="none"` のNodeでは、標準UXsimの挙動を変えない |

---

## 16. 初回FCFS実装後に確認すべきテスト

初回FCFS実装後には、今回の変更が既存機能を壊していないことを確認するため、少なくとも以下の既存テストおよび標準サンプルを再実行する必要がある。

- `tests_order_exchange_baseline.py`
- `tests_vehicle_research_attributes.py`
- `tests_node_order_control_attributes.py`
- `tests_world_order_control_setters.py`
- `tests_order_control_eligibility.py`
- `tests_random_eligible_order_control.py`
- `tests_order_control_node_arrival_times.py`
- `demos_and_examples/example_00en_simple.py`

また、FCFS分岐そのものを確認するため、新規テストとして `tests_fcfs_order_control_transfer.py` を追加する可能性がある。

### 新規テストの想定内容

最小ネットワーク例：

```
orig1 -> merge -> dest
orig2 -> merge -> dest
```

`merge` を `order_control_type="fcfs"` に設定し、少なくとも以下を確認する想定である。

- `merge` が `order_control_eligible=True` になること
- `merge` に `order_control_type="fcfs"` を設定できること
- 複数Vehicleが `merge` に到着したとき、初回到着時刻が早いVehicleが優先されること
- `order_control_type="none"` の場合には標準挙動が維持されること
- outlinkが詰まって通れないVehicleがいても、シミュレーションが異常停止しないこと
- 通過不能Vehicleの初回到着時刻が上書きされないこと

---

## 17. 今後の実装順序案

| Step | 内容 |
|------|------|
| **Step 1** | FCFS用分岐の最小実装 — `Node.transfer()` で `order_control_type=="fcfs"` の場合だけFCFS処理へ分岐。クリアランス制約なし、tiebreakerなし、到着時刻順のみ |
| **Step 2** | FCFS用通過可否判定を整理 — 通過可否判定をヘルパー化できるか検討。後でクリアランス制約を追加しやすくする |
| **Step 3** | FCFS用テスト追加 — 最小ネットワークでFCFS分岐が動くことを確認。標準挙動が壊れていないことを確認 |
| **Step 4** | 同時到着時の固定tiebreakerを検討 — `Vehicle` に `order_control_node_arrival_tiebreakers` を追加するか検討。実到着時刻は書き換えない。ソートキーを `(arrival_time, tiebreaker)` に拡張 |
| **Step 5** | クリアランスありFCFSへ拡張 — Nodeに `last_order_control_inlink`、`last_order_control_entry_timestep`、`order_control_clearance_timesteps` を追加するか検討。クリアランス待ちと容量制約による通過不能を区別 |

---

## 18. 現時点の結論

現時点では、**まずはクリアランスなしFCFS（案A）を実装する**。

ただし、その実装は将来のクリアランスありFCFS（案B）の土台になるようにする。

特に重要なのは以下である。

- FCFS候補Vehicleの優先順位作成
- 通過可否判定
- 実際のリンク間移動処理

**これらをできるだけ分けて考えること。**

また、同時到着時の固定ランダム順序については、到着時刻そのものを書き換えるのではなく、将来的に別の `tiebreaker` を持たせる方式が望ましい。

**以上を踏まえ、次の実装フェーズでは、FCFS用 `Node.transfer()` 分岐の最小実装に進む。**

---

## 新しいチャットで再開する場合

新しいチャットでは、以下を伝える。

- [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を読んでください
- [ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4_DESIGN_NOTES.md) を読んでください
- [ORDER_EXCHANGE_RESEARCH_CONTEXT.md](ORDER_EXCHANGE_RESEARCH_CONTEXT.md) を読んでください
- 本ファイル [ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md](ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md) を読んでください
- 現在のブランチは `feature/intersection-order-control` です
- フェーズ4-2まで完了済みです
- 次は、FCFS用 `Node.transfer()` 分岐の最小実装（案A：クリアランスなしFCFS）に進む予定です
