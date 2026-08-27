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

## 文書保守方針

**採用日：2026-08-25**

本節は、本メモおよび関連研究メモ（特に `ORDER_EXCHANGE_PROGRESS.md`）の**編集・更新**について、2026-08-25 に**作業の途中から正式に採用**した方針である。研究メモ作成の最初から一貫して適用されていたものではない。採用前の既存編集には、古い記述の直接更新や削除が含まれている可能性がある。**採用前の編集を推測で復元しない。** 現存する記述について、**今後の編集から**本節を適用する。過去版の復元が必要な場合は、Git 履歴、保存スナップショット、既存の進捗記録等を根拠として**個別に**判断する。採用前の状態が不明な場合、推測で歴史的記録を作らない。

本研究では、実装方式、実験条件、性能値が時点によって変化する。同じ名称の機能でも、Analyzer 生成あり・なし、full TMAX・short TMAX、正式反映前・後などで結果の意味が異なる。最終状態だけを残すと、設計変更の理由、性能改善の原因、過去の診断結果の適用範囲を確認しにくい。Git 履歴だけでは、将来の利用者や AI が適切な過去版を必ず参照できるとは限らない。本文中に当時の記録と更新注記を残すことで、設計判断の根拠と変遷を同時に確認できる。一方で、古い記述を無注記で残すと現行仕様と誤認されるため、現在状態と最新参照先を併記する必要がある。

### 原則として保存する記述

次は、現在状態と異なる場合でも、研究・設計・実装の経緯を示す**歴史的記録**として原則保存する。

- 当時の設計方針
- 当時の実装状態
- 当時の未解決事項
- 当時の次作業候補
- 実験条件
- 診断条件
- 測定結果
- 性能値
- 不具合の再現記録
- 修正経緯
- 採用または不採用の判断理由
- 過去の正本や旧方式を前提とする比較方法
- 当時の研究上の判断を理解するために必要な記述

現在状態と異なるという理由だけで、これらを削除しない。

### 現在状態と異なる場合の整理方法

古い記述と現在状態が異なる場合は、原則として次の順で整理する。

```text
古い記述を残す
↓
当時の記録であることを明示する
↓
更新日と現在状態を追記する
↓
最新情報の参照先を示す
```

必要に応じて、次の形式を使用できる。

```markdown
> **更新注記（YYYY-MM-DD）：**
> 以下は当時の設計・調査・実装時点の記録である。
> 現在の状態は更新済みであり、最新情報は該当する最新節を参照する。
```

既存文書の語調に合う場合は、古い予定へ取り消し線を付け、その直後に完了日と最新参照先を追加してもよい。ただし、取り消し線だけで終わらせず、現在状態と最新参照先が分かるようにする。

### 直接修正してよい記述

次は、歴史的意味を変えない範囲で直接修正できる。

- 誤字脱字
- 明白な文法上の誤り
- Markdown の崩れ
- 明白なファイル名・関数名・属性名の転記ミス
- 数字の明白な転記ミス
- 不可視文字
- 内容を変えない表記統一
- 意図せず発生した同一内容の完全重複
- リンクまたは参照先の明白な誤り

数値や名称が当時の実装状態を示している可能性がある場合は、単なる誤記と断定せず、周辺文脈を確認する。

### 判断が難しい場合

記述を残す必要があるか、単純に修正または削除してよいか判断できない場合は、**保守的に判断して残す**。そのうえで、必要に応じて次を追記する。

- 当時の記録である可能性
- 現在状態
- 最新参照先
- 判断が確定していないこと

将来の AI や作業者が、古いという理由だけで削除しないようにする。

### 削除を検討できる場合

削除を検討できるのは、少なくとも次をすべて満たす場合に限定する。

- 歴史的・研究的意味がないことを確認できる
- 当時の判断や実装状態を失わない
- 単なる編集事故、完全重複、壊れた断片等である
- 削除によって実験条件や設計経緯の解釈が変わらない

判断に迷う場合は削除しない。

### 今後の適用

本節は、今後の人間の作業者および AI による編集にも適用する。冒頭付近の本節と、各節に付された更新注記（例：2026-08-24 の §23 関連注記）を併せて参照すること。

---

## 1. メモの目的と現在の状態

### 1.1 目的

本メモは、Order Exchange 研究における TVT の制度設計・技術設計を正式に記録する。BATCH Phase 4-6Y 完了後、次の本体対象として TVT の設計整理を開始した。

### 1.2 現在の状態

| 区分 | 状態 |
|------|------|
| TVT制御ロジック | **未実装** |
| FCFS | 実装済み |
| BATCH（Level 2含む） | 実装済み・主要診断済み。**Level 2 mimic World の TMAX は 2026-08-24 に short TMAX 方式へ正式変更済み**（§23） |
| 全World baseline仮想計算 | **制度ロジック未実装**（設計のみ）。**性能調査・基盤安全性確認は 2026-08-24 に実施済み**（§23） |
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

> **更新注記（2026-08-24）：** 本章は TVT **制度ロジック**（baseline 到着・通過記録を含む）の設計記録であり、**未実装**のままである。TVT 向け全World baseline の**性能調査**、BATCH Level 2 short TMAX の検証・正式反映は **§23** で実施済み。

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

> **更新注記（2026-08-24）：** 上記は策定時点の設計上の未確定事項である。BATCH Level 2 の virtual horizon 30・199・200 での A/B 正しさは §23.7 で確認済み。全World baseline の horizon 正式値・未解決率は **未確定**（§23.18）。

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

> **2026-08-26更新：** TVT候補Vehicleは、時間条件に加え、全World baseline開始時点ですでに対象inlink上にいるVehicleへ限定する。詳細は **§24** を参照。

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

> **更新注記（2026-08-24）：** 頻度・horizon の正式値は**未確定**のまま。5,000 台条件での性能基盤確認（`World.copy()` + forward）は §23 で実施済み。baseline 到着・通過記録の取得は未実装（§23.18）。

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

> **更新注記（2026-08-24）：** 上表の mimic World 構築は BATCH Level 2 局所推定向けである。正式実装 `order_control_batch_level_2_reference.py` は **short TMAX 方式**へ変更済み（§23.8）。`Analyzer` を生成しない mimic World は Phase 4-6Y で確認済み。旧 **full TMAX** 方式の説明・比較は §23.6、§23.9。全World baseline 経路の現在ボトルネックは `World.copy()`（§23.13）。

---

## 18. 性能測定の必要性

> **更新注記（2026-08-24）：** 以下 §18.2〜§18.4 は**策定時点の測定計画**である。計画に基づく測定・short TMAX 反映・再測定は実施済み。最新結果は **§23** を参照。

### 18.1 方針

現段階では**性能測定コードを作成しない**。本節は測定**計画**のみを記載する。

**2026-08-24 追記：** 計画に基づく初期測定、Vehicle ログ A/B、cProfile、Level 2 short TMAX の A/B 正しさ検証、正式実装への反映、および正式 short TMAX 実装での再測定を実施した。詳細は **§23** を参照する。

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

> **更新注記（2026-08-24）：** 上記は branching 調査時点の参考値である。TVT 向け全World baseline の体系測定（full TMAX 時代・short TMAX 正式反映後）は **§23.3、§23.12** を参照。

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

- **全World baseline の実行性能**（2026-08-24：5,000 台条件で初期測定・short TMAX 反映・再測定済み。§23。10,000 台実測は未実施）
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

1. ~~**全World baseline 仮想計算の性能測定**（§18 の計画に基づく。測定コードは別作業で作成）~~ **2026-08-24 実施済み**（§23）
2. **TVT 向け全World baseline で必要な情報の設計**（baseline 予想到着・通過記録は未実装）
3. **全 Node 共有の baseline 管理の設計**
4. **性能カウンターの設計・導入**（§23.17 参照）
5. **TVT 制度ロジックの段階的実装**
6. horizon 30、50、100 の比較と未解決率の評価（TVT 実装後）
7. 非参加 Vehicle なし共通 `trade_rank` の**独立診断コード**による自動検証
8. UXsim 処理順と制度上の既到着判定の対応確認
9. 5,000 台で baseline 要求回数・実行回数・総時間を測定（TVT 実装後）
10. 10,000 台で実測（TVT 実装後）
11. 3 時間目標を超える場合に `World.copy()` 軽量化を検討（§23.14 参照。未着手）

