# ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES

UXsim Order Exchange 改変作業における、phase 4-6：交差点BATCH処理の実装前正式設計メモ。

進捗の詳細は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照してください。FCFS / clearance 実装の詳細は [ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md](ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES.md) を参照してください。

---

## 1A. 実装状況サマリ（phase 4-6A〜4-6M）

進捗の詳細・コミットID・回帰結果は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照。Phase 4-6E〜4-6Jの設計・判断経緯の詳細は **§1C**、Phase 4-6Kの実装記録は **§1D**、Phase 4-6Lの統括メソッド記録は **§1E**、Phase 4-6Mの `Node.transfer()` 接続記録は **§1F**、Phase 4-6Nの比較・診断記録は **§1G**、Node訪問単位の共通状態設計は **§1H**（zero-service追加形成・size-one BATCHとFCFS等価性は **§1H.25**）を参照。

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
| | phase 4-6K：`serve_order_control_batch_service_queue()`（12e8eae） |
| | phase 4-6L：`transfer_batch()`（BATCH形成・実通過統括）（e9f3ce9） |
| | phase 4-6M：`Node.transfer()` へのBATCH分岐接続（b03538c） |
| | phase 4-6N：`serve_order_control_batch_service_queue()` のroute_next_link参照順修正（05fa2d1） |
| | phase 4-6N：clearance=0比較テスト3本（f339b88） |
| | phase 4-6N：比較・Node再訪診断の正式記録（c06936c） |
| | phase 4-6N：診断スクリプトの通常回帰テストからの分離保存（0e35799） |
| | phase 4-6O：現在訪問状態の共通基盤（e3243e7） |
| | phase 4-6P：Node端到着記録の訪問対応（b1b4d7f・b051c58） |
| | phase 4-6Q：FCFSのcurrent visit参照（7c3c6d3・9100803） |
| | phase 4-6R：BATCH形成のcurrent visit参照（cdd19be・30588a0・ae57e40） |
| | phase 4-6S：BATCH assignmentの訪問対応・service unit visit_id・実通過照合（5e26bc9） |
| | phase 4-6T：小規模BATCH再訪end-to-end統合（b7159f9） |
| | phase 4-6U：high-demand再実行・検証完了（§1H.24。本体変更なし） |
| | phase 4-6V：zero-service追加形成修正・size-one BATCHとFCFSの等価性回復（2b10b08） |
| | phase 4-6V診断：size-one BATCH対FCFS等価性・batch size予備比較（fe9e53e。§1H.25） |
| **診断スクリプト** | `diagnostics/order_control/`（6本＋README）。通常回帰テストから分離済み（`0e35799`）。詳細は `diagnostics/order_control/README.md` |
| **BATCH形成〜シミュレーション接続まで完成** | trigger候補取得 → … → service queue登録（4-6I）→ 実通過（4-6K）→ 統括呼出し（4-6L）→ **`Node.transfer()` 接続（4-6M）** → **BATCH形成のcurrent visit参照（4-6R）** → **BATCH assignmentの訪問対応（4-6S）** → **小規模BATCH再訪end-to-end統合（4-6T）** |
| **現時点の主要課題** | trip-end VehicleのBATCH service unit対応、stale service unit処理方針、assignment正式全訪問履歴、Level 2仮想サービス推定、Level 2 unresolved時のLevel 1 fallback接続、Time-value Transaction |
| **未実装** | Level 2仮想サービス推定、Level 2 unresolved時のLevel 1 fallback接続 |
| | trip-end VehicleのBATCH service unit対応 |
| | stale service unitの自動削除または回復方針 |
| | assignmentの正式な全訪問履歴 |
| | Time-value Transaction、比較対象Node共通管理、目的地自動検証、taxi mode向け動的dest検証 |
| **当面の研究シナリオ前提** | 比較対象内部交差点Nodeを目的地としない端点間OD |
| | 全比較方式で同一ネットワーク・同一OD需要 |
| **研究基本設定（明示指定）** | 研究の通常方式は **Level 2**（未実装）。Level 2で解決不能時は **Level 1** へfallback、必要に応じて **Level 0** へfallback。 |
| | 暫定比較では `batch_size=10`、`order_control_batch_t_trigger_level=1`（Level 1は最終基本設定ではない） |
| **次工程候補** | Level 2仮想サービス推定の設計調査（**§1H.25**）。Level 2 unresolved時のLevel 1 fallback接続。必要に応じてLevel 0 fallback。trip-end Vehicleは研究対象外。stale service unit回復は必要性が低ければ保留。assignment全訪問履歴は後回し。Time-value Transaction本体 |

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

**後の実装で変更された判断：** §10・§12・§18・§21の旧記述（「4-6E〜4-6G未実装」「snapshot estimated arrival未実装」「service unit形式TBD」等）は、Phase 4-6E〜4-6J完了時点では **§1Cが正** である。Phase 4-6K（service queue実通過）完了時点では **§1Dが正**、Phase 4-6L（`transfer_batch()` 統括）完了時点では **§1Eが正**、Phase 4-6M（`Node.transfer()` 接続）完了時点では **§1Fが正** である。旧節は設計経緯の参考として残し、実装状況は本節および §1D・§1E・§1F を優先参照すること。

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

#### 現在地点（Phase 4-6J完了時点の記録）

- **実装済み：** trigger候補取得 → … → Node群一括設定（上記）。
- **当時未実装だった項目のうち、後続Phaseで実装済み：** service queue実通過（4-6K）、BATCH統括（4-6L）。現行の実装状況は **§1A・§1D・§1E** を参照。

#### 研究基本設定（明示指定。Phase 4-6J完了時点の記録）

**t_trigger推定の研究基本設計（現行方針）：** 通常方式はLevel 2。Level 2でunresolvedの場合はLevel 1へfallback。必要に応じてLevel 0へfallback。

**当時の実装可能な暫定設定（Phase 4-6J時点）：** Level 2は未実装のため、以下のコード例では `order_control_batch_t_trigger_level=1` を使用していた。

```python
W.set_order_control_for_nodes(
    target_node_names,
    order_control_type="batch",
    batch_size=10,
    transaction_case=None,
    order_control_batch_t_trigger_level=1,
)
```

`batch_size` の基本値は **10**（Node既定値は **1** のまま維持。研究条件では10を明示指定する）。

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

★印は Phase 4-6E〜4-6J で完成した処理。Phase 4-6K（実通過）・Phase 4-6L（`transfer_batch()` 統括）・Phase 4-6M（`Node.transfer()` 接続）は **§1D・§1E・§1F** を参照。

**4-6L完了時点の次工程（4-6Mで実装済み。§1F参照）：**

- `Node.transfer()` へのBATCH分岐（`transfer_batch()` 呼出し）
- `Node.transfer()` 接続後の実シミュレーション時系列テスト
- N=1 BATCHとFCFSのシミュレーション全体での完全同一性テスト

**引き続き未実装：**

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
- `transfer_batch()` からの呼び出し（**Phase 4-6Lで実装済み。§1E**）：

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

### 1C.13 現在未実装の範囲（Phase 4-6M完了後）

Phase 4-6K（**§1D**）、Phase 4-6L（**§1E**）、Phase 4-6M（**§1F**）により、service queue実通過、BATCH形成と実通過の統合呼出し、正常終了時の `incoming_vehicles` 整理、`Node.transfer()` からのBATCH分岐、実シミュレーション上の到着・形成・実通過時系列、N=1 BATCHとclearance付きFCFSの完全一致は**実装・テスト済み**である。

**引き続き未実装：**

- Level 2仮想サービス推定
- Level 2 unresolved時のLevel 1 fallback接続
- trip-end VehicleのBATCH service unit対応
- Time-value Transaction
- 比較対象Node共通管理、目的地自動検証、taxi mode向け動的dest検証

**注記：** §15の設計段階記述にあった「residual batchを一時的に後ろへ回す」方針は、Phase 4-6K実装では採用していない。未完了service unitは正式queueの最後尾へ移動せず、元の相対順序で残す（**§1D.11**）。

---

### 1C.14 Phase 4-6K（service queueに基づく実通過）— 実装完了

Phase 4-6Kは**実装・テスト・回帰確認完了**（commit `12e8eae`）。詳細は **§1D** を正とする。

### 1C.14A Phase 4-6L（BATCH形成・実通過の統括）— 実装完了

Phase 4-6Lは**実装・17テスト・回帰確認完了**（commit `e9f3ce9`）。詳細は **§1E** を正とする。

- メソッド名：`transfer_batch()`、戻り値：`dict`（`formation_result`、`transferred_vehicle_count`）
- `form_order_control_batch()` と `serve_order_control_batch_service_queue()` を各1回呼ぶ
- 正常終了時に `incoming_vehicles` を空にする
- **`Node.transfer()` への接続は Phase 4-6M（§1F）で実装済み**

#### 確定済み設計（§1C.14で列挙していた項目は §1D で実装済み）

- メソッド名：`serve_order_control_batch_service_queue()`、戻り値：`int`（通過Vehicleオブジェクト数）
- BATCH形成（`form_order_control_batch()`）と実通過を分離
- `Node.transfer()` へは**未接続**（Phase 4-6Kの意図的な範囲外。**Phase 4-6M（§1F）で接続済み**）

#### 旧「今後確認する事項」

§1C.14に列挙していた未確定事項は、Phase 4-6K実装・33テストで確定した。回答は **§1D** 各節を参照。

---

### 1C.15 次回再開時チェックリスト（Phase 4-6L完了時点の記録）

現行の再開チェックリストは **§1F.16** を正とする。以下はPhase 4-6L完了時点の再開情報である。

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| 最新コミット（4-6K） | `12e8eae` |
| Phase 4-6L | `transfer_batch()` 実装・17テスト・回帰確認済み、**未commit** |
| `Node.transfer()` | BATCH分岐は**未接続**（**4-6Mで接続済み。§1F**） |
| 次工程 | `Node.transfer()` へのBATCH分岐接続（**4-6Mで完了。§1F**） |

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
| **4-6K** | `Node.serve_order_control_batch_service_queue(s) -> int` | 実装・33テスト・指定既存回帰成功。commit済み（12e8eae） |
| 入力（4-6H） | `register_order_control_batch_service_units()` | commit済み（8cf6dec） |
| 参考（FCFS） | `transfer_fcfs_clearance()` | Link間遷移の実装元 |

#### 現在地点（Phase 4-6K完了時点の記録）

- **実装済み：** 登録済みservice queueに基づくVehicle実通過、service unit内FIFO、同一inlink連続service unit処理、未到着待機、clearance判定、下流空間・各容量条件判定、0台通過時の異方向service unit確認、1台以上通過後の停止規則、residual部分の保持、完了service unit削除、未完了service unitの正式queue順維持、FCFSと同じLink間遷移、通過Vehicle数の戻り値、必要最小限の重大不整合検出。
- **4-6K時点では意図的に未接続：** `Node.transfer()` からの呼出し（**4-6M（§1F）で接続済み**）。
- **4-6K時点では未実装だった項目（後続Phaseで実装済み）：** `Node.transfer()` BATCH分岐・接続後回帰・N=1 BATCHとFCFS完全一致（**4-6M、§1F**）。BATCH統括（**4-6L、§1E**）。引き続き未実装：Level 2、trip-end Vehicle、Time-value Transaction。

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

Phase 4-6Kでは単体レベルの判断順の対応まで33テストで確認済み。シミュレーション全体での完全同一性は **Phase 4-6M（§1F.13）で確認済み**。

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

### 1D.18 未実装範囲と次工程（Phase 4-6K時点の記録）

Phase 4-6K完了時点では、次工程候補として以下が未実装であった。うち項目1〜4は **Phase 4-6L（§1E）で実装済み**。

1. BATCH専用transfer統括メソッド → **4-6Lで `transfer_batch()` として実装済み（§1E）**
2. 1 timestepごとの新規BATCH形成回数の管理 → **4-6Lで各 `transfer_batch()` 呼出しにつき形成を必ず1回に固定（§1E.5）**
3. 形成済みservice queueの実通過との接続（統合呼出し） → **4-6Lで実装済み（§1E）**
4. `incoming_vehicles` の最終整理 → **4-6Lで正常終了時のみ実施（§1E.8）**
5. `Node.transfer()` へのBATCH分岐 → **4-6Mで実装済み（§1F）**
6. 接続後の回帰テスト → **4-6Mで実施済み（§1F.14）**
7. N=1 BATCHとFCFSの完全同一性テスト（シミュレーション全体） → **4-6Mで確認済み（§1F.13）**

引き続き未実装：Level 2仮想サービス推定、trip-end VehicleのBATCH対応、Time-value Transaction。

**現行の次工程は §1F.15 を参照。**

---

### 1D.19 再開時チェックリスト（Phase 4-6K時点の記録）

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| 最新コミット（4-6K） | `12e8eae` — Phase 4-6Kの実装・33テスト・正式Markdown記録 |
| Phase 4-6K | commit済み（`12e8eae`） |
| `Node.transfer()` | BATCH分岐**未接続**（**4-6Mで接続済み。§1F**） |
| 次工程（4-6K時点） | BATCH専用transfer統括 → **4-6Lで完了。`Node.transfer()` 接続は4-6Mで完了。現行は §1F.15・§1F.16** |

---

## 1E. Phase 4-6L：BATCH形成・実通過の統括メソッド

本節は、Phase 4-6I（`form_order_control_batch()`）と Phase 4-6K（`serve_order_control_batch_service_queue()`）を、1 timestepあたり正しい順序で各1回呼び出す **`Node.transfer_batch()`** の設計・実装・テストを記録する。別担当者または別AIが本メモとリポジトリのみを読んで、BATCH処理の統括層を正確に理解できることを目的とする。

**位置づけ：** Phase 4-6Lは Phase 4-6K の直後工程である。BATCH形成と実通過の中身は再実装せず、既存2メソッドを統括する。`Node.transfer()` へのBATCH分岐は **Phase 4-6M（§1F）で実装済み**。

### 1E.1 対象範囲と現在地点（Phase 4-6L完了時点の記録）

| Phase | メソッド | 状態 |
|-------|----------|------|
| **4-6L** | `Node.transfer_batch(s) -> dict` | 実装・17テスト・指定既存回帰成功（commit `e9f3ce9`） |
| 形成（4-6I） | `form_order_control_batch()` | commit済み（d10a6db） |
| 実通過（4-6K） | `serve_order_control_batch_service_queue()` | commit済み（12e8eae） |
| 接続先 | `Node.transfer()` | **Phase 4-6M（§1F）で接続済み** |

**4-6Lで実装済み：** BATCH形成とservice queue実通過の統合呼出し（各1回）、正常終了時の `incoming_vehicles` 整理、例外時の `incoming_vehicles` 維持、形成結果と通過台数の辞書返却、到着timestep T→形成・通過判定timestep T+1の単体確認。

**4-6L時点では未実装だった項目（4-6Mで実装済み。§1F参照）：** `Node.transfer()` からの `transfer_batch()` 呼出し、接続後の実シミュレーション時系列テスト、N=1 BATCHとFCFSのシミュレーション全体での完全同一性。

### 1E.2 メソッドの責任とシグネチャ

```python
def transfer_batch(s) -> dict:
```

`transfer_batch()` は、BATCH形成処理やVehicle実通過処理の中身を再実装しない。既存の2メソッドを正しい順序で呼ぶ**統括メソッド**である。

### 1E.3 Phase 4-6I・4-6Kとの責任分担

| メソッド | 責任 |
|----------|------|
| `Node.form_order_control_batch()` | trigger候補取得、t_trigger推定、候補抽出、方向別最大N適用、batch ID・assignment・service unit登録 |
| `Node.serve_order_control_batch_service_queue()` | 未到着・clearance・下流空間・各容量条件の判定、service queueに従うVehicle実通過、residual部分の保持、完了service unit削除 |
| `Node.transfer_batch()` | 上記2メソッドを順に各1回呼び、正常終了後の `incoming_vehicles` 整理と結果返却 |

### 1E.4 処理順序

`transfer_batch()` の処理順は次のとおりであり、**この順序へ変更してはならない**。

```
BATCH形成を必ず1回試みる（form_order_control_batch）
    ↓
service queue実通過を必ず1回行う（serve_order_control_batch_service_queue）
    ↓
incoming_vehiclesを空にする（正常終了時のみ）
    ↓
結果を返す
```

禁止事項：

- 実通過を先にして、形成を後にしない
- `incoming_vehicles` を形成前に空にしない
- `incoming_vehicles` を実通過前に空にしない

形成を先にする理由：前timestep末までに到着済みのtrigger Vehicleについて、現在timestepで形成した直後に同じ `transfer_batch()` 呼出し内で実通過判定を行い、不要な追加1 timestep待ちを避けるためである。

### 1E.5 BATCH形成の呼出し

`transfer_batch()` は、次を**必ず1回**呼ぶ（任意ではない。whileループ等で同一呼出し内に複数回形成しない）。

```python
s.form_order_control_batch(
    t_trigger_level=s.order_control_batch_t_trigger_level,
    max_batch_size=s.batch_size,
)
```

- `t_trigger_level` は Node属性 `order_control_batch_t_trigger_level` から取得する
- `max_batch_size` は Node属性 `batch_size` から取得する
- `transfer_batch()` の引数として受け取らない
- 固定値を使用しない

`transfer_batch()` を1回呼ぶたびに形成処理を必ず1回呼ぶ。trigger候補がある場合だけ実際に新しいBATCHが形成され、trigger候補がない場合は `"no_trigger_candidate"` が返る。

形成結果は `"batch_formed"` または `"no_trigger_candidate"` のいずれかである。`"no_trigger_candidate"` でも、既存service queueに未完了service unitが残っている可能性があるため、実通過処理へ進む。

### 1E.6 service queue実通過の呼出し

形成結果にかかわらず、次を**必ず1回**呼ぶ。

```python
s.serve_order_control_batch_service_queue()
```

1回だけ呼ぶ理由：`serve_order_control_batch_service_queue()` は1回の呼出しで、service unit内FIFO、同一inlinkの連続service unit処理、0台通過時に確認可能な異inlink service unit処理、1台以上通過後の停止判定、完了service unit削除、residual部分の保持、未完了service unitの正式queue順維持をまとめて処理する。同じtimestep内に再度呼ぶと、現在timestepでは再確認しないと決めた通過不能service unitをもう一度判定するおそれがある。

### 1E.7 Vehicle到着から形成・通過までの時系列

UXsimでは、`Node.transfer()` が `Vehicle.update()` より先に実行される（`World.exec_simulation()`）。

timestep TにNode端へ到着するVehicleの時系列：

```
timestep T の Node.transfer()
    VehicleはまだNode端への到着登録前

timestep T の Vehicle.update()
    VehicleがNode端へ到着
    同じNodeの incoming_vehicles へ登録
    初回Node到着情報を記録

timestep T+1
    transfer_batch() によりBATCH形成
    同じ transfer_batch() 内で実通過判定
```

したがって、timestep Tに到着したVehicleが最初に形成・通過判定を受けるのは timestep T+1 である。

既存実装は到着時刻（秒）からtimestepへ変換し、次を計算する。

```python
arrival_timestep = int(round(arrival_seconds / W.DELTAT))
first_transfer_timestep = arrival_timestep + 1
```

Phase 4-6Lの時系列テスト（`test_timeline_arrival_formation_transfer`）で確認済み：

- `arrival_timestep = 10`、`arrival_seconds = 10.0`、`W.DELTAT = 1`
- Level 0推定結果 = 11（= `first_transfer_timestep`）
- timestep 11の同じ `transfer_batch()` 呼出し内でBATCH形成・1台通過（timestep 12まで余分に待たせない）
- 到着登録前のtimestep 10では `formation_result = "no_trigger_candidate"`、`transferred_vehicle_count = 0`

### 1E.8 incoming_vehiclesの最終整理

形成処理と実通過処理の**両方が正常終了した場合だけ**、次を実行する。

```python
s.incoming_vehicles = []
```

**責任を `transfer_batch()` に置く理由：** 現在の `Node.transfer()` はFCFSの場合、`transfer_fcfs_clearance()` の後に `return` する流れであり、FCFS専用transferが自分自身で `incoming_vehicles` を空にする。将来BATCHも同様に `Node.transfer()` から呼ばれるため、`transfer_batch()` が正常終了時の `incoming_vehicles` 整理を担当する。

#### 1E.8.1 正常終了時に削除されるVehicle

`serve_order_control_batch_service_queue()` 終了後も `incoming_vehicles` に残っている全Vehicleを削除する。残存Vehicleには次の2種類が含まれ得る。

1. batch assignment済みだが、今回は通過できなかった到着済みVehicle
2. 今回のBATCH形成には選ばれず、未batchのまま残った到着済みVehicle

どちらのVehicleも、Vehicle本体は現在のinlink上に残る。batch assignment済みVehicleについては、service unit内のVehicle列、batch assignment、residual部分、正式service queue内の未完了service unitと順序も維持する。未batch Vehicleにはservice unit、assignment、residual部分が存在しないため、それらを維持する対象とはしない。

Node端に残ったVehicleは、同じtimestep末の `Vehicle.update()` でNode端にいることが再度検出され、次のtimestepの通過判定に使用するため、**同じNodeの `incoming_vehicles`** へ再登録される。

#### 1E.8.2 形成前・実通過前には空にしない

- 形成前に空にするとtrigger候補を取得できない
- 実通過前に空にすると、到着済みVehicleが未到着扱いになる

したがって、`incoming_vehicles` を空にするのは形成と実通過の正常終了後だけである。

### 1E.9 例外時の動作

`form_order_control_batch()` または `serve_order_control_batch_service_queue()` が例外を送出した場合、`transfer_batch()` は `incoming_vehicles` を空にしない。`finally` による無条件clearは行っていない。

| 例外発生箇所 | 動作 |
|--------------|------|
| 形成時 | 実通過メソッドを呼ばない。`incoming_vehicles` を空にしない。元の例外をそのまま呼出し元へ伝える |
| 実通過時 | `incoming_vehicles` を空にしない。`transfer_batch()` 独自のロールバックは行わない。元の例外をそのまま呼出し元へ伝える |

### 1E.10 戻り値

```python
{
    "formation_result": formation_result,
    "transferred_vehicle_count": transferred_vehicle_count,
}
```

| キー | 内容 |
|------|------|
| `formation_result` | `"batch_formed"` または `"no_trigger_candidate"` |
| `transferred_vehicle_count` | 今回の呼出しでLink間遷移を完了したVehicleオブジェクト数（0以上のint）。`W.DELTAN` を掛けた交通量ではない |

この戻り値だけでは、未到着・clearance未充足・下流空間・各容量条件未充足などの詳細理由は区別しない。現時点では主に単体テスト、デバッグ、`Node.transfer()` 接続後の動作確認に使用する。

### 1E.11 docstringの設計記録

`transfer_batch()` のdocstringに、次を記載済みである（Phase番号はdocstringへ記載していない）。

- `form_order_control_batch()` を必ず1回呼ぶ
- Node属性の `order_control_batch_t_trigger_level` と `batch_size` を使用する
- `serve_order_control_batch_service_queue()` を必ず1回呼ぶ
- 形成結果にかかわらず実通過する
- 正常終了時に `incoming_vehicles` を空にする
- 例外時には `incoming_vehicles` を空にしない
- 形成結果と通過Vehicle数を辞書で返す

### 1E.12 テストと回帰結果

#### 新規テストファイル

- `tests_order_control_batch_transfer.py`
- テスト関数数：**17**
- `TESTS` 登録数：**17**
- 成功メッセージ：`Order-control batch transfer tests passed.`

#### テスト範囲（主要）

| 観点 | テスト例 |
|------|----------|
| 形成→実通過の呼出し順 | `test_call_order_count_and_arguments` |
| 各メソッドを必ず1回だけ呼ぶ | 上記、 `test_single_form_and_serve_call_with_multiple_unbatched` |
| Node属性のtrigger levelとbatch_sizeの受け渡し | `test_call_order_count_and_arguments` |
| 形成結果と通過台数の4種類の組合せ | `test_return_*` 4本 |
| `no_trigger_candidate` でも実通過 | `test_serve_called_when_no_trigger_candidate`、`test_no_trigger_transfers_from_existing_queue` |
| `batch_formed` でも実通過 | `test_serve_called_when_batch_formed` |
| 形成成功・0台通過 | `test_batch_formed_zero_transfer_success` |
| 正常終了時の `incoming_vehicles` 整理 | `test_incoming_vehicles_cleared_on_success` |
| 形成時例外で実通過を呼ばない | `test_formation_exception_no_serve_no_clear` |
| 形成時・実通過時の例外オブジェクト維持 | 上記、 `test_serve_exception_no_clear` |
| 例外時の `incoming_vehicles` 維持 | 上記2本 |
| T到着・T+1形成・通過 | `test_timeline_arrival_formation_transfer` |
| N=1形成直後の同呼出し内実通過 | `test_n1_same_call_formation_and_transfer` |
| 既存queueへの新規service unit末尾追加 | `test_existing_queue_plus_new_formation` |

