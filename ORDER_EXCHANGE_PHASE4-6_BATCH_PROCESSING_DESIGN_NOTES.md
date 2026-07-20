# ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES

UXsim Order Exchange 改変作業における、phase 4-6：交差点BATCH処理の実装前正式設計メモ。

進捗の詳細は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照してください。FCFS / clearance 実装の詳細は [ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md) を参照してください。

---

## 1A. 実装状況サマリ（phase 4-6A〜4-6K）

進捗の詳細・コミットID・回帰結果は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照。Phase 4-6E〜4-6Jの設計・判断経緯の詳細は **§1C**、Phase 4-6Kの実装記録は **§1D** を参照。

| 区分 | 内容 |
|------|------|
| **実装・テスト・コミット済み** | phase 4-6A：`earliest_arrival_timestep` 記録（94b05f2） |
| | phase 4-6B：BATCH状態コンテナ（28ed156） |
| | phase 4-6C：`get_order_control_batch_trigger_candidates()`（40d5ad7） |
| | phase 4-6D：t_trigger Level 0/1推定（d79db61） |
| | phase 4-6E：`get_order_control_batch_candidates_by_inlink()`（4cdc16f） |
| | phase 4-6F：`get_ordered_order_control_batch_candidates_by_inlink()`（d00cb85） |
| | phase 4-6G：`apply_order_control_batch_max_size()`（c7a80e8） |
| | phase 4-6H：`register_order_control_batch_service_units()`（8cf6dec） |
| | phase 4-6I：`form_order_control_batch()`（d10a6db） |
| | phase 4-6J：`order_control_batch_t_trigger_level` とNode群一括設定（1ae9204） |
| | phase 4-6K正式Markdown記録（9a2f32f：4-6E〜4-6J記録） |
| **実装・テスト完了（未commit）** | phase 4-6K：`serve_order_control_batch_service_queue()`（単体実装、`Node.transfer()`未接続）、`tests_order_control_batch_service_queue_transfer.py`（33テスト） |
| **service unit登録〜実通過まで完成** | trigger候補取得 → t_trigger推定 → 全inlink候補抽出 → 処理順決定 → N適用 → batch ID・assignment・service queue登録 → 統合メソッド → Node設定 → **登録済みservice queueに基づくVehicle実通過（4-6K）** |
| **未実装** | BATCH専用transfer統括、`Node.transfer()` batch分岐 |
| | 新規BATCH形成と実通過の統合（1 timestep内の統括呼出し） |
| | `incoming_vehicles` 全体のtimestep末整理 |
| | Level 2仮想サービス推定、Time-value Transaction |
| | N=1 BATCHとFCFSのシミュレーション全体での完全同一性テスト（`Node.transfer()`接続後） |
| | trip-end VehicleのBATCH service unit対応 |
| **当面の研究シナリオ前提** | 比較対象内部交差点Nodeを目的地としない端点間OD |
| | 全比較方式で同一ネットワーク・同一OD需要 |
| **研究基本設定（明示指定）** | `batch_size=10`、`order_control_batch_t_trigger_level=1` |
| **次フェーズ候補** | BATCH専用transfer統括メソッドの設計・実装 → `Node.transfer()` BATCH分岐接続 → 接続後回帰テスト → N=1 BATCHとFCFS完全同一性テスト |

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

## 1C. Phase 4-6E〜4-6J 実装記録（引き継ぎ用）

本節は、Phase 4-6E〜4-6Jの設計・実装・テスト・判断経緯を、**現在の `uxsim/uxsim.py` とテスト**に一致する形で記録する。別担当者または別AIが本メモとリポジトリのみを読んで次工程を安全に再開できることを目的とする。

**後の実装で変更された判断：** §10・§12・§18・§21の旧記述（「4-6E〜4-6G未実装」「snapshot estimated arrival未実装」「service unit形式TBD」等）は、Phase 4-6E〜4-6J完了時点では **§1Cが正** である。Phase 4-6K（service queue実通過）完了時点では **§1Dが正** である。旧節は設計経緯の参考として残し、実装状況は本節および §1D を優先参照すること。

### 1C.1 対象範囲と現在地点

#### Phaseと実コードの対応

| Phase | メソッド / 属性 | コミット |
|-------|----------------|----------|
| 4-6C（入力元） | `Node.get_order_control_batch_trigger_candidates()` | 40d5ad7 |
| 4-6D（入力元） | `Node.estimate_order_control_batch_t_trigger_level_0()` / `_level_1()` | d79db61 |
| **4-6E** | `Node.get_order_control_batch_candidates_by_inlink(s, t_trigger)` | 4cdc16f |
| **4-6F** | `Node.get_ordered_order_control_batch_candidates_by_inlink(s, candidates_by_inlink, trigger_vehicle)` | d00cb85 |
| **4-6G** | `Node.apply_order_control_batch_max_size(s, ordered_candidates_by_inlink, max_batch_size)` | c7a80e8 |
| **4-6H** | `Node.register_order_control_batch_service_units(s, selected_groups_by_inlink)` | 8cf6dec |
| **4-6I** | `Node.form_order_control_batch(s, t_trigger_level, max_batch_size)` | d10a6db |
| **4-6J** | `node.order_control_batch_t_trigger_level`、`_validate_order_control_batch_t_trigger_level()`、`Node.__init__()`、`World.addNode()`、`World.set_order_control_for_nodes()`、`World.set_order_control_for_randomly_selected_eligible_nodes()` | 1ae9204 |

#### 現在地点（Phase 4-6J完了時点）

- **実装済み：** trigger候補取得 → t_trigger推定（Level 0/1）→ 全inlink候補抽出 → 処理順決定 → 方向別N適用 → batch ID・assignment・service unit正式登録 → 統合メソッド → 既存の `batch_size` 一括設定機能を維持・利用しながら、新しい `order_control_batch_t_trigger_level` 設定を Node別・Node群一括・ランダム選択Node群へ追加。
- **未実装：** service queueに基づくVehicle実通過、通過後Vehicle削除、完了service unit削除、BATCH専用transfer統括、`Node.transfer()` BATCH分岐、Level 2仮想サービス推定、residual batch、Time-value Transaction、FCFSとN=1 BATCHの完全同等性テスト。

#### 研究基本設定（明示指定）

```python
W.set_order_control_for_nodes(
    target_node_names,
    order_control_type="batch",
    batch_size=10,
    transaction_case=None,
    order_control_batch_t_trigger_level=1,
)
```

`batch_size` のNode既定値は **1** のまま維持。研究条件では **10** を明示指定する。

---

### 1C.2 BATCH処理全体のデータフロー（Phase 4-6E〜4-6J）

```
Node端へ到着済みの未batch Vehicleから trigger候補を取得する          [4-6C]
    ↓
trigger候補listの先頭Vehicleをtriggerとして選ぶ                    [4-6I内]
    ↓
Level 0またはLevel 1でt_triggerを推定する                          [4-6D]
    ↓
全inlinkから候補Vehicleを抽出する                                  [4-6E] ★
    ↓
trigger inlinkを先頭にして候補群を順序付けする                      [4-6F] ★
    ↓
方向別最大batchサイズNを適用する                                    [4-6G] ★
    ↓
batch ID、Vehicle assignment、service unitを正式登録する            [4-6H] ★
    ↓
上記を統合メソッドから一続きに実行する                              [4-6I] ★
    ↓
既存のbatch_size設定機構を維持しつつ、                              [4-6J] ★
order_control_batch_t_trigger_levelを
Node別・Node群一括で設定可能にする
```

★印は Phase 4-6E〜4-6J で完成した処理。

**次工程（未実装）：**

- service queueに従うVehicleの実通過
- 通過済みVehicleのservice unitからの削除
- 完了service unitのqueueからの削除
- BATCH専用transfer統括
- `Node.transfer()` へのBATCH分岐
- Level 2の仮想サービス推定
- residual batch
- Time-value Transaction

#### 前段（4-6C・4-6D）との接続

- **4-6C** `get_order_control_batch_trigger_candidates()`：対象Nodeの `incoming_vehicles` から、当該Nodeで未batch assignmentの到着済みVehicleを、到着時刻・タイブレーカー・id順に並べて返す（read-only）。
- **4-6D** `estimate_order_control_batch_t_trigger_level_0/1(trigger_vehicle)`：選ばれたtrigger vehicleに対し `t_trigger`（int timestep）を推定する（read-only）。Level 1は異方向切替時のみclearanceを反映し、それ以外はLevel 0と同値。
- **4-6I** は上記2段を含め、4-6E〜4-6Hを順に呼ぶ。

---

### 1C.3 主要データ構造と用語

#### 1C.3.1 VehicleのNode別batch assignment