**今回の作業範囲外（2026-08-24 時点）：** TVT 本体の Python 実装、baseline 到着・通過記録、既存テストの変更。

> **2026-08-26更新：** snapshot固定集合と二段階観測設計の整理は完了した。次は到着・通過collectorの具体設計である。詳細は **§24** を参照。

---

## 23. 全World baseline仮想計算の性能検証とLevel 2 short TMAX

記録日：2026-08-24

対象：TVT向け全World baseline仮想計算

関連機能：BATCH Level 2 `t_trigger` 推定

現在の状態：

- short TMAX を正式実装へ反映済み
- `World.copy()` 軽量化は未着手
- TVT 制度ロジックは未実装
- baseline 予想到着・予想通過記録は未実装

### 23.1 全World baselineを検討する目的

- TVT で全World baseline 仮想計算を利用する可能性がある。
- 将来、baseline 仮想計算から Vehicle の予想到着 timestep、予想通過可能 timestep、予想到着順位、予想通過順位等を取得する構想がある。
- 全World baseline の結果は全対象 Node 間で共有することを必須とする。
- Node ごとに別々の全World 仮想計算を実行する設計は採用しない。
- 将来 BATCH でも、バッチ形成のきっかけとなる到着 Vehicle が対象 Node を通過するまでに到着可能な Vehicle を抽出し、BATCH 候補選定の精度向上へ使用する可能性がある。
- 今回の作業は TVT 制度ロジック実装前の基盤性能・安全性確認である。

### 23.2 初期の全World baseline方式

```text
実World
↓
World.copy()
↓
複製Worldを通常のexec_simulation()で指定horizonだけ前進
↓
実Worldは変更しない
```

- Analyzer 付きの通常 `exec_simulation()` 経路を使用した。
- 通常の Vehicle 走行、route、signal、capacity、clearance、FCFS、BATCH 形成、BATCH service queue、Level 2 および fallback を維持した。
- 表示、保存、progress 表示のみを抑制した。
- 各試行は同じ `real_W` から独立した `World.copy()` で開始した。
- 実World、`W.rng`、`W.order_control_rng` の不変性を確認した。
- fork と実World の参照独立性を確認した。

診断スクリプト：`diagnostics/order_control/tvt_global_baseline_performance.py`

### 23.3 初期性能測定（full TMAX 正本時代）

条件：

```text
Vehicle数：5,000台
ネットワーク：6×6 grid
branch timestep：T=50
各horizon：3回
```

| horizon | World.copy()中央値 | forward中央値 | 合計中央値 |
|---:|---:|---:|---:|
| 6 timestep | 約1.539秒 | 約0.802秒 | 約2.346秒 |
| 30 timestep | 約1.522秒 | 約3.776秒 | 約5.302秒 |
| 50 timestep | 約1.521秒 | 約5.862秒 | 約7.388秒 |

確認結果（全 9 試行）：

- 実World 不変
- `W.rng` 不変
- `W.order_control_rng` 不変
- 参照独立性成立
- fork は指定 horizon 分だけ正常前進
- 初期方式は技術的には利用可能だったが、性能負荷が大きかった

### 23.4 Vehicleログ停止A/B診断

診断スクリプト：`diagnostics/order_control/tvt_global_baseline_logging_ab.py`

B 条件：

```python
fork_W.vehicle_logging_timestep_interval = -1
```

（`World.copy()` 完了後、forward 開始前に fork のみへ適用）

| horizon | forward短縮率 | total短縮率 |
|---:|---:|---:|
| 6 | 約1.80% | 約1.21% |
| 30 | 約0.71% | 約0.60% |
| 50 | 約0.95% | 約0.64% |

- A/B 交通状態は完全一致した。
- fork 側 `W.rng` の終了状態は一致した。
- fork 側 `W.order_control_rng` の終了状態は一致した。
- Vehicle ログは主要ボトルネックではなかった。
- `World.copy()` 後にログを停止しても、すでにコピーされた過去ログ等には作用しないため、copy 時間の直接的な軽量化にはならない。

### 23.5 cProfileによるボトルネック特定

診断スクリプト：`diagnostics/order_control/tvt_global_baseline_profile.py`

50 timestep forward の cProfile 結果（参考。プロファイル実行中の絶対秒数は通常性能値として使用しない）：

```text
exec_simulation()                            約6.119秒
Node.transfer()                              約5.873秒
Node.transfer_batch()                        約5.870秒
form_order_control_batch()                   約5.833秒
Level 2 t_trigger推定                        約5.785秒
_build_mimic_world()                         約5.572秒
finalize_scenario()                          約5.360秒
Link.init_after_tmax_fix()                   約5.352秒
```

```text
Level 2呼出回数：428回
_run_limited_virtual_loop()累積：約0.065秒
```

結論：

- Level 2 の局所仮想進行自体は主要コストではなかった。
- 毎回の mimic World 構築が主要コストだった。
- mimic World が実World の `TMAX=30000` を引き継いでいた。
- 各 mimic Link について、局所 Level 2 計算には過大な長さの `traveltime_actual` および Euler 集計配列が毎回生成されていた。
- Analyzer、通常の Vehicle 走行、car-following、Vehicle ログは、この条件では主要ボトルネックではなかった。

`World.copy()` について：

- `World.copy()` は dill による World 全体の直列化と復元である。
- プロファイル上は `dill.dumps()` 側が支配的だった。
- cProfile には大きなオーバーヘッドがあるため、プロファイル実行中の絶対秒数は通常性能値として使用しない。
- 通常実行での copy 中央値は約 1.5 秒である。

### 23.6 full TMAX方式とshort TMAX方式

変更前（full TMAX 方式）：

```python
tmax=max(
    real_W.TMAX,
    (real_W.T + 200) * real_W.DELTAT,
)
```

変更後（short TMAX 方式、2026-08-24 正式反映）：

```python
tmax=(real_W.T + 200) * real_W.DELTAT,
```

理由：

- Level 2 は局所 mimic World を短い virtual horizon だけ進行する。
- 実World 全期間の TMAX を局所 mimic World へ引き継ぐ必要性は確認されなかった。
- 実World の大きな TMAX に由来する過大な配列生成が主要コストだった。
- `finalize_scenario(create_analyzer=False)` や Level 2 の交通ロジックは変更していない。
- 正式変更は TMAX 選択式の 1 行だけである。

制約：

- 現在の式は、既存余裕値 200 を維持している。
- virtual horizon 30、199、200 を中心に検証した。
- virtual horizon が 200 を超える場合の一般化は未検証である。
- 将来 200 を超える場合は、境界式を別途設計・検証する必要がある。

### 23.7 short TMAXのA/B正しさ検証

診断スクリプト：`diagnostics/order_control/level2_mimic_tmax_ab.py`

grid5000 の A/B 条件：

```text
snapshot timestep：50、300、550
virtual horizon：30、199、200
合計：9組
```

全 9 組が passed。

比較項目（少なくとも次を含む）：

- Level 2 呼出し入力列
- `resolved`
- `reason`
- `t_virtual_trigger`
- `t_level_2_candidate`
- `t_level_1`
- `snapshot_timestep`
- `simulated_timestep_count`
- Vehicle transfer timestep 記録
- virtual Node arrival timestep 記録
- virtual outlink choice
- service stop trace
- sink end-trip trace
- adopted `t_trigger`
- 50 timestep 後の交通状態
- fork 側 `W.rng`
- fork 側 `W.order_control_rng`
- `real_W` 不変性

horizon 終端境界検証：

```text
virtual horizon 199：simulated_timestep_count=199
virtual horizon 200：simulated_timestep_count=200
```

両方について次が成立：

- `resolved=False`
- `reason="virtual_horizon_exceeded"`
- A/B 結果完全一致
- 実World および両 RNG 不変

large real TMAX 境界ケース：

```text
real_W.TMAX：30000
snapshot timestep：10
virtual horizon：200
clearance：201

full TMAX方式のmimic TMAX期待値：30000
short TMAX方式のmimic TMAX実測値：210
short TMAX方式のmimic TSIZE実測値：210
仮想ループ最終timestep：210
simulated_timestep_count：200
```

結果：

- `virtual_horizon_exceeded`
- A/B 完全一致
- 実World 不変
- 両 RNG 不変
- `IndexError` なし
- `traveltime_actual` 範囲不足なし
- `cum_arrival` および `cum_departure` 範囲不足なし
- off-by-one 問題なし

