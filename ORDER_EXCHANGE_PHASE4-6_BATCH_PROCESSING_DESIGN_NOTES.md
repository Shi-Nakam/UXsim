# ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES

UXsim Order Exchange 改変作業における、phase 4-6：交差点BATCH処理の実装前正式設計メモ。

進捗の詳細は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照してください。FCFS / clearance 実装の詳細は [ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md) を参照してください。

---

## 1A. 実装状況サマリ（phase 4-6A〜4-6D）

進捗の詳細・コミットID・回帰結果は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照。

| 区分 | 内容 |
|------|------|
| **実装・テスト・コミット済み** | phase 4-6A：`earliest_arrival_timestep` 記録（94b05f2） |
| | phase 4-6B：BATCH状態コンテナ（28ed156） |
| | phase 4-6C：`get_order_control_batch_trigger_candidates()`（40d5ad7） |
| | phase 4-6D：t_trigger Level 0/1推定（d79db61） |
| **設計確定・未実装** | BATCH候補集合形成（`earliest <= t_trigger`、全inlink走査） |
| | inlink別batch形成、N適用、batch_id発行、assignments書き込み |
| | service queue追加、residual batch、`Node.transfer()` batch分岐 |
| | snapshot estimated arrivalによるinlink別batch間順序 |
| | Level 2仮想サービス計算、Level 2→Level 1 fallback |
| **当面の研究シナリオ前提** | 比較対象内部交差点Nodeを目的地としない端点間OD |
| | 全比較方式で同一ネットワーク・同一OD需要 |
| **将来課題** | 比較対象Node共通管理、目的地自動検証、trip-end service unit |
| | taxi mode向け動的dest検証、Time-value Transaction本体 |
| **次フェーズ候補** | phase 4-6E：全inlinkからFIFO維持でBATCH候補抽出（参照専用） |

---

## 1B. このメモの位置づけ（続き）

- 本メモは、**UXsimへのBATCH処理実装前の正式設計メモ**である。
- 背景資料として、以下のPDFメモがある。
  - ファイル名：`UXsim_BATCH_design_note.pdf`
  - タイトル：UXsim向け簡易BATCH処理 実装デザインノート