**属性：** `vehicle.order_control_batch_assignments`

**形式：**

```python
{
    node_name: batch_id,  # batch_id は非負int
    ...
}
```

- keyはNode名（`str`）、valueは当該Nodeにおけるbatch ID。
- 登録時は辞書全体を置き換えず、**現在Nodeのkeyだけ**を追加する。
- 別Nodeの既存assignmentは維持する。
- 同じNodeでassignment済みのVehicleは再assignmentしない（`ValueError`）。
- 同一Vehicleが同一Nodeを再訪すると既存assignmentが残るため、現key設計では再assignmentは `ValueError` になる。**同一Node再訪への本格対応は未実装。**

#### 1C.3.2 Nodeのservice queue

**属性：** `node.order_control_batch_service_queue`
**型：** `collections.deque`

**service unitの形式：**

```python
{
    "batch_id": batch_id,      # 非負int。queue内位置（queue[0]等）とは無関係
    "inlink": inlink,          # Linkオブジェクト
    "vehicles": list(vehicles), # FIFO順のVehicle list（新しいlist容器）
}
```

- 1方向別batch = 1 service unit。1回の形成結果全体を1件にまとめない。
- 複数方向があれば複数service unitに分ける。
- `list(vehicles)` で新容器を作り、Vehicleオブジェクト自体は複製しない。
- queue末尾へ追加。既存要素の内容・順序は変更しない。
- 同一inlinkのservice unitが複数存在してよい（別形成機会・別batch ID）。

#### 1C.3.3 Node別batch ID

**属性：** `node.order_control_batch_next_id`

- Nodeごとの非負整数。ネットワーク全体で一意である必要はない。
- 方向別batchごとに1 ID。1回の登録で複数方向なら入力順に連番。
- 登録した方向別batch数だけ `next_id` を進める。複数回登録時は更新済み `next_id` から再開。

**queue添字とbatch IDの区別：** `queue[0]`・`queue[1]` の0・1はqueue内位置（Python添字）であり、batch IDではない。

#### 1C.3.4 最大batchサイズ（`node.batch_size` と `max_batch_size`）

| 名称 | 種別 | 意味 |
|------|------|------|
| `node.batch_size` | Node属性（設定値） | Nodeに保存する研究設定。`World.set_order_control_for_nodes()` で一括設定。既定値 **1** |
| `max_batch_size` | メソッド引数 | `form_order_control_batch()` / `apply_order_control_batch_max_size()` の引数名 |

- `order_control_batch_max_size` というNode属性は**存在しない**（当初案は撤回、§1C.12参照）。
- 将来のBATCH専用transferからの呼び出し予定：

```python
s.form_order_control_batch(
    t_trigger_level=s.order_control_batch_t_trigger_level,
    max_batch_size=s.batch_size,
)
```

- **N** は1回の形成で作る**1方向batch**のVehicle数上限。**1 timestepの通過台数上限ではない。**

#### 1C.3.5 t_trigger Level

**属性：** `node.order_control_batch_t_trigger_level`（既定値 **1**、有効値 **0** または **1**）

| Level | 内容 | 実装 |
|-------|------|------|
| **0** | 初回通過可能timestep、trigger vehicleのearliest arrival等の基本下限制約で `t_trigger` 推定 | 実装済み |
| **1** | Level 0の基本値を使用。直前通過inlinkとtrigger inlinkが異なる場合のみclearance状態を考慮。`last_order_control_inlink` が `None`、またはtrigger inlinkが `last_order_control_inlink` と同じ場合はLevel 0相当 | 実装済み |
| **2** | 仮想サービス計算による推定（設計上想定） | **未実装**（設定・形成とも専用 `ValueError`） |

---

### 1C.4 Phase 4-6E：inlink別候補Vehicle抽出

**メソッド：** `Node.get_order_control_batch_candidates_by_inlink(s, t_trigger)`

| 項目 | 内容 |
|------|------|
| 引数 | `t_trigger`：非負 `int`（`bool`不可） |
| 戻り値 | `dict`：`{inlink: [vehicles...]}`。候補がないinlinkはキーに含めない |
| 副作用 | **なし**（read-only） |

**処理概要：**

1. Nodeがorder-control対象かつ `order_control_type == "batch"` であることを検証。
2. 対象Nodeの**全inlink**を走査。
3. 各inlinkについて、物理FIFO順（`inlink.vehicles`）で未assignment Vehicleのうち、`order_control_earliest_arrival_timesteps[s.name] <= t_trigger` を満たす先頭連続部分を候補とする（`earliest > t_trigger` に達したらそのinlinkの走査を打切り）。
4. assignment済みVehicleは候補から除外。assignmentは各inlinkで未assignmentが物理queueの**接頭辞**であることを検証（prefix violationで `ValueError`）。
5. `veh.v` や `route_next_link` は候補フィルタに使わない。

**重要な意味論：**

- triggerは到着済みVehicleだが、同じ形成に入る候補は**未到着でも** `earliest_arrival_timestep <= t_trigger` なら含まれ得る。
- Node端へ未到着でも、t_triggerまでに到着可能と評価されれば候補に含まれる。

**戻り値例：**

```python
{link_a: [A1, A2], link_b: [B1]}
```

**主な `ValueError` 条件：** 非eligible / 非batch Node、不正 `t_trigger`、inlinkの `end_node` 不一致、`veh.link` 不一致、非 `run` state、earliest未記録・不正・非単調減少、assignment prefix violation。

**テスト：** `tests_order_control_batch_candidates_by_inlink.py`（22テスト）— 全inlink走査、FIFO、未到着候補包含、prefix検証、read-only、副作用なし。

---

### 1C.5 Phase 4-6F：候補群の処理順決定

**メソッド：** `Node.get_ordered_order_control_batch_candidates_by_inlink(s, candidates_by_inlink, trigger_vehicle)`

| 項目 | 内容 |
|------|------|
| 入力 | 4-6Eの `dict`、trigger vehicle |
| 戻り値 | `list` of `(inlink, candidate_list)`。各listは新しい `list(...)` 容器 |
| 副作用 | **なし**（read-only） |

**処理順：**

1. trigger vehicleのinlinkを**常に先頭**。
2. その他inlinkは `snapshot_estimated_arrival_timestep` 昇順、同値時は `head_vehicle.id` 昇順。
3. 各inlink内のFIFO順は維持。trigger vehicleはtrigger inlink候補listの**先頭**である必要がある。

**`snapshot_estimated_arrival_timestep` の計算（実コード）：**

```
trigger_arrival_timestep = round(trigger_vehicle.order_control_node_arrival_times[s.name] / W.DELTAT)
remaining_distance = max(0, inlink.length - head_vehicle.x)
remaining_free_flow_timesteps = ceil((remaining_distance / inlink.u) / W.DELTAT)
snapshot_estimated_arrival_timestep = trigger_arrival_timestep + remaining_free_flow_timesteps
```

- trigger vehicleの**初回到着timestep**を基準とし、他inlinkの先頭Vehicleが自由流速度でNode端へ到達するまでの残りtimestepを加算する。
- 現速度 `veh.v` は使わない（形成時点の位置 `x` とリンク自由流速度 `u` のみ）。

**戻り値例：**

```python
[(link_b, [B1]), (link_a, [A1, A2])]
```

**主な `ValueError` 条件：** 空dict、非Node inlink、候補listが未assignment接頭辞でない、Vehicle重複、trigger不在・非先頭、trigger未着・未記録・既assignment。

**テスト：** `tests_order_control_batch_candidate_group_ordering.py`（24テスト）— trigger inlink先頭、snapshot順、タイブレーク、FIFO整合、入力不変。

---

### 1C.6 Phase 4-6G：方向別最大batchサイズの適用

**メソッド：** `Node.apply_order_control_batch_max_size(s, ordered_candidates_by_inlink, max_batch_size)`

| 項目 | 内容 |
|------|------|
| `max_batch_size` | 方向別batchごとの上限（全方向合計上限ではない） |
| 戻り値 | 新しい外側 `list`、各Vehicle listも新容器。Vehicleオブジェクトは同一 |
| 副作用 | **なし**（read-only） |

**ルール：**

- 入力の方向順を維持。
- 候補数 < N：全Vehicle採用し次方向へ。
- 候補数 ≥ N：FIFO先頭N台採用し**形成処理を終了**（以降の方向は含めない）。

**例（N=2）：**

```
入力: [(link_b, [B1]), (link_a, [A1,A2,A3]), (link_c, [C1])]
出力: [(link_b, [B1]), (link_a, [A1, A2])]
```

**主な `ValueError` 条件：** `max_batch_size` が、boolを除く1以上のintではない場合（`int` ではない、`bool` である、または1未満である場合）、空list、inlink重複、空候補list。