### 23.8 正式実装への反映

> **重要：BATCH Level 2 の正式実装は、2026-08-24 時点で short TMAX 方式へ変更済み。**

変更した正式実装ファイル：

```text
uxsim/order_control_batch_level_2_reference.py
```

変更した関数：

```text
_build_mimic_world()
```

変更差分：

```diff
- tmax=max(real_W.TMAX, (real_W.T + 200) * real_W.DELTAT),
+ tmax=(real_W.T + 200) * real_W.DELTAT,
```

- 公開関数シグネチャは変更していない。
- 戻り値形式は変更していない。
- `timing_collector` 等の診断専用処理は正式実装へ追加していない。
- `uxsim.py` の import 先は変更していない。
- 通常の UXsim 処理は従来どおり `uxsim/order_control_batch_level_2_reference.py` を import する。

### 23.9 旧full TMAX正本の保存

保存先：

```text
diagnostics/order_control/order_control_batch_level_2_full_tmax_reference_snapshot.py
```

保存時点の情報：

```text
ファイルサイズ：52085 bytes
SHA-256：1e624467771b5610c95ea977bb1c6fde6752f4f88d48bba67166d2d530135784
```

- 保存時点で変更前正本とバイト単位で完全一致していた。
- 通常の UXsim 処理から import しない。
- 旧 full TMAX 方式との比較、復元、差分確認に使用する。
- `uxsim` パッケージ内へ `_original.py` として並置しなかった。
- 正式実装の二重管理と誤 import を避けるため、`diagnostics` 配下へ保存した。

### 23.10 今後のfull TMAX A/B比較に関する重要注意

> **注意：現在の正本 `uxsim/order_control_batch_level_2_reference.py` は、すでに short TMAX 方式へ変更済みである。**

したがって、今後 `level2_mimic_tmax_ab.py` 等で旧 full TMAX 方式と比較する場合、**A 条件を現在の正本へ向けてはいけない**。

今後の比較構成：

```text
A条件、旧full TMAX：
diagnostics/order_control/order_control_batch_level_2_full_tmax_reference_snapshot.py

B条件、正式short TMAX：
uxsim/order_control_batch_level_2_reference.py
```

計測用フックが必要な場合に限り、次の診断専用モデルを使用できる：

```text
diagnostics/order_control/order_control_batch_level_2_short_tmax_reference.py
```

- 現在の `level2_mimic_tmax_ab.py` には、正本変更前の A/B 構成を前提とする部分がある。
- 将来再利用する前に、A 条件の import 先と差替え対象を確認・修正する必要がある。
- 既存診断をそのまま実行すると、意図せず short TMAX 同士を比較する可能性がある。

### 23.11 正式実装でのテスト結果

```text
Level 2関連テスト：71 passed in 16.13s
BATCH統合、service queue、current visit、RNG関連：81 passed in 16.81s
確認済み合計：152 passed
```

全 pytest について：

- `python -m pytest -q` による全テスト実行も試みた。
- 全テストは完走していない。
- デモスクリプトが GUI、描画、表示その他の待機と思われる状態となった。
- 確認された子プロセスは次である：
  - `demos_and_examples/example_10en_signal_4legged_intersection.py`
  - `demos_and_examples/example_05en_gridlock_and_prevention.py`
  - `demos_and_examples/example_02en_bottleneck.py`
- 子プロセスは確認時に CPU 0.0% の sleep 状態だった。
- 子プロセスを個別に終了したが、別のデモが順次起動したため、全 pytest 実行方法自体が今回の確認には不適切と判断した。
- pytest 本体と `caffeinate` を手動終了した。
- `F` 表示が確認されたため、少なくとも一部デモ関連テストは失敗扱いとなった。
- **全テスト成功とは記録しない。**
- GUI・表示待ちとなるデモを除外したテスト範囲は、必要に応じて後から調査する。

`ps` に表示された約 5 時間等の経過時間は、Mac のスリープ時間、一時停止時間等を含み得るため、実 CPU 計算時間として扱わない。

### 23.12 正式short TMAX実装での全World性能

診断スクリプト：`diagnostics/order_control/tvt_global_baseline_performance.py`（正式実装を通常経路で使用）

条件：

```text
Vehicle数：5,000台
ネットワーク：6×6 grid
branch timestep：T=50
各horizon：3回
```

| horizon | copy中央値 | forward中央値 | 合計中央値 |
|---:|---:|---:|---:|
| 6 | 約1.518秒 | 約0.051秒 | 約1.570秒 |
| 30 | 約1.501秒 | 約0.252秒 | 約1.756秒 |
| 50 | 約1.515秒 | 約0.424秒 | 約1.936秒 |

確認結果（全 9 試行）：

- 実World 不変
- 両 RNG 不変
- 参照独立性成立
- 指定 horizon だけ正常前進
- 例外なし

旧 full TMAX 方式（§23.3）との概算比較：

```text
6 timestep forward：約15.7倍高速
30 timestep forward：約15.0倍高速
50 timestep forward：約13.8倍高速
50 timestepのcopy込み合計：約3.8倍高速
```

（forward 中央値の比。copy 時間はほぼ変化なし）

正式実装反映前の short TMAX 性能測定（診断中のみ差替え）は `tvt_global_baseline_short_tmax_performance.py` で実施したが、正本反映後は `tvt_global_baseline_performance.py` で同等の正式経路測定が可能である。

### 23.13 現在の主要ボトルネック

50 timestep の正式 short TMAX 方式：

```text
World.copy()：約1.515秒
forward：約0.424秒
合計：約1.936秒
```

- copy が合計時間の約 78% を占める。
- short TMAX 反映後は `World.copy()` が主要ボトルネックである。
- Vehicle ログ停止だけでは copy 時間は短くならない。
- copy 後に Analyzer やログを削除しても、すでに直列化済みなので copy 時間は改善しない。
- 本格的な copy 軽量化には、コピー前またはコピー処理中の対象変更が必要である。
- 現時点では copy 軽量化を後回しにし、TVT 実装を優先する。

### 23.14 World.copy()軽量化の将来候補（未着手）

#### 不要状態をコピー対象から除外する専用コピー

対象候補：Analyzer、Vehicle の過去ログ、Link の事後分析用配列、可視化用状態、保存用状態

課題：カスタム直列化が必要となる可能性がある。コピー対象漏れによって交通結果が変わる危険がある。copy 後ではなく、copy 前または copy 処理中に除外する必要がある。

#### 現在状態だけを新Worldへ移植する方式

Network、Vehicle、Node、Link の現在状態を新 World へ明示的に再構築する。全World 版 mimic 構築に近い。必要な状態項目が多く、実装難易度が高い。

#### 不変構造を共有し、可変状態だけ複製する方式

Copy-on-write に近い考え方。性能改善の可能性は高い。仮想側から実World を汚染する危険が最も高い。設計難易度も最も高い。

#### 実Worldの不要ログを最初から蓄積しない方式

コピー元 World そのものを小さくする。通常の分析・可視化への影響確認が必要。Vehicle ログ停止 A/B では forward 改善は約 1% だった。copy 時間への効果は別途測定が必要。

方針：

- short TMAX 正式実装を新しい安定基準とする。
- copy 軽量化は、short TMAX 正式実装を基礎として別の実験用コピーまたは診断経路で行う。
- 困難な copy 軽量化が不成立でも、short TMAX の成果を失わない構成にする。

### 23.15 baseline更新頻度と全Node共有

- 全World baseline 結果は全対象 Node 間で共有する。
- Node ごとに別々の全World 仮想計算を行わない。
- baseline の計算間隔は、可能な限り長くしたくない。
- ただし、ネットワーク内の対象 Node のいずれかで意思決定関連状態が変化すれば、再計算が必要となる可能性がある。
- 36 Node の混雑ネットワークでは、Vehicle 到着、BATCH 形成、service queue 変化、TVT 候補変化等がネットワーク内のどこかで頻繁に発生する可能性がある。
- **したがって、イベント駆動の再計算回避によって大幅に実行回数を削減できるとは現時点で断定しない。**
- TVT 対象 Vehicle が存在しない場合等の省略候補はあるが、実際の削減率は実測が必要である。
- 全 Node 共有の主目的は、同一 timestep・同一 baseline を Node ごとに重複計算しないことである。

