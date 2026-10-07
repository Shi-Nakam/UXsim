# TVT-MP 実験設計メモ

作成日:

- 2026-10-07

## 文書の位置づけ

- 本文書は TVT-MP の実験条件、研究ネットワーク、比較条件、VOT、容量、初期試行、正式実験、結果保存を扱う。
- TVT-MP 内部のアルゴリズム、record、registry、API、評価契約、テスト契約の正本ではない。
- 内部実装の正本は `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md` および必要に応じて旧巻（例: 第2巻）を参照する。
- 実験の結果、バグ、新しい指標、仕様変更、API 変更、record 変更、CSV 列変更が必要になった場合は、実装設計メモへ戻って設計・記録する。
- 実験条件と実装仕様は必要に応じて往復する。
- 往復時には、実験設計メモ、実装設計メモ、`ORDER_EXCHANGE_PROGRESS_3.md` の相互参照を残す。
- 実験で観察された現象だけを理由に、実装仕様を文書化せず変更しない。
- 本文では **確定事項**、**基本方針**、**初期試行条件**、**正式実験前の未確定事項** を区別する。

---

# 1. 研究・実験の位置づけ

- TVT-MP は将来技術を前提とする時間価値取引型交差点管理である。
- 基本実験では true VOT を正しく申告する（`vot_true` と `vot_declared` を一致させる participating 車両）。
- strategy-proofness は未証明である。
- buyer、seller、nonparticipating を扱う。
- 主な研究対象は次である。
  - 交通管理メカニズム
  - 市場・取引・メカニズムデザインの交通制御応用
  - candidate 予測と actual 結果の差
- 初期の小規模 run は論文結果の生成ではない。目的は実行性、バグ、処理時間、候補形成、取引成立、研究出力の確認である。
- 正式実験条件は、小規模 run の結果だけで自動的に確定しない。

---

# 2. 時間設定

評価期間、baseline 仮想計算、意思決定窓は別概念として扱う。

## 意思決定窓

意思決定 timestep を **T** とする。

対象となる未来到着 Visit の正式条件:

```text
T < baseline_arrival_timestep <= T + 6
```

同じ内容を差分で表す場合:

```text
0 < baseline_arrival_timestep - T <= 6
```

重要:

- 単に「6 timestep 以内」とだけ書かない（T 到着 Visit を誤って含めないため）。
- **T 到着 Visit**（`baseline_arrival_timestep <= T`）は含まない。
- 未来到着は **0 より大きく 6 以下** の差分である。
- 意思決定窓幅 **6** はコード定数（`order_control_tvt_mp_driver.py` の `_DECISION_WINDOW_STEPS` 等）であり、実験 script の自由入力ではない。

## baseline horizon

- 初期小規模 run の設定候補は **30 timestep**。
- 当初想定範囲の下限として 30 を採用する。
- 意思決定窓 6 とは **別の概念** である。
- baseline horizon は、意思決定窓全体を観測できるよう **6 以上** が必要（実装は `order_control_tvt_baseline_horizon_steps >= 6` を要求）。
- World 属性は **`order_control_tvt_baseline_horizon_steps`**（コード既定 6；実験では 30 を設定する基本案）。

## candidate local horizon

- candidate local horizon は、対応する全 World baseline 結果の **`configured_horizon_steps`** を上限として使用する。
- **独立した自由入力 local horizon は設けない。**
- baseline horizon を 30 に設定すれば、candidate local horizon 上限も結果的に 30 となる。
- 必要情報が揃えば上限前に早期終了し得る。

## 評価期間と内部期間

初期小規模 run の基本案:

| 項目 | 値 |
| --- | --- |
| 評価期間 | 300 timestep |
| 評価対象 timestep | T = 0 から T = 299 |
| evaluation end timestep | 299（`order_control_tvt_evaluation_end_timestep`） |
| baseline horizon | 30 |
| 内部 TSIZE | 330（`tmax=330` 秒、`DELTAT=1` 秒） |
| evaluation end 後の内部余白 | T = 300 から T = 329 は baseline 仮想計算用の内部余白であり、実 World の交通計算は進めない |
| `exec_simulation` 終了後に期待する `World.T` | **300**（= evaluation end + 1） |

研究出力 API（`build_tvt_mp_research_output`）は、evaluation end および ex-post 処理完了後、`World.T == evaluation_end_timestep + 1` を前提とする（実装設計第4巻）。

---

# 3. 自由流速度、DELTAT、Link 長

## 時間刻み