**N=1とFCFS：** 将来FCFS比較条件として使用可能だが、service queue実通過が未実装のため完全なFCFS同等性テストは未実施。

**テスト：** `tests_order_control_batch_max_size_application.py`（12テスト）。

---

### 1C.7 Phase 4-6H：正式batch・service unit登録

**メソッド：** `Node.register_order_control_batch_service_units(s, selected_groups_by_inlink)`

Phase 4-6E〜4-6Hの中で**唯一の正式な状態変更**を行うメソッド。

| 項目 | 内容 |
|------|------|
| 入力 | `[(inlink, vehicles), ...]`（非空） |
| 戻り値 | 正常時 `None` |
| 副作用 | assignment追加、service queue末尾追加、`order_control_batch_next_id` 更新 |

**登録前検証（`planned_service_units` 構築）：** Node eligible・batch、非空list、2要素tuple、非空vehicle list、Node inlink・`end_node` 一致、inlink重複なし、Vehicle重複なし、`veh.link is inlink`、`state=="run"`、当該Node未assignment、`next_id` 非負int、queueが `deque`。

**正式状態変更の順序：**

1. 各Vehicleへ `order_control_batch_assignments[s.name] = batch_id`
2. 各service unitを `order_control_batch_service_queue` 末尾へ追加
3. `order_control_batch_next_id = initial_next_id + len(planned_service_units)`

**ロールバック（例外時）：**

- 今回追加したassignmentのみ `del veh.order_control_batch_assignments[s.name]`
- 今回追加したqueue末尾要素のみ `pop()`
- `order_control_batch_next_id` を `initial_next_id` へ復元
- 元の例外をそのまま `raise`

**テスト修正経緯（`test_append_to_existing_service_queue`）：**

| | 修正前（不自然） | 修正後（正しい連続性） |
|--|------------------|------------------------|
| 既存batch ID | 99 | 0 |
| 登録前 `next_id` | 0 | 1 |
| 新規発行batch ID | — | 1 |
| 登録後 `next_id` | — | 2 |

**テスト：** `tests_order_control_batch_service_unit_registration.py`（18テスト）— batch ID発行、assignment、queue追加、複数回登録、ロールバック、副作用範囲。

---

### 1C.8 Phase 4-6I：BATCH形成統合メソッド

**メソッド：** `Node.form_order_control_batch(s, t_trigger_level, max_batch_size)`

| 項目 | 内容 |
|------|------|
| 呼び出し単位 | 同一Nodeで繰り返し呼ばれる。1回の呼出しで最大1回のBATCH形成（シミュレーション全体で1回ではない） |
| trigger選択 | trigger候補listの先頭Vehicle |
| 戻り値 | `"no_trigger_candidate"`（正常・形成なし）または `"batch_formed"`（登録完了） |

**True/Falseを使わない理由：** `False` は処理失敗と誤解されうる。trigger候補なしは正常結果のため状態説明文字列を採用。

**helper呼出し順序（再実装せず委譲）：**

```
get_order_control_batch_trigger_candidates()
    ↓（空なら "no_trigger_candidate" で return）
estimate_order_control_batch_t_trigger_level_0 または _level_1
    ↓
get_order_control_batch_candidates_by_inlink(t_trigger)
    ↓（空dictは内部不整合 ValueError）
get_ordered_order_control_batch_candidates_by_inlink(...)
    ↓
apply_order_control_batch_max_size(..., max_batch_size)
    ↓（空listは内部不整合 ValueError）
register_order_control_batch_service_units(...)
    ↓
"batch_formed"
```

- Level 2は専用 `ValueError`。統合メソッド側にロールバックは重複実装しない（4-6Hに委譲）。

**テスト修正経緯（`test_uses_existing_helper_methods`）：**

- 初版：`inspect.getsource()` でソース文字列検索 → 改行・括弧・変数名で壊れやすい。
- 最終版：bound methodをテスト内wrapperへ一時置換、`call_order` に記録、wrapperから元メソッドを同引数で実行、`finally` で復元。本番コードにテスト専用分岐なし。

**テスト：** `tests_order_control_batch_formation_integration.py`（14テスト）。

---

### 1C.9 Phase 4-6J：BATCH設定値とNode群への設定

**追加属性：** `node.order_control_batch_t_trigger_level`（既定 **1**）

**モジュールヘルパー：** `_validate_order_control_batch_t_trigger_level(value, node_name=None)` — 0/1のみ有効、2は専用 `ValueError`、`bool` 不可。

**拡張箇所：**

- `Node.__init__(..., order_control_batch_t_trigger_level=1)`
- `World.addNode(..., order_control_batch_t_trigger_level=1)`
- `World.set_order_control_for_nodes(..., order_control_batch_t_trigger_level=1)`
- `World.set_order_control_for_randomly_selected_eligible_nodes(..., order_control_batch_t_trigger_level=1)`

**設計意図：**

- t_trigger推定LevelをNode属性として保持（通常は全対象Nodeへ同値を一括設定、必要時はNode別上書き可）。
- 最大batchサイズは既存 `node.batch_size` を使用。`order_control_batch_max_size` は追加しない。
- 標準Node・FCFS Node・time_value Nodeも属性を持つが、現時点の交通処理では未使用。

**`set_order_control_for_nodes()` の原子性（2パス）：**

1. **検証パス：** `order_control_type`、`batch_size`、`transaction_case`、`t_trigger_level`、全対象Nodeの存在・eligibility
2. **更新パス：** 全検証成功後のみ `order_control_type`、`batch_size`、`transaction_case`、`order_control_batch_t_trigger_level` を一括更新

対象リスト後半に不正Nodeがあっても、前半だけ更新された状態を残さない。

**ランダム選択setter：** Node選択のみ担当。設定適用は `set_order_control_for_nodes()` へ委譲。`random_seed` による選択再現性を維持。

**テスト：** `tests_order_control_batch_node_settings.py`（11テスト）。既存設定テストも最小更新：`tests_node_order_control_attributes.py`、`tests_world_order_control_setters.py`、`tests_random_eligible_order_control.py`、`tests_order_control_eligibility.py`。

---

### 1C.10 原子性・副作用・エラー処理

#### read-onlyメソッド

次のメソッドは、BATCHの候補取得・推定・選択を行うが、Vehicleのbatch assignment、Nodeのservice queue、Nodeのnext batch IDを変更しない。

- `Node.get_order_control_batch_trigger_candidates()`
- `Node.estimate_order_control_batch_t_trigger_level_0()`
- `Node.estimate_order_control_batch_t_trigger_level_1()`
- `Node.get_order_control_batch_candidates_by_inlink()`
- `Node.get_ordered_order_control_batch_candidates_by_inlink()`
- `Node.apply_order_control_batch_max_size()`

#### 状態を変更するメソッド

**`Node.register_order_control_batch_service_units()`**

- Vehicleの `order_control_batch_assignments`、Nodeの `order_control_batch_service_queue`、Nodeの `order_control_batch_next_id` を直接更新する。
- 登録途中に例外が発生した場合のロールバック処理も、このメソッドが担当する。

**`Node.form_order_control_batch()`**

- 最後に `Node.register_order_control_batch_service_units()` を呼び出すため、正常終了すると、Vehicleのbatch assignment、Nodeのservice queue、Nodeのnext batch IDが更新される。
- 実際の登録処理と、登録途中に例外が発生した場合のロールバック処理は、`Node.register_order_control_batch_service_units()` が担当する。

**`World.set_order_control_for_nodes()`**

- 指定されたNodeの `order_control_type`、`batch_size`、`transaction_case`、`order_control_batch_t_trigger_level` を更新する。

**`World.set_order_control_for_randomly_selected_eligible_nodes()`**

- ランダムに選択したNode名を `World.set_order_control_for_nodes()` へ渡す。
- Node設定の実際の更新処理は、`World.set_order_control_for_nodes()` が担当する。

#### エラー・副作用の原則

- 正式登録**前**のhelperで例外 → assignment・queue・`next_id` は未変更。
- 正式登録**中**の例外 → 4-6Hが部分更新をロールバック。
- 統合メソッドは例外を別例外へ置き換えない。
- setterは全検証後に一括更新。不正 `t_trigger_level` を属性へ保存してからエラーにしない。
- BATCH形成・登録は別Nodeのassignmentや状態を変更しない。
- Link順序、Vehicle位置・速度、`World.T` 等は変更しない。

---

### 1C.11 テスト体系と回帰結果

#### BATCH専用テスト（Phase 4-6A〜4-6J）