#### 1E.12.1 形成成功・0台通過テスト

`test_batch_formed_zero_transfer_success` で確認済み：

- `batch_size = 2`、A1・A2をBATCH形成
- `out.capacity_in_remain = 0`
- `formation_result = "batch_formed"`、`transferred_vehicle_count = 0`
- A1・A2はlink1上に残る。service unit内に [A1, A2] のFIFO順で残る
- 両Vehicleのbatch assignmentが残る
- 正常終了後の `incoming_vehicles` は空

#### 1E.12.2 回帰テスト結果

Phase 4-6Lの新規17テストはすべて成功済み。実装直後および2件のテストコード修正後、次を再実行し、すべて exit code 0。

- `tests_order_control_batch_transfer.py`
- `tests_order_control_batch_service_queue_transfer.py`
- `tests_order_control_batch_formation_integration.py`
- `tests_order_control_batch_t_trigger_estimation.py`
- `tests_order_exchange_baseline.py`
- `demos_and_examples/example_00en_simple.py`

**baseline：** completed trips 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、delay ratio 0.017、total distance traveled 48000.0 m

**example：** completed trips 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、delay ratio 0.385、total distance traveled 1632250.0 m

既知値と一致し、確認対象の主要指標に回帰は検出されなかった。

### 1E.13 未実装範囲と次工程（Phase 4-6L完了時点の記録）

**4-6L完了時点では未実装だった項目（4-6Mで実装済み。§1F参照）：**

- `Node.transfer()` から `transfer_batch()` を呼ぶBATCH分岐
- `Node.transfer()` 接続後の実シミュレーション時系列テスト
- N=1 BATCHとFCFSのシミュレーション全体での完全同一性

**引き続き未実装：**

- Level 2仮想サービス推定
- trip-end VehicleのBATCH対応
- Time-value Transaction

現行の次工程は **§1F.15** を参照。

### 1E.14 再開時チェックリスト（Phase 4-6L完了時点の記録）

現行の再開チェックリストは **§1F.16** を正とする。以下はPhase 4-6L完了時点の再開情報である。

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| 最新commit | `e9f3ce9` — Phase 4-6Lの `transfer_batch()` 実装・17テスト |
| Phase 4-6M | **§1F参照**（本節作成時点では未着手） |
| `Node.transfer()` | BATCH分岐**未接続**（4-6Mで接続済み） |
| 次に読む実装 | `Node.transfer_batch()`、`Node.form_order_control_batch()`、`Node.serve_order_control_batch_service_queue()` |
| 次に読むテスト | `tests_order_control_batch_transfer.py`、`tests_order_control_batch_service_queue_transfer.py` |
| 次工程 | `Node.transfer()` へのBATCH分岐接続（**4-6Mで完了。§1F**） |

---

## 1F. Phase 4-6M：Node.transfer()へのBATCH分岐接続

本節は、Phase 4-6Lの `transfer_batch()` を `Node.transfer()` から呼び出す接続、接続後の実シミュレーション検証、Vehicle引継ぎ、N=1 BATCHとclearance付きFCFSの完全一致確認を記録する。別担当者または別AIが本メモとリポジトリのみを読んで、BATCH処理がシミュレーション本体にどう接続されたかを正確に理解できることを目的とする。

**位置づけ：**

| Phase | 内容 |
|-------|------|
| **4-6K** | service queueに基づくVehicle実通過（`serve_order_control_batch_service_queue()`） |
| **4-6L** | BATCH形成と実通過の統括メソッド（`transfer_batch()`） |
| **4-6M** | 統括メソッドを `Node.transfer()` へ接続 |

### 1F.1 対象範囲と現在地点

Phase 4-6Mでは、本番コードの変更は `Node.transfer()` 冒頭へのBATCH分岐4行のみである。`transfer_batch()` および配下の形成・実通過メソッドは変更していない。

| 区分 | 状態 |
|------|------|
| **本番コード変更** | `Node.transfer()` へBATCH分岐4行追加のみ（**未commit**） |
| **新規テスト** | `tests_order_control_batch_node_transfer_integration.py`（13テスト、**未commit**） |
| **4-6Lコミット** | `e9f3ce9`（`transfer_batch()` 実装・17テスト） |
| **接続完了** | BATCH Nodeで `transfer_batch()` が1 timestepに1回呼ばれる |
| **未実装** | Level 2、trip-end Vehicle、Time-value Transaction、比較対象Node共通管理、目的地自動検証 |

### 1F.2 Node.transfer()へ追加した分岐

```python
if s.order_control_eligible and s.order_control_type == "batch":
    s.transfer_batch()
    return
```

- 条件は **`order_control_eligible` が True かつ `order_control_type == "batch"`** の両方（`order_control_type` だけでは分岐しない）
- `transfer_batch()` を**1回**呼び、直後に `return` する
- FCFS分岐・標準UXsim transferの本体は変更していない

### 1F.3 分岐位置と処理順序

`Node.transfer()` 冒頭の処理順は次のとおりである。

```
FCFS分岐（order_control_eligible かつ order_control_type == "fcfs"）
    → transfer_fcfs_clearance() → return

BATCH分岐（order_control_eligible かつ order_control_type == "batch"）
    → transfer_batch() → return

標準UXsim transfer（既存処理）
```

FCFS分岐は Phase 4-6M 以前から存在し、**変更していない**。

### 1F.4 BATCH分岐後にreturnする理由

`transfer_batch()` の後に `return` しない場合、同一Node・同一timestepで次の両方が実行されるおそれがある。

1. BATCH処理（`transfer_batch()`）
2. 標準UXsim transfer

同一timestepにBATCHと標準方式の両方でVehicleを移動させないため、`transfer_batch()` 呼出し後に `Node.transfer()` を終了する。

### 1F.5 transfer_batch()の戻り値を使わない理由

`transfer_batch()` は次の辞書を返す。

```python
{
    "formation_result": formation_result,
    "transferred_vehicle_count": transferred_vehicle_count,
}
```

`Node.transfer()` ではこの辞書を受け取らない。

```python
s.transfer_batch()
return
```

理由：

- 必要な交通状態変更は `transfer_batch()` 内部で完了する
- 現在の `Node.transfer()` 呼出し元は辞書を使用しない
- BATCH Nodeだけ `Node.transfer()` が辞書を返すと、FCFS・標準UXsimとの戻り値の一貫性を失う
- BATCH分岐の `Node.transfer()` は従来どおり `None` を返す

### 1F.6 既存メソッドとの責任分担

Phase 4-6Mでは、形成・実通過ロジックを `Node.transfer()` へ重複実装していない。責任分担は次のとおりである（詳細は **§1C・§1D・§1E** を参照）。

| メソッド | 責任 |
|----------|------|
| `form_order_control_batch()` | trigger候補取得、t_trigger推定、候補抽出、inlink候補群順序付け、最大batchサイズN適用、Vehicle assignment、service unit登録 |
| `serve_order_control_batch_service_queue()` | 到着状態確認、Link整合性、route_next_link確認、clearance、inlink全体の物理的先頭、下流空間・各容量条件、Link間移動、residual保持、完了service unit削除、未完了service unit順序維持 |
| `transfer_batch()` | 形成を必ず1回、実通過を必ず1回、正常終了時に `incoming_vehicles` を空にし、結果辞書を返す |
| `Node.transfer()` | order_control設定に応じてFCFS・BATCH・標準UXsimの経路を選ぶ |

### 1F.7 実シミュレーション上の到着・形成・実通過時系列

`World.exec_simulation()` では `Node.transfer()` が `Vehicle.update()` より先に呼ばれる（**§1C.10**）。

実シミュレーションテスト（`test_simulation_timeline_arrival_formation_transfer`）で確認した時系列：

```
timestep T の Node.transfer()
    VehicleはまだNode端への到着登録前 → BATCH形成されない

timestep T の Vehicle.update()
    VehicleがNode端へ到着
    同じNodeの incoming_vehicles へ登録

timestep T+1 の Node.transfer()
    BATCH分岐から transfer_batch() を1回呼ぶ
    BATCHを形成
    同じ transfer_batch() 内で実通過可否を確認
    条件を満たせば同じtimestep T+1 にLink間移動
```

次と整合する。

```
first_transfer_timestep = arrival_timestep + 1
```

形成後に不要な追加1 timestepを待たせず、timestep T+1で実通過できることを確認済みである。

### 1F.8 Node端に残るbatch assignment済みVehicle

対象は、Node端へ到着済みで、現在Node向けbatch assignmentを持ち、正式service queue内のservice unitへ登録済みのVehicleである。

#### 1F.8.1 下流空間・各容量条件によりLink間移動できなかったVehicle

outlink流入容量不足等により、現在timestepにはinlinkからoutlinkへ移動できなかったVehicle（`test_capacity_blocked_batch_vehicle_reregistration`）。

確認済み：

- timestep T+1でBATCH形成
- 同timestepでは未通過、Vehicle本体はinlink上に残る
- batch assignment・service unit内のVehicle列を保持
- `transfer_batch()` 終了直後は `incoming_vehicles` が空
- 同timestep末の `Vehicle.update()` で同じNodeの `incoming_vehicles` へ再登録
- 次timestepに既存service unitのFIFO先頭Vehicleとして再確認
- 新しいbatch IDを付与せず、service unitへ重複登録しない

#### 1F.8.2 clearance未充足で通過しなかったVehicle

`test_service_queue_stop_reregistration` で確認した内容である。B1はservice unitのFIFO先頭として実通過可否を確認された。B1は前方service unitの停止によって未処理だったのではなく、B1自身が異方向切替clearanceを満たさなかったため、当該timestepの実通過処理が終了した。

テスト条件の要点：

- batch ID 0の先頭service unitは `vehicles` が空
- batch ID 1のservice unitにB1が存在し、B1がそのservice unitのFIFO先頭である
- `last_order_control_inlink` は link1、`last_order_control_entry_timestep` は 10
- B1のinlinkは link2、current timestepは 10、`clearance_timesteps` は 1
- B1自身について異方向切替clearanceを確認し、clearance未充足のためB1は通過せず処理が終了する

確認済み：

- 完了済みの空service unitは正式queueから削除された
- B1を含む未完了service unitは正式queueの先頭に残った
- B1のVehicle本体、batch assignment、service unit内の登録を維持した
- `transfer_batch()` 正常終了時に `incoming_vehicles` は空になった
- 同じtimestep末の `Vehicle.update()` で、B1は同じNodeの `incoming_vehicles` へ再登録された
- timestep 12でclearanceを満たし、B1が通過した
- B1へ新しいbatch IDは付与されず、service unitへの重複登録も発生しなかった

後方service unitが未処理となる一般的な停止規則は **§1D** を参照。本節はその一般仕様を Phase 4-6Mの実シミュレーションで直接確認した記録ではない。

**注記：** service unitへ登録済みでも未到着のVehicleは、もともと `incoming_vehicles` に存在しない。未到着Vehicleを「`incoming_vehicles` から削除された後に再登録されるVehicle」として説明しない。

### 1F.9 service unitへ登録されなかった到着済み・未batch Vehicle

対象は、Node端へ到着して `incoming_vehicles` に存在する一方、現在Node向けbatch assignmentを持たず、今回形成されたservice unitへ登録されなかったVehicleである。

| 分類 | 条件・理由 | テスト |
|------|-----------|--------|
| **t_trigger候補範囲外** | `earliest_arrival_timestep > t_trigger`（到着済みでも候補に含まれない） | `test_t_trigger_out_of_range_unbatched_carryover` |
| **方向別N超過** | 同一inlinkの候補がNを超え、FIFO先頭N台のみ登録 | `test_n_exceeded_unbatched_carryover` |
| **形成打切り（他方向）** | trigger方向がN台に達し、他方向Vehicleは未登録 | `test_formation_cutoff_other_direction_unbatched` |

共通の引継ぎ（確認済み）：

- Vehicle本体はinlink上に残る
- 現在Node向けbatch assignmentは付与されない
- residual部分ではない
- 1回の `Node.transfer()` でBATCH形成は1回だけ
- `transfer_batch()` 正常終了時に `incoming_vehicles` から削除
- 同timestep末の `Vehicle.update()` で同じNodeの `incoming_vehicles` へ再登録
- 次timestepでも未batchであり、trigger候補になり得る

### 1F.10 異方向Vehicleの同時到着

3方向同時到着テスト（`test_three_direction_simultaneous_arrival`）と、A1・B1のLevel 0/Level 1比較テスト（`test_a1_b1_two_direction_level0_level1_trigger`）は**目的の異なる別テスト**である。

**3方向同時到着（batch_size=1）：**

- 異なるinlinkからA1・B1・C1を同じtimestepにNode端へ到着
- 保存済みtiebreaker順：A1 → B1 → C1
- A1が最初のtrigger
- 1回の `Node.transfer()` で `form_order_control_batch()` は1回だけ
- A1だけがservice unitへ登録
- B1・C1はtrigger方向がN=1に達したことによる形成打切りで未batchのまま残る
- 同じtimestepに第2・第3のBATCHを形成しない

### 1F.11 Level 0とLevel 1のt_trigger比較

A1・B1テスト（`test_a1_b1_two_direction_level0_level1_trigger`）の条件と結果：

| 項目 | 値 |
|------|-----|
| A1・B1のNode初回到着timestep | 10 |
| A1の形成・実通過timestep | 11 |
| batch_size | 1 |
| clearance_timesteps | 1 |
| A1通過後の `last_order_control_inlink` | A1のinlink（link1） |
| A1通過後の `last_order_control_entry_timestep` | 11 |
| B1のLevel 0 t_trigger | 11 |
| A1通過後のclearance下限 | 13（`11 + 1 + 1`） |
| B1のLevel 1 t_trigger | 13（`max(11, 13)`） |

B1はA1と異なるinlinkに属するため、異方向切替clearanceが必要である。Level 1では最新の直近通過状態とclearanceを反映し、Level 0より後ろのt_triggerになり得る。Level 2は未実装であり、既存service queue全体の仮想処理結果までは反映していない。

### 1F.12 snapshot estimated arrivalとの関係

**earliest_arrival_timestep**（Link進入時に記録、候補包含条件 `earliest_arrival_timestep <= t_trigger` に使用）と、**snapshot estimated arrival**（BATCH形成時点の位置からinlink終端までの残距離÷自由流速度で推定、trigger方向以外のinlink候補群の順序付けに使用）は別概念である（**§6・§1C.5**）。

Phase 4-6Mではsnapshot estimated arrivalの計算を重複実装・重複テストせず、`tests_order_control_batch_candidate_group_ordering.py` を回帰テストとして実行し、接続後も成功を確認した。

### 1F.13 N=1 BATCHとclearance付きFCFSの比較

`test_n1_batch_vs_fcfs_equivalence` で、次の条件で完全一致を確認した。

| 項目 | BATCH | FCFS |
|------|-------|------|
| batch_size / type | 1、level 1 | — |
| order_control_type | `"batch"` | `"fcfs"` |
| clearance_timesteps | 1（共通） | 1（共通） |
| ネットワーク・OD・seed・容量 | 同一 | 同一 |

**比較シナリオ：** 2 inlinkからA1/B1（departure 0）、A2/B2（20）、A3/B3（40）の6台。方向切替とclearance待機が実際に発生する。

**Vehicle単位の比較（全6台で完全一致）：**

- Node端への初回到着時刻
- outlinkへの初回進入timestep（各timestepの `exec_simulation` 前後で `previous_link is not out and vehicle.link is out` を検出。`veh.x == 0` には依存しない）
- outlink進入Vehicle順序、通過inlink順序
- trip終了timestep（`state == "end"` になった初回timestep）

**全Vehicleの記録・完了保証：**

- BATCH・FCFS双方で全6台のoutlink進入timestepとtrip終了timestepが記録されたことを明示確認
- 全6台がtripを完了したことを確認（`completed == len(vehicle_names)`）
- 記録欠落によるNone同士の偽陽性を防止

**Node状態：**

各timestepの `(timestep, last_order_control_inlink_name, last_order_control_entry_timestep)` 履歴をLink名で比較。通過inlink列から方向切替回数を算出し一致を確認。異方向通過間で `current_pass_timestep - previous_pass_timestep > clearance_timesteps` となることを確認し、少なくとも1回のclearance待機を保証。

**集計値（一致）：** completed trips、total travel time、average travel time。独自の誤った距離推定（`travel_time * 20`）は使用せず、N=1比較からtotal distanceは除外。baseline・exampleでは従来どおり既存出力でtotal distanceの既知値一致を確認。

**結果：** 最初の不一致はなかった。

### 1F.14 テストと回帰結果

**新規テストファイル：** `tests_order_control_batch_node_transfer_integration.py`（テスト関数13件、`TESTS` 登録13件）

**成功メッセージ：** `Order-control batch Node.transfer integration tests passed.`

| テスト関数 | 確認範囲 |
|-----------|---------|
| `test_batch_node_calls_transfer_batch_once` | BATCH分岐 |
| `test_fcfs_node_calls_fcfs_once` | FCFS分岐維持 |
| `test_standard_node_eligible_false` / `test_standard_node_type_none` | 標準UXsim分岐維持 |
| `test_simulation_timeline_arrival_formation_transfer` | T末到着→T+1形成・実通過 |
| `test_capacity_blocked_batch_vehicle_reregistration` | 容量不足Vehicleの再登録 |
| `test_service_queue_stop_reregistration` | clearance未充足Vehicleの再登録とclearance充足後の通過 |
| `test_t_trigger_out_of_range_unbatched_carryover` | t_trigger候補範囲外Vehicleの引継ぎ |
| `test_n_exceeded_unbatched_carryover` | N超過Vehicleの引継ぎ |
| `test_formation_cutoff_other_direction_unbatched` | 形成打切りによる他方向Vehicleの引継ぎ |
| `test_three_direction_simultaneous_arrival` | 3方向同時到着 |
| `test_a1_b1_two_direction_level0_level1_trigger` | Level 0/Level 1 t_trigger比較 |
| `test_n1_batch_vs_fcfs_equivalence` | N=1 BATCH・FCFS完全一致 |

**回帰テスト：** 新規13テスト、指定既存回帰テスト21ファイル、exampleがすべて exit code 0。N=1比較テストのレビュー修正後も、新規テスト・主要回帰テスト・baseline・exampleを再実行し成功。

**baseline（既知値と一致）：** completed trips 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、delay ratio 0.017、total distance traveled 48000.0 m

**example（既知値と一致）：** completed trips 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、delay ratio 0.385、total distance traveled 1632250.0 m

確認対象の主要指標に回帰は検出されなかった。

### 1F.15 未実装範囲と次工程

**Phase 4-6Mで実装・確認済み（未実装項目に含めない）：**

- `Node.transfer()` へのBATCH分岐
- 実シミュレーション上の到着・形成・実通過時系列
- Node端に残るVehicleの次timestepへの再登録
- N=1 BATCHとclearance付きFCFSの完全一致

**引き続き未実装：**

- Level 2仮想サービス推定
- Level 2 unresolved時のLevel 1 fallback接続
- trip-end VehicleのBATCH service unit対応
- Time-value Transaction
- 比較対象Node共通管理、目的地自動検証、taxi mode向け動的dest検証

**次工程候補（確定していない）：**

1. Level 2仮想サービス推定の設計
2. Level 2 unresolved時のLevel 1 fallback
3. 複数ネットワーク・複数OD・右左折あり条件でのBATCH動作確認
4. Nとt_trigger levelの感度分析設計
5. trip-end Vehicle対応の必要性再検討
6. Time-value Transactionへの接続設計

### 1F.16 再開時チェックリスト

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| 最新commit | `e9f3ce9` — Phase 4-6Lの `transfer_batch()` 実装・17テスト・正式Markdown記録 |
| Phase 4-6M | `Node.transfer()` へのBATCH分岐実装、新規13テスト・回帰確認済み。**本Markdown更新時点では未commit** |
| 変更中ファイル | `uxsim/uxsim.py`、`tests_order_control_batch_node_transfer_integration.py`、本正式Markdown 2ファイル |
| `Node.transfer()` | BATCH分岐**接続済み** |
| 次に読む実装 | `Node.transfer()`、`Node.transfer_batch()`、`Node.form_order_control_batch()`、`Node.serve_order_control_batch_service_queue()` |
| 次に読むテスト | `tests_order_control_batch_node_transfer_integration.py`、`tests_order_control_batch_transfer.py`、`tests_order_control_batch_service_queue_transfer.py` |
| 次工程候補 | Level 2仮想サービス推定、複数ネットワーク条件での動作確認、感度分析設計、Time-value Transaction接続設計 |

> **§1G.15・§1G.16はPhase 4-6N診断・比較フェーズの記録である。** 現行の訪問状態設計は **§1H** を正とする。

---

## 1G. Phase 4-6N：比較テストとNode再訪状態の診断

本節は、Phase 4-6M完了後に実施した route_next_link 参照順修正、clearance=0での3方式比較、high-demandでのprefix violation再現・原因診断、Node再訪の有無調査を記録する。別担当者または別AIが本メモとリポジトリのみを読んで、現時点の課題と次工程を正確に理解できることを目的とする。

**位置づけ：** Phase 4-6Nは性能最適化フェーズではなく、**比較基準の確立**と**Node再訪に対応していないorder-control状態設計の問題発見**フェーズである。

### 1G.1 対象範囲と現在地点

| Phase | 内容 | 状態 |
|-------|------|------|
| **4-6N（一部）** | `serve_order_control_batch_service_queue()` のroute_next_link参照順修正 | commit済み（`05fa2d1`） |
| **4-6N（一部）** | clearance=0比較テスト3本 | commit済み（`f339b88`） |
| **4-6N（一部）** | 比較・Node再訪診断の正式記録 | commit済み（`c06936c`） |
| **4-6N（診断）** | high-demand prefix violation再現・lifecycle診断・Node再訪診断 | commit済み（`0e35799`。`diagnostics/order_control/`） |
| **4-6N（設計）** | Node訪問単位の共通状態設計 | **§1H** に記録済み。基盤（4-6O）・到着記録（4-6P）は実装済み |
| **4-6N（未完了）** | high-demand再実行（BATCH形成の参照先変更は Phase 4-6R で完了。**§1H.21**） |

**ブランチ：** `feature/intersection-order-control`

**§1G記録時点の最新commit：** `0e35799`（診断スクリプト分離）。訪問状態設計は **§1H** を参照。

**Phase 4-6M：** `b03538c`

**§1Gで判明した課題（§1Hで設計対応）：** Node名keyのみのorder-control状態では訪問を区別できない。BATCHではprefix violation、FCFSでは過去到着時刻の再利用可能性。

### 1G.2 未到着Vehicleのroute_next_link参照順修正

**commit：** `05fa2d1`

**修正前：**

```
service unitのFIFO先頭Vehicleを取得
    ↓
route_next_linkを参照
    ↓
incoming_vehiclesへの存在を確認
```

**修正後：**

```
service unitのFIFO先頭Vehicleを取得
    ↓
incoming_vehiclesへの存在を確認
    ↓
未到着なら正常な待機として終了
    ↓
到着済みならservice unitとの整合性を検証
    ↓
route_next_linkを参照
```

**理由：**

- BATCHはNode端未到着Vehicleをservice unitへ登録できる（§1C.4、§1D.5）。
- 未到着Vehicleでは `route_next_link_choice()` がまだ実行されず、`route_next_link` 属性が存在しない場合がある（`Vehicle.update()` は `Node.transfer()` より後に実行される。§1E.7）。
- 未到着は正常状態であり、AttributeErrorにしてはいけない。
- 到着済みで `route_next_link=None` は重大不整合なので、既存どおり `ValueError` とする（§1D.14）。

**回帰テスト：** `test_not_arrived_without_route_next_link_attribute`（`tests_order_control_batch_service_queue_transfer.py`）

### 1G.3 Clearance=0比較テスト（commit済み）

**commit：** `f339b88`

Node再訪状態修正**前**の基準値として、次の3テストを追加した。いずれも性能優劣をassertするテストではない。

| # | ファイル | ネットワーク |
|---|----------|-------------|
| 1 | `tests_order_control_batch_vs_fcfs_vs_uxsim_standard_medium_network.py` | medium corridor |
| 2 | `tests_order_control_batch_vs_fcfs_vs_uxsim_standard_grid_network.py` | unsignalized 6×6 grid |
| 3 | `tests_order_control_batch_vs_fcfs_vs_signalized_uxsim_standard_grid_network.py` | 固定2相信号 6×6 grid |

**共通BATCH設定：**

- `batch_size = 10`
- `order_control_batch_t_trigger_level = 1`（**Level 1は暫定比較**。研究の通常方式はLevel 2→Level 1→Level 0 fallback）
- `clearance_timesteps = 0`

