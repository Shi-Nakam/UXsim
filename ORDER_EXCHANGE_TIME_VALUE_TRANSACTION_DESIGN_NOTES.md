# ORDER EXCHANGE TIME-VALUE TRANSACTION DESIGN NOTES

**本メモの位置づけ（冒頭宣言）**

- 本メモは Time-value Transaction（以下 **TVT**）設計の**正本**である。
- TVT本体は**まだ実装されていない**。
- 本文では**確定事項**、**保留事項**、**撤回済み事項**を区別する。
- BATCH Level 2 の実装済み内容と、TVT の未実装設計を混同しない。
- 今後新しい合意が得られた場合は、本メモを更新する。
- 既存の時系列議論よりも、後から行われた訂正と確定事項を優先する。

関連資料（参照のみ。TVTの確定内容は本メモを優先）：

- `ORDER_EXCHANGE_PROGRESS.md`
- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md`
- `ORDER_EXCHANGE_RESEARCH_CONTEXT.md`
- `uxsim/uxsim.py`
- `uxsim/order_control_batch_level_2_reference.py`

---

## 1. メモの目的と現在の状態

### 1.1 目的

本メモは、Order Exchange 研究における TVT の制度設計・技術設計を正式に記録する。BATCH Phase 4-6Y 完了後、次の本体対象として TVT の設計整理を開始した。

### 1.2 現在の状態

| 区分 | 状態 |
|------|------|
| TVT制御ロジック | **未実装** |
| FCFS | 実装済み |
| BATCH（Level 2含む） | 実装済み・主要診断済み |
| 全World baseline仮想計算 | **未実装**（設計のみ） |
| TVT局所仮想計算 | **未実装**（設計のみ） |
| 経済評価（G, R） | **未実装**（設計のみ） |

### 1.3 研究シナリオ前提（BATCHと共通）

- 比較対象内部交差点 Node を目的地としない端点間 OD を使用する。
- trip-end Vehicle は現在の研究対象外。
- 全比較方式（signalized UXsim、FCFS、BATCH、TVT）で同一ネットワーク・同一需要を用いる。

---

## 2. 用語と順位概念

### 2.1 三種類の順位（必ず区別する）

#### （1）baseline予想到着順位

取引なしの**全World baseline仮想計算**によって予測された、対象 Node への到着順位。

- TVTがない場合の FCFS 予想到着順位の基準。
- 「FCFS順位」と言うとき、本メモでは原則として **baseline予想到着順位** を指す。

#### （2）割当権利行使順位

`Node.transfer()` において、Vehicle が通過を試す機会を与えられる順番。

- **TVTが直接変更するのはこの割当権利行使順位**。
- TVTがない場合は、baseline予想到着順位と同じ。

#### （3）実通過順位

容量、clearance、outlink の受入可能性、実際の到着誤差などを反映して実現した通過順位。

- 割当権利行使順位と同じになるとは限らない。
- TVT は Vehicle の実際の到着時刻や実通過順位を**直接操作しない**。

### 2.2 その他の重要用語

| 用語 | 意味 |
|------|------|
| 意思決定窓 | 制度上、TVT検討の対象となる未到着未確定 Vehicle の時間範囲（基本6 timestep） |
| 全World baseline horizon | 全World baseline仮想計算の進行長（初期検討中心は50 timestep。正式値未確定） |
| TVT候補Vehicle | 具体的な候補取引を構成する母集団の Vehicle |
| 権利保有車両 | 意思決定窓内の未確定参加 Vehicle のうち baseline予想到着順位が最上位の Vehicle |
| 確定順位ブロック | 今回の TVT より前に割当権利行使順位が確定している Vehicle の連続順位列 |
| 参加Vehicle | TVTに参加する Vehicle |
| 非参加Vehicle | TVTに参加しない Vehicle（順位固定対象になり得る） |

### 2.3 権利保有車両のコード上候補名

説明上は「**権利保有車両**」を使用する。コード上の候補名：

- `right_of_entry_vehicle`
- `right_of_entry_inlink`
- `right_of_entry_baseline_rank`
- `right_of_entry_expected_arrival_timestep`
- `right_of_entry_expected_passage_timestep`

`right_holder` は何の権利か分かりにくいため、**原則として使用しない**。

### 2.4 「候補」の区別

- **TVT候補Vehicle**：候補取引母集団の Vehicle
- **買い手候補**：prefix 選択により買い手集合を構成する Vehicle
- **具体的取引候補**：買い手集合・売り手・取引後順位を含む一つの候補取引

---

## 3. 全World baseline仮想計算

### 3.1 概要（設計・未実装）

各実 timestep の開始時点における実 World を基礎に、**取引なし**の共通 baseline 仮想計算を **World 全体**について実施する。

- ネットワーク内の各 Node は、現在設定されている制御方式を維持する。
- 制御方式の例：signalized UXsim、FCFS、BATCH、TVT。
- **同一実 timestep では、全対象 Node が同じ全World baseline 結果を参照する。**
- 対象 Node ごとに別々の全World baseline を作らない。
- signalized UXsim、FCFS、BATCH 等の制御状態を反映する。

**「取引なし」の意味（全World baseline 内での TVT Node の扱い）**

全World baseline 仮想計算は、仮想計算開始後に**新しい TVT を検討・成立させない**「取引なし」の反実仮想である。

- TVT が設定された Node についても、全World baseline 仮想計算の**開始後**には新しい TVT を実行しない。
- 仮想計算開始時点までにすでに確定している割当権利行使順位は**維持**する。
- 未確定 Vehicle については、**新しい TVT を行わない baseline 条件**で処理する。
- 「各 Node が現在設定されている制御方式を維持する」という記載は、**TVT Node で新しい TVT を発生させることを意味しない**。

### 3.2 取得する Vehicle 別情報（設計）

- Vehicle 識別情報
- current visit または visit ID
- 対象 Node
- inlink
- `route_next_link`
- TVT 参加・非参加
- baseline予想到着 timestep
- baseline予想到着順位
- baseline予想通過可能 timestep
- 必要に応じた baseline予想通過順位
- 既確定順位の有無
- 割当済み権利行使順位
- horizon 内に到着情報を取得できたか
- horizon 内に通過情報を取得できたか

### 3.3 取得する Node 別情報（設計）

- 既存の確定順位ブロック
- 既到着かつ未確定の Vehicle
- 意思決定窓内 Vehicle
- 権利保有車両
- TVT候補 Vehicle
- baseline予想到着順位列
- 権利保有車両の baseline予想通過可能 timestep（TVT候補 Vehicle の時間範囲を決める**直接の基準**）
- 必要に応じた、Vehicle 別 baseline予想通過可能 timestep への参照
- horizon 内で必要情報を取得できたか

### 3.4 virtual horizon

- 全World baseline の仮想 horizon は、**初期想定として50 timestepを中心に検討**している。
- 50 は正式な基本値として**最終確定していない**。
- horizon 30、50、100 などの比較と未解決率の測定が必要。

**重要：6 timestep は全World baseline の全長ではない。6 timestep は意思決定窓の基本値である。**

---

## 4. 意思決定窓とTVT検討の発動

### 4.1 意思決定窓の基本値

**6 timestep**（制度上の基本値。経済最適化のための値ではない）。

### 4.2 制度上の意思決定窓内Vehicle

原則として次をすべて満たす Vehicle：

1. 対象 Node での**割当権利行使順位が未確定**
2. 対象 Node へ**まだ到着していない**
3. 全World baseline による予想到着までの残り時間が **1 から 6 timestep**

概念的には：

```
0 < baseline予想到着timestep - 現在timestep <= 6
```

**既到着 Vehicle は意思決定窓内 Vehicle に含めない**（§5 で別処理）。

### 4.3 6 timestep の根拠（確定）

- 対象 Link 長は原則 100 m 以上。
- 自由流速度は 60 km/h（約 16.67 m/s）。
- `DELTAT = 1` 秒。
- 100 m の自由流走行に約 6 秒を要する。
- TVT では前方 Vehicle が他 Vehicle を先行させる可能性があり、安全に減速して権利を譲るための時間と距離が必要。
- 雨天時の停止余裕も考慮し、**到着直前ではなく約6秒前に意思決定**する考え方。
- したがって 6 timestep は**安全性と現実性**を根拠とする基本値。
- 後の感度分析対象にはなり得るが、採用理由は経済最適化ではない。

### 4.4 TVT検討の発動タイミング（確定）

- 意思決定窓内 Vehicle は複数台になり得る。
- そのうち baseline予想到着順位が最上位の**未確定参加 Vehicle** を権利保有車両とする。
- 非参加 Vehicle は baseline 順位を持つが、権利保有車両にはならない。
- **TVT検討は、意思決定窓への初回進入時に行う。**
- 同じ Vehicle について、次の実 timestep 以降に改めて同じ起点条件で TVT を**再検討しない**。

### 4.5 UXsim処理順に関する注意（実装時確認事項）

制度上の「現在 timestep で既到着」と、UXsim コード上で到着が記録される処理位置が一致するとは限らない。実装時に次を確認する：

| 確認項目 | 関連処理 |
|----------|----------|
| `Node.transfer()` の実行時点 | 通過試行・incoming 処理 |
| `Vehicle.update()` の実行時点 | Vehicle 状態更新 |
| `incoming_vehicles` への登録時点 | Node 到着記録 |
| current visit の到着記録時点 | `order_control_current_visit` |
| 現在 timestep で到着した Vehicle を既到着とみなす処理位置 | 制度定義との対応 |

**制度上の定義**と**コード上の検出条件**は分けて設計・実装する。

---

## 5. 既到着未確定Vehicleの処理

### 5.1 発生条件

全World baseline 仮想計算または実 World 状態の確認により、対象 Node へ**既到着**であるにもかかわらず**割当権利行使順位が未確定**の Vehicle が判明し得る。

### 5.2 基本方針（確定）

既到着 Vehicle については、**参加・非参加を問わず TVT の起点にしない**。

理由：到着前に順位交換を成立させ、安全に減速または譲歩するという TVT の制度趣旨に反するため。

### 5.3 処理手順（確定）

1. 既到着かつ未確定の Vehicle を特定する。
2. 到着情報、固定 tiebreaker、Vehicle ID により一意の順序を作る。
3. 参加・非参加にかかわらず TVT の起点にしない。
4. 既存の確定順位ブロック直後から、連続した割当権利行使順位を付与する。
5. 確定順位ブロックへ追加する。
6. その後、残る未到着 Vehicle について意思決定窓と TVT 候補を処理する。

### 5.4 重大不整合（停止方向）

- すでに対象 Node を**通過した** Vehicle に未確定順位が残っている場合：救済せず、**重大な実装不整合として停止**。
- 同じ current visit への複数順位割当。
- 同一 Node の同一順位を複数 Vehicle へ割当。
- 確定順位ブロック内の順位重複。
- 確定順位ブロック内の欠番。

登録時に保証済みの不変条件は、実行時に重複確認しない方針があり得る。実装時の検査位置と頻度は**必要最小限**とする。

---

## 6. 同着Vehicleと参加状態中立方式

### 6.1 同着順位の決定（確定）

同じ baseline予想到着 timestep となる Vehicle は、次の順序で一意に順位化する：

1. baseline予想到着 timestep
2. 固定 tiebreaker
3. Vehicle ID

**参加・非参加は同着 Vehicle の順位決定条件に使用しない。**

### 6.2 参加状態中立方式（確定）

本方式を当面の確定事項とする。

- 参加状態は**順位決定後**に使用する。
- 非参加 Vehicle は TVT の買い手にも売り手にもならない。
- 参加 Vehicle は条件を満たせば権利保有車両、買い手、売り手になり得る。
- **非参加であることを理由に、同着グループ内で tiebreaker や Vehicle ID より先へ繰り上げない。**

---

## 7. TVT候補Vehicleの時間条件

### 7.1 意思決定窓内Vehicleとの区別（確定）

| 区分 | 定義 |
|------|------|
| **意思決定窓内Vehicle** | TVT の発動と今回の確定範囲に関係。現在から 1〜6 timestep 以内に到着予定の未到着未確定 Vehicle。既到着は含まない。 |
| **TVT候補Vehicle** | 具体的候補取引を構成する母集団。**意思決定窓内Vehicleだけに限定されない。** |

### 7.2 TVT候補Vehicleの時間条件（確定）

権利保有車両の baseline予想通過可能 timestep の **1 timestep 前まで**に対象 Node へ到着可能と予測される Vehicle：

```
TVT候補Vehicleのbaseline予想到着timestep
<= right_of_entry_expected_passage_timestep - 1
```

同値表現：

```
TVT候補Vehicleのbaseline予想到着timestep + 1
<= right_of_entry_expected_passage_timestep
```

### 7.3 TVT候補Vehicleに含まれ得る Vehicle

- 権利保有車両
- 後に買い手として選択され得る参加 Vehicle
- 買い手の前進によって売り手となり得る参加 Vehicle
- 順位を固定する非参加 Vehicle
- 具体的候補取引によっては当事者にならない Vehicle

### 7.4 時間範囲の関係

意思決定窓内 Vehicle 群と TVT候補 Vehicle 群の時間範囲は、同じ場合もあれば、**TVT候補 Vehicle 群の方が広い**場合もある。

### 7.5 未確定のまま残る Vehicle

意思決定窓外であり、成立取引にも含まれず、順位も確定しなかった Vehicle は未確定のまま残る。

- 後続 timestep の別 TVT 検討で時間条件を満たせば、何度でも TVT候補 Vehicle になり得る。
- 将来その Vehicle 自身が意思決定窓へ初めて入ったとき、別の権利保有車両を起点とする TVT の候補にもなり得る。
- その時点で意思決定窓内の未確定参加 Vehicle の中で最上位なら、**その Vehicle 自身が権利保有車両**となり TVT 検討の起点になる。

---

## 8. 権利保有車両

### 8.1 定義（確定）

権利保有車両は、**最初に通過すると予測された Vehicle ではない**。

既到着 Vehicle の強制確定後、**意思決定窓内にいる未確定参加 Vehicle のうち、baseline予想到着順位が最上位の Vehicle**。

### 8.2 権利の内容（確定）

- 権利保有車両が持つのは、**最初に通過を試す権利**。
- 実際に最初に通過できることを**保証しない**。
- 通過できない場合は、既存 FCFS と同様に、通過不能理由に応じて後順位 Vehicle へ通過機会を回すことがある。

### 8.3 baseline予想通過可能timestep

TVT候補 Vehicle の時間範囲を定めるため、権利保有車両の **baseline予想通過可能 timestep** も全World baseline から取得する。

---

## 9. TVT候補生成ルール

### 9.1 最終ルール名称（確定）

Case I、II、III は**最終的な比較対象として残さない**。次を使用する：

| 略称 | 名称 |
|------|------|
| **TVT-SB** | Single-Buyer Rule |
| **TVT-MH** | Multi-Inlink Head-Buyer Rule |
| **TVT-SP** | Single-Inlink Prefix-Buyer Rule |
| **TVT-MP** | Multi-Inlink Prefix-Buyer Rule |

**TVT-MP が最も一般的**であり、他の三方式を構造的に包含する。

経済的に非合理で納得性の低い簡易 Case I を、研究上の比較対象として別途実装する可能性は**保留**（§20）。

### 9.2 候補 inlink と prefix（確定）

- 権利保有車両と**同じ inlink** は、買い手候補 inlink から**除外**する。
- 各候補 inlink では、買い手を**物理的先頭 Vehicle からの連続 prefix** として選ぶ。

例：inlink B に `B1, B2, B3` がいる場合、許可される選択：

- 選ばない
- `B1`
- `B1, B2`
- `B1, B2, B3`

`B2` だけ、`B1` と `B3` だけ、`B2` と `B3` だけ、という候補は**生成しない**。

- 複数 inlink から買い手が選ばれた場合、inlink の処理順は使わず、**全World baseline の予想到着順位**で買い手を並べ直す。

### 9.3 候補数（確定）

候補 inlink 数を `L`、各候補 inlink の候補 Vehicle 数を `n_l` とする：

| 方式 | 候補数 |
|------|--------|
| TVT-SB | `N_SB = L` |
| TVT-MH | `N_MH = 2^L - 1` |
| TVT-SP | `N_SP = Σ n_l` |
| TVT-MP | `N_MP = ∏(n_l + 1) - 1` |

### 9.4 候補順位範囲の初期上限（確定）

- **初期上限：10**（公平性上の値ではなく、候補生成と計算量評価の初期上限）。
- 感度分析候補：**15**、**20**（保留・評価対象）。

### 9.5 4方式と共通処理の関係（設計用補足）

4方式で異なるのは、基本的に**買い手集合の生成方法**です。

- **TVT-SB**：各候補 inlink の物理的先頭 Vehicle を、一台ずつ個別の買い手集合候補とする
- **TVT-MH**：各候補 inlink の物理的先頭 Vehicle について、選択または非選択を組み合わせる
- **TVT-SP**：一つの候補 inlink を選び、その inlink の物理的先頭から連続する prefix を選ぶ
- **TVT-MP**：複数の候補 inlink について、各 inlink の prefix 長を組み合わせる

各方式で買い手集合を生成した後は、非参加 Vehicle なしの場合、§10・§11 の共通順位計算を使用します。

処理関係は次です。

```text
方式別に買い手集合を生成する
↓
複数inlinkから集めた買い手を一つのリストへ統合する
↓
買い手をbaseline順位順へ並べ直す
↓
候補ごとの最後の買い手を特定する
↓
trade_scopeを決める
↓
売り手を特定する
↓
trade_rankを構成する
↓
trade_orderを派生させる
↓
同一inlink FIFOを確認する
↓
局所仮想計算を行う
↓
経済評価を行う
```

この共通処理は、非参加 Vehicle なしの候補について導出済みです。

非参加 Vehicle ありの候補は、§12 の別処理を使用します。

### 9.6 TVT-SBの買い手候補条件（設計用補足）

TVT-SB の買い手候補は、次をすべて満たす Vehicle です。

- 権利保有車両とは別 inlink にいる
- その inlink の物理的先頭 Vehicle である
- TVT候補 Vehicle の時間条件を満たす
- TVT参加 Vehicle である

したがって、権利保有車両と同じ inlink の後続 Vehicle を、TVT-SB の単独買い手候補として生成しません。

買い手候補生成規則によって防げる FIFO 違反と、非参加 Vehicle の固定順位を含む取引後順位構成後に初めて判明する FIFO 違反は区別してください。

### 9.7 TVT-MHの構造（設計用補足）

TVT-MH では、各候補 inlink の物理的先頭 Vehicle について、選択または非選択を組み合わせます。

例えば、候補 inlink の先頭 Vehicle が B1 と C1 なら、買い手集合候補は次です。

```python
[B1]
[C1]
[B1, C1]
```

全 Vehicle を選ばない候補は取引にならないため除外します。

候補数は次です。

```text
N_MH = 2^L - 1
```

### 9.8 TVT-SPの構造と最大9候補の導出（設計用補足）

TVT-SP では、一つの候補 inlink を選び、その inlink の物理的先頭 Vehicle から連続する prefix を買い手集合とします。

例えば、inlink B に次の Vehicle がいる場合、

```python
[B1, B2, B3]
```

候補は次です。

```python
[B1]
[B1, B2]
[B1, B2, B3]
```

候補数は次です。

```text
N_SP = n_1 + n_2 + ... + n_L
```

候補順位範囲の初期上限は 10 台であり、その中に権利保有車両 1 台を含みます。

したがって、権利保有車両以外の TVT候補 Vehicle は最大 9 台です。

```text
n_1 + n_2 + ... + n_L <= 9
```

よって、次が成立します。

```text
N_SP <= 9
```

この最大 9 候補という値は、次の前提に依存します。

- 候補順位範囲上限が 10
- その中に権利保有車両 1 台を含む
- 非参加 Vehicle なし
- 同じ Vehicle を複数の候補 inlink へ重複計上しない

### 9.9 TVT-MPの構造（設計用補足）

TVT-MP では、各候補 inlink について、選択する prefix 長を 0 からその inlink の候補 Vehicle 数までの範囲で選びます。

例えば、

```python
inlink_B = [B1, B2]
inlink_C = [C1]
inlink_D = [D1, D2]
```

なら、各 inlink の選択肢数は次です。

```text
inlink B：0台、1台、2台の3通り
inlink C：0台、1台の2通り
inlink D：0台、1台、2台の3通り
```

組合せ総数は、

```text
3 × 2 × 3 = 18
```

です。

全 inlink で 0 台を選ぶ組合せを除外するため、具体的取引候補数は、

```text
18 - 1 = 17
```

です。

一般式は次です。

```text
N_MP = ∏(n_l + 1) - 1
```

### 9.10 選択prefixの統合（設計用疑似コード）

**対象となるTVT方式**：TVT-MP（および複数 inlink から prefix を選ぶ全方式）

**使用前提**：各候補 inlink で選択された prefix が `selected_prefixes` として与えられている。

**入力の意味**：`selected_prefixes` — inlink 別に選ばれた prefix のリスト（各要素は Vehicle 列）

**出力の意味**：`buyers` — 統合直後の買い手 Vehicle 列（baseline 順位順ではない）

**各変数の意味**：`buyers` — 複数 prefix から統合した買い手 Vehicle 列；`buyers_sorted` — baseline 順位順に並べ直した買い手 Vehicle 列

**順位の基準**：`baseline_rank` は 1 始まりの辞書（§11.5 参照）

**具体例**：下記のとおり

**実装済みコードではなく、設計用の疑似コードである。**

```python
buyers = []