| ファイル | テスト数 | 主な保証内容 |
|----------|----------|--------------|
| `tests_order_control_batch_earliest_arrival_timestep.py` | 3 | earliest記録（4-6A） |
| `tests_order_control_batch_state_containers.py` | 5 | 状態コンテナ初期化（4-6B） |
| `tests_order_control_batch_trigger_candidates.py` | 9 | trigger候補（4-6C） |
| `tests_order_control_batch_t_trigger_estimation.py` | 21 | Level 0/1推定（4-6D） |
| `tests_order_control_batch_candidates_by_inlink.py` | 22 | 候補抽出・FIFO・read-only（4-6E） |
| `tests_order_control_batch_candidate_group_ordering.py` | 24 | trigger inlink先頭・snapshot順（4-6F） |
| `tests_order_control_batch_max_size_application.py` | 12 | N適用・方向打切り（4-6G） |
| `tests_order_control_batch_service_unit_registration.py` | 18 | 登録・ロールバック（4-6H） |
| `tests_order_control_batch_formation_integration.py` | 14 | helper接続順・戻り値（4-6I） |
| `tests_order_control_batch_node_settings.py` | 11 | t_trigger_level設定・原子性（4-6J） |

#### 設定・eligibility関連

| ファイル | 保証内容 |
|----------|----------|
| `tests_node_order_control_attributes.py` | Node属性初期値・検証 |
| `tests_world_order_control_setters.py` | 一括setter・2パス更新 |
| `tests_random_eligible_order_control.py` | ランダム選択再現性 |
| `tests_order_control_eligibility.py` | eligibility検証 |

#### FCFS・clearance回帰

| ファイル | 保証内容 |
|----------|----------|
| `tests_fcfs_order_control_clearance_0.py` | clearance=0 |
| `tests_fcfs_order_control_clearance_1.py` | clearance=1 |
| `tests_fcfs_order_control_clearance_xyz.py` | X/Y/Z問題 |
| `tests_fcfs_order_control_transfer.py` | FCFS transfer基本 |
| `tests_fcfs_order_control_behavior.py` | FCFS挙動 |
| `tests_fcfs_order_control_tiebreaker.py` | タイブレーカー |
| `tests_order_control_clearance_settings.py` | clearance設定 |
| `tests_order_control_fcfs_vs_uxsim_standard_*.py` 等 | sanity check比較 |

#### 回帰結果（Phase 4-6J完了時点、従来既知値と一致）

**`tests_order_exchange_baseline.py`：**

| 指標 | 値 |
|------|-----|
| completed trips | 48 / 48 |
| average speed | 16.5 m/s |
| total travel time | 2928.0 s |
| average travel time | 61.0 s |
| average delay | 1.0 s |
| delay ratio | 0.017 |
| total distance traveled | 48000.0 m |

**`demos_and_examples/example_00en_simple.py`：**

| 指標 | 値 |
|------|-----|
| completed trips | 735 / 810 |
| average speed | 11.7 m/s |
| total travel time | 119475.0 s |
| average travel time | 162.6 s |
| average delay | 62.6 s |
| delay ratio | 0.385 |
| total distance traveled | 1632250.0 m |

テスト成功に加え、**従来の既知値と一致したため、Phase 4-6E〜4-6Jによる回帰は検出されていない。**

---

### 1C.12 設計判断と途中で修正した論点

#### 1C.12.1 `order_control_batch_max_size` 案の撤回

当初 `order_control_batch_max_size` を新Node属性として追加する案を検討。既存の `node.batch_size` と `World.set_order_control_for_nodes()` 一括設定が存在するため、同義属性の二重管理を避け撤回。**正式設定値は `node.batch_size`。**

#### 1C.12.2 World共通属性案の撤回

World側へ共通BATCH設定属性を新設する案を検討したが、既存setterで `batch_size` 一括設定可能なため新設せず、`t_trigger_level` のみ既存setterへ追加。

#### 1C.12.3 `batch_size` 既定値1の維持

研究基本条件はN=10だが、Node・setterの既定値は1を維持。研究では10を明示指定、N=1は将来FCFS比較に使いやすく、既存API挙動も維持。

#### 1C.12.4 `t_trigger_level` 基本値を1にした理由

Level 1は `last_order_control_inlink` が `None`、またはtrigger inlinkが `last_order_control_inlink` と同じ場合はLevel 0と同値。異方向時のみclearance反映。既存テストで確認済みのため通常設定をLevel 1とした。

#### 1C.12.5 BATCH形成を `Vehicle.update()` にしなかった理由

`Vehicle.update()` はVehicleごとに順次実行される。同一timestep到着のB1・C1がA1.update()時点で未登録の可能性があり、更新順にBATCH結果が依存する危険がある。到着検出は `Vehicle.update()`、形成は次timestepの `Node.transfer()` で前timestepまでの到着が揃った状態で行う責務分離を採用。

#### 1C.12.6 到着timestepと最初の通過判定

`World.exec_simulation()` の順序：`Link.update()` → `Node.generate()` → `Node.update()` → `Node.transfer()` → `Vehicle.carfollow()` → `Vehicle.update()`。`incoming_vehicles` への追加は同timestepの `Vehicle.update()`。最初の通過判定は**次timestepの `Node.transfer()`**。`first_transfer_timestep = arrival_timestep + 1` と一致。

#### 1C.12.7 固定タイブレーカー

同時到着Vehicleが次回trigger候補として比較される場合も、初回Node到着時に保存したタイブレーカーを使用。次回形成時に再付与しない。

#### 1C.12.8 1 timestepあたりのBATCH形成回数

1 Node・1 timestepで新規BATCH形成は最大1回。`form_order_control_batch()` をwhileループで繰り返さない。

#### 1C.12.9 既存service queueがある場合の新規形成

queueが空でなくても未batch到着Vehicleがあれば新BATCHを形成しqueue末尾へ追加。確定済み既存service unitへ後付けしない。同一inlinkのservice unit複数連続を許容。

#### 1C.12.10 True/Falseを統合メソッド戻り値にしなかった理由

trigger候補が存在しないことは正常な結果であり、処理失敗ではない。

Falseを返すと失敗と誤解される可能性があるため、正常状態を明示する文字列 `"no_trigger_candidate"` と `"batch_formed"` を戻り値として採用した。

（実装詳細は §1C.8 も参照。）

---

### 1C.13 現在未実装の範囲（Phase 4-6K完了後）

Phase 4-6K（**§1D**）により、service queueに基づくVehicle実通過・通過後Vehicle削除・完了service unit削除・同一inlink連続service unitの同一timestep内処理・異方向service unitへのclearance適用・residual部分のFIFO保持は**実装済み**である。

**引き続き未実装：**

- BATCH専用transfer統括メソッド
- `Node.transfer()` へのBATCH分岐
- 1 timestep内の新規BATCH形成と実通過の統合呼出し
- `incoming_vehicles` 全体のtimestep末整理
- Level 2仮想サービス推定
- trip-end VehicleのBATCH service unit対応
- Time-value Transaction
- N=1 BATCHとFCFSのシミュレーション全体での完全同一性テスト（`Node.transfer()`接続後）

**注記：** §15の設計段階記述にあった「residual batchを一時的に後ろへ回す」方針は、Phase 4-6K実装では採用していない。未完了service unitは正式queueの最後尾へ移動せず、元の相対順序で残す（**§1D.11**）。

---

### 1C.14 Phase 4-6K（service queueに基づく実通過）— 実装完了

Phase 4-6Kは**実装・テスト・回帰確認完了**（コードは未commit）。詳細は **§1D** を正とする。

#### 確定済み設計（§1C.14で列挙していた項目は §1D で実装済み）

- メソッド名：`serve_order_control_batch_service_queue()`、戻り値：`int`（通過Vehicleオブジェクト数）
- BATCH形成（`form_order_control_batch()`）と実通過を分離
- `Node.transfer()` へは**未接続**（Phase 4-6Kの意図的な範囲外）

#### 旧「今後確認する事項」

§1C.14に列挙していた未確定事項は、Phase 4-6K実装・33テストで確定した。回答は **§1D** 各節を参照。

---

### 1C.15 次回再開時チェックリスト（Phase 4-6K完了後）

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| 最新コミット（Markdown） | `9a2f32f`（Phase 4-6E〜4-6J正式記録） |
| Phase 4-6K実装 | 完了・テスト・回帰確認済み、**未commit** |
| working tree（Markdown更新前） | `uxsim/uxsim.py` 変更、`tests_order_control_batch_service_queue_transfer.py` 未追跡 |
| `Node.transfer()` | BATCH分岐は**未接続** |
| BATCH service queue | 正式登録（4-6H）および実通過（4-6K）まで完成 |
| 研究基本設定 | `batch_size=10`、`order_control_batch_t_trigger_level=1` |
| `batch_size` 既定値 | 1 |
| 次工程 | BATCH専用transfer統括 → `Node.transfer()`接続 → 接続後回帰 → N=1 BATCHとFCFS完全同一性テスト |