### 23.16 10,000台・3時間以内に関する見通し（未測定の概算）

5,000 台での正式 short TMAX 方式：

```text
50 timestep全World baseline：約1.94秒／回
```

10,000 台で単純比例を仮定した参考範囲（**未測定の概算**）：

```text
約3秒から5秒／回の可能性
```

3 時間は 10,800 秒。

上限概算（**以下を含まない**）：

```text
1回3秒なら約3,600回
1回4秒なら約2,700回
1回5秒なら約2,160回
```

含まれないもの：通常の実World シミュレーション時間、TVT 制度計算、baseline 情報記録、分析・出力、その他の制御処理。

- TMAX=30000 の全期間で毎 timestep 計算する場合、3 時間以内は難しい可能性が高い。
- 実際の baseline 実行回数が 2,000 回程度であれば、3 時間以内が視野に入る可能性はある。
- ただし、対象 Node のいずれかで状態変化が頻繁に起こる場合、実行回数を 2,000 回程度へ抑えられる保証はない。
- 最終判断には 10,000 台条件での実測が必要である。

### 23.17 TVT実装時の性能カウンター（必須方針）

少なくとも次を記録する方針とする：

- 全World baseline 要求総数
- 実際の全World baseline 実行総数
- baseline を実行した実 timestep 数
- 同一 timestep 内の重複要求数
- 全 Node 共有により省略した重複計算数
- horizon 別実行回数
- `World.copy()` 累積時間
- forward 累積時間
- baseline 計算全体の累積時間
- 1 回当たり時間の中央値、最小値、最大値
- baseline 到着・通過記録処理時間
- 10,000 台条件での総実行時間

計測自体が本番処理へ過大な負荷を与えないよう、軽量カウンターを使用する。

### 23.18 未実装・未確定事項

- TVT 制度ロジック
- 全World baseline 専用モード
- baseline 予想到着 timestep
- baseline 予想到着順位
- baseline 予想通過可能 timestep
- baseline 予想通過順位
- 意思決定窓
- 確定順位ブロック
- TVT 候補 Vehicle
- 未解決率測定
- baseline 結果の保持形式
- baseline 再計算条件
- horizon の最終値
- 10,000 台実測
- `World.copy()` 軽量化
- virtual horizon 200 超の一般化

### 23.19 今後の推奨順序

1. 今回の調査結果と正式変更を既存 Markdown へ保存する。
2. short TMAX 正式実装を現在の安定基準とする。
3. TVT 向け全World baseline で必要な情報を設計する。
4. 全 Node 共有の baseline 管理を設計する。
5. 性能カウンターを設ける。
6. TVT 制度ロジックを段階的に実装する。
7. 5,000 台で baseline 要求回数、実行回数、総時間を測定する。
8. 10,000 台で実測する。
9. 3 時間目標を超える場合に `World.copy()` 軽量化へ進む。
10. copy 軽量化は short TMAX 正式実装を基礎とする別の実験用コピーまたは診断経路で行う。

---

## 24. 全World baselineのsnapshot固定集合と二段階観測設計

記録日：2026-08-26

対象：TVT向け全World baseline仮想計算

状態：設計更新。TVT制度ロジックおよびcollectorは未実装。

### 24.1 この更新の位置づけ

- 今回は、全World baselineの交通予測対象、TVT候補Vehicleの追加条件、snapshot固定集合、二段階の観測方法、早期終了の論理を整理した設計更新である。
- 既存コード調査とTerminalでの実コード確認に基づく。
- 保存構造、属性名、collectorの具体的実装方式は未確定である。
- 今回の設計更新によるPythonコード変更はまだ行っていない。

### 24.2 今回の設計検討直前のGit状態

今回の設計検討を開始する直前の保存済みGit状態は次のとおりである。

```
直前の保存済みコミット：
3690a8c

コミット名：
Optimize Level 2 TMAX, partially validate global World baseline, and document findings and revised maintenance policy

ブランチ：
feature/intersection-order-control

GitHubへのpush：
完了済み

push時の更新範囲：
96861f9..3690a8c
```

- コミット `3690a8c` には、Level 2 short TMAXの正式反映、全World baselineの部分的検証、関連診断、技術記録、および文書保守方針が保存されている。
- 2026-08-26の今回の設計更新は、コミット `3690a8c` を出発点として行った未実装の設計整理である。
- 今回編集する2026-08-26の設計更新自体は、現時点ではまだ新しいコミットへ保存されていない。
- 本節の記録時点では、2026-08-26の設計更新はまだ新しいコミットへ保存されていない。

### 24.3 TVT候補Vehicleのsnapshot時点条件

従来の時間条件（§7.2）に加え、TVT候補Vehicleの必要条件として次を採用する。

```
全World baseline開始時点において、
すでに対象Nodeへ接続する対象inlink上にいること
```

時間条件は次のとおりである。

```
candidate_expected_arrival_timestep
<=
right_holder_expected_passage_timestep - tau
```

現在の暫定値は次のとおりである。

```
tau = 1
```

したがって、TVT候補範囲に入るには、少なくとも次の両方が必要である。

```
1. baseline開始時点ですでに対象inlink上にいる
2. 権利保有車両の予想通過timestepの tau timestep前までに到着すると予測される
```

採用理由：

- baseline開始後に上流Nodeから対象inlinkへ進入したVehicleは、取引なしbaselineではそのinlinkへ入っても、TVTありの実Worldでは上流側の交通状態や経路選択の変化により、同じinlinkへ入らない可能性がある。
- そのVehicleを下流NodeのTVT候補にすると、TVTありの世界では到着しない可能性があるVehicleを前提として取引を構成する危険がある。
- baseline開始時点ですでに対象inlink上にいるVehicleへ限定すれば、そのVehicleが対象Nodeへ向かっている事実はsnapshot時点で固定される。
- baseline開始後に対象inlinkへ入ったVehicleは、今回のTVT候補範囲へ追加しない。

### 24.4 snapshot固定集合

対象Nodeごとに、baseline開始時点で対象inlink上にいるVehicleを固定集合とする。

固定集合には、TVT参加Vehicleと非参加Vehicleの両方を含める。

理由：

- 固定集合は交通予測の対象であり、TVT当事者だけの集合ではない。
- 非参加Vehicleもbaseline順位や固定順位枠に関係する。
- `participates_in_order_exchange` はTVT取引への参加・非参加だけを表す。
- `participates_in_order_exchange` はFCFSまたはBATCHへの参加・適用を表す属性ではない。
- 1台のVehicleについて、TVT参加・非参加はシミュレーション中に変化しない前提である。

固定集合内のVehicleを、説明上次の2状態に区別する。

```
A：
snapshot時点で対象Nodeへ到着済みのVehicle

B：
snapshot時点で対象inlink上にいるが、
まだ対象Nodeへ到着していないVehicle
```

重要事項：

- AとBは、処理上の状態を説明するための概念分類である。
- A用とB用に別の保存構造を作ると確定したわけではない。
- `arrival_time` の有無によって排他的に区別できる。
- AとBの和集合がsnapshot固定集合である。
- baseline開始後に対象inlinkへ入ったVehicleは固定集合へ追加しない。

### 24.5 既存current visitとvisit ID

既存コード調査で確認した事項：

- order-control対象Nodeへ向かうinlinkへ進入すると、既存 `order_control_visit_id` が増加する。
- `order_control_current_visit["visit_id"]` へ現在visitのIDが保存される。
- 同じVehicleが同じNodeを再訪した場合も、新しい `visit_id` で区別される。
- 新規のvisit IDを追加する必要はない方向である。
- snapshot時点の `visit_id`、Node、inlinkを固定し、そのvisitに関する到着・通過だけを記録する。
- 後続の対象Node訪問または再訪は、固定した `visit_id` と異なるため、今回の固定集合記録から除外できる。

対象Node条件は、既存current visit生成条件と同じ次の条件である。

```
order_control_eligible == True
かつ
order_control_type != "none"
```

対象inlinkは、当該Nodeの `Node.inlinks` に含まれるLinkである。

### 24.6 記録する交通予測

snapshot固定集合の各Vehicleについて、少なくとも次を取得する方向である。

```
Vehicle識別情報
既存visit_id
対象Node
対象inlink
到着時に選択されたroute_next_link
取引なしbaseline予想到着timestep
取引なしbaseline予想通過timestep
到着timestepを取得できたか
通過timestepを取得できたか
```