- `reaction_time = 1`（秒）
- `deltan = 1`
- **`DELTAT = 1` 秒**（`World.DELTAT = REACTION_TIME * DELTAN`）

## 自由流速度

- 研究上の自由流速度は **60000 / 3600 m/s**（60 km/h、約 **16.67 m/s**）。
- `free_flow_speed` は World 共通属性ではなく、**各 Link を `addLink` するときに明示**する。
- UXsim 既定値 **20 m/s** を省略使用しない。
- Link 作成後に表面的な属性だけを書き換えず、**`addLink` 時に設定**する。
- baseline World、candidate local World、実 World で **同じ Link 条件**を使う。

## 全 Link 長 100 m 以上（研究設計上の下限）

研究ネットワークの **全 Link** について、長さ **100 m 以上**を必須条件とする。

根拠:

```text
(60000 / 3600) × 6 = 100 m
```

自由流速度 60 km/h では、固定された意思決定窓の上限 **6 timestep**（秒）の間に **100 m** 走行する。意思決定窓とネットワーク空間スケールを整合させるための研究上の下限である。

重要:

- 100 m は一般的な UXsim の技術的制約ではない。
- **TVT-MP 研究におけるネットワーク設計上の下限**である。
- 特段の理由がなければ 100 m ちょうどではなく、**200 m** など余裕を持つ。
- 初期小規模 run では流入 Link・流出 Link とも **200 m** を基本案とする。
- 200 m を 60 km/h で自由流走行する時間は約 **12 秒**。

---

# 4. 車線と交通流基本図

- 研究の基本条件は **単車線**（`number_of_lanes = 1`）。
- 自由流速度は **16.67 m/s**（60000/3600）へ変更する（上節）。
- **`jam_density`** は当面 UXsim 既定値 **0.2 台/m** を維持する。
- **`reaction_time`** は当面 UXsim 既定値 **1 秒** を維持する。
- 基本図を構成する他のパラメータを、容量を 1500 台/時へ合わせる目的だけで変更しない。

自由流速度 16.67 m/s、`jam_density` 0.2 台/m、`reaction_time` 1 秒の場合、Link 内部の理論容量はおおむね **0.769 台/秒**、約 **2769 台/時** となる。

これは **Link 内部の理論基本図容量**であり、現実の交差点流入部または Link 境界の処理能力と同じ意味ではない。

---

# 5. Link 境界容量と Node 容量

## UXsim 既定値の意味

- `capacity_in` と `capacity_out` を省略すると、**Link 内部の基本図容量の 2 倍**が使われる。
- これは Link 境界を追加ボトルネックにしないための **技術的既定値**である。
- Node の `flow_capacity=None` は容量 0 ではなく、**Node 独自の追加流量制約なし**（実質的に無限容量）を意味する。

## 1500 台/時の換算

```text
1500 / 3600 ≈ 0.4167 台/秒
```

1 台当たりでは約 **2.4 秒**に相当する。

## 正式実験の有力案（未確定）

方式間で共通の道路条件として、次を **有力案**とする。

- 各流入 Link の `capacity_out = 1500 / 3600` 台/秒
- 各流出 Link の `capacity_in = 1500 / 3600` 台/秒
- Node の `flow_capacity = None`

意味:

- Link 内部の基本図は維持する。
- Link 境界へ現実的な追加ボトルネックを設定する。
- `capacity_in` または `capacity_out` を基本図容量より小さく設定しても、基本図の関係を壊すものではない。
- Node へ不要な追加ボトルネックを重ねない。

**1500 台/時を正式な基本実験条件として採用するかは、正式実験設計時に最終確認する。**

## 初期小規模 run の基本案（確定ではないが初回 script 用）

コード実行性の確認を優先するため、**`capacity_in`、`capacity_out`、Node `flow_capacity` を明示変更せず UXsim 既定値を使用**する基本案を記録する。

---

# 6. Signal、FCFS、BATCH、TVT-MP の比較条件

## 比較の基本原則

- 道路、Link、車線、自由流速度、需要、OD、VOT、seed 等の物理条件を可能な限り共通化する。
- 方式間で変える中心は **通行権の決め方**である。

## Signal