**再開時に読むファイル・メソッド・テスト：**

- メモ：本ファイル **§1D**、§1C、[ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md)
- 実装：`serve_order_control_batch_service_queue`、`form_order_control_batch`、`register_order_control_batch_service_units`、`transfer_fcfs_clearance`
- テスト：`tests_order_control_batch_service_queue_transfer.py`（33テスト）、§1D.17一覧

---

### 1C.16 関連コミット・ファイル・テスト一覧

#### コミット（Phase 4-6E〜4-6J）

| SHA | 内容 |
|-----|------|
| `4cdc16f` | inlink別BATCH候補Vehicle抽出（4-6E） |
| `d00cb85` | trigger inlink優先と他inlink候補群の順序付け（4-6F） |
| `c7a80e8` | 方向別最大batchサイズの適用（4-6G） |
| `8cf6dec` | batch ID、Vehicle assignment、service unitの正式登録（4-6H） |
| `d10a6db` | trigger選択から正式登録までの統合（4-6I） |
| `1ae9204` | BATCH t_trigger Levelの一括設定・Node別設定（4-6J） |

#### 主要実装ファイル

- `uxsim/uxsim.py`

#### 主要テストファイル

- `tests_order_control_batch_candidates_by_inlink.py`
- `tests_order_control_batch_candidate_group_ordering.py`
- `tests_order_control_batch_max_size_application.py`
- `tests_order_control_batch_service_unit_registration.py`
- `tests_order_control_batch_formation_integration.py`
- `tests_order_control_batch_node_settings.py`
- `tests_order_control_batch_t_trigger_estimation.py`
- `tests_order_control_batch_trigger_candidates.py`
- `tests_order_control_batch_state_containers.py`
- `tests_order_control_batch_earliest_arrival_timestep.py`
- `tests_node_order_control_attributes.py`
- `tests_world_order_control_setters.py`
- `tests_random_eligible_order_control.py`
- `tests_order_control_eligibility.py`
- FCFS・clearance・baseline：§1C.11参照

---

## 1D. Phase 4-6K：service queueに基づくVehicle実通過

本節は、Phase 4-6E〜4-6J（§1C）で正式登録された `order_control_batch_service_queue` に従い、Vehicleをinlinkからoutlinkへ実際に移動させる **Phase 4-6K** の設計・実装・テスト・判断理由を記録する。別担当者または別AIが本メモとリポジトリのみを読んで次工程を安全に再開できることを目的とする。

**位置づけ：** Phase 4-6Kは §1C の直後工程である。BATCH形成（`form_order_control_batch()`）は行わず、登録済みservice unitのみを処理する。

### 1D.1 対象範囲と現在地点

#### Phaseと実コードの対応

| Phase | メソッド | 状態 |
|-------|----------|------|
| **4-6K** | `Node.serve_order_control_batch_service_queue(s) -> int` | 実装・33テスト・指定既存回帰19本＋example成功。**未commit** |
| 入力（4-6H） | `register_order_control_batch_service_units()` | commit済み（8cf6dec） |
| 参考（FCFS） | `transfer_fcfs_clearance()` | Link間遷移の実装元 |

#### 現在地点（Phase 4-6K完了時点）

- **実装済み：** 登録済みservice queueに基づくVehicle実通過、service unit内FIFO、同一inlink連続service unit処理、未到着待機、clearance判定、下流空間・各容量条件判定、0台通過時の異方向service unit確認、1台以上通過後の停止規則、residual部分の保持、完了service unit削除、未完了service unitの正式queue順維持、FCFSと同じLink間遷移、通過Vehicle数の戻り値、必要最小限の重大不整合検出。
- **意図的に未接続：** `Node.transfer()` からの呼出し。Phase 4-6Kは単体メソッドとして完成させ、シミュレーション本体への統合は次工程とする。
- **引き続き未実装：** BATCH専用transfer統括、新規BATCH形成と実通過の統合、incoming_vehicles全体のtimestep末整理、Level 2、trip-end Vehicle対応、Time-value Transaction、N=1 BATCHとFCFSのシミュレーション全体での完全同一性テスト。

---

### 1D.2 メソッドの責任と戻り値

#### 完全なシグネチャ

```python
def serve_order_control_batch_service_queue(s) -> int:
```

#### 責任分担

| メソッド | 責任 |
|----------|------|
| `Node.form_order_control_batch()` | 新しいBATCHを形成し、Vehicle assignmentとservice unitを正式登録する |
| `Node.serve_order_control_batch_service_queue()` | すでに登録済みのservice unitに従い、Vehicleを実際にLink間で移動させる |

`serve_order_control_batch_service_queue()` は新しいBATCHを形成しない。

#### 戻り値

今回のメソッド呼出しで、実際にinlink→outlinkのLink間遷移を完了した **Vehicleオブジェクト数**（`int`）を返す。

- 0台通過：`return 0`
- 3台通過：`return 3`

**注意：** 戻り値は `W.DELTAN` を掛けた交通量（platoon流量）ではない。Vehicleオブジェクト1台ごとに1を加算する。

正式service queueが空の場合は、状態を変更せず `0` を返す。

---

### 1D.3 service queue、service unit、residual部分の定義

#### 正式service queue

- **属性：** `node.order_control_batch_service_queue`
- **型：** `collections.deque`
- **役割：** 次のtimestepにも引き継ぐservice unitの正式な待ち順。未完了service unitは正式queue内に残る。

#### service unit

```python
{
    "batch_id": batch_id,
    "inlink": inlink,
    "vehicles": [vehicle_1, vehicle_2, ...],
}
```

同じinlink方向に属し、同じbatch IDを持つFIFO順のVehicle列。

#### 完了service unit

`service_unit["vehicles"] == []` となったservice unit。処理終了時に正式service queueから削除する。

#### 未完了service unit

Vehicleが1台以上残っているservice unit。正式service queue内の**元の相対順序**で残す。未完了service unitを正式queueの最後尾へ移動しない。

#### residual部分

service unitから1台以上が通過した後、途中Vehicleが下流空間・各容量条件を満たさず通過不能になった場合に残る未通過Vehicle列。

例：通過前 `[A1, A2, A3]` でA1のみ通過しA2が通過不能のとき、residual部分は `[A2, A3]`。

- residual部分は元のservice unit内にFIFO順で残す
- 別のservice unitとして作り直さない

#### 下流空間・各容量条件

以下をまとめた呼称：

- outlinkへの進入空間（先行Vehicleとの間隔）
- `outlink.capacity_in_remain`
- `inlink.capacity_out_remain`
- `node.flow_capacity_remain`（`flow_capacity` が設定されているNodeのみ）

---

### 1D.4 Vehicleごとの判断順序

各service unitのFIFO先頭Vehicleについて、**必ず次の順**に判断する。これがPhase 4-6Kの中心規則である。

```
1. Node端へ到着済みか（incoming_vehicles に存在するか）
        ↓
2. clearanceを満たすか
        ↓
3. 下流空間・各容量条件を満たすか
        ↓
4. すべて満たすならVehicleを通過させる
```

---

### 1D.5 未到着時の処理

#### 判定

```python
vehicle not in node.incoming_vehicles
```

未到着は内部不整合（`ValueError`）ではない。BATCH形成時（`t_trigger` 時点）には到着可能と評価されたVehicleが、実通過時点ではまだNode端に到着していない場合がある。

#### 未到着時の動作

- Vehicleを通過させない
- service unit内のVehicle順を変更しない
- **後続service unitを確認しない**
- そのtimestepの処理全体を終了する
- それまでに完了したservice unitだけを正式queueから削除する
- 未完了service unitを元の順番で正式queueに残す
- それまでに通過したVehicleオブジェクト数を返す

#### 後続service unitを確認しない理由

未到着Vehicleを飛ばして別方向のservice unitを処理すると、BATCH形成時（4-6H/4-6I）に固定したservice queue順序を崩すため。

---

### 1D.6 clearance判定

#### 使用する既存状態

- `node.last_order_control_inlink`
- `node.last_order_control_entry_timestep`
- `node.order_control_clearance_timesteps`

#### clearance履歴のペア整合性（メソッド入口で1回のみ）

正常状態は次の2種類のみ：

| 状態 | `last_order_control_inlink` | `last_order_control_entry_timestep` |
|------|----------------------------|-------------------------------------|
| 通過履歴なし | `None` | `None` |
| 通過履歴あり | not `None` | not `None` |

片方だけが `None` の場合は `ValueError`。

#### clearance不要