補足：

- Bの `route_next_link` はsnapshot時点では未確定であり、対象Nodeへの到着直前の `route_next_link_choice()` 後に取得する。
- `route_next_link` は、TVT局所仮想計算において固定outlinkとして利用する方向である。
- 全World baselineの取引なし予想通過timestepと、TVT候補ごとの局所仮想計算によるTVT後予想通過timestepを区別する。
- 到着順位は、既存の `arrival_time`、`arrival_tiebreaker`、Vehicle IDから必要時に構成する方向である。
- 通過順位はTVT形成の初期実装には必須とせず、予測対実績の研究分析で必要になった場合に後から追加する。
- 通過順位を追加する場合は、同一timestep内のtransfer成功順を記録する必要がある。
- service unitの想定処理順と実処理順の比較も、将来の分析候補として残す。

### 24.7 Aの扱い

snapshot時点で既到着のAについて：

- TVTの起点または新規取引候補にしない。
- 参加・非参加を問わず、既存設計に従って先に順位を確定する（§5 参照）。
- 既存の `arrival_time`、`arrival_tiebreaker`、Vehicle IDを順位付けに使える。
- 取引なし予想通過timestepは、全World baselineのforkで取得する必要がある場合がある。
- TVT候補から除外することと、baseline記録対象から除外することを混同しない。

### 24.8 baseline開始timestep Tで到着するVehicle

baseline開始時点ではBだったが、forkの最初の処理timestep `T` で到着したVehicleについて、次を確定事項とする。

意思決定窓の条件は次のとおりである。

```
0 < expected_arrival_timestep - T <= 6
```

したがって：

- 到着timestepが `T` なら残り時間は0であり、意思決定窓外である。
- 権利保有車両にはしない。
- snapshot時点で既到着だったAと同着扱いにはしない。
- 到着時刻 `T` を持つ、新たに到着したVehicleとして扱う。
- snapshot時点で既到着のVehicleが `T` より前の到着時刻を持つ場合、既到着Vehicleより後着となる。
- timestep `T` に複数台が到着した場合、その車両間は `arrival_tiebreaker`、Vehicle IDで一意に順位付けする。
- TVT起点対象外として、到着順位に従って確定順位ブロックへ追加する方向である。

### 24.9 意思決定窓観測区間

「前半」という曖昧な用語は使わず、次の名称を用いる。

```
意思決定窓観測区間
```

baseline開始timestepを `T` とした場合、制度上の意思決定窓内到着は次のとおりである。

```
T < expected_arrival_timestep <= T + 6
```

`timestep T+6` の到着も観測する必要がある。

既存 `exec_simulation(duration_t2=DELTAT)` の動作では、`T` から `T+6` までの処理には7 timestep分の実行が必要である。

例（`T = 50`）：

| 到着timestep | 区分 |
|--------------|------|
| 50 | 意思決定窓外 |
| 51 | 意思決定窓内 |
| 56 | 意思決定窓内 |
| 57 | 意思決定窓外 |

### 24.10 権利保有車両の選定

意思決定窓観測区間の終了後、Nodeごとに次を行う。

```
Bのうち、
T+1からT+6に到着したVehicleを抽出
↓
そのうち割当権利行使順位が未確定のVehicleを抽出
↓
そのうちTVT参加Vehicleを抽出
↓
baseline予想到着順位が最上位のVehicleを権利保有車両とする
```

補足：

- TVT用の「順位未確定」「割当権利行使順位」「確定順位ブロック」は現在未実装である。
- BATCHの `batch_assignment` はBATCH service unitへの所属を表すものであり、TVTの順位確定状態には使用しない。
- 非参加Vehicleはbaseline順位と候補範囲に関係し得るが、権利保有車両、買い手、売り手にはならない。

### 24.11 権利保有車両通過待ち区間

意思決定窓観測区間の後、権利保有車両が存在するNodeについて、そのVehicleの取引なし予想通過timestepを取得するまで全World baselineを継続する。

この区間中も、snapshot固定集合Bの到着timestep記録を継続する。

権利保有車両の通過timestepを `P` とした場合、TVT候補範囲は次のとおりである。

```
candidate_expected_arrival_timestep <= P - 1
```

例（`P = 70`）：

| 到着timestep | 区分 |
|--------------|------|
| 69 | 候補時間範囲内 |
| 70 | 候補時間範囲外 |

補足：

- T+6までに到着しなかったBでも、T+6後から `P-1` までに到着すればTVT候補範囲に入り得る。
- したがって、T+6後もBの到着記録は必要である。
- `P` より後の到着は今回の候補範囲には不要である。
- 権利保有車両が意思決定窓観測区間中に既に通過していた場合は、記録済みの `P` を使用する。
- `P` のtimestep処理が完了してから候補範囲を確定する。
- UXsimでは同一timestep内に通過処理が到着記録より先に行われるが、`P` と同じtimestepの到着は条件上候補外なので問題にならない。

### 24.12 Node別の概念状態

実装上のenum名や属性名は確定せず、概念上、Nodeごとに次を区別する必要がある。

```
意思決定窓観測中
TVT検討不要
権利保有車両の通過待ち
TVT用baseline情報取得完了
horizon終端時未解決
```

補足：

- 状態遷移は同一baseline内で原則一方向である。
- 一度完了したNodeを再判定する必要はない。
- 完了済みNodeの後続通知は無視できる。
- 具体的な保存構造と名称はcollector設計時に決める。

### 24.13 全World baselineの早期終了

TVTだけが共通baselineを利用する初期段階では、次を全体終了条件の方向とする。

```
全対象Nodeが、

TVT検討不要
または
TVT用baseline情報取得完了

のいずれかになった
```

補足：

- T+6の到着処理が完了する前には終了しない。
- 全NodeがT+6時点でTVT検討不要なら、その時点で終了可能である。
- 一部Nodeが権利保有車両通過待ちなら、全World仮想計算自体は継続する。
- 最後の未完了Nodeが完了したtimestepの処理終了後に停止する。
- horizonへ到達しても必要な `P` が得られないNodeは未解決として終了する。
- 早期終了は完全なtimestep境界でのみ行う。
- 既存 `exec_simulation()` を1 timestepずつ実行できることは確認済みである。
- 早期終了の実際の性能効果は未測定であり、1 timestep単位の関数呼出し負荷と比較する必要がある。

### 24.14 TVTと将来BATCHの共通利用

共通化するのは交通予測である。

```
snapshot固定集合
到着timestep
visit_id
対象Node
対象inlink
route_next_link
取引なし予想通過timestep
```

BATCHの将来候補条件は、到着済みtrigger Vehicleの予想通過timestepを `P` として、暫定的に次のとおりである。

```
other_vehicle_expected_arrival_timestep <= P - 1
```

補足：

- TVTの6 timestep意思決定窓はBATCHには直接使用しない。
- TVTとBATCHは同じ全World baseline交通予測を共有することを必須とする。
- 完了条件は制度ごとに異なり得る。
- 将来、TVTとBATCHの両方が同一baselineを利用する場合、baseline全体の終了には、有効になっている両制度の必要情報が揃う必要がある。これは論理和ではなく論理積である。
- BATCH共通利用が未実装のTVT初期段階では、BATCH側の完了を待たない。

### 24.15 保持と性能の方針

- 初期実装では、現在のbaseline実行に必要な結果だけを保持する。
- 直前baselineや全期間のbaseline結果を `real_W` へ蓄積しない。
- 次回の `World.copy()` 対象を増やさないことを重視する。
- 研究分析用の長期記録は、必要性が具体化した後に別の軽量ログとして追加する。
- 分析候補には、予想到着と実到着、予想通過と実通過、必要なら順位差、service unit想定順と実処理順の比較がある。
- これらをすべて初期実装から記録するとは確定しない。

### 24.16 未実装・未確定事項

- TVT用の割当権利行使順位
- TVT用の順位未確定状態
- 確定順位ブロック
- Aおよびtimestep T到着Vehicleの順位確定処理
- 権利保有車両選定処理
- 到着・通過collector
- Node別状態の保存構造
- 通過通知の正式な接続方法
- collector例外時の扱い
- 早期終了の性能測定
- 通過順位の研究分析用記録
- service unit想定順と実処理順の比較記録
- 将来BATCHによる共通baseline利用