- UXsim 標準の信号制御を使用する。
- order-control 順位制御を使用しない。
- 青信号間に **全赤時間**を明示する。
- サイクル長、青時間、全赤時間は **未確定**。
- 単車線の飽和流率を 1500 台/時とし、南北・東西へ青時間を 50% ずつ配分する理想化条件では、各方向の実効容量は約 **750 台/時**、合計約 **1500 台/時**となる。
- 実際には全赤時間、切替損失等により各方向 750 台/時を下回り得る。
- 信号方式だけ Link 容量を 750 台/時へ下げたうえで青時間を半分にしない。**容量低下を二重計上しない。**

## FCFS

- 信号なし。
- 到着順による通行権。
- 共通の order-control **clearance** を使用する。

## BATCH

- 信号なし。
- バッチ形成とバッチ順位による通行権。
- 共通の order-control clearance を使用する。

## TVT-MP

- 信号なし。
- 時間価値取引による順位変更（`order_control_type="time_value"`、`transaction_case=None`；Case III は使用しない）。
- 共通の order-control clearance を使用する。

## clearance の初期基本案

- **1 timestep**（`order_control_clearance_timesteps` の既定 1）。
- 方式間で共通。
- 正式実験時に安全前提として再確認する。

---

# 7. 交差点内部最大 6 台の位置づけ

指導教授との議論では、ある瞬間に交差点のスクウェア内へ **最大 6 台程度**が存在し得るとの想定がある。

この **6 台**は次を意味しない。

- 6 台/秒の流量容量
- `Node.flow_capacity = 6`
- 候補 Visit 数上限 6

この 6 台は、**瞬間的な交差点内部の空間収容台数**である。

現行 UXsim の Node は基本的に空間を持たず、Vehicle を交差点内部へ滞在させるモデルではない。したがって、現行の単一 Node 表現では最大 6 台を **直接モデル化しない**。

将来、交差点内部を短い Link や movement Link で表現する場合には検討できるが、これは現行 TVT-MP 研究の初期実験に **直ちに追加しない**構造拡張課題である。

一方、**候補 Visit 数上限 10**（`order_control_tvt_max_candidate_visit_count`）は、交差点付近に 6 台程度がまとまり得る想定を余裕をもって包含する値として維持する。

---

# 8. VOT 分布

## 基本条件

- 車両単位の VOT を **対数正規分布**とする。
- 元尺度の算術平均は **1 円/秒**。
- 元尺度の算術標準偏差は **3 円/秒**。
- 将来の物価水準上昇とライドシェア等による 1 車両当たり乗員数増加を考慮した **将来シナリオ仮定**である。
- 現在または過去の日本データの厳密な推定値とは位置づけない。

## 対数空間パラメータ

- `mu = -ln(10) / 2`（おおむね **-1.1513**）
- `sigma = sqrt(ln(10))`（おおむね **1.5174**）

## 基本実験での申告

- **participating**: `vot_true = vot_declared`。
- 戦略的虚偽申告は扱わない。
- **nonparticipating**: 外部効果算定用の `vot_true` を与える。`vot_declared` は取引申告値として使用しない（`None`）。
- VOT 0 はコード上有効だが、連続対数正規分布では通常生成されない。
- VOT を恣意的に上下で切り捨てない基本案とする。
- **生成した個別 VOT は保存**する（trial / 正式実験の成果物候補: `vehicle_vot.csv` 等）。

## seed

- **交通 seed** と **VOT 生成 seed** を分離する（初期小規模 run: 交通 0、VOT 1）。

## 将来の感度分析（未確定）

- 元尺度平均 0.5 円/秒、標準偏差 1.5 円/秒に相当する分析。
- 基本条件と同じ基礎乱数を使用し、各 Vehicle の VOT を一律に **0.5 倍**する。
- 相対順位と変動係数を保ち、円ベースの絶対水準の影響を分離する。

---

# 9. 初期小規模 run

## 目的

- コード実行性
- 仮想計算を含む実行時間
- バグ発見
- 候補形成の有無
- 取引成立の有無
- evaluation end 処理
- 研究出力 5 表
- 同一 seed での再現性
- パラメータ調整

## ネットワーク・制御

- **2 流入、1 流出**の単車線合流
- TVT-MP 対象 Node は **1 か所**（例: `merge`）
- 流入 Link 2 本、流出 Link 1 本
- 各 Link 長 **200 m**
- 自由流速度 **60000/3600 m/s**
- `infer_order_control_eligible_nodes()` の後、`set_order_control_for_nodes(["merge"], order_control_type="time_value", transaction_case=None)` の方向
- `exec_simulation()` が評価 timestep ごとに TVT-MP driver を自動実行する（実装設計第4巻）
- evaluation end 後に `build_tvt_mp_research_output()` と `write_tvt_mp_research_output_csv()` を **明示呼出し**（Analyzer へ自動接続しない）