for prefix in selected_prefixes:
    buyers.extend(prefix)
```

具体例：

```python
selected_prefixes = [
    [B1, B2],
    [C1],
]
```

統合直後は次です。

```python
buyers = [B1, B2, C1]
```

inlink 別 prefix の列挙順は、Node 全体の baseline 順位順とは限りません。

そのため、次の疑似コードで baseline 順位順へ並べ直します。

```python
buyers_sorted = sorted(
    buyers,
    key=lambda vehicle: baseline_rank[vehicle],
)
```

例えば、baseline 順位が次の関係なら、

```text
B1 < C1 < B2
```

結果は次です。

```python
buyers_sorted = [B1, C1, B2]
```

---

## 10. 取引後の割当権利行使順位

### 10.1 候補列挙と評価（確定）

複数の候補取引を列挙する。各候補について、**最後の買い手**となる Vehicle を一台定め、その Vehicle を含む買い手集合を構成する。別の Vehicle を最後の買い手とする候補も、それぞれ独立した候補取引として評価する。

### 10.2 候補ごとの処理（確定）

1. 買い手集合を生成する
2. 買い手集合を baseline 順位順へ並べる
3. 当該候補における最後の買い手を特定する
4. 最後の買い手の baseline 順位までを `trade_scope` とする
5. `trade_scope` 内の非買い手参加 Vehicle を売り手とする
6. 非参加 Vehicle がいれば、その順位を固定する
7. 取引後の割当権利行使順位を作る
8. FIFO 条件を確認する
9. 局所仮想計算を行う
10. 経済評価を行う

成立条件を満たす候補の中から、**経済価値が最も高いもの**を選ぶ。

### 10.3 候補ごとの最後の買い手（設計用疑似コード）

**対象となるTVT方式**：TVT-SB、TVT-MH、TVT-SP、TVT-MP（買い手集合生成後の共通処理）

**使用前提**：一つの具体的取引候補について、`buyers_sorted` が与えられている。

**入力の意味**：`buyers_sorted` — 当該具体的取引候補の買い手 Vehicle 列（baseline 順位順）

**出力の意味**：`last_buyer_rank` — 当該具体的取引候補における最後の買い手の baseline 順位（1 始まり）

**各変数の意味**：`last_buyer_rank` — 当該候補の `trade_scope` 決定に使用する 1 始まりの baseline 順位値

**順位の基準**：`baseline_rank` は 1 始まりの辞書（§11.5 参照）

**実装済みコードではなく、設計用の疑似コードである。**

最後の買い手は、全候補を通じて事前に一台へ固定するものではありません。

一つの具体的取引候補に含まれる買い手集合ごとに、次を計算します。

```python
last_buyer_rank = max(
    baseline_rank[buyer]
    for buyer in buyers_sorted
)
```

次を明記する。

- 一つの具体的取引候補について計算する
- 買い手集合候補ごとに `last_buyer_rank` は変わり得る
- 最後の買い手となり得る Vehicle は複数存在する
- 各具体的取引候補を局所仮想計算と経済条件で評価する
- 成立候補の中から最も価値の高い候補を選ぶ

---

## 11. 非参加Vehicleなしの順位構築

### 11.1 方式（確定）

非参加 Vehicle がいない場合は、**共通 trade_rank 方式**を使用する。

### 11.2 変数名と意味

| 変数 | 意味 |
|------|------|
| `buyers_sorted` | baseline 順位順に並べた買い手 Vehicle 列 |
| `sellers_sorted` | `trade_scope` 内の非買い手参加 Vehicle（baseline 相対順維持） |
| `last_buyer_rank` | 当該候補の最後の買い手の baseline 順位 |
| `trade_scope` | 最後の買い手の baseline 順位までの範囲 |
| `trade_rank` | 取引後割当権利行使順位の**正本** |
| `trade_order` | 必要時のみ `trade_rank` から派生 |

### 11.3 順位付け規則（確定）

- 買い手：baseline 相対順を維持して 1 位から連続順位を付与。
- 売り手：`trade_scope` 内の非買い手参加 Vehicle。`sellers_sorted` は baseline 相対順を維持。
- 各売り手の取引後順位（概念式）：

```
売り手のbaseline順位 + その売り手よりbaselineで後ろにいた買い手数
```

- 取引範囲外 Vehicle は baseline 順位を維持。

### 11.4 検証上の注意

過去の 11 候補確認は**手作業**によるものであり、共通 `trade_rank` コードを実行して生成したものではない。**独立診断コードによる自動検証が必要**（§22）。

### 11.5 順位とPython添字に関する共通注意

- Python のリスト添字は **0 始まり**である
- `baseline_rank` はリスト添字ではない
- `baseline_rank` は、Vehicle をキー、**1 始まり**の順位を値とする辞書である
- 辞書の値は任意に設定できるため、`baseline_rank` を 1 始まりにしても Python の規則には反しない

次の例をそのまま用いる。

```python
baseline_order = [A1, B1, C1]