**2026-08-27更新：** §24のsnapshot固定集合と二段階観測設計を受け、collectorの内部記録、索引、通知処理、読取機能、実装順序を **§25** に整理した。collector本体とUXsim接続はまだ未実装である。

---

## 25. 全World baseline collectorの実装前設計

記録日：2026-08-27

対象：TVT向け全World baselineにおける到着・通過collector

状態：実装前設計。collector本体、UXsim通知接続、テストは未実装。

### 25.1 位置づけ

- 記録日：2026-08-27
- §24のsnapshot固定集合と二段階観測設計を、実装可能な形へ具体化した。
- collector本体、UXsim通知接続、テストはまだ未実装である。
- Cursor調査だけで確定せず、Terminalによる実コード確認を経て整理した。
- 今回は実装前設計であり、実装結果ではない。

今回の設計整理の出発点として、直前の保存済みGit状態は次のとおりである。

```
直前の保存済みコミット：
86313cc

コミット名：
Document TVT baseline snapshot-fixed vehicle set, arrived and not-yet-arrived handling, and observation until right_of_entry_vehicle passage

ブランチ：
feature/intersection-order-control

GitHubへのpush：
完了済み

push時の更新範囲：
3690a8c..86313cc
```

本節の記録時点では、今回の設計更新はまだ新しいコミットへ保存されていない。

### 25.2 collectorの責任

collectorは、snapshot固定visitについて次の交通予測上の事実だけを保持する。

- snapshot時点の固定visit識別情報
- baseline予想到着timestep
- arrival_tiebreaker
- route_next_link
- baseline予想通過timestep

collectorは次を担当しない。

- 意思決定窓判定
- Aおよびtimestep T到着Vehicleの順位確定
- right_of_entry_vehicleの選定
- TVT候補Vehicleの確定
- Node別の制度状態
- 早期終了判定
- 買い手・売り手選定
- trade_rank
- 支払い・補償
- 通過順位
- BATCH service unit分析
- 長期分析ログ

### 25.3 固定visit 1件分の情報

固定visit 1件について、次を保持する方向である。

- vehicle_name
- vehicle_id
- node_name
- inlink_name
- visit_id
- snapshot時点で到着済みだったか
- baseline予想到着timestep
- arrival_tiebreaker
- route_next_link_name
- baseline予想通過timestep

補足：

- vehicle_idは、必要時に到着順位を作るために保持する。
- 到着順位は、arrival timestep、arrival tiebreaker、vehicle IDから制度側が作る。
- snapshot時点のA/B区分は、独立した不変情報として保持する。
- Bがbaseline中に到着すると、AとBの両方でarrival timestepが非Noneになるため、この区分はarrival timestepだけから復元できない。
- 到着情報、route_next_link、通過情報の未取得はNoneで表す。
- 取得有無を表す重複したboolは追加しない。
- fork内のVehicle、Node、Linkオブジェクトは保持しない。
- participates_in_order_exchangeはcollectorへ複製しない。

主キーは次である。

```
(vehicle_name, visit_id)
```

node_nameとinlink_nameは主キーへ含めず、記録項目および整合性確認に使う。

### 25.4 内部記録形式

固定visit 1件を、小さな可変のdataclassで表すことを第一候補とする。

- frozenにはしない。
- 初期実装ではslots等の最適化を入れない。
- 10項目とNoneを含む型を明示しやすい。
- B到着時の3項目更新と通過timestepの更新が読みやすい。
- 複数索引とBATCH一時保持から同じ記録を参照しやすい。
- プレーンな結果への変換をcollector内へ集約できる。

dataclass採用は実装予定であり、まだコードへ反映していない。

### 25.5 索引構造

主索引：

```
(vehicle_name, visit_id) → 固定visit記録
```

Vehicle別補助索引：

```
vehicle_name → 同じ固定visit記録
```

Node別補助索引：

```
node_name → 同じ固定visit記録の一覧
```

補足：

- 同一baselineでは、1 Vehicleにつき固定visitは最大1件である。
- 3索引は記録を複製せず、同じ記録オブジェクトを参照する。
- 索引はsnapshot登録時だけ構築する。
- 到着時と通過時には索引を変更しない。
- Vehicle別索引は、通常transferでcurrent visitを読む前の固定集合判定に使う。
- Node別索引は、T+6時点のNode別読取に使う。
- Node別一覧の登録順には、到着順位や通過順位としての意味を持たせない。

### 25.6 snapshot登録

snapshot登録時に、固定visitの記録と3索引を作る。

Aについては登録時に次を保存する。

- baseline予想到着timestepとして使うsnapshot時点の到着timestep
- arrival_tiebreaker
- route_next_link_name

Bについては登録時に次をNoneとする。

- baseline予想到着timestep
- arrival_tiebreaker
- route_next_link_name

AとBのbaseline予想通過timestepはNoneから開始する。

登録時には少なくとも次を確認する。

- 主キーが未登録
- 同一Vehicleが別の固定visitへ登録されていない
- visit_idが正の整数
- Aなら到着情報とroute_next_linkが存在する
- Bなら到着情報は未記録
- passage timestepは未記録

Vehicle、Node、inlink、current visit、A/B判定、研究シナリオ条件の整合は、snapshot固定集合を構築するドライバ側で確認する方向である。

登録時に保証した条件を、通知時に不要に重複検証しない。

### 25.7 Bの到着記録

Bの到着通知では、次を1回だけ記録する。

- baseline予想到着timestep
- arrival_tiebreaker
- route_next_link_name

補足：

- 固定集合外visitの通知は無視する。
- 主キーが一致するのにNodeが異なる通知は重大不整合とする。
- Aへの到着通知は二重到着として重大不整合とする。
- 到着済みBへの再通知も二重到着として重大不整合とする。
- route_next_linkが必要時点でNoneなら重大不整合とする。
- timestep Tの到着もcollectorには通常どおり記録する。
- 意思決定窓内外はcollectorでは判定しない。

### 25.8 通過記録

通過記録は次の2処理に分ける。

**通過前：**

- snapshot固定visitか確認する
- 通過Nodeが固定Nodeと一致するか確認する
- 到着情報が存在するか確認する
- route_next_linkが存在するか確認する
- baseline予想通過timestepが未記録か確認する
- 二重通過等があれば、Vehicleの物理的通過前に停止する

**通過後：**

- 通過前に確認済みの固定visit記録へ、現在のtimestepをbaseline予想通過timestepとして設定するだけ
- 固定集合検索、visit ID確認、二重通過確認、到着確認、route_next_link確認は繰り返さない

通過後の設定は、collector内の1件用の薄い内部処理へ統一する方向である。

### 25.9 BATCHの通過記録

BATCHでは次の順序とする方向である。

1. 通過前に固定visitと未記録を確認する
2. Vehicleの物理的通過を完了する
3. service unitからVehicleを削除する
4. service unitからvisit IDを削除する
5. transferred_vehicle_countを更新する
6. active_inlinkを更新する
7. 確認済みの固定visit記録への参照を一時listへ追加する
8. service queueを整理する
9. queue整理後、一時list内の各記録へ同じW.Tを設定する

補足：

- 一時listはBATCH関数内のローカル変数とする。
- collectorがNoneなら一時listを作らない。
- listの並び順は通過順位として保存または解釈しない。
- queue整理と通過記録を必ず同じ順序で行う小さな内部処理を設ける方向である。
- service queueが空の早期returnでは、通過記録予定が存在しないため追加処理は不要である。
- queue整理前に例外が起きたbaselineは全体を失敗扱いとし、部分的なcollector結果を利用しない。
- 例外の握りつぶしやロールバックは初期実装へ入れない。

### 25.10 通過接続対象

初期collectorで対応する通過経路は次の3つである。

- BATCH
- FCFS clearanceあり
- 通常Node.transfer

FCFS clearanceなしは、回帰確認・デバッグ用であり、研究評価の正式FCFS経路ではないため初期対応へ含めない。必要になった場合は、将来追加可能である。

### 25.11 Worldとの接続

- World内部にcollector参照をNoneで常設する方向である。
- constructorの公開引数にはしない。
- real_WではNoneのままとする。
- real_W.copy()完了後にfork側だけcollectorを設定する。
- VehicleとNodeは、所属Worldへの既存参照を通じて同じcollectorへ到達する。
- collectorはfork_Wへの逆参照を持たない。
- collector無効時はWorld属性の読取とNone判定だけを追加する。
- collector無効時には、通知情報の取得、名前の組立て、一時list生成、collector処理、追加RNG消費を行わない。