## 需要

| 項目 | 値 |
| --- | --- |
| 合計車両数 | 10 |
| participating | 8 |
| nonparticipating | 2 |
| 交通 seed | 0 |
| VOT 生成 seed | 1 |
| buyer / seller | 事前指定しない（順位変換の結果として決まる） |

### 投入 timestep（`departure_time_is_time_step=1`）

| vehicle_name | orig | departure_timestep | participating |
| --- | --- | ---: | --- |
| （orig_a 先頭） | orig_a | 5 | False（nonparticipating） |
| （orig_a） | orig_a | 7 | True |
| （orig_a） | orig_a | 9 | True |
| （orig_a） | orig_a | 11 | True |
| （orig_a） | orig_a | 13 | True |
| （orig_b） | orig_b | 6 | True |
| （orig_b） | orig_b | 8 | True |
| （orig_b） | orig_b | 10 | False（nonparticipating） |
| （orig_b） | orig_b | 12 | True |
| （orig_b） | orig_b | 14 | True |

- orig_a へ 5 台（5, 7, 9, 11, 13）、orig_b へ 5 台（6, 8, 10, 12, 14）。
- 全車同時投入は避ける。初回は **取引成立を絶対条件にしない**。

## 時間・TVT パラメータ

- baseline horizon **30**
- candidate local horizon 上限 **30**（独立設定なし）
- 意思決定窓: **0 < baseline_arrival_timestep - T <= 6**
- candidate Visit 数上限 **10**
- 評価期間 **300** timestep（T = 0…299）
- internal **TSIZE 330**
- clearance **1** timestep
- Link 境界容量・Node 容量: **既定値**（明示変更しない基本案）

## 観測・診断の方針

- `transaction_count == 0` の場合、候補未形成、経済的不成立、未解決等の区別診断は **後から検討**する。
- **最初から新 counter を追加しない**（必要になれば実装設計メモへ戻る）。

---

# 10. 実験 script と結果の保存方針

UXsim 本来の公式デモ（`demos_and_examples` 等）と、東京大学側の独自研究用 script を **混同しない**。

研究用 script は demos へ置かず、研究専用の配置を使用する（**今回の文書作業では directory は未作成**）。

## 基本構成案

| パス | 用途 |
| --- | --- |
| `research_scripts/` | 研究 script（Git 管理対象） |
| `research_outputs/trial/` | 初期試行・調整（原則 Git 管理外） |
| `research_outputs/experiments/` | 論文用正式結果（バックアップ対象） |

### research_scripts

- 研究 script を保存する。
- Git 管理対象とする。
- 再現に必要な設定や分析 script も将来ここへ整理する。

### research_outputs/trial

- 初期動作確認、バグ発見、パラメータ調整、再現調査。
- 不要になれば削除可能。
- 原則として Git 管理しない。

初期試行でも再現に必要な次を一時保存できる構成とする（ファイル名は script 実装時に具体化）:

- 5 つの研究用 CSV
- 実際の Vehicle 別 VOT
- 実行条件、seed、実行時間、エラーまたは警告、実行要約

### research_outputs/experiments

- 論文分析に使う正式実験結果。
- 実験ごとに一意の directory。
- 原則 **上書きしない**。
- 元 CSV を保持し、集計後も削除しない。
- バックアップ対象とする。
- 通常の Git へ大量 CSV を直接入れない。

## 正式実験で保存する候補

- `manifest.json`
- `run_summary.txt`
- `vehicle_vot.csv`
- `tvt_mp_transactions.csv`
- `tvt_mp_visits.csv`
- `tvt_mp_vehicles.csv`
- `tvt_mp_nodes.csv`
- `tvt_mp_scenario.csv`

### manifest 候補項目

- scenario name、実験 ID、実行日時
- Git branch、Git commit hash
- 実行 script
- 交通 seed、VOT seed、VOT 分布
- 時間設定、horizon、意思決定窓、candidate 上限、clearance
- ネットワーク条件、Link 条件、容量条件
- OD・需要、参加率、実行時間、既知の警告

**今回の文書作業では、`research_scripts`、`research_outputs`、`.gitignore` を実際には作成または変更しない。**

---

# 11. 実験と実装設計の往復運用

## 実験設計メモ（本文書）へ記録するもの

- 実験条件、ネットワーク、需要、VOT、seed
- 比較条件、感度分析
- 実験結果、実行時間、観察事項
- 正式実験結果の保存方針