baseline_rank = {
    A1: 1,
    B1: 2,
    C1: 3,
}
```

このとき、

```python
baseline_order[0]  # A1
baseline_rank[A1]  # 1
```

である。

また、次を用いる。

```python
trade_scope = baseline_order[:last_buyer_rank]
```

`last_buyer_rank` は **1 始まり**の順位値である。

例えば、

```python
last_buyer_rank = 2
```

なら、

```python
trade_scope = baseline_order[:2]
```

の結果は、

```python
[A1, B1]
```

である。

Python のスライス終端は含まれないが、0 始まりのリストに 1 始まりの順位値をそのまま終端として使用することで、当該順位の Vehicle までを含む範囲になる。

### 11.6 設計用疑似コード：非参加Vehicleなしの共通順位計算

**対象となるTVT方式**：TVT-SB、TVT-MH、TVT-SP、TVT-MP（非参加 Vehicle なしの候補）

**使用前提**：

- 現在の未確定範囲を対象とする
- `baseline_order` は未確定範囲内の baseline 予想到着順位順
- `baseline_rank` は Vehicle をキー、1 始まりの未確定範囲内 baseline 順位を値とする辞書
- `buyers` には、この具体的取引候補で選択された買い手 Vehicle が入っている
- 非参加 Vehicle は含まれない
- `trade_rank` は未確定範囲内の取引後割当権利行使順位の正本
- Node 全体の順位への変換は、確定順位ブロックへ接続するときに行う

**入力の意味**：`baseline_order`、`baseline_rank`、`buyers`

**出力の意味**：`buyers_sorted`、`sellers_sorted`、`last_buyer_rank`、`trade_rank`、`trade_order`

**順位の基準**：`baseline_rank` は 1 始まり；`trade_rank` の値も 1 始まりの未確定範囲内順位

**実装済みコードではなく、設計用の疑似コードである。**

#### 1. 買い手をbaseline順位順へ並べる

```python
buyers_sorted = sorted(
    buyers,
    key=lambda vehicle: baseline_rank[vehicle],
)
```

#### 2. 最後の買い手のbaseline順位を求める

```python
last_buyer_rank = max(
    baseline_rank[buyer]
    for buyer in buyers_sorted
)
```

#### 3. 最後の買い手までを取引範囲として切り出す

```python
trade_scope = baseline_order[:last_buyer_rank]
```

#### 4. 買い手判定用の補助集合を作る

```python
buyer_set = set(buyers_sorted)
```

`buyer_set` は順位の正本ではなく、Vehicle が買い手かどうかを効率的に判定するための補助集合である。

#### 5. 売り手をbaseline順位順で抽出する

```python
sellers_sorted = [
    vehicle
    for vehicle in trade_scope
    if vehicle not in buyer_set
]
```

これは非参加 Vehicle なしの処理を前提とする。

そのため、`trade_scope` 内の非買い手 Vehicle はすべて参加 Vehicle であり、売り手になる。

#### 6. trade_rankを初期化し、買い手へ新順位を付与する

```python
trade_rank = {}