- 過去に通過したVehicleがない（両方 `None`）
- 処理対象inlinkが `last_order_control_inlink` と同じ

#### clearance必要

処理対象inlinkが `last_order_control_inlink` と異なる場合。既存FCFS（`transfer_fcfs_clearance()`）と同じ式：

```python
s.W.T - s.last_order_control_entry_timestep > s.order_control_clearance_timesteps
```

`W.T` と `last_order_control_entry_timestep` はいずれもtimestep番号。`W.DELTAT`（秒）を引かない。

#### clearance未充足時

- Vehicleを通過させない
- 後続service unitを確認しない
- そのtimestepの処理全体を終了する
- 完了済みservice unitだけを正式queueから削除する
- 未完了service unitを元の順番で残す
- それまでの通過Vehicleオブジェクト数を返す

既存FCFSのclearance未充足時の停止（後続候補へ進まない）と同じ考え方。

#### 通過成功後のclearance履歴更新

Vehicleを**実際に通過させた場合のみ**更新：

```python
s.last_order_control_inlink = inlink
s.last_order_control_entry_timestep = s.W.T
```

通過できなかった場合は更新しない。

---

### 1D.7 下流空間・各容量条件を満たさない場合

先頭Vehicleが到着済みでclearanceも満たしているが、下流空間・各容量条件を満たさず通過できない場合。**今回のメソッド呼出しで既に何台通過したか**（`transferred_vehicle_count`）で処理を分ける。

#### 1D.7.1 今回の呼出しで、まだ1台も通過していない場合（`transferred_vehicle_count == 0`）

- 通過不能service unitを正式queue内の**元の位置**に残す（最後尾へ移さない）
- **同じinlinkの後続service unitは確認しない**（単車線では物理的先頭が通過不能なら後方Vehicleは追い越せず必ず通過不能）
- **異なるinlinkの後続service unitを順番に確認する**（まだ1台も通過していないため、過去の最終通過時刻によっては異方向へのclearanceがすでに満たされている可能性がある）

異方向service unitについても、§1D.4と同じ判断順（未到着 → clearance → 下流空間・各容量条件）を適用する。異方向service unitも通過不能で通過Vehicle数が0台のままなら、さらに後方の別inlinkのservice unitを確認できる。

ただし、一度通過不能と判定されたinlinkは `blocked_inlinks` に記録し、そのinlinkの後続service unitは確認しない。

#### 1D.7.2 今回の呼出しで、すでに1台以上通過した場合（`transferred_vehicle_count > 0`）

次のVehicleが下流空間・各容量条件を満たさず通過不能になったら、**そのtimestepの処理全体を終了**する。

理由：

- 同一inlinkの後続Vehicleは単車線で通過不能Vehicleを追い越せない
- 異方向service unitは、現在timestepにすでにVehicleが通過したため、同じtimestep内に方向切替clearanceを満たせない

通過不能Vehicleと後続Vehicleはservice unitに残し、次のtimestepに再判定する。

---

### 1D.8 最初のVehicleが通過した後の処理

今回の呼出しで最初のVehicleが通過した後は、通過したVehicleのinlink方向（`active_inlink`）のみを処理する。

1. 現在のservice unit内をFIFO順に処理する
2. service unitが完了（`vehicles` が空）したら後続service unitを確認する
3. 後続service unitが同じinlinkなら処理を続ける
4. さらに同じinlinkのservice unitが続く限り、**件数に上限なく**処理を繰り返す
5. 同一inlinkの途中Vehicleが通過不能になったら終了する（§1D.7.2）
6. 異なるinlinkのservice unitに到達しても終了する

異方向で終了する理由：現在timestepにVehicleが通過したため、方向切替clearanceを同じtimestep内に満たせない。

---

### 1D.9 同一inlinkの連続service unit

同じinlinkのservice unitが2件に限らず、3件以上を含む任意の件数だけ連続する可能性がある。到着・clearance・下流空間・各容量条件を満たす限り、同じtimestep内で連続処理する。**固定上限を設けない。**

複数service unitをまたいだ合計通過Vehicle数が `node.batch_size`（N）を超えてもよい。

**`node.batch_size` の意味：**

- 1回のBATCH形成（`form_order_control_batch()`）で作る1方向service unitの最大Vehicle数
- **1 timestepの通過Vehicle数上限ではない**

---

### 1D.10 作業用listと正式service queue

#### 2つの入れ物の役割

| 入れ物 | 役割 |
|--------|------|
| **正式service queue**（`order_control_batch_service_queue`） | 次timestepにも引き継ぐ正式な待ち順。未完了service unitを残し、完了service unitを取り除く |
| **作業用list**（`service_units_to_check`） | 今回のメソッド呼出しでservice unitを確認する順番。開始時の確認順を維持する |

開始時に作成：

```python
service_units_to_check = list(s.order_control_batch_service_queue)
```

#### 具体例

**開始時の正式queue：** `A → B → C`

**処理結果：** Aは未完了、Bは完了、Cは未完了または未処理

**終了時の正式queue：** `A → C`（完了したBは削除）

作業用listは `A, B, C` の確認順を保持する。Bが完了して正式queueから除かれても、作業用list上の確認順は変化しない。これにより、正式queueの途中にある完了service unitを除外しつつ、未完了service unitの元の順序を維持できる。

**途中終了の例（clearance未充足）：**

- 開始時：`A → B → C`
- A：未完了、B：完了、C：clearance未充足で終了
- 終了時：`A → C`（空になったBを正式queueに残さない）

#### service unit自体は複製しない

`list(...)` 変換は外側のlistのみ新規作成する。各service unit辞書は複製しない。正式queueと作業用listは同じservice unit辞書への参照を共有するため、作業用list側で `vehicles` からVehicleを削除すると、正式queueに残る同じservice unitでもVehicle数が減る。外側の並び順は別管理。

#### 処理終了時の正式queue整理（`_finalize_service_queue()`）

作業用listのうち、`vehicles` が残っている未完了service unitだけを、元の順番で正式queueへ戻す。これにより完了service unitの削除と未完了service unitの相対順序維持を同時に行う。

---

### 1D.11 residual部分と正式queue順

residual部分（§1D.3）は元のservice unit内の `vehicles` リストにFIFO順で残す。別service unitには分割しない。

未完了service unit（residualを含む）は正式service queueの**元の相対順序**で残す。**最後尾へ移動しない。**

> **§15との関係：** 設計段階の「residual batchを一時的に後ろへ回す」記述は、Phase 4-6K実装では採用していない。現在の実装仕様は本節（§1D）を正とする。

---

### 1D.12 Link間遷移

通過可能Vehicleについて、`Node.transfer_fcfs_clearance()` と同じ方法でLink間遷移を行う。BATCH独自のVehicle移動方法は作っていない。

更新対象（少なくとも）：

- `inlink.cum_departure`、`outlink.cum_arrival`
- `inlink.traveltime_actual`、`vehicle.link_arrival_time`
- `inlink.capacity_out_remain`、`outlink.capacity_in_remain`
- `node.flow_capacity_remain`（`flow_capacity` 設定時のみ）
- `inlink.vehicles`、`outlink.vehicles_enter_log`
- `vehicle.link`、新Linkの `order_control_earliest_arrival_timesteps`
- `vehicle.x`、`vehicle.lane`、`vehicle.leader`、`vehicle.follower`
- `vehicle.move_remain`（通過後0）、`vehicle.v`
- `outlink.vehicles`、`node.incoming_vehicles`（通過Vehicleを削除）
- `last_order_control_inlink`、`last_order_control_entry_timestep`

#### move_remain

`Vehicle.carfollow()` で計算される、現在timestepにinlink終端を越えて進もうとした残り距離。通過時に `move_remain * outlink.u / inlink.u` でoutlink側移動距離へ換算し、使用後に0へ戻す。

#### trip-end Vehicle

比較対象内部Nodeを目的地としない研究シナリオ前提を維持。Phase 4-6Kではtrip-end VehicleをBATCH service unitで処理する機能は実装していない。

---

### 1D.13 blocked_inlinksとactive_inlink

実装で使用する一時状態：

| 変数 | 意味 |
|------|------|
| `blocked_inlinks` | 今回の呼出しでまだ1台も通過していない間（`transferred_vehicle_count == 0`）に、下流空間・各容量条件を満たさず通過不能と判定されたinlinkの集合。同じinlinkの後続service unitは確認しない |
| `active_inlink` | 今回の呼出しで最初にVehicleが通過したinlink。最初の通過後は `active_inlink` と同じinlinkのservice unitだけを処理し、異なるinlinkに到達した時点で終了 |

---

### 1D.14 必要最小限の実行時検証

登録時（4-6H）に保証済みの不変条件を、実通過時に全Vehicleについて重複検証しない。