**signalized UXsim設定（テスト3）：** 内部grid Node 36個に `signal=[60, 60]`、phase 0=東西、phase 1=南北、offset=0。外部OD Nodeは非信号。FCFS・BATCHケースのnetwork・需要はunsignalized gridケース（テスト2）と同一。

### 1G.4 Medium network比較結果

| 項目 | UXsim standard | FCFS c=0 | BATCH L1 c=0 N=10 |
|------|----------------|----------|-------------------|
| completed trips | 383 / 500 | 383 / 500 | 383 / 500 |
| completed ratio | 0.766 | 0.766 | 0.766 |
| total travel time | 53941.0 s | 56257.0 s | 56276.0 s |
| average travel time | 140.8 s | 146.9 s | 146.9 s |
| average delay | 11.2 s | 17.3 s | 17.3 s |
| delay ratio | 0.080 | 0.118 | 0.118 |
| total distance | 992850.0 m | 992850.0 m | 992850.0 m |

**BATCH / FCFS：** average travel time ratio **1.0003**、total travel time ratio **1.0003**、total travel time difference **+19.0 s**（BATCH−FCFS）、average travel time difference 約 **+0.05 s/完了Vehicle**、total distance ratio **1.0**。

**解釈：** BATCHとFCFSはほぼ同等。丸め前ではBATCHがごくわずかに長い。性能優劣のassertは行っていない。

### 1G.5 Unsignalized grid比較結果

条件：6×6 grid、1000 Vehicle、departure 0–500、TMAX=5000、eligible Node 36、単車線、同一network・需要・seed。

| 項目 | Unsignalized UXsim | FCFS c=0 | BATCH L1 c=0 |
|------|-------------------|----------|--------------|
| completed trips | 1000 / 1000 | 1000 / 1000 | 1000 / 1000 |
| completed ratio | 1.000 | 1.000 | 1.000 |
| total travel time | 165917.0 s | 167772.0 s | 167872.0 s |
| average travel time | 165.9 s | 167.8 s | 167.9 s |
| average delay | 1.3 s | 3.2 s | 3.3 s |
| delay ratio | 0.008 | 0.019 | 0.019 |
| total distance | 3292000.0 m | 3292000.0 m | 3292000.0 m |

**BATCH / FCFS：** average travel time ratio **1.0006**、total travel time ratio **1.0006**、average travel time difference **+0.100 s**、total travel time difference **+100.0 s**、completed trips difference **0**、total distance ratio **1.0**。

**解釈：** clearance=0ではBATCHとFCFSはほぼ同等。BATCHがごくわずかに長い。unsignalized UXsimにはFCFS・BATCHの順序制約がないため、研究上の主要な信号制御比較ではなく実装sanity checkとして扱う。

### 1G.6 固定2相信号grid比較結果

FCFS・BATCHのnetwork・制御条件は §1G.5 のunsignalized gridケースと同一（信号なし + order control）。

| 項目 | Signalized UXsim | FCFS c=0 | BATCH L1 c=0 |
|------|-----------------|----------|--------------|
| completed trips | 1000 / 1000 | 1000 / 1000 | 1000 / 1000 |
| total travel time | 335835.0 s | 167772.0 s | 167872.0 s |
| average travel time | 335.8 s | 167.8 s | 167.9 s |
| average delay | 171.2 s | 3.2 s | 3.3 s |
| total distance | 3498400.0 m | 3292000.0 m | 3292000.0 m |

**FCFS / signalized：** average travel time ratio 約 **0.500**（Step 4C記録を再現）。

**BATCH / signalized：** average travel time ratio 約 **0.500**。

**BATCH / FCFS：** average travel time ratio **1.0006**、total travel time difference **+100.0 s**、average travel time difference **+0.100 s**。

**解釈：** 固定2相信号による待ちが大きい。FCFS・BATCHは信号待ちがないため約半分の平均旅行時間。FCFS・BATCHの結果はunsignalized grid比較と同一。BATCHがFCFSより優位とは確認されていない。

### 1G.7 Clearance=0比較の現時点の解釈

- medium・gridの両方でBATCHとFCFSはほぼ同等。いずれもBATCHがごくわずかに長い。
- clearance=0では方向切替による無通過時間がない。
- BATCHによる同方向集約の主要な利益が現れにくい。
- service unit順や未到着Vehicle待ちによる小さな不利益が現れた可能性があるが、原因をこの比較だけで確定しない。
- 性能優劣をassert条件としていない。
- 比較テストは **Node再訪状態修正前の基準値** である（commit `f339b88`）。

### 1G.8 Clearance=1 high-demand比較の失敗（診断スクリプトへ分離）

**診断スクリプト：** `diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py`（`0e35799` commit済み）

診断スクリプトの目的、既知の非zero終了、実行方法については `diagnostics/order_control/README.md` を参照。

**条件：** 6×6 grid、5000台・10000台、内部grid `clearance=1`、signalized all-red `signal=[60, 1, 60, 1]`（phase 0=東西方向が青、phase 1=全赤、phase 2=南北方向が青、phase 3=全赤）、staggered offset、BATCH `clearance=1`、N=10、Level 1（Level 2実装前の暫定比較設定）。

**5,000台BATCH実行中の例外：**

```
Batch assignment prefix violation on inlink h_5_3_4
at node g_5_4:
assigned vehicle veh_1952 appears after an unassigned vehicle.
```

5,000台で停止したためBATCHの交通結果は取得できず、10,000台BATCHは未実行。

**既存signalized all-red vs FCFSテストは正常再実行：**

- 5,000台：FCFS / signalized all-red average travel time ratio ≈ **1.386**
- 10,000台：FCFS / signalized all-red average travel time ratio ≈ **1.142**

この時点ではclearance=1によるservice queue滞留が原因候補だったが、後続のclearance=0診断（§1G.9）で必要条件ではないことが判明した。

### 1G.9 Clearance=0 high-demandでの再現（診断スクリプトへ分離）

**診断スクリプト：** `diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py`（`0e35799` commit済み）

診断スクリプトの目的、既知の非zero終了、実行方法については `diagnostics/order_control/README.md` を参照。

**条件：** 5,000 Vehicle、departure 0–500、TMAX=30000、clearance=0、BATCH Level 1、N=10。10,000台は未実行。

**W.T=605での例外：**

```
Batch assignment prefix violation on inlink v_5_4_1
at node g_4_1:
assigned vehicle veh_1619 appears after an unassigned vehicle.
```

**例外時の状態：**

| 項目 | 値 |
|------|-----|
| inlink `v_5_4_1` [0] | veh_1651、unassigned、x=45.0 |
| inlink `v_5_4_1` [1] | veh_1619、assigned batch_id=318、x=20.0 |
| veh_1619 in `g_4_1.incoming_vehicles` | False |
| `g_4_1.order_control_batch_service_queue` | 空 |

**結論：** clearance=0でも再現したため、clearance=1によるqueue滞留は必要条件ではない。

この時点では、高需要下の複数BATCH・assignment蓄積が原因候補として考えられた。

その後の§1G.10・§1G.11の診断により、第1回訪問のassignment残存とNode再訪の組合せが根本原因と判明した。高需要そのものを根本原因と断定しない。高需要は、Node再訪と過去状態漏出を発見しやすくした再現条件として位置づける。

### 1G.10 Batch ID 318 lifecycle診断（診断スクリプトへ分離）

**診断スクリプト：** `diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py`（`0e35799` commit済み）

診断スクリプトの目的、既知の非zero終了、実行方法については `diagnostics/order_control/README.md` を参照。

**対象：** Node `g_4_1`、Vehicle `veh_1619`、batch ID **318**

#### 1G.10.1 時系列

| W.T | イベント |
|-----|---------|
| **583** | veh_1619が `h_4_2_1` からg_4_1へ到着。trigger=veh_1619、t_trigger=584。batch 318発行（Vehicle=[veh_1619]のみ）。assignment 318登録。service unit 318を正式queueへ追加。**同一timestep**にveh_1619がg_4_1を通過（`h_4_2_1`→`v_4_5_1`）。veh_1619をservice unitからpop。空になったservice unit 318を正式queueから**正常削除**。 |
| 通過後 | service unit 318は存在しない。**Vehicle側assignment 318は残る。** |
| **604** | veh_1619が `v_5_4_1` へ進入。別inlinkからg_4_1へ**2回目の接近**。 |
| **605** | `v_5_4_1`上で、unassignedのveh_1651の後方に、過去assignment 318を持つveh_1619が存在。**prefix violation。** |

#### 1G.10.2 判定

**service unitの誤削除ではない。**

支持された仮説：**第1回訪問のbatch assignmentがVehicle側に残り、同じNodeへの第2回接近時にも現在有効なassignmentとして解釈された。**

根拠：

- veh_1619は第1回訪問で実際に通過した。
- service unit 318は正常完了・正常削除された。
- Vehicle側assignmentだけが残った。
- veh_1619は後に同じNodeへ再接近した。
- prefix検証はNode名keyの過去assignmentを現在訪問のassignmentとして扱った（§1C.4、§1C.3.1）。

### 1G.11 UXsim・FCFS・BATCHのNode再訪診断（診断スクリプトへ分離）

**診断スクリプト：** `diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py`（`0e35799` commit済み）

診断スクリプトの目的、既知の非zero終了、実行方法については `diagnostics/order_control/README.md` を参照。

**条件：** 5,000 Vehicle、6×6 grid、departure 0–500、同一vehicle_plans、signalized UXsim / FCFS c=0 / BATCH c=0 N=10 Level 1。

#### 1G.11.1 T≤605の比較

| 指標 | Signalized | FCFS | BATCH |
|------|-----------|------|-------|
| 再接近Vehicle数 | 17 | 10 | 12 |
| 再接近Vehicle割合 | 17 / 4207（約0.40%） | 10 / 4442（約0.23%） | 12 / 4412（約0.27%） |
| 再接近event数 | 17 | 10 | 12 |
| 再接近Node数 | 9 | 10 | 8 |
| 最大接近回数 | 2 | 2 | 2 |
| 再通過Vehicle数 | 0 | 0 | 0 |

**分母の意味：** 上記割合の分母は、各方式についてT≤605までに1回以上Nodeへ接近したVehicle数である（全5,000台を分母とする割合ではない）。

T≤605では再接近はあるが再通過は0（2回目の通過完了前または観測期間内）。BATCHはW.T=605で既知のprefix violationにより停止。

#### 1G.11.2 全期間結果（signalized・FCFSのみ）

| 指標 | Signalized | FCFS |
|------|-----------|------|
| 再接近Vehicle数・割合 | 2135 / 5000（**42.7%**） | 1152 / 5000（**23.0%**） |
| 再接近event数 | 8152 | 3041 |
| 再通過Vehicle数・割合 | 2135（42.7%） | 1152（23.0%） |
| 再通過event数 | 8152 | 3041 |

BATCHはW.T=605までの結果のみ。全期間結果は未取得。

#### 1G.11.3 Node再訪に関する結論

- **Node再訪はBATCH固有ではない。** signalized UXsimとFCFSでも多数発生する。
- 現在のUXsimの動的・確率的・逐次的な経路選択では、grid上でサイクルが発生し得る。Node再訪をUXsimの誤りと断定しない。
- BATCHだけが再訪を大幅に増やしているとは、T≤605の結果からは言えない（観測期間がBATCHだけ短い点に注意）。
- **BATCH固有の問題は再訪そのものではなく、過去のNode訪問のassignmentを現在のNode訪問のassignmentとして扱う状態管理である。**
- FCFSも初回Node到着時刻を現在の順序制御へ使っているため、Node再訪時に過去訪問の到着時刻を参照する可能性を別途検討する必要がある。

**veh_1619のg_4_1再接近（T≤605）：** signalized=False、FCFS=False、**BATCH=True**（方式間で経路が異なるため、veh_1619個別の再接近がBATCH固有とは限らない。FCFSでも別Vehicleがg_4_1再接近を確認）。

### 1G.12 根本原因

現在、主に次の制御状態が **Node名をkey** として記録されている。

- `order_control_node_arrival_times`
- `order_control_node_arrival_tiebreakers`
- `order_control_earliest_arrival_timesteps`
- `order_control_batch_assignments`

Node名だけでは、第1回訪問・第2回訪問・それ以降の訪問を区別できない。

その結果：

- 第1回訪問で作成した制御状態がVehicle側に残る。
- 同じNodeへの再訪時に過去状態を現在状態として解釈する。
- BATCHではprefix violationとして表面化した。
- FCFSでも優先順に古い到着時刻を使う可能性がある。

今回のprefix violationは、assignmentだけの局所的な問題ではなく、**Nodeへの訪問単位を区別していないorder-control状態設計の問題**である。assignment削除だけを確定修正としない。

### 1G.13 Node再訪対応の設計要件（確定実装ではない）

#### 1G.13.1 各Node訪問を区別する

同じVehicleが同じNodeを複数回訪問した場合、各訪問を別の制御単位として扱う必要がある。

設計候補概念：`node_name` + `visit_id`（具体的なデータ構造は後続設計レビューで確定）。

#### 1G.13.2 現在訪問の制御状態と履歴を分離

**現在訪問の制御に必要な情報：** 現在訪問のinlink、現在訪問のearliest arrival timestep、現在訪問のNode端到着時刻、現在訪問のtiebreaker、現在有効なbatch assignment。

**履歴・分析用情報：** 初回Node到着時刻、過去の各訪問、過去のinlink・outlink、過去のbatch ID、過去の通過時刻。

初回到着履歴を削除するのではなく、現在訪問の制御状態と分離する。

#### 1G.13.3 訪問開始

Vehicleが新しいLinkへ進入し、そのLinkの `end_node` へ向かい始めた時点を、当該Nodeへの新しい訪問開始候補とする。

訪問開始時には：

- 新しい訪問を識別する状態を作る
- 今回のinlinkを記録する
- earliest arrival timestepを計算する
- 今回訪問用の到着時刻を**未記録を表す初期状態**にする
- 今回訪問用のtiebreakerを**未記録を表す初期状態**にする
- 今回訪問用のbatch assignmentを**assignmentなしを表す初期状態**にする

`None` を格納するか、キーを作らないか等の実装形式は後続設計で確定する。

#### 1G.13.4 訪問終了

VehicleがNodeを実際に通過したとき：

- 現在訪問を完了状態にする
- 現在訪問で有効だったassignmentを終了する
- 必要な情報を履歴として保存する
- 次回同じNodeへ接近した場合は新しい訪問として扱う

#### 1G.13.5 FCFS

FCFSの順序付けには、初回訪問の到着時刻ではなく、**現在訪問のNode端到着時刻とtiebreaker**を使用する必要がある。

#### 1G.13.6 BATCH

BATCHでは、少なくとも次を同じ訪問単位へ関連付ける必要がある：earliest arrival timestep、trigger候補、t_trigger、候補抽出、batch assignment、service unit、prefix検証、実通過、訪問完了。service unitへ登録した訪問とVehicleの現在訪問が一致することを確認できる設計が必要。

#### 1G.13.7 経路選択（今回は変更しない）

次は行わない：Node再訪の禁止、過去訪問Nodeへ向かうLinkの除外、`route_next_link_choice()` の変更、UXsim標準の動的経路選択の変更。

理由：Node再訪はUXsim標準とFCFSでも発生している。経路選択を変更すると比較基準そのものが変わる。まずorder-control側でNode再訪を正常に扱う設計を行う。

### 1G.14 現在未完了の比較

Node再訪対応前に、以下を**取得済みと記載しない。**

| 比較 | 状態 |
|------|------|
| high-demand 5,000台 BATCH clearance=0 | prefix violationで停止 |
| high-demand 10,000台 BATCH clearance=0 | 未実行 |
| high-demand 5,000台 BATCH clearance=1 | prefix violationで停止 |
| high-demand 10,000台 BATCH clearance=1 | 未実行 |

### 1G.15 次工程（合意した作業順）

1. route_next_link確認順修正を独立commit — **完了**（`05fa2d1`）
2. 成功済みclearance=0比較3本を独立commit — **完了**（`f339b88`）
3. 比較結果とNode再訪診断結果を正式Markdownへ記録 — **完了**（`c06936c`）
4. 診断スクリプトを通常テストと分離して保存 — **完了**（`0e35799`）
5. Node訪問単位の状態設計を作成 — **完了**（**§1H** として正式記録。本Markdown更新時点では未commit）
6. 設計レビュー
7. FCFS・BATCHの順で訪問対応を実装
8. 小規模再訪テスト
9. 5,000台clearance=0を再実行
10. 5,000台・10,000台clearance=1を再実行

### 1G.16 再開時チェックリスト

| 項目 | 値 |
|------|-----|
| ブランチ | `feature/intersection-order-control` |
| §1G記録時点の最新commit | `0e35799` |
| 直前commit | `c06936c` |
| その前 | `f339b88` |
| Phase 4-6M | `b03538c` |
| Step 1 | 完了・commit済み（`05fa2d1`） |
| Step 2 | 完了・commit済み（`f339b88`） |
| Step 3 | 完了・commit済み（`c06936c`） |
| Step 4 | 完了・commit済み（`0e35799`） |
| Step 5 | 設計記録完了（**§1H**。本Markdown更新時点では未commit） |
| 次は | §1H設計レビュー → Phase 4-6O |
| commit済み | route_next_link確認順修正、clearance=0比較テスト3本、正式記録（`c06936c`）、診断スクリプト分離（`0e35799`） |
| 未commit | 本Markdown更新2ファイル（§1H追加） |
| 現在の結論 | Node再訪はUXsim標準・FCFS・BATCHで発生。BATCH prefix violationは過去assignment残存とNode再訪の組合せ。service unit誤削除ではない。FCFSも過去到着状態の再利用可能性あり。 |

**次に読む実装：**

- `Vehicle.record_order_control_node_first_arrival()`
- `Vehicle.record_order_control_earliest_arrival_timestep_for_current_link()`
- `Vehicle.update()`、`Vehicle.route_next_link_choice()`
- `Node.transfer_fcfs_clearance()`
- `Node.form_order_control_batch()`、`Node.get_order_control_batch_candidates_by_inlink()`
- `Node.serve_order_control_batch_service_queue()`

**次に読む診断（`diagnostics/order_control/`。`0e35799` commit済み）：**

- `diagnostics/order_control/README.md`
- `diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py`
- `diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py`
- `diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py`
- `diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py`

診断スクリプトの目的、既知の非zero終了、実行方法については `diagnostics/order_control/README.md` を参照。

**次工程：** §1H設計レビュー → Phase 4-6O（現在訪問状態の共通基盤）。詳細は **§1H.17**。

---

## 1H. Node再訪に対応するFCFS・BATCH共通訪問状態設計

本節は、§1Gで判明したNode名keyのみのorder-control状態設計の問題に対し、FCFS・BATCHで共通利用する**Node訪問単位の制御状態**をどう導入するかを記録する。§1Gの診断結果・根本原因の詳細は **§1G** を参照。本節は**設計記録**である。Phase 4-6O（基盤）・Phase 4-6P（到着記録）は **§1H.18**・**§1H.19.7** で実装済み。FCFSの参照先変更は Phase 4-6Q（**§1H.20** で実装済み）。BATCH形成の参照先変更は Phase 4-6R（**§1H.21** で実装済み）。

### 1H.1 設計目的と対象範囲

**背景（§1Gより）：** Node再訪はsignalized UXsim・FCFS・BATCHで発生する。現在の `order_control_node_arrival_times`、`order_control_node_arrival_tiebreakers`、`order_control_earliest_arrival_timesteps`、`order_control_batch_assignments` はいずれもNode名をkeyとし、第1回訪問と第2回以降の訪問を区別できない。BATCHでは過去assignmentが再訪時に現在有効なassignmentとして扱われ、prefix violationとして表面化した。FCFSでも初回訪問の到着時刻を再訪時の順序制御に使う可能性がある（現行 `transfer_fcfs_clearance()` は `order_control_node_arrival_times` を参照）。

**本設計の目的：**

- FCFS・BATCHで共通のNode訪問状態を導入する。
- **現在訪問の制御状態**と**過去の分析用履歴**を分離する。

**本設計の対象外（変更しない）：**

- `route_next_link_choice()` の選択方式
- 確率的経路選択、渋滞状況に応じた経路選好更新
- UXsim標準の経路選択挙動全般

**本設計で新たに追加しない：**

- 過去訪問Nodeへ戻るLinkを候補から除外する処理
- Node再訪・サイクルを禁止する処理

（これらの禁止処理は現在のUXsimに存在しない。）

### 1H.2 Node訪問の定義

| 用語 | 定義 |
|------|------|
| **訪問開始** | Vehicleが新しいLinkへ進入し、そのLinkの `end_node` へ向かい始めた時点 |
| **Node端到着** | `Vehicle.update()` でLink終端への到達が判定され、`route_next_link_choice()` 実行後に `end_node.incoming_vehicles` へ登録された時点 |
| **Node通過** | Vehicleがinlinkからoutlinkへ実際に移動した時点 |
| **訪問終了** | Node通過が成功した時点 |

**同一訪問の継続：** Node端での通過待ち、clearance待機、下流容量不足、`incoming_vehicles` への次timestepでの再登録は、いずれも**同じ訪問**の継続である。

**新しい訪問：** Node通過後に新しいLinkへ進入した場合、または過去に訪問したNodeへ別のLinkから再接近した場合。

**明確化：** `incoming_vehicles` への再登録だけでは、新しい訪問を開始しない。

### 1H.3 訪問識別子

**現行設計方針：**

- Vehicleごとに単調増加する整数 **`visit_id`** を用いる。
- **`visit_id` はすべてのLink進入を数える番号ではない。** 次の条件を満たすNodeへ向かうLinkへ進入した場合だけ1増やす。
  - `end_node.order_control_eligible is True`
  - `end_node.order_control_type != "none"`
- したがって **`visit_id` はVehicleごとのorder-control対象Node訪問番号** として扱う。
- 同一訪問中は変更しない。`incoming_vehicles` への再登録では増やさない。
- 同じNodeへの再訪では新しい `visit_id` になる。
- 「次に発行する訪問番号」という別属性は設けない。Vehicle属性 `order_control_visit_id` が最後に発行した値を保持する（初期値 `0`）。

**制御上の訪問識別（概念）：** `Vehicle` + `Node` + `visit_id`

**`visit_id` はbatch IDではない。** 訪問はBATCH形成前から存在し、FCFSでも共通利用する。batch IDだけでは訪問を識別できない。

### 1H.4 Vehicleの現在訪問状態

Vehicleは、現在向かっているorder-control対象Nodeについて、**現在訪問状態を1件だけ**保持する。

**必要な基本情報：**

| 項目 | 用途 |
|------|------|
| `visit_id` | 訪問識別 |
| 訪問先Node | 対象Node |
| inlink | 現在訪問の進入Link |
| earliest arrival timestep | BATCH候補包含・形成 |
| Node端到着時刻 | FCFS順序付け |
| 到着tiebreaker | FCFS同時到着の順序 |
| 現在訪問のBATCH assignment | 形成・prefix検証・実通過 |

order-control対象外Nodeへの訪問状態は**作成しない**。新しく進入したLinkの `end_node` がorder-control対象外の場合は `order_control_current_visit = None` とし、`order_control_visit_id` は増やさない（直前の対象Node訪問状態を対象外Link上に残さない）。

**データ構造（決定済み）：** Vehicle上の1つの辞書 `order_control_current_visit`（未訪問時は `None`）。Vehicle属性 `order_control_visit_id`（初期値 `0`）と併用する。

**辞書キー（第一案）：** `visit_id`、`node`、`inlink`、`earliest_arrival_timestep`、`arrival_time`、`arrival_tiebreaker`、`batch_assignment`。`node` と `inlink` はオブジェクト参照とする。

### 1H.5 現在制御状態と分析用履歴の分離

| 区分 | 内容 | 方針 |
|------|------|------|
| **常に保持** | 現在訪問の制御状態 | FCFS・BATCHの現在制御に使用 |
| **初回分析履歴（既存属性を維持）** | `order_control_node_arrival_times`、`order_control_node_arrival_tiebreakers`、`order_control_earliest_arrival_timesteps` | 同一Vehicle・同一Nodeの**初回値のみ**保存。再訪時に上書きしない。FCFS・BATCHの現在制御には使わない |
| **過去batch ID** | 研究分析用 | 履歴として保持。現在有効なassignmentとは分離。具体的な利用方法は未確定 |

**段階移行（`order_control_earliest_arrival_timesteps`）：** 移行完了後の最終方針は上表のとおり初回のみ記録とする。Phase 4-6Oでは既存BATCH挙動を変えないため、同辞書は**現行どおり再訪時にも上書き**する（FCFS・BATCHは引き続き既存辞書を参照）。初回分析履歴としての上書き禁止へ切り替えるのは Phase 4-6R（BATCH参照先を現在訪問状態へ変更）と同時とする（**§1H.13**、**§1H.14**）。

**分析データの基本方針：**

- 加工済みの平均値等をそのまま保存しない。
- 後から必要な指標を算出できる**基本的な事実**を保存する。
- Vehicleオブジェクトそのものではなく、Vehicle IDまたはVehicle名と `visit_id` を保存する。