## 実装設計メモへ戻して記録するもの

- バグ原因、本番コード修正
- 新しい仕様、record / registry 変更
- public API 変更、CSV 列変更
- 新しい指標の正式定義、新 counter
- evaluation end 処理変更、テスト契約変更

## ORDER_EXCHANGE_PROGRESS_3.md へ記録するもの

- 現在地、どのメモが正本か
- 実験から実装へ戻った理由
- 完了事項、未確定事項、次の再開地点
- Git 状態（記録のみ；操作は利用者 Terminal）

## 往復時の手順

実験から実装へ戻る場合:

1. 実験メモに **観察事実**を記録する。
2. 実装設計メモに **原因・仕様・修正方針**を記録する。
3. 双方から相互参照する（日付・節見出しを明記）。

---

# 12. 確定事項、基本案、未確定事項

## 確定事項

- 意思決定窓条件は **0 より大きく 6 以下**（`T < baseline_arrival_timestep <= T + 6`；T 到着 Visit は含めない）。
- **candidate local horizon の独立設定なし**（baseline の `configured_horizon_steps` を上限）。
- 基本 VOT 分布（対数正規、元尺度平均 1 円/秒、標準偏差 3 円/秒；対数 `mu`、`sigma` は第8節）。
- 基本実験で participating の **true VOT と declared VOT を一致**。
- 自由流速度 **60 km/h**（60000/3600 m/s）；**`addLink` 時に明示**。
- **DELTAT 1 秒**（`reaction_time=1`、`deltan=1`）。
- 研究ネットワークの **全 Link 長 100 m 以上**（TVT-MP 研究設計上の下限；意思決定窓 6 秒との整合）。
- **単車線**（`number_of_lanes=1`）。
- 実験 script を **公式 demo から分離**する方針。
- **trial** と **正式実験結果**を分離する方針。
- **実験と実装設計を往復可能**とする運用。

## 初期小規模 run の基本案

初回 script 作成時に最終確認できる基本案（上記 §9 の要約）:

- 2 流入 1 流出、各 Link **200 m**、自由流 **60 km/h**
- **10 台**（参加 8、非参加 2）、投入 **5–14**、seed 交通 **0** / VOT **1**
- baseline horizon **30**、candidate 上限 **10**、評価 **300**、TSIZE **330**、clearance **1**
- Link 境界・Node 容量は **UXsim 既定**（明示変更しない）

## 正式実験前の未確定事項

- `capacity_in` / `capacity_out` へ **1500 台/時**を正式採用するか
- Signal のサイクル長、青時間、全赤時間
- 正式研究ネットワーク、OD 需要、右左折率、Node 数、TVT-MP 対象 Node 数
- 需要の時間変動、参加率、seed 数
- 正式感度分析条件（0.5 倍 VOT 等）
- 交差点内部最大 6 台を直接モデル化しない方針を正式実験でも維持するか
- `manifest.json` の正式 schema
- `research_outputs` のバックアップ先
- `.gitignore` の変更
- 正式実験 ID の命名規則
- vehicle 名・Node/Link 名の正式命名（小規模 run の表は基本案）

---

# 13. 最新再開地点

- TVT-MP 集計・研究出力の実装、検証、文書化、push は **完了済み**（実装設計第4巻・進捗第3巻の工程8記録）。
- **現在は初期小規模 run の実験設計段階**である。
- **本メモ（`TVT_MP_EXPERIMENT_DESIGN_NOTES.md`）を新設**した。
- 次の直接作業は、本メモの **独立確認**（利用者と Copilot で Terminal 上の内容確認）。document コミットは確認後。
- 文書確認後に **document コミットと push** を行う（利用者 Terminal）。
- その後、小規模実行 script の実装前条件を最終確認する。
- **script 作成、実行、出力 directory 作成、`.gitignore` 変更にはまだ進んでいない。**
- **`diagnostics/order_control.zip` には触れない。**
- **Git 操作は利用者が Terminal で行う**（Cursor では行わない）。

---

## 相互参照

| 文書 | 役割 |
| --- | --- |
| `TVT_MP_EXPERIMENT_DESIGN_NOTES.md` | 実験条件・ネットワーク・保存方針の正本（本文書） |
| `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_4.md` | TVT-MP 内部実装・API・評価契約の正本 |
| `ORDER_EXCHANGE_PROGRESS_3.md` | 工程・再開地点・正本の案内 |