### 25.12 読取機能

初期実装の読取機能は次の2つに限定する。

1. Node名を指定し、そのNodeの固定visitをプレーンなdictのlistとして取得する
2. vehicle_nameとvisit_idを指定し、固定visit1件をプレーンなdictとして取得する

補足：

- Node別読取はT+6時点の制度判断に使う。
- 1件読取はright_of_entry_vehicleの通過待ちに使う。
- collector内部の変更可能な記録は制度側へ直接返さない。
- 新しいプレーンなdictへ変換して返す。
- 並び順は保証しない。
- A/B、到着済みB、到着順位の絞り込みとsortは制度側が行う。
- 全Node一括exportは初期実装へ含めない。
- 完了Nodeを再読しない判断は制度側が行う。

### 25.13 名称候補

次を実装時の第一候補名とする。

| 対象 | 第一候補名 |
|------|-----------|
| collector本体 | OrderControlBaselineCollector |
| 固定visit記録 | OrderControlBaselineVisitRecord |
| World内部参照 | _order_control_baseline_collector |
| snapshot登録 | register_snapshot_visit |
| B到着記録 | record_baseline_arrival |
| 通過前確認 | prepare_baseline_passage_recording |
| 通過後設定 | apply_baseline_passage_timestep |
| Node別読取 | export_node_baseline_visits |
| 1件読取 | get_baseline_visit_snapshot |
| BATCH一時list | _pending_baseline_passage_records |
| BATCH queue整理後処理 | _finalize_service_queue_and_apply_pending_baseline_passages |
| A/B区分 | was_arrived_at_snapshot |
| 予想到着timestep | baseline_arrival_timestep |
| 予想通過timestep | baseline_passage_timestep |

これらは実装時の第一候補名である。実装中に既存コードとの衝突や不明瞭さが判明した場合は見直し得る。right-holderという用語は使用しない。

### 25.14 ファイル構成

第一候補の初期ファイル構成は次である。

- `uxsim/order_control_baseline_collector.py`
  - dataclassによる固定visit記録
  - collector本体
  - プレーン結果への変換
- `uxsim/uxsim.py`
  - World内部collector参照
  - 到着通知
  - BATCH通過通知
  - FCFS clearanceあり通過通知
  - 通常transfer通過通知
- `tests_order_control_baseline_collector.py`
  - collector単体テスト
- `tests_order_control_baseline_collector_uxsim.py`
  - UXsim接続テスト

初期の手動診断は、接続テスト後に必要性を判断する。

### 25.15 実装順序

次の3回に分ける想定とする。

**第1回実装：**

- collector内部記録
- collector本体
- World内部collector参照
- collector単体テスト
- UXsim通知接続はまだ行わない

**第2回実装：**

- B到着通知
- BATCH通過接続
- FCFS clearanceあり通過接続
- 通常transfer通過接続
- UXsim接続テスト
- collector無効時の交通結果とRNG不変確認
- real_Wとforkの分離確認

**第3回実装：**

- 必要な追加テスト
- 小規模なfork実行診断
- snapshot固定集合を構築する最小補助処理または診断用ドライバ
- collector接続後の設計メモ更新

二段階観測ドライバ、TVT制度処理、Node状態、早期終了は、この3回の後の別作業とする。

### 25.16 初回実装へ含めないもの

少なくとも次を含めない。

- TVT制度ロジック
- right_of_entry_vehicle選定
- Aおよびtimestep T到着Vehicleの順位確定
- trade_rank
- 買い手・売り手選定
- 支払い・補償
- Node別制度状態
- 早期終了
- T+6とP待ちの二段階ドライバ
- 通過順位
- BATCH固有の分析情報
- 長期ログ
- 全Node一括export
- FCFS clearanceなし通知
- slots等の性能最適化
- 過去baseline結果のreal_Wへの保存

### 25.17 最小テスト

**collector単体テスト**として、少なくとも次を実装予定とする。

- A登録
- B登録
- 主キー重複
- 同一Vehicle二重登録
- B正常到着
- 固定集合外到着の無視
- Aへの到着通知を二重到着として停止
- B二重到着を停止
- 固定集合外通過を記録対象外にする
- 正常な通過前確認
- 未到着Bの通過を停止
- 二重通過を停止
- 通過後のtimestep設定
- Node別読取がプレーンコピーを返す
- 1件読取がプレーンコピーを返す
- 読取結果を変更してもcollector内部が変わらない

**UXsim接続テスト**として、少なくとも次を実装予定とする。

- collector無効時の交通結果とRNG状態が従来と一致
- B到着情報の記録
- BATCHでqueue整理後に通過timestepを記録
- FCFS clearanceありの成功処理後に通過timestepを記録
- 通常transferで固定集合外Vehicleを安全に無視
- real_Wのcollector参照がNoneのまま
- forkだけでcollectorが有効

T、T+6、P-1、Pの境界はcollector単体テストではなく、将来の制度ドライバテストで扱う。

### 25.18 未実装・未確定事項

- 実装中の名称の最終確認
- snapshot固定集合を構築する正式な補助処理
- 接続テスト用ネットワーク
- node_name不一致時の具体的な例外メッセージ
- collector接続後の小規模診断
- 二段階観測ドライバ
- TVT制度処理
- 早期終了
- 性能測定

### 25.19 次回作業開始点と第1回実装の完了条件

#### 次回作業開始点

次に行う作業は、§25.15で定義した「第1回実装」である。

第1回実装では、次だけを行う。

- `uxsim/order_control_baseline_collector.py`を新規作成する
- 可変dataclassによる`OrderControlBaselineVisitRecord`を実装する
- `OrderControlBaselineCollector`を実装する
- 主索引、Vehicle別補助索引、Node別補助索引を実装する
- snapshot固定visitの登録処理を実装する
- Bの到着記録処理を実装する
- 通過前確認処理を実装する
- 通過後のbaseline予想通過timestep設定処理を実装する
- Node別読取処理を実装する
- 固定visit1件の読取処理を実装する
- `uxsim/uxsim.py`のWorld初期化へ、内部collector参照を`None`で追加する
- `tests_order_control_baseline_collector.py`を新規作成する
- collector単体テストを実装・実行する

第1回実装では、次を行わない。

- `Vehicle.record_order_control_node_arrival()`へのcollector通知接続
- BATCHへのcollector通知接続
- FCFS clearanceありへのcollector通知接続
- 通常`Node.transfer()`へのcollector通知接続
- `tests_order_control_baseline_collector_uxsim.py`の作成
- snapshot固定集合をUXsimのforkから自動構築する正式な補助処理
- 二段階観測ドライバ
- TVT制度処理
- 早期終了
- 性能測定

#### 第1回実装の完了条件

次のすべてを満たした時点で、第1回実装を完了とする。

1. `uxsim/order_control_baseline_collector.py`が作成されている
2. 固定visit記録の10項目が実装されている
3. 主索引、Vehicle別補助索引、Node別補助索引が実装されている
4. 3索引が同じ固定visit記録を参照している
5. snapshot登録処理が実装されている
6. Bの到着記録処理が実装されている
7. 通過前確認処理が実装されている
8. 通過後のtimestep設定処理が実装されている
9. Node別読取と固定visit1件読取が、内部記録ではなくプレーンな新しいdictを返す
10. 読取結果を変更してもcollector内部記録が変化しない
11. `uxsim/uxsim.py`のWorld初期化に内部collector参照が`None`で存在する
12. UXsimの到着・通過処理には、まだcollector通知が追加されていない
13. §25.17で定めたcollector単体テストがすべて成功する
14. 既存テストへの意図しない影響がない
15. TVT制度処理、二段階観測、早期終了を実装していない
16. 実装結果をTerminalで確認している
17. 実装完了後、設計メモと進捗メモを更新する前に結果を整理している

#### 新しいチャットでの再開方法