**将来再構成用の基本情報候補：** batch ID、Node、inlink、形成timestep、Vehicle IDまたはVehicle名、`visit_id`、service unit内の順序。

**保留：** 詳細な全訪問履歴の保存範囲、BATCH形成履歴の具体的な項目・格納先。診断専用の詳細履歴は通常実行では保持しない。

### 1H.6 訪問開始処理

Link進入時の処理は、研究対象Vehicleの5つのLink進入経路（`Node.generate`、標準 `Node.transfer`、FCFS 2種、BATCH `_transfer_vehicle`）から、Vehicle共通メソッド **`begin_order_control_visit_on_link_entry()`** をそれぞれ1回だけ呼ぶ形に集約する。

**Vehicle初期状態：** `order_control_visit_id = 0`、`order_control_current_visit = None`。

**対象外Nodeへ向かうLinkへ進入した場合：** `order_control_current_visit = None`、`order_control_visit_id` は増やさない。Originから最初に進入したLinkの `end_node` が対象外でもこの状態を維持する。

**対象Nodeへ向かうLinkへ進入した場合**（`end_node.order_control_eligible` かつ `order_control_type != "none"`）：

- `order_control_visit_id` を1増やし、現在訪問状態を新規作成する（初めての対象Node訪問では `order_control_visit_id = 1`）。
- 訪問先Node、inlinkを記録する。
- earliest arrival timestepを**現在訪問状態**へ記録する（既存 `record_order_control_earliest_arrival_timestep_for_current_link()` と同等の計算）。
- Phase 4-6Oでは、既存 `order_control_earliest_arrival_timesteps` も**現行どおり再訪時に上書き**する（**§1H.5**）。初回のみ記録へ変更するのは Phase 4-6R と同時。
- `arrival_time`、`arrival_tiebreaker`、`batch_assignment` の初期値は **`None`**（未記録・assignmentなし）。

### 1H.7 Node端到着処理

現行 `Vehicle.update()` の流れに即する（`Node.transfer()` はこの処理の途中に割り込まない）。

```
Link終端への到達判定（s.x == s.link.length）
    ↓
route_next_link_choice()
    ↓
end_node.incoming_vehicles へ登録
    ↓
現在訪問の到着時刻・tiebreakerを記録
    ↓
初回訪問なら既存の分析用初回履歴にも記録
```

**補足：**

- Link終端到達はVehicle位置とLink長の条件により判定される。`incoming_vehicles` への登録そのものが到達判定ではない。
- `route_next_link_choice()` はLink終端到達判定後、`incoming_vehicles` 登録前に実行する（現行位置を維持）。
- 到着情報の記録は `record_order_control_node_first_arrival()` 相当の処理を、**現在訪問状態**向けに行う。
- **同一訪問中**の `incoming_vehicles` 再登録では、到着時刻・tiebreakerを上書きしない。

### 1H.8 FCFSの訪問対応

`transfer_fcfs_clearance()` の候補抽出・並べ替えで、既存の初回到着辞書（`order_control_node_arrival_times` 等）ではなく**現在訪問状態**を参照する。

**並べ替えキー（昇順）：** 現在訪問の到着時刻 → 現在訪問のtiebreaker → Vehicle ID

FCFSの通過処理・clearance処理のロジック自体は変更しない。

### 1H.9 BATCH形成の訪問対応

BATCH候補はVehicle単体ではなく、**Vehicleの現在訪問単位**で判定する。

**候補判定で参照：** 対象Node、`visit_id`、inlink、earliest arrival timestep、現在訪問に対するBATCH assignmentの有無。

**現在訪問のassignmentに関連付ける情報（最低限）：** batch ID、Node、`visit_id`。

**assignment済み判定：** 現在のNode・現在の `visit_id` に対応するassignmentが存在すること。

**prefix検証：** 処理対象Nodeへの**現在訪問**だけで判定する。過去訪問のbatch IDは現在のprefix判定へ含めない。

### 1H.10 Service unitの訪問対応

**第一候補（並行リスト案）：**

```python
service_unit = {
    "batch_id": ...,
    "inlink": ...,
    "vehicles": [...],
    "visit_ids": [...],
}
```

`vehicles[i]` と `visit_ids[i]` は同一Vehicleの同一訪問に対応する。service unitへNodeを重複保存する設計ではない。

**登録時：** Vehicleを `vehicles` へ追加し、その時点のVehicleのcurrent `visit_id` を `visit_ids` へ追加。

**実通過時の照合（いずれも一致必須）：**

- Vehicleの現在訪問Node == service queueを処理中のNode
- Vehicleの現在訪問inlink == `service_unit["inlink"]`
- Vehicleの現在 `visit_id` == `service_unit["visit_ids"]` の対応位置の値

**通過後（service unit側）：** 通過したVehicleと対応する `visit_id` を `vehicles` / `visit_ids` から同時に削除。

**不変条件：** `len(service_unit["vehicles"]) == len(service_unit["visit_ids"])`

並行リスト案と、Vehicleと `visit_id` を1組の要素として保存する代替案の比較は、実コードへの影響確認後に最終決定する（**§1H.16.2**）。

### 1H.11 Node通過時の状態更新

VehicleがNodeを実際に通過した場合、service unit側とVehicle側を**別々に**更新する。通過しなかった場合はどちらも終了処理を行わない。

#### 1H.11.1 Service unit側

通過したVehicleと、そのVehicleに対応する `visit_id` をservice unitから削除する。

#### 1H.11.2 Vehicle側

終了する訪問に記録されているBATCH assignmentを分析用履歴へ記録した後、その訪問状態を完了させる。必要なbatch情報（batch ID、Node、inlink、形成timestep、Vehicle名、`visit_id`、service unit内順序等）を**現在訪問の制御状態とは別の分析用履歴**へ保存する。次のNodeへの訪問状態には、終了したassignmentを引き継がない。

### 1H.12 重大不整合

実行中に推測修復せず、いずれも `ValueError` とする。

- order-control対象Nodeへ向かっているのに、現在訪問状態が存在しない
- Vehicleの現在訪問Nodeが、処理中Nodeと一致しない
- Vehicleの現在訪問inlinkが、service unitの `inlink` と一致しない
- service unit登録時の `visit_id` が、Vehicleの現在 `visit_id` と一致しない
- `service_unit["vehicles"]` と `service_unit["visit_ids"]` の長さが一致しない

### 1H.13 既存状態からの移行方針

| 既存状態 | 移行後 |
|----------|--------|
| `order_control_node_arrival_times` | 初回分析履歴として維持（上書きしない） |
| `order_control_node_arrival_tiebreakers` | 同上 |
| `order_control_earliest_arrival_timesteps` | 初回分析履歴として初回のみ記録（再訪時に上書きしない）。**Phase 4-6Oでは現行の上書き挙動を維持**し、Phase 4-6RでBATCH参照先切替と同時に初回履歴化へ変更 |
| `order_control_batch_assignments`（Node名key） | 初回訪問時のbatch ID互換記録（legacy）。現在制御はcurrent visit `batch_assignment`（**Phase 4-6Sで実装。§1H.22**） |

**移行順：**

1. 現在訪問状態の共通基盤（Phase 4-6O）— 現在訪問へのearliest記録、既存辞書の上書き挙動は維持
2. Node端到着記録の訪問対応（Phase 4-6P）
3. FCFSの参照先変更（Phase 4-6Q）
4. BATCH形成の参照先変更（Phase 4-6R）— 現在訪問状態への参照切替と、`order_control_earliest_arrival_timesteps` の初回履歴化を同時実施
5. service unit・実通過対応（Phase 4-6S）— **実装済み（§1H.22）**

移行完了後、FCFS・BATCHの現在制御が既存の初回履歴辞書を参照していないことを確認する。

### 1H.14 実装小Phase

各小Phaseは、実装 → 専用テスト → 回帰確認 → 正式記録 → commit・push まで完了してから次へ進む。境界は実コードの依存関係確認後に必要最小限調整できる。

| Phase | 内容 |
|-------|------|
| **4-6O** | 現在訪問状態の共通基盤（**実装済み**。§1H.18） |
| **4-6P** | Node端到着記録の訪問対応（**実装済み**。§1H.19） |
| **4-6Q** | FCFSの参照先変更（**実装済み**。§1H.20） |
| **4-6R** | BATCH形成の訪問対応（参照先を現在訪問状態へ切替。`order_control_earliest_arrival_timesteps` を初回分析履歴化）（**実装済み**。§1H.21） |
| **4-6S** | BATCH assignmentの訪問対応、service unit visit_id、実通過照合（**実装済み**。§1H.22） |
| **4-6T** | 小規模BATCH再訪end-to-end統合テスト（**実装済み**。§1H.23。`b7159f9`） |
| **4-6U** | 5,000台clearance=0、5,000台clearance=1、10,000台clearance=1のhigh-demand再実行。既知prefix violation非再発、全ケース正常終了、sanity check PASS。**再実行・検証完了**（§1H.24。本体変更なし） |
| **4-6V** | zero-service追加形成修正、size-one BATCHとFCFSの等価性回復、正式テスト（**§1H.25**。`2b10b08`） |
| **4-6V診断** | size-one BATCH対FCFS等価性・batch size予備比較診断スクリプト（**§1H.25**。`fe9e53e`） |

### 1H.15 テスト方針

- 現在訪問状態の単体テスト
- FCFSの強制再訪テスト
- BATCHの強制再訪テスト
- service unitと現在訪問の不整合検出
- 再訪を含むN=1 BATCHとFCFSの整合性
- 既存回帰テスト
- high-demand再実行（性能優劣は合格条件にしない）

**high-demand再実行順：** 5,000台・clearance=0 → 5,000台・clearance=1 → 10,000台・clearance=1

`diagnostics/order_control/` 配下は、用途ごとに次の3区分で扱う。いずれも repository root の `tests_*.py` による通常自動回帰には含めない。

- **Phase 4-6N legacy診断4本：** 修正前不具合の再現・原因調査資料（prefix violation等のhistorical record）
- **Phase 4-6V post-fix診断2本：** 修正後の探索的・手動回帰診断（`grid_n1_fcfs_route_fixed_small_check.py`、`grid_10000_batch_size_and_signal_timing_preliminary_check.py`）
- 補正signal baselineモード（`--corrected-signal-baseline-only`）も上記10,000台診断スクリプト内の探索的診断である

### 1H.16 決定済み・要確認・保留事項

#### 1H.16.1 決定済み

- Node訪問を制御単位として区別する
- Vehicleごとの単調増加整数 `visit_id` を使用する（order-control対象Nodeへの訪問時のみ増加。**§1H.3**）
- 現在訪問状態はorder-control対象Nodeだけに作る。対象外Nodeへ向かうLink進入時は `order_control_current_visit = None` とし `order_control_visit_id` は増やさない
- FCFS・BATCHは現在訪問状態を制御に使う
- 既存の初回履歴は分析用として上書きせず維持する（`order_control_earliest_arrival_timesteps` の初回履歴化は Phase 4-6R と同時。**§1H.5**）
- 過去のbatch IDも分析用履歴として保持する
- service unitは登録時の `visit_id` を保持する
- 通過時にservice unit側とVehicle側の2状態を更新する
- 経路選択とNode再訪の可否は変更しない
- 現在訪問状態はVehicle上の1つの辞書 `order_control_current_visit`（`None` 初期）と `order_control_visit_id`（`0` 初期）で保持する
- 辞書キー：`visit_id`、`node`、`inlink`、`earliest_arrival_timestep`、`arrival_time`、`arrival_tiebreaker`、`batch_assignment`（`node`・`inlink` はオブジェクト参照）
- Link進入処理は `begin_order_control_visit_on_link_entry()` に集約し、5つのLink進入経路から各1回呼ぶ
- `arrival_time`、`arrival_tiebreaker`、`batch_assignment` の初期値は `None`

#### 1H.16.2 実コード・既存テスト確認後に最終決定

- service unitの並行リスト案か、Vehicleと `visit_id` を1組にする案か

#### 1H.16.3 第一候補として試行し、小規模テストで確認

- Node側へBATCH形成履歴を保存する案

#### 1H.16.4 現時点では保留

- BATCH履歴の詳細項目と最終的な格納構造
- 過去batch IDの具体的な研究利用方法
- 詳細な全訪問履歴の保存範囲
- 将来の分析用追加ログ

（将来の加工に必要な基本情報を保存できる設計にする、という方針は **§1H.16.1** で決定済み。）

### 1H.17 次工程・再開時チェックリスト

| 項目 | 値 |
|------|-----|
| Step 1〜4 | 完了・commit済み（`05fa2d1`、`f339b88`、`c06936c`、`0e35799`） |
| Step 5 | 設計記録完了（**§1H**） |
| Phase 4-6O実装前調査 | 完了（§1H.3・§1H.4・§1H.5・§1H.6・§1H.13・§1H.14・§1H.16 反映） |
| Phase 4-6O | **実装・専用テスト・回帰確認・commit・push済み**（**§1H.18**、`e3243e7`） |
| Phase 4-6P | **実装・専用テスト・回帰確認・commit・push済み**（**§1H.19**、`b1b4d7f`・`b051c58`） |
| Phase 4-6Q | **実装・専用テスト・回帰確認・commit・push済み**（**§1H.20**、`7c3c6d3`・`9100803`） |
| Phase 4-6R | **実装・専用テスト・既存テスト更新・広い回帰確認・commit・push済み**（**§1H.21**、`cdd19be`・`30588a0`・`ae57e40`） |
| Phase 4-6S | **実装・専用テスト・既存テスト更新・広い回帰確認・commit・push済み**（**§1H.22**、`5e26bc9`） |
| Phase 4-6T | **実装・回帰確認・commit・push済み**（**§1H.23**、`b7159f9`） |
| Phase 4-6U | **再実行・検証完了**（**§1H.24**。本体・テスト・診断Python変更なし。結果は§1H.24に記録する） |
| Phase 4-6V | **実装・専用テスト・限定回帰・commit・push済み**（**§1H.25**、`2b10b08`） |
| Phase 4-6V診断 | **診断スクリプト追加・commit・push済み**（**§1H.25**、`fe9e53e`） |
| 最新実装commit | `2b10b08` |
| 直前の文書commit（Phase 4-6U） | `aca6ce9`（文書更新前HEAD。Phase 4-6V本体は `2b10b08`、診断は `fe9e53e`） |
| high-demand BATCH比較 | **完了**（Phase 4-6U。5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケース。U1〜U3すべてexit 0、prefix violationなし。§1H.24） |
| size-one BATCHとFCFSの等価性 | **修正後コードで確認済み**（200台固定route・10,000台自由経路。§1H.25） |
| batch size探索 | **ここで終了**（修正後N=10・N=20予備比較のみ。§1H.25） |

**次工程：**

1. Level 2仮想サービス推定の設計調査（未実装）
2. Level 2 unresolved時のLevel 1 fallback接続（未実装）
3. 必要に応じてLevel 0 fallback（未実装）
4. trip-end Vehicleは研究対象外
5. stale service unit回復は必要性が低ければ保留
6. assignment正式全訪問履歴は後回し
7. Time-value Transaction本体（未実装）

**終了した工程：**

- 追加のbatch size探索（§1H.25）

**補正signal settingによるP2〜P4：** 未実行。追加実行の要否と時期は別途判断する（§1H.25.13）。

**再開時に読むもの：**

- 本メモ **§1H**（本設計）、**§1G**（診断・根本原因）、**§1H.19**（Phase 4-6P到着記録・乱数設計・実装記録）、**§1H.20**（Phase 4-6Q FCFS参照先変更・実装記録）、**§1H.21**（Phase 4-6R BATCH参照先変更・実装記録）、**§1H.22**（Phase 4-6S BATCH assignment訪問対応・実装記録）、**§1H.23**（Phase 4-6T 小規模BATCH再訪end-to-end統合・実装記録）、**§1H.24**（Phase 4-6U high-demand再実行・検証記録）、**§1H.25**（Phase 4-6V zero-service追加形成・size-one BATCHとFCFS等価性・batch size予備比較）
- `diagnostics/order_control/README.md`（診断スクリプトは通常回帰ではなく既知問題の再現・確認資料。Phase 4-6U後の比較診断2本の現在期待はexit 0）
- 本体：`Vehicle.order_control_current_visit`、`current visit` の `batch_assignment`、`Vehicle.get_order_control_batch_assignment()`、`Vehicle.has_order_control_batch_assignment()`、`Vehicle.assign_order_control_batch_to_current_visit()`、`Vehicle.order_control_batch_assignments`、`Node.get_order_control_batch_trigger_candidates()`、`Node.get_order_control_batch_candidates_by_inlink()`、`Node.get_ordered_order_control_batch_candidates_by_inlink()`、`Node.register_order_control_batch_service_units()`、`Node.serve_order_control_batch_service_queue()`、`Node.transfer_batch()`、`Node.transfer()`
- テスト：`tests_order_control_batch_revisit_integration.py`、`tests_order_control_batch_visit_assignment.py`、`tests_order_control_batch_revisit_ranking.py`、`tests_order_control_batch_service_unit_registration.py`、`tests_order_control_batch_service_queue_transfer.py`、`tests_order_control_batch_transfer.py`、`tests_order_control_batch_node_transfer_integration.py`

### 1H.18 Phase 4-6O実装記録

**状態：** 実装・専用テスト・回帰確認・commit・push済み（`e3243e7`）。

#### 1H.18.1 Vehicle属性・現在訪問辞書

`Vehicle.__init__` に追加：

- `order_control_visit_id = 0`
- `order_control_current_visit = None`

order-control対象Nodeへの訪問開始時の `order_control_current_visit` 辞書：

```python
{
    "visit_id": int,
    "node": Node,
    "inlink": Link,
    "earliest_arrival_timestep": int,
    "arrival_time": None,
    "arrival_tiebreaker": None,
    "batch_assignment": None,
}
```

`node` と `inlink` はオブジェクト参照。Phase 4-6Oでは、`arrival_time`、`arrival_tiebreaker`、`batch_assignment` はいずれも `None` で開始する。`arrival_time` と `arrival_tiebreaker` の記録は Phase 4-6P、`batch_assignment` の現在訪問対応は後続のBATCH対応Phaseで実装する。

#### 1H.18.2 追加・維持メソッド

| メソッド | 役割 |
|----------|------|
| `_compute_order_control_earliest_arrival_timestep_for_current_link()` | earliest arrival timestep を計算して `int` で返す |
| `begin_order_control_visit_on_link_entry()` | Link進入後に earliest 記録・対象Node判定・visit_id増加・現在訪問辞書作成または `None` 化 |
| `record_order_control_earliest_arrival_timestep_for_current_link()` | **維持**。既存 `order_control_earliest_arrival_timesteps` のみ更新。`visit_id` と `order_control_current_visit` には触れない |

#### 1H.18.3 Link進入経路への接続

`begin_order_control_visit_on_link_entry()` を次の5経路から、各Link進入につき1回だけ呼ぶ：

1. `Node.generate`
2. `Node.transfer`
3. `Node.transfer_fcfs_no_clearance`
4. `Node.transfer_fcfs_clearance`
5. `serve_order_control_batch_service_queue()` 内の `_transfer_vehicle`

#### 1H.18.4 visit_idの動作（実装確認済み）

- order-control対象Nodeへ向かうLink進入時のみ `order_control_visit_id` を1増加
- 対象条件：`node.order_control_eligible` かつ `node.order_control_type != "none"`
- 対象外Nodeでは `visit_id` を増やさず `order_control_current_visit = None`
- Originから最初に対象外Nodeへ向かう場合は `0` / `None` を維持
- 最初の対象Node訪問で `visit_id = 1`
- 同一対象Nodeへの再訪でも新しい `visit_id` を発行

#### 1H.18.5 Earliest arrivalの段階移行（Phase 4-6O時点）

- 現在訪問辞書へ `earliest_arrival_timestep` を記録
- 既存 `order_control_earliest_arrival_timesteps` も更新（end_node 名 key）
- 既存辞書は再訪時にも従来どおり上書き（回帰互換維持）
- FCFS・BATCHはまだ既存辞書を参照（現在訪問状態は制御に未接続）
- 既存辞書の初回分析履歴化は **Phase 4-6R**（BATCH参照先切替と同時）

#### 1H.18.6 Phase 4-6Oで変更していない範囲

- `Vehicle.update()` のNode端到着処理
- 現在訪問への `arrival_time`・`arrival_tiebreaker` 記録（Phase 4-6P）
- FCFSの参照先変更（Phase 4-6Q）
- BATCH候補・形成の参照先変更（Phase 4-6R）— **実装済み（§1H.21）**
- BATCH assignmentの現在訪問対応（Phase 4-6S）— **実装済み（§1H.22）**
- service unitへの `visit_id` 追加・実通過照合（Phase 4-6S）— **実装済み（§1H.22）**
- 訪問終了処理・BATCH履歴
- high-demand比較の再実行

#### 1H.18.7 専用テスト

**ファイル：** `tests_order_control_current_visit_state.py`（15関数、**全件PASS**）

| # | テスト関数 | 確認範囲 |
|---|-----------|----------|
| 1 | `test_vehicle_initial_values` | Vehicle初期値 |
| 2 | `test_origin_to_ineligible_first_link` | 対象外Nodeへの最初のLink進入 |
| 3 | `test_first_eligible_node_visit_via_generate` | 最初の対象Node訪問 |
| 4 | `test_eligible_to_ineligible_clears_current_visit` | 対象Nodeから対象外Nodeへ |
| 5 | `test_next_eligible_visit_after_ineligible_link` | 次の対象Node訪問 |
| 6 | `test_same_eligible_node_revisit_gets_new_visit_id` | 同一対象Nodeへの再訪 |
| 7 | `test_earliest_arrival_timestep_calculation` | earliest arrival計算 |
| 8 | `test_legacy_earliest_dict_overwrites_on_revisit` | 既存earliest辞書の上書き互換 |
| 9 | `test_legacy_record_method_does_not_touch_current_visit` | 既存記録メソッドの互換性 |
| 10 | `test_incoming_vehicles_reregistration_does_not_increment_visit_id` | incoming再登録でID不変 |
| 11 | `test_link_entry_via_node_generate` | Link進入経路：generate |
| 12 | `test_link_entry_via_standard_transfer` | Link進入経路：標準transfer |
| 13 | `test_link_entry_via_transfer_fcfs_no_clearance` | Link進入経路：FCFS no clearance |
| 14 | `test_link_entry_via_transfer_fcfs_clearance` | Link進入経路：FCFS clearance |
| 15 | `test_link_entry_via_batch_transfer_vehicle` | Link進入経路：BATCH `_transfer_vehicle` |

上記のうち、Link進入経路を確認する既存4テスト（#12〜#15）を補強し、5つのLink進入経路すべてについて、進入先Linkの `end_node` がorder-control対象Nodeである場合に現在訪問状態が正しく作成されることを確認した（`Node.generate` は #3・#11 で確認）。確認した5経路は `Node.generate`、`Node.transfer`、`Node.transfer_fcfs_no_clearance`、`Node.transfer_fcfs_clearance`、`serve_order_control_batch_service_queue()` 内の `_transfer_vehicle` である。各経路では、`order_control_visit_id` が進入前より1増加すること、`order_control_current_visit` が作成されること、現在訪問の `node` が進入先Linkの `end_node`、`inlink` が進入先Linkと一致すること、`earliest_arrival_timestep` が既存式による手計算値と一致すること、`arrival_time`・`arrival_tiebreaker`・`batch_assignment` が `None` であること、既存 `order_control_earliest_arrival_timesteps` にも進入先Nodeの値が記録されることを確認した。対象外Node進入の確認も維持している：Originから対象外Nodeへ進入した場合は `visit_id` を増やさず `current visit` は `None`（#2）、対象Nodeから対象外Nodeへ進入した場合は `visit_id` を維持し `current visit` を `None` にする（#4）。

#### 1H.18.8 回帰テスト（すべてPASS）

- `tests_order_control_batch_earliest_arrival_timestep.py`
- `tests_order_control_batch_state_containers.py`
- `tests_order_control_batch_service_queue_transfer.py`
- `tests_order_control_batch_node_transfer_integration.py`
- `tests_order_control_batch_transfer.py`
- `tests_order_control_eligibility.py`
- `tests_fcfs_order_control_clearance_0.py`
- `tests_fcfs_order_control_clearance_1.py`
- `tests_order_exchange_baseline.py`
- `demos_and_examples/example_00en_simple.py`

**交通結果：** baseline・exampleとも既知値と一致。既存交通結果に変化なし。

- baseline：48/48 trips、平均速度 16.5 m/s、総旅行時間 2928.0 s、平均旅行時間 61.0 s、平均遅延 1.0 s、遅延比 0.017、総走行距離 48000.0 m
- example：735/810 trips、平均速度 11.7 m/s、総旅行時間 119475.0 s、平均旅行時間 162.6 s、平均遅延 62.6 s、遅延比 0.385、総走行距離 1632250.0 m