for new_rank, buyer in enumerate(
    buyers_sorted,
    start=1,
):
    trade_rank[buyer] = new_rank
```

買い手間の baseline 相対順を維持し、1 位から連続順位を付与する。

#### 7. 売り手ごとに、その売り手よりbaselineで後ろにいた買い手数を数える

```python
for seller in sellers_sorted:
    seller_baseline_rank = baseline_rank[seller]

    buyers_behind = sum(
        1
        for buyer in buyers_sorted
        if baseline_rank[buyer] > seller_baseline_rank
    )

    trade_rank[seller] = (
        seller_baseline_rank
        + buyers_behind
    )
```

ここで「後ろ」とは、baseline 順位の数値が大きいことを意味する。

買い手が売り手の後方から前方へ移動するたびに、その売り手の割当権利行使順位が 1 つ後退する。

#### 8. 取引範囲外Vehicleはbaseline順位を維持する

```python
for vehicle in baseline_order:
    if vehicle not in trade_rank:
        trade_rank[vehicle] = baseline_rank[vehicle]
```

#### 9. trade_rankからtrade_orderを派生させる

```python
trade_order = sorted(
    baseline_order,
    key=lambda vehicle: trade_rank[vehicle],
)
```

`trade_rank` が順位情報の正本である。

`trade_order` は、表示、診断、FIFO 検査、局所仮想計算に使用する派生順位列である。

次の具体例：

```python
trade_rank = {
    B1: 1,
    C1: 2,
    A1: 3,
}
```

その場合、`trade_order` は次である。

```python
trade_order = [B1, C1, A1]
```

#### 10. 返却値

```python
return {
    "buyers_sorted": buyers_sorted,
    "sellers_sorted": sellers_sorted,
    "last_buyer_rank": last_buyer_rank,
    "trade_rank": trade_rank,
    "trade_order": trade_order,
}
```

`buyers_sorted` と `sellers_sorted` の両方が、baseline 相対順を明示的に維持する Vehicle 列である。

---

## 12. 非参加Vehicleありの順位構築

### 12.1 非参加Vehicleの扱い（確定）

- 非参加 Vehicle は TVT の買い手にも売り手にもならない。
- TVT の明示的な順位交換によって、**非参加 Vehicle の割当権利行使順位を変更してはいけない**。
- 実際の到着時刻や実通過順位は交通状態により変化し得るが、**TVT が割り当てる順位は固定**する。

### 12.2 処理の分岐（確定）

可読性を重視し、非参加 Vehicle の有無で**別の順位構築処理**を使用する：

| 条件 | 方式 |
|------|------|
| 非参加 Vehicle なし | 直接的な共通 `trade_rank` 方式（§11） |
| 非参加 Vehicle あり | **固定順位枠方式** |

### 12.3 固定順位枠方式（確定・単一買い手まで）

1. 非参加 Vehicle の baseline 順位を固定する
2. 買い手を許された先頭側順位へ配置する
3. 参加売り手を baseline 相対順で残りの空き順位へ配置する
4. 取引後順位列を作る
5. 同一 inlink FIFO を確認する

非参加 Vehicle ありの**単一買い手**では、固定順位枠方式が採用方針。

### 12.4 非参加Vehicleあり・複数買い手一般形（保留）

**未完成**。固定順位枠と確定ブロックの接続ではなく、次が未確定：

- どの買い手集合を生成するか
- 各 inlink の prefix と非参加固定順位をどう両立させるか
- 有効候補を取りこぼさないか
- 候補数をどう抑えるか
- FIFO 違反候補をどこまで事前除外するか

### 12.5 非参加Vehicleの有無による処理分岐の説明（設計用補足）

> 非参加車両を含まない候補では、買い手と売り手のbaseline順位から取引後順位を直接算出する。非参加車両を含む候補では、非参加車両のbaseline順位を固定枠として保持したうえで、残る順位枠へ買い手と売り手を配置する。両方式を使い分ける理由は、処理の可読性と、非参加車両の順位不変条件を明示的に保証するためである。

将来、実装時の docstring に使用する英語版として、次をそのまま用いる。

```python
"""
For candidates without non-participating vehicles, post-trade
ranks are calculated directly from the baseline ranks of buyers
and sellers. For candidates containing non-participating vehicles,
their baseline ranks are preserved as fixed rank slots, and buyers
and sellers are placed in the remaining slots. Separate procedures
are used to improve readability and to explicitly guarantee that
the assigned ranks of non-participating vehicles remain unchanged.
"""
```

日本語版を設計上の正本とし、実装時の docstring には英語版を使用する予定である。

### 12.6 固定順位枠方式で確認済みの処理手順（設計用補足）

次の処理手順は確認済みである。

1. 非参加 Vehicle の baseline 順位を固定する
2. 買い手を許された先頭側順位へ配置する
3. 参加売り手を baseline 相対順で残る空き順位へ配置する
4. 取引後順位列を一意に作る
5. 同一 inlink FIFO を検査する
6. FIFO 違反なら、その具体的取引候補を棄却する

次も明記する。

- 同じ具体的取引候補について、FIFO を満たすまで順位配置を繰り返す方式ではない
- 候補ごとに一度だけ順位を構成し、FIFO 検査の結果で採用または棄却するフィルタリング方式である
- 候補全体では生成と棄却を繰り返すため、広い意味で試行錯誤型と表現する合理性がある

ただし、非参加 Vehicle あり単一買い手について、**実装用の完全な固定順位枠疑似コードはまだ確定していない**。

---

## 13. 同一inlink FIFO

### 13.1 原則（確定）

同じ inlink 上の Vehicle の **baseline 相対順**を、TVT によって**逆転させてはいけない**。

### 13.2 検査方法（確定）

- 取引前と取引後の順位列から同一 inlink Vehicle だけを抽出し、相対順が同じか確認する。
- 同一 inlink で複数買い手を選ぶ場合に **prefix だけを生成**することは、FIFO 違反候補を最初から減らすための**候補生成規則**。
- 候補生成規則によって FIFO を維持することを基本とし、完成した取引後順位列に対する FIFO 検査は、候補生成または順位構成の誤りを検出するための**安全確認**として実施する。

### 13.3 検査対象外（確定）

- **確定順位ブロックと新規確定順位列の接続部**だけを対象とする追加的な FIFO 検査は**行わない**。
- 接続部分は baseline 順位の前後関係を維持して接続されるため。
- FIFO 検査は、**取引によって順位を構成し直した範囲**を対象とする。

### 13.4 固定順位枠方式と FIFO（確定）

- 固定順位枠方式は、候補ごとに取引後順位を一意に構成し、FIFO 違反なら候補を**棄却**するフィルタリング方式。
- 同じ候補について、FIFO を満たすまで順位配置を繰り返す方式ではない。
- 候補生成と棄却を繰り返すため、広い意味では試行錯誤型と表現することに合理性がある。

### 13.5 事前除外（保留）

初期実装では FIFO 棄却数と棄却率を計測し、棄却率が高い場合にだけ事前除外条件を追加する案を保留。

#### FIFO検査の概算負荷（設計用補足）

Vehicle 数を `N`、関係 inlink 数を `L` とする。

現在の `preserves_inlink_fifo()` は、一つの inlink ごとに、

1. `baseline_order` の `N` 台を確認する
2. `trade_order` の `N` 台を確認する

ため、おおむね `2N` 回の Vehicle 条件確認を行う。

これを `L` 本の inlink について行うため、粗い上限概算は次である。

```text
L × 2N = 2 × N × L
```

例えば、`N=10`、`L=4` なら、

```text
2 × 10 × 4 = 80
```

程度の Vehicle 条件確認である。

これは、現在のリスト内包表記をそのまま実行した場合の粗い概算であり、厳密な実行命令数ではない。

局所仮想計算では、複数 timestep にわたり Vehicle、Link、Node の状態を更新するため、初期見通しは次である。

```text
FIFO検査時間
≪
局所仮想計算時間
```

この関係の意味は次である。

- 初期実装では、複雑な FIFO 事前除外規則を最初から多数作らない
- まず取引後順位を構成する
- 比較的安価で単純な FIFO 検査によって違反候補を除外する
- FIFO 検査を通過した候補だけを、高価な局所仮想計算へ渡す
- 候補漏れの危険がある複雑な最適化より、検証しやすい方式を先に採用する

次も記載する。

- FIFO 棄却数を記録する
- FIFO 棄却率を記録する
- FIFO 棄却理由を記録する
- 棄却率が高い場合のみ、明らかな FIFO 違反の事前除外を追加する
- 事前除外追加前後で、有効候補集合が一致することをテストする
- FIFO 検査と局所仮想計算の時間関係は、実装後に実測で確認する

### 13.6 relevant_inlinks（設計用疑似コード）

**対象となるTVT方式**：全 TVT 方式（FIFO 検査前）

**使用前提**：`trade_scope` が決定済みである。

**入力の意味**：`trade_scope` — 当該具体的取引候補の取引範囲内 Vehicle 列

**出力の意味**：`relevant_inlinks` — 取引範囲内 Vehicle が走行している inlink の集合

**実装済みコードではなく、設計用の疑似コードである。**

```python
relevant_inlinks = {
    vehicle.inlink
    for vehicle in trade_scope
}
```

`relevant_inlinks` は、今回の取引範囲内 Vehicle が走行している inlink の集合である。

同じ inlink は集合内に一度だけ入る。

外部から無関係な inlink 集合を渡すのではなく、`trade_scope` から生成する方針である。

### 13.7 FIFO判定関数 preserves_inlink_fifo（設計用疑似コード）

**対象となるTVT方式**：全 TVT 方式

**使用前提**：`baseline_order`、`trade_order`、`relevant_inlinks` が与えられている。

**入力の意味**：

- `baseline_order`：取引前の baseline 順位順に並べた Vehicle 列
- `trade_order`：候補 TVT 適用後の割当権利行使順位順に並べた Vehicle 列
- `relevant_inlinks`：今回の取引範囲に含まれる Vehicle の inlink 集合

**出力の意味**：`True` — 全 relevant inlink で FIFO 維持；`False` — いずれかの inlink で FIFO 違反

**各変数の意味**：

- `baseline_inlink_order`：`baseline_order` から現在確認中の inlink の Vehicle だけを抜き出した列
- `trade_inlink_order`：`trade_order` から同じ inlink の Vehicle だけを抜き出した列

**実装済みコードではなく、設計用の疑似コードである。**

```python
def preserves_inlink_fifo(
    baseline_order,
    trade_order,
    relevant_inlinks,
):
    for inlink in relevant_inlinks:
        baseline_inlink_order = [
            vehicle
            for vehicle in baseline_order
            if vehicle.inlink is inlink
        ]

        trade_inlink_order = [
            vehicle
            for vehicle in trade_order
            if vehicle.inlink is inlink
        ]

        if baseline_inlink_order != trade_inlink_order:
            return False

    return True