**実通過時に検証する重大不整合（`ValueError`）：**

- clearance履歴のinlinkとtimestepの片方だけが `None`
- 先頭Vehicleに現在Node向けbatch assignmentがない
- assignmentのbatch IDとservice unitのbatch IDが一致しない
- Vehicleの現在Linkとservice unitのinlinkが一致しない
- `vehicle.route_next_link` が `None`

**正常な待機・通過不能（`ValueError` にしない）：**

- 未到着（`not in incoming_vehicles`）
- clearance未充足
- 物理的先頭でない（`veh != inlink.vehicles[0]`）
- 下流Link進入空間不足
- outlink流入容量不足、inlink流出容量不足、Node流量容量不足

**実通過時に繰り返していない検証：** Vehicle重複、service unit全体のFIFO、queue後方service unitの全構造、全Vehicleのassignment、batch_sizeやt_trigger_levelの型・範囲。

---

### 1D.15 N=1 BATCHとFCFSの対応

N=1では、各service unitが到着済みtrigger Vehicle 1台で構成される。

| 状況 | FCFS（`transfer_fcfs_clearance()`） | N=1 BATCH（`serve_order_control_batch_service_queue()`） |
|------|-------------------------------------|----------------------------------------------------------|
| clearance未充足 | 後続候補へ進まず停止 | 後続service unitへ進まず停止 |
| 下流空間・各容量条件未充足 | 後続候補を確認（`continue`） | 同inlink後続service unitは確認しない（単車線で追い越せない）。異inlinkのservice unitを確認 |
| 次timestep | 保存済み到着順から再評価 | 未完了service unitを元の正式queue順から再評価 |

Phase 4-6Kでは単体レベルの判断順の対応まで33テストで確認済み。シミュレーション全体での完全同一性は `Node.transfer()` 接続後の課題。

---

### 1D.16 docstringの設計記録

`serve_order_control_batch_service_queue()` のdocstringに、次の主要規則を記載済み：

- 未到着は後続へ進まず待つ
- clearance未充足も後続へ進まず待つ
- 0台通過時の通過不能では異方向service unitを確認する
- 最初の通過後は同一inlinkを処理する
- 1台以上通過後の途中通過不能では全体終了
- 異方向に到達しても全体終了
- 同一inlink連続service unitに固定上限を設けない
- 完了service unitは途中終了時もqueueから削除する
- 未完了service unitの相対順序を維持する

---

### 1D.17 テストと回帰結果

#### 新規テストファイル

`tests_order_control_batch_service_queue_transfer.py`

- テスト関数数：**33**
- `TESTS` 登録数：**33**（各テスト1回実行）
- 結果：`Order-control batch service-queue transfer tests passed.`

#### テスト範囲（整理）

| カテゴリ | テスト例 |
|----------|----------|
| 基本通過 | 空queue、1台通過、複数台通過、residual部分のFIFO保持 |
| 未到着 | `test_not_arrived_waits` |
| clearance | 履歴なし、同一inlink不要、異方向未充足、充足後通過、履歴ペア不整合（両方向）、成功時のみ履歴更新 |
| 下流空間・容量 | 下流進入空間、outlink流入、inlink流出、Node流量（不足・通過時減少） |
| 物理的先頭 | `test_not_physical_head` |
| 連続service unit | 同一inlink3件以上、N超過通過、0台通過時異方向確認、同inlink後続スキップ |
| 作業用list・queue整理 | 中間完了unit削除、途中終了時完了unit削除、1台以上通過後に後方unitへ進まない |
| 重大不整合 | assignment欠如、batch ID不一致、Vehicle Link不一致、`route_next_link=None` |
| Link遷移 | `test_link_transition_updates` |
| N=1とFCFS対応 | `test_n1_clearance_blocks_later_unit`、`test_n1_capacity_fail_checks_different_inlink` |

#### 新規Phase 4-6Kテスト1本・指定既存回帰テスト19本・example

新規Phase 4-6Kテスト1本（テスト関数33件）、指定既存回帰テスト19本、example 1本がすべて exit code 0。baseline・exampleの主要交通結果は従来の既知値と一致し、確認対象の主要指標に回帰は検出されなかった。

**baseline（`tests_order_exchange_baseline.py`）：** completed trips 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、delay ratio 0.017、total distance traveled 48000.0 m

**example（`example_00en_simple.py`）：** completed trips 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、delay ratio 0.385、total distance traveled 1632250.0 m

---

### 1D.18 未実装範囲と次工程

Phase 4-6K完了後の次工程候補（いずれも**未実装**）：

1. BATCH専用transfer統括メソッド
2. 1 timestepごとの新規BATCH形成回数の管理
3. 形成済みservice queueの実通過との接続（統合呼出し）
4. `incoming_vehicles` の最終整理
5. `Node.transfer()` へのBATCH分岐
6. 接続後の回帰テスト
7. N=1 BATCHとFCFSの完全同一性テスト（シミュレーション全体）

引き続き未実装：Level 2仮想サービス推定、trip-end VehicleのBATCH対応、Time-value Transaction。

---

### 1D.19 再開時チェックリスト

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| 最新コミット（Markdown） | `9a2f32f` — Phase 4-6E〜4-6J正式記録 |
| Phase 4-6K | 実装・33テスト・回帰完了。**本Markdown更新時点では未commit** |
| 変更中ファイル | `uxsim/uxsim.py`、`tests_order_control_batch_service_queue_transfer.py`、本正式Markdown 2ファイル |
| `Node.transfer()` | BATCH分岐**未接続** |
| 次に読む実装 | `Node.serve_order_control_batch_service_queue()` |
| 次に読むテスト | `tests_order_control_batch_service_queue_transfer.py` |
| 次工程 | BATCH専用transfer統括と `Node.transfer()` 接続の設計 |

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
- `earliest_arrival_timestep <= t_trigger` を満たす車両を候補に含める。（**Phase 4-6Eで実装済み。詳細は§1C.4**）

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
- 他方向batchの順序は、**snapshot estimated arrival**（下記）に基づく。（**Phase 4-6Fで実装済み。詳細は§1C.5**）

### snapshot estimated arrival（Phase 4-6Fで実装済み）

**後の実装で変更：** 以下は設計段階の記述。実装仕様は **§1C.5** の計算式を正とする。

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
- `inlink.u <= 0` の場合はValueErrorとする。

### phase 4-6Bで実装済み：BATCH状態コンテナ

**Vehicle**

- `order_control_batch_assignments = {}`（Vehicle側。Phase 4-6Hで当該Node keyへの書き込みを実装済み。§1C.3.1）

**Node**

- `order_control_batch_service_queue = deque()`（初期化のみ）
- `order_control_batch_next_id = 0`（Phase 4-6Hで登録時に増加。§1C.3.3）

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

### Phase 4-6Kの確定仕様（§1Dを正とする）

1. **未到着**と**下流空間・各容量条件による通過不能**を区別する。
2. 未到着なら、後続service unitへ進まず到着を待つ（§1D.5）。
3. 一部通過後に残った未通過Vehicle列を **residual部分** と呼ぶ（§1D.3）。
4. residual部分を元service unit内にFIFO順で残す。別service unitとして作り直さない。
5. 未完了service unitを正式service queueの**最後尾へ移動しない**。未完了service unit同士の相対順序を維持する。
6. 次のtimestepでは、正式service queueの元の順番から再評価する。
7. 今回の呼出しでまだ1台も通過していない場合に限り、下流空間・各容量条件を満たさないservice unitを残したまま、条件を満たし得る異inlinkの後続service unitを確認する（§1D.7.1）。

### 設計段階の旧案（参考）

- 容量制約・アウトリンク閉塞・node容量不足等により、batch途中車両が一時的に通過不可になった場合、未通過部分を **residual batch** として扱う、という用語・概念は維持する。
- residual batchは元batch内の未通過部分であり、**内部順序を維持**する。
- 設計段階では、未完了service unitを一時的にqueue後方へ移す案も検討した。しかし、N=1 BATCHとFCFSの評価順を対応させる観点から、Phase 4-6Kではこの案を採用しなかった。
- 既存FCFSでは、容量制約等で通過できないvehicleがあっても、clearance未充足とは区別しながら後続候補を処理する構造を採っていた。Phase 4-6Kでは、0台通過時の通過不能に限り異inlink後続service unitの確認という形で、FCFSのcontinueに相当する処理を実装している（§1D.7.1）。

> 現在の実装仕様は **§1D.11** を正とする。旧案の「queue後方へ移す」記述は設計経緯の参考であり、現行コードの動作ではない。

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

### 当初の実装済み範囲（Phase 4-6A〜4-6D）