### 1H.19 Phase 4-6P実装前調査・到着記録と乱数設計

**状態：** 実装前調査・乱数設計調査完了（設計時点の記録）。**実装・専用テスト・回帰確認・commit・push済み**（`b1b4d7f`・`b051c58`）。実装結果は **§1H.19.7**。

#### 1H.19.1 Node端到着処理の現行順序

研究対象の通常Vehicle（`single_trip`、order-control対象内部Nodeを目的地としない）について、`Vehicle.update()` のLink終端到達処理は次の順序とする。

```
Link終端到達判定（vehicle.x == vehicle.link.length）
    → node_event（存在する場合）
    → route preference update（設定時）
    → route_next_link_choice()
    → end_node.incoming_vehicles へ登録
    → Node到着情報を記録
```

`incoming_vehicles` への登録そのものはLink終端到達判定ではない。

同一 timestep では `Node.transfer()` が先に完了しており、`Vehicle.update()` で記録した到着情報は次 timestep の `Node.transfer()` から参照される。`route_next_link_choice()` の現在位置は変更しない。

目的地到着経路（`link.end_node == dest` の trip-end 処理）は今回の実装対象外とする。

#### 1H.19.2 現在訪問への到着記録

Phase 4-6Pでは `Vehicle.record_order_control_node_arrival(node)` を追加する。

- 現在訪問の `arrival_time`・`arrival_tiebreaker` を記録する
- 同一Vehicle・同一Nodeの初回到着なら、既存初回履歴にも**同じ値**を記録する
- 既存 `record_order_control_node_first_arrival(node)` は削除せず維持する（thin wrapper か内部ヘルパー共有は実装時に既存直接呼出しテストへの影響を確認して決定）

`arrival_time` は `W.T * W.DELTAT`（秒）。`W.DELTAT` が1以外でも同式。型は `W.DELTAT` に応じて `int` または `float`。キー名 `arrival_time` を維持し、timestep単位へは変更しない。

`Vehicle.update()` の通常Vehicle用到着記録箇所を、新メソッドの呼出しへ差し替える。研究対象外経路の扱いは変更しない。

#### 1H.19.3 再登録・再訪時の処理

**同一訪問中の再登録：** `arrival_time` と `arrival_tiebreaker` がともに非 `None` のとき、値の上書き・新しい乱数生成・初回履歴の更新は行わない。

**不完全な到着状態：** 片方だけが `None` のときは重大不整合として `ValueError`。自動修復しない。

**対象Nodeで current visit がない：** `order_control_current_visit is None` のときは `ValueError`。

**対象外Node：** `current visit` が `None` で正常。到着情報を記録せず、`ValueError` にしない。

**再訪：** 既存初回履歴（`order_control_node_arrival_times` / `order_control_node_arrival_tiebreakers`）は上書きしない。現在訪問へ新しい `arrival_time` を記録する。

**重複検証しない条件（Phase 4-6Oで保証）：** 現在訪問の `node`・`inlink`・`visit_id` と到着時状態の一致は、到着のたびに検証しない。

#### 1H.19.4 tiebreakerの乱数設計

| 到着種別 | 乱数源 | 記録先 |
|----------|--------|--------|
| 初回訪問 | `W.rng.random()` を**1回** | 現在訪問と初回履歴の**両方**（同値） |
| 再訪 | `W.order_control_rng.random()` を**1回** | **現在訪問のみ** |
| 同一訪問再登録 | 消費なし | — |

**設計判断：**

- 初回訪問は既存シミュレーションとの互換性維持のため `W.rng` を使う
- 再訪は Phase 4-6P で新たに追加される情報のため、共有乱数列へ影響しない独立 stream を使う
- どちらも一様乱数であり、同時到着順の tiebreaker として使用する
- 初回・再訪で乱数源が異なることは、意図的な互換性設計である

**`order_control_rng` の seed：** 既存 `W.rng = np.random.default_rng(seed=random_seed)` は**変更しない**（現行の乱数列を維持）。`order_control_rng` のみ `np.random.SeedSequence(random_seed).spawn(2)[1]` から派生する。`random_seed=None` でも現行と同様に非決定的だが正常動作する。Phase 4-6P では新しい公開 World 引数は追加しない。`SeedSequence` の生成を1回にするか専用ヘルパーへ分けるかは実装時に決定する。

再訪時に共有 `W.rng` を追加消費すると、後続の経路選択・標準Node merge・DUOノイズ・初回 tiebreaker 等の乱数列がずれる。独立 stream により既存 `W.rng` の消費順を維持する設計とする（再訪なしシナリオでは共有列への影響を避ける）。

#### 1H.19.5 Phase 4-6Pの実装範囲

- `World` へ `order_control_rng` を追加
- `Vehicle.record_order_control_node_arrival(node)` を追加
- 初回訪問：`W.rng` 1回で現在訪問と初回履歴へ同値保存
- 再訪：`order_control_rng` 1回で現在訪問のみへ保存
- 同一訪問再登録・不完全状態・対象Nodeで current visit なしの各判定
- `Vehicle.update()` の通常Vehicle用到着記録箇所を新メソッド呼出しへ差し替える（研究対象外経路は変更しない）
- 既存 `record_order_control_node_first_arrival()` の維持
- 専用テスト `tests_order_control_current_visit_arrival.py` を追加

#### 1H.19.6 未変更・保留範囲

変更しない：`route_next_link_choice()` の位置、`incoming_vehicles` 登録位置、`visit_id` 発行、Link進入時の現在訪問作成、earliest arrival 計算、既存 earliest 辞書の再訪時上書き、FCFS/BATCH 参照先、BATCH assignment、service unit、訪問終了、BATCH履歴、high-demand比較。FCFS の現在訪問参照は Phase 4-6Q。

**専用テスト方針（`tests_order_control_current_visit_arrival.py`）：** 初回到着・`arrival_time` 式・初回 tiebreaker の `W.rng` 1回生成・両辞書への同値記録・同一訪問再登録での値維持と乱数非消費・再訪での新 `arrival_time` と `order_control_rng` tiebreaker・再訪での `W.rng` 非消費・初回履歴非上書き・`random_seed` 再現・`random_seed=None` 正常動作・片方のみ `None` の `ValueError`・対象Nodeで current visit なしの `ValueError`・対象外Nodeでの非要求。Node・inlink 不一致の改ざんテストは含めない。

（設計時点の上記方針について：実装時には current visit の **Node** 不一致を重大な状態不整合として検出する仕様を確定し、Node不一致テストを `tests_order_control_current_visit_arrival.py` に追加した。**inlink** 不一致の到着記録テストは追加していない。詳細は **§1H.19.7.10**。）

#### 1H.19.7 Phase 4-6P実装記録

**状態：** 実装・専用テスト・回帰確認・commit・push済み。

- Step 1（独立乱数生成器）：commit `b1b4d7f` — `phase 4-6P: add independent order-control random stream`
- Step 2（到着記録・統合テスト修正）：commit `b051c58` — `phase 4-6P: record initial and revisit arrivals and update BATCH integration setup`
- 設計記録commit（実装前）：`5846226` — `phase 4-6P: document current-visit arrival and tiebreaker random-stream design`
- 直前Phase：Phase 4-6O（`e3243e7`）

##### 1H.19.7.1 独立乱数生成器

`World.__init__` に `W.order_control_rng` を追加した。既存の `W.rng` 初期化は変更していない。

```python
W.rng = np.random.default_rng(seed=random_seed)
order_control_seed_sequence = np.random.SeedSequence(random_seed)
order_control_child_seed_sequence = order_control_seed_sequence.spawn(1)[0]
W.order_control_rng = np.random.default_rng(
    order_control_child_seed_sequence
)
W.random_seed = random_seed
```

- `W.rng` の初期化式は変更していない
- `W.order_control_rng` は `SeedSequence(random_seed).spawn(1)[0]` から派生する
- `order_control_rng` の生成および消費は `W.rng` を消費しない
- 同じ `random_seed` では `order_control_rng` の乱数列が再現する
- `random_seed=None` でも両方の Generator を利用できる
- 専用テスト：`tests_order_control_rng.py`

（設計時点 **§1H.19.4** では `spawn(2)[1]` を候補としていたが、実装時に `spawn(1)[0]` を採用した。）

##### 1H.19.7.2 current visit到着記録メソッド

`Vehicle.record_order_control_node_arrival(node)` を追加した。VehicleがNodeの `incoming_vehicles` へ登録された直後に呼ばれ、現在訪問の到着情報を一元的に記録する。

`Vehicle.update()` の次の2経路について、従来の `record_order_control_node_first_arrival(node)` 呼び出しを新メソッドへ変更した（順序は維持）：

1. `node.incoming_vehicles.append(vehicle)`
2. `vehicle.record_order_control_node_arrival(node)`

対象経路：taxiモードでのリンク間移動要求、通常のリンク間移動要求。

##### 1H.19.7.3 対象Nodeの条件

`order_control_eligible is True` かつ `order_control_type != "none"` のNodeのみ処理する。対象外Nodeでは、current visitの検証・更新、初回履歴の更新、`W.rng`・`W.order_control_rng` の消費を行わずに return する。

##### 1H.19.7.4 arrival_timeの確定仕様

`arrival_time = W.T * W.DELTAT`（秒）。`link_arrival_time`・`earliest_arrival_timestep`・仮想到着時刻は使用しない。`arrival_time` は、その current visit でVehicleが対象Nodeの `incoming_vehicles` へ最初に登録された時刻である。

##### 1H.19.7.5 初回訪問時の確定仕様

VehicleがそのNodeへ初めて到着する場合（`node.name` が初回履歴辞書に未登録）：

- `W.rng` から `arrival_tiebreaker` を1回だけ生成する
- 同じ `arrival_time` を current visit と初回履歴（`order_control_node_arrival_times` / `order_control_node_arrival_tiebreakers`）へ保存する
- 同じ `arrival_tiebreaker` を current visit と初回履歴へ保存する
- `W.order_control_rng` は消費しない

##### 1H.19.7.6 再訪時・同一訪問中の再登録

**再訪**（新しい `visit_id` を持つ別の current visit。初回履歴に当該Node名が既に存在）：

- `arrival_time` は再訪中の現在時刻 `W.T * W.DELTAT` から新規計算する
- `arrival_tiebreaker` は `W.order_control_rng` から1回だけ生成する
- 新しい到着情報は current visit のみへ保存する
- 初回履歴は上書きしない
- `W.rng` は消費しない

**同一訪問中の再登録**（`visit_id`・current visit は同じ。`arrival_time` と `arrival_tiebreaker` がともに記録済み）：

- 到着情報は上書きしない
- 乱数は追加消費しない

##### 1H.19.7.7 異常系

order-control対象Nodeでは、検証は乱数生成より前に行われ、次を `ValueError` とする：

- `order_control_current_visit` が存在しない
- current visit の `node` が到着Nodeと一致しない
- `arrival_time` だけが `None`、または `arrival_tiebreaker` だけが `None`

`ValueError` 発生時には current visit・初回履歴・`W.rng`・`W.order_control_rng` の状態を変更しない。

##### 1H.19.7.8 既存メソッドとの関係

- `record_order_control_node_first_arrival(node)` は削除していない
- 既存メソッドの実装自体も変更していない
- 新メソッドから既存メソッドを呼ぶ構成にはしていない（初回訪問時に1回生成した同じ tiebreaker を current visit と初回履歴へ保存する必要があるため）
- `Vehicle.update()` の実運用経路では `record_order_control_node_arrival(node)` を使用する

##### 1H.19.7.9 BATCH統合テストの手動セットアップ更新

`tests_order_control_batch_node_transfer_integration.py` の `_setup_arrived_vehicle()` は、inlink上のVehicle状態・`incoming_vehicles`・earliest arrival辞書・初回到着時刻辞書・初回tiebreaker辞書を手動設定していたが、`order_control_current_visit` を準備していなかった。手動到着状態から `veh.update()` を呼ぶ統合テストで `order_control_current_visit is None` の `ValueError` が発生した。

対応としてテスト専用補助関数 `_begin_arrived_current_visit_for_test(...)` を追加した：

- `begin_order_control_visit_on_link_entry()` で正式に current visit を開始する
- テストが手動指定した `earliest_arrival_timestep` を復元する
- current visit の `arrival_time` と `arrival_tiebreaker` を既存初回履歴と同値にする
- 乱数は生成しない。`batch_assignment` は `None` のまま維持する

適用範囲は、手動セットアップ後に `veh.update()` を呼ぶ6テスト・6車両のみ。共通の `_setup_arrived_vehicle()` は変更していない。`Node.transfer()` やBATCH単体メソッドだけを呼ぶVehicleには不要な current visit を追加していない。本体の `ValueError` 要件を緩和するものではなく、既存統合テストの手動状態を現在の正式な状態モデルへ更新するものである。

##### 1H.19.7.10 新規テスト

- `tests_order_control_rng.py`：`order_control_rng` の存在、`W.rng` との分離、同一seed再現性、異seed差異、相互非干渉、`random_seed=None` 対応
- `tests_order_control_current_visit_arrival.py`：対象外Nodeの副作用なし、current visit欠如・**Node不一致**・片側 `None` の `ValueError`、初回訪問の同値保存、`W.rng` 使用、同一訪問再登録no-op、再訪時の current visit のみ更新・初回履歴維持、再訪再登録no-op、再訪tiebreaker再現、`Vehicle.update()` 統合（設計時点ではNode不一致テストを含めない方針だったが、実装時にNode不一致検出を確定しテストを追加。**§1H.19.6** 参照）

##### 1H.19.7.11 回帰確認結果

Phase 4-6P専用テスト、current visit・初回履歴の既存テスト、FCFS既存テスト、BATCH（状態・候補抽出・形成・登録・service queue・`Node.transfer()` 統合）、order-control設定、Vehicle属性、車両リスト読込み、baseline、example、中規模ネットワークsanity checkはいずれもPASS。診断スクリプト（`diagnostics/order_control/`）は通常回帰テストではないため実行していない。

**baseline・example（既知値と一致）：**

- baseline：48/48 trips、平均速度 16.5 m/s
- example：735/810 trips、平均速度 11.7 m/s

**中規模ネットワーク（性能優劣はPhase 4-6Pの合否基準ではない）：**

FCFS対UXsim standard（500 Vehicle）：standard completed 383/500、FCFS 383/500、standard average travel time 140.8 s、FCFS 146.9 s、eligible FCFS nodes 10、既存sanity checkすべてPASS。

BATCH・FCFS・UXsim standard：いずれも completed 383/500、standard 140.8 s、FCFS 146.9 s、BATCH 146.9 s、BATCH/FCFS average travel time ratio 1.0003（表示上BATCHはFCFSよりhigher）、FCFSとBATCHのeligible Nodeは各10件で一致、既存sanity checkすべてPASS。

##### 1H.19.7.12 Phase 4-6P完了時点とPhase 4-6Q・4-6Rへの引き継ぎ

**Phase 4-6P完了時点（当時）：**

- current visitに現在訪問の `arrival_time` と `arrival_tiebreaker` が記録される
- 初回履歴（`order_control_node_arrival_times` / `order_control_node_arrival_tiebreakers`）は互換用として維持される
- 初回訪問では current visit と初回履歴が同値
- 再訪では current visit のみが再訪値を持つ
- FCFSとBATCHは、当時はまだ既存のNode名キーの初回履歴を参照していた

**Phase 4-6Qで行ったこと（実装済み。§1H.20）：**

- FCFSの到着順位参照先を current visit へ変更した
- 再訪時に現在訪問の `arrival_time` と `arrival_tiebreaker` がFCFS制御へ使われるようにした

**Phase 4-6Rで行ったこと（実装済み。§1H.21）：**

- BATCHのtrigger候補順位および関連参照先を current visit へ変更した
- `order_control_earliest_arrival_timesteps` の初回分析履歴化（**§1H.13**・**§1H.14**）を実施した

**Phase 4-6Sで行ったこと（実装済み。§1H.22）：**

- current visitの `batch_assignment` をBATCH本体へ接続した
- service unitへの `visit_id` 保存と実通過照合を実装した
- 過去訪問assignmentが再訪Vehicleを妨げない設計へ変更した（legacy assignmentを現在制御から除外）

### 1H.20 Phase 4-6Q実装記録（FCFSのcurrent visit参照）

**状態：** 実装・専用テスト・回帰確認・commit・push済み。

**commit：**

- 実装：`7c3c6d3` — `phase 4-6Q: rank FCFS by current visit and add revisit tests`
- 手動FCFS到着テストセットアップ修正：`9100803` — `phase 4-6Q: add current visit to manual FCFS arrival test setup`

**最新実装commit：** `9100803`

**次工程（Phase 4-6Q完了時点）：** Phase 4-6R（当時は未着手）

#### 1H.20.1 FCFS順位キー取得メソッド

`Vehicle.get_order_control_fcfs_rank_key(node)` を追加した。

返却値は current visit から次の順位キー（昇順）：

```
(arrival_time, arrival_tiebreaker, veh.id)
```

1. current visitの `arrival_time`
2. current visitの `arrival_tiebreaker`
3. `veh.id`

このメソッドは次の初回履歴を参照しない：

- `order_control_node_arrival_times`
- `order_control_node_arrival_tiebreakers`

#### 1H.20.2 FCFS順位読取時の異常系

`get_order_control_fcfs_rank_key(node)` では、次を `ValueError` とする：

- `order_control_current_visit` が存在しない
- current visitの `node` がFCFS対象Nodeと一致しない
- `arrival_time` または `arrival_tiebreaker` の少なくとも一方が `None`

到着情報については、次のすべてが `ValueError` である：

- `arrival_time` と `arrival_tiebreaker` が両方とも `None`
- `arrival_time` だけが `None`
- `arrival_tiebreaker` だけが `None`

**`record_order_control_node_arrival(node)` との違い：**

| 状況 | `record_order_control_node_arrival(node)` | `get_order_control_fcfs_rank_key(node)` |
|------|-------------------------------------------|----------------------------------------|
| 両方 `None` | これから到着情報を記録する正常な開始状態 | FCFS順位を読む時点では到着記録済みでなければならない重大不整合 |
| 片側だけ `None` | 不整合（`ValueError`） | 不整合（`ValueError`） |

登録時に保証済みの不変条件について、次の過剰な重複検証は追加していない：

- `visit_id` の型や正値性
- 到着値の数値型
- tiebreakerの値域
- current visitの `inlink` と `veh.link` の一致
- 初回履歴との一致

#### 1H.20.3 FCFS transferの変更

次の2メソッドを、同じ current visit 順位仕様へ変更した：

- `Node.transfer_fcfs_no_clearance()`
- `Node.transfer_fcfs_clearance()`

実運用経路は `transfer_fcfs_clearance()` である。回帰・デバッグ用の `transfer_fcfs_no_clearance()` も同じ順位仕様へ変更した。

候補抽出条件は、`incoming_vehicles` 内のVehicleについて次のみ：

```
veh.route_next_link is not None
```

従来の次の候補条件は削除した：

```
node.name in veh.order_control_node_arrival_times
```

current visitが欠けているVehicleや到着情報未記録のVehicleを候補から黙って除外せず、順位キー取得時に `ValueError` とする。

clearance判定、容量判定、物理先頭判定、リンク遷移、`incoming_vehicles` のclear処理など、順位参照以外のFCFS処理は変更していない。

#### 1H.20.4 初回履歴の扱い

次の初回履歴は削除・改名・更新停止していない：

- `order_control_node_arrival_times`
- `order_control_node_arrival_tiebreakers`

Phase 4-6Q完了時点の状態：

- FCFSは current visit を参照する
- BATCHはまだ初回履歴（`order_control_node_arrival_times` / `order_control_node_arrival_tiebreakers` / `order_control_earliest_arrival_timesteps`）を参照していた
- 初回履歴は分析・診断・互換のため維持する
- 初回訪問時には Phase 4-6P の仕様どおり current visit と初回履歴へ同値保存する
- 再訪時には初回履歴を上書きしない

その後、Phase 4-6RでBATCHも current visit 参照へ変更した（**§1H.21**）。

#### 1H.20.5 再訪順位の専用テスト

新規ファイル `tests_fcfs_order_control_revisit_ranking.py`（13テスト）を追加した。少なくとも次を確認する：

- 順位キーメソッドが current visit の値を返す
- 初回履歴を参照しない
- current visit欠如時の `ValueError`
- current visitのNode不一致時の `ValueError`
- `arrival_time` と `arrival_tiebreaker` が両方 `None` の場合の `ValueError`
- `arrival_time` だけが `None` の場合の `ValueError`
- `arrival_tiebreaker` だけが `None` の場合の `ValueError`
- 再訪Vehicleと初回訪問Vehicleの順位
- 再訪Vehicle同士の current visit tiebreaker順位
- `arrival_time` と tiebreaker が同値の場合の `veh.id` fallback
- 同一訪問中の再登録で順位キーが変わらない
- transfer経由で current visit 欠如が黙って除外されず `ValueError` になる
- transfer経由でNode不一致が `ValueError` になる
- transfer経由で到着情報が両方 `None` の場合に `ValueError` になる

同一訪問中の再登録テストでは、テスト側で `incoming_vehicles` へ事前 `append` せず、`veh.carfollow()` と `Vehicle.update()` による通常の再登録を使用し、同一Vehicleが1回だけ登録されることを確認した。

#### 1H.20.6 tests_order_control_current_visit_state.pyの更新

手動到着状態では初回履歴のみ設定され、current visitの `arrival_time` と `arrival_tiebreaker` が未設定だった。テスト専用補助関数 `_sync_arrived_current_visit_for_test(...)` を追加し、既存 current visit へ到着情報を同期した（`begin_order_control_visit_on_link_entry()` は再度呼ばず、`visit_id` を増やさない。乱数は生成しない）。

適用した6テスト：

- `test_eligible_to_ineligible_clears_current_visit`
- `test_next_eligible_visit_after_ineligible_link`
- `test_same_eligible_node_revisit_gets_new_visit_id`
- `test_legacy_earliest_dict_overwrites_on_revisit`
- `test_link_entry_via_transfer_fcfs_no_clearance`
- `test_link_entry_via_transfer_fcfs_clearance`

#### 1H.20.7 BATCH統合テスト内のFCFS手動状態更新

回帰確認中、`tests_order_control_batch_node_transfer_integration.py` の `test_fcfs_node_calls_fcfs_once` が失敗した。

**原因：** `_setup_arrived_vehicle()` でFCFS到着済み状態を手動作成していたが、初回履歴のみ存在し current visit が存在しなかった。Phase 4-6Q後の `get_order_control_fcfs_rank_key(merge)` で `ValueError` となった。

**対応（commit `9100803`）：** 既存の `_begin_arrived_current_visit_for_test()` を `_setup_arrived_vehicle()` 直後に呼び、`arrival_time` と `arrival_tiebreaker` を初回履歴と同値に同期した。本体の `ValueError` 要件は緩和していない。BATCH本体も変更していない。

#### 1H.20.8 回帰確認結果

**Phase 4-6Q専用・小規模テスト（すべてPASS）：**

- `tests_fcfs_order_control_revisit_ranking.py`
- `tests_order_control_current_visit_state.py`
- `tests_order_control_current_visit_arrival.py`
- `tests_order_control_node_arrival_times.py`
- `tests_order_control_rng.py`
- `tests_fcfs_order_control_tiebreaker.py`
- `tests_fcfs_order_control_behavior.py`
- `tests_fcfs_order_control_transfer.py`
- `tests_fcfs_order_control_clearance_0.py`
- `tests_fcfs_order_control_clearance_1.py`
- `tests_fcfs_order_control_clearance_xyz.py`

**order-control設定・Vehicle周辺（すべてPASS）：**

- `tests_order_control_clearance_settings.py`
- `tests_order_control_eligibility.py`
- `tests_node_order_control_attributes.py`
- `tests_world_order_control_setters.py`
- `tests_random_eligible_order_control.py`
- `tests_vehicle_research_attributes.py`
- `tests_load_vehicle_list_to_uxsim.py`

**BATCH単体・統合（すべてPASS。BATCH本体は未変更、初回履歴参照のまま）：**

- 状態コンテナ、earliest arrival、trigger候補、t_trigger推定、inlink別候補、候補グループ順序、max batch size、service unit登録、service queue transfer、BATCH形成統合、BATCH transfer、BATCH `Node.transfer()` 統合
- `test_fcfs_node_calls_fcfs_once` は修正後PASS
- `test_n1_batch_vs_fcfs_equivalence` はPASS

**baseline・example（既知値と一致）：**

| テスト | completed trips | average speed | total travel time | average travel time | average delay | total distance traveled |
|--------|-----------------|---------------|-------------------|---------------------|---------------|-------------------------|
| baseline | 48 / 48 | 16.5 m/s | 2928.0 s | 61.0 s | 1.0 s | 48000.0 m |
| example | 735 / 810 | 11.7 m/s | 119475.0 s | 162.6 s | 62.6 s | 1632250.0 m |