```

### 13.8 FIFO維持例（設計用補足）

```python
baseline_order = [A1, B1, A2, C1, B2]
trade_order = [B1, A1, A2, C1, B2]
```

inlink_A だけを抜き出すと、次である。

```python
baseline_inlink_order = [A1, A2]
trade_inlink_order = [A1, A2]
```

両者が一致するため、inlink_A の FIFO は維持されている。

### 13.9 FIFO違反例（設計用補足）

```python
baseline_order = [S1, N, B]
trade_order = [B, N, S1]
```

S1 と N は同じ inlink_A にいて、S1 が N の前方にいるものとする。

inlink_A だけを抜き出すと、次である。

```python
baseline_inlink_order = [S1, N]
trade_inlink_order = [N, S1]
```

両者が異なるため、`preserves_inlink_fifo()` は `False` を返す。

これは、S1 の後方を走行していた N が、取引後順位では S1 より前になっており、単車線上で物理的に実現できないためである。

---

## 14. 確定順位ブロックの拡張

### 14.1 確定順位ブロックの定義（確定）

今回の TVT より前に割当権利行使順位が確定している Vehicle の連続順位列。

### 14.2 順位の付与（確定）

#### 順位記号の基準

以下の記号は、Node 全体の絶対順位ではなく、既存の確定順位ブロックを除いた**現在の未確定範囲内順位**を表す（`K_confirmed_before` および `K_confirmed_after` を除く）。

**1. 現在の未確定範囲**

既存の確定順位ブロックより後ろに位置し、割当権利行使順位がまだ確定していない Vehicle の順位範囲。

**2. 未確定範囲内 baseline 順位（`baseline_rank`）**

現在の未確定範囲だけを対象として、baseline 予想到着順位を 1 位から数えた順位。TVT 候補生成と取引後順位構築では、`baseline_rank` はこの未確定範囲内順位として扱う。

**3. `r_local`**

新規に確定する順位列における未確定範囲内順位。

**4. `K_confirmed_before`**

既到着未確定 Vehicle の強制確定が完了した後、今回新たに確定する順位列を接続する直前における、確定順位ブロック末尾の Node 全体での割当権利行使順位。既到着未確定 Vehicle が存在しない場合は、それ以前から存在する確定順位ブロック末尾の順位。確定順位ブロックが空の場合は 0。

**5. `r_assigned`**

Node 全体での割当権利行使順位：

```
r_assigned = K_confirmed_before + r_local
```

**6. `K_confirmed_after`**

今回の処理後における、拡張後の確定順位ブロック末尾の Node 全体での割当権利行使順位：

```
K_confirmed_after = K_confirmed_before + K_fixed
```

例：既存確定順位ブロックが 1 位から 5 位までで、`K_fixed` が 4 なら、拡張後の確定順位ブロック末尾は 9 位（`K_confirmed_after = 5 + 4 = 9`）。

**`trade_rank`**

取引後割当権利行使順位の正本（§11）。`trade_rank` も未確定範囲内順位として構成する。Node 全体での割当権利行使順位へ変換するのは、新規確定順位列を既存確定順位ブロックへ接続するときである。

**二重加算の禁止**

`K_last_buyer`、`K_decision_window`、`K_fixed` は現在の未確定範囲内順位である。これらを Node 全体の絶対順位として扱い、さらに `K_confirmed_before` を加えるような**二重加算をしない**。

#### 順位の付与

処理順は次のとおり。

1. 既存の確定順位ブロックを確認する
2. 既到着未確定 Vehicle がいれば、先に割当権利行使順位を付与して確定順位ブロックへ追加する
3. その時点の確定順位ブロック末尾を `K_confirmed_before` とする
4. TVT 成立、不成立、または未解決時に新たに確定する順位列を、その直後へ接続する
5. `r_assigned = K_confirmed_before + r_local`
6. `K_confirmed_after = K_confirmed_before + K_fixed`

この加算は単なる連番付与であり、**独立した未解決問題ではない**。「確定ブロック後の順位オフセット」を主要な未解決事項として扱わない。

### 14.3 TVT成立時の確定範囲（確定）

```
K_fixed = max(K_last_buyer, K_decision_window)
```

| 記号 | 意味 |
|------|------|
| `K_last_buyer` | 採用された候補取引における最後の買い手の、**現在の未確定範囲内 baseline 順位** |
| `K_decision_window` | 今回の意思決定窓内 Vehicle のうち、**未確定範囲内 baseline 順位**が最後の Vehicle の順位 |
| `K_fixed` | 今回新たに確定する、**現在の未確定範囲の終端順位** |

既到着 Vehicle は別途先に強制確定するため、`K_decision_window` の算定対象に含めない。

`K_last_buyer`、`K_decision_window`、`K_fixed` はいずれも未確定範囲内順位であり、Node 全体の絶対順位ではない（§14.2「二重加算の禁止」参照）。

### 14.4 確定の具体（確定）

**TVT が成立した場合**：`K_fixed` までを確定する。

- TVT 当事者は取引後順位で確定。
- 取引によって順位を変更されない Vehicle は baseline 順位を維持して確定。

**TVT が不成立の場合**：今回の意思決定窓内に含まれる未確定 Vehicle 全体を、baseline FCFS 予想到着順位のまま確定。

**次の場合も同様に baseline 順位で確定**：

- 全World baseline で TVT 候補形成に必要な情報を解決できなかった場合。
- 生成した候補取引のうち、局所仮想計算で通過時刻等を解決できた候補が一つもなかった場合。

**意思決定窓外の未確定 Vehicle**は、上記の理由だけでは確定しない。

---

## 15. 経済評価と候補選択

### 15.1 評価手順（確定）

候補ごとに局所仮想計算を実行し、baseline との予想通過時刻差を評価する。

1. 各買い手の利益 `G_b` を計算する
2. `G_b <= 0` となる候補を除外する
3. 各売り手の必要補償額または留保額 `R_s` を計算する
4. 買い手側総価値 `G` を計算する
5. 売り手側必要補償額 `R` を計算する
6. `G >= R` を満たす候補を成立可能とする
7. **`G - R` が最大**の候補を選ぶ
8. `G - R` が同値なら、**当事者数が多い**候補を選ぶ
9. 当事者数も同じなら、**ランダム**に選ぶ

### 15.2 ランダム選択（保留）

最後のランダム選択の具体的 RNG 設計は保留（§20）。

### 15.3 経済評価の変数と数式（設計用補足）

各買い手 `b` の利益：

```text
G_b
```

各売り手 `s` の必要補償額または留保額：

```text
R_s
```

買い手側総価値：

```text
G = Σ G_b
```

売り手側必要補償総額：

```text
R = Σ R_s
```

各買い手について、次を必要条件とする。

```text
G_b > 0
```

`G_b` が 0 以下となる買い手を一台でも含む具体的取引候補は、成立候補として採用しない。

そのため、成立候補では必ず次が成り立つ。

```text
G > 0
```

経済的成立条件は次である。

```text
G >= R
```

候補の経済価値、または余剰は次である。

```text
surplus = G - R
```

成立候補の中から `surplus` が最大の候補を選ぶ。

`surplus` が同値なら、当事者数が多い候補を選ぶ。

当事者数も同じならランダムに選ぶ。

ランダム選択の具体的 RNG 設計は保留事項である。

### 15.4 買い手別支払額（設計用補足）

取引価格の総額は、売り手側必要補償総額 `R` である。

各買い手 `b` の支払額は、各買い手の利益 `G_b` に比例して配分する。

```text
P_b = R * G_b / G
```

次を明記する。

- 成立候補では各 `G_b` が正である
- したがって `G` は必ず正である
- `P_b` の計算で `G=0` によるゼロ除算は発生しない
- 各売り手への必要補償額は `R_s`
- 売り手側必要補償総額は `R = ΣR_s`
- 支払額と補償額は予測値に基づいて取引成立時に事前確定する
- 実通過結果に基づく事後精算は行わない
- 内部計算では値を丸めない
- 表示または出力時だけ必要な桁数へ丸める

### 15.5 G >= Rの数値比較方法（設計用補足）

#### 方式1：完全比較方式

当面の採用方式である。

```python
established = G >= R
```

内部の未丸め値をそのまま比較する。

制度上、わずかでも `G` が `R` を下回る候補は不成立とする。

長所：

- 制度定義と直接対応する
- 判定が分かりやすい
- ログの解釈が容易
- ごく小さい負の余剰を成立扱いしない

注意：

- Python の浮動小数点表現誤差により、数学的には等しい値がわずかに異なる可能性がある

#### 方式2：Tolerance方式

代替案である。

```python
established = G >= R - epsilon
```

または同値な表現として、

```python
established = G + epsilon >= R
```

長所：

- 浮動小数点表現誤差や加算誤差に強い

短所：

- `epsilon` の選定が必要
- 厳密には `G < R` の候補を成立扱いする可能性がある
- `epsilon` が制度上の追加パラメータとなる

#### 方式3：Decimal方式

代替案である。

```python
established = Decimal(G) >= Decimal(R)
```

長所：

- 2 進浮動小数点による誤差を大幅に抑えられる
- `G >= R` の制度定義に近い比較ができる

短所：

- 実装が複雑になる
- float より計算負荷が大きい
- シミュレーション由来の値を Decimal へどの時点で変換するかを決める必要がある

現時点の方針は次である。

- 初期実装では**完全比較方式**を採用する
- 内部計算では丸めない
- 表示時だけ丸める
- 数値表現誤差により、本来成立すべき候補が不成立になる問題が実際に確認された場合、Tolerance 方式または Decimal 方式を再検討する
- Tolerance 方式と Decimal 方式は撤回案ではなく、問題発生時の代替案である

---

## 16. 全World baselineと局所仮想計算の役割分担

### 16.1 全World baseline仮想計算

- **役割**：取引なし条件における到着・通過予測の取得。
- **対象**：World 全体。
- **頻度・horizon**：保留（§18, §20）。

### 16.2 局所仮想計算

- **役割**：個別の候補取引によって割当権利行使順位を変えた場合の予想通過時刻を計算。
- **対象範囲**：対象 Node の**全 inlink と全 outlink**を基本とする。

### 16.3 同一timestepの処理（確定）

- 同一 timestep では各 Node が**共通全World baseline**を参照し、それぞれ独立に候補を局所評価する。
- 各 Node で**最大1件**の TVT を選び、全 Node の評価完了後に**一括して実 World へ登録**する構想。
- Node の反復順が同一 timestep の取引結果に影響しないようにする。

### 16.4 予測限界（確定）

局所計算である以上、他 Node で同時に成立する TVT の将来影響を完全には予測できない。この差は、予測値と実現値の差として**事後評価**する。

---

## 17. BATCH Level 2から再利用可能な実装

BATCH Level 2（`order_control_batch_level_2_reference.py`）で実装済みの以下は、TVT 局所仮想計算の参考になる。**ただし全World baseline は BATCH の局所 mimic World とは異なるため、そのまま流用できると断定しない。**

| 項目 | BATCH L2 での実装状況 |
|------|----------------------|
| mimic World 構築方法 | 実装済み |
| Node、Link、Vehicle 対応辞書 | 実装済み |
| capacity、clearance、service queue 状態の複製 | 実装済み |
| leader、follower の再構築 | 実装済み |
| route 状態の複製 | 実装済み |
| Analyzer を生成しない mimic World | 実装済み（高速化に大きな効果） |
| 通常 `exec_simulation()` を使わない限定仮想ループ | 実装済み |
| 実 World と実 Vehicle を変更しない処理 | 実装済み |
| 実 World RNG を消費しない処理 | 実装済み |
| `resolved` / `unresolved` の区別 | 実装済み |
| 軽量カウンター | 実装済み |

**注意**：TVT の全World baseline 仮想計算は、BATCH の局所 mimic World（単一 Node 周辺）とはスコープが異なる。再利用は設計・実装時に個別に判断する。

---

## 18. 性能測定の必要性

### 18.1 方針

現段階では**性能測定コードを作成しない**。本節は測定**計画**のみを記載する。

### 18.2 測定項目（計画）

少なくとも次を**別々に**測定する：

| 測定項目 | 内容 |
|----------|------|
| World コピー時間 | 5,000 台 World のコピー時間 |
| 仮想進行（6 step） | コピー後 6 timestep 進行時間 |
| 仮想進行（30 step） | コピー後 30 timestep 進行時間 |
| 仮想進行（50 step） | コピー後 50 timestep 進行時間 |
| Analyzer 有無 | Analyzer あり・なしの差 |
| ログ記録有無 | ログ記録あり・なしの差 |
| 毎実 timestep 実行 | 毎実 timestep 実行した場合の全体推定時間 |
| 2〜3 timestep 間隔 | 2 または 3 timestep 間隔の場合の全体推定時間 |

### 18.3 6 timestep 時点の追加測定（計画）

- World 全体で意思決定窓内 Vehicle を一台も検知できず、6 timestep で仮想計算を終了できた回数
- 6 timestep 時点で延長が必要になった回数
- 需要条件および混雑条件別の頻度

### 18.4 50 timestep 時点の追加測定（計画）

- 50 timestep まで進めた回数
- 50 timestep 進めても必要な到着・通過情報を取得できなかった回数
- 未解決 Vehicle 数
- 未解決 Node 数
- 未解決理由
- 需要条件および混雑条件別の未解決率
- 将来 50 を 100 へ延長した場合の解決率改善

参考：`diagnostics/order_control/world_state_branching_investigation.py` において、5,000 台 World のコピー時間（tracemalloc なし中央値約 1.59 s）等の初期調査結果がある。

---

## 19. 確定事項

本文で確定した内容の要約：

- FCFS 順位は**全World baseline 予想到着順位**
- TVT が変更するのは**割当権利行使順位**（実到着時刻・実通過順位を直接操作しない）
- **意思決定窓の基本値は 6 timestep**（安全性・現実性の根拠。全World baseline horizon ではない）
- **既到着 Vehicle は意思決定窓内 Vehicle に含めない**
- **既到着 Vehicle は参加状態を問わず TVT 起点にしない**
- 同着順位は **baseline予想到着 timestep → 固定 tiebreaker → Vehicle ID**
- **参加状態中立方式**
- 意思決定窓内の未確定参加 Vehicle の最上位が**権利保有車両**（最初に通過予測された Vehicle ではない）
- **意思決定窓内 Vehicle と TVT候補 Vehicle を区別**
- TVT候補時間条件：`baseline予想到着timestep <= right_of_entry_expected_passage_timestep - 1`
- 候補生成ルール：**TVT-SB、TVT-MH、TVT-SP、TVT-MP**（TVT-MP が一般形）
- 非参加なし：**共通 trade_rank 方式**
- 非参加あり：**固定順位枠方式**（単一買い手まで確定）
- **同一 inlink FIFO 維持**（prefix 生成規則＋取引後順位の安全確認）
- TVT 成立時確定範囲：`K_fixed = max(K_last_buyer, K_decision_window)`
- 不成立・未解決時：意思決定窓内 Vehicle 全体を baseline 順位で確定
- **Node ごと 1 timestep 最大 1 取引**
- **`G - R` 最大候補の採用**；同値なら当事者数が多い候補を優先
- **Case I、II、III を最終 TVT ルール名として使わない**
- 同一 timestep で全 Node が**共通全World baseline**を参照
- 意思決定窓への**初回進入時のみ** TVT 検討（同一 Vehicle の再検討なし）

**疑似コード・数式に関する追記分（§9〜§15 補足）**：

- Python のリスト添字は 0 始まりだが、`baseline_rank` は 1 始まりの順位値を持つ辞書である
- 4 方式は買い手集合生成方法が異なり、非参加 Vehicle なしでは生成後の共通順位計算を共有する
- `trade_rank` を取引後順位の正本とし、`trade_order` は派生順位列とする
- `sellers_sorted` は `trade_scope` 内の非買い手 Vehicle を baseline 相対順で保持する
- 同一 inlink FIFO は `preserves_inlink_fifo()` の方法で検査する
- 非参加 Vehicle あり単一買い手には固定順位枠方式を使用する
- 経済的成立条件は `G >= R`
- 各買い手について `G_b > 0` を必要条件とする
- 買い手別支払額は `P_b = R * G_b / G`
- 支払いと補償は予測値で事前確定し、事後精算しない
- 内部計算では丸めず、表示時だけ丸める
- `G >= R` の初期判定には完全比較方式を採用する

---

## 20. 保留事項

### 20.1 非参加Vehicleあり単一買い手

- 固定順位枠方式を使用する方針自体は**確定**（§12.3、§12.6）
- 確認済みの処理手順は §12.6 へ記録済み
- **実装にそのまま使える完全な固定順位枠疑似コードは未確定**

### 20.2 非参加Vehicleあり複数買い手一般形

- 固定順位枠を使用する方向
- **完全な候補生成規則は未確定**
- **完全な順位構築疑似コードは未確定**
- どの買い手集合を生成するか
- 各 inlink の prefix と非参加固定順位をどう両立させるか
- 有効候補を取りこぼさないか
- 候補数をどう抑えるか（非参加 Vehicle ありの**候補数抑制**）
- FIFO 違反候補をどこまで事前除外するか

### 20.3 FIFO事前除外

- 初期実装では最終 FIFO 検査（`preserves_inlink_fifo()`）を使う
- FIFO 棄却数、棄却率、棄却理由を測定する
- 棄却率が高い場合のみ、固定順位枠候補に対する明らかな FIFO 違反の事前除外を検討する
- 事前除外追加前後で有効候補集合の一致を確認する

### 20.4 G >= Rの代替比較方式

- **完全比較方式は当面の採用方式であり、保留事項ではない**（§15.5）
- Tolerance 方式と Decimal 方式は、数値表現誤差による問題が確認された場合の**代替案**
- これらを撤回済み事項（§21）へ入れない

### 20.5 RNG

- `surplus` が同値で当事者数も同じ場合のランダム選択について、**具体的 RNG 設計**は引き続き保留（再現可能 seed、実 World RNG と TVT 専用 RNG の選択、Node 別 RNG、候補列挙順から独立した選択、仮想計算が実 World RNG を消費しないこと）

### 20.6 その他の保留事項

- **全World baseline の実行性能**
- global および local horizon の**正式な基本値**
- horizon 30、50、100 の**比較**
- 毎 timestep 実行と 2 または 3 timestep 間隔の**比較**
- 経済的に非合理な簡易 Case I を研究上の比較対象として**別途実装するか**
- UXsim 内の**現在 timestep 到着記録時点**と制度上の既到着判定の対応
- 候補順位範囲上限 15、20 への**感度分析**

**保留事項に含めないもの**（確定済み）：

- 単一買い手・複数買い手モードの切替方法
- TVT 成立時の確定範囲
- 確定ブロック後の順位オフセット
- 確定ブロック境界の FIFO
- `G >= R` の初期判定方式（完全比較方式）

---

## 21. 撤回済みまたは採用しない案

以下は過去議論にあったが、**現在の確定事項として採用しない**：

- FCFS 順位を Node までの**残距離順**で決める案
- 権利保有車両を baseline で**最初に通過する Vehicle**とする案
- 全World baseline 仮想計算を**6 timestep だけ**実行する案
- TVT候補 Vehicle を**買い手候補だけ**とみなす案
- **非参加 Vehicle より前の Vehicle だけ**で取引を構成する案
- 買い手群を**単一 inlink だけ**に限定する案
- 複数 inlink 買い手間の順序を**新たに探索**する案
- BATCH の同着規則を TVT へ**自動流用**する案
- **Case I、II、III**を最終的な TVT ルールとしてそのまま使用する案
- **単一買い手モードと複数買い手モード**を研究設定として切り替える案
- 確定ブロックとの接続を**特別な未解決問題**とする説明
- 確定ブロック接続部だけを**特別に FIFO 検査**する案

---

## 22. 次に行う作業

1. **全World baseline 仮想計算の性能測定**（§18 の計画に基づく。測定コードは別作業で作成）
2. horizon 30、50、100 の比較と未解決率の評価
3. 非参加 Vehicle なし共通 `trade_rank` の**独立診断コード**による自動検証
4. UXsim 処理順と制度上の既到着判定の対応確認
5. TVT 実装の着手（上記測定・検証結果を踏まえて）

**今回の作業範囲外**：性能測定コードの作成、TVT 本体の Python 実装、既存テストの変更。