新しいチャットでは、最初に次を確認する。

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`の§24と§25
- `ORDER_EXCHANGE_PROGRESS.md`の2026-08-27の記録
- 最新コミット
- `git status --short`
- `uxsim/uxsim.py`のWorld初期化付近
- 既存のorder-control関連テスト配置

その後、§25.19に従って第1回実装のCursor指示文を作成する。

Cursor報告だけで実装結果を確定せず、Terminalで変更内容とテスト結果を確認する。

Git操作は次の順序を守る。

- ステージング
- ステージ済み差分の確認
- コミット
- 最新コミットと残存変更の確認
- ここまでの結果に問題がないことを確認
- 別の指示で`git push`
- push結果の確認

コミットまでのコマンドと`git push`を同じコマンド列へ入れない。

### 25.20 第1回実装の結果

記録日：2026-08-27

対象：§25.15・§25.19で定義した第1回実装

状態：第1回実装は完了。UXsim通知接続は未実装。本節の記録時点では、実装結果と本節の記録はまだ新しいコミットへ保存されていない。

§25.1〜§25.19は実装前設計の記録である。本節はTerminalでコード・差分・テスト結果を確認したうえでの実装結果記録である。

#### 25.20.1 実装した範囲

今回、次を実装した。

- `uxsim/order_control_baseline_collector.py`を新規作成
- 可変dataclass `OrderControlBaselineVisitRecord`
- `OrderControlBaselineCollector`
- 主索引
- Vehicle別補助索引
- Node別補助索引
- snapshot固定visit登録
- Bのbaseline到着記録
- 通過前確認
- 通過後のbaseline予想通過timestep設定
- Node別読取
- 固定visit1件読取
- `World.__init__`の内部collector参照
- collector単体テスト

実装では、時間価値取引の根幹に関わる処理について、短さや高度なPython技法より、後から研究者が理解しやすい可読性を優先した。

#### 25.20.2 固定visit記録の10項目

- `vehicle_name`
- `vehicle_id`
- `node_name`
- `inlink_name`
- `visit_id`
- `was_arrived_at_snapshot`
- `baseline_arrival_timestep`
- `arrival_tiebreaker`
- `route_next_link_name`
- `baseline_passage_timestep`

補足：

- Vehicle、Node、Link、Worldのオブジェクト参照は保持しない
- `participates_in_order_exchange`は複製しない
- 未取得は`None`で表す
- 重複する取得済みboolは追加していない
- dataclassは可変であり、`frozen`や`slots`は使用していない

#### 25.20.3 3索引

- `_visit_records_by_primary_key` — `(vehicle_name, visit_id)`から固定visit記録を取得
- `_visit_record_by_vehicle_name` — `vehicle_name`から同一baselineで唯一の固定visit記録を取得
- `_visit_records_by_node_name` — `node_name`から固定visit記録の一覧を取得

補足：

- 3索引は同じdataclassインスタンスを参照する
- snapshot登録時だけ索引を変更する
- 到着・通過記録では索引を変更しない
- Node別一覧順には順位としての意味を持たせない

#### 25.20.4 実装した操作

| メソッド | 役割 |
|----------|------|
| `register_snapshot_visit` | snapshot固定visit登録と3索引構築 |
| `record_baseline_arrival` | Bの到着3項目を1回記録（固定集合外は無視） |
| `prepare_baseline_passage_recording` | 通過前確認（固定集合外Vehicleは`None`） |
| `apply_baseline_passage_timestep` | 通過前確認済み記録へ通過timestep設定 |
| `export_node_baseline_visits` | Node別プレーンdict list（未登録Nodeは空list） |
| `get_baseline_visit_snapshot` | 固定visit1件のプレーンdict（未登録visitは`None`） |

#### 25.20.5 到着通知の処理順序

初回実装後、Terminal確認の過程で`record_baseline_arrival`の処理順序を修正した。最終的な順序は次のとおりである。

1. 主キー検索に必要な`vehicle_name`と`visit_id`を確認
2. 主キーでsnapshot固定visitを検索
3. 固定集合外visitなら、到着payloadを検証せず無視
4. 固定visitがある場合だけNode一致を確認
5. Aへの二重到着を確認
6. Bの二重到着または部分的既存状態を確認
7. 新しい到着3項目を確認
8. 到着3項目を同じ固定visit記録へ設定

この順序にした理由は、固定集合外通知を安全に無視し、固定visitの重大な既存状態を新しい通知値のvalidationより先に検出するためである。

#### 25.20.6 通過前確認と通過後設定

- `prepare_baseline_passage_recording`は、最初にVehicle別索引で固定集合への所属を確認する
- 固定集合外Vehicleでは、`visit_id`や`node_name`を検証せず`None`を返す
- 固定集合内Vehicleでは、visit ID、Node、到着情報、route_next_link、二重通過を確認する
- `apply_baseline_passage_timestep`は、通過前確認済みの記録へtimestepを設定する薄い処理である
- 通過後処理では、固定集合検索や同じ確認を繰り返さない
- この分離は、将来BATCHで物理通過前に確認し、service queue整理後に記録するための準備である
- 今回はBATCHその他のUXsim通過処理へまだ接続していない

#### 25.20.7 World内部参照

- `World.__init__`へ`W._order_control_baseline_collector = None`を追加
- 公開constructor引数は変更していない
- `World.copy()`は変更していない
- real_Wとforkへのcollector設定処理はまだ実装していない
- UXsimの到着・通過処理への通知接続もまだ実装していない

#### 25.20.8 validation方針

- `visit_id`はboolではない正のint
- `vehicle_id`はboolではない非負int
- timestepはboolではない非負int
- `arrival_tiebreaker`はboolではないintまたはfloat
- 名前は空でないstr
- 登録時に全入力を確認してから3索引を更新するため、入力validation失敗時の部分登録を防いでいる
- 登録時に保証済みの不変条件は通知時に不要に重複確認しない
- 二重到着、二重通過、Node不一致、visit ID不一致、未到着通過などの重大不整合は検出する

#### 25.20.9 テスト結果

新規の`tests_order_control_baseline_collector.py`に33件のテストがあり、Terminalで直接実行して成功した。

| コマンド | 結果 |
|----------|------|
| `python tests_order_control_baseline_collector.py` | 成功 |
| `python tests_order_control_rng.py` | 成功 |
| `python tests_order_control_current_visit_state.py` | 成功 |
| `python tests_order_control_current_visit_arrival.py` | 成功 |
| `python tests_order_control_batch_t_trigger_level_2_body.py` | 成功（22 tests） |
| `python -m py_compile uxsim/order_control_baseline_collector.py uxsim/uxsim.py tests_order_control_baseline_collector.py` | 成功 |
| `git diff --check` | 問題なし |
| 未追跡の新規2ファイルについて`git diff --no-index --check /dev/null uxsim/order_control_baseline_collector.py` および `tests_order_control_baseline_collector.py` | 問題なし |

#### 25.20.10 Terminalで確認した実装範囲

- `uxsim/uxsim.py`の変更はコメント1行とcollector参照初期化1行の計2行追加
- `uxsim.py`内に`record_baseline_arrival`、`prepare_baseline_passage_recording`、`apply_baseline_passage_timestep`の呼出しはまだ存在しない
- したがって、到着・通過通知は未接続
- `diagnostics/order_control.zip`は未追跡のままで、今回の実装では触れていない

#### 25.20.11 第1回実装の完了判断

§25.19の完了条件1から16を、Terminal確認済みとして満たした。

完了条件17（実装完了後、設計メモと進捗メモを更新する前に結果を整理）についても、実装結果を整理したうえで本§25.20と進捗メモを更新したため、満たした。

本節の記録時点では、第1回実装および本記録はまだ新しいコミットへ保存されていない。コミット済み・push済みとは記載しない。

#### 25.20.12 今回実装していないもの

- UXsim到着通知接続
- BATCH通過通知接続
- FCFS clearanceあり通過通知接続
- 通常`Node.transfer()`通過通知接続
- FCFS clearanceなし通知
- snapshot固定集合を自動構築するdriver
- real_Wからforkを作成してcollectorを設定する処理
- 二段階観測ドライバ
- right_of_entry_vehicle選定
- TVT制度処理
- Node別制度状態
- 早期終了
- 通過順位
- 支払い・補償
- 性能測定

#### 25.20.13 次の作業

次の作業は、§25.15で定義した第2回実装である。

- B到着通知接続
- BATCH通過接続
- FCFS clearanceあり通過接続
- 通常`Node.transfer()`通過接続
- UXsim接続テスト
- collector無効時の交通結果とRNG不変確認
- real_Wとforkの分離確認

第2回実装へ直ちに着手済みではない。