**中規模ネットワーク（500 Vehicle。性能優劣はPhase 4-6Qの合否基準ではない）：**

FCFS対UXsim standard：completed 383/500（ratio 0.766）、standard total travel time 53941.0 s、FCFS 56257.0 s、standard average travel time 140.8 s、FCFS 146.9 s、standard average delay 11.2 s、FCFS 17.3 s、total distance traveled 両方992850.0 m、eligible FCFS Node数10、既存sanity checkすべてPASS。

BATCH・FCFS・UXsim standard：completed 全方式383/500、standard total travel time 53941.0 s、FCFS 56257.0 s、BATCH 56276.0 s、standard average travel time 140.8 s、FCFS 146.9 s、BATCH 146.9 s、standard average delay 11.2 s、FCFS 17.3 s、BATCH 17.3 s、total distance traveled 全方式992850.0 m、BATCH/FCFS average travel time ratio 1.0003（表示上BATCHはFCFSよりhigher）、FCFS・BATCHのeligible Node数各10、eligible Node集合一致、既存sanity checkすべてPASS。

**1,000台グリッドネットワーク（性能優劣はPhase 4-6Qの合否基準ではない）：**

FCFS対UXsim standard：completed 1000/1000（ratio 1.000）、standard total travel time 165917.0 s、FCFS 167772.0 s、standard average travel time 165.9 s、FCFS 167.8 s、standard average delay 1.3 s、FCFS 3.2 s、total distance traveled 両方3292000.0 m、eligible FCFS Node数36、既存sanity checkすべてPASS。

BATCH・FCFS・UXsim standard：completed 全方式1000/1000、standard total travel time 165917.0 s、FCFS 167772.0 s、BATCH 167872.0 s、standard average travel time 165.9 s、FCFS 167.8 s、BATCH 167.9 s、standard average delay 1.3 s、FCFS 3.2 s、BATCH 3.3 s、total distance traveled 全方式3292000.0 m、BATCH/FCFS average travel time ratio 1.0006、BATCH − FCFS average travel time差0.1 s（表示上BATCHはFCFSよりhigher）、FCFS・BATCHのeligible Node数各36、eligible Node集合一致、既存sanity checkすべてPASS。

**実行しなかったもの（通常回帰では未実行）：**

- 5,000台・10,000台のhigh-demand比較（Phase 4-6T〜4-6Uで予定。**その後Phase 4-6Uで5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースを実行・検証完了。§1H.24**。10,000台・clearance=0は未実行）
- signalized UXsimとのhigh-demand比較
- `diagnostics/order_control/` 配下の診断スクリプト（Phase 4-6Nの修正前状態と既知prefix violationを保存するもの。通常回帰テストではない）

#### 1H.20.9 Phase 4-6Q完了時点

- FCFSは current visit の `arrival_time` と `arrival_tiebreaker` を参照する
- 再訪Vehicleは現在訪問の到着情報でFCFS順位付けされる
- 同一訪問中の再登録では順位キーは変化しない
- 初回履歴は維持される
- BATCHは当時はまだ初回履歴を参照していた（Phase 4-6Rは未着手）
- 現在の次工程は Phase 4-6R（当時）

### 1H.21 Phase 4-6R実装記録（BATCH形成のcurrent visit参照）

**状態：** 実装・専用テスト・既存テスト更新・広い回帰確認・commit・push済み。

**commit：**

- Step 1：`cdd19be` — `phase 4-6R: add BATCH current-visit accessors and preserve first earliest history`
- Step 2：`30588a0` — `phase 4-6R: use current-visit timing in BATCH formation and add revisit tests`
- Step 3：`ae57e40` — `phase 4-6R: add current visits to manual BATCH test vehicles, assert arrival errors, and exclude ineligible-node earliest`

**最新実装commit：** `ae57e40`

**次工程（Phase 4-6R完了時点）：** Phase 4-6S（当時は未着手。**その後完了。§1H.22**）

#### 1H.21.1 Step別の役割

| Step | commit | 内容 |
|------|--------|------|
| Step 1 | `cdd19be` | BATCH用current visitアクセサー、legacy earliest辞書の初回履歴化、earliest関連テスト |
| Step 2 | `30588a0` | Node側BATCH形成処理のcurrent visit参照、再訪BATCH専用テスト |
| Step 3 | `ae57e40` | 既存BATCHテスト8ファイル更新（7ファイルで手動Vehicle状態へcurrent visit追加、1ファイルで対象外Node進入後の期待値更新）、到着情報欠如時のValueErrorテスト |

#### 1H.21.2 BATCH専用current visitアクセサー（Step 1）

Vehicleへ次の3メソッドを追加した。

| メソッド | 役割 |
|----------|------|
| `_require_order_control_current_visit_for_batch(node)` | BATCH形成用current visit取得。存在・node一致を確認し辞書を返す。フィールド固有検証は行わない |
| `get_order_control_batch_trigger_rank_key(node)` | 到着済みtrigger候補の順位キー `(arrival_time, arrival_tiebreaker, veh.id)` を返す |
| `get_order_control_batch_earliest_arrival_timestep(node)` | 現在訪問のBATCH制御用 `earliest_arrival_timestep` を返す |

**`_require_order_control_current_visit_for_batch(node)` の `ValueError`：**

- `order_control_current_visit` が `None`
- current visitの `node` が対象Nodeと一致しない

**`get_order_control_batch_trigger_rank_key(node)`：**

- 返却値：`(current visitのarrival_time, current visitのarrival_tiebreaker, veh.id)`。昇順で `(arrival_time, arrival_tiebreaker, veh.id)` の順に比較
- `ValueError`：current visit欠如、node不一致、`arrival_time` が `None`、`arrival_tiebreaker` が `None`、両方 `None`
- 参照しない：`order_control_node_arrival_times`、`order_control_node_arrival_tiebreakers`

**`get_order_control_batch_earliest_arrival_timestep(node)`：**

- `ValueError`：current visit欠如、node不一致、`earliest_arrival_timestep` が `None`
- `arrival_time` と `arrival_tiebreaker` は要求しない
- 参照しない：`order_control_earliest_arrival_timesteps`
- 到着前Vehicleでは正常：`earliest_arrival_timestep` 記録済み、`arrival_time=None`、`arrival_tiebreaker=None`

#### 1H.21.3 legacy earliest辞書の初回履歴化（Step 1）

`order_control_earliest_arrival_timesteps` の意味を変更した。

| 時期 | 挙動 |
|------|------|
| Phase 4-6Rより前 | order-control対象かどうかにかかわらず進入Link終端Nodeへ記録する場合があった。同じNode再訪時に上書き |
| Phase 4-6R Step 1以降 | order-control対象Nodeへの**初回訪問**の分析履歴。初回のみ保存、再訪時は上書きしない。再訪の新earliestはcurrent visitへ。対象外Nodeには記録しない |

変更メソッド：

- `Vehicle.begin_order_control_visit_on_link_entry()`
- `Vehicle.record_order_control_earliest_arrival_timestep_for_current_link()`

| 訪問種別 | legacy earliest | current visit earliest |
|----------|-----------------|------------------------|
| 初回対象Node訪問 | 同値保存 | 同値保存 |
| 再訪 | 初回値維持 | 新値へ更新 |
| 対象外Node進入 | Node名を追加しない | current visitなし（`order_control_current_visit = None`） |

#### 1H.21.4 earliest_arrival_timestepとtau_timesteps

```
earliest_arrival_timestep = (
    link_entry_timestep
    + free_flow_travel_timesteps
    + tau_timesteps
)
```

既定値：`W.order_control_batch_tau_timesteps = 1`

既定値 `tau_timesteps=1` では、`earliest_arrival_timestep` は単純な自由流到着timestepではない。自由流で到着可能なtimestepへ1 timestepを加えた、**予測上の最初の通過可能timestep**として使用する。

```
base_trigger_timestep = max(
    first_transfer_timestep,
    trigger_earliest_arrival_timestep,
)
```

- `first_transfer_timestep`：実到着記録の次にある最初のtransfer可能timestep
- `trigger_earliest_arrival_timestep`：リンク進入時に自由流旅行時間と `tau_timesteps` で推定した最早通過可能timestep

earliest側へ追加の1は加えない（`tau_timesteps` 既定値1の補正と重複するため）。

#### 1H.21.5 trigger候補のcurrent visit参照（Step 2）

`Node.get_order_control_batch_trigger_candidates()` を変更した。

- 候補元：`s.incoming_vehicles`
- 維持した候補条件：`veh.route_next_link is not None`、`s.name not in veh.order_control_batch_assignments`
- 削除したlegacy条件：`s.name in veh.order_control_node_arrival_times`、`s.name in veh.order_control_node_arrival_tiebreakers`（初回履歴は現在制御入力ではない。current visit欠如を黙って候補外にしない）
- sort key：`veh.get_order_control_batch_trigger_rank_key(s)`
- 不完全なcurrent visit・到着情報は黙って除外せず `ValueError`

#### 1H.21.6 t_trigger入力検証（Step 2）

`Node._validate_order_control_batch_t_trigger_inputs()` からlegacyキー検証（arrival_time、arrival_tiebreaker、earliest）を削除し、次を状態検証のために呼ぶ：

- `trigger_vehicle.get_order_control_batch_trigger_rank_key(s)` — current visit存在・node一致・arrival記録
- `trigger_vehicle.get_order_control_batch_earliest_arrival_timestep(s)` — current visit存在・node一致・earliest記録

維持した既存検証：Nodeがorder-control対象、order_control_typeがbatch、triggerがincoming_vehiclesに存在、route_next_link存在、legacy assignment上で未割当、Level 1ではtrigger.link存在、last_order_control_inlink存在時はlast_order_control_entry_timestepも存在。

#### 1H.21.7 base trigger timestepとLevel 0・Level 1（Step 2）

`Node._compute_order_control_batch_base_trigger_timestep()` の読取先のみcurrent visitへ変更。

```
arrival_timestep = int(round(trigger_arrival_time / W.DELTAT))
first_transfer_timestep = arrival_timestep + 1
base_trigger_timestep = max(first_transfer_timestep, trigger_earliest_arrival_timestep)
```

使用しない：legacy `order_control_node_arrival_times`、`order_control_earliest_arrival_timesteps`、`link_arrival_time`、`W.T`

Level 0の式は変更していない（baseをintで返す）。Level 1の分岐・式も変更していない（last_order_control_inlinkがNoneならbase、同inlinkならbase、異inlinkなら `max(clearance_satisfied_timestep, base)`。`clearance_satisfied_timestep = last_order_control_entry_timestep + order_control_clearance_timesteps + 1`）。入力検証通過後は必ずintを返す（推定不能のNone返却は存在しない）。

#### 1H.21.8 inlink候補包含判定（Step 2）

`Node.get_order_control_batch_candidates_by_inlink()` の第一・第二パスで `veh.get_order_control_batch_earliest_arrival_timestep(s)` を使用。

第一パス維持：link一致、`state=="run"`、earliest非負整数、同inlink内earliest非減少、assignment prefix条件。第二パス維持：assignment済みcontinue、earliest≤t_triggerで候補追加、earliest>t_triggerでbreak。

到着前Vehicleは正常：current visitあり、node一致、earliestあり、`arrival_time=None`、`arrival_tiebreaker=None`。trigger順位アクセサーは使用しない。

#### 1H.21.9 candidate group ordering（Step 2）

`Node.get_ordered_order_control_batch_candidates_by_inlink()` 内に直接実装（独立group-orderメソッドは追加していない）。

triggerの `arrival_time` 取得元をcurrent visitへ変更：

```
trigger_rank_key = trigger_vehicle.get_order_control_batch_trigger_rank_key(s)
arrival_seconds = trigger_rank_key[0]
trigger_arrival_timestep = int(round(arrival_seconds / W.DELTAT))
```

各候補グループ：

```
remaining_distance = max(0, inlink.length - head_vehicle.x)
remaining_free_flow_timesteps = ceil((remaining_distance / inlink.u) / W.DELTAT)
snapshot_estimated_arrival_timestep = trigger_arrival_timestep + remaining_free_flow_timesteps
```

比較キー `(snapshot_estimated_arrival_timestep, head_vehicle.id)` の昇順でtrigger inlink以外を並べる。

`trigger_arrival_timestep` は全グループへ共通加算されるため、同一Vehicle位置snapshotでは通常グループ間相対順序は変わらない。切替理由は、現在訪問の時間軸で `snapshot_estimated_arrival_timestep` の絶対値を計算し、初回訪問の古いtrigger到着時刻と混在させないため。

#### 1H.21.10 form_order_control_batch()

`Node.form_order_control_batch()` 自体にlegacy arrival/earliestの直接参照はなかった。委譲先（trigger候補、t_trigger推定、inlink候補、group ordering）がcurrent visit参照へ変わることでBATCH形成全体がcurrent visitを使用する。batch ID、max batch size、assignment設定、service unit登録、形成後状態更新、返却値は変更していない。

#### 1H.21.11 再訪BATCH専用テスト（Step 2）

**ファイル：** `tests_order_control_batch_revisit_ranking.py`（15テスト）

確認範囲：current visit arrival_time/tiebreakerによるtrigger順位、`veh.id` fallback、trigger current visit欠如・到着情報欠如の `ValueError`、Level 0/1がcurrent visit arrival・earliestを使用、current visit earliestによるinlink候補包含/除外、inlink候補current visit欠如の `ValueError`、到着前Vehicleでarrival値Noneでも正常、legacy arrivalキーなしでもcandidate group ordering動作、snapshot比較キーの独立計算、同一訪問再登録でtrigger順位不変、`form_order_control_batch()` がcurrent visit順位のtriggerを使用。

candidate group orderingはlegacy値とcurrent visit値で順位逆転を期待するテストではない（trigger arrival_timeは全グループへ共通加算）。

#### 1H.21.12 既存BATCHテストの手動状態更新（Step 3）

Step 3のcommit `ae57e40` は合計**8ファイル**を変更した。うち7ファイルは手動Vehicle状態のcurrent visit対応、残る1ファイルは `tests_order_control_batch_service_queue_transfer.py`（order-control対象外Node進入後のlegacy earliest非記録・current visit終了の期待値更新）である。

Step 2後、次の7ファイルは手動Vehicle状態にcurrent visitがなく当初失敗した。

- `tests_order_control_batch_trigger_candidates.py`
- `tests_order_control_batch_t_trigger_estimation.py`
- `tests_order_control_batch_candidates_by_inlink.py`
- `tests_order_control_batch_candidate_group_ordering.py`
- `tests_order_control_batch_formation_integration.py`
- `tests_order_control_batch_transfer.py`
- `tests_order_control_batch_node_transfer_integration.py`

対応：到着済み/到着前用current visit同期補助関数追加、初回訪問ではlegacyとcurrent visitを同値、到着前はarrivalをNone、乱数なし、既存current visitは新visitを開始せず同期、`visit_id` 一致。

**Trigger候補の不完全到着状態：**

| 仕様 | 挙動 |
|------|------|
| 旧 | legacy到着キー欠如を黙って候補外 |
| Phase 4-6R後 | `route_next_link=None` は候補外。route_next_linkあり・assignmentなしでarrival欠如は `ValueError` |

分割テスト：`test_vehicle_without_route_next_link_is_excluded`、`test_candidate_with_missing_arrival_time_raises`、`test_candidate_with_missing_arrival_tiebreaker_raises`

**対象外Nodeへのリンク遷移（`test_link_transition_updates`）：** 旧期待はdestがlegacy earliest辞書に存在。Phase 4-6R後はdest（`order_control_eligible=False`）へlegacy earliestを追加せず、進入後 `current visit` は `None`。

**incoming_vehiclesクリア（`test_incoming_vehicles_cleared_on_success`）：** U1はBATCH形成対象外Vehicleをincomingに含めクリアのみ検証。`route_next_link=None` でtrigger候補外、current visitは追加しない。

#### 1H.21.13 回帰確認結果（Step 3）

**Phase 4-6R直結：** `tests_order_control_batch_current_visit_accessors.py`、`tests_order_control_batch_revisit_ranking.py`、`tests_order_control_batch_earliest_arrival_timestep.py`、`tests_order_control_current_visit_state.py`、`tests_order_control_current_visit_arrival.py`、`tests_fcfs_order_control_revisit_ranking.py` — すべてPASS

**BATCH単体・統合（12ファイル）：** 状態コンテナ、earliest arrival、trigger候補、t_trigger推定、inlink別候補、候補グループ順序、max batch size、service unit登録、service queue transfer、BATCH形成統合、BATCH transfer、BATCH `Node.transfer()` 統合 — すべてPASS。`test_fcfs_node_calls_fcfs_once` PASS、`test_n1_batch_vs_fcfs_equivalence` PASS

**FCFS回帰（6ファイル）：** tiebreaker、behavior、transfer、clearance_0、clearance_1、clearance_xyz — すべてPASS

**order-control共通（9ファイル）：** clearance設定、eligibility、Node属性、World setter、random eligible、Vehicle研究属性、車両リスト読込、RNG、node arrival times — すべてPASS

**baseline（既知値一致）：** completed 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、total distance 48000.0 m

**example（既知値一致）：** completed 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、total distance 1632250.0 m

**中規模ネットワーク（500 Vehicle）：** FCFS対standard — completed 383/500（ratio 0.766）、standard total travel time 53941.0 s、FCFS 56257.0 s、eligible FCFS Node 10、sanity checkすべてPASS。BATCH・FCFS・standard — completed 383/500、standard 53941.0 s、FCFS 56257.0 s、BATCH 56276.0 s、average travel time standard 140.8 s / FCFS 146.9 s / BATCH 146.9 s、BATCH/FCFS ratio 1.0003、eligible Node各10・集合一致、sanity checkすべてPASS。**性能優劣は合否基準ではない。**

**1,000台グリッド：** FCFS対standard — completed 1000/1000、standard 165917.0 s、FCFS 167772.0 s、eligible 36、sanity PASS。BATCH・FCFS・standard — completed 1000/1000、standard 165917.0 s、FCFS 167772.0 s、BATCH 167872.0 s、average travel time 165.9 / 167.8 / 167.9 s、BATCH/FCFS ratio 1.0006、差0.1 s、eligible各36・集合一致、sanity PASS。**性能優劣は合否基準ではない。**

**未実行（通常回帰）：** 5,000台・10,000台high-demand比較、signalized UXsim high-demand比較、`diagnostics/order_control/` 診断スクリプト（Phase 4-6T〜4-6U予定。**その後Phase 4-6Uで5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースを比較診断2本で実行・完了。§1H.24**。10,000台・clearance=0は未実行）

#### 1H.21.14 Phase 4-6Sへ残るassignment問題

`order_control_batch_assignments` は引き続きNode名key。候補除外条件 `s.name in veh.order_control_batch_assignments` により、初回訪問assignmentが残る再訪Vehicleは現在訪問未割当でもtrigger/inlink候補外またはprefix `ValueError` になり得る。Phase 4-6Rではこの条件を変更していない。current visitの `batch_assignment` もBATCH本体では未使用。

Phase 4-6Sで検討・実装：`batch_assignment` のBATCH本体接続、service unit `visit_id` 保存、Vehicle current visitとservice unit照合、実通過時assignment訪問対応、service完了時更新、current visit終了/破棄、過去訪問assignmentが再訪を妨げない設計。**既知のprefix violationはPhase 4-6Rでは解消していない。**

#### 1H.21.15 Phase 4-6R完了時点

- FCFSはcurrent visitの `arrival_time` と `arrival_tiebreaker` を参照する
- BATCH trigger順位もcurrent visitの `arrival_time` と `arrival_tiebreaker` を参照する
- BATCH t_triggerはcurrent visitの `arrival_time` と `earliest_arrival_timestep` を参照する
- BATCH inlink候補包含はcurrent visitの `earliest_arrival_timestep` を参照する
- candidate group orderingのtrigger基準時刻はcurrent visitの `arrival_time` を参照する
- legacy arrival辞書・legacy earliest辞書は初回訪問履歴として維持する
- 再訪時の現在制御にはcurrent visit値を使用する
- 同一訪問中の再登録では順位情報を上書きしない
- assignmentはまだNode訪問対応していない
- Phase 4-6Sは未着手
- 次工程はPhase 4-6S

### 1H.22 Phase 4-6S実装記録（BATCH assignmentの訪問対応）

**状態：** 実装・専用テスト・既存テスト更新・広い回帰確認・commit・push済み。

**実装commit：** `5e26bc9` — `phase 4-6S: move BATCH assignments to current visits and bind service units to per-vehicle visit IDs`

**最新実装commit：** `5e26bc9`

本体・専用テスト・既存テスト更新は1commitにまとめた。候補判定、assignment記録、service unit訪問記録、実通過照合が同じ状態モデルとして一体であるため。

**次工程：** 文書内の既存工程表（**§1H.14**・**§1H.17**）と現在の残課題を確認して設定する。（**その後Phase 4-6Tで小規模BATCH再訪end-to-end統合を完了。§1H.23**）

#### 1H.22.1 commitの役割

`5e26bc9`：

- BATCH assignmentの現在制御をcurrent visitへ移行
- service unitへのVehicleごとの `visit_id` 追加
- 実通過前の訪問・assignment照合
- registerロールバックのcurrent visit対応
- 専用テスト32件（`tests_order_control_batch_visit_assignment.py`）
- 既存テスト9ファイル更新

#### 1H.22.2 current visit assignmentの正式仕様

現在BATCH制御のassignmentは `Vehicle.order_control_current_visit["batch_assignment"]` を使用する。

| 値 | 意味 |
|----|------|
| `None` | 現在訪問では未割当。BATCH候補になり得る |
| 非負整数の `batch_id` | 現在訪問でそのbatch IDのservice unitへ割当済み。同じ訪問では新しいBATCH候補にしない |

追加したVehicleメソッド：

| メソッド | 役割 |
|----------|------|
| `_validate_order_control_batch_assignment_field_value(batch_assignment, node)` | `batch_assignment` フィールドの型検証（内部） |
| `get_order_control_batch_assignment(node)` | 現在訪問のassignmentを返す。`None` は未割当 |
| `has_order_control_batch_assignment(node)` | `get_order_control_batch_assignment(node) is not None` |
| `assign_order_control_batch_to_current_visit(node, batch_id)` | 現在訪問へbatch IDを設定。legacy辞書へは書き込まない |

`get_order_control_batch_assignment(node)`：BATCH用current visit取得ヘルパーを使用。current visitの存在・Nodeオブジェクト一致を確認。legacy `order_control_batch_assignments` は参照しない。

`has_order_control_batch_assignment(node)`：`ValueError` を握りつぶさない。

`assign_order_control_batch_to_current_visit(node, batch_id)`：batch IDは非負整数（bool拒否）。既存assignmentの上書きを拒否。legacy互換記録は `Node.register_order_control_batch_service_units()` が担当。

不正値（bool、負数、float、文字列、その他の型）は `ValueError`。

#### 1H.22.3 候補判定・t_trigger・prefix・orderingの変更

次の4メソッドでassignment参照をlegacy辞書からcurrent visitへ変更した。

- `Node.get_order_control_batch_trigger_candidates()`
- `Node._validate_order_control_batch_t_trigger_inputs()`
- `Node.get_order_control_batch_candidates_by_inlink()`
- `Node.get_ordered_order_control_batch_candidates_by_inlink()`

**Trigger候補：** `route_next_link` が存在し、current visit `batch_assignment` が `None`。現在訪問で割当済みなら例外を出さず候補外。過去legacy assignmentだけでは候補外にしない。

**t_trigger入力検証：** current visit `batch_assignment` が `None` なら正常。現在訪問で割当済みのVehicleがtriggerとして直接渡された場合は `ValueError`（通常経路ではtrigger候補取得時に除外されるため呼出し不整合）。

**inlink候補・prefix：** assigned/unassignedをcurrent visit assignmentで判定。正常なprefixはassigned群の後ろにunassigned群。unassignedを見た後にassignedが現れた場合は `ValueError`。過去legacy assignmentはprefix判定へ影響させない。

**candidate group ordering：** assignment prefix再検証、assignment済みVehicleの除外、trigger未割当検証をcurrent visit assignmentへ変更。

**変更していないもの：** trigger順位、t_trigger Level 0・Level 1の数式、earliest包含条件、prefixの物理的意味、candidate group orderingのsnapshot式、group比較キー、max batch size。

#### 1H.22.4 register処理

`Node.register_order_control_batch_service_units()` の事前検証（状態変更なし）：order-control対象、batch type、入力コンテナ、inlink重複拒否、Vehicle重複拒否、`veh.link` と登録inlinkの一致、`veh.state`、current visitの存在・Node一致・inlink一致、`visit_id` が正の整数、current visit `batch_assignment` が `None`。