1. Vehicle側にBATCH用の `earliest_arrival_timestep` を付与する。（**phase 4-6A**）
2. World/Node側にBATCH用状態コンテナを初期化する。（**phase 4-6B**）
3. BATCH trigger候補Vehicleを決定的順序で返す参照専用ヘルパーを追加する。（**phase 4-6C**）
4. `t_trigger` をLevel 0 / Level 1で推定する参照専用ヘルパーを追加する。（**phase 4-6D**）
5. 既存FCFS / clearance処理を壊さないことを回帰テストで確認済み。

### 当初の未実装項目とPhase 4-6K完了時点の状況

**後の実装で変更：** 項目1〜9は主に Phase 4-6C〜4-6I で実装され、項目10〜11は Phase 4-6K で実装された。以下に Phase 4-6K 完了時点の状況を示す。

1. 未batch車両がリンク端に到着したらtrigger vehicleとする（**4-6C・4-6Iで実装済み**）。
2. 同時到着時は既存FCFSと同様にtiebreaker等でtrigger順を決める（**4-6Cで実装済み**）。
3. `earliest_arrival_timestep <= t_trigger` を満たす未batch車両を全inlinkからFIFO維持で候補化する。（**4-6E実装済み。§1C.4**）
4. 候補をinlink方向別に分ける。（**4-6E実装済み**）
5. 各方向で最大N台までbatch化する。（**4-6G実装済み。§1C.6**）
6. Nに達したら今回のbatch形成を打ち切る。（**4-6G実装済み**）
7. 他方向batchをsnapshot estimated arrivalで並べ、trigger方向を先頭にする。（**4-6F実装済み。§1C.5**）
8. batch_id発行、`order_control_batch_assignments` への記録、service queueへの追加。（**4-6H実装済み。§1C.7**）
9. batch化済み車両を再候補にしない。（**4-6C・4-6Eで実装済み**）
10. batch内順序を固定する。未到着なら待つ。（**4-6Kで実装済み。§1D**）
11. residual batchとして扱う方針を実装する。（**4-6Kでresidual部分の保持を実装済み。§1D.3・§1D.11。queue最後尾移動は採用せず**）
12. `order_control_type="batch"` で `Node.transfer` から分岐する。（**未実装**）
13. Level 2仮想サービス計算とLevel 2→Level 1 fallback。（**未実装**）

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

### 当初の実装済みテスト（Phase 4-6A〜4-6D）

- `tests_order_control_batch_earliest_arrival_timestep.py`（Phase 4-6A）
- `tests_order_control_batch_state_containers.py`（Phase 4-6B）
- `tests_order_control_batch_trigger_candidates.py`（Phase 4-6C）
- `tests_order_control_batch_t_trigger_estimation.py`（Phase 4-6D、21テスト関数）

Phase 4-6A〜4-6D各実装後、FCFS/clearance既存テストおよび `tests_order_exchange_baseline.py`、`example_00en_simple.py` はPASS。主要交通結果は既知値と一致（確認対象の主要指標に回帰は検出されなかった）。

Phase 4-6E〜4-6Jで追加されたBATCH形成・登録・設定のテストは **§1C.11** を参照。

Phase 4-6Kで追加されたservice queue実通過テストは **§1D.17** を参照（`tests_order_control_batch_service_queue_transfer.py`、33テスト）。

### Phase 4-6J完了時点の未実施テストとPhase 4-6Kでの対応

| 課題 | 4-6Kでの状況 |
|------|-------------|
| service queueに基づくVehicle実通過 | **実装・テスト済み（§1D）** |
| service unit内の未到着Vehicleが到着まで待つこと | **テスト済み** |
| 同一inlinkの連続service unitを同一timestep内に続けて処理すること | **テスト済み** |
| 同一inlinkの連続service unitをまたいだ通過台数がNを超えてもよいこと | **テスト済み** |
| 異なるinlinkのservice unitへ切り替わる際のclearance | **テスト済み** |
| 容量不足時の停止 | **テスト済み** |
| 通過済みVehicleのservice unitからの削除 | **実装済み** |
| 完了service unitのqueueからの削除 | **実装・テスト済み** |
| residual batch | **residual部分のFIFO保持を実装・テスト済み（queue最後尾移動なし）** |
| N=1 BATCHとFCFSの完全同等性 | **単体判断順はテスト済み。シミュレーション全体は接続後** |
| `Node.transfer()` 接続後の回帰確認 | **未実施（次工程）** |
| `clearance_timesteps=1` でFCFSより方向切替回数が減る可能性 | **接続後の検証課題** |

---

## 22. 未解決事項

### 解決済み

- `earliest_arrival_timestep` → **Vehicle.order_control_earliest_arrival_timesteps として実装済み**（phase 4-6A）
- `tau_timesteps` のWorld設定 → **order_control_batch_tau_timesteps、setter実装済み**（初期値1、phase 4-6A）
- t_trigger Level 0 / Level 1推定 → **phase 4-6Dで実装済み**
- trigger候補の決定順 → **get_order_control_batch_trigger_candidates() で実装済み**（phase 4-6C）
- Node別batch assignment → **order_control_batch_assignments、phase 4-6Bで初期化、4-6Hで書き込み**
- 全inlinkからのBATCH候補抽出 → **phase 4-6Eで実装済み**（§1C.4）
- snapshot estimated arrivalによるinlink別batch間順序 → **phase 4-6Fで実装済み**（§1C.5）
- service unitの具体的データ形式 → **phase 4-6Hで確定**（§1C.3.2）。batch内部構造もこのservice unit形式を指す
- residual部分と正式queue順 → **phase 4-6Kで方針確定・実装済み**（元の相対順序を維持、最後尾へ移動しない。§1D.11）
- service queueに基づくVehicle実通過 → **phase 4-6Kで実装済み**（§1D）

### 未解決・将来課題

- `tau_timesteps` を常に1でよいか（研究比較で可変にするか）。
- Level 2仮想サービス計算をいつ導入するか。
- Level 2 unresolved時のLevel 1 fallback接続をいつ実装するか。
- BATCH専用transfer統括メソッド。
- `Node.transfer()` へのBATCH分岐。
- N=1 BATCHとFCFSのシミュレーション全体での完全同一性（単体判断順は4-6Kで確認済み。接続後の課題）。
- debug/log出力の粒度。
- 比較対象Node共通管理。
- 目的地自動検証。
- trip-end service unit。
- taxi mode向け動的dest検証。
- Time-value Transactionとどの段階で接続するか。

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
- `Node.transfer`（BATCH分岐は**未接続**）
- `transfer_fcfs_clearance`
- `transfer_fcfs_no_clearance`
- `record_order_control_node_first_arrival`
- `record_order_control_earliest_arrival_timestep_for_current_link`（phase 4-6A）
- `get_order_control_batch_trigger_candidates`（phase 4-6C）
- `estimate_order_control_batch_t_trigger_level_0` / `_level_1`（phase 4-6D）
- `get_order_control_batch_candidates_by_inlink`（phase 4-6E）
- `get_ordered_order_control_batch_candidates_by_inlink`（phase 4-6F）
- `apply_order_control_batch_max_size`（phase 4-6G）
- `register_order_control_batch_service_units`（phase 4-6H）
- `form_order_control_batch`（phase 4-6I）
- `_validate_order_control_batch_t_trigger_level`、`set_order_control_for_nodes`（phase 4-6J）
- `serve_order_control_batch_service_queue`（**phase 4-6K。`Node.transfer()`未接続**）
- `Link.__init__`
- `Link.update` / `in_out_flow_constraint` 周辺

### BATCH関連テスト（Phase 4-6A〜4-6K）

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
- `tests_order_control_batch_service_queue_transfer.py`（**phase 4-6K、33テスト**）

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

- 現在ブランチ：`feature/intersection-order-control`。
- `git status`。
- `git log --oneline -20`。
- **Phase 4-6E〜4-6Jは実装・テスト・commit・push済み**（最新Markdownコミット：**9a2f32f**）。
- **Phase 4-6Kは実装・33テスト・回帰確認済み。本Markdown更新時点では未commit。**
- **BATCH形成・service unit登録・service queue実通過は実装済み。`Node.transfer()` batch分岐は未実装。**
- FCFS / clearance までは検証済み。
- 次は **BATCH専用transfer統括メソッドの設計・実装 → `Node.transfer()` BATCH分岐接続**。
- 詳細は **§1D** を優先参照（4-6K）、形成・登録は **§1C**。
- 目的地Vehicleは端点間OD前提で保留。比較対象Node共通管理・自動検証は将来課題。
- 一時退避PDF `phase4-6A_batch_earliest_arrival_timestep_memo.pdf` はリポジトリ外。正式Markdownを優先参照。