- phase 4-6A作業時の一時退避用PDFメモもある。
  - ファイル名：`phase4-6A_batch_earliest_arrival_timestep_memo.pdf`
  - 保存場所：UXsimリポジトリ外（Macデスクトップ）
  - 位置づけ：チャット上限到達時の一時退避用。リポジトリ内の正式記録ではない。
  - **以後の作業再開時は、本正式メモおよび [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を優先して参照する。**
- 本正式メモは、PDFメモを背景資料としつつ、その後の議論で更新・修正された**最新版仕様**をまとめる。
- **PDFメモの完全再現が目的ではない。** 実装開始・次チャット引き継ぎに必要な仕様をまとめる。
- 元論文BATCHの忠実再現ではなく、UXsimのリンク流出入制約・アウトリンク容量制約・ノード容量制約・実際のtransfer可否を考慮する **UXsim-adapted BATCH** を対象とする。
- 既存FCFS / clearance実装を壊さずに拡張することを重視する。
- PDFメモに含まれていたBATCH以外の重要考察、特に **Time-value Transaction**、**リスク込みVOT**、**仮想通過時刻の利用可能性** も本メモに残す。

---

## 2. 元論文BATCHとの関係

- 元論文のSlot-based Intersectionでは、車両がIntersection Managerへaccess requestを出し、そのrequestには **earliest arrival time** が付随する。
- 補足資料では、requestは概念的に `{V, at_V, X_V}` と表され、`at_V` は vehicle V の earliest arrival time に対応する。
- **FAIR** は個別車両をFCFS的に処理する。
- **BATCH** は、遅延車両が生じたとき、その遅延幅に応じて後続リクエストをまとめ、同一flow/laneの車両をまとめて処理する。
- 元論文では、車両は割当access timeに合わせて速度調整することが前提である。
- UXsimでは、このような厳密なslot-following速度制御は標準では行わず、リンク上の車両移動、前方車両、容量制約、アウトリンク閉塞、ノードtransfer可否に従う。
- したがって、本研究では元論文のBATCH思想を参考にしつつ、UXsim内部の交通流モデルに適応したBATCHを実装する。
- 本実装は、元論文BATCHの理論モデルそのものではなく、**UXsim-adapted BATCH / FCFS-with-BATCH** である。

---

## 3. BATCHの基本思想

- **FCFS** は、車両1台を1つの処理単位として扱う。
- **BATCH** は、同一inlink方向の複数車両を1つの処理単位として扱う。
- ここでいう方向は地理的な東西南北ではなく、UXsim上の **inlink ID** または **approach ID** を意味する。
- 1つのbatch内には複数方向の車両を混ぜない。
- batchは、形成後は1つの大きな車両のようにFCFS的に処理される。
- BATCHの狙いは、FCFS(clearance=1)で発生しやすい高頻度方向切替を抑え、同一inlink方向の車両をまとめて処理することでclearanceロスを減らすことである。
- ただし、BATCHは厳密な1台単位の到着順をある程度緩めるため、**公平性・待ち時間分散とのトレードオフ**がある。

---

## 4. 前提条件

### 初期実装の前提

- 単車線。
- 右左折あり。ただしtrajectory compatibility matrixは使わない。
- 1タイムステップ中に交差点へ進入できるのは1方向のみ。
- batchは同一inlink方向の車両のみで構成する。
- `deltan=1`。
- 1 vehicle = 1 unit。
- T2 / clearance は外部入力または既存clearance設定に対応させる。
- 最大batchサイズ **N** は外部入力パラメータとする。
- T1は実通過処理と仮想サービス計算で役割を分けて考える。

### T1について

- **実通過処理**では、同一inlink連続通過の間隔はUXsim標準transfer条件・リンク流出容量・アウトリンク流入容量等に従う。
- したがって、初期実装では実通過処理にT1を明示的なsleepとして入れるとは限らない。
- 一方、**仮想サービス計算**では、同一inlink連続処理の間隔としてT1を使う可能性がある。
- 初期案では、仮想計算用T1は1 timestepまたは`W.DELTAT`相当として扱う候補があるが、実装時に確認する。

---

## 5. 時刻管理

BATCH実装では、制御ロジック用の時刻は基本的に **timestep 単位**で統一する。

ただし、これは既存の秒単位保存値をそのままtimestepとして扱うことを意味しない。保存形式は秒単位の属性があり、BATCH計算時にはtimestepへ明示的に変換する。

### 理由

- 現行UXsimでは `vehicle.departure_time` や `vehicle.arrival_time` は timestep 表記である。
- FCFS clearance実装も、`last_order_control_entry_timestep` や `order_control_clearance_timesteps` に基づく timestep ベースで処理している。
- 秒単位の保存値とtimestep単位の計算値を混同すると、BATCH候補判定やclearance判定が混乱する。

### Node到着時刻の保存と変換

現在実装されている `order_control_node_arrival_times[node.name]` の記録値は**秒単位**である。`record_order_control_node_first_arrival(node)` 呼び出し時に `W.T * W.DELTAT` で記録される。

BATCH制御ロジックでは、この値を `W.DELTAT` で割り、`int(round(...))` によって `arrival_timestep` へ変換して使用する。

```
arrival_timestep = int(
    round(
        order_control_node_arrival_times[node.name]
        / W.DELTAT
    )
)
```

### 主要時刻

| 名称 | 単位 | 用途 |
|------|------|------|
| `earliest_arrival_timestep` | timestep | BATCH候補包含および `t_trigger` 下限 |
| `order_control_node_arrival_times[node.name]` | 秒 | 対象Nodeへの初回到着時刻の保存値（`W.T * W.DELTAT`） |
| `arrival_timestep` | timestep | 上記保存値を変換したBATCH計算用のNode到着時刻 |
| `actual_pass_timestep` | timestep | 実通過時刻を将来記録する際の制御単位（**未実装**） |
| `t_trigger` | timestep | trigger vehicleの予定通過タイムステップ |
| `first_transfer_timestep` | timestep | Node到着後最初のtransfer対象timestep（`arrival_timestep + 1`） |

秒表示が必要な場合は、`timestep * W.DELTAT` で秒に変換する。

---

## 6. earliest_arrival_timestep

- `earliest_arrival_timestep` は、元論文の earliest arrival time / `at_V` に対応する。
- `earliest_arrival_timestep` は **BATCH形成の中核データ**である。
- 車両が当該Nodeへ向かうリンクへ進入した時点で付与する。
- これは「自由流・単独・最短条件であれば、このtimestep以降に当該Nodeへ到着可能である」という**下限値**である。
- UXsim上の実際のノード端到着（`order_control_node_arrival_times[node.name]`、秒単位）とは異なる。
- 実混雑・前方車両・アウトリンク閉塞・ノード容量制約により、実際のノード端到着が `earliest_arrival_timestep` より遅れることはあり得る。
- それでもBATCH候補判定では、実到着予測ではなく **`earliest_arrival_timestep`** を用いる。

### phase 4-6Aで実装済み

- Vehicle属性：`order_control_earliest_arrival_timesteps`（dict、key=`node.name`、value=int timestep）
- メソッド：`record_order_control_earliest_arrival_timestep_for_current_link()`
- World設定：`order_control_batch_tau_timesteps`（初期値1）、`set_order_control_batch_tau_timesteps()`
- テスト：`tests_order_control_batch_earliest_arrival_timestep.py`
- コミット：94b05f2

### 計算式（実装済み）

```
free_flow_travel_timesteps = ceil((link.length / link.u) / W.DELTAT)

link_entry_timestep = int(round(veh.link_arrival_time / W.DELTAT))

earliest_arrival_timestep =
    link_entry_timestep
    + free_flow_travel_timesteps
    + tau_timesteps
```

ここで：

- `link.u` はUXsimの `free_flow_speed`。
- `W.DELTAT` は1 timestepあたりの秒数。
- `tau_timesteps` は `W.order_control_batch_tau_timesteps`（初期値1）。
- `veh.link_arrival_time` は現在リンクへの進入時刻（**単位は秒**）。
- `ceil` を使うのは、自由流でも到達できない早すぎるtimestepを earliest arrival として扱わないため。
- `link_entry_timestep` は `int(round(...))` で復元する（浮動小数誤差回避）。

---

## 7. arrival_time_to_node と actual_pass_time

### arrival_time_to_node

- 車両が現在リンクの終端、つまり `link.end_node` 側に到着し、Node処理候補になる時刻を指す**概念名**。
- UXsimコード上は、`vehicle.x == vehicle.link.length` となり、`node.incoming_vehicles` に追加されるタイミングに対応する。
- 既存order-control改変では `record_order_control_node_first_arrival(node)` が呼ばれる。
- このメソッドはUXsim標準ではなく、order-control / FCFS改変で追加された補助機能と理解する。
- 実装上の保存値は `order_control_node_arrival_times[node.name]` で、**単位は秒**（`W.T * W.DELTAT`）。
- BATCH制御計算では、この保存値から `arrival_timestep` へ変換して使用する（§5参照）。

### actual_pass_time / actual_pass_timestep

- UXsimのtransfer条件を満たし、実際にinlinkからoutlinkへ移った時刻。
- outlink容量、inlink流出容量、node流量容量、アウトリンク空間、信号またはorder-control条件などを満たす必要がある。
- 将来、制御ロジック用に `actual_pass_timestep`（timestep単位）として記録する想定であるが、**現時点では正式な記録属性として未実装**。

### 重要

- `arrival_time_to_node` と `actual_pass_time` は**明確に区別**する。
- リンク端に到着していても、容量制約やアウトリンク閉塞で実通過できないことがある。

---

## 8. service unit と unresolved の用語

### service unit

- Nodeが処理順序上の1単位として扱う対象を意味する**仮称**である。
- 単独vehicle、1台batch、複数台batch、residual batchを含む。
- 実装時の正式な変数名はUXsim側の構造に合わせて決めてよい。

### unresolved

- 仮想サービス計算上、その時点では通過時刻を確定できないvehicleまたはbatchを指す。
- 典型例は、アウトリンク閉塞、容量制約、前方同一inlink車両のブロックなどにより、現在情報だけではいつ通れるか決められない場合である。
- unresolvedは主にLevel 2以降の仮想サービス計算に関係する概念であり、**初期実装では必要最小限でよい**。

---

## 9. trigger vehicle と t_trigger

- BATCH形成のきっかけは、**未batch車両がリンク端に到着すること**である。
- その車両を **trigger vehicle** と呼ぶ。
- trigger vehicleはすでにノード端に到着している。
- trigger vehicleの予定通過タイムステップを **`t_trigger`** とする。
- BATCH候補判定は **`earliest_arrival_timestep <= t_trigger`** によって行う。
- `t_trigger` をどう推定するかが、BATCH形成範囲を左右する。

**Level 0 / 1 / 2 は候補判定の違いではなく、`t_trigger` 推定方法の違い**である。

### Level 0 / 1 / 2 の位置づけ（確定）

| Level | 位置づけ | 状態 |
|-------|----------|------|
| **Level 2** | 研究上の通常推定方式として最終的に使用する予定。形成済みservice unitやbatchを仮想的に処理し、現在観測可能な容量・閉塞状態を考慮する。将来いつoutlinkが空くかを完全予測するものではない。unresolvedが発生する可能性がある。 | **未実装** |
| **Level 1** | Level 2でunresolvedとなり有効なt_triggerを決定できない場合のfallback。既存clearance状態を考慮。必要入力が整っていれば必ず計算できる。不整合時はValueError（Level 0へ自動fallbackしない）。 | **実装済み**（phase 4-6D、d79db61） |
| **Level 0** | 最小基準・比較・単体検証・デバッグ用。Level 1のfallbackとは位置づけない。 | **実装済み**（phase 4-6D、d79db61） |

### phase 4-6Cで実装済み：trigger候補識別

- `Node.get_order_control_batch_trigger_candidates()`（参照専用）
- BATCH対象Nodeの `incoming_vehicles` から未batch Vehicleを抽出し、`(arrival_time, tiebreaker, veh.id)` でsorted新listを返す
- 非BATCH Nodeでは `[]`。新しい乱数は生成しない。副作用なし
- 候補listの各Vehicleはすでに対象Nodeの `incoming_vehicles` に入っており、Node端へ到着済みである
- BATCH形成処理を実行する時点では、返却listの先頭Vehicleを現在のBATCH形成を起動するtrigger vehicleとして使用する想定である
- ただし phase 4-6C の現段階では、trigger vehicleの確定・保存およびBATCH形成処理には未接続である
- コミット：40d5ad7

### phase 4-6Dで実装済み：t_trigger推定（Level 0 / Level 1）

**共通前提**

- `t_trigger` の単位はtimestep
- 計算式に **`W.T` は含めない**（後の時刻で再計算しても現在時刻だけでt_triggerが後ろへ動かない）
- 推定結果はNode/Vehicleへ保存しない。参照専用

**Node到着時刻の変換**

```
arrival_timestep = int(round(
    trigger_vehicle.order_control_node_arrival_times[node.name] / W.DELTAT
))
first_transfer_timestep = arrival_timestep + 1
```

（incoming_vehiclesへ登録されるタイムステップの `Node.transfer()` は既に終了しているため、到着timestepそのものではなく次timestepからが最初のtransfer対象）

**Level 0**

```
trigger_earliest_arrival_timestep =
    trigger_vehicle.order_control_earliest_arrival_timesteps[node.name]

t_trigger = max(first_transfer_timestep, trigger_earliest_arrival_timestep)
```

- clearance、容量、service queueは考慮しない

**Level 1**

```
base_trigger_timestep = max(first_transfer_timestep, trigger_earliest_arrival_timestep)
```

- `last_order_control_inlink is None` → `t_trigger = base_trigger_timestep`
- `trigger_vehicle.link == last_order_control_inlink` → `t_trigger = base_trigger_timestep`
- 異inlink → `clearance_satisfied = last_entry + clearance + 1`、`t_trigger = max(base, clearance_satisfied)`
- `last_order_control_inlink` があるのに `last_order_control_entry_timestep is None` → ValueError
- テスト：`tests_order_control_batch_t_trigger_estimation.py`（21テスト関数）

### 旧表（参考、Level 2未実装部分は上記に統合）

| Level | 内容 |
|-------|------|
| **Level 0** | trigger vehicleの到着情報とearliest下限から簡易推定。（**実装済み**） |
| **Level 1** | 直近通過inlinkとtrigger inlinkの関係・clearanceを反映。（**実装済み**） |
| **Level 2** | service unit仮想処理・容量制約反映。unresolved時はLevel 1へfallback。（**未実装**） |

---

## 10. BATCH候補集合

候補集合は、**ノード端に到着済みの車両だけに限定しない**。

### 候補集合

- 当該Nodeへ向かう**全インリンク上の未batch車両**。
- 各車両にはリンク進入時点で `earliest_arrival_timestep` が付与されている（phase 4-6Aで実装済み）。
- `earliest_arrival_timestep <= t_trigger` を満たす車両を候補に含める（**未実装**。次フェーズ4-6E候補）。

### 候補Vehicleの状態条件（設計確定）

- 対象状態は **`veh.state == "run"`** とする。
- **`veh.v > 0` は条件にしない**。渋滞等により `veh.v == 0` のVehicleも候補になり得る。

### 同一inlink内FIFO（設計確定）

- 単車線を前提とする。
- `inlink.vehicles` の物理的FIFO順を維持する。
- earliest arrivalや乱数で同一inlink内を並べ替えない。
- 後続Vehicleが先行Vehicleを追い越さない。

### Node別batch assignmentの判定（phase 4-6Bで実装済み）

- `order_control_batch_assignments` はNode別dict（key=`node.name`、value=`batch_id`）。
- 候補除外は **`node.name in veh.order_control_batch_assignments`** で行う。
- 別Nodeでのみbatch化済み（例：`assignments["other_node"]=0`）の場合、対象Nodeでは未batchとして扱う。
- 辞書全体が空かどうか、または `len(assignments)>0` だけでVehicle全体を除外してはいけない。

### 重要

- **`predicted_arrival_time` は使わない。**
- batch形成時点で未到着の車両を含み得る。
- 未到着車両について、実際に到着しそうな時刻や `predicted_arrival_time` を候補判定に使うと、trigger時刻より後になるのが自然であるため、BATCH候補から外れてしまう。
- したがって、BATCH候補判定では `predicted_arrival_time` ではなく、リンク進入時に付与された **`earliest_arrival_timestep`** と **`t_trigger`** を比較する。
- 一度batch化された車両は、**再び候補集合に入らない**。

---

## 11. 同時到着時のtrigger順序

- 同一timestepに複数の未batch車両がリンク端に到着する可能性がある。
- その場合、既存FCFS改変と同様に、**`order_control_node_arrival_times[node.name]`（秒）、tiebreaker、`veh.id`** 等で先着順を決める。
- 先着扱いとなった車両をtrigger vehicleとして通常のBATCH形成処理を行う。

### 例

- A方向車両AとB方向車両Bが同時到着し、tiebreakerによりAが先着扱いとなった場合、Aをtrigger vehicleとする。
- このときBはすでに同じtimestepで到着しているため、Bの `earliest_arrival_timestep` はAの `t_trigger` 以下である。
- したがって、BはA-triggerによるcandidate setに含まれる。
- その結果、A方向batchがtrigger方向として先に置かれ、B方向車両はB方向batchとして後続に置かれる。
- **同時到着専用の特別処理は基本的に不要**であり、tiebreakerでtrigger順を決めたうえで通常のbatch形成処理に含めればよい。

---

## 12. inlink方向別batch化

- candidate setには複数inlink方向の車両が含まれ得る。
- candidate setを **inlink方向ごとに分割**する。
- 各batchは**同一inlink方向の車両のみ**で構成する。
- batch内の順序は、そのinlink内のFIFO / request orderを破らない。
- **trigger vehicleを含む方向のbatchを最初に処理**する。
  - これは、trigger vehicleが現在まさに到着してBATCH形成を起動した車両であるため自然な処理順である。
- 他方向batchの順序は、**snapshot estimated arrival**（下記）に基づく。**未実装**。

### snapshot estimated arrival（設計確定・未実装）

Link進入時に固定された `order_control_earliest_arrival_timesteps` とは**別指標**。batch間順序決定専用。

trigger vehicleがNode端へ到着した時点で、各inlink別batchの先頭Vehicleについて：

```
remaining_distance = max(0, inlink.length - head_vehicle.x)

remaining_free_flow_timesteps = ceil(
    (remaining_distance / inlink.u) / W.DELTAT
)

snapshot_estimated_arrival_timestep =
    trigger_arrival_timestep + remaining_free_flow_timesteps
```

その他inlink別batchの処理順キー（昇順）：

```
(snapshot_estimated_arrival_timestep, head_vehicle.id)
```

重要：

- **現在速度 `veh.v` は使用しない**。Linkの自由流速度 `inlink.u` を使用する。
- `order_control_earliest_arrival_timesteps` を上書きしない。
- 新しい乱数tiebreakerは追加しない。同値時は `head_vehicle.id` を最終キーとする。
- **`tau_timesteps` は加えない**（相対接近順序評価のため概念上不要）。
- `inlink.u <= 0` の場合はValueErrorとする予定。

### phase 4-6Bで実装済み：BATCH状態コンテナ

**Vehicle**

- `order_control_batch_assignments = {}`（初期化のみ。assignment書き込みは未実装）

**Node**

- `order_control_batch_service_queue = deque()`（初期化のみ）
- `order_control_batch_next_id = 0`（初期化のみ。増加は未実装）

- テスト：`tests_order_control_batch_state_containers.py`
- コミット：28ed156

---

## 13. Nの定義とN超過時の扱い

### 元論文との差分

- 元論文では、Nは1回のbatchに含める最大request数として扱われる。
- しかし、多方向・複数inlinkのUXsim networkでは、総数上限としてのNは方向数に依存してbatch効果を弱めたり、一方向偏重を招く可能性がある。

### UXsim-adapted BATCHでの定義

- **N = 各inlink方向batchに含める最大車両数。**
- つまり、Nは**方向別batchサイズの上限**である。

### N超過時の扱い

- 同一inlink方向でN台に達したら、その時点で**今回のbatch形成を打ち切る**。
- その後に他方向候補が存在し得る場合でも、**同じbatch形成処理内では追加しない**。
- 同じbatch形成処理内で、N超過分を第2 batchとして後ろへ回すことは**しない**。
- N超過分は**未batchのまま残す**。
- 次に実際にノード端へ到着した未batch車両が、**次回のtrigger vehicle**となる。
- 次回triggerは、元のrequest順だけではなく、**UXsim上の実到着順**に依存する。
- これはUXsim-adapted BATCHとして自然である。

### 例

- 候補列から同一方向Nが15台、Eが5台相当含まれる場合、N=10ならまずN10台で打ち切る。
- 残ったN5台とE5台は未batchのまま残る。
- 次回batch形成は、残り未batch車両のうち**実際に次に到着した車両**がtriggerとなる。

---

## 14. batch化後の処理

- 一度batch化された車両群は**固定**される。
- batchは、あたかも1台の大きな車両のようにFCFS的に処理される。
- batch内順序は**固定**される。
- 未到着車両がbatch内にいる場合でも、**順序を変更しない**。
- **未到着なら待つ。**
- 未到着を理由に別方向車両を先に処理すると、それはBATCHではなく逐次FCFSに戻ってしまう。
- この「未到着なら待つ」は**BATCHの本質**である。

---

## 15. residual batch

- **未到着**と**容量制約による通過不能**は区別する。
- 未到着の場合は、batchの番を維持して到着を待つ。
- 容量制約・アウトリンク閉塞・node容量不足等により、batch途中車両が一時的に通過不可になった場合、未通過部分を **residual batch** として扱う。
- residual batchは元batch内の未通過部分であり、**内部順序を維持**する。
- residual batchは一時的に後ろへ回す。
- 既存FCFSでは、容量制約等で通過できないvehicleがあっても、clearance未充足とは区別しながら後続候補を処理する構造を採っていた。
- BATCHでも、未到着待ちと容量制約による一時的通過不可を区別し、容量制約等の場合にはresidual batchとして後回しにする。
- 具体的な後回し処理は、既存FCFSのcontinue/break方針を参考にして実装時に決める。
- 将来到着する新規batchに無制限に抜かされないようにするため、**residual batchの挿入位置管理**は実装時の重要課題として残す。

---

## 16. UXsimコードとの対応関係

### 確認済み事項

- `link.u` は `free_flow_speed`。
- 車両はまず `x_next = x + link.u * W.DELTAT` で自由流速度走行を試みる。
- `leader` がいる場合、`x_cong = leader.x - link.delta_per_lane * W.DELTAN` により進行位置が制限される。
- 極度な渋滞では `x_next` がほとんど進まず、停車相当になり得る。
- `num_vehicles_queue` は `veh.v < link.u` の車両数に基づく。
- `vehicle.x == vehicle.link.length` になると `link.end_node` 側に到着し、`node.incoming_vehicles` に追加される。
- `record_order_control_node_first_arrival(node)` はこの時点で呼ばれるorder-control改変由来の補助機能。
- 実通過には、outlink容量、inlink流出容量、node流量容量、outlink空間、signal/order-control条件が必要。
- `veh.link_arrival_time` は現在リンクへの進入時刻として使われており、**単位は秒**。

---

## 17. 車両状態・不変条件

名称は実装時に適切に決めてよいが、以下の論理条件を守る必要がある。

- 各車両は、少なくとも「**未batch**」「**batch化済みまたは単独処理単位化済み**」「**通過済み**」のいずれかの状態を持つ。
- 未batch車両がリンク端に到着してtriggerになった場合、そのタイムステップで**必ず**batchまたは単独処理単位に組み込まれる。
- 複数台batchにならない場合でも、単独vehicleまたは1台batchとして扱われる。
- 一度batch化・単独処理単位化された車両は、**再びbatch候補に入らない**。
- batch内の車両順序は**固定**される。
- residual batch内の車両順序も**固定**される。
- `actual_pass_time` / `actual_pass_timestep` は実通過時に**一度だけ**記録する想定（**未実装**）。

---

## 18. 初期実装でやること

### 実装済み（phase 4-6A〜4-6D）

1. Vehicle側にBATCH用の `earliest_arrival_timestep` を付与する。（**phase 4-6A**）
2. World/Node側にBATCH用状態コンテナを初期化する。（**phase 4-6B**）
3. BATCH trigger候補Vehicleを決定的順序で返す参照専用ヘルパーを追加する。（**phase 4-6C**）
4. `t_trigger` をLevel 0 / Level 1で推定する参照専用ヘルパーを追加する。（**phase 4-6D**）
5. 既存FCFS / clearance処理を壊さないことを回帰テストで確認済み。

### 未実装（次フェーズ以降）

1. 未batch車両がリンク端に到着したらtrigger vehicleとする（trigger確定・保存）。
2. 同時到着時は既存FCFSと同様にtiebreaker等でtrigger順を決める。
3. `earliest_arrival_timestep <= t_trigger` を満たす未batch車両を全inlinkからFIFO維持で候補化する。（**phase 4-6E候補**）
4. 候補をinlink方向別に分ける。
5. 各方向で最大N台までbatch化する。
6. Nに達したら今回のbatch形成を打ち切る。
7. 他方向batchをsnapshot estimated arrivalで並べ、trigger方向を先頭にする。
8. batch_id発行、`order_control_batch_assignments` への記録、service queueへの追加。
9. batch化済み車両を再候補にしない。
10. batch内順序を固定する。未到着なら待つ。
11. residual batchとして扱う方針を実装する。
12. `order_control_type="batch"` で `Node.transfer` から分岐する。
13. Level 2仮想サービス計算とLevel 2→Level 1 fallback。

---

## 18A. 目的地Vehicle・trip-end（当面の前提と将来課題）

### 現行UXsimのtrip-end経路

- `single_trip` Vehicleで `link.end_node == dest` の場合、通常のinter-link transfer requestとは異なるtrip-end処理を取る。
- 概念的には：`flag_waiting_for_trip_end` を設定し、inlink先頭になった時点で `end_trip()` する。
- `route_next_link` を持つ通常transferとして `Node.transfer()` へ入らない。

### BATCHへの影響

- 現在のBATCH service unitへ目的地Vehicleを含めるには追加設計が必要。
- 将来検討例：trip-end Vehicleのservice unit化、route_next_linkありVehicleとの共通処理、batch途中でのend_trip、residual batchとtrip-endの関係、`Node.transfer()` と `Vehicle.end_trip()` の役割分担、trip-end Vehicleがtriggerになる場合の扱い。

### 当面の研究シナリオ前提（実装ではなくシナリオ設計）

- **OD需要は原則ネットワーク端点間に設定し、比較対象内部交差点NodeをVehicleの目的地として使用しない。**
- 標準UXsim、FCFS、BATCH、Time-value Transactionの比較では、ネットワークとOD需要を同一にする。
- この前提はBATCHだけに有利/不利な条件を置くためではなく、**全比較方式で同一条件を維持するため**である。

### 保留した実装（将来課題）

当初検討したが、現時点では実装しない：

- `validate_order_control_destination_assumptions()` 等の目的地前提自動検証
- Node属性 `order_control_comparison_target`
- Worldメソッド `set_order_control_comparison_targets(...)` / `clear_...` / `get_...`
- `finalize_scenario()` または `exec_simulation()` への自動検証接続
- trip-end service unit

理由：比較Node選択方式がランダム選択以外は未実装であり、比較対象Node管理の共通層を今作ると過剰設計の可能性。当面は端点間ODでシナリオ側から回避可能。

### 将来の比較対象Node管理案（設計メモ）

3概念の分離：

| 概念 | 意味 |
|------|------|
| `order_control_eligible` | ネットワーク構造上、order controlを適用可能か |
| `order_control_comparison_target` | 今回の実験で比較対象として選ばれたか（**未実装**） |
| `order_control_type` | そのケースで none / fcfs / batch / time_value のどれを適用するか |

将来想定される比較Node選択方式：全eligible、ランダム選択、交通量ベース、渋滞指標ベース、中心性ベース、地理的範囲、一定間隔・配置条件、手動指定、外部ファイル、複数条件の組合せ。

将来作業候補：

- A. 比較対象Node集合の独立管理
- B. 比較対象Node選択方式の共通インターフェース
- C. 比較対象Node集合確定後のdest重複検証
- D. taxi mode（`dest` / `dest_list` 動的変化）向け別検証
- E. trip-end service unit（比較対象Nodeを目的地として許容する場合）

---

## 19. 初期実装でやらないこと / 後続実装

初期実装で後回しにする候補：

- 完全なLevel 2仮想容量コピー。
- compatibility network / trajectory compatibility matrix。
- 複数方向の同時進入。
- time-value transaction 本体。
- 支払い処理。
- 最適signal offsetや信号最適化。
- 元論文BATCHの完全再現。

ただし、**Level 2仮想サービス計算**や**time-value transaction**への接続は、将来実装で重要である。

---

## 20. Time-value Transaction への接続

BATCH制御そのものは時間価値取引ではない。しかし、BATCHで導入する仮想通過時刻・service order・residual/unresolved管理は、将来のTime-value Transactionの基盤になり得る。

### 基本方針

- Time-value Transactionでは、**現在の順序ならいつ通るか**、**順序変更後ならいつ通るか**を比較する必要がある。
- そのため、**仮想サービス時刻**が重要になる。

### リスク込みVOT

- VOTは、確実な時間短縮1単位の価値ではなく、**不確実な時間短縮機会を得る権利**、または**不確実な追加待ち時間を受け入れることに対するリスク込みの単位時間評価額**として扱う可能性が高い。
- **急いでいる側**は、想定ほど短縮されないリスクと、想定以上に短縮される可能性を織り込む。
- **譲る側**は、想定以上に待つリスクと、想定以下で済む可能性を織り込む。

### 仮想通過時刻

- 仮想通過時刻は完全な将来予測である必要はない。
- 現在観測可能な待ち行列状態・ブロック状態を反映した近似でも、制度設計上は一定の合理性を持ち得る。

### シミュレーション評価

シミュレーションでは、以下を比較することで、予測誤差・リスク・受容可能性を評価できる。

- 取引時に期待された短縮時間
- 想定された追加待ち時間
- 実際に得られた短縮時間
- 実際に発生した追加待ち時間

この観点は、今後の **Time-value Transaction設計メモ** へ引き継ぐ。

---

## 21. テスト方針

### 実装済みテスト（phase 4-6A〜4-6D）

- `tests_order_control_batch_earliest_arrival_timestep.py`（phase 4-6A）
- `tests_order_control_batch_state_containers.py`（phase 4-6B）
- `tests_order_control_batch_trigger_candidates.py`（phase 4-6C）
- `tests_order_control_batch_t_trigger_estimation.py`（phase 4-6D、21テスト関数）

phase 4-6A〜4-6D各実装後、FCFS/clearance既存テストおよび `tests_order_exchange_baseline.py`、`example_00en_simple.py` はPASS。主要交通結果は既知値と一致（交通挙動変化なし）。

### 今後のテスト候補

- `earliest_arrival_timestep` が期待通り計算されること。
- `link.u` / `W.DELTAT` / `tau_timesteps` の単位変換が正しいこと。
- 未batch車両がtriggerになったとき、候補集合が `earliest_arrival_timestep <= t_trigger` で形成されること。
- 同一timestep同時到着時にtiebreaker等でtrigger順が決まること。
- 同時到着した他方向車両がcandidate setに含まれ、方向別batchとして処理されること。
- 同一inlink方向ごとにbatchが形成されること。
- Nに達したら今回のbatch形成を打ち切ること。
- N超過分が未batchとして残ること。
- 次回triggerが、残り未batch車両のうち実際に次に到着した車両になること。
- batch化済み車両が再候補にならないこと。
- batch内未到着車両がいる場合に順序を維持して待つこと。
- 容量制約等でbatch途中車両が一時的に通過不可になった場合にresidual batchになること。
- N=1の場合にFCFS系挙動と比較できること。
- `clearance_timesteps=1` でFCFSより方向切替回数が減る可能性を確認すること。

---

## 22. 未解決事項

### 解決済み（phase 4-6A〜4-6D）

- `earliest_arrival_timestep` を既存属性で持つか → **Vehicle.order_control_earliest_arrival_timesteps として実装済み**
- `tau_timesteps` のWorld設定 → **order_control_batch_tau_timesteps、setter実装済み（初期値1）**
- t_trigger Level 0 / Level 1推定 → **phase 4-6Dで実装済み**
- trigger候補の決定順 → **get_order_control_batch_trigger_candidates() で実装済み**
- Node別batch assignmentの意味 → **order_control_batch_assignments、phase 4-6Bで実装済み（初期化のみ）**

### 未解決・将来課題

- `tau_timesteps` を常に1でよいか（研究比較で可変にするか）。
- Level 2仮想サービス計算をいつ導入するか。
- Level 2 unresolved時のLevel 1 fallback接続をいつ実装するか。
- 全inlinkからのBATCH候補抽出（phase 4-6E）。
- snapshot estimated arrivalの実装タイミング。
- residual batchの挿入位置管理をどう実装するか。
- batch内部構造の具体的データ形式。
- service unitの具体的データ形式。
- `order_control_type` 名を `"batch"` にするか、別名にするか（現状 `"batch"` を使用）。
- debug/log出力の粒度。
- 比較対象Node共通管理、目的地自動検証、trip-end service unit。
- Time-value Transactionとどの段階で接続するか。
- taxi mode向け動的dest検証。

---

## 23. 新しいチャットで再開する場合

新しいチャットで再開する場合は、まず以下を読むこと。

### 必読メモ

- [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md)
- [ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md)
- [ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md)

### 確認すべきuxsim.py箇所

- `Vehicle.update`
- `Vehicle.carfollow`
- `Node.transfer`
- `transfer_fcfs_clearance`
- `transfer_fcfs_no_clearance`
- `record_order_control_node_first_arrival`
- `record_order_control_earliest_arrival_timestep_for_current_link`（phase 4-6A）
- `get_order_control_batch_trigger_candidates`（phase 4-6C）
- `estimate_order_control_batch_t_trigger_level_0` / `_level_1`（phase 4-6D）
- `Link.__init__`
- `Link.update` / `in_out_flow_constraint` 周辺

### BATCH関連テスト（phase 4-6A〜4-6D）

- `tests_order_control_batch_earliest_arrival_timestep.py`
- `tests_order_control_batch_state_containers.py`
- `tests_order_control_batch_trigger_candidates.py`
- `tests_order_control_batch_t_trigger_estimation.py`

### FCFS / clearance基本テスト

- `tests_fcfs_order_control_clearance_0.py`
- `tests_fcfs_order_control_clearance_1.py`
- `tests_fcfs_order_control_clearance_xyz.py`
- `tests_order_control_clearance_settings.py`
- `tests_fcfs_order_control_transfer.py`
- `tests_fcfs_order_control_behavior.py`
- `tests_fcfs_order_control_tiebreaker.py`
- `tests_order_control_node_arrival_times.py`
- `tests_vehicle_research_attributes.py`

### sanity check系

- `tests_order_control_fcfs_vs_uxsim_standard_medium_network.py`
- `tests_order_control_fcfs_vs_uxsim_standard_grid_network.py`
- `tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_network.py`
- `tests_order_control_fcfs_vs_signalized_uxsim_standard_grid_high_demand.py`
- `tests_order_control_fcfs_clearance_one_vs_signalized_uxsim_all_red_grid_high_demand.py`

### baseline / example

- `tests_order_exchange_baseline.py`
- `demos_and_examples/example_00en_simple.py`

### 再開時に確認すること

- 現在ブランチ。
- `git status`。
- `git log --oneline -20`。
- **phase 4-6A〜4-6Dまで実装・コミット済み**（最新実装コミット：d79db61）。
- **BATCH形成本体・`Node.transfer()` batch分岐は未実装**。
- FCFS / clearance までは検証済み。
- 次は **phase 4-6E相当：全inlinkからのBATCH候補抽出（参照専用）** へ進む段階。
- 目的地Vehicleは端点間OD前提で保留。比較対象Node共通管理・自動検証は将来課題。
- 一時退避PDF `phase4-6A_batch_earliest_arrival_timestep_memo.pdf` はリポジトリ外。正式Markdownを優先参照。