登録時：inlinkグループごとにbatch IDを発行、current visitへbatch IDを設定、service unitへ `vehicles` と同順の `visit_ids` を保存、service queueへappend、batch next IDを更新。同じservice unit内のVehicleには同じbatch ID。別inlinkグループには別batch ID。

#### 1H.22.5 legacy `order_control_batch_assignments` の現在仕様

`veh.order_control_batch_assignments[node.name]`

| 時期 | 役割 |
|------|------|
| Phase 4-6Sより前 | 現在BATCH制御のassignment参照先。Node名keyのため訪問を区別できず、通過後も残るため再訪時に過去assignmentが現在assignmentとして解釈された |
| Phase 4-6S以降 | 初回訪問時のbatch IDを残すlegacy互換記録。同じNodeへの再訪時に初回値を上書きしない。候補判定、prefix、t_trigger入力検証、service実通過照合には使用しない。正式な全訪問assignment履歴ではない |

初回訪問：`legacy[node.name] = batch_id`、`current_visit["batch_assignment"] = batch_id`

再訪：`legacy[node.name]` は初回値のまま、`current_visit["batch_assignment"]` は再訪時の新batch_id

#### 1H.22.6 service unitの確定構造

```python
{
    "batch_id": int,
    "inlink": Link,
    "vehicles": list[Vehicle],
    "visit_ids": list[int],
}
```

`vehicles[i]` ↔ `visit_ids[i]`。`visit_ids[i]` は登録時点のVehicle current visit `visit_id`。Vehicleごとに発行。service unit全体に1つだけ保存しない。並列リスト方式で既存FIFO処理を維持。

#### 1H.22.7 registerロールバック

登録途中で例外が発生した場合、登録開始前へ戻す：

- current visit `batch_assignment`（書き込み先visit辞書への参照を保存し旧値を書き戻す）
- 今回新規追加したlegacyキーのみ削除（VehicleとNode名の組で記録。登録前から存在した初回値は変更しない）
- 今回appendしたservice unit
- `order_control_batch_next_id`

全登録が成功するか、登録開始前の状態へ完全に戻るかのどちらか。

#### 1H.22.8 service実通過前の検証

`Node.serve_order_control_batch_service_queue()` 内を `_validate_service_unit_visit()` と `_validate_service_unit_arrived_vehicle()` に分離。

`_validate_service_unit_visit()`（`incoming_vehicles` 確認より前）：

1. service unit必須キー4件
2. `batch_id` 取得
3. `batch_id` が非負整数でboolではない
4. `vehicles` と `visit_ids` がlist
5. 長さ一致
6. service中の `vehicles` が空でない
7. `registered_visit_id` 取得
8. `registered_visit_id` が正の整数でboolではない
9. current visitの存在
10. current visitのNode一致
11. current visitの `visit_id` 一致
12. current visit `batch_assignment` が `None` でない
13. current visit `batch_assignment` とservice unit `batch_id` の一致

構造不正・visit不一致・batch ID不一致は `ValueError`（待機しても解消しない重大不整合）。

**実通過処理の順序：**

1. service unit構造と現在訪問を照合
2. `incoming_vehicles` 確認
3. 未到着ならservice unitを維持して待機
4. 到着済みなら `veh.link` とservice unit inlinkを照合
5. 到着済みなら `route_next_link` を確認
6. clearance・物理先頭・各容量・lane・move_remainを確認
7. Link遷移

| 状況 | 挙動 |
|------|------|
| 同じ訪問で未到着 | 待機 |
| `route_next_link` 属性がない未到着Vehicle | 経路確認前に待機 |
| `visit_id` 不一致 | `ValueError` |
| batch ID不一致 | `ValueError` |
| 到着済みで `route_next_link=None` | `ValueError` |
| 到着済みだが交通条件不足 | 正常な待機または通過停止 |

#### 1H.22.9 通過成功後の更新

通過成功時に同時実行：

```python
service_unit["vehicles"].pop(0)
service_unit["visit_ids"].pop(0)
```

空service unitは既存処理でqueueから除去。訪問不一致等の異常unitは自動削除せず `ValueError` で検出（stale unit自動削除とは区別）。

**current visit：** 実通過前にvisit ID・batch IDを照合。通過元 `batch_assignment` を明示的に `None` へ戻さない。outlink進入で `begin_order_control_visit_on_link_entry()` を呼び、次Nodeがorder-control対象なら新current visitへ置換、対象外なら `None`。Link遷移後に通過元current visitへ書き込まない。Phase 4-6Sではassignment履歴を作らない。

#### 1H.22.10 既知prefix violationへの対応

Phase 4-6N診断の既知問題（例：Vehicle `veh_1619`、Node `g_4_1`、過去assignment batch 318、再訪時現在訪問は未割当、inlink前方に未割当 `veh_1651`、後方 `veh_1619` がlegacy assignmentによりassignedと誤認、prefix violation）について：

| Phase | 状態 |
|-------|------|
| Phase 4-6R | arrival・earliest・trigger順位をcurrent visit対応。assignment問題は当時未解決 |
| Phase 4-6S | assigned/unassignedをcurrent visit `batch_assignment` で判定。過去batch 318は現在prefixへ影響しない。再訪Vehicleが現在訪問では未割当ならunassignedとして扱う。assignment由来の根本原因へ対応し、通常回帰・縮小再現テストで問題が再現しないことを確認（high-demand実ネットワークでの再確認は未実施） |

Phase 4-6Sではassignment由来の根本原因へ対応し、通常回帰・縮小再現テストで問題が再現しないことを確認した。high-demand診断スクリプト自体は今回実行していない。high-demand実ネットワークでの再確認は未実施である。

#### 1H.22.11 新規専用テスト

**ファイル：** `tests_order_control_batch_visit_assignment.py`（32件）

| 分類 | 内容 |
|------|------|
| A | assignment accessor（未割当None、割当済み、current visit欠如、Node不一致、型不正） |
| B | assignment設定（正常登録、二重拒否、batch ID型不正） |
| C | trigger候補（legacy無影響、現在割当除外、t_trigger直接渡し `ValueError`） |
| D | prefix（legacy無影響、current visit prefix違反） |
| E | register（初回、再訪legacy維持、複数visit_ids、既存assignment拒否、ロールバック） |
| F | 正常service（実通過、対象外Node遷移） |
| G | service検証（current visit欠如、Node不一致、visit_id不一致、batch_assignment欠如、batch ID不一致、長さ不一致、batch_idキー欠如、batch_id型不正、registered visit_id型不正） |
| H | 待機（正常未到着、visit_id不一致を未到着と誤認しない） |
| I | 並列リスト同期（複数Vehicle通過時の同期削除） |

#### 1H.22.12 既存テスト更新（9ファイル）

- `tests_order_control_batch_candidate_group_ordering.py`
- `tests_order_control_batch_candidates_by_inlink.py`
- `tests_order_control_batch_node_transfer_integration.py`
- `tests_order_control_batch_service_queue_transfer.py`
- `tests_order_control_batch_service_unit_registration.py`
- `tests_order_control_batch_t_trigger_estimation.py`
- `tests_order_control_batch_transfer.py`
- `tests_order_control_batch_trigger_candidates.py`
- `tests_order_control_current_visit_state.py`

registerテストは正式registerを使用。service・Link遷移テストはregisterを新たに呼ばず手動設定。候補・prefixテストはservice unitを作らずcurrent visit assignmentのみ。trigger順位、t_trigger数値、earliest包含、candidate group ordering、max batch size、batch ID発行順、service queue順、clearance、容量、lane、move_remain、Link遷移、N=1 BATCHとFCFS等価性の期待値は変更していない。

#### 1H.22.13 回帰確認結果

**BATCH限定：** Step 1専用・current visit基盤、BATCH候補・形成、service queue・実通過の全ファイルPASS。`test_fcfs_node_calls_fcfs_once` PASS、`test_n1_batch_vs_fcfs_equivalence` PASS。

**FCFS回帰（6ファイル）・order-control共通（9ファイル）：** すべてPASS。

**baseline：** completed 48/48、average speed 16.5 m/s、total travel time 2928.0 s、average travel time 61.0 s、average delay 1.0 s、total distance 48000.0 m（既知値一致）

**example：** completed 735/810、average speed 11.7 m/s、total travel time 119475.0 s、average travel time 162.6 s、average delay 62.6 s、total distance 1632250.0 m（既知値一致）

**中規模（500 Vehicle）：** 全方式 completed 383/500（ratio 0.766）。standard total travel time 53941.0 s、FCFS 56257.0 s、BATCH 56276.0 s。average travel time standard 140.8 s / FCFS 146.9 s / BATCH 146.9 s。BATCH/FCFS ratio 1.0003。eligible Node各10・集合一致。sanity check全9項目（FCFS対standard）・全16項目（3方式）PASS。Phase 4-6R参考値と完全一致。

**1,000台グリッド：** 全方式 completed 1000/1000。standard 165917.0 s、FCFS 167772.0 s、BATCH 167872.0 s。average travel time 165.9 / 167.8 / 167.9 s。BATCH/FCFS ratio 1.0006、差0.1 s。eligible各36・集合一致。sanity check全9項目・全20項目PASS。Phase 4-6R参考値と完全一致。

**性能優劣はPhase 4-6Sの合否基準ではない。**

**未実行（通常回帰）：** 5,000台・10,000台high-demand比較、signalized UXsim high-demand比較、`diagnostics/order_control/` 診断スクリプト。

#### 1H.22.14 後続工程へ残す課題

**trip-end Vehicle：** `route_next_link=None` ならtrigger候補外だがinlink候補・service unit登録の可能性あり。到着済み実通過で `ValueError`。Phase 4-6Sでは変更していない。

**stale service unit：** 正常完了unitは全Vehicle通過後にqueueから削除。異常unit（visit_id不一致、batch ID不一致、Vehicleが別訪問へ進行）は `ValueError` で検出し自動削除しない。

**assignment履歴：** Phase 4-6Sで実装したのは現在制御のcurrent visit assignmentとlegacy初回互換記録のみ。全訪問履歴、assigned/served/cancelled時刻、取引履歴統合は未実装。正式履歴はUXsim標準・FCFS・BATCH・Time-value Transactionを横断して後続設計。

#### 1H.22.15 Phase 4-6S完了時点の状態

- FCFS順位はcurrent visit参照
- BATCH arrival・earliest・trigger順位はcurrent visit参照
- BATCH assignmentもcurrent visit参照
- service unitはVehicleごとの `visit_id` を保持
- 実通過前にservice unitとcurrent visitの訪問を照合
- legacy arrival・earliest辞書は初回訪問履歴
- legacy assignment辞書は初回batch IDの互換用記録（現在制御に使用しない）
- 再訪Vehicleは現在訪問のassignmentで判定
- 過去assignmentは現在prefixへ影響しない
- assignment由来の既知prefix violationの根本原因へ対応し、通常回帰・縮小再現テストで問題が再現しないことを確認（high-demand実ネットワークでの再確認は未実施）
- trip-end、stale unit自動処理、全訪問履歴は未実装

### 1H.23 Phase 4-6T実装記録（小規模BATCH再訪end-to-end統合）

**状態：** 実装・回帰確認・commit・push済み（`b7159f9`）。

**実装commit：** `b7159f9` — `phase 4-6T: verify initial and repeat BATCH service at the same node through Node.transfer`

**最新実装commit：** `b7159f9`

本体変更なし。新規テスト1ファイルのみ。

#### 1H.23.1 Phase 4-6Tの調査結果

**文書上の定義：** 統合・小規模再訪テスト。

**Phase 4-6S完了時点で確認済みだったもの：**

- 再訪時のcurrent visitによる候補判定
- legacy assignmentが現在候補・prefixへ影響しない
- 再訪register時にlegacy初回値を上書きしない
- service unitへの `visit_id` 保存
- visit_id・batch ID不一致の検出
- 単回のBATCH形成・実通過
- current visitの再訪時更新

**不足していたもの：** 同一Vehicleの初回訪問から再訪時の二回目実通過までを、通常の `Node.transfer()` 経路で一続きに確認する小規模統合テスト。

Phase 4-6S完了時点では一部実施済みで、工程定義全体の完了は未確認だった。その後Phase 4-6Tでこの不足を新規テスト1本で補い、完了した。

#### 1H.23.2 新規テストの目的

`tests_order_control_batch_revisit_integration.py` の `test_same_vehicle_revisits_batch_node_and_completes_both_service_units` は、Phase 4-6Sの単体・手動再訪テストでは検証できなかった、同一Vehicleによる同一BATCH Nodeへの初回形成・初回実通過・再訪形成・再訪実通過の連続確認を行う。

#### 1H.23.3 World・route構成

**Node：**

| Node | 役割 |
|------|------|
| orig1 | 出発地 |
| orig2 | ループ戻り点 |
| merge | 対象BATCH Node |
| mid | 中間Node |
| dest | 最終目的地（order-control対象外） |

**Link：**

| Link | 経路 |
|------|------|
| link1 | orig1 → merge |
| out | merge → mid |
| mid_orig2 | mid → orig2 |
| link2 | orig2 → merge |
| out2 | merge → dest |

**固定route：** link1 → out → mid_orig2 → link2 → out2（`enforce_route()` で固定）

**Vehicle：** 1台（`veh_revisit_batch`、orig1 → dest）

#### 1H.23.4 BATCH設定

- `deltan=1`、`tmax=400`、`random_seed=0`
- `batch_size=1`、`order_control_batch_t_trigger_level=0`
- `order_control_clearance_timesteps=0`
- 単車線、Vehicle 1台

Node-local batch IDは初回 `0`、再訪 `1` と連続発行される。

本テストはLevel 0の研究評価ではなく、BATCH形成・登録・実通過の統合経路を決定的に確認するためのものである。研究の通常方式がLevel 2である方針は変更していない。

#### 1H.23.5 通常呼出し経路

初回・再訪とも `merge.transfer()` を呼ぶ。`Node.transfer()` から内部的に `transfer_batch()` → `form_order_control_batch()` → `register_order_control_batch_service_units()` → `serve_order_control_batch_service_queue()` の通常経路を使用する。

テストから直接呼んでいないもの：`assign_order_control_batch_to_current_visit()`、`register_order_control_batch_service_units()`、`serve_order_control_batch_service_queue()`。

register直後の状態観測にはoutlink容量ブロックを使用した。容量復帰後に `merge.transfer()` で実通過させた。

#### 1H.23.6 初回訪問の確認結果

- current visitのNode：merge、inlink：link1
- `first_visit_id`：1
- 登録前 `batch_assignment`：None
- `first_batch_id`：0
- 初回service unitの `batch_id`：0、`visit_ids`：`[1]`
- 初回legacy assignment：0
- Vehicleがlink1からoutへ実通過
- 通過後service queue：空、current visit：None（outの終点midはorder-control対象外）

#### 1H.23.7 再訪の確認結果

- current visitのNode：同じmerge、inlink：link2
- `revisit_visit_id`：2（`> first_visit_id`）
- 再訪登録前 `batch_assignment`：None
- legacy assignment：初回値0のまま
- `revisit_batch_id`：1（`!= first_batch_id`）
- 再訪service unitの `batch_id`：1、`visit_ids`：`[2]`（初回の `[1]` ではない）
- Vehicleがlink2からout2へ実通過
- 再訪通過後service queue：空、current visit：None（out2の終点destはorder-control対象外）
- Vehicleは最終的に `state="end"`

#### 1H.23.8 assignment・visit IDの関係

| 訪問 | visit_id | batch_id | legacy assignment | service unit visit_ids |
|------|----------|----------|-------------------|------------------------|
| 初回 | 1 | 0 | 0 | [1] |
| 再訪 | 2 | 1 | 0のまま | [2] |

- `visit_id` は訪問ごとに更新される
- batch IDはservice unitごとに更新される
- legacy assignmentは初回値を保持する
- 現在制御は再訪current visitの `batch_assignment` を使用する
- service unitは再訪時の `visit_id` を保持する

#### 1H.23.9 service queue完了

初回・再訪とも、実通過後にservice queueが空になり、正常なservice unitがqueueへ残らないことをPhase 4-6Tのend-to-endテストで確認した。service unit内のvehiclesとvisit_idsの同期削除そのものはPhase 4-6Sの専用テストで確認済みであり、Phase 4-6Tではその処理を含む通常経路が正常完了することを確認した。

未実装のまま：visit_id不一致等の異常stale unitの自動削除・自動回復。

#### 1H.23.10 prefix violationの確認範囲

過去legacy assignmentを持つ再訪Vehicleが、通常の `Node.transfer()` 経路で再形成・再通過でき、prefix `ValueError` が発生しないことを確認した。テストはVehicle 1台のため、前方未割当Vehicleと後方legacy再訪Vehicleの歴史的縮小配置は再現していない。

| Phase | 確認範囲 |
|-------|----------|
| Phase 4-6S | 前方・後方配置によるprefix根本条件を候補抽出で確認（`test_d1_legacy_assignment_does_not_affect_prefix`） |
| Phase 4-6T | 同一Vehicleの再訪を通常経路で形成・登録・実通過まで確認 |
| Phase 4-6U | high-demand実ネットワーク（U1〜U3）で既知assignment prefix violationは再発しなかった（§1H.24） |

#### 1H.23.11 回帰結果

Phase 4-6T Step 2で次の19ファイルがすべてPASS。

**再訪・current visit関連（7）：** `tests_order_control_batch_revisit_integration.py`、`tests_order_control_batch_visit_assignment.py`、`tests_order_control_batch_revisit_ranking.py`、`tests_order_control_batch_current_visit_accessors.py`、`tests_order_control_current_visit_state.py`、`tests_order_control_current_visit_arrival.py`、`tests_order_control_batch_earliest_arrival_timestep.py`

**BATCH候補・形成（8）：** `tests_order_control_batch_state_containers.py`、`tests_order_control_batch_trigger_candidates.py`、`tests_order_control_batch_t_trigger_estimation.py`、`tests_order_control_batch_candidates_by_inlink.py`、`tests_order_control_batch_candidate_group_ordering.py`、`tests_order_control_batch_max_size_application.py`、`tests_order_control_batch_service_unit_registration.py`、`tests_order_control_batch_formation_integration.py`

**BATCH service・統合（3）：** `tests_order_control_batch_service_queue_transfer.py`、`tests_order_control_batch_transfer.py`、`tests_order_control_batch_node_transfer_integration.py`（`test_fcfs_node_calls_fcfs_once`、`test_n1_batch_vs_fcfs_equivalence` 含む）

**FCFS再訪（1）：** `tests_fcfs_order_control_revisit_ranking.py`

**実行しなかったもの：** baseline、example、中規模比較、1,000台グリッド比較、5,000台・10,000台high-demand、signalized UXsim high-demand、`diagnostics/order_control/` 配下の診断スクリプト。変更は新規テスト1ファイルのみで本体変更なし。Phase 4-6Sで広い回帰を完了済みのため、Phase 4-6Tでは小規模再訪統合とBATCH関連回帰に限定した。

#### 1H.23.12 対象外項目

Phase 4-6Tで実装していないもの：trip-end Vehicle対応、stale異常unitの自動削除・回復、assignment正式全訪問履歴、Level 2仮想サービス推定、Level 2 unresolved時のLevel 1 fallback接続、Time-value Transaction。

trip-end Vehicleとstale unitの工程位置は未確定。assignment全訪問履歴は分析項目が明確になった後に横断設計する。

#### 1H.23.13 Phase 4-6Uへの移行条件

Phase 4-6T完了により、次はPhase 4-6Uとしてhigh-demand再実行と既知prefix violationの実ネットワーク再確認へ進む。

- 5,000台・clearance=0 → 5,000台・clearance=1 → 10,000台・clearance=1
- 必要に応じて `diagnostics/order_control/` 配下の診断資料を参照
- signalized UXsim high-demand比較

#### 1H.23.14 Phase 4-6T完了時点の状態

- 同一Vehicleが同じBATCH Nodeを二回訪問し、初回・再訪とも `Node.transfer()` 経由でBATCH形成・登録・実通過を完了
- `visit_id` 1 → 2、batch ID 0 → 1、legacy assignment 0を維持
- 正常な初回・再訪service unitは完了後queueから削除される
- BATCH関連19ファイル回帰PASS、本体変更なし
- high-demand実ネットワークでの再確認はPhase 4-6Uで実施予定

### 1H.24 Phase 4-6U実行記録（high-demand再実行・既知prefix violation非再発確認）

**状態：** 再実行・検証完了。本体・テスト・診断Pythonコード変更なし。結果は本節に記録する。

**位置づけ：** Phase 4-6Uは実行・検証フェーズである。新しい実装commitはない。**最新実装commit** は引き続き `b7159f9`（Phase 4-6T）。**直前の文書commit（Phase 4-6T）** は `aca6ce9`。文書更新前のHEADは `aca6ce9`。

#### 1H.24.1 目的

Phase 4-6S（current visit assignment対応）・Phase 4-6T（小規模再訪end-to-end統合）後、Node再訪・BATCH assignment対応がhigh-demand実ネットワークでも正常に動作し、Phase 4-6S以前のassignment由来既知prefix violationが再発しないことを確認する。

性能上BATCHがFCFSまたはsignalized UXsimより優れることは合否条件ではない。

#### 1H.24.2 実行条件（共通）

- 6×6 grid、`random_seed=0`、`DEMAND_GEN_SEED=42`
- BATCH Level 1、`batch_size=10`、`order_control_batch_t_trigger_level=1`
- FCFS・BATCHのeligible Node：内部36 Node、集合一致
- 比較診断は `diagnostics/order_control/` 配下（通常回帰テストではない）
- 補助診断（lifecycle・node revisit）は今回未実行

#### 1H.24.3 Case U1（5,000台・clearance=0）

**実行ファイル：** `diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py`

**条件：** 5,000台、departure 0–500、tmax=30,000、FCFS clearance=0、BATCH clearance=0、signalized UXsim `signal=[60, 60]`。

**実行結果：**

- exit code：0
- 実行時間：67秒
- 最終成功メッセージ：`BATCH Level 1 vs FCFS clearance=0 vs signalized UXsim grid high-demand 5000 test passed.`
- sanity check：全20項目PASS
- assignment prefix violation：なし
- visit_id mismatch：なし
- batch_assignment mismatch：なし
- service unit構造不正：なし

| 方式 | completed | avg travel time | total travel time | avg delay | total distance | unfinished | last completed |
|------|-----------|-----------------|-------------------|-----------|----------------|------------|----------------|
| signalized UXsim | 5,000/5,000 (1.000) | 1,432.9 s | 7,164,538.0 s | 1,268.3 s | 23,185,600.0 m | 0 | 3,449.0 s |
| FCFS c=0 | 5,000/5,000 (1.000) | 821.2 s | 4,106,096.0 s | 656.6 s | 18,424,000.0 m | 0 | 1,922.0 s |
| BATCH L1 c=0 | 5,000/5,000 (1.000) | 1,027.3 s | 5,136,397.0 s | 862.7 s | 19,844,000.0 m | 0 | 2,525.0 s |

**比較（観測値）：** BATCH/FCFS avg TT ratio 1.251、total TT ratio 1.251、distance ratio 1.077。BATCH/signalized avg TT ratio 0.717、total TT ratio 0.717、distance ratio 0.856。average speedは既存出力なし。

**既知問題との比較（Phase 4-6S以前）：** W.T=605・Node `g_4_1`・inlink `v_5_4_1`・veh_1619（過去assignment batch 318）・前方veh_1651でassignment prefix violation停止していた。Case U1ではBATCHはlast completed trip time 2,525.0 sまで完走、5,000/5,000完了、prefix violationなし。同一条件のhigh-demand比較がprefix violationなしで完走し、既知停止地点を越えた。通常比較ログではveh_1619等の個別lifecycleは出力されていない。個別Vehicle lifecycle診断は今回実行しておらず、veh_1619の内部状態を個別には確認していない。

#### 1H.24.4 Case U2（5,000台・clearance=1）

**実行ファイル：** `diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py`（Case U2とU3を連続実行）

**条件：** 5,000台、departure 0–500、tmax=30,000、FCFS clearance=1、BATCH clearance=1、signalized UXsim all-red相当、`signal=[60, 1, 60, 1]`、staggered offset。

**実行結果（Case U2部分）：**

- スクリプト全体exit code：0（Case U2完了後Case U3へ進行）
- スクリプト総実行時間：331秒（U2+U3合計）
- sanity check：全24項目PASS
- assignment prefix violation：なし
- visit_id mismatch：なし
- batch_assignment mismatch：なし
- service unit構造不正：なし

| 方式 | completed | avg travel time | total travel time | avg delay | total distance | unfinished | last completed |
|------|-----------|-----------------|-------------------|-----------|----------------|------------|----------------|
| signalized all-red | 5,000/5,000 (1.000) | 1,102.0 s | 5,510,114.0 s | 937.4 s | 20,188,000.0 m | 0 | 2,724.0 s |
| FCFS c=1 | 5,000/5,000 (1.000) | 1,573.2 s | 7,866,209.0 s | 1,408.6 s | 19,571,200.0 m | 0 | 3,409.0 s |
| BATCH L1 c=1 | 5,000/5,000 (1.000) | 1,147.1 s | 5,735,703.0 s | 982.5 s | 18,976,800.0 m | 0 | 2,348.0 s |

**比較（観測値）：** BATCH/FCFS avg TT ratio 0.729、total TT ratio 0.729、distance ratio 0.970。BATCH/signalized avg TT ratio 1.041、total TT ratio 1.041、distance ratio 0.940。average speedは既存出力なし。

**既知問題との比較（Phase 4-6S以前）：** 5,000台BATCH clearance=1でprefix violation（Node `g_5_4`、inlink `h_5_3_4`、Vehicle `veh_1952`）。BATCH停止により10,000台未到達。Case U2ではBATCHはlast completed trip time 2,348.0 sまで完走、5,000/5,000完了、prefix violationなし、Case U3へ進行。同一5,000台clearance=1比較条件は正常終了。過去の停止は再発しなかった。veh_1952の個別lifecycle追跡は今回行っていない。

#### 1H.24.5 Case U3（10,000台・clearance=1）

**条件：** 10,000台、departure 0–500、tmax=50,000、FCFS clearance=1、BATCH clearance=1、signalized UXsim all-red相当、`signal=[60, 1, 60, 1]`、staggered offset。

**実行結果：**

- 過去はCase U2でBATCH停止のため10,000台BATCHは未実行だった
- Phase 4-6Uで初めて10,000台BATCHの結果出力まで到達
- sanity check：全24項目PASS
- assignment prefix violation：なし
- visit_id mismatch：なし
- batch_assignment mismatch：なし
- service unit構造不正：なし

| 方式 | completed | avg travel time | total travel time | avg delay | total distance | unfinished | last completed |
|------|-----------|-----------------|-------------------|-----------|----------------|------------|----------------|
| signalized all-red | 10,000/10,000 (1.000) | 2,699.0 s | 26,989,929.0 s | 2,534.1 s | 50,367,200.0 m | 0 | 5,703.0 s |
| FCFS c=1 | 10,000/10,000 (1.000) | 3,329.3 s | 33,293,441.0 s | 3,164.4 s | 39,892,000.0 m | 0 | 6,492.0 s |
| BATCH L1 c=1 | 10,000/10,000 (1.000) | 3,011.9 s | 30,119,206.0 s | 2,847.0 s | 40,996,000.0 m | 0 | 5,382.0 s |

**比較（観測値）：** BATCH/FCFS avg TT ratio 0.905、total TT ratio 0.905、distance ratio 1.028。BATCH/signalized avg TT ratio 1.116、total TT ratio 1.116、distance ratio 0.814。average speedは既存出力なし。

#### 1H.24.6 prefix violation・状態不整合の確認

U1〜U3すべてで次を確認した。

- assignment prefix violation：なし
- visit_id mismatch：なし
- batch_assignment mismatch：なし
- service unit構造不正：なし
- AssertionError・想定外例外：なし
- FCFS・BATCH eligible Node各36、集合一致
- Vehicle数・需要条件一致
- 全方式completed ratio 1.000、unfinished 0

Phase 4-6Sのcurrent visit assignment対応と、Phase 4-6Tの再訪end-to-end確認が、今回のhigh-demand条件でも正常に動作した。個別Vehicleのlifecycle診断は実行しておらず、今回の確認は全Vehicleの内部履歴を個別監査したものではない。

Phase 4-6Uで実行したU1〜U3のhigh-demand条件では、既知assignment prefix violationは再発しなかった（他条件での非再発を一般化しない）。

#### 1H.24.7 sanity check

- Case U1：20項目すべてPASS
- Case U2：24項目すべてPASS
- Case U3：24項目すべてPASS

#### 1H.24.8 性能値の位置付け

性能値は観測結果として記録する。合否条件は正常終了・状態整合性・既知prefix violation非再発である。

**観測された関係：**

- Case U1：BATCHはFCFSよりaverage travel timeが長い。BATCHはsignalized UXsimより短い。
- Case U2：BATCHはFCFSよりaverage travel timeが短い。BATCHはsignalized UXsimよりわずかに長い。
- Case U3：BATCHはFCFSよりaverage travel timeが短い。BATCHはsignalized UXsimより長い。

性能差は経路・総走行距離も方式間で異なるため、単純な制御方式だけの因果効果として断定しない。追加分析には経路差・距離差・再訪率等の検討が必要である。

#### 1H.24.9 実行時間

| ケース | 実行時間 |
|--------|----------|
| Case U1（単独スクリプト） | 67秒 |
| Case U2+U3（同一スクリプト） | 331秒（合計） |

#### 1H.24.10 補助診断の扱い

今回未実行：

- `diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py`
- `diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py`

理由：U1〜U3がすべてexit 0、prefix violationが再発せず、追加の原因追跡が不要だった。診断Pythonファイル自体は変更・削除していない。

#### 1H.24.11 未実行項目

- 上記補助診断2本
- FCFS high-demand単独比較テスト
- baseline、example、中規模比較、1,000台通常グリッド比較
- 10,000台clearance=0（既存BATCH 3方式比較ファイルなし。Phase 4-6U既定順にも含まれない）
- Level 2、Time-value Transaction

#### 1H.24.12 Phase 4-6U完了時点の状態

- Phase 4-6Uは再実行・検証完了
- U1〜U3すべて正常終了
- 5,000台clearance=0：全方式5,000/5,000
- 5,000台clearance=1：全方式5,000/5,000
- 10,000台clearance=1：全方式10,000/10,000（10,000台BATCHは今回初到達）
- 全方式completed ratio 1.000、unfinished 0
- FCFS・BATCH eligible Node集合一致
- 本体・テスト・診断Pythonコード変更なし
- 最新実装commit：`b7159f9`
- 結果は本節に記録する

#### 1H.24.13 後続課題

- trip-end Vehicleとstale service unitの工程位置決定
- Level 2仮想サービス推定（研究の通常方式。未実装）
- Level 2 unresolved時のLevel 1 fallback接続（未実装）
- assignment正式全訪問履歴（分析項目明確化後に横断設計）
- Time-value Transaction本体

### 1H.25 Phase 4-6V：zero-service追加形成・size-one BATCHとFCFSの等価性・batch size予備比較

**状態：** Phase 4-6V本体修正・正式テストは `2b10b08` でpush済み。既存診断2本の初期版は `fe9e53e` でpush済み。補正signal baselineモード（`--corrected-signal-baseline-only`）と本節の補足記録は、その後の比較条件訂正に伴う後続更新として追加した。

**本体修正・正式テストcommit：** `2b10b08` — `phase 4-6 fix: reform BATCH after zero service and restore size-one BATCH equivalence with FCFS`

**診断スクリプトcommit（初期版）：** `fe9e53e` — `phase 4-6 diagnostics: verify size-one BATCH equivalence with FCFS and recheck N=10 vs N=20`

**最新実装commit：** `2b10b08`

進捗の詳細・診断数値は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) のフェーズ4-6V節を参照。診断スクリプトの実行方法は `diagnostics/order_control/README.md` を参照。

#### 1H.25.1 size-one BATCHとFCFSの確認対象となる不変条件

同じclearance、同じ候補順位、Level 1条件において、size-one BATCH（`batch_size=1`）はFCFSと確認対象の交通結果が一致することを目標とする。

これは確認済みnetwork・需要・seed・制御条件における実装不変条件であり、全条件に対する一般的理論証明とは書かない。

#### 1H.25.2 修正前の構造差

**FCFS：**

- blocked候補をcontinueで飛ばす
- 同一timestep内で次候補を評価する

**旧BATCH：**

- 一回だけformする
- 一回だけregisterする
- 一回だけserveする
- zero-serviceでも次候補を形成しない

#### 1H.25.3 修正後の反復

概念的な処理：

1. `Node.transfer()` / `transfer_batch()` 開始時のtrigger snapshotを固定
2. form
3. register
4. serve
5. zero-serviceかつ停止理由なしなら、次の未割当trigger候補を検討
6. 必要に応じてform・register・serveを反復
7. 一台以上通過、clearance停止、arrival wait、候補枯渇等で終了

#### 1H.25.4 trigger snapshot

- `transfer_batch()` 開始時に一度だけ作成
- キーは `(vehicle.id, visit_id)`
- same-node revisitの別visitを区別
- 反復中に拡張しない
- batch member候補全体を `incoming_vehicles` だけへ限定するものではない
- `t_trigger` に基づく既存batch member候補取得は維持

#### 1H.25.5 blocked inlinkの意味

clearance以外の通過不能条件により、その `transfer_batch()` 呼出し内で追加形成対象から一時的に除外するinlink：

- outlink空間不足
- inlink流出容量不足
- outlink流入容量不足
- Node容量不足
- inlinkの先頭Vehicleが通過できない等

**`blocked_inlinks`：**

- 同一 `transfer_batch()` 呼出し内で共有するset
- 次timestepへ持ち越さない
- blocked service unitはqueueへ保持
- assignment・batch ID・visit IDを維持
- 次timestepでは再評価可能
- same-inlink FIFO上、先頭Vehicleを追い越して後続Vehicleを処理しない

#### 1H.25.6 clearance停止との違い

- clearance未充足はFCFSと同様に候補走査を停止する
- clearance未充足のinlinkを `blocked_inlinks` へ追加しない
- clearance未充足の候補を飛ばして別方向へ進まない
- 次timestepで再評価する

#### 1H.25.7 arrival wait停止

- queue先頭service unitの先頭VehicleがNode端へ未到着
- Vehicleが `incoming_vehicles` へ未登録
- queue順を維持する
- 後続service unitを評価しない
- 同一 `transfer_batch()` 呼出し内で追加batchを形成しない
- `blocked_inlinks` へ追加しない
- 次timestepで再評価する

#### 1H.25.8 一台以上通過後

- 一度のserve処理内では通過可能なVehicleを複数台処理できる
- 最初の一台が通過した時点でserve自体を打ち切らない
- 一台以上通過した場合に終了するのは、次の追加形成反復
- 部分通過後に別batchを追加形成しない

#### 1H.25.9 N>=1への一般化

- size-one専用hackではない
- N>1のzero-serviceにも適用する
- N上限到達・未到達を追加形成条件に使用しない
- triggerが変われば `t_trigger` も変わり得る
- 最初のtriggerでは候補外だったVehicleが、次のtriggerでは候補になり得る

#### 1H.25.10 Link容量・Node容量の技術前提

今回のgrid条件：

- `free_flow_speed`=20 m/s
- `jam_density`=0.2 veh/m
- `number_of_lanes`=1
- `reaction_time`=1 s
- `DELTAN`=1
- `DELTAT`=1 s

UXsim既定式によるLink基礎容量：0.8 veh/s

未指定時：

- `capacity_out`=基礎容量×2=1.6 veh/s
- `capacity_in`=基礎容量×2=1.6 veh/s

Node：

- `flow_capacity`=`None`
- 実質無制限

実通過判定で使用：

- `inlink.capacity_out_remain`
- `outlink.capacity_in_remain`
- `node.flow_capacity_remain`

#### 1H.25.11 UXsim signal制御の離散実装と補正signal setting

**UXsim本体は変更していない。** 今回行ったのは、現行UXsim実装を前提とした比較用signal settingの補正である。

**`signal_control()` の境界条件（現行実装）：**

- phase切替条件：`signal_t > signal[signal_phase]`（`>=` ではない）
- 各 `Node.update()` 内で `signal_control()` が実行され、その後 `Node.transfer()` が参照する
- `exec_simulation()` の順序：Link.update → Node.generate → **Node.update** → **Node.transfer**

**off-by-one挙動（`DELTAT`=1秒）：**

- 設定値59 → transfer判定上 **60 timesteps**
- 設定値1 → transfer判定上 **2 timesteps**
- 設定値0 → transfer判定上 **1 timestep**（zero-duration phase）

**旧signal `[60,1,60,1]`（historical condition）：**

- 設定意図：green 60秒、all-red 1秒、green 60秒、all-red 1秒
- 実効完全phase長：**[61, 2, 61, 2]** timesteps、実効cycle **126** timesteps
- 設定cycle length：122秒、offset step：30.5秒、offset値：{0.0, 30.5, 61.0, 91.5}
- 意図した実効60/1/60/1を実現していない。現行の公平なFCFS/BATCH対signal baselineには使用しない

**補正signal `[59,0,59,0]`（corrected comparison setting）：**

- 設定値：**[59, 0, 59, 0]**
- 実効完全phase長：**[60, 1, 60, 1]** timesteps、実効cycle **122** timesteps
- 設定cycle length：118秒、offset step：29.5秒、offset値：{0.0, 29.5, 59.0, 88.5}
- offset計算式は旧signalと同じ：`((row + column) % 4) * (sum(signal_setting) / 4)`

**実Node確認（`Node.update()`、PASS判定の根拠）：**

- offset 0.0、29.5、59.0、88.5 の全4値で、初回不完全cycle後の定常完全phase長が60/1/60/1
- 方向変更時系列（offset=0）：T=旧方向green、T+1=all-red相当、T+2=新方向green

**order-control clearance=1との対応（補正signal条件）：**

- FCFS/BATCH：T=旧方向通過、T+1=別方向禁止、T+2=別方向可能
- 補正signal：T=旧方向green、T+1=all-red、T+2=新方向green
- **方向変更1回あたりの実効通過禁止timestep数は一致する**
- ただし発生契機・頻度・green継続・需要応答性は異なり、制御方式全体が同一ではない

**旧signal `[60,1,60,1]` では** 実効all-red 2 timestepsのため、上記の局所時系列対応は成立しない。

#### 1H.25.12 補正signal対修正後BATCH N=10（現行比較）

**Case：** `S_CORRECTED_SIGNAL_EFFECTIVE_60_1_60_1`

**補正signal（10,000台・確定結果）：**

- `signal=[59,0,59,0]`
- total travel time：28,535,318.0秒
- average travel time：2,853.5318秒
- average delay：2,688.6358秒
- total distance traveled：49,528,800.0m
- last completed trip time：5,900

**修正後BATCH N=10：**

- total travel time：27,782,978.0秒
- average travel time：2,778.2978秒
- average delay：表示値約2,613.4秒（完全精度未保存）
- total distance traveled：39,962,400.0m
- last completed trip time：4,971

**補正signal / BATCH N=10：**

- total travel time：約1.027079
- average travel time：約1.027079
- total distance traveled：約1.239385
- last completed trip time：約1.186884

**BATCH N=10の平均旅行時間は、補正signalより75.2340秒、約2.64%短い。**

固定需要・1 seed・自由経路の探索的結果であり、一般的優位とは書かない。

#### 1H.25.13 旧signal historical noteと順位反転

**旧signal `[60,1,60,1]` 保存値（historical exploratory result）：**

- total travel time：26,989,929.0秒
- 正確なaverage travel time：26,989,929.0 / 10,000 = **2,698.9929秒**
- average delay表示値：約2,534.1秒
- total distance traveled：50,367,200.0m
- last completed trip time：5,703

**旧BATCH N=10対旧signal（精密比較、historical）：**

- 差：+79.3049秒、BATCH / 旧signal ≈ 1.029383、BATCHが約2.9383%長い

**補正後BATCH N=10対補正signal：**

- 差：−75.2340秒、BATCH / 補正signal ≈ 0.973635、BATCHが約2.6365%短い

旧signal比較ではBATCHが長かったが、補正signal比較ではBATCHが短くなり **順位が反転した**（約−5.5748 percentage points）。

旧signalから補正signalへの変化は、all-red短縮だけの因果効果とは書かない。green実効長・all-red実効長・設定cycle length・offset具体値・network混雑・route choiceも連動して変化した。

旧P2〜P4は旧signal builder（all-red設定値1、実効2 timesteps）によるhistorical exploratory results。意図した実効all-red 1 timestep条件ではない。現行の正式signal timing感度分析には使用しない。補正signal settingによるP2〜P4は未実行であり、追加実行の要否と時期は別途判断する。

#### 1H.25.14 FCFS参考比較（保存値・再実行なし）

FCFS clearance=1保存値：total travel time 33,293,441.0秒、average travel time 3,329.3441秒、average delay 3,164.4481秒、total distance traveled 39,892,000.0m、last completed trip time 6,492

- 補正signal / FCFS average travel time：2,853.5318 / 3,329.3441 ≈ **0.8571**
- BATCH N=10 / FCFS average travel time：2,778.2978 / 3,329.3441 ≈ **0.8345**

FCFS clearance=1と補正signalは、方向変更1回あたりの実効通過禁止timestep数（T/T+1/T+2）の意味では対応するが、制御方式全体は異なる。

#### 1H.25.15 Level 2との関係

- zero-service追加形成の反復制御は `t_trigger` Level 1固有ではない
- Level 2 estimatorも既存のform・register・serve経路へ接続可能（**Level 2は未実装。設計対象**）
- Level 2 unresolved時にはLevel 1へfallbackする（未実装）
- 必要に応じてLevel 0へfallbackする（未実装）
- trigger snapshot・`blocked_inlinks`・clearance停止・arrival wait停止の意味はLevel 2でも維持する
- Level 2の実装により、今回確定したservice queue・assignment・visit IDの意味を変更しない
- trip-end Vehicleは研究対象外とする
- stale service unit回復は必要性が低ければ保留する
- assignmentの全訪問履歴対応は後回しとする

これらは現在実装と確認済み範囲の技術記録として記述し、一般的な理論証明として書かない。

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

### 当初の未実装項目とPhase 4-6M完了時点の状況

**後の実装で変更：** 項目1〜11は Phase 4-6C〜4-6K で実装され、項目12（`Node.transfer()` BATCH分岐）は **Phase 4-6M（§1F）で実装済み**。BATCH形成と実通過の統括は **Phase 4-6L（§1E）で実装済み**。

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
12. `order_control_type="batch"` で `Node.transfer` から `transfer_batch()` を呼ぶBATCH分岐。（**4-6Mで実装済み。§1F**）
13. Level 2仮想サービス計算とLevel 2→Level 1 fallback。（**未実装**）
14. 1 timestep内のBATCH形成と実通過の統合呼出し、正常終了時の `incoming_vehicles` 整理。（**4-6Lで実装済み。§1E**）

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

Phase 4-6Lで追加されたBATCH統括テストは **§1E.12** を参照（`tests_order_control_batch_transfer.py`、17テスト）。

Phase 4-6Mで追加された `Node.transfer()` 接続統合テストは **§1F.14** を参照（`tests_order_control_batch_node_transfer_integration.py`、13テスト）。

### Phase 4-6J完了時点の未実施テストと後続Phaseでの対応

| 課題 | 状況 |
|------|------|
| service queueに基づくVehicle実通過 | **実装・テスト済み（§1D）** |
| service unit内の未到着Vehicleが到着まで待つこと | **テスト済み** |
| 同一inlinkの連続service unitを同一timestep内に続けて処理すること | **テスト済み** |
| 同一inlinkの連続service unitをまたいだ通過台数がNを超えてもよいこと | **テスト済み** |
| 異なるinlinkのservice unitへ切り替わる際のclearance | **テスト済み** |
| 容量不足時の停止 | **テスト済み** |
| 通過済みVehicleのservice unitからの削除 | **実装済み** |
| 完了service unitのqueueからの削除 | **実装・テスト済み** |
| residual batch | **residual部分のFIFO保持を実装・テスト済み（queue最後尾移動なし）** |
| N=1 BATCHとFCFSの完全同等性 | **4-6Mでシミュレーション全体の完全一致を確認（§1F.13）** |
| `Node.transfer()` 接続後の回帰確認 | **4-6Mで実施済み（§1F.14）** |
| `clearance_timesteps=1` でFCFSより方向切替回数が減る可能性 | **接続後の検証課題（複数ネットワーク条件での動作確認）** |

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
- BATCH形成と実通過の統合呼出し（`transfer_batch()`）→ **phase 4-6Lで実装済み**（§1E）
- 正常終了時の `incoming_vehicles` 整理 → **phase 4-6Lで実装済み**（§1E.8）
- `Node.transfer()` へのBATCH分岐 → **phase 4-6Mで実装済み**（§1F）
- N=1 BATCHとFCFSのシミュレーション全体での完全同一性 → **phase 4-6Mで確認済み**（§1F.13）

### 未解決・将来課題

- `tau_timesteps` を常に1でよいか（研究比較で可変にするか）。
- Level 2仮想サービス計算をいつ導入するか。
- Level 2 unresolved時のLevel 1 fallback接続をいつ実装するか。
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
- `Node.transfer`（BATCH分岐は **4-6Mで接続済み。§1F**）
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
- `serve_order_control_batch_service_queue`（phase 4-6K、commit `12e8eae`）
- `transfer_batch`（phase 4-6L、commit `e9f3ce9`）
- `Node.transfer` のBATCH分岐（**phase 4-6M。§1F**）
- `Link.__init__`
- `Link.update` / `in_out_flow_constraint` 周辺

### BATCH関連テスト（Phase 4-6A〜4-6N）

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
- `tests_order_control_batch_service_queue_transfer.py`（phase 4-6K、33テスト）
- `tests_order_control_batch_transfer.py`（phase 4-6L、17テスト）
- `tests_order_control_batch_node_transfer_integration.py`（phase 4-6M、13テスト）
- `tests_order_control_batch_vs_fcfs_vs_uxsim_standard_medium_network.py`（phase 4-6N、commit `f339b88`）
- `tests_order_control_batch_vs_fcfs_vs_uxsim_standard_grid_network.py`（phase 4-6N、commit `f339b88`）
- `tests_order_control_batch_vs_fcfs_vs_signalized_uxsim_standard_grid_network.py`（phase 4-6N、commit `f339b88`）

### Phase 4-6N診断スクリプト（`0e35799` commit済み。`diagnostics/order_control/`）

保存先：`diagnostics/order_control/`。ファイル名は `tests_` で始まらない。通常の自動テスト探索対象に含めない。既知のprefix violationは意図的再現であり、非zero終了は診断結果（通常テスト失敗ではない）。

- `diagnostics/order_control/README.md`
- `diagnostics/order_control/batch_assignment_318_lifecycle_diagnostic.py`
- `diagnostics/order_control/batch_clearance_zero_vs_fcfs_vs_signalized_uxsim_grid_high_demand_5000_diagnostic.py`
- `diagnostics/order_control/batch_clearance_one_vs_fcfs_vs_signalized_uxsim_all_red_grid_high_demand_diagnostic.py`
- `diagnostics/order_control/node_revisit_high_demand_5000_diagnostic.py`

診断スクリプトの目的、既知の非zero終了、実行方法については `diagnostics/order_control/README.md` を参照。

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
- **Phase 4-6A〜4-6M：** 実装・テスト・commit済み（4-6Mは `b03538c`）。
- **Phase 4-6N（commit済み）：** route_next_link参照順修正（`05fa2d1`）、clearance=0比較テスト3本（`f339b88`）、正式記録（`c06936c`）、診断スクリプト分離（`0e35799`）。
- **Phase 4-6N Step 5：** Node訪問単位の共通状態設計を **§1H** に記録済み。基盤（4-6O）・到着記録（4-6P）・FCFS参照先変更（4-6Q）・BATCH参照先変更（4-6R）・BATCH assignment訪問対応（4-6S）・小規模BATCH再訪end-to-end統合（4-6T）は実装済み。high-demand再実行・検証（4-6U）は5,000台・clearance=0、5,000台・clearance=1、10,000台・clearance=1の3ケースで完了（§1H.24）。zero-service追加形成修正（4-6V）は完了（§1H.25、`2b10b08`）。診断スクリプト（`fe9e53e`）は§1H.25
- **現時点の主要課題：** Level 2仮想サービス推定・Level 2 unresolved時のLevel 1 fallback接続・Time-value Transaction（設計メモ **§1H.25**）
- **優先参照：** ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md の **§1H** を優先参照。診断・根本原因は **§1G**、`Node.transfer()` 接続は **§1F**。Phase 4-6Q実装記録は **§1H.20**、Phase 4-6R実装記録は **§1H.21**、Phase 4-6S実装記録は **§1H.22**、Phase 4-6T実装記録は **§1H.23**、Phase 4-6U実行記録は **§1H.24**、Phase 4-6V zero-service追加形成・等価性・batch size予備比較は **§1H.25**
- **次工程候補（§1H.17・§1H.25）：** Level 2仮想サービス推定の設計調査。Level 2 unresolved時のLevel 1 fallback接続。必要に応じてLevel 0 fallback。trip-end Vehicleは研究対象外。stale service unit回復は必要性が低ければ保留。assignment全訪問履歴は後回し。Time-value Transaction本体
- 目的地Vehicleは端点間OD前提で保留。比較対象Node共通管理・自動検証は将来課題。
- 一時退避PDF `phase4-6A_batch_earliest_arrival_timestep_memo.pdf` はリポジトリ外。正式Markdownを優先参照。
