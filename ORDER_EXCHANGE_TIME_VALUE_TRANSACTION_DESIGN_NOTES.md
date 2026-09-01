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
- 意思決定窓内 Vehicle の baseline 到着順位を、参加状態とは無関係に先に作る（§6.1、§6.2）。
- §4.5 に従い、その順位列の先頭に連続する非参加 Vehicle を先に確定する。
- その後に残る未確定参加 Vehicle のうち、baseline 到着順位が最上位の Vehicle を権利保有車両とする。
- 先行確定後に未確定参加 Vehicle が残らない場合は、権利保有車両を選定せず、TVT 検討不要とする（§4.5）。
- 非参加 Vehicle は baseline 順位を持つが、権利保有車両にはならない。
- **TVT検討は、意思決定窓への初回進入時に行う。**
- 同じ Vehicle について、次の実 timestep 以降に改めて同じ起点条件で TVT を**再検討しない**。

### 4.5 権利保有車両選定前の先頭非参加Vehicleの先行確定（確定）

本節は、過去に確定済みだった処理順序の**記録漏れを補修**するものである。新しい制度ルールではない。

- §5 の既到着未確定 Vehicle の先行確定後に行う。
- 権利保有車両を選定する前に行う。
- 到着順位上の先頭 Vehicle を未確定のまま飛び越えて TVT 形成へ進まないための処理である。

#### baseline到着順位

意思決定窓内の未到着・順位未確定 Vehicle を、次の順で一意に並べる：

1. baseline予想到着 timestep
2. 固定 tiebreaker
3. Vehicle ID

参加状態は、この順位決定に使用しない。§6.1 および §6.2「参加状態中立方式」に従う。

#### 共通する同着順位原則

次の 3 群すべてで、同じ到着順位規則を使用する：

1. 既到着かつ順位未確定の Vehicle
2. 意思決定窓内の未確定到着予定 Vehicle
3. 意思決定窓外で TVT 候補となる Vehicle

参加 Vehicle と非参加 Vehicle の間で、参加状態を理由とする同着順位上の優劣を設けない。同じ baseline 予想到着 timestep の場合は、参加状態を用いず、固定 tiebreaker、Vehicle ID の順で一意に順位づける。

#### 先頭非参加Vehicleの処理

1. §5 に従って、既到着かつ順位未確定の Vehicle を先に確定する。
2. 意思決定窓内の未到着・順位未確定 Vehicle について、参加状態とは無関係に baseline 到着順位を作る。
3. その順位列を先頭から確認する。
4. 最初の未確定参加 Vehicle より前に、非参加 Vehicle が 1 台以上連続している場合、それらを baseline 到着順位のまま先に確定する。
5. 先行確定した非参加 Vehicle へ、既存の確定順位ブロック直後から連続する割当権利行使順位を与える。
6. 先行確定した非参加 Vehicle を確定順位ブロックへ追加する。
7. その後に残る未確定参加 Vehicle のうち、baseline 到着順位が最上位の Vehicle を権利保有車両とする。
8. 先行確定後に未確定参加 Vehicle が残らない場合、権利保有車両を選定せず、その Node では TVT 検討不要とする。

未確定範囲の再構成：

- 先頭に連続する非参加 Vehicle を確定順位ブロックへ追加した後、それらは現在の未確定範囲から除かれる。
- その後に残る未確定 Vehicle だけを対象として、未確定範囲内 baseline 順位を 1 位から数え直す。
- 権利保有車両、`K_last_buyer`、`K_decision_window`、`K_fixed`、`r_local` および `trade_rank` は、この更新後の未確定範囲内順位を基準とする。
- 先行確定済みの非参加 Vehicle を、`K_confirmed_before` と未確定範囲内順位の両方で重複して数えない。これは §14.2 の二重加算禁止と整合する。
- Node 全体の割当権利行使順位は、`K_confirmed_before` の後へ、この更新後の未確定範囲内順位を接続して作る。

補助例：

```text
先行確定前の意思決定窓内baseline順位：
n n p p n

先頭のn nを先行確定した後の未確定範囲：
p p n
```

更新後の未確定範囲では、残る `p p n` を未確定範囲内 baseline 順位 1 位、2 位、3 位として扱う。

補足：

- 先頭領域に非参加 Vehicle がいなければ、先行確定は 0 台である。
- 最初の未確定参加 Vehicle より後ろにいる非参加 Vehicle は、この理由だけでは先行確定しない。
- 非参加 Vehicle を参加 Vehicle より到着順位上で優遇する処理ではない。
- 参加状態とは無関係に作成済みの baseline 到着順位の先頭を飛び越えないための処理である。
- 非参加 Vehicle を TVT の買い手、売り手、権利保有車両にする処理ではない。

#### 意思決定窓内Vehicleがすべて非参加の場合

意思決定窓内の未到着・順位未確定 Vehicle がすべて非参加 Vehicle である場合：

1. 意思決定窓内 Vehicle を、参加状態とは無関係に構成した baseline 到着順位のまま先頭からすべて確定する。
2. すべての Vehicle へ連続する割当権利行使順位を与え、確定順位ブロックへ追加する。
3. 意思決定窓内に未確定参加 Vehicle が残らないため、権利保有車両は選定しない。
4. 権利保有車両が存在しないため、TVT 候補 Vehicle を特定せず、TVT 形成へ進まない。
5. この Node は、取引候補を評価した後の TVT 不成立ではなく、権利保有車両が存在しないことによる **TVT 検討不要** として扱う。
6. 順位結果としては、意思決定窓内 Vehicle が baseline 到着順位のまま確定し、意思決定窓内に未確定 Vehicle は残らない。
7. 意思決定窓外の Vehicle は、この TVT 検討不要を理由として順位を確定しない。

同着 Vehicle は、baseline 予想到着 timestep → 固定 tiebreaker → Vehicle ID の順で一意に順位づける。参加・非参加を理由に、同着順位の優劣を設けない。

#### 説明例

次の例は説明のため今回追加するものであり、新しい制度ルールではない。

```text
n n p p n p n p p
```

- `n` は非参加 Vehicle
- `p` は参加 Vehicle
- この列は参加状態とは無関係に決めた baseline 到着順位
- 同じ baseline 予想到着 timestep の Vehicle は、固定 tiebreaker、Vehicle ID で既に一意に並んでいる

処理：

1. 先頭の 2 台の `n` を baseline 順位のまま先に確定する。
2. その 2 台へ連続する割当権利行使順位を与え、確定順位ブロックへ追加する。
3. その後に残る未確定参加 Vehicle の最上位である、最初の `p` を権利保有車両とする。
4. その権利保有車両を起点として TVT 形成を検討する。
5. 後方にいる残りの `n` は、この先行確定処理だけを理由に直ちには確定しない。
6. 後方 Vehicle の確定範囲は、TVT 成立時は §14.3、不成立・未解決時は §14.4 に従う。

#### 後続処理への接続

- TVT 成立時の確定範囲は §14.3 を正本とする。
- TVT 不成立・未解決時の確定範囲は §14.4 を正本とする。
- 意思決定窓外 Vehicle の扱いは §7.5、§14.3、§14.4 を参照する。
- §14.3 と §14.4 の既存本文を本節で再定義しない。

### 4.6 UXsim処理順に関する注意（実装時確認事項）

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

§5 の既到着 Vehicle の強制確定後、§4.5 の先頭非参加 Vehicle の先行確定後、その時点で意思決定窓内に残る未確定参加 Vehicle のうち、baseline 到着順位が最上位の Vehicle（詳細は §4.5）。

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

§4.5 で先頭非参加 Vehicle を先行確定した場合、その Vehicle は未確定範囲から除外する。残る未確定 Vehicle について `baseline_rank` を 1 位から再構成する。§14.3 の `K_last_buyer`、`K_decision_window`、`K_fixed` は、この再構成後の未確定範囲内順位を使用する。

**3. `r_local`**

新規に確定する順位列における未確定範囲内順位。

**4. `K_confirmed_before`**

既存の確定順位ブロックを起点として、既到着かつ順位未確定の Vehicle がいればそれらを先行確定して追加し、§4.5 に該当する意思決定窓内の先頭非参加 Vehicle がいればそれらも先行確定して追加する。これらの先行確定をすべて終えた時点の確定順位ブロック末尾の Node 全体での割当権利行使順位を `K_confirmed_before` とする。今回新たに確定する TVT 成立、不成立または未解決時の順位列を接続する直前の位置である。

補足：

- 既到着未確定 Vehicle が存在しない場合でも、先頭非参加 Vehicle を追加したなら、その追加後の末尾を `K_confirmed_before` とする（例：既存ブロック末尾が 5 位で先頭非参加を 2 台追加した場合、`K_confirmed_before` は 7）。
- 既到着未確定 Vehicle も先頭非参加 Vehicle も存在しない場合は、それ以前から存在する確定順位ブロック末尾を `K_confirmed_before` とする。
- これらがいずれも存在せず、確定順位ブロック自体も空の場合は 0 とする。

意思決定窓内 Vehicle がすべて非参加の場合は、意思決定窓内の全非参加 Vehicle を先行確定した後の確定順位ブロック末尾が `K_confirmed_before` となる。この場合は権利保有車両が存在せず、TVT 結果として新たに接続する順位列も存在しない。したがって、`K_confirmed_before` の後へ今回の TVT による順位列を接続しない（§4.5）。

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

`K_confirmed_after` は、TVT 成立、不成立または未解決によって新たな順位列を接続した場合の値である。意思決定窓内 Vehicle がすべて非参加で、§4.5 の先行確定だけで処理が完了した場合は、新たな順位列を接続しないため、今回の処理について `K_confirmed_after` を別途計算する必要はない。この場合の確定順位ブロック末尾は `K_confirmed_before` で表される。

**`trade_rank`**

取引後割当権利行使順位の正本（§11）。`trade_rank` も未確定範囲内順位として構成する。Node 全体での割当権利行使順位へ変換するのは、新規確定順位列を既存確定順位ブロックへ接続するときである。

**二重加算の禁止**

`K_last_buyer`、`K_decision_window`、`K_fixed` は現在の未確定範囲内順位である。これらを Node 全体の絶対順位として扱い、さらに `K_confirmed_before` を加えるような**二重加算をしない**。

#### 順位の付与

処理順は次のとおり。

1. 既存の確定順位ブロックを確認する
2. 既到着未確定 Vehicle を先に確定順位ブロックへ追加する
3. §4.5 に従い、意思決定窓内の先頭に連続する非参加 Vehicle を必要に応じて先行確定し、確定順位ブロックへ追加する
4. 先行確定済み Vehicle を未確定範囲から除き、残る未確定 Vehicle の `baseline_rank` を 1 位から再構成する
5. その時点の確定順位ブロック末尾を `K_confirmed_before` とする
6. 意思決定窓内 Vehicle がすべて非参加で、権利保有車両が存在せず TVT 検討不要となった場合は、TVT による新しい順位列を接続せず、`r_assigned` および `K_confirmed_after` の追加計算を行わずに、この Node の今回の処理を終了する。この場合の確定順位ブロック末尾は、先行確定完了後の `K_confirmed_before` と同じ位置である
7. 権利保有車両が存在し、TVT 成立、不成立または未解決によって新たに確定する順位列がある場合だけ、その順位列を接続する
8. 新たに確定する順位列の各 Vehicle について、`r_assigned = K_confirmed_before + r_local` を計算する
9. 新たな順位列を接続した場合だけ、`K_confirmed_after = K_confirmed_before + K_fixed` を計算する

全非参加時に、未定義の `r_local`、`K_fixed`、`K_confirmed_after` を要求しない。

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

TVT 候補 Vehicle の一部についてしか必要情報を取得できない場合、取得済み Vehicle だけで部分的 TVT を形成しない。この場合は baseline 情報を解決できなかった場合として、本節の既存処理に従う。詳細は §24.12 および §25.25 を参照する。

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
- §5 の既到着 Vehicle 先行確定後、意思決定窓内 baseline 到着順位の先頭に連続する非参加 Vehicle を先に確定し、先行確定済み Vehicle を未確定範囲から除いて残る Vehicle の未確定範囲内 baseline 順位を 1 位から再構成したうえで、その最上位の未確定参加 Vehicle を**権利保有車両**とする（§4.5。最初に通過予測された Vehicle ではない）
- 意思決定窓内 Vehicle がすべて非参加なら、全 Vehicle を baseline 到着順位のまま確定し、権利保有車両を選定せず、TVT 検討不要とする。全非参加時は先行確定だけで処理を終了し、TVT 順位列の接続計算を行わない（§4.5）
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

**2026-08-31更新：** 初期正式 driver でも、固定 horizon の一括 forward を採用する実装前設計である。正式 driver の仕様は **§25.25** を正本とする。

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
right_of_entry_expected_passage_timestep - tau
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
- baseline 到着順位は、baseline 予想到着 timestep、固定 tiebreaker、Vehicle ID で一意にする。この規則は、既到着かつ順位未確定の Vehicle、意思決定窓内の未確定到着予定 Vehicle、意思決定窓外の TVT 候補 Vehicle に共通して適用する。参加 Vehicle と非参加 Vehicle の間で、参加状態を理由とする同着順位上の優劣を設けない（詳細は §6.1、§6.2）。
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
baseline予想到着timestep、固定tiebreaker、Vehicle IDで一意のbaseline到着順位を作る
↓
先頭に連続する非参加Vehicleを§4.5に従って先行確定する
↓
先行確定済みVehicleを未確定範囲から除き、残る未確定Vehicleのbaseline_rankを1位から再構成する
↓
残る未確定参加Vehicleを抽出
↓
再構成後の未確定範囲内baseline順位最上位を権利保有車両とする
↓
未確定参加Vehicleが残らなければ、権利保有車両を選定せず、TVT検討不要とする
```

補足：

- 同着時に参加状態で優劣をつけない。同着順位は固定 tiebreaker、Vehicle ID で決める（詳細は §6.1、§6.2）。
- 意思決定窓内 Vehicle がすべて非参加の場合は、全 Vehicle を先行確定し、再構成対象となる未確定 Vehicle が残らず、TVT 検討不要として終了する。意思決定窓外 Vehicle はこの理由だけでは確定しない（§4.5）。
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

#### P取得後の情報充足条件

- `P` を取得しただけでは、TVT 用 baseline 情報取得完了ではない。
- `P - 1` までに到着する候補集合を確定する。
- 候補全員の必要 baseline 情報が必要である。特に候補全員の baseline 予想通過 timestep が必要である。
- `P - 1` に到着する Vehicle の通過は `P` より後になり得る。
- 候補集合確定後も観測が必要になり得る。
- 候補時間範囲は right_of_entry vehicle の `P - 1` で固定する。
- 他候補の通過時刻を理由に再帰拡張しない。

詳細は §25.25 を参照する。

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

補足（2026-08-31）：

- `TVT用baseline情報取得完了` は、後続の TVT 形成などへ進むための baseline 情報が揃った状態である。TVT 形成や順位確定そのものが完了した状態ではない。
- `P` 取得だけでは完了しない。
- 候補全員の必要 baseline 情報が必要である。
- 一部候補だけ情報が揃った場合は完了にしない。
- 一部情報だけを使った部分的 TVT は行わない。
- horizon 終端時に必要情報が不足していれば未解決である。
- 未解決時の順位処理は §14.4 に従う。
- 正式 driver は Node 状態を判定しない。

詳細は §25.25 を参照する。

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

#### 24.13.1 記録補修の位置づけ

記録日：2026-08-31

本補修の情報源は、ユーザーが保存していた過去の M365 Copilot 会話記録 3 件である。M365 Copilot がその内容を確認し、本指示文へ必要事項を整理した。Cursor は元ファイルを直接参照していない。

時系列は次のとおりである。

```text
古い
プロンプト_4.docx
↓
プロンプト_5.docx
↓
プロンプト_6.docx
新しい
```

Git 管理下の既存 Markdown には、上記 §24.13 本文のような早期終了の**骨格**は残っていたが、**詳細**は十分保存されていなかった。特にプロンプト 5 には、snapshot 固定集合、二段階観測、1 timestep 単位の進行、Node 別完了、全 Node 集約に関する具体的な検討記録が残っていた。プロンプト 6 には、collector と TVT 制度処理の責任分担が残っていた。

今回は、過去に検討済みだった内容を回収する**記録補修**である。新しい早期終了方式の実装を開始するものではない。初期正式 driver が固定 horizon 一括実行を採用する現在方針（§25.25）は変更しない。

非技術的な説明：

- 必要な交通予測情報が最大 horizon より早く揃った場合、残りの仮想計算を省略するための方式だった。
- 複数 Node が同じ full-World baseline を共有する。
- 一部 Node だけで情報が揃っても、full-World baseline 全体は停止できない。
- 全対象 Node について、それ以上の観測が不要になった場合にのみ全体を停止できる。

#### 24.13.2 過去の検討経緯

**プロンプト 4 段階の初期検討：**

- full-World baseline の最大 horizon として 30 から 50 timestep 程度、主に 50 timestep を想定していた。
- 6 timestep は TVT の意思決定窓として検討された。
- 条件によっては最大 horizon まで進めず、6 timestep 付近で終了できる可能性が議論された。
- 「6 timestep で終了できる頻度」を性能測定候補として考えていた。
- 同一実 timestep では、各 Node が別々の full-World baseline を実行せず、1 回の共通 baseline を全対象 Node で共有する方針だった。
- Node ごとに 1 timestep 最大 1 回の TVT 評価とする制度処理も議論されていた。
- full-World baseline 未解決や局所仮想計算未解決時の制度処理も議論されていた。

**プロンプト 4 段階での混在（区別が必要）：**

- 意思決定窓の終了
- Node 内の TVT 評価終了
- full-World baseline 全体の早期終了
- horizon 到達
- TVT 不成立時の制度処理

したがって、プロンプト 4 にある「6 timestep で終了」という表現だけを、現在の正式終了条件として使用しない。

```text
6 timestep
=
TVT の意思決定窓

最大 horizon
=
早期終了できなかった場合の仮想計算上限
```

#### 24.13.3 snapshot固定集合

**プロンプト 5 で具体化された内容：**

早期終了で観測する Vehicle 集合は、baseline 開始時点の snapshot で固定する。

対象は、baseline 開始時点ですでに TVT 対象 Node へ接続する対象 inlink 上にいる研究対象 Vehicle である。

snapshot 時点で次の両方を含む。

- 対象 Node へ到着済みで、まだ通過していない Vehicle
- 対象 inlink 上にいるが、まだ対象 Node へ到着していない Vehicle

baseline 開始後に対象 inlink へ進入した Vehicle は、今回の snapshot 固定集合へ追加しない。

**採用理由：**

- 動的 route choice により、baseline 中に新たな Vehicle が対象 Node へ向かう可能性がある。
- 観測対象を動的に追加すると、終了対象が増え続ける可能性がある。
- snapshot 固定集合なら、早期終了判定に使う観測対象を baseline 開始時点で有限集合として固定できる。
- 固定集合外の後続 visit や新規進入 Vehicle の通知は collector が無視する。
- 同一 Vehicle が将来別 Node へ進んでも、今回固定した visit 以外は追加しない。

**現在実装済みとの関係：**

- snapshot 固定集合の構築は `register_snapshot_fixed_visits()` で実装済み（§25.23）。
- collector による到着・通過記録と固定集合外通知の無視は実装済み。
- 初期正式 driver でも同じ snapshot 固定集合を使用する（§25.25）。

#### 24.13.4 timestep境界と1 timestep単位の進行

- baseline 開始時の `fork_W.T` を `T` とする。
- `fork_W.T == T` では timestep T はまだ未処理である。
- `W.T == T - 1` という解釈は採用しない。
- 早期終了方式では、timestep T から 1 timestep ずつ処理する。
- 判定は各 timestep 全体の処理完了後に行う。
- 到着通知や通過通知の途中で停止しない。
- 不完全な timestep 途中の状態を終了結果にしない。

概念上の反復：

```text
1 timestepを完全に処理
↓
そのtimestep中の到着・通過情報がcollectorへ記録される
↓
exec_simulation(duration_t2=DELTAT)が戻る
↓
完全なtimestep境界でNode別状態を評価する
↓
全体終了条件を評価する
↓
継続または終了
```

これは**過去の早期終了方式**の処理骨格である。初期正式 driver の固定 horizon 一括実行（§25.25）と混同しない。

#### 24.13.5 二段階観測

##### 第1区間：意思決定窓観測

baseline 開始時点を `T` とする。

意思決定窓の到着条件：

```text
T < baseline_arrival_timestep <= T + 6
```

- T から T+6 までの timestep 処理を観測する。
- T+6 の timestep 処理終了前には、意思決定窓の観測完了とはしない。
- timestep T に到着する Vehicle は、意思決定窓へ新たに入る Vehicle とは別に扱う。
- T+1 から T+6 に到着する Vehicle が意思決定窓の対象になり得る。
- T+6 までの到着記録に基づき、後続 TVT 制度処理が right_of_entry vehicle の有無を判断する。
- collector 自身は意思決定窓や right_of_entry vehicle を判定しない。

6 timestep を baseline 全体の最大 horizon と誤記しない。

##### 第2区間：right_of_entry vehicleと候補情報の観測

意思決定窓観測後、right_of_entry vehicle が存在する Node では、その Vehicle の baseline 予想通過 timestep `P` を取得するため、観測を継続する。

候補時間条件：

```text
candidate_expected_arrival_timestep <= P - 1
```

**過去のプロンプト 5 での Node 観測完了（旧条件）：**

```text
P取得
→ P - 1で候補時間範囲を確定
→ Node完了
```

**現在の最新設計（§24.11、§25.25）：**

```text
P取得
→ P - 1でTVT候補Vehicle集合を確定
→ 候補Vehicle全員の必要baseline情報を取得
→ NodeのTVT用baseline情報取得完了
```

`P` 取得だけで Node 完了とする古い条件を、現在の実装条件として使用しない。

#### 24.13.6 Node別の概念状態

少なくとも次の概念状態を区別する。

```text
意思決定窓観測中

TVT検討不要

right_of_entry vehicleの通過情報待ち

TVT候補Vehicleの必要情報待ち

TVT用baseline情報取得完了

horizon終端時未解決
```

**意思決定窓観測中**

- T+6 の処理完了前。
- right_of_entry vehicle を判断するための到着情報を観測している状態。

**TVT検討不要**

- 意思決定窓観測と必要な先行順位処理の結果、今回 TVT を検討すべき right_of_entry vehicle が存在しない状態。
- collector ではなく後続 TVT 制度処理が判定する。
- この Node について、それ以上の baseline 観測が不要となる。

**right_of_entry vehicleの通過情報待ち**

- right_of_entry vehicle は制度側で特定できた。
- baseline 予想通過 timestep `P` がまだ記録されていない。
- P 取得まで観測継続が必要。

**TVT候補Vehicleの必要情報待ち**

- `P` を取得済み。
- `P - 1` を基準とする候補集合を確定できる。
- 候補 Vehicle 全員の必要 baseline 情報がまだ揃っていない。
- 特に一部候補の baseline 予想通過 timestep が未取得。
- 現在の最新設計では、情報取得完了として扱わない。

**TVT用baseline情報取得完了**

後続の TVT 形成、局所仮想計算、経済評価へ進むために必要な baseline 情報が揃った状態である。次が完了した状態**ではない**。

- TVT 形成
- 局所仮想計算
- 買い手・売り手選定
- 経済評価
- 支払い・補償
- 順位確定
- §14.3 または §14.4 の処理

現在の完了条件として、少なくとも次が必要である。

- right_of_entry vehicle を制度側で特定できる
- `P` を取得済み
- `P - 1` に基づく候補集合を確定できる
- 候補 Vehicle 全員の必要 baseline 情報が揃っている
- 特に候補 Vehicle 全員の baseline 予想通過 timestep が揃っている

**horizon終端時未解決**

次を含む。

- `P` を取得できなかった
- `P` がないため候補集合を確定できなかった
- 候補 Vehicle の一部または全部について必要情報を取得できなかった
- Node が情報取得完了になる前に設定 horizon へ到達した

horizon 終端時未解決は、機械的な実行異常ではない。後続制度処理が §14.4 に従って扱う。

#### 24.13.7 一部情報による部分的TVTの禁止

現在の最新設計（§14.4、§25.25）として：

候補 Vehicle 全員の必要情報が揃わなければ、情報取得済み Vehicle だけを使った部分的 TVT を形成しない。

例：

```text
baseline到着順位：
A, B, C, D, E, F

必要な通過情報を取得できたVehicle：
A, B, E
```

A、B、E だけで TVT を形成すると、E が C、D より前へ移る可能性がある。C、D は E より先に到着しているにもかかわらず、順位を下げられることへの対価を受け取らない可能性がある。したがって、部分的 TVT は形成しない。

候補全員の必要情報が揃わなければ Node 未解決とする。候補時間範囲は right_of_entry vehicle の `P - 1` で固定する。ほかの候補 Vehicle の通過時刻を理由に候補時間範囲を再帰的に拡張しない。

未解決時は §14.4 へ接続する。

- 意思決定窓内の未確定 Vehicle 全体を baseline 到着順位で確定する。
- 意思決定窓外の未確定 Vehicle は、未解決という理由だけでは確定しない。

#### 24.13.8 Node別完了条件

Node は次のいずれかの場合に、早期終了判定上の完了扱いとなる。

```text
TVT検討不要

または

TVT用baseline情報取得完了
```

- TVT 検討不要と情報取得完了は異なる。
- TVT 検討不要は、TVT 形成へ進まないことが判明した状態。
- 情報取得完了は、TVT 形成以降へ進むための baseline 情報が揃った状態。
- 一部候補だけ情報が揃った状態は完了ではない。
- horizon 終端時未解決は早期終了上の通常完了状態ではない。
- horizon 到達によって観測を終える状態である。
- Node 状態の判定は collector の責任ではない。

#### 24.13.9 full-World baseline全体の早期終了条件

次を最新の終了条件として記録する（上記 §24.13 本文と同旨）。

```text
すべての対象Nodeが、

TVT検討不要

または

TVT用baseline情報取得完了

のいずれかになった
```

- 一部 Node だけ完了しても full-World baseline 全体は終了しない。
- TVT 検討不要 Node と情報取得完了 Node が混在してもよい。
- すべての Node がいずれかに該当すれば終了できる。
- 1 つでも意思決定窓観測中、P 待ち、候補情報待ちの Node が残れば継続する。
- 最後の未完了 Node が完了した timestep の**全処理終了後**に停止する。
- 通知の途中で即時停止しない。
- 完全な timestep 境界でのみ停止する。
- 設定 horizon 到達前でも全体完了条件を満たせば早期終了できる。
- 全体完了条件を満たさなければ設定 horizon まで継続する。

#### 24.13.10 horizon到達時

- horizon は、早期終了できなかった場合の実行上限である。
- horizon へ到達しても取得できない交通情報があり得る。
- 未取得値は collector で `None` のまま残り得る。
- horizon 完走後の情報不足は driver の実行異常ではない。
- 未完了 Node は horizon 終端時未解決として後続制度処理へ渡す。
- 一部情報だけを完全情報として扱わない。
- horizon を超えて自動延長しない。
- horizon 値は感度分析対象である。
- 早期終了と、World 終端を避ける 1 timestep 余白（§25.25.11）は**別の論点**である。
- 将来早期終了を導入する場合も、forward 後に World 終端へ到達させない契約と整合させる。

#### 24.13.11 空集合の区別

**World 全体の snapshot 固定集合が 0 件**

- 今回観測する固定 visit が存在しない。
- forward せず 0 step で正常終了できる。
- 現在の固定 horizon 正式 driver でも採用済み（§25.25.10）。
- horizon 余白検査を行わない。

**特定 Node だけ snapshot 固定集合が 0 件**

- その Node を TVT 検討不要と即断できるかは制度側が判断する。
- ほかの Node に観測対象があれば full-World baseline 全体は継続し得る。
- 特定 Node の 0 件と World 全体の 0 件を混同しない。
- 特定 Node が 0 件の場合の厳密な Node 状態設定方式は、過去記録では確定を確認できない。
- 具体的状態設定は §24.13.16 の未確定実装細部として残す。

#### 24.13.12 完了済みNode

- Node 状態は同一 baseline 内で原則一方向である。
- 完了済み Node を再判定する必要はない。
- 完了済み Node の後続通知は、早期終了判定上は無視できる。
- collector 内の固定 visit 記録を途中で削除または破壊しない。
- 早期終了判定側が、完了済み Node を次回の評価対象から外す。
- 完了済み Node の具体的な保存形式は §24.13.16 で未確定。

#### 24.13.13 collectorと制度処理の責任分担

**プロンプト 6 で具体化された責任分担：**

collector が担当すること：

- snapshot 固定集合の保持
- 固定 visit の識別
- baseline 到着 timestep の記録
- arrival tiebreaker の記録
- route_next_link の記録
- baseline 通過 timestep の記録
- 公開読取 API による結果提供
- 固定集合外通知の無視
- 固定対象 visit の重大な二重記録等の不整合検出

collector が担当しないこと：

- 意思決定窓判定
- right_of_entry vehicle 選定
- `P - 1` 候補集合確定
- 候補 Vehicle 全員の情報充足判定
- Node 状態判定
- 全 Node 完了判定
- 早期終了判定
- TVT 形成
- 経済評価
- 順位確定

早期終了判定に必要な交通事実を collector が提供し、その意味を TVT 制度処理側が解釈する。

#### 24.13.14 固定horizon正式driverとの関係

- 現在の初期正式 driver は固定 horizon 一括実行である（§25.25）。
- 初期正式 driver は Node 状態を毎 timestep 判定しない。
- 初期正式 driver は早期終了を実行しない。
- 初期正式 driver で早期終了を採用しないことは、過去の早期終了設計を**撤回した意味ではない**。
- 早期終了の性能効果を確認した後で、将来採用を再検討する。
- 将来導入する場合、1 timestep 単位の fork 進行と Node 状態判定を含む制御が必要である。

**未確定の実装配置（§24.13.16 参照）：**

- 固定 horizon driver を拡張するか
- 早期終了対応の別 driver を作るか
- Node 状態評価 helper を設けるか
- Node 状態をどのモジュールへ置くか

#### 24.13.15 早期終了の性能評価

少なくとも次を測定候補とする。

- Node ごとに必要情報が揃った最初の timestep
- 全対象 Node が完了状態になった最初の timestep
- horizon 到達前に全 Node が完了した baseline 実行回数
- 早期終了可能率
- 早期終了できなかった実行回数
- 未解決 Node が 1 つ以上残ったため早期終了できなかった回数
- 仮に早期終了していた場合の省略可能 timestep 数
- 1 回当たりの平均、中央値、最大省略 timestep 数
- 対象 Node 数別の早期終了可能率
- 混雑条件別の早期終了可能率
- 需要条件別の早期終了可能率
- 1 timestep 単位で `exec_simulation()` を呼ぶ負荷
- 毎 timestep の Node 状態判定負荷
- 未完了 Node 集合の走査負荷
- 固定 horizon 一括方式と早期終了方式の総実行時間比較

- 採用可否は省略 timestep 数だけではなく、1 timestep 呼出しと判定処理を含む**総実行時間**で判断する。
- 対象 Node 数が多い場合、最後の未完了 Node に全体終了時刻が引っ張られる可能性がある。
- 混雑 Node または未解決 Node が 1 つでも残れば horizon まで継続する。
- このため初期正式 driver では固定 horizon 一括実行を採用した。
- 早期終了を永久に不採用としたわけではない。

**固定 horizon 完走後の事後測定：**

- collector には固定 visit の到着・通過 timestep が残る。
- collector だけでは right_of_entry vehicle、`P - 1` 候補集合、候補全員情報充足を判断できない。
- 事後的な早期終了可能時刻の推定には、後続 TVT 制度処理または同等の診断ロジックが必要である。
- 正式 driver へ過剰な制度状態記録を追加しない。
- 性能評価用診断は正式 driver とは別責任とする方向。
- 具体的な診断 API は §24.13.16 で未確定。

#### 24.13.16 現在も未確定の実装細部と再開地点

**未確定の実装細部：**

- Node 状態の enum、dataclass、dict 等の具体形式
- 完了済み Node 集合または未完了 Node 集合の具体形式
- 毎 timestep 全 Node を走査するか、未完了 Node だけを走査するか
- collector record を毎回読み直すか
- 別の制度状態を逐次更新するか
- Node 状態評価をどのモジュールへ置くか
- 固定 horizon driver を拡張するか、早期終了用 driver を分けるか
- 早期終了採用の性能閾値
- 早期終了導入時の result フィールド
- 特定 Node の固定集合 0 件時の具体的な状態設定
- horizon 到達と全 Node 完了が同じ timestep に成立した場合の内部的な分岐表現
- 性能評価用診断の具体的 API
- 早期終了導入時の World 終端後 1 timestep 余白の検査方法

**完全な timestep 境界で判定すること自体は確定**であり、未確定へ戻さない。

**将来の再開地点：**

- 早期終了の制度上の基本設計は本 §24.13 を正本とする。
- プロンプト 4、5、6 を再読しなくても、本節から再開できるよう必要事項を記録した。
- 将来の作業は、未確定の実装形式と性能上の採用判断に限定する。
- 初期固定 horizon driver の実装を先に進める現在方針は変更しない。

**2026-09-01 更新：**

- Node 別の**確定順位ブロック**と**未確定 visit 集合**について、実装前仕様を **§25.25.30** で確定した。
- 本節記録時点の「Node 状態の enum、dataclass、dict 等の具体形式」は、**評価状態**（§24.12 の概念状態）と**順位状態**（§25.25.30）を区別して参照する。
- **順位状態**（確定ブロック・未確定 visit・`VisitKey`・公開 API・不変条件）は **§25.25.30** を正本とする。
- **評価状態**（TVT 検討不要、P 待ち、baseline 情報取得完了、horizon 終端時未解決等）、**完了済み Node 集合**、**毎 timestep 走査方法**、**早期終了**関連、**実交通上の未確定 visit 登録タイミング**は、引き続き本節または §25.25.30 対象外として未確定または別作業である。
- 過去の「TVT 順位状態全体が未確定」という記録は、**今回 §25.25.30 で確定した範囲**と**なお未確定の範囲**を分けて解釈する。誤りとして削除しない。

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

**2026-08-31更新：** 上記は 2026-08-27 時点の記録である。最新状態は次のとおり。

- collector 本体は実装済み（§25.23 以降）。
- UXsim 通知接続は実装済み。
- snapshot 固定集合構築補助処理は実装済み。
- 小規模 fork 統合診断は実装済み（§25.24）。
- 正式 driver は §25.25 で実装前設計済み。Python 実装は未着手。
- 早期終了の性能測定は引き続き未実装。
- Node 別状態は引き続き未実装。
- World 終端回避用追加 1 timestep 余白は §25.25.11 で確定（2026-08-31 追加確認）。

詳細は §25.20 から §25.25 を参照する。

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

### 25.21 第2回実装の結果

記録日：2026-08-28

対象：§25.15・§25.20で定義した第2回実装（UXsim通知接続と接続テスト）

状態：第2回実装のコード上の作業は完了。本節の記録時点では、第2回実装のコード変更と本記録はまだ新しいコミットへ保存されていない。pushもされていない。

§25.1〜§25.19は実装前設計の記録である。§25.20は第1回実装の結果記録である。本節はTerminalで差分、接続位置、テスト結果を直接確認したうえでの第2回実装結果記録である。

#### 25.21.1 実装した範囲

今回、次を実装した。

- `Vehicle.record_order_control_node_arrival()`へのB到着通知接続
- `Node._serve_order_control_batch_service_queue_internal()`へのBATCH通過通知接続
- `Node.transfer_fcfs_clearance()`へのFCFS clearanceあり通過通知接続
- 通常`Node.transfer()`への通過通知接続
- `tests_order_control_baseline_collector_uxsim.py`の新規作成
- collector無効時の交通結果とRNG状態の不変確認
- real_Wとfork_Wのcollector分離確認
- 固定集合外Vehicleを安全に無視する接続確認
- 通過前の重大不整合で物理通過前に停止する確認

今回の実装では、次の2ファイルだけを変更・作成した。

- 変更：`uxsim/uxsim.py`
- 新規：`tests_order_control_baseline_collector_uxsim.py`

第1回実装済みの`uxsim/order_control_baseline_collector.py`と`tests_order_control_baseline_collector.py`は変更していない。

実装では、時間価値取引の根幹に関わる処理について、短さや高度なPython技法より、研究者が処理順序を後から理解できる可読性を優先した。

#### 25.21.2 B到着通知

- 接続先は`Vehicle.record_order_control_node_arrival()`
- UXsim既存の`arrival_time`と`arrival_tiebreaker`の設定完了後に通知する
- 同一visitで到着情報がすでに記録済みの場合は、既存の早期returnによりcollectorへ再通知しない
- collectorが`None`の場合は通知用情報を組み立てない
- collectorが有効な場合だけ、次を`record_baseline_arrival()`へ渡す
  - `vehicle_name`
  - current visitの`visit_id`
  - `node_name`
  - baseline到着timestep
  - `arrival_tiebreaker`
  - `route_next_link_name`
- baseline到着timestepは、既存の秒単位`arrival_time`から次の方法で変換する

`int(round(arrival_time / W.DELTAT))`

- この通知では追加RNGを消費しない
- 固定集合外visitはcollector側で無視する
- 固定集合内visitで`route_next_link`が存在しない場合は重大不整合となる

#### 25.21.3 通過通知の共通原則

- 物理通過前に`prepare_baseline_passage_recording()`を呼ぶ
- 物理通過前のvisit IDを使用する
- `begin_order_control_visit_on_link_entry()`によってcurrent visitが次のNode向けへ切り替わった後に、元のvisit IDを取り直さない
- 固定集合外Vehicleでは`prepare`が`None`を返し、通常の物理通過を続ける
- 固定集合内Vehicleの重大不整合は物理通過前に`ValueError`となる
- 物理通過と必要なUXsim状態更新が成功した後だけ、`apply_baseline_passage_timestep()`を呼ぶ
- 通過前に確認したrecordを物理通過後に再検索しない
- 通過後に同じ整合性確認を繰り返さない
- collector無効時にはcurrent visitやvisit IDをcollector通知用に取得しない

#### 25.21.4 FCFS clearanceあり通過接続

- 接続先は`Node.transfer_fcfs_clearance()`
- 実際に通過条件を満たしたVehicleだけを対象とする
- collector有効時に、物理通過前のcurrent visitからvisit IDを取得する
- current visitが`None`なら`None`をprepareへ渡す
- 固定集合外Vehicleならprepareがpayload検証前に`None`を返す
- 固定集合内Vehicleでcurrent visitが欠落していれば、物理通過前に重大不整合として停止する
- 物理通過、outlink追加、incoming Vehicle削除、`last_order_control_inlink`および`last_order_control_entry_timestep`更新後に通過timestepを設定する
- FCFS clearanceなしには接続していない

#### 25.21.5 通常Node.transfer通過接続

- 接続先は、FCFSとBATCHへの早期分岐後に実行される通常`Node.transfer()`
- 固定集合内のtime-value対象visitでもこの通知経路を利用できる
- time-value制度処理自体はまだ実装していない
- order-control対象外の通常Nodeでは、固定集合外Vehicleのcurrent visitが`None`でも安全に通過できる
- collector有効時にだけcurrent visitとvisit IDを通知用に確認する
- prepareは累積台数やLink状態を変更する前に呼ぶ
- applyはoutlink追加とincoming Vehicle削除後に呼ぶ
- 信号、merge priority、通常RNG選択、容量判定などの既存交通処理は変更していない

#### 25.21.6 BATCH通過接続

最終処理順序は次のとおりである。

1. service unitとcurrent visitの既存整合性確認
2. 到着、clearance、通過可能性の確認
3. collector有効時に、検証済みの`service_unit["visit_ids"][0]`を使ってprepare
4. `_transfer_vehicle()`による物理通過
5. `service_unit["vehicles"].pop(0)`
6. `service_unit["visit_ids"].pop(0)`
7. `transferred_vehicle_count`更新
8. `active_inlink`更新
9. prepareでrecordが返った場合だけ、関数ローカルのpending listへ追加
10. service queue整理
11. queue整理後、pending recordへ同じ`W.T`を設定

補足：

- pending listはcollector有効時だけ作成する
- pending listの順序を通過順位として保存・解釈しない
- queue整理とpending recordへのapplyを小さなローカル処理にまとめた
- arrival wait、clearance stop、transfer後のcapacity block、正常終了の各return経路で、queue整理後にapplyする
- service queueが最初から空の場合はpending recordがないため追加処理しない
- queue整理前に例外が発生したbaselineは失敗扱いであり、例外を握りつぶさない
- rollbackは追加していない
- zero-service reformation等の既存BATCH挙動を変更していない

#### 25.21.7 collector内部索引との責任分離

実装確認の過程で、初回実装後に次の修正を行った。

- 当初、`uxsim.py`からcollectorの非公開索引`_visit_record_by_vehicle_name`を直接参照する実装があった
- Terminal差分確認でこれを検出した
- 最終実装では、BATCH、FCFS clearanceあり、通常transferの3経路から直接参照を削除した
- 固定集合への所属判定は`prepare_baseline_passage_recording()`へ集約した
- collectorに新しい所属確認メソッドは追加していない
- `uxsim.py`に`_visit_record_by_vehicle_name`という文字列が存在しないことをTerminalで確認した

修正理由は次のとおりである。

- collector内部実装をUXsim本体から隠す
- 索引名変更による接続側の破損を防ぐ
- 固定集合判定の責任をcollectorへ維持する
- 同じ索引検索の重複を避ける

#### 25.21.8 collector無効時の不変確認

- 同一ネットワーク、同一Vehicle、同一seedの2つのWorldを使用
- 一方は既定のcollector `None`
- もう一方はcollector属性を明示的に`None`へ設定
- Vehicleの完了状態、到着時刻または旅行時間、通過後Linkが一致
- `W.rng.bit_generator.state`が一致
- `W.order_control_rng.bit_generator.state`が一致
- collector通知接続による追加RNG消費は確認されなかった
- collector無効時は、World属性の読取とNone判定以外の通知処理を行わない構成である

#### 25.21.9 固定集合外Vehicleの確認

次の3経路で確認した。

- BATCH
- FCFS clearanceあり
- 通常Node.transfer

特に次を区別して記録する。

- BATCHではcurrent visitとservice-unit visit IDを持つが、collector未登録のVehicleが正常通過
- FCFS clearanceありではcurrent visitを持つが、collector未登録のVehicleが正常通過
- 通常Node.transferではorder-control対象外Nodeでcurrent visitが`None`のcollector未登録Vehicleが正常通過

いずれもcollector記録を作らず、物理通過を妨げなかった。

#### 25.21.10 通過前の重大不整合

- BATCH service unitの登録visit IDとcollector固定visitのvisit IDを意図的に不一致にした接続テストを実施
- `prepare_baseline_passage_recording()`が物理通過前に`ValueError`を送出
- Vehicleは元のinlinkと`incoming_vehicles`に残った
- outlinkへ移動しなかった
- collectorの`baseline_passage_timestep`も`None`のままだった

#### 25.21.11 real_Wとfork_Wの分離

- real_Wのcollector参照は`None`
- `fork_W = real_W.copy()`を実行
- copy完了後にfork_W側だけへcollectorを設定
- real_W側は`None`のまま
- fork側collectorへ固定visitを登録してもreal_W側にcollector結果は現れない
- collectorはWorldへの逆参照を持たない
- real_Wへcollectorを設定してからcopyする方式にはしていない

#### 25.21.12 新規接続テスト

`tests_order_control_baseline_collector_uxsim.py`に、次の11件がある。

- `test_collector_disabled_traffic_and_rng_unchanged`
- `test_b_arrival_notification_records_baseline_facts`
- `test_b_arrival_notification_ignores_duplicate_and_outside_fixed_set`
- `test_batch_passage_records_after_service_queue_finalize`
- `test_batch_passage_ignores_outside_fixed_set_vehicle`
- `test_fcfs_clearance_passage_records_original_visit`
- `test_fcfs_clearance_passage_ignores_outside_fixed_set_vehicle`
- `test_normal_transfer_passage_on_time_value_node`
- `test_normal_transfer_passage_ignores_outside_fixed_set_vehicle`
- `test_batch_passage_stops_before_physical_transfer_on_inconsistency`
- `test_real_world_and_fork_collector_are_separated`

#### 25.21.13 Terminalで確認したテスト結果

次を、Terminalで直接実行して成功した。

| コマンド | 結果 |
|----------|------|
| `python tests_order_control_baseline_collector.py` | 成功 |
| `python tests_order_control_baseline_collector_uxsim.py` | 成功 |
| `python tests_order_control_rng.py` | 成功 |
| `python tests_order_control_current_visit_state.py` | 成功 |
| `python tests_order_control_current_visit_arrival.py` | 成功 |
| `python tests_fcfs_order_control_clearance_1.py` | 成功 |
| `python tests_order_control_batch_service_queue_transfer.py` | 成功 |
| `python tests_order_control_batch_transfer.py` | 成功 |
| `python tests_order_control_batch_zero_service_reformation.py` | 成功 |
| `python tests_order_control_batch_revisit_integration.py` | 成功 |
| `python tests_order_control_n1_batch_vs_fcfs_revisit_equivalence.py` | 成功 |
| `python tests_order_control_batch_t_trigger_level_2_body.py` | 成功（22 tests） |
| `python -m py_compile uxsim/uxsim.py uxsim/order_control_baseline_collector.py tests_order_control_baseline_collector.py tests_order_control_baseline_collector_uxsim.py` | 成功 |
| `git diff --check` | 問題なし |
| 未追跡の新規接続テストについて`git diff --no-index --check` | 問題なし |
| `grep -n '_visit_record_by_vehicle_name' uxsim/uxsim.py` | 0件 |

#### 25.21.14 今回実装していないもの

- FCFS clearanceなし通知
- snapshot固定集合を自動構築する正式driver
- T+6までの意思決定窓管理
- right_of_entry_vehicle選定
- right_of_entry_vehicle通過待ち
- 二段階観測ドライバ
- TVT候補確定
- 到着順位
- 確定順位ブロック
- trade_rank
- 買い手・売り手選定
- 支払い・補償
- Node別制度状態
- 早期終了
- 通過順位
- BATCH固有の分析情報
- 長期ログ
- 全Node一括export
- real_Wへのbaseline結果保存
- 性能最適化
- 診断スクリプト変更

#### 25.21.15 第2回実装の完了判断

- 第2回実装として予定した通知接続、接続テスト、collector無効時確認、real_Wとfork_Wの分離確認を実装した
- Cursor報告後にTerminalで差分、private索引参照の不存在、追加テスト、全指定テスト、構文、形式を確認した
- 第2回実装のコード上の作業は完了と判断する
- 実装結果を整理したうえで本§25.21と進捗メモを更新したため、メモ更新を含めた第2回実装の完了条件を満たした
- 本記録時点では新しいコミットへ保存されておらず、pushされていない

#### 25.21.16 次の作業

次の作業は、§25.15で想定した第3回実装相当の作業である。

- 必要な追加テストの確認
- 小規模fork実行診断
- snapshot固定集合を構築する最小補助処理または診断用driver
- collector接続後の設計確認

ただし、次を明記する。

- 「第3回実装」という名称は§25.15の実装順序上の便宜的名称であり、恒久的なフェーズ名ではない
- 直ちに着手済みではない
- 二段階観測ドライバ、TVT制度処理、Node状態、早期終了は、その後の別作業である

### 25.22 snapshot固定集合構築の具体設計

記録日：2026-08-28

状態：実装前設計である。snapshot固定集合を構築する補助処理とそのテストはまだ未実装である。

本節は、Terminalによる実コード確認、小規模実測、Cursorへの訂正提示と再調査を経て確定した設計結果を記録する。§24の歴史的記述や§25.21までの実装結果は削除せず、本節で最新の確定事項を追記・訂正する。

#### 25.22.1 位置づけ

- §24のsnapshot固定集合設計を、現在実装済みのcollectorとUXsim通知接続へつなぐための具体設計である
- collector本体と通知接続はコミット`bfb3933`までで実装・push済み
- 今回設計するのは、fork Worldのsnapshot状態から固定visitを選び、collectorへ登録する補助処理である
- 二段階観測、right_of_entry_vehicle選定、TVT制度処理、早期終了は今回の範囲外
- 今回の補助処理はTVT対象Nodeだけを扱う
- FCFS Node、BATCH Node、標準UXsim NodeでTVT制度処理を行うものではない

#### 25.22.2 4方式比較との関係

- 最終比較の基本は、signalized UXsim、FCFS、BATCH、time-value transactionの4方式
- 1つのネットワーク内で方式を混在させる場合と、全比較対象Nodeを同じ方式へ設定したWorld同士を比較する場合の両方を想定する
- 例として、全比較対象NodeをFCFSへ設定したケースと、全比較対象Nodeをtime_valueへ設定したケースを比較できる
- `order_control_type="none"`は標準UXsim制御
- signalized UXsimは独立した`order_control_type`ではなく、通常は`order_control_type="none"`のNodeに信号を設定するケース
- TVT制度処理を行うのは`order_control_type="time_value"`のNodeだけ
- collectorがBATCH、FCFS、通常transferへ接続されていることは、これらのNodeでTVT制度を実行することを意味しない

#### 25.22.3 TVT対象Node集合の引継ぎ

1. 研究用driverが、比較対象Nodeを`set_order_control_for_nodes()`で`time_value`へ設定する
2. その戻り値であるNode一覧からNode名一覧を一度だけ作る
3. 同じNode集合を人が改めて二度入力しない
4. `real_W`をcopyして`fork_W`を作る
5. real_WのNodeオブジェクトをforkへ直接渡さない
6. Node名一覧をfork側のsnapshot補助処理へ引き継ぐ
7. fork側で`fork_W.get_node(node_name)`によりfork自身のNodeを取得する

補足：

- 全比較対象Nodeをtime_valueにするケースでは、その全Node名が引き継がれる
- 一部Nodeだけをtime_valueにする混在ケースにも同じ方法で対応できる
- Node名一覧を自動的にWorld全体から再抽出する方式は初期実装では採用しない
- 理由は、設定時に得たNode集合をそのまま使う方が実験意図を明示でき、同じ集合の再入力による食い違いを防げるため

#### 25.22.4 対象Nodeの事前検証

固定visit候補を調査する前に、Node名一覧全体を検証する。

確認項目：

- Node名一覧が空でない
- 同じNode名が重複していない
- 各Node名が空でない文字列
- fork WorldにNodeが存在する
- `order_control_eligible is True`
- `order_control_type == "time_value"`

方針：

- 空集合、重複、存在しないNode名、非文字列、空文字列は`ValueError`
- `fcfs`、`batch`、`none`のNodeが含まれていれば`ValueError`
- `none`については信号あり・なしを区別せずTVT対象外
- 全Nodeの検証を完了してからVehicle候補の調査へ進む
- Node入力エラーによる途中登録を防ぐ

#### 25.22.5 baseline開始timestep T

- baseline開始timestepをTとする
- snapshotは`fork_W.T == T`で、timestep Tの処理を開始する直前に作る
- 「Timestep Tの処理開始前」は、Tより前の時刻で作るという意味ではなく、時刻番号はTだがTのmain loopをまだ実行していない状態
- `W.T == T - 1`という過去のCursor解釈は誤りであり採用しない
- snapshot固定集合構築後に初めてforkのtimestep Tを処理する
- `exec_simulation(duration_t2=W.DELTAT)`でtimestep Tを1回処理すると、実行後は`W.T == T + 1`
- `W.TIME == (T + 1) * W.DELTAT`
- 補助処理へTを別引数として渡さず、呼出時点の`fork_W.T`をTとして扱う
- driverは、`exec_simulation()`が正常に戻った後で、次の`exec_simulation()`を始める前に補助処理を呼ぶ

#### 25.22.6 timestep T到着Vehicle

- timestep Tの処理中に新たに対象Nodeへ到着するVehicleは、snapshot時点では未到着なのでB
- Bとして固定visit登録する
- timestep Tの`Vehicle.update()`で通常の到着経路を通る
- collectorの`baseline_arrival_timestep`はTになる
- `was_arrived_at_snapshot`はFalseのまま

小規模実測（Terminalで実行した一時的な標準入力Python診断）で次を確認した：

- snapshot時点は`W.T == 10`
- Vehicleの到着情報はNone
- timestep 10を処理後、`W.T == 11`
- `baseline_arrival_timestep == 10`
- `was_arrived_at_snapshot is False`

#### 25.22.7 Aの定義と抽出元

Aは、snapshot時点ですでに対象Nodeへ到着済みだが、まだ当該Nodeを通過していない固定visitである。

Aの主な抽出元：

- `target_node.incoming_vehicles`

Aについて確認する条件：

- `veh.state == "run"`
- `veh.order_control_current_visit is not None`
- current visitの`visit_id`が正しい
- `current_visit["visit_id"] == veh.order_control_visit_id`
- `current_visit["node"] is target_node`
- `current_visit["inlink"]`が対象Nodeのinlink
- `veh.link is current_visit["inlink"]`
- Vehicleがそのinlinkの`vehicles`にも存在する
- `arrival_time`と`arrival_tiebreaker`が両方非None
- 片方だけ存在する状態は重大不整合
- `route_next_link is not None`
- `route_next_link.start_node is target_node`

Aの登録値：

- `vehicle_name=veh.name`
- `vehicle_id=veh.id`
- `node_name=target_node.name`
- `inlink_name=current_visit["inlink"].name`
- `visit_id=current_visit["visit_id"]`
- `was_arrived_at_snapshot=True`
- `baseline_arrival_timestep=int(round(arrival_time / fork_W.DELTAT))`
- `arrival_tiebreaker=current_visit["arrival_tiebreaker"]`
- `route_next_link_name=veh.route_next_link.name`
- `baseline_passage_timestep=None`

Aの到着timestepは、正常なtimestep境界では`fork_W.T`より前である。timestep Tに到着するVehicleはsnapshot時点ではBであるため。

#### 25.22.8 Aのコンテナ状態に関する実測と訂正

確認した実コード上の処理順序（1 timestep内）：

1. `Node.transfer()`
2. `Vehicle.carfollow()`
3. `Vehicle.update()`

`Node.transfer()`末尾で`incoming_vehicles`はいったん空になるが、通過できずinlink終端に残ったVehicleは、その後の同じtimestepの`Vehicle.update()`で再び`incoming_vehicles`へ追加される。

`record_order_control_node_arrival()`は到着情報が既に存在すれば早期returnするが、`incoming_vehicles.append()`はその呼出しより前に完了している。

小規模実測では、次を確認した。

到着直後：

- Vehicleは`node.incoming_vehicles`に存在
- Vehicleは元の`inlink.vehicles`にも存在
- `veh.link is inlink`
- 到着情報は記録済み

次のtimestepで通過を物理的に阻止した後も、正常な`exec_simulation()`終了時点では：

- Vehicleは`node.incoming_vehicles`に再登録済み
- Vehicleは元の`inlink.vehicles`にも存在
- inlink-only Aにはならなかった

過去の調査解釈の訂正：

- `Node.transfer()`末尾でincomingがクリアされるため、正常なtimestep境界でinlink-only Aが残るという解釈は誤り
- 正常な`exec_simulation()`停止境界では、到着済み・未通過Aはincomingとinlinkの両方に存在する
- inlink-only Aは、transfer後・`Vehicle.update()`前のmain loop途中、例外中断、または手動transferだけを呼んだ中間状態では発生し得る
- snapshot補助処理は、そのような中間状態を正常状態として受け入れない

#### 25.22.9 Bの定義と抽出元

Bは、snapshot時点で対象Nodeのinlink上にいるが、まだ対象Nodeへ到着していない固定visitである。

Bの抽出元：

- 対象Nodeの各`inlink.vehicles`

Bについて確認する条件：

- `veh.state == "run"`
- `veh.link is inlink`
- `veh.order_control_current_visit is not None`
- current visitの`node`がtarget_node
- current visitの`inlink`が走査中のinlink
- current visitの`visit_id`が`veh.order_control_visit_id`と一致
- `arrival_time`と`arrival_tiebreaker`が両方None
- `veh not in target_node.incoming_vehicles`

B登録時は、snapshot時点で`veh.route_next_link`が何らかの値を持っていても、collectorへは保存しない。

Bの登録値：

- `vehicle_name=veh.name`
- `vehicle_id=veh.id`
- `node_name=target_node.name`
- `inlink_name=inlink.name`
- `visit_id=current_visit["visit_id"]`
- `was_arrived_at_snapshot=False`
- `baseline_arrival_timestep=None`
- `arrival_tiebreaker=None`
- `route_next_link_name=None`
- `baseline_passage_timestep=None`

#### 25.22.10 AとBの重複防止

処理順序：

1. `node.incoming_vehicles`からAを調査する
2. Aの登録予定データを一時listへ追加する
3. Aとして追加したVehicle名を一時的な集合へ記録する
4. 各inlinkの`inlink.vehicles`を走査する
5. Aとして登録予定データへ追加済みのVehicleが再び見つかることは正常
6. そのVehicleはBとして追加せずスキップする
7. Aとして追加されていないVehicleについて、B条件を満たすものだけをBとして追加する
8. Aとして追加されていないのに到着情報が両方存在するVehicleがinlink上で見つかった場合は、正常なsnapshot境界と矛盾するため`ValueError`
9. 到着情報が片方だけ存在する場合も`ValueError`
10. 全対象Nodeを通じて、同一Vehicleは最大1固定visit

「登録予定データへ追加済み」とは、collectorへ登録済みという意味ではなく、全候補検証中の一時データへ追加済みという意味である。

#### 25.22.11 対象外Vehicleと重大不整合

正常に固定集合から除外するもの：

- まだ出発していないVehicle
- `state=="end"`
- `state=="abort"`
- trip-end処理対象
- taxi mode
- specified_route
- 対象Nodeのinlink上にいないVehicle
- current visitのNodeが別Node
- 対象Nodeをすでに通過済みのVehicle

ただし、`participates_in_order_exchange=False`は除外条件にしない。交通予測にはTVT参加者・非参加者の両方が必要である。

重大不整合として停止するもの：

- 対象Nodeのincomingまたはinlink上にいるのにcurrent visitがない
- current visitの必須キー欠落
- visit ID不一致
- current visitのNode不一致
- inlink不一致
- `veh.link`とcurrent visit inlinkの不一致
- arrival_timeとarrival_tiebreakerの片側欠落
- Aでroute_next_linkがNone
- Aでroute_next_link.start_nodeがtarget_nodeではない
- 正常なsnapshot境界で、Aとして検出されていない到着済みVehicleがinlink上に存在
- 同一Vehicleが複数固定visit候補になる

正常な対象外Vehicleを、状態破損として扱わないよう注意する。

#### 25.22.12 全候補検証後の登録

第1段階：

- 全対象Nodeを検証
- 全A/B候補を抽出
- current visitとUXsim状態を検証
- collectorへ渡す登録予定データをプレーンなdictのlistとして作る
- 同一Vehicle重複を検出
- collectorはまだ変更しない

第2段階：

- 第1段階の全検証が成功した場合だけ、登録予定データを順番に`collector.register_snapshot_visit(**entry)`へ渡す

補足：

- 登録予定データは、`register_snapshot_visit()`の引数名と一致するdictとする第一候補
- collector内部の可変dataclassは事前計画へ流用しない
- 登録計画専用dataclassは初期実装では追加しない
- collector側のvalidationを補助処理側へ全面複製しない
- 補助処理側はUXsimオブジェクト状態とA/B分類を確認する
- この構成により、Node・Vehicle検証中の部分登録を防ぐ

#### 25.22.13 登録順序と戻り値

第一候補の順序：

- `set_order_control_for_nodes()`の返却Node順から作ったNode名順
- 各Node内ではAを先に調査
- BはNodeの各inlinkを安定した順序で走査
- 各inlink内では`inlink.vehicles`の物理FIFO順

ただし、この登録順に到着順位、通過順位、trade_rank等の制度上の意味を持たせない。

初期実装の戻り値は、総登録件数`int`だけとする第一候補とする。

Node別A/B件数、主キーlist、登録計画listは初期公開戻り値へ含めない。

#### 25.22.14 補助処理の配置と最小構造

第一候補の新規モジュール：

- `uxsim/order_control_baseline_snapshot.py`

第一候補の公開関数：

`register_snapshot_fixed_visits(fork_W, collector, *, target_node_names) -> int`

内部構造の第一候補：

- `_resolve_and_validate_target_nodes`
- `_build_snapshot_visit_registration_plan`
- `register_snapshot_fixed_visits`

A用とB用の小関数を過度に分割せず、登録計画構築処理内で明示的なforループとして記述する方針とする。

collector本体へ追加しない理由：

- collectorはUXsimオブジェクトに依存しない純粋な記録層
- snapshot固定集合構築はVehicle、Node、Link、Worldの状態を読むUXsim依存処理
- 責任を分離する必要がある

`uxsim.py`本体へ埋め込まない理由：

- TVT研究用のsnapshot構築ロジックをUXsim本体へ過度に混在させない
- 将来の二段階観測driverから独立して再利用できるようにする

#### 25.22.15 実装時に必要なテスト

新規候補：

- `tests_order_control_baseline_snapshot.py`

少なくとも次を検証予定とする：

- 空の対象Node名一覧
- 重複Node名
- 非文字列・空文字列
- 存在しないNode
- 非eligible Node
- `fcfs`、`batch`、`none` Nodeの拒否
- Aのみ
- Bのみ
- 同一NodeにAとB
- 複数inlink
- 複数time_value Node
- Aがincomingとinlinkの両方に存在しても1件だけ登録
- A未検出の到着済みinlink Vehicleを重大不整合として拒否
- current visit欠落
- visit ID不一致
- Node不一致
- inlink不一致
- arrival情報片側欠落
- Aのroute_next_link欠落
- Aのroute_next_link.start_node不一致
- 正常な対象外Vehicleの除外
- `participates_in_order_exchange=False`のVehicleも固定集合へ含む
- 全候補検証失敗時にcollectorが空のまま
- timestep T到着VehicleがBとして登録される
- timestep T処理後にbaseline_arrival_timestepがTになる
- timestep T処理後にW.TがT+1になる
- 登録後に固定集合外Vehicleが後からinlinkへ入ってもcollectorへ追加されない

#### 25.22.16 小規模実測結果

今回の一時的な標準入力Python診断（Terminalで実行。既存テストヘルパをimportし、ファイル変更なし）について記録する。

実測で確認できた事項：

- timesteps 0から9を処理後、`W.T == 10`
- この時点でtimestep 10は未処理
- timestep 10を1回処理後、`W.T == 11`
- timestep 10で到着したVehicleは、到着直後にincomingとinlinkの両方に存在
- baseline snapshotでBとして登録したVehicleの`baseline_arrival_timestep == 10`
- `was_arrived_at_snapshot is False`
- 通過を阻止した次timestep後も、正常なexec終了時にはVehicleがincomingへ再追加された
- そのためinlink-only Aにはならなかった
- 診断中の最初の容量カウンターだけによる通過阻止は、timestep更新で容量が回復して失敗した
- その後、outlink入口をVehicleで物理的に塞ぐ診断へ修正した
- 最終実測結果はAのincoming再登録とBのtimestep T到着記録を支持した
- 標準入力スクリプトのみを使い、ファイル変更は行っていない
- 実行後のGit状態は未追跡の`diagnostics/order_control.zip`だけ

#### 25.22.17 未実装事項

- `uxsim/order_control_baseline_snapshot.py`
- `register_snapshot_fixed_visits`
- snapshot固定集合構築の単体テスト
- 小規模fork診断の恒久ファイル
- real_Wからfork_Wを作りcollectorを設定する正式driver
- 二段階観測driver
- right_of_entry_vehicle選定
- TVT制度処理
- Node別制度状態
- 早期終了
- 通過順位
- 支払い・補償
- 性能測定

#### 25.22.18 次の作業

次の作業は、本節の設計に従って次を実装する。

- `uxsim/order_control_baseline_snapshot.py`
- `register_snapshot_fixed_visits`
- 対象Nodeの事前検証
- A/B登録予定データの構築
- 全候補検証後のcollector登録
- `tests_order_control_baseline_snapshot.py`
- timestep T到着境界テスト

まだ実装へ着手済みではない。

### 25.23 snapshot固定集合構築補助処理の実装結果

記録日：2026-08-28

本節は、§25.22の実装前設計に従って実装した結果、慎重な欠陥探索レビュー、レビュー後の修正、およびTerminalでの最終確認を記録する。§25.22は実装前設計として残す。

#### 25.23.1 実装した範囲

- 新規作成：`uxsim/order_control_baseline_snapshot.py`
- 新規作成：`tests_order_control_baseline_snapshot.py`
- 既存ファイルは変更していない
- 公開関数：`register_snapshot_fixed_visits(fork_W, collector, *, target_node_names) -> int`
- TVT対象Nodeの一括事前検証
- snapshot時点で到着済みのVehicleの抽出・検証
- snapshot時点で未到着のVehicleの抽出・検証
- 全候補検証後のcollector登録
- 同一Vehicleの重複検出
- 正常な対象外Vehicleの除外
- timestep T到着境界テスト

#### 25.23.2 公開関数の責任

`register_snapshot_fixed_visits()`が担当すること：

- fork Worldの現在状態をsnapshotとして読む
- 渡されたTVT対象Node名を検証する
- 到着済み・未到着の固定visit登録予定データを作る
- 登録予定データをcollectorの正式validationで全件事前確認する
- 全検証成功後に実collectorへ登録する
- 総登録件数をintで返す

担当しないこと：

- real_Wのcopy
- fork baselineで実際に使用するcollectorの作成とforkへの設定
- forkの仮想進行
- 二段階観測
- right_of_entry_vehicle選定
- TVT制度処理
- 早期終了
- 支払い・補償
- Node別制度状態
- 分析ログ

#### 25.23.3 対象Nodeの事前検証

実装した検証：

- `target_node_names`が文字列単体ではなく、Node名の反復可能な集合である
- 空集合を拒否
- 非文字列を拒否
- 空文字列を拒否
- Node名重複を拒否
- `fork_W.get_node(node_name)`を正式なNode取得経路として使用
- 存在しないNode名を、元例外をcauseとして保持したValueErrorへ変換
- `order_control_eligible=True`を必須とする
- `order_control_type="time_value"`を必須とする
- `none`、`fcfs`、`batch`を拒否
- 全Nodeの検証後にVehicle候補調査へ進む

Node名は、time_value設定時に得たNode一覧から一度だけ作り、forkへ引き継ぐ設計である。

#### 25.23.4 get_node例外変換のレビュー後修正

初回実装では、`fork_W.get_node()`が送出するすべてのExceptionを、Node不存在を表すValueErrorへ変換していた。

慎重な欠陥探索レビューで、Node不存在以外の内部障害まで誤ってNode不存在と表示する可能性を検出した。

最終実装では次のように修正した：

- 現行`World.get_node()`がNode不存在時に生成するメッセージと元例外メッセージを比較する
- Node不存在メッセージと一致する場合だけValueErrorへ変換する
- 元例外を`__cause__`として保持する
- Node不存在以外の予期しない例外は、元の型とメッセージのまま再送出する
- テストでは、存在しないNode名のcause保持と、予期しないRuntimeErrorの非変換を確認した

#### 25.23.5 到着済みVehicleの処理

到着済みVehicleは、各対象Nodeの`incoming_vehicles`から抽出する。

主な確認内容：

- `state=="run"`
- current visitが存在
- 必須キーが存在
- visit IDがboolではない正のint
- current visitのvisit IDとVehicleのvisit IDが一致
- current visitのNodeが対象Node
- current visitのinlinkが対象Nodeのinlink
- Vehicleの現在Linkがcurrent visitのinlink
- Vehicleがそのinlinkの`vehicles`にも存在
- arrival_timeとarrival_tiebreakerが両方存在
- route_next_linkが存在
- route_next_linkが対象Nodeから始まる
- 到着timestepがsnapshotのTより前

登録値として、§25.22で定めた10項目を設定する。

通常の`exec_simulation()`経路だけでVehicleを対象Nodeへ到着させ、到着済みVehicleとして登録する統合テストを追加した。Terminalで新規モジュール全体とA処理を確認した。

このテストでは次を確認している：

- Vehicleは`incoming_vehicles`と元の`inlink.vehicles`の両方に存在
- current visitの到着情報が設定済み
- `was_arrived_at_snapshot is True`
- baseline到着timestepが実際の到着timestepと一致
- `route_next_link_name`が正しい
- 登録件数は1件
- `record_order_control_node_arrival()`をテストから直接呼ばず、通常のUXsim実行経路を使用

#### 25.23.6 未到着Vehicleの処理

未到着Vehicleは、各対象Nodeの各`inlink.vehicles`をFIFO順に走査して抽出する。

主な確認内容：

- `state=="run"`
- Vehicleの現在Linkが走査中inlink
- current visitが存在
- 必須キーが存在
- visit IDが正しい
- current visitのNodeが対象Node
- current visitのinlinkが走査中inlink
- arrival_timeとarrival_tiebreakerが両方None
- 対象Nodeのincoming_vehiclesには存在しない

登録時には、snapshot時点のroute_next_linkを保存せず、次をNoneとする：

- baseline_arrival_timestep
- arrival_tiebreaker
- route_next_link_name
- baseline_passage_timestep

#### 25.23.7 正常な対象外Vehicle

次を固定集合から正常に除外する：

- `state=="end"`
- `state=="abort"`
- trip-end待ち
- taxi mode
- specified_routeあり

`participates_in_order_exchange=False`は除外せず、交通予測のため固定集合へ含める。

#### 25.23.8 全候補検証後の登録

最終実装では、次の三段階になった。

第1段階：

- 全対象Nodeを検証
- 全到着済み・未到着候補を検証
- 登録予定dictのlistを構築
- 同一Vehicle重複を検出
- 実collectorは変更しない

第2段階：

- 空の一時的な`OrderControlBaselineCollector`を作る
- 登録予定データを一時collectorへ全件登録する
- collector自身の正式な`register_snapshot_visit()` validationを全件通過するか確認する
- 失敗した場合は例外をそのまま伝播し、実collectorは変更しない
- 一時collectorのprivate索引は参照しない

第3段階：

- 一時collectorへの全件登録が成功した場合だけ、同じ登録予定データを実collectorへ登録する

その他：

- snapshot側へcollectorの型validationを全面複製していない
- 一時collectorの内容を実collectorへコピーしていない
- 実collectorへの登録には元のregistration planを使用する
- registration planはcollectorの引数名に対応するプレーンdict
- 専用dataclassは追加していない

#### 25.23.9 部分登録リスクのレビュー後修正

慎重な欠陥探索レビューで、初回実装には次の問題があった：

- registration planの後半にcollectorが拒否する値がある場合、実collectorへの前半登録だけが残る可能性があった

具体的な確認テスト：

- 1件目は正常な到着済みVehicle
- 2件目は`arrival_tiebreaker=True`
- snapshot側では登録予定データまで作成できる
- collectorはboolのarrival_tiebreakerを拒否する
- 一時collectorで失敗する
- 実collectorには1件目を含め何も登録されない

修正後は、registration planに起因するcollector validation失敗では、実collectorが変更されない。

#### 25.23.10 同一Vehicleの重複管理

最終実装の2構造：

`arrived_vehicle_names`

- `incoming_vehicles`から到着済みとして登録予定へ追加したVehicle名だけを保持
- 同じNode、同じvisit、同じinlinkの走査で再び見つかった到着済みVehicleを、未到着として二重登録しないために使う
- 未到着Vehicleは追加しない

`vehicle_name_to_planned_visit`

- 到着済み・未到着の両方を含む全登録予定Vehicleを管理
- Node名、visit ID、inlink名を保持
- 全対象Nodeを通じた重複検出に使用

実装確認経緯：

- 初回実装では、未到着Vehicleまで`arrived_vehicle_names`へ加えていた
- Terminal確認で、変数名と役割の不一致、および別Node重複を黙ってスキップする可能性を検出した
- 修正後は役割を分離した
- 同じNode、同じvisit、同じinlinkのA再出現だけを正常にスキップ
- 別Node、別visit、別inlinkでの再出現はValueError
- incoming_vehicles内の同一Vehicle重複もValueError
- Bの別Node再出現は`arrived_vehicle_names`によって黙ってスキップされず、人工的な異常状態テストではLink不一致により停止した
- このLink不一致は重複検出より直接的な物理状態不整合であり、正常な停止である

#### 25.23.11 内部ヘルパー

少なくとも次の内部処理と役割を持つ：

- `_resolve_and_validate_target_nodes`：対象Node名全体の検証とNode取得
- `_build_snapshot_visit_registration_plan`：到着済み・未到着の登録予定全体を構築
- `_ordered_inlinks_for_node`：`Node.inlinks`の挿入順でinlinkを返す
- `_should_skip_non_fixed_set_vehicle`：正常な研究対象外Vehicleの判定
- `_record_planned_vehicle_name`：全登録予定Vehicleの重複検出
- `_handle_arrived_vehicle_name_seen_on_inlink`：到着済みVehicleの正常な二重コンテナ出現と異常な再出現を区別
- current visit、visit ID、arrival情報の小さな検証ヘルパー
- 到着済み・未到着の登録予定dictを作る処理

ヘルパー数が増えたが、Node検証、重複管理、current visit検証などの異なる責任を明確にするためであり、制度処理を抽象化したものではない。正しく動くことを最優先とし、その範囲で研究者が後からA/B分類、検証、重複防止、登録順序を理解しやすい可読性を優先した。

#### 25.23.12 登録順序と戻り値

登録予定データの順序：

1. `target_node_names`の入力順
2. 各Nodeで到着済みVehicleを先に調査
3. `Node.inlinks`の既存挿入順
4. 各inlink内では`inlink.vehicles`のFIFO順

この順序に到着順位、通過順位、trade_rankなどの制度上の意味を持たせない。

戻り値は、登録した固定visitの総件数intである。

#### 25.23.13 timestep T境界

次のテストがTerminalで成功した：

- snapshot時点の`fork_W.T == 10`
- timestep 10は未処理
- Vehicleのarrival情報はNone
- 未到着Vehicleとして登録
- timestep 10を通常の`exec_simulation()`で1回処理
- 実行後`fork_W.T == 11`
- `baseline_arrival_timestep == 10`
- `was_arrived_at_snapshot is False`

`record_order_control_node_arrival()`をテストから直接呼ばず、通常のUXsim実行経路を使った。

#### 25.23.14 単体テスト

`tests_order_control_baseline_snapshot.py`には、最終的に59件のテストがある。

Terminalで次を確認した：

- `grep -c '^def test_'`の結果が59
- `grep -c '^    test_.*,$'`の結果が59
- 重複したテスト関数名は存在しない

過去の途中時点または報告誤りとして54件、55件が記録されていたが、最終件数は59件である。

主な試験分類：

- 対象Node入力検証
- Node不存在のcause保持
- 予期しないget_node例外の非変換
- 到着済みVehicle
- 通常exec経路での到着済みVehicle
- 未到着Vehicle
- A/B組合せ
- 複数inlink
- 複数time_value Node
- 正常な到着済みVehicleの二重コンテナ出現
- 別Node・別visit・別inlinkの異常な再出現
- Bの別Node再出現を黙ってスキップしないこと
- incoming内の重複
- current visit不整合
- arrival情報不整合
- route_next_link不整合
- 正常な対象外Vehicle
- `participates_in_order_exchange=False`の包含
- Vehicle検証失敗時に実collectorが空
- collector正式validation失敗時に実collectorが空
- timestep T境界
- 登録後の固定集合不変

#### 25.23.15 Terminal確認結果

次をTerminalで直接実行し、すべて成功した：

- `python tests_order_control_baseline_snapshot.py`：成功、59 tests
- `python tests_order_control_baseline_collector.py`：成功
- `python tests_order_control_baseline_collector_uxsim.py`：成功
- `python tests_order_control_rng.py`：成功
- `python tests_order_control_current_visit_state.py`：成功
- `python tests_order_control_current_visit_arrival.py`：成功
- `python tests_order_control_batch_revisit_integration.py`：成功
- `python tests_order_control_batch_t_trigger_level_2_body.py`：成功、22 tests
- `python -m py_compile uxsim/order_control_baseline_snapshot.py tests_order_control_baseline_snapshot.py uxsim/order_control_baseline_collector.py uxsim/uxsim.py`：成功
- `git diff --check`：問題なし
- 新規2ファイルの`git diff --no-index --check`：問題なし
- テスト関数数59
- TESTS一覧数59
- 重複テスト名なし

新規モジュール全体、A/B処理、重複管理、追加テスト、テスト件数、全指定テスト、構文、形式をTerminalで確認した。

#### 25.23.16 非空collectorに関する制約

- 初期実装は、freshな空collectorに対して一度だけ呼ぶことを前提とする
- collectorが空かどうかを調べる公開APIは現在ない
- snapshot補助処理からcollectorのprivate索引を直接参照していない
- registration planに起因するcollector validation失敗は、一時collectorによって実collector登録前に検出する
- 非空collectorや外部から差し替えられたcollector実装に固有の失敗については、実collector登録の原子性を保証しない
- rollbackは実装していない
- この呼出規約は正式driver実装時にも維持する必要がある

#### 25.23.17 慎重な欠陥探索レビューの結果

通常の実装報告とテスト確認の後に、改めて欠陥を探す目的のレビューを実施した。

レビュー結果：

- Critical：0件
- Major相当：2件
- Minor：8件

Major相当として検出・修正したもの：

1. collector正式validationの途中失敗による実collector部分登録の可能性
2. `get_node()`の予期しない例外までNode不存在に誤変換する問題

修正後、Terminalでコードと追加テストを確認し、全指定テストを再実行して成功した。

Minor指摘のうち、今回対応しなかったもの：

- `np.str_` Node名対応
- 異常なTまたはDELTATの追加validation
- 壊れたcurrent visit値に対する型検証の全面追加
- 同名別Nodeまたは同名別Linkへの過剰な防御

これらは、正常なWorld生成や登録時保証へ委ねるか、正式driver設計時に必要性を再評価する。

#### 25.23.18 今回実装していないもの

- real_W.copy()を行う正式driver
- fork側へcollectorを設定する正式driver
- 小規模fork診断の恒久ファイル
- 二段階観測driver
- T+6意思決定窓
- right_of_entry_vehicle選定
- right_of_entry_vehicle通過待ち
- TVT候補確定
- 到着順位
- 確定順位ブロック
- trade_rank
- 買い手・売り手選定
- 支払い・補償
- Node別制度状態
- 早期終了
- 通過順位
- 長期ログ
- real_Wへのbaseline結果保存
- 性能最適化

#### 25.23.19 完了判断と次の作業

- §25.22で予定したsnapshot固定集合構築補助処理と単体テストは実装済み
- 初回実装後に慎重な欠陥探索レビューを実施した
- Major相当2件を修正した
- Terminalでコード、重複管理、一時collector、例外変換、59件のテスト、既存テスト、構文、形式を確認済み
- コード上の実装は完了と判断する
- 実装結果と再レビュー結果を整理したうえで本§25.23と進捗メモを更新したため、メモ更新を含む完了条件を満たした
- 本記録時点では未コミット・未push

次の作業は、次の小規模fork診断または最小driverの検討である：

- real_Wを作成してtimestep Tまで進める
- T処理開始前にfork_Wを作る
- fork側だけcollectorを設定する
- time_value設定時に得たNode名一覧を渡す
- `register_snapshot_fixed_visits()`を実行する
- forkを数timestep進める
- 到着・通過記録を確認する
- real_W不変を確認する
- 固定集合外Vehicleがcollectorへ追加されないことを確認する

これは、§25.15で便宜的に第3回実装相当としていた残りの作業である。

二段階観測やTVT制度処理は、その後の別作業である。

### 25.24 snapshot固定集合の小規模fork統合診断

記録日：2026-08-29

#### 25.24.1 診断の位置づけ

- 新規作成：`diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`
- 回帰テストではなく、正式driver実装前の恒久的な統合診断
- real_Wからfork_Wを作る
- fork側だけcollectorを設定する
- `register_snapshot_fixed_visits()`でsnapshot固定集合を登録する
- fork側だけを進める
- baseline到着・通過通知を確認する
- 固定集合外Vehicleの到着・通過通知がcollectorに無視されることを確認する
- real_W不変と参照分離を確認する
- TVT制度処理そのものは実装・再現しない

実行方法：

```text
python diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py
```

#### 25.24.2 小規模World

- 構成：`orig --[in]--> junction --[out]--> dest`
- `junction`はVehicleの目的地ではない
- 単車線
- `in`と`out`はそれぞれ長さ200、自由流速度20
- `deltan=1`
- `DELTAT=1`
- `tmax=100`
- `random_seed=0`
- junctionは作成時にeligibleかつ`order_control_type="none"`
- その後`set_order_control_for_nodes()`で`time_value`へ設定

#### 25.24.3 TVT対象Node一覧の引継ぎ

- `set_order_control_for_nodes()`の戻り値を`configured_tvt_nodes`として受け取る
- その戻り値から`tvt_target_node_names`を一度だけ作る
- 同じNode集合を人が二度入力しない
- real_WのNodeオブジェクトをfork_Wへ渡さない
- Node名一覧を`register_snapshot_fixed_visits()`へ渡す
- fork側ではfork自身のNodeを取得する

#### 25.24.4 snapshot時点

- `SNAPSHOT_T = 20`
- real_Wをtimestep 0から19まで処理
- snapshot時点では`real_W.T == 20`
- timestep 20は未処理
- copy直後も`fork_W.T == 20`
- `W.T == T - 1`という解釈は採用しない

#### 25.24.5 Vehicle構成

- `arrived_fixed_vehicle`
  - 出発時刻0
  - snapshot時点で到着済み・未通過
  - 固定集合へ含む
- `not_yet_arrived_fixed_vehicle`
  - 出発時刻11
  - snapshot時点でinlink上・未到着
  - 固定集合へ含む
- `outside_fixed_vehicle`
  - snapshot登録後、fork側だけへ追加
  - 固定集合へ含めない
- `outlink_blocker`
  - 到着済みVehicleをsnapshotまで未通過に保つ診断専用補助Vehicle
  - 固定集合へ含めない

#### 25.24.6 到着済みVehicle

snapshot時点で次を確認した：

- `incoming_vehicles`に存在
- `in.vehicles`にも存在
- current visitのNodeはjunction
- current visitのinlinkはin
- arrival_timeとarrival_tiebreakerは設定済み
- route_next_linkはout
- arrival timestepは10
- snapshot T=20より前
- まだjunctionを通過していない

登録後とfork進行後のcollector結果：

- `was_arrived_at_snapshot is True`
- `baseline_arrival_timestep == 10`
- `baseline_passage_timestep == 21`

#### 25.24.7 未到着Vehicle

snapshot時点で次を確認した：

- `in.vehicles`に存在
- `incoming_vehicles`には存在しない
- current visitのNodeはjunction
- current visitのinlinkはin
- arrival_timeとarrival_tiebreakerはNone
- snapshot固定集合へ未到着Vehicleとして登録

fork進行後のcollector結果：

- `was_arrived_at_snapshot is False`
- `baseline_arrival_timestep == 21`
- `baseline_passage_timestep == 22`

timestepの説明：

- snapshotは`W.T==20`でtimestep 20未処理
- forkの1 step目でtimestep 20を処理
- timestep 21の処理中にbaseline arrival timestep 21を記録
- timestep 22にbaseline passageを記録

#### 25.24.8 snapshot固定集合登録

- fork側のみへfreshな`OrderControlBaselineCollector`を設定
- real_WのcollectorはNoneのまま
- `register_snapshot_fixed_visits()`を1回だけ実行
- Node名一覧はtime_value設定結果から得た一覧をそのまま使用
- 登録件数は2
- 登録対象は到着済みVehicleと未到着Vehicle
- ブロッカーと固定集合外Vehicleは登録されない
- collectorの公開APIだけで結果を確認
- collectorはWorldへの逆参照を持たない

#### 25.24.9 ブロッカー初期実装の問題

初回実装には次の問題があった：

- `state=="run"`なのに`VEHICLES_RUNNING`へ登録されていなかった
- `carfollow()`を受けず、`Vehicle.update()`だけを受けていた
- 解除時に`x`と`x_old`だけを終端へ移し、`x_next`を更新していなかった
- 不整合な状態による一時的な入口開放を利用して診断が成功した可能性があった

この初期方式は採用しない。

#### 25.24.10 最終ブロッカー方式

最終方式：

- 診断専用にoutlink入口へ手動配置するrun Vehicle
- `W.VEHICLES`に存在
- `W.VEHICLES_LIVING`に存在
- `W.VEHICLES_RUNNING`に存在
- `outlink.vehicles`に存在
- `state=="run"`
- `link is outlink`
- `x`、`x_old`、`x_next`、`v`、`move_remain`を0にする
- 通常の`carfollow()`と`Vehicle.update()`を受ける
- `Vehicle.update()`末尾の診断用`user_function`で入口位置へ戻す
- fork作成後、fork側だけ`user_function=None`として固定を解除
- 瞬間移動は行わない
- 解除後は通常の`carfollow()`と`update()`で前進
- 診断終了時には正常にtrip-endし、`state=="end"`となった
- `VEHICLES_RUNNING`と`VEHICLES_LIVING`から削除済み
- `link is None`

#### 25.24.11 ブロッカー方式の限界

- ブロッカーは診断専用の人工配置
- 通常の`Node.generate()`や`Node.transfer()`によるLink進入ではない
- Linkの`cum_arrival`、`vehicles_enter_log`、`capacity_in_remain`などを標準進入と同一に再現するものではない
- Aをsnapshotまで未通過に保つための診断補助
- 正式driverの処理ではない
- `outlink.u=0`は`set_traveltime_instant()`の除算で問題になるため採用しなかった

#### 25.24.12 固定集合外Vehicle

- snapshot固定集合登録後にfork側だけへ追加
- real_Wには存在しない
- 通常のUXsim経路でinlinkへ進入
- current visitを通常経路で作成
- junctionへ通常経路で到着
- junctionを通常経路で通過
- current visitやarrival情報を診断側で直接書き換えていない
- inlink進入を確認
- 対象Node到着を確認
- 対象Node通過を確認
- 到着timestepは30
- 到着直後に主キーでcollector recordがNone
- 通過直後にも主キーでcollector recordがNone
- Node別exportにVehicle名が存在しない
- Node別export件数は2件のまま
- 到着通知と通過通知が固定集合外Vehicleを無言で無視した

#### 25.24.13 fixed set外確認のレビュー後補強

慎重な欠陥探索レビューで、初回診断はoutside Vehicleがinlinkへ入っただけで成功していた。

その状態では次を未確認だった：

- 対象Node到着通知の無視
- 対象Node通過通知の無視

レビュー後に次を追加した：

- inlink進入、Node到着、Node通過を別々に履歴管理
- 到着直後の主キーrecord不存在確認
- 通過直後の主キーrecord不存在確認
- Node別exportの名前不存在と件数不変
- これらすべてをfork loop終了条件へ追加
- fork進行は3 stepから12 stepへ延長
- 最終`fork_W.T == 32`

#### 25.24.14 fork進行

- fork側だけを1 timestepずつ進める
- `MAX_FORK_STEPS=30`
- 実際は12 stepで完了
- 最終`fork_W.T == 32`
- 上限未達時はVehicle状態、collector状態、outside進捗を含むAssertionError
- 無限loopにはしない

終了条件：

- Aのbaseline passage記録済み
- Bのbaseline arrival記録済み
- Bのbaseline passage記録済み
- outsideのinlink進入済み
- outsideの対象Node到着済み
- outsideの対象Node通過済み
- outside到着後のcollector非登録確認済み
- outside通過後のcollector非登録確認済み
- Node別export件数不変

#### 25.24.15 real_W不変

比較項目：

World：

- T
- TIME
- W.rng状態
- W.order_control_rng状態
- collectorがNone

Vehicle：

- state
- link名
- x
- link_arrival_time
- order_control_visit_id
- current visit要点
- `has_user_function`
- ブロッカーについては`x_old`、`x_next`、`v`、`move_remain`

Node：

- junctionのincoming Vehicle名

Link：

- inとoutのVehicle名順
- outlink速度

次を確認した：

- fork作成直前とfork進行完了後のreal_W snapshotが完全一致
- real_Wをfork作成後に進めていない
- outside Vehicleをreal_Wへ追加していない
- real_W側ブロッカーのuser_functionは残った
- `real_world_unchanged is True`

#### 25.24.16 参照分離

次を確認した：

- real_Wとfork_Wは別オブジェクト
- junction Nodeは別オブジェクト
- in Linkとout Linkは別オブジェクト
- 到着済みVehicleは別オブジェクト
- 未到着Vehicleは別オブジェクト
- ブロッカーは別オブジェクト
- fork Vehicleのlinkはfork側Link
- fork current visitのNodeとinlinkはfork側オブジェクト
- fork側だけcollectorを保持
- collectorはWorldへの逆参照を持たない
- `reference_independence is True`

#### 25.24.17 最終実行結果

最終出力の要点：

- `snapshot_timestep = 20`
- `registered_visit_count = 2`
- A arrival = 10
- A passage = 21
- B arrival = 21
- B passage = 22
- outside entered inlink = True
- outside arrived at target node = True
- outside passed target node = True
- outside arrival timestep = 30
- outside recorded = False
- real_W unchanged = True
- reference independence = True
- blocker state = end
- blocker managed consistently = True
- real outlink speed unchanged = True
- final fork timestep = 32
- fork steps executed = 12
- 最終メッセージ：`TVT baseline snapshot fork probe passed.`

#### 25.24.18 関連テストと形式確認

Terminalで次が成功した：

- `python diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`
- `python tests_order_control_baseline_snapshot.py`（59件）
- `python tests_order_control_baseline_collector.py`
- `python tests_order_control_baseline_collector_uxsim.py`
- `python -m py_compile diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py uxsim/order_control_baseline_snapshot.py uxsim/order_control_baseline_collector.py uxsim/uxsim.py`
- `git diff --check`
- 新規診断ファイルの`git diff --no-index --check`

#### 25.24.19 慎重な再レビュー

診断実装後に、欠陥を探す目的の再レビューを複数回実施した。

レビューで確認した主な問題：

- 初期ブロッカーのVehicle管理不整合
- 解除時の`x_next`不整合
- outside Vehicleがinlinkへ入っただけで成功していた
- outsideの到着・通過通知無視を実際には確認していなかった
- 成功出力の一部boolが固定値だった
- timestepコメントが不正確だった
- real_W側user_function保持確認がなかった

これらを修正または補強し、Terminalで診断・ブロッカー管理・outside Vehicleの到着・通過・collector非登録・real_W不変・参照分離・関連テスト・構文・形式を再確認して成功した。

正しく動くことを最優先とし、その範囲で処理順序を後から理解しやすい実装を優先した。

#### 25.24.20 この診断で確認できないこと

次は未確認である：

- 複数time_value Node
- 制御方式の混在
- 大規模需要
- 長時間進行
- 性能
- 二段階観測
- T+6意思決定窓
- right_of_entry_vehicle選定
- TVT候補確定
- 到着順位
- 確定順位ブロック
- trade_rank
- 買い手・売り手選定
- 支払い・補償
- Node別制度状態
- 早期終了
- 通過順位

#### 25.24.21 完了判断と次の作業

- 小規模fork統合診断は実装済み
- 初期実装後に複数回の慎重な再レビューを実施
- 指摘された主要な不足を修正済み
- Terminalで診断と関連テストを最終確認済み
- 恒久診断として完了と判断した
- 本記録時点では診断ファイルとメモ更新は未コミット・未push

次の作業は、今回の診断結果を踏まえた正式driver構造の設計である。直ちに二段階観測やTVT制度処理全体へ進むわけではない。まず次を検討する：

- real_Wからfork_Wを作る責任
- fresh collectorを作りforkへ設定する責任
- Node名一覧を渡す責任
- `register_snapshot_fixed_visits()`を呼ぶ責任
- fork進行の開始・終了条件
- baseline結果を次の処理へ渡す方法
- real_W不変確認を本番driverでどこまで行うか

**2026-08-31更新：** 上記「次の作業」として列挙されていた正式driver構造の設計を **§25.25** に記録した。正式driverの Python 実装はまだ開始していない。詳細は §25.25 を参照する。

### 25.25 正式全World baseline driverの実装前設計

記録日：2026-08-31

本節を、初期正式driverの最新方針の正本とする。

#### 25.25.1 位置づけ

- snapshot固定集合collectorは実装済みである。
- UXsimの到着・通過通知接続は実装済みである。
- snapshot固定集合構築補助処理（`register_snapshot_fixed_visits()`）は実装済みである。
- 小規模fork統合診断（`diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`）は実装・確認済みである。
- 今回記録するのは、これらを正式な全World baseline入口へ接続する **driver** の実装前設計である。
- 正式driverのコードと専用テストは未実装である。
- 本節はコミット `d3bb306` を出発点として整理した。
- `d3bb306` は origin へ push 済みである。
- 今回の設計メモ更新は未コミット・未 push である。

#### 25.25.2 初期正式driverの目的

正式driverは、本物の交通世界を変えずに、複製した交通世界だけを指定された長さだけ進め、TVTを行わなかった場合の到着・通過の事実を集める入口である。指定した観察時間を正常に進めても、すべての交通情報が得られるとは限らない。情報が得られなかったことは装置の故障ではなく、取得できなかった事実として後続処理へ渡す。正式driverは順位確定やTVT形成を行わない。

技術的な目的は次のとおりである。

- `real_W` を変更しない。
- `real_W` を copy して `fork_W` を作る。
- `fork_W` だけへ fresh collector を設定する。
- snapshot固定集合を登録する。
- 呼出側が指定した baseline horizon だけ `fork_W` を進める。
- TVTなし baseline の到着・進行先・通過情報を collector へ記録する。
- collector と実行メタデータを結果として返す。
- `fork_W` 自体は返さない。
- 正式driverは TVT 制度処理を行わない。

#### 25.25.3 初期版の実行方式

snapshot固定集合が 1 件以上ある場合、初期正式driverは **固定 horizon を一括実行** する。

概念上の実行は次のとおりである。

```python
fork_W.exec_simulation(
    duration_t2=baseline_horizon_steps * fork_W.DELTAT
)
```

これは設計上の概念例であり、本節の記録時点では Python 実装ではない。

- `baseline_horizon_steps` は **観測長** である。
- 全件情報取得まで進める処理の **最大上限** という意味ではない。
- horizon 50 は現在の検討中心であり、正式な固定値ではない。
- driver 内部へ 50 を埋め込まない。
- Node 別状態を毎 timestep 判定しない。
- 初期版では全 Node 完了による早期終了を実行しない（早期終了の詳細は §24.13 を参照。本節では変更しない）。
- 指定 horizon の一括実行後に collector を後続へ渡す。
- 一括実行後、実際に指定 step 数進んだことを確認する。
- 一括実行は World 終端へ到達しない範囲で行う。
- World 終端時の Analyzer 終了集計を baseline driver へ持ち込まない。

詳細は §25.25.11 を参照する。

事後確認条件：

```text
fork_W.T_after == fork_W.T_before + baseline_horizon_steps
```

#### 25.25.4 `baseline_horizon_steps`

- 公開引数名の第一候補は `baseline_horizon_steps` である。
- `bool` ではない `int` である。
- 1 以上である。
- 0 または負数は不正である。
- 上限は初期 driver 内に固定しない。
- 感度分析によって異なる値を指定できる。
- horizon 不足時に自動短縮しない。

空固定集合の 0 step 正常終了は、引数として horizon 0 を許可することとは別である。

#### 25.25.5 対象Node名一覧

- `target_node_names` は time_value 設定時に得た Node 集合から **一度だけ** 作る。
- 同じ Node 集合を人が再入力しない。
- driver 内部で `tuple` へ一度だけ固定する。
- 登録と終了時件数確認に同じ `tuple` を使う。
- 初期 driver の入力型第一候補は `list` または `tuple` である。
- `str`、`bytes`、`set`、その他の一般 `Iterable` を初期 driver では受け付けない第一候補とする。
- Node 名の存在、重複、空文字、eligibility、time_value 設定は snapshot 補助処理へ委譲する。
- 登録時に保証済みの検証を driver で重複実装しない。

#### 25.25.6 real_Wの入口条件と不変確認

**入口条件：**

- `real_W._order_control_baseline_collector` は `None` であることを要求する第一候補とする。
- `real_W` へ collector を設定しない。

**呼出前に保存する軽量情報：**

- `real_W.T`
- `real_W.TIME`
- `real_W._order_control_baseline_collector`

正常終了時に、これらが変化していないことを確認する。

詳細な RNG、全 Vehicle、全 Node、全 Link の比較は、既存小規模 fork 診断と driver 専用テストの責任とする。

公開引数 `verify_real_world_unchanged` は初期 API へ追加しない。

#### 25.25.7 fork作成とcollector設定

1. baseline 開始 timestep として `real_W.T` を保存する。
2. `fork_W = real_W.copy()` を実行する。
3. copy 直後の `fork_W.T` が baseline 開始 timestep と一致することを確認する。
4. copy 直後の fork collector が `None` であることを確認する。
5. fresh な `OrderControlBaselineCollector` を作る。
6. `fork_W` だけへ collector を設定する。
7. `real_W` の collector は `None` のままとする。

`fork_W` は可変な内部状態であり、正式結果として返さない。

#### 25.25.8 snapshot固定集合登録

- `register_snapshot_fixed_visits()` を fork 進行前に 1 回だけ呼ぶ。
- fresh な空 collector へ登録する。
- 時刻 T の snapshot 状態を読む。
- `fork_W.T == T` であり、timestep T はまだ処理されていない。
- Node 名一覧は time_value 設定結果から得たものを使用する。
- snapshot 固定集合外 Vehicle は後から追加しない。
- collector が固定集合外通知を無視する既存仕様を維持する。
- 登録件数を `registered_visit_count` として保存する。

既存 `order_control_baseline_snapshot.py` の docstring は、本記録時点ではコード変更しない。

推奨呼出順：

```text
real_Wを時刻Tまで通常実行
→ real_W.TはTで、timestep Tは未処理
→ real_W.copy()
→ fork_Wのsnapshot固定集合を登録
→ baseline forwardを開始
```

docstring の「`after fork_W.exec_simulation()` returns normally」が、上記の `real_W` 側通常実行後の状態を指す可能性がある。docstring の明確化要否は、将来のコード修正候補として残す。

#### 25.25.9 登録件数の整合確認

collector 公開 API を用いて、対象 Node 別 export 件数の合計を確認する。

概念：

```python
sum(
    len(collector.export_node_baseline_visits(node_name))
    for node_name in target_node_names
)
```

確認時点：

1. snapshot 登録直後
2. fixed horizon 終了後、または空固定集合による 0 step 終了時

毎 timestep の件数確認は初期版では行わない。

理由：

- 固定集合の登録は snapshot 時の 1 回だけである。
- 固定集合外通知は collector で無視される。
- 毎 timestep 確認する必要性が低い。
- 余計な実行負荷を避ける。

登録件数と export 合計が一致しなければ重大な実行不整合とする。

#### 25.25.10 空のsnapshot固定集合

- `registered_visit_count == 0` は正常に起こり得る。
- snapshot 固定集合は baseline 開始時点ですでに対象 inlink 上にいる Vehicle に限定される（§24.4）。
- baseline 開始後に対象 inlink へ入った Vehicle は今回の固定集合へ追加しない。
- 登録件数 0 なら、今回記録する対象 Vehicle は存在しない。
- horizon を進めても collector の対象は増えない。
- この場合、余白検査を行わない。
- fork forward を行わない。
- `fork_steps_executed = 0`
- `final_fork_timestep = baseline_timestep_T`
- 正常結果を返す。
- これは情報不足や Node 未解決とは区別する。

引数 `baseline_horizon_steps` 自体は、空固定集合の場合でも 1 以上の有効値を要求する。

#### 25.25.11 forkの残り実行可能step数

snapshot 固定集合が 1 件以上の場合、次を確認する。

```text
remaining_steps = fork_W.TSIZE - fork_W.T
```

現在確認済みの UXsim の意味：

- `fork_W.T` は次に処理する timestep である。
- `fork_W.T == fork_W.TSIZE` なら新しい step を処理できない。
- `fork_W.T <= fork_W.TSIZE - 1` なら少なくとも 1 step 処理できる。

**2026-08-31確定：** snapshot 固定集合が 1 件以上の場合、指定 horizon に加えて **1 timestep 以上** を残せることを要求する。正式 driver の実行条件は次で確定する。

```text
baseline_horizon_steps + 1 <= fork_W.TSIZE - fork_W.T
```

同値な厳密不等式：

```text
baseline_horizon_steps < fork_W.TSIZE - fork_W.T
```

World 終端ちょうどへの到達は **許可しない**。horizon 終了後に `fork_W.T == fork_W.TSIZE` となる実行は許可しない。

**確定理由（2026-08-31 Terminal 確認）：** baseline forward が World 終端へ到達すると、次が自動実行される。

```text
World.simulation_terminated()
→ Analyzer.basic_analysis()
→ od_to_pandas()
```

`Analyzer.basic_analysis()` は単なる終了表示ではなく、少なくとも次を計算して Analyzer 状態へ保存する。

- 完了 trip 数
- 全 trip 数
- 総走行距離
- 総旅行時間
- 平均旅行時間
- 総遅延
- 平均遅延

これらは baseline collector による到着・通過情報収集には不要である。World 終端へ到達しても collector 結果が壊れるという証拠は確認されていない。一方、次は確認できた。

- baseline 収集に不要な終了時集計が追加実行される
- 不要な計算負荷が生じる
- fork の Analyzer 状態が変更される
- baseline driver の責任外である終了後分析が実行される
- 終了後分析に由来する例外や副作用の可能性を余計に持ち込む

**正常境界例：**

```text
fork_W.T = 200
fork_W.TSIZE = 251
baseline_horizon_steps = 50
```

- `remaining_steps` は 51 である。
- horizon 50 に加えて 1 timestep 残せる。
- timestep 200 から 249 までの 50 step を処理する。
- forward 終了後は `fork_W.T == 250` である。
- `fork_W.TSIZE == 251` であり、World 終端まで 1 timestep 残る。
- `simulation_terminated()` は実行されない。
- `Analyzer.basic_analysis()` も実行されない。

**1 timestep 不足の境界例：**

```text
fork_W.T = 200
fork_W.TSIZE = 250
baseline_horizon_steps = 50
```

- `remaining_steps` は 50 である。
- horizon 自体の 50 step は処理できるが、forward 終了後に `fork_W.T == fork_W.TSIZE` となる。
- `simulation_terminated()` と `Analyzer.basic_analysis()` が実行される。
- 正式 driver の契約上は 1 timestep 余白不足である。
- forward 開始前に設定不整合として停止する。
- horizon を 49 へ自動短縮しない。

**歴史的記録：** 本節初版（2026-08-31 前半）では、`baseline_horizon_steps <= fork_W.TSIZE - fork_W.T` を候補とし、1 timestep 余白は未確定としていた。同日の追加 Terminal 確認により、上記条件へ確定した。

#### 25.25.12 horizon不足

- snapshot 固定集合が 1 件以上の場合に残り step 数を検査する。
- 次を満たさなければ **設定不整合** とする。

```text
baseline_horizon_steps + 1 <= fork_W.TSIZE - fork_W.T
```

- horizon step 数だけ実行可能でも、終了後の 1 timestep が残らなければ不足である。
- World 終端へ到達する実行を許可しない。
- 指定 horizon を完走できない場合、および 1 timestep 余白が不足する場合は、World 作成時の **実行可能期間不足** である。
- 交通情報を取得できなかった状態とは異なる。
- horizon 不足を理由に自動短縮しない。
- horizon 不足時の例外型（`ValueError` または `RuntimeError`）は実装前に確定する。**2026-08-31 更新：** `ValueError` に確定。詳細は **§25.25.28.11**、**§25.25.28.15** を参照する。
- 空固定集合の場合は forward しないため、残り step 数検査を行わない。

#### 25.25.13 進行済みforkを後から延長しない

初期正式driverは次を **行わない**。

- `fork_W.TMAX` の後変更
- `fork_W.TSIZE` の後変更
- Link 内部配列の手動延長
- Analyzer 内部状態の手動延長
- `finalize_scenario()` の再実行
- horizon の自動短縮
- 現在状態を新規全 World へ手動移植
- 通常 `exec_simulation()` を代替する専用 forward loop

理由：

- finalized かつ進行済み World を安全に延長する公開 API が確認できない。
- `TSIZE` は `finalize_scenario()` で `TMAX` から構成される。
- Link の `traveltime_actual` は当初の `TSIZE` に合わせて作られる。
- `k_mat`、`q_mat`、`v_mat`、`tn_mat`、`dn_mat` 等は当初の `TMAX` を前提に作られる。
- `Q_AREA`、`K_AREA` 等も当初設定に依存する。
- `TMAX` または `TSIZE` だけを変更すると内部状態が一致しない。
- `finalize_scenario()` の再実行は `T` と `TIME` を 0 へ戻す。
- `finalize_scenario()` は内部配列、`RouteChoice`、`Analyzer` 等を再初期化する。
- 手動延長は対象漏れと交通結果変化の危険が高い。
- BATCH Level 2 は必要な `TMAX` を持つ mimic World を最初から新規構築しており、進行済み全 World fork の事後延長ではない。

将来、専用配列延長 helper または全 World 再構築方式を研究する可能性は残すが、初期 driver へ含めない。

#### 25.25.14 World作成時のbaseline用余白

正式 driver 自身が fork を後から延長しないため、実験・シナリオ設計側で、最後の baseline 実行にも十分な将来計算余地を確保する必要がある。

区別する概念：

```text
通常の研究評価期間

新しいTVT判断を開始できる期間

baseline forkが将来を計算するための余白

Worldが技術的に進行できる期間
```

名称候補：

```text
T_evaluation_end
H_max
TSIZE
```

ただし、`T_evaluation_end` と `H_max` は正式名称・保存場所とも **未確定** である。

**2026-08-31確定：** baseline 終了後に 1 timestep 残す方針を採用する。現在の名称候補を使った概念式は次で統一する。

```text
TSIZE >= T_evaluation_end + H_max + 1
```

式の `+1` は、baseline forward 終了後に World 終端へ到達させないための技術的余白である。

**歴史的記録：** 本節初版では `TSIZE >= T_evaluation_end + H_max` を採用候補として記録していた。2026-08-31 の追加 Terminal 確認により、World 終端時の `simulation_terminated()` と `Analyzer.basic_analysis()` を避けるため、上記 `+1` 式を採用しなかった。

`T_evaluation_end` の境界定義は引き続き未確定である。次を実験・評価設計上の未確定事項として記録する（§25.25.26 参照）。

- `T_evaluation_end` の正式名称
- `T_evaluation_end` の正確な境界定義
- 保存場所
- `H_max` の設定場所
- horizon 感度分析との連動
- `real_W` を余白期間まで進めるか
- 余白期間を評価指標へ含めるか
- `T_evaluation_end` 以降の新規 TVT 発動をどこで抑止するか

#### 25.25.15 正常な情報不足

指定 horizon を正常に完走しても、collector record で次が `None` のまま残り得る。

- `baseline_arrival_timestep`
- `arrival_tiebreaker`
- `route_next_link_name`
- `baseline_passage_timestep`

また、次も正常に起こり得る。

- Node ごとに全情報取得、一部情報取得、全情報未取得が混在する。
- right_of_entry vehicle の baseline 予想通過 timestep `P` が得られない。
- TVT 候補 Vehicle の一部または全部の baseline 予想通過 timestep が得られない。

driver は次を行わない。

- `None` の補完
- 到着時刻や通過時刻の推測
- `route_next_link` の推測または選び直し
- 一部情報を完全情報として扱うこと
- 全件情報取得を成功条件とすること

horizon 完走後の情報不足は、driver の実行異常ではない。後続の Node 別 TVT 制度処理が解釈する。

#### 25.25.16 `P`取得だけでは情報取得完了ではない

制度上の明確化：

- right_of_entry vehicle の baseline 予想通過 timestep を `P` とする。
- `P` を取得しただけでは、Node の TVT 用 baseline 情報取得完了ではない。
- `P - 1` までに到着すると予測される TVT 候補 Vehicle 集合を確定する必要がある。
- 候補 Vehicle 全員について、TVT 形成以降に必要な baseline 情報が必要である。
- 特に候補 Vehicle 全員の baseline 予想通過 timestep が必要である。
- `P - 1` に到着する Vehicle の通過時刻が `P` より後になる可能性がある。
- 候補集合を確定した後も、候補全員の通過情報を得るための観測が必要になり得る。
- 候補時間範囲は right_of_entry vehicle の `P - 1` で固定する。
- 他の候補 Vehicle の通過時刻を理由に候補時間範囲を再帰的に拡張しない。

説明用語として **right_of_entry vehicle** を使用する。`right-holder` は使用しない。`right_of_entry_vehicle` は、コード識別子候補について明示的に説明する場合以外、説明用語として使用しない。

#### 25.25.17 一部情報による部分的TVTの禁止

制度上の確定事項：

- TVT 候補 Vehicle 全員の必要情報が揃わなければ、その Node で TVT を形成しない。
- 情報取得済み Vehicle だけを使った部分的な TVT は行わない。
- 一部情報取得の場合も、全く情報を取得できない場合も、制度上は Node 未解決となり得る。

説明例：

```text
baseline到着順位：
A, B, C, D, E, F

必要な通過情報を取得できたVehicle：
A, B, E
```

A、B、E だけで TVT を形成すると、E が C、D より前へ移る可能性がある。C、D は E より先に到着しているにもかかわらず、順位を下げられることに対する補償を受けない可能性がある。したがって、A、B、E だけを使った部分的 TVT を形成しない。候補全員の必要情報が揃わなければ Node 未解決として扱う。

未解決時は既存 §14.4 に従う。

- 意思決定窓内の未確定 Vehicle 全体を baseline 到着順位で確定する。
- 意思決定窓外の未確定 Vehicle は、未解決という理由だけでは確定しない。

この説明例は制度理由の説明であり、新しい候補生成規則ではない。

#### 25.25.18 `TVT用baseline情報取得完了`の意味

`TVT用baseline情報取得完了` とは、後続の TVT 形成、局所仮想計算、経済評価などへ進むために必要な baseline 情報が揃った状態である。

これは次が完了した意味 **ではない**。

- TVT 形成
- 局所仮想計算
- 買い手・売り手選定
- 経済評価
- 支払い・補償
- 順位確定
- §14.3 または §14.4 の順位処理

Node が情報取得完了になるためには、少なくとも次が必要である。

- right_of_entry vehicle を制度側で特定できる
- `P` を取得できる
- `P - 1` に基づく候補集合を確定できる
- 候補 Vehicle 全員の必要 baseline 情報が揃っている
- 特に候補全員の baseline 予想通過 timestep が揃っている

情報不足の場合は、horizon 終端時未解決として後続制度処理が扱う。正式 driver 自身は、この Node 状態を判定しない。

#### 25.25.19 正式driverの処理順

これは正式 driver の処理順であり、早期終了方式の処理順ではない。

1. 入力を検証する。
2. `real_W` の軽量不変確認用情報を保存する。
3. `real_W` を copy して `fork_W` を作る。
4. copy 直後の時刻と collector 状態を確認する。
5. fresh collector を `fork_W` だけへ設定する。
6. snapshot 固定集合を 1 回登録する。
7. 登録件数と collector export 件数を照合する。
8. 登録件数が 0 なら、残り step 数検査と forward を行わず 0 step 正常結果を返す。
9. 登録件数が 1 以上なら、指定 horizon を実行した後にも 1 timestep を残せるか確認する（§25.25.11）。
10. 条件不足なら forward 開始前に設定不整合として停止する。
11. 条件充足時だけ、指定 horizon を 1 回の `exec_simulation()` で一括実行する。
12. 実行後の `fork_W.T` が、実行前時刻＋指定 horizon と一致することを確認する。
13. 実行後に `fork_W.T < fork_W.TSIZE` であることを確認する。
14. collector export 件数が登録時から変化していないことを確認する。
15. `real_W` の `T`、`TIME`、collector が変化していないことを確認する。
16. collector と実行メタデータを result として返す。
17. `fork_W` は返さない。

事後確認条件：

```text
fork_W.T_after == fork_W.T_before + baseline_horizon_steps
```

かつ

```text
fork_W.T_after < fork_W.TSIZE
```

#### 25.25.20 result dataclass

第一候補：

```python
@dataclass
class OrderControlBaselineForkResult:
    collector: OrderControlBaselineCollector
    target_node_names: tuple[str, ...]
    baseline_timestep_T: int
    configured_horizon_steps: int
    fork_steps_executed: int
    final_fork_timestep: int
    registered_visit_count: int
```

各フィールドの意味：

- `collector`：snapshot 固定集合の取得済み・未取得 baseline 情報。
- `target_node_names`：今回の結果に対応する対象 Node 名の固定 `tuple`。
- `baseline_timestep_T`：snapshot 時点。次に処理する timestep。
- `configured_horizon_steps`：呼出側が指定した観測長。
- `fork_steps_executed`：実際に実行した step 数。
- `final_fork_timestep`：forward 終了後の `fork_W.T`。
- `registered_visit_count`：snapshot 固定集合の登録総数。

- dataclass は非 frozen とする。
- `horizon_reached` を含めない。
- `early_terminated` を含めない。
- Node 別状態を含めない。
- `fork_W` を含めない。
- 空固定集合は `registered_visit_count == 0` かつ `fork_steps_executed == 0`。
- 通常実行は `fork_steps_executed == configured_horizon_steps`。

`target_node_names` を含める理由：

- 結果と対象 Node 集合を一体で保持する。
- 後続処理が Node 一覧を再入力しない。
- 結果と対象 Node 一覧の取り違えを防ぐ。
- collector の確認対象を明確にする。
- 入力順を維持する。

#### 25.25.21 正式driverの責任

- 入力の最小限の検証
- `real_W` の copy
- `fork_W` の作成
- fresh collector の作成
- `fork_W` だけへの collector 設定
- snapshot 固定集合の登録
- 登録件数の照合
- 空固定集合の判定
- 残り実行可能 step 数の確認
- 固定 horizon 一括実行
- 到着・通過記録の収集
- fork の進行 step 数確認
- collector 件数の不変確認
- `real_W` の軽量不変確認
- result 返却

#### 25.25.22 正式driverが担当しないこと

- 既到着 Vehicle の順位確定
- timestep T 到着 Vehicle の制度処理
- 意思決定窓内 Vehicle の制度上の抽出
- baseline 到着順位の構成
- 参加状態中立方式の適用
- 先頭非参加 Vehicle の先行確定（§4.5）
- `baseline_rank` の再構成
- right_of_entry vehicle の選定
- `P` の制度上の解釈
- `P - 1` 候補範囲の確定
- TVT 候補 Vehicle 集合の確定
- 候補 Vehicle 全員の情報充足判定
- 部分的 TVT 禁止の制度上の適用
- Node 別の TVT 検討不要、情報取得完了、未解決判定
- §14.4 fallback
- TVT 成立・不成立処理
- `trade_rank`
- 局所仮想計算
- 買い手・売り手選定
- 経済評価
- 支払い・補償
- 実績との比較分析
- 長期ログ
- 早期終了

これらは後続の Node 別 TVT 制度処理または将来の研究分析処理の責任である。

#### 25.25.23 初期実装ファイル候補

新規作成第一候補：

- `uxsim/order_control_baseline_driver.py`
- `tests_order_control_baseline_driver.py`

変更不要の第一候補：

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/order_control_baseline_snapshot.py`
- `uxsim/__init__.py`
- 既存テスト
- 既存診断
- Markdown 以外のファイル

正式 driver の直接 import 候補：

```python
from uxsim.order_control_baseline_driver import (
    OrderControlBaselineForkResult,
    run_snapshot_fixed_baseline_fork,
)
```

既存 collector と snapshot が専用モジュールから直接 import されているため、初期版では `uxsim/__init__.py` を変更しない。

**2026-08-31 更新：** 関数名、公開シグネチャ、実装ファイルを **§25.25.28** で確定した。snapshot docstring だけを実装時に変更する。詳細は §25.25.28 を参照する。

#### 25.25.24 テスト責任

将来の `tests_order_control_baseline_driver.py` で確認する事項：

- `baseline_horizon_steps` の `bool` 拒否
- 0 以下の拒否
- `target_node_names` の形式不正
- `real_W` に collector 設定済みの場合の拒否
- fork 側だけ fresh collector
- snapshot 登録 1 回
- 空固定集合 0 step 正常終了
- 1 件以上で固定 horizon 一括実行
- 指定 step 数と実際の進行一致
- `final_fork_timestep`
- 未到着 record が残っても正常終了
- 未通過 record が残っても正常終了
- 全取得、一部取得、全未取得の混在でも driver は正常終了
- 登録件数と export 件数の一致
- 固定集合外 Vehicle が件数を増やさない
- horizon 不足の検出（horizon step 数は実行可能だが終了後 1 timestep が残らない境界を含む）
- horizon 実行後に 1 timestep 以上残る境界の成功
- horizon step 数は実行可能だが、終了後の 1 timestep が残らない境界の拒否
- 正常終了時に `fork_W.T_after < fork_W.TSIZE`
- World 終端へ到達しないこと
- `simulation_terminated()` を呼ばないこと
- `Analyzer.basic_analysis()` を呼ばないこと
- 空固定集合では余白不足でも 0 step 正常終了すること
- horizon を自動短縮しないこと
- `real_W` の `T`、`TIME`、collector 不変
- 複数回呼出しで fresh collector が独立
- result の全フィールド
- result へ `target_node_names` が含まれる
- `fork_W` を返さない

正式 driver テストへ含めない事項：

- §4.5 の順位処理
- right_of_entry vehicle 選定
- Node 解決判定
- 部分的 TVT 禁止の制度処理
- §14.4 fallback
- 経済評価
- 早期終了

これらは後続制度処理または将来の早期終了専用テストの責任である。

**2026-08-31 更新：** 専用テスト形式と具体項目を **§25.25.28** で確定した。特定 Node だけ 0 件と、全対象 Node 合計 0 件を区別する。詳細は §25.25.28 を参照する。

#### 25.25.25 早期終了との関係

- 既存 §24.13 に早期終了の設計骨格が保存されている。
- **Git 管理下の Markdown だけを調査した時点**（§25.25 初版記録時）では、§24.11 から §24.13 より詳しい過去記録を確認できなかった。
- **その後**、ユーザーが保存していた過去の M365 Copilot 会話記録 3 件について、M365 Copilot が内容を確認した。特にプロンプト 5 に、snapshot 固定集合、二段階観測、1 timestep 単位の進行、Node 別完了、全 Node 集約の詳細が残っていた。プロンプト 6 に、collector と TVT 制度側の責任分担が残っていた。
- 回収した詳細を **§24.13.1 以降** へ正式記録した（2026-08-31 記録補修）。Cursor は元の 3 ファイルを直接参照していない。
- 初期正式 driver は引き続き固定 horizon 一括実行である。
- 早期終了は今回の正式 driver 実装範囲外である。
- 性能上の採否と未確定実装細部は別作業である（§24.13.15、§24.13.16 参照）。
- 将来は更新済み §24.13 を出発点とする。
- 既存 §24.13 本文（骨格）は変更しない。
- 既存の早期終了骨格を削除しない。
- 未確認の処理順を過去の合意事項として追加しない。

#### 25.25.26 未確定事項

**World 作成・正式 driver（§25.25）：**

- `T_evaluation_end` の正式名称
- `T_evaluation_end` の境界定義
- `T_evaluation_end` の保存場所
- `H_max` の正式名称と設定場所
- horizon 感度分析との余白連動
- `real_W` を余白期間まで進めるか
- 余白期間を研究評価へ含めるか
- `T_evaluation_end` 以降の新 TVT 発動抑止位置
- TVT 順位状態と確定順位ブロックの実装

**2026-08-31 更新：** 次の旧未確定事項は **§25.25.28** で解消済みである。

- horizon 不足時の例外型 → `ValueError`（§25.25.28.11、§25.25.28.15）
- snapshot docstring の明確化要否 → 実装時に docstring のみ明確化（§25.25.28.18）
- driver 関数の最終的な型注釈 → `real_W: World`（§25.25.28.2）
- 正式 baseline driver の実装 → **§25.25.28**（`order_control_baseline_driver.py`、§25.25.29 で実装・検証記録）

**2026-09-01 更新：** 次の旧未確定事項は **§25.25.30** で解消済みである。

- TVT 順位状態と確定順位ブロックの実装 → **§25.25.30**（Node 別確定順位ブロック・未確定 visit 集合・公開 API・専用テスト契約）

**早期終了（詳細は §24.13.16 参照）：**

- 性能上の採否と性能閾値
- Node 状態の保存形式
  - 2026-09-01 更新：上記は本節記録時点の未確定事項である。その後、順位状態は §25.25.30 で確定した。Node 評価状態の保存形式は引き続き未確定である。
- Node **評価**状態の保存形式（§24.12。順位状態は §25.25.30 で確定）
- 早期終了の実装配置（driver 拡張か別 driver か）
- 毎 timestep の Node 走査方法
- 性能評価用診断の具体 API
- 早期終了対応 result の追加フィールド

#### 25.25.27 実装再開情報

将来この作業を再開するときは、次を確認すればよい。

- 正本は本 §25.25 である。
- 既存実装は collector、通知接続、snapshot 固定集合登録まで完了している。
- 既存恒久診断は `diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py` である。
- 最新保存済みコミットは `b40cf23` である（origin へ push 済み）。
- World 終端時には `simulation_terminated()` から `Analyzer.basic_analysis()` が実行されることを Terminal で確認した。
- baseline 収集に不要な終了集計を避けるため、forward 後に 1 timestep 以上を残す方針を確定した。
- 残り step 条件は `baseline_horizon_steps + 1 <= fork_W.TSIZE - fork_W.T` である。
- 次の直接作業は、正式 driver コードと専用テストの実装前最終確認、または実装指示の作成である。
- 正式 driver 実装前に、ユーザーが保存していた過去の会話記録 3 件について M365 Copilot が確認を行った。欠落していた早期終了設計の詳細を §24.13 へ補修した。Cursor は元ファイルを直接参照していない。
- 初期正式 driver へ早期終了を実装する方針へ変更したわけではない。初期正式 driver は固定 horizon 一括実行のままである。
- 将来早期終了を再検討するときは §24.13 から再開する。元のプロンプト 4、5、6 の再読から始めなくてよいよう、必要な内容を §24.13 へ記録した。
- `diagnostics/order_control.zip` は未追跡であり、触れない。

**2026-08-31 更新：** 正式 driver 実装前の残存設計を **§25.25.28** で確定した。今後は §25.25.28 を直接参照して実装へ進む。§25.25.27 記録時点の実装前最終確認は完了した。最新保存済みコミットは `142d235` である。

#### 25.25.28 実装前残存設計事項の確定

記録日：2026-08-31

本 §25.25.28 を、正式 driver の関数名、公開 API、入力検証、処理順、例外、result、実装範囲、専用テストに関する **最新の正本** とする。既存 §25.25.1 から §25.25.27 は削除しない。§25.25.12 では horizon 不足時の例外型が未確定とされていたが、本節で `ValueError` に確定する。

#### 25.25.28.1 位置づけ

**確定したこと：** 関連コードと既存メモを読み取り、正式 driver 実装に直接必要な残存設計事項を確定した。今回はコード実装ではなく、実装中の現場判断をなくすための設計確定である。

**なぜ必要か：** driver 実装者が、入力の受け方、処理順、異常時の扱い、返却結果を実装中にその場で決めないため。

**何を防ぐか：** 実装途中での命名・検証順・例外型の再判断、早期終了の混入、制度処理責任の越境、部分結果の誤返却。

**コード上の実現：** 本節を実装指示の正本とし、driver は既存 `World.copy()`、`OrderControlBaselineCollector`、`register_snapshot_fixed_visits()`、fork 側 `exec_simulation()` を組み合わせる上位調整処理として実装する。新しい交通制度や TVT 制度処理は追加しない。

**通常時・異常時：** 通常時は固定 horizon 一括実行で collector と実行メタデータを返す。異常時は result を返さず、本節で定めた例外境界に従う。

**テストで保証：** `tests_order_control_baseline_driver.py` が本節全体の契約を検証する。collector・snapshot の細部は既存専用テストへ委ねる。

非技術的には、既存の部品をどの順序で使い、どの入力を受け付け、何を正常または異常として返すかを、コードを書く前に確定した作業である。

- 初期正式 driver は固定 horizon 一括実行のままである。
- 初期正式 driver は早期終了を行わない。
- 早期終了設計の正本は §24.13 である。
- 本節の内容を driver 本体と専用テストの実装指示へ直接使用する。

#### 25.25.28.2 公開API

##### 関数名

**確定：** `run_snapshot_fixed_baseline_fork`

**理由：** `register_snapshot_fixed_visits()` と語彙が対応する。snapshot 時点で固定した visit を対象とすることが分かる。fork World で baseline を実行することが分かる。リポジトリ内に同名の既存関数がない。`run_fixed_horizon_baseline_fork` より snapshot 固定集合の前提が明確。`run_order_control_baseline_fork` より責任範囲が明確。

**何を防ぐか：** 関数名だけでは snapshot 固定集合か、一般 baseline か、horizon 方式かが判別できない混乱。

**コード：** `uxsim/order_control_baseline_driver.py` に公開関数として定義する。

**テスト：** driver モジュールからの import 成功を実装後確認する。

非技術的には、名前を見ただけで「開始時点で固定した Vehicle を、複製交通上で観察する関数」だと理解できるようにするためである。

##### result dataclass

**確定：**

```python
@dataclass
class OrderControlBaselineForkResult:
    collector: OrderControlBaselineCollector
    target_node_names: tuple[str, ...]
    baseline_timestep_T: int
    configured_horizon_steps: int
    fork_steps_executed: int
    final_fork_timestep: int
    registered_visit_count: int
```

dataclass は **非 frozen** とする。

**何を防ぐか：** `fork_W` 全体の漏洩、早期終了フラグの混入、制度状態の driver 責任化。

**テスト：** 通常ケースと全対象 Node 合計 0 件ケースで 7 フィールドを検証する（§25.25.28.20）。

##### 公開シグネチャ

**確定：**

```python
def run_snapshot_fixed_baseline_fork(
    real_W: World,
    *,
    target_node_names: list[str] | tuple[str, ...],
    baseline_horizon_steps: int,
) -> OrderControlBaselineForkResult:
```

- `real_W` だけを positional 引数とする。
- `target_node_names` と `baseline_horizon_steps` は keyword-only とする。
- 初期 API へ動作切替フラグを追加しない。
- `real_W` には `World` 型注釈を付ける。
- `World` を driver モジュールから明示的に import する（例：`from uxsim.uxsim import World`）。
- 現行構造では `uxsim.py` から driver への逆 import がないため、循環 import は想定されない。実装後に新 driver モジュールの import 確認を行う。
- 戻り値型は `OrderControlBaselineForkResult`。
- **例外時には result を返さない。**

**呼出例：**

```python
result = run_snapshot_fixed_baseline_fork(
    real_W,
    target_node_names=tvt_target_node_names,
    baseline_horizon_steps=50,
)
```

**何を防ぐか：** 引数順の取り違え、keyword なしでの曖昧な呼出し。

**テスト：** list/tuple 受付と result 内の tuple 固定を検証する。

非技術的には、Node 一覧と観察時間を名前付きで渡し、呼出コードを見ただけで各値の意味が分かるようにして、引数順の取り違えを防ぐためである。

#### 25.25.28.3 入力validationと実行順序

**確定した処理順（driver 入口から result 返却まで）：**

1. `target_node_names` の容器型を確認する。
2. 空 list または空 tuple を拒否する。
3. `fixed_target_node_names` として tuple へ固定する。
4. `baseline_horizon_steps` の型と範囲を確認する。
5. `real_W._order_control_baseline_collector is None` を確認する。
6. `real_W` の軽量不変確認用の値を保存する。
7. `baseline_timestep_T` として `real_W.T` を保存する。
8. `real_W.copy()` を実行する。
9. copy 直後の fork identity、T、collector 状態を確認する。
10. fresh collector を生成する。
11. `fork_W` だけへ collector を設定する。
12. snapshot 固定集合を登録する。
13. 登録直後の件数を照合する。
14. 全対象 Node 合計 0 件なら、`real_W` 不変を確認して 0 step result を返す。
15. 合計 1 件以上なら、horizon 後の 1 timestep 余白を検査する。
16. `fork_W.T` を forward 開始前時刻として保存する。
17. 固定 horizon を 1 回の `exec_simulation()` で一括実行する。
18. 指定 horizon 分だけ T が進んだことを確認する。
19. World 終端へ到達していないことを確認する。
20. forward 後の collector 件数を照合する。
21. `real_W` の軽量不変を確認する。
22. 正常 result を返す。

**順序の理由（何を防ぐか）：**

- 空 Node 一覧は不要な `World.copy()` を避けるため copy 前に拒否する。
- 全対象 Node 合計 0 件かどうかは、snapshot 登録後でなければ判明しない。
- 全対象 Node 合計 0 件なら forward しないため、horizon 余白検査を行わない。
- horizon 余白不足は forward 開始前に検出する。
- snapshot 登録前に 0 件かどうかを推測しない。
- result はすべての事後確認に成功した後だけ返す。
- forward 後の collector 件数確認より先に result を返さない。

**実装前擬似コード（実装そのものではなく、実装順序と分岐を固定するためのもの）：**

```text
validate target_node_names container type
reject empty target_node_names
fixed_target_node_names = tuple(target_node_names)

validate baseline_horizon_steps
validate real_W collector is None

baseline_timestep_T = real_W.T
real_world_t_before = real_W.T
real_world_time_before = real_W.TIME
real_world_collector_before = real_W._order_control_baseline_collector

fork_W = real_W.copy()
validate copied fork identity, timestep, and collector state

collector = OrderControlBaselineCollector()
fork_W._order_control_baseline_collector = collector

registered_visit_count = register_snapshot_fixed_visits(
    fork_W,
    collector,
    target_node_names=fixed_target_node_names,
)

validate registered_visit_count against collector exports

if registered_visit_count == 0:
    validate real_W unchanged
    return OrderControlBaselineForkResult(
        collector=collector,
        target_node_names=fixed_target_node_names,
        baseline_timestep_T=baseline_timestep_T,
        configured_horizon_steps=baseline_horizon_steps,
        fork_steps_executed=0,
        final_fork_timestep=baseline_timestep_T,
        registered_visit_count=0,
    )

validate horizon plus one-timestep margin

fork_timestep_before = fork_W.T

fork_W.exec_simulation(
    duration_t2=baseline_horizon_steps * fork_W.DELTAT
)

validate executed timestep count
validate World termination was not reached
validate registered visit count unchanged
validate real_W unchanged

return OrderControlBaselineForkResult(
    collector=collector,
    target_node_names=fixed_target_node_names,
    baseline_timestep_T=baseline_timestep_T,
    configured_horizon_steps=baseline_horizon_steps,
    fork_steps_executed=baseline_horizon_steps,
    final_fork_timestep=fork_W.T,
    registered_visit_count=registered_visit_count,
)
```

**テスト：** 各分岐点（空 Node 拒否、全対象 Node 合計 0 件の 0 step 正常終了分岐、余白不足、通常 forward）を専用テストで個別に検証する（§25.25.28.20）。

#### 25.25.28.4 target_node_names

**確定した受入型：**

| 区分 | 型 |
|------|-----|
| 受け付ける | `list`、`tuple` |
| 拒否する | `str`、`bytes`、`set`、`generator`、その他の一般 `Iterable` |

driver 入口で list または tuple であることと、空でないことを確認してから、一度だけ tuple へ固定する。

```python
fixed_target_node_names = tuple(target_node_names)
```

**driver が担当する検証：**

- 容器型が list または tuple
- 空でないこと
- tuple への固定

**`register_snapshot_fixed_visits()` へ委譲する検証：**

- 各要素が非空文字列
- Node 名重複
- Node の存在
- `order_control_eligible=True`
- `order_control_type="time_value"`

**何を防ぐか：** set の順序不定、generator の消費による分かりにくい挙動、登録・件数確認・result で異なる Node 順序を使う不整合。既存 snapshot が保証する意味的検証の driver 側重複実装。

**通常時：** 非空 list/tuple を受け取り、固定 tuple で登録・照合・result に使用する。

**異常時：** 容器型不正・空 → `ValueError`（copy 前）。意味的検証失敗 → snapshot の `ValueError` を伝播。

**テスト：** list/tuple 受付、str/bytes/set/generator 拒否、空 list/tuple 拒否、result の tuple 固定。Node 存在等は snapshot 既存テストへ委ねる。

##### 空の target_node_names

**確定：** `target_node_names` が空なら **入力エラー**。`World.copy()` 前に `ValueError` を送出する。

**区別：**

| 状況 | 意味 |
|------|------|
| `target_node_names` が空 | 調査する Node が指定されていない **入力エラー** |
| `target_node_names` は非空だが `registered_visit_count == 0` | 対象 Node は指定済みだが、全対象 Node を通じて観察対象 Vehicle がいない **正常結果** |

**テスト：** 空 list/tuple 拒否テスト。全対象 Node 合計 0 件テストと混同しない。

#### 25.25.28.5 baseline_horizon_steps

**確定：**

- bool ではない Python `int`
- 1 以上
- `float` は拒否
- NumPy 整数は初期版では拒否
- driver 内に上限を固定しない
- horizon を自動短縮しない

**検証概念：**

```python
if (
    isinstance(baseline_horizon_steps, bool)
    or not isinstance(baseline_horizon_steps, int)
    or baseline_horizon_steps < 1
):
    raise ValueError(...)
```

**何を防ぐか：** 真偽値・小数・0・負数を step 数として扱うことによる曖昧な入力を防ぐ。NumPy 整数を初期版で拒否するのは、乗算できないためではなく、既存 order-control 系の検証規則に合わせ、受付型を Python の `int` に限定して一貫性を保つためである。

**通常時：** 正の Python int を `configured_horizon_steps` として保持し、forward 時に使用する。

**異常時：** 型・範囲不正 → `ValueError`（copy 前）。

**テスト：** True/False/0/負数/float/NumPy 整数拒否、正の Python int 受付。

**明記：** 全対象 Node 合計 0 件で `fork_steps_executed == 0` になることと、入力 horizon として 0 を許可することは **別** である。

#### 25.25.28.6 real_Wの入口条件と保存値

**確定した入口条件：**

```text
real_W._order_control_baseline_collector is None
```

非 `None` なら `World.copy()` 前に `ValueError` を送出する。

- collector 属性は `World.__init__()` で必ず `None` として作成される。
- `getattr()` は使わず正式属性を直接参照する。
- `real_W` へ collector を一時的にも設定しない。
- `real_W` の `finalized` 状態を driver で重複検査しない。
- `T`、`TIME`、`TSIZE`、`DELTAT` の一般的な型と値を全面再検証しない。
- horizon 余白は fork 作成後に必要条件だけを確認する。

**copy 前に保存する値：**

- `real_W.T`
- `real_W.TIME`
- `real_W._order_control_baseline_collector`
- `baseline_timestep_T` として `real_W.T`

**何を防ぐか：** 本物交通へ仮想計算用記録帳がすでに付いている状態での copy、real_W 汚染。

**通常時：** 入口で `None` を確認し、終了時に保存値と一致することを確認する（正常終了時のみ。§25.25.28.14）。

**異常時：** 非 `None` → `ValueError`。正常終了後の不変違反 → `RuntimeError`。

**テスト：** collector 設定済み `real_W` の入口拒否。正常系および代表的異常系での `T`/`TIME`/collector 不変。

非技術的には、本物の交通へ仮想計算用記録帳がすでに付いている場合、安全な複製処理の入口条件が崩れているため、処理開始前に拒否する。

#### 25.25.28.7 World.copy()とcopy直後確認

**確定：**

- `World.copy()` は正常時に pickle 複製した `World` を返す。
- 正常経路に `None` を返す分岐はない。
- 本番 driver では copy 戻り値の `None` 確認を追加しない。
- copy 例外は変換せず伝播する。
- 失敗時には result を返さない。
- 自動再試行しない。

**copy 直後に確認する項目：**

```text
fork_W is not real_W
fork_W.T == baseline_timestep_T
fork_W._order_control_baseline_collector is None
```

不一致は **`RuntimeError`**。

全 Vehicle、Node、Link の参照独立性を本番 driver で毎回詳しく調べない。詳細検査は既存診断と専用テストの責任である。

**何を防ぐか：** copy 失敗の隠蔽、同一オブジェクト誤用、時刻ずれ、collector の誤伝播。

**テスト：** fork と real_W の別オブジェクト、T 一致、fork のみ collector 設定。copy 直後不整合の `RuntimeError`。

非技術的には、複製の本来の失敗理由を一般的な driver エラーへ置き換えず、原因を調査できる状態を保つためである。

#### 25.25.28.8 collector生成とsnapshot登録

**確定した処理順：**

```text
real_W 入口確認
→ World.copy()
→ copy 直後確認
→ fresh collector 生成
→ fork_W だけへ collector 設定
→ snapshot 固定集合登録
```

**collector 生成：**

```python
collector = OrderControlBaselineCollector()
```

**fork への設定：**

```python
fork_W._order_control_baseline_collector = collector
```

- `OrderControlBaselineCollector()` は引数なし。
- driver 自身が新規生成した collector なので、空かどうかを private 属性で再検査しない。
- collector を `real_W` へ設定しない。
- collector から `fork_W` への逆参照はない。
- result で collector を返しても `fork_W` 全体への参照は残らない。

**snapshot 登録：**

```python
registered_visit_count = register_snapshot_fixed_visits(
    fork_W,
    collector,
    target_node_names=fixed_target_node_names,
)
```

- fork forward 前に 1 回だけ呼ぶ。
- fresh collector へ登録する。
- 戻り値は **全対象 Node を合計した** 固定 visit 登録件数。
- 0 件も正常な戻り値。
- Node や Vehicle の意味的検証は snapshot 処理へ委譲する。
- snapshot 処理の既存例外は原則そのまま伝播する。
- driver 固有の一般例外へ一律変換しない。
- 登録失敗時は result を返さない。
- rollback しない。

**何を防ぐか：** 記録帳の real_W 混入、登録失敗理由の潰れ、部分登録結果の誤返却。

**テスト：** forward 前 1 回呼出、登録件数と export 一致、snapshot 例外維持、登録失敗時に result なし。

非技術的には、仮想計算の記録を本物の交通や次回の `real_W.copy()` へ混入させないためである。また、snapshot 処理が示す具体的な不整合理由を、driver が「登録失敗」という一種類の説明へ潰さないため、元例外を原則維持する。

#### 25.25.28.9 登録件数の照合

**確定した照合（公開 API のみ）：**

```python
exported_visit_count = sum(
    len(collector.export_node_baseline_visits(node_name))
    for node_name in fixed_target_node_names
)
```

確認：`exported_visit_count == registered_visit_count`

**照合時点：**

1. snapshot 登録直後
2. 固定 horizon 実行後

全対象 Node 合計 0 件の場合は、登録直後の照合後に 0 step で返すため、forward 後照合は **ない**。

**毎 timestep 照合しない理由：** 初期 driver は一括実行。固定集合登録は開始時の 1 回だけ。固定集合外通知は collector が無視する。毎 timestep の全 Node export は不要な負荷となる。

**異常時：** 件数不一致は **`RuntimeError`**。

**例外メッセージに含める必須情報：**

- `registered_visit_count`
- `exported_visit_count`
- 照合時点が登録直後か forward 後か
- `fixed_target_node_names`

**テスト：** 登録直後・forward 後の件数一致。不一致 `RuntimeError`。

非技術的には、登録処理が「10 件登録した」と報告したのに、記録帳には 9 件または 11 件しかないという内部矛盾を見逃さないためである。

#### 25.25.28.10 全対象Node合計0件の正常終了

**確定した 0 step 正常終了条件：**

```text
registered_visit_count == 0
```

ここで `registered_visit_count` は、特定 Node の件数ではなく、**全対象 Node へ登録された固定 visit の合計** である。

##### 固定 horizon を実行する例

- Node A：0 件
- Node B：2 件
- Node C：0 件
- `registered_visit_count`：2 件

Node B の固定 visit を観察する必要があるため、horizon 余白検査後に固定 horizon を実行する。

##### 0 step で正常終了する例

- Node A：0 件
- Node B：0 件
- Node C：0 件
- `registered_visit_count`：0 件

全対象 Node を通じて観察対象がないため、horizon 余白検査と forward を行わず正常終了する。

**全体合計 0 件の場合の動作：**

- horizon 余白検査を行わない
- `exec_simulation()` を呼ばない
- 0 step で正常終了する
- 通常と同じ result dataclass を返す
- result 返却前に `real_W` の軽量不変を確認する

**テスト：** 複数 Node の 0 件・非 0 件組合せ。特定 Node だけ 0 件でも全体合計 ≥ 1 なら forward する。

#### 25.25.28.11 horizon後の1 timestep余白

**確定した実行可能条件（全対象 Node 合計 ≥ 1 の場合のみ）：**

```text
fork_W.TSIZE - fork_W.T >= baseline_horizon_steps + 1
```

同値：

```text
baseline_horizon_steps + 1 <= fork_W.TSIZE - fork_W.T
```

全対象 Node 合計 0 件では forward しないため、この検査を行わない。

**不足時：** **`ValueError`**

**理由（何を防ぐか）：** driver 内部の故障ではない。horizon と World の残り期間の組合せが実行条件を満たさない。呼出側が World 作成時の余白または horizon を修正できる。forward 前に検出できる。World 終端時の `simulation_terminated()` → `Analyzer.basic_analysis()` を baseline 収集へ持ち込まない。

**例外メッセージに含める必須情報：**

- `baseline_horizon_steps`
- `remaining_steps`（`fork_W.TSIZE - fork_W.T`）
- `required_steps`（`baseline_horizon_steps + 1`）
- `fork_W.T`
- `fork_W.TSIZE`
- horizon 実行後に追加 1 timestep を残す必要があること

**数値例：**

| 区分 | 値 |
|------|-----|
| 正常 | `horizon=50`, `TSIZE=250`, `T=100`, `remaining=150`, `required=51` |
| 正常境界 | `horizon=50`, `TSIZE=251`, `T=200`, `remaining=51`, `required=51` |
| 不足境界 | `horizon=50`, `TSIZE=250`, `T=200`, `remaining=50`, `required=51` → horizon 50 step 自体は処理可能だが終了後に World 終端へ到達するため `ValueError` |

horizon を 49 へ自動短縮しない。

**テスト：** 正常境界・不足境界・十分余白の成功。

非技術的には、必要な交通観察の直後に、baseline には不要な World 終了時集計を動かさないため、観察時間とは別に 1 timestep を残す。

#### 25.25.28.12 固定horizon一括実行

**確定（全対象 Node 合計 ≥ 1 かつ余白条件充足時）：**

```python
fork_W.exec_simulation(
    duration_t2=baseline_horizon_steps * fork_W.DELTAT
)
```

- 固定 horizon を **一括実行** する。
- 1 timestep ずつ反復しない。
- 初期 driver では早期終了しない。
- 終端未到達時の正常戻り値は `0`。
- World 終端到達時の戻り値は `1`。
- 正常経路に `None` 戻り値はない。
- 戻り値を result へ保存しない。
- 戻り値を主要な成功条件として使用しない。

**何を防ぐか：** `return_code` だけでの成功判定、早期終了ループの混入。

**テスト：** `exec_simulation()` 1 回呼出、`duration_t2 == baseline_horizon_steps * DELTAT`。

非技術的には、関数の「完了」という戻り値だけでなく、依頼した timestep 数が実際に処理され、World 終了処理へ入っていないことを時刻の変化で確認する。

#### 25.25.28.13 実行後の事後条件

result を返す前に、次を **すべて** 確認する。

##### 指定 horizon 分の完走

```text
fork_W.T_after == fork_W.T_before + baseline_horizon_steps
```

不一致は **`RuntimeError`**。必須メッセージ情報：`fork_W.T_before`、`fork_W.T_after`、`baseline_horizon_steps`、期待した `fork_W.T_after`。

##### World 終端非到達

```text
fork_W.T_after < fork_W.TSIZE
```

不一致は **`RuntimeError`**。必須メッセージ情報：`fork_W.T_after`、`fork_W.TSIZE`、1 timestep を残す契約であること。

##### collector 件数不変

実行後の `exported_visit_count == registered_visit_count`。不一致は **`RuntimeError`**。

##### real_W 軽量不変

次が呼出前から変化していないこと：

- `real_W.T`
- `real_W.TIME`
- `real_W._order_control_baseline_collector`

不一致は **`RuntimeError`**。メッセージに変化した項目名、変更前の値、変更後の値を含める。

fork 側の `TIME` は、通常の UXsim 不変条件では `T` と `DELTAT` に連動するため、初期 driver で重複確認しない。

**テスト：** step 数一致、終端非到達、件数不変、real_W 不変（正常系）。

非技術的には、例外なく関数が戻っただけでなく、観察時間、終端回避、固定集合不変、real_W 不変をすべて満たした場合だけ、正式な正常結果を返す。

#### 25.25.28.14 途中例外と部分結果

**確定：**

- `World.copy()` 例外はそのまま伝播
- collector 生成例外はそのまま伝播
- snapshot 登録例外は原則そのまま伝播
- `exec_simulation()` 例外はそのまま伝播
- **result を返さない**
- **部分的な collector 結果を返さない**
- rollback しない
- horizon を変更して自動再試行しない
- 別 fork を作成して自動再試行しない

**real_W 軽量不変確認：** driver 本体では **正常終了時だけ** 行う。異常時に `finally` 内の確認例外を新たに送出すると、本来の copy、snapshot、forward 例外を隠す可能性があるため。

**ただし：** 代表的な異常経路でも `real_W` が不変であることは **専用テスト** で確認する。

**テスト：** 途中例外時に result なし、部分 collector を正常結果として返さない。代表的異常経路での real_W 不変。

非技術的には、調査が途中で中断された場合、途中まで記入された調査票を完成済み baseline 結果として後続処理へ渡さないためである。例外を一律に driver 固有の `RuntimeError` へ変換しない理由は、本来の原因と traceback を保持するためである。

#### 25.25.28.15 例外型と例外メッセージ

##### ValueError（呼出前または forward 前の入力・設定不整合）

- `target_node_names` の容器型不正
- 空の `target_node_names`
- `baseline_horizon_steps` の型または範囲不正
- `real_W` に collector 設定済み
- horizon 後 1 timestep 余白不足

##### RuntimeError（入力受付後の内部状態矛盾）

- copy 後の fork が `real_W` と同一
- copy 後の `fork_W.T` が baseline 開始 T と不一致
- copy 後の fork collector が `None` ではない
- snapshot 戻り件数と collector export 件数が不一致
- 指定 horizon 分だけ T が進んでいない
- forward 後に World 終端へ到達
- forward 後に collector 件数が変化
- 正常終了時に `real_W` が変化

##### 元例外を伝播（既存処理固有の原因を維持）

- `World.copy()`
- collector 生成
- snapshot 登録
- `exec_simulation()`

各例外メッセージには、問題を再現・診断するために必要な実値を含める。特に `real_W` 不変違反には、変化した項目名、変更前の値、変更後の値を含める。

**テスト：** 各 `ValueError`/`RuntimeError` 経路、元例外維持（copy、snapshot、forward）。

非技術的には、利用者が設定を直すべき問題、内部コードを調査すべき問題、既存処理固有の問題を区別するためである。

#### 25.25.28.16 resultの整合条件

result dataclass は §25.25.28.2 の 7 フィールド。非 frozen。

##### 各フィールドの意味（通常ケース：`registered_visit_count >= 1`）

| フィールド | 意味 |
|------------|------|
| `collector` | snapshot 固定集合の取得済み・未取得 baseline 情報を保持する記録帳 |
| `target_node_names` | 今回の結果に対応する対象 Node 名の固定 tuple。後続が Node 一覧を再入力しない |
| `baseline_timestep_T` | snapshot 時点。次に処理する timestep |
| `configured_horizon_steps` | 呼出側が指定した観測長 |
| `fork_steps_executed` | 実際に実行した step 数（通常は `configured_horizon_steps` と一致） |
| `final_fork_timestep` | forward 終了後の `fork_W.T`（通常は `baseline_timestep_T + configured_horizon_steps`） |
| `registered_visit_count` | 全対象 Node 合計の snapshot 固定 visit 登録数 |

##### 各フィールドの意味（全対象 Node 合計 0 件）

| フィールド | 値 | 意味 |
|------------|-----|------|
| `collector` | fresh な空 collector | 観察すべき固定 visit がなかったため、到着・通過記録を含まない |
| `target_node_names` | 固定 tuple | どの Node を調査した結果、合計 0 件だったかを result 自身が保持 |
| `baseline_timestep_T` | copy 前の `real_W.T` | どの時点の snapshot を調べたか |
| `configured_horizon_steps` | 入力 horizon | 観察対象があれば進める予定だった step 数。0 step の理由は horizon が 0 だからではない |
| `fork_steps_executed` | `0` | 1 timestep も進めなかった |
| `final_fork_timestep` | `baseline_timestep_T` | forward していないため開始時刻と同じ |
| `registered_visit_count` | `0` | 全対象 Node 合計で固定 visit が 0 件 |

result 全体は次を表す：対象 Node は正しく指定されていたが、全対象 Node を通じて観察対象 Vehicle が一台もいなかったため、仮想計算を進めず正常終了した。

##### 追加しない項目と理由

| 除外 | 理由 |
|------|------|
| `return_code` | `T` の事後確認で代替できる |
| `horizon_reached` | 通常実行では固定 horizon を完走するため冗長 |
| `early_terminated` | 初期 driver は早期終了しない |
| Node 別制度状態 | 後続 TVT 制度処理の責任 |
| `fork_W` | 大量の可変状態を後続へ漏らさない |

##### 整合条件

**全対象 Node 合計 0 件：**

```text
registered_visit_count == 0
fork_steps_executed == 0
final_fork_timestep == baseline_timestep_T
configured_horizon_steps >= 1
```

**通常実行：**

```text
registered_visit_count >= 1
fork_steps_executed == configured_horizon_steps
final_fork_timestep == baseline_timestep_T + configured_horizon_steps
```

driver 内部ではさらに `final_fork_timestep < fork_W.TSIZE` を確認済み。`fork_W.TSIZE` は result に含めないため、最後の条件は result 利用者が再確認する条件ではなく、driver が result 返却前に保証する事後条件である。

**テスト：** 通常ケースと 0 件ケースの 7 フィールド検証。

#### 25.25.28.17 内部helper候補

可読性を保つため、内部 helper を用いる第一候補。helper 名は責任が分かる具体名とする。helper を細分化しすぎて公開 driver の処理順が読めなくなる構造は避ける。helper の最終的な統合・分割は実装中の可読性確認による軽微な調整を許可するが、**確定済みの処理順、例外境界、責任分担、result の意味は変更しない**。

| helper 第一候補名 | 責任 |
|-------------------|------|
| `_validate_and_freeze_target_node_names` | 容器型・空拒否・tuple 固定 |
| `_validate_baseline_horizon_steps` | horizon 型・範囲検証 |
| `_count_exported_baseline_visits` | `fixed_target_node_names` に対する export 合計件数 |
| `_validate_registered_visit_count` | `registered_visit_count` と export 合計の一致（照合時点を引数で受け取る） |
| `_validate_copied_fork` | copy 直後の identity・T・collector |
| `_validate_remaining_baseline_steps` | horizon + 1 timestep 余白 |
| `_validate_completed_fork_forward` | T 完走・終端非到達 |
| `_validate_real_world_unchanged` | real_W の T・TIME・collector |
| `_build_empty_baseline_result` | 全対象 Node 合計 0 件の result 構築 |
| `_build_completed_baseline_result` | 通常完了の result 構築 |

短い高度な Python 表現より、Python 初学者が処理順を追える明示的な実装を優先する。

#### 25.25.28.18 snapshot docstring

**確定方針：** 正式 driver 実装時に、`uxsim/order_control_baseline_snapshot.py` の **docstring だけ** を明確化する。今回（2026-08-31）は方針のメモ化のみ。Python docstring 自体はまだ変更しない。

**正しい順序：**

```text
real_W を時刻 T まで通常実行
→ real_W.T == T で、timestep T は未処理
→ real_W.copy()
→ copy 直後の fork_W から snapshot 固定集合を登録
→ fork baseline forward を開始
```

docstring に明記する内容：

- `real_W` が baseline 開始時点 T へ到達した後に copy する
- copy 直後の `fork_W` を渡す
- fork baseline forward 前に呼ぶ
- `fork_W.T == T` では timestep T は未処理

関数本体、引数、戻り値、validation は変更しない。

**何を防ぐか：** 将来の実装者が仮想計算後の Vehicle 集合を誤って snapshot 固定集合として登録すること。

**テスト：** コードレビューおよび本文確認（§25.25.28.20）。

#### 25.25.28.19 実装ファイルと変更範囲

##### 新規作成

- `uxsim/order_control_baseline_driver.py`
- `tests_order_control_baseline_driver.py`

##### driver 実装時に docstring だけ変更

- `uxsim/order_control_baseline_snapshot.py`

##### 実装結果の記録時に変更

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`
- `ORDER_EXCHANGE_PROGRESS.md`

##### 変更しない

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/__init__.py`
- 既存テスト
- 既存診断
- `diagnostics/order_control.zip`

**import：**

```python
from uxsim.order_control_baseline_driver import (
    OrderControlBaselineForkResult,
    run_snapshot_fixed_baseline_fork,
)
```

実装中に既存コードの動作変更が必要と判明した場合は、勝手に変更範囲を広げず、作業を止めて必要な理由を報告する。

非技術的には、正式 driver は新しい交通動作を追加するものではなく、既存の copy、collector、snapshot、forward を正しい順序で接続する調整役なので、巨大な `uxsim.py` へ混ぜず専用ファイルへ置く。

#### 25.25.28.20 専用テストの仕様対応

**新規テスト：** `tests_order_control_baseline_driver.py`

**形式（既存 order-control テストと同様）：**

- `test_*` 関数
- `TESTS` 一覧
- `if __name__ == "__main__":` による直接実行
- 実行：`python tests_order_control_baseline_driver.py`
- テスト用 World helper は新規ファイル内へ置く第一候補
- pytest 専用形式へ変更しない
- 既存 snapshot validation の全テストを重複しない

非技術的には、driver テストは既存部品を正しい順序で接続できているかを確認し、collector や snapshot が個別に保証済みの細部を全面的に再試験しない。

##### 入力 validation

list 受付、tuple 受付、result で tuple 固定、str/bytes/set/generator 拒否、空 list/tuple 拒否、True/False 拒否、horizon 0 拒否、負数 horizon 拒否、float 拒否、NumPy 整数拒否、正の Python int 受付、`real_W` に collector 設定済みなら拒否。

##### copy と collector

`fork_W` と `real_W` が別オブジェクト、copy 直後の T 一致、fork だけへ fresh collector、`real_W` の collector は `None`、複数回呼出しで別 collector、前回記録が次回へ混入しない。

##### snapshot 登録

forward 前に 1 回だけ、登録件数と export 合計一致、snapshot 例外維持、登録失敗時に result なし。

##### 全対象 Node 合計 0 件

特定 Node だけ 0 件で他 Node に固定 visit があれば forward、全対象 Node 合計 0 件の場合だけ 0 step 終了、余白検査なし、`exec_simulation()` 非呼出、result 7 フィールド正しい、`configured_horizon_steps` は入力値維持、`fork_steps_executed == 0`、`final_fork_timestep == baseline_timestep_T`。

##### 1 timestep 余白

`remaining_steps == horizon + 1` で成功、`remaining_steps == horizon` で `ValueError`、十分余白の通常例で成功、horizon 自動短縮なし、forward 後に少なくとも 1 timestep 残る。

##### 一括実行

`exec_simulation()` 1 回、`duration_t2 == baseline_horizon_steps * DELTAT`、指定 step 数だけ T 進行、`T_after < TSIZE`、`simulation_terminated()` 非呼出、`Analyzer.basic_analysis()` 非呼出。

##### collector 結果

到着済み固定 Vehicle の既存情報保持、未到着固定 Vehicle の到着記録、通過した場合の通過記録、未到着なら `None`、到着済み未通過なら通過だけ `None`、一部または全部 `None` でも driver 正常終了、全固定 visit の通過完了を成功条件にしない、固定集合外 Vehicle が件数を増やさない、forward 後も登録件数一致。

##### 不整合と例外

copy 直後の各不整合で `RuntimeError`、登録件数不一致・実行 step 数不一致・World 終端到達・実行後 collector 件数不一致・real_W 軽量不変違反で `RuntimeError`、既存例外を不要に変換しない、途中例外時に result なし、部分 collector を正常結果として返さない、代表的異常経路でも `real_W` の T・TIME・collector 不変。

##### result

通常ケースと 0 件ケースで 7 フィールド、`target_node_names` は tuple、`fork_W`/`return_code`/`early_terminated`/Node 別制度状態を含まない。

##### 仕様とテストの対応

| 仕様 | テスト |
|------|--------|
| 入力型契約 | 入力 validation テスト |
| `target_node_names` の tuple 固定 | result テスト |
| `real_W` の collector `None` 契約 | 入口拒否テスト |
| copy 後の fork 条件 | copy 直後不整合テスト |
| snapshot 登録 1 回 | 呼出回数テスト |
| 全対象 Node 合計 0 件 | 複数 Node の 0 件・非 0 件組合せテスト |
| 1 timestep 余白 | 正常境界と不足境界テスト |
| 固定 horizon 一括 forward | 呼出回数と duration テスト |
| 情報不足が正常結果 | `None` 残存テスト |
| 固定集合件数不変 | 登録直後と forward 後の件数テスト |
| `real_W` 不変 | 正常系および代表的異常系テスト |
| 元例外維持 | copy、snapshot、forward の例外伝播テスト |
| 部分 result 禁止 | forward 途中例外テスト |
| result の 7 フィールド | 通常ケースと 0 件ケースの result テスト |
| snapshot docstring | コードレビューおよび本文確認 |

**既存 collector・snapshot テストへ委ねる内容：** Node 存在、eligibility、time_value、visit 重複、collector 内部 validation、固定集合外通知の無視の詳細。

**新 driver テストで必要な内容：** 上記表の接続順・分岐・例外境界・result 契約。

#### 25.25.28.21 実装後の完了確認

将来の実装完了条件：

- 新規 driver モジュールの import 成功
- 新規専用テスト全件成功
- collector 既存テスト成功
- snapshot 既存テスト成功
- collector と UXsim 通知接続に関係する既存テスト成功
- 小規模 fork 診断成功
- `py_compile` 成功
- `git diff --check` 成功
- テスト関数数と `TESTS` 一覧数の一致
- 重複テスト関数名なし
- 変更対象ファイルが予定範囲内
- `diagnostics/order_control.zip` 未接触
- 慎重な欠陥探索レビュー
- レビュー指摘の修正後に関係テストを再実行
- 実装結果とレビュー結果を設計メモ・進捗メモへ記録

#### 25.25.28.22 今回確定しない事項

次は初期正式 driver の実装に直接必要ないため、今回確定しない。

- 早期終了の性能上の採否・実装形式
- Node 別制度状態の保存形式
- right_of_entry vehicle 選定、P-1 候補集合、TVT 形成
- §14.4 fallback、局所仮想計算、経済評価、支払い・補償
- TVT 順位状態、確定順位ブロック
- `T_evaluation_end` の上位実験 driver への保存方法
- 余白期間の研究評価への含め方
- `real_W` を余白期間まで進めるか

**これらが未確定でも、初期固定 horizon 正式 driver は実装可能である。**

**2026-09-01 更新（歴史的記録の補足）：**

- 本節記録時点では、TVT 順位状態・確定順位ブロック・Node 別制度状態の保存形式は「初期正式 driver 実装に直接不要なため未確定」とされていた。
- 正式 baseline driver 完成（コミット `bd24ad1`）後、**Node 別の確定順位ブロックと未確定 visit 集合**について実装前仕様を **§25.25.30** で確定した。
- **§25.25.30 で確定した範囲：** 順位状態部品（`OrderControlTvtNodeRankState`）、`VisitKey`、`K_confirmed`、登録・確定 API、不変条件、例外、専用テスト契約。
- **引き続き本節で未確定のまま、または §25.25.30 対象外：** Node 別**評価**状態、right_of_entry vehicle 選定、P-1 候補集合、TVT 形成、§14.4 fallback の判断、局所仮想計算、経済評価、支払い・補償、早期終了、実交通上の未確定 visit 登録タイミング、上位 TVT 制御の関数名・実装場所。
- 最新の順位状態部品仕様の正本は **§25.25.30** を参照する。本節の未確定リストは、driver 実装前時点の歴史的記録として残す。

#### 25.25.28.23 実装再開情報

**実装者が最初に確認するファイルと節（順序）：**

1. 設計メモ §25.25.28
2. `uxsim/order_control_baseline_collector.py`
3. `uxsim/order_control_baseline_snapshot.py`
4. `diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`
5. `tests_order_control_baseline_snapshot.py`
6. 新規作成する driver モジュール
7. 新規作成する driver テスト

**実装時の作業順：**

1. result dataclass
2. driver 固有入力 validation
3. Node 別 export 件数合計 helper
4. copy 直後確認 helper
5. horizon 余白確認 helper
6. real_W 軽量不変確認 helper
7. 公開 driver 関数
8. snapshot docstring 修正
9. 専用テスト
10. 関係テストと診断
11. 欠陥探索レビュー
12. 実装結果のメモ更新

**次の直接作業：**

- 初期正式 driver の残存設計は本 §25.25.28 で確定した。
- 次は driver 本体、専用テスト、snapshot docstring 修正の実装。
- 新規 driver：`uxsim/order_control_baseline_driver.py`
- 新規テスト：`tests_order_control_baseline_driver.py`
- snapshot 本体は変更せず docstring だけを明確化。
- `uxsim.py`、collector、`uxsim/__init__.py`、既存診断は変更しない。
- 実装中に新しい制度判断を追加しない。
- 早期終了へ戻らない。
- 既存コードの動作変更が必要と判明した場合は、勝手に変更範囲を拡大せず作業を止めて理由を報告する。
- 最新保存済みコミットは `142d235`。
- 今回のメモ更新は未コミット、未 push。
- `diagnostics/order_control.zip` には触れない。

**2026-09-01 更新：**

- §25.25.28 に基づく固定 horizon 正式 driver の実装は完了した。
- 実装・検証・独立監査・監査後テスト補強の記録は **§25.25.29** を参照する。
- 上記「次は driver 本体、専用テスト、snapshot docstring 修正の実装」は完了済みである。
- 今後の再開は **§25.25.29.23** を参照する。
- §25.25.28 記録時点の最新保存済みコミットは `142d235` だった。
- その後、§25.25.28 の実装可能な仕様を記録した `6d30a9f` が作成され、`origin/feature/intersection-order-control` へ push された。
- §25.25.28 に基づく現在の未コミット実装は `6d30a9f` を基準としている。
- 現在の実装・検証・独立監査結果と再開情報は **§25.25.29** を参照する。

**コミット履歴の関係（2026-09-01 時点）：**

| 区分 | 内容 |
|------|------|
| `142d235` | §25.25.28 作成前の保存済み状態 |
| `6d30a9f` | §25.25.28 を含む、現在の実装の基準コミット |
| 現在の作業ツリー | `6d30a9f` の上にある未コミットの driver 実装・テスト・docstring・メモ更新 |

#### 25.25.29 正式driverの実装・検証・独立監査結果

記録日：2026-09-01

本 §25.25.29 を、§25.25.28 に基づく実装結果、テスト結果、初回レビュー、Cursor Grok 4.6 による独立監査、監査後のテスト補強、および今後の再開情報の **正本** とする。§25.25.28 は実装前仕様の正本として維持する。既存 §25.25.1 から §25.25.28 は削除しない。

#### 25.25.29.1 実装の位置づけ

**確定したこと：** §25.25.28 を実装前仕様の正本として、固定 horizon 正式 driver を実装した。

**何を実装したか：** 既存の `World.copy()`、`OrderControlBaselineCollector`、`register_snapshot_fixed_visits()`、fork 側 `exec_simulation()` を正しい順序で接続する上位調整処理。`real_W` を進めず、copy した `fork_W` だけを指定 horizon 分進め、snapshot 開始時に固定した visit について到着・通過情報を collector へ記録する。

**何を実装していないか：** 早期終了、TVT 形成、right_of_entry vehicle 選定、P-1 候補集合、局所仮想計算、経済評価、支払い、補償、順位確定。初期正式 driver は **固定 horizon 一括方式** のままである。

**正常時：** horizon 内に到着・通過情報を取得できないことは正常な研究結果であり、driver 異常ではない。全固定 visit の通過完了を成功条件にしない。

**検証の経緯：** 実装担当モデル（Composer 2.5）による初回実装・専用テスト作成の後、初回レビューでテスト実効性と例外メッセージを補修した。続いて、**同じ Cursor チャット内でモデルを Cursor Grok 4.6 へ変更**し、過去の完了報告・自己評価・テスト成功報告を正解とせず、§25.25.28 と実ファイルだけを根拠とする独立監査を行った。監査後、Moderate 指摘 Q1 から Q5 を専用テストへ補強した。

非技術的には、本物の交通を変えず、複製交通だけを先へ進め、開始時点で観察対象だった Vehicle の将来到着・通過情報を集める正式な入口を実装した。実装とテストを同じモデルが作ると同じ思い込みが双方へ入り得るため、異なるモデルによる独立監査を追加し、「正しく見える」だけでなく設計と実ファイルの照合で確認した。

#### 25.25.29.2 変更ファイル

**新規作成：**

| ファイル | 内容 |
|----------|------|
| `uxsim/order_control_baseline_driver.py` | 正式 driver 本体 |
| `tests_order_control_baseline_driver.py` | 専用テスト |

**既存ファイル変更：**

| ファイル | 変更内容 |
|----------|----------|
| `uxsim/order_control_baseline_snapshot.py` | **docstring のみ**（登録順序の誤読防止） |

**変更していない主要ファイル：**

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/analyzer.py`
- `uxsim/__init__.py`
- 既存テスト（collector、snapshot、collector_uxsim 等）
- 既存診断（`diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py` 等）

新規 driver 本体は、初回実装確認時点で **312 行** だった（2026-09-01 時点の記録。将来の変更で変わり得る）。

#### 25.25.29.3 公開API

**実装済み result dataclass（非 frozen）：**

```python
@dataclass
class OrderControlBaselineForkResult:
    collector: OrderControlBaselineCollector
    target_node_names: tuple[str, ...]
    baseline_timestep_T: int
    configured_horizon_steps: int
    fork_steps_executed: int
    final_fork_timestep: int
    registered_visit_count: int
```

**実装済み公開関数：**

```python
def run_snapshot_fixed_baseline_fork(
    real_W: World,
    *,
    target_node_names: list[str] | tuple[str, ...],
    baseline_horizon_steps: int,
) -> OrderControlBaselineForkResult:
```

**契約：**

- `real_W` だけ positional。`target_node_names` と `baseline_horizon_steps` は keyword-only。
- `uxsim.order_control_baseline_driver` から直接 import する（`uxsim/__init__.py` は変更していない）。
- `fork_W`、`return_code`、`early_terminated`、Node 別制度状態は返さない。
- 例外時は result を返さない。

非技術的には、後続処理へ巨大な `fork_W` 全体を渡さず、観察記録と実行条件だけを明確な結果オブジェクトとして渡す API である。

#### 25.25.29.4 driverの実際の処理順

実装は §25.25.28 の 22 ステップと **変更なし** で対応する。

| 順 | 処理 | 実装箇所（概略） |
|----|------|------------------|
| 1 | `target_node_names` の容器型確認 | `_validate_and_freeze_target_node_names` |
| 2 | 空 list / 空 tuple 拒否 | 同上 |
| 3 | `fixed_target_node_names` として tuple 固定 | 同上 |
| 4 | `baseline_horizon_steps` の型・範囲確認 | `_validate_baseline_horizon_steps` |
| 5 | `real_W._order_control_baseline_collector is None` 確認 | `run_snapshot_fixed_baseline_fork` 入口 |
| 6 | `real_W` の T、TIME、collector 保存 | 同上 |
| 7 | `baseline_timestep_T` 保存 | 同上 |
| 8 | `real_W.copy()` | 同上 |
| 9 | copy 直後の fork 確認 | `_validate_copied_fork` |
| 10 | fresh collector 生成 | `OrderControlBaselineCollector()` |
| 11 | `fork_W` だけへ collector 設定 | 同上 |
| 12 | snapshot 固定集合登録 | `register_snapshot_fixed_visits` |
| 13 | 登録直後の件数照合 | `_validate_registered_visit_count` |
| 14 | 全対象 Node 合計 0 件 → real_W 不変確認後 0 step result | `_build_empty_baseline_result` |
| 15 | 合計 ≥ 1 → horizon 後 1 timestep 余白検査 | `_validate_remaining_baseline_steps` |
| 16 | forward 前 `fork_W.T` 保存 | `fork_timestep_before` |
| 17 | `exec_simulation()` 1 回 | `fork_W.exec_simulation(duration_t2=...)` |
| 18 | 指定 horizon 分の T 進行確認 | `_validate_completed_fork_forward`（第 1 段） |
| 19 | World 終端非到達確認 | 同上（第 2 段） |
| 20 | forward 後 collector 件数照合 | `_validate_registered_visit_count` |
| 21 | `real_W` 不変確認 | `_validate_real_world_unchanged` |
| 22 | 正常 result 返却 | `_build_completed_baseline_result` |

非技術的には、入力を先に検査し、観察対象を確定してから必要な場合だけ仮想計算を進め、すべての確認に成功した後で結果を返す流れである。

#### 25.25.29.5 入力validation

##### target_node_names

**受け付ける：** `list`、`tuple`（subclass 含む。`isinstance` による判定）。

**拒否する：** `str`、`bytes`、`set`、`generator`、その他の一般 `Iterable`。空 list / 空 tuple は `World.copy()` 前に `ValueError`。

**委譲：** 各 Node 名の意味的検証（存在、eligibility、重複等）は `register_snapshot_fixed_visits()` へ委譲。

**空 Node 一覧の例外メッセージに含む情報：**

- 少なくとも 1 つの対象 Node 名が必要
- 空 Node 一覧は入力エラー
- 非空 Node 一覧を指定した結果、全対象 Node 合計の登録 visit が 0 件となる正常ケースとは異なる

##### baseline_horizon_steps

**受け付ける：** bool ではない Python `int`、1 以上。

**拒否する：** `True`、`False`、`0`、負数、`float`、NumPy 整数、その他の型。

**例外メッセージ：** 実際の値（`value=...`）と型名（`type=...`）、および bool ではない Python int であること。

**NumPy 整数拒否の理由：** 乗算できないためではない。既存 order-control 系の検証規則に合わせ、初期 API の受付型を Python `int` に限定して一貫性を保つため（§25.25.28.5 と同旨）。

#### 25.25.29.6 real_Wとfork_Wの分離

- `real_W._order_control_baseline_collector` は入口で `None` でなければならない。非 `None` なら copy 前に `ValueError`。
- `real_W` へ collector を一時的にも設定しない。
- copy 後：`fork_W is not real_W`、`fork_W.T == baseline_timestep_T`、`fork_W._order_control_baseline_collector is None` を確認。不一致は `RuntimeError`。
- `World.copy()` 例外は変換せず伝播。copy 戻り値の `None` 確認は追加していない。
- 正常終了時に `real_W.T`、`real_W.TIME`、`real_W._order_control_baseline_collector` の不変を確認。
- 全 Vehicle、全 Node、全 Link、RNG の詳細比較は本番 driver へ入れていない。詳細な参照独立性は既存 fork 診断と専用テストの責任。

非技術的には、本物の交通と複製交通を取り違えず、仮想計算が本物の進行時刻や記録設定を変えないことを守るための確認である。

#### 25.25.29.7 collectorとsnapshot固定集合

- copy 直後確認後に `OrderControlBaselineCollector()` を生成し、`fork_W` だけへ設定する。
- driver が新規生成した collector の空状態を private 属性で重複検査しない。
- `register_snapshot_fixed_visits()` を fork forward 前に **1 回だけ** 呼ぶ。
- 戻り値は全対象 Node 合計の登録 visit 数。登録直後と forward 後に公開 export API で件数照合する。
- snapshot 登録例外は原則そのまま伝播。登録失敗時に result を返さない。
- 固定集合外通知では登録件数を増やさない（collector 既存契約に委譲。driver テストで接続を確認）。

**登録順序の実証（event list）：** `test_register_snapshot_fixed_visits_called_once_before_exec_simulation` で `events == ["register", "exec"]` を確認した。

非技術的には、仮想計算を始める前に観察対象を固定し、開始後に新しく現れた Vehicle を今回の観察対象へ混入させないためである。

#### 25.25.29.8 全対象Node合計0件

**0 step 正常終了条件：** `registered_visit_count == 0`（特定 Node ではなく **全対象 Node 合計**）。

- 特定 Node だけ 0 件でも、他 Node に visit があれば固定 horizon を実行する（`test_partial_node_zero_still_forwards_when_other_node_has_visits`）。
- 全対象 Node 合計 0 件の場合だけ、余白検査と `exec_simulation()` を省略し、`real_W` 不変を確認して通常と同じ dataclass を返す。
- **全対象 Node 合計 0 件かつ World の残り step 数が horizon 後 1 timestep 余白を満たさない場合でも**、forward しないため正常終了する（監査後テストで直接確認。下記）。

**0 件 result：**

```python
OrderControlBaselineForkResult(
    collector=collector,
    target_node_names=fixed_target_node_names,
    baseline_timestep_T=baseline_timestep_T,
    configured_horizon_steps=baseline_horizon_steps,
    fork_steps_executed=0,
    final_fork_timestep=baseline_timestep_T,
    registered_visit_count=0,
)
```

**監査後追加テスト `test_zero_total_registered_visits_skips_insufficient_margin_validation`：**

| 設定 | 値 |
|------|-----|
| `tmax` | 250 |
| `T` | 200 |
| `horizon` | 50 |
| `remaining_steps` | 50 |
| `required_steps` | 51 |
| Vehicle | なし |
| `target_node_names` | 非空 |

**確認：** `ValueError` なし、`registered_visit_count == 0`、`fork_steps_executed == 0`、`final_fork_timestep == 200`、`configured_horizon_steps == 50`、`exec_simulation()` 非呼出、`real_W` 不変。

#### 25.25.29.9 horizon後の1 timestep余白

- 全対象 Node 合計 ≥ 1 の場合だけ検査する。
- 条件：`baseline_horizon_steps + 1 <= fork_W.TSIZE - fork_W.T`
- 不足は `ValueError`。horizon を自動短縮しない。
- 例外メッセージに `baseline_horizon_steps`、`remaining_steps`、`required_steps`、`fork_W.T`、`fork_W.TSIZE`、および World 終端前に少なくとも 1 timestep を残す旨を含む。

**確認済みテスト：**

- `test_succeeds_when_remaining_steps_equals_horizon_plus_one`（`remaining_steps == horizon + 1` で成功）
- `test_rejects_when_remaining_steps_equals_horizon_only`（`remaining_steps == horizon` で `ValueError`）
- `test_succeeds_with_sufficient_margin_example`（十分余白で成功）
- `test_does_not_automatically_shorten_horizon`（自動短縮なし）
- `test_simulation_terminated_not_called`、`test_analyzer_basic_analysis_not_called`（終端処理回避）

**余白不足メッセージ（`test_rejects_when_remaining_steps_equals_horizon_only` で assert）：**

- `baseline_horizon_steps=50`
- `remaining_steps=50`
- `required_steps=51`
- `fork_W.T=200`
- `fork_W.TSIZE=250`
- World 終端前に少なくとも 1 timestep を残す契約

#### 25.25.29.10 固定horizon一括実行

```python
fork_W.exec_simulation(
    duration_t2=baseline_horizon_steps * fork_W.DELTAT
)
```

- 呼出しは 1 回。1 timestep 反復ではない。早期終了なし。
- `exec_simulation()` の戻り値は result へ保存せず、主要成功条件にもしない。T の進行を事後確認する。

**専用テスト：** `test_calls_exec_simulation_once`、`test_exec_simulation_duration_matches_horizon`、`test_advances_timestep_by_configured_horizon`、`test_simulation_terminated_not_called`、`test_analyzer_basic_analysis_not_called`。

#### 25.25.29.11 実行後の事後確認

実装条件：

```text
fork_W.T == fork_timestep_before + baseline_horizon_steps
fork_W.T < fork_W.TSIZE
exported_visit_count == registered_visit_count  （forward 後）
real_W.T / TIME / collector 不変  （正常終了時）
```

各不一致は `RuntimeError`。result はすべての事後確認後にだけ返す。

**監査後補強で公開 driver 経路または専用分岐を追加確認：**

- T が期待値より多く進んだ場合の拒否（`test_runtime_error_when_forward_advances_more_than_configured_horizon`）
- forward 後に World 終端へ到達した異常を公開 driver が拒否（`test_runtime_error_when_public_driver_forward_reaches_world_termination`）
- `real_W.TIME` だけ変更した場合の検出（`test_runtime_error_when_real_world_time_changes_before_success_return`）
- `real_W._order_control_baseline_collector` だけ変更した場合の検出（`test_runtime_error_when_real_world_collector_changes_before_success_return`）

##### World終端異常の検出順序

本番 driver の `_validate_completed_fork_forward` は次の順で事後確認する。

1. 指定 horizon 分の T 進行確認（`fork_W.T == fork_timestep_before + baseline_horizon_steps`）
2. World 終端非到達確認（`fork_W.T < fork_W.TSIZE`）

通常の事前余白条件を通過した場合、正しい期待終了時刻は少なくとも `TSIZE - 1` である。その状態から patched `exec_simulation()` が `fork_W.T` を `TSIZE` へ進めると、実際の T は期待終了 T より大きくなるため、**公開 driver では先に進行量不一致として `RuntimeError` になる**（メッセージ：`did not advance by baseline_horizon_steps`）。

一方、次の終端専用条件：

```text
fork_W.T == expected_fork_timestep_after
かつ
fork_W.T >= fork_W.TSIZE
```

は、正常な事前余白条件と両立しない。この終端専用分岐は、内部 helper を直接呼ぶ既存テスト `test_runtime_error_when_world_reaches_termination_after_forward` が担当する。

これは仕様変更ではなく、事前条件・事後確認順序・テスト責任の関係を明確にした記録である。

#### 25.25.29.12 例外と部分結果

**ValueError：** `target_node_names` 型不正、空 `target_node_names`、`baseline_horizon_steps` 型・範囲不正、`real_W` に collector 設定済み、1 timestep 余白不足。

**RuntimeError：** copy 直後の内部不整合、登録件数不一致、T 進行不一致、World 終端到達、forward 後件数不一致、`real_W` 不変違反。

**元例外を原則伝播：** `World.copy()`、collector 生成、snapshot 登録、`exec_simulation()`。

**途中例外時：** result を返さない。部分 collector を返さない。rollback しない。自動再試行しない。別 fork を作らない。driver 本体の `real_W` 不変確認は **正常終了時だけ**。

**専用テストで確認：** `exec_simulation()` 例外後にも `real_W` の T、TIME、collector が不変（`test_no_result_on_exec_simulation_exception` 強化後）。

非技術的には、途中で中断された仮想調査を完成済み結果として返さず、元の失敗理由を隠さないための扱いである。

#### 25.25.29.13 result

**通常 result：**

```python
OrderControlBaselineForkResult(
    collector=collector,
    target_node_names=fixed_target_node_names,
    baseline_timestep_T=baseline_timestep_T,
    configured_horizon_steps=baseline_horizon_steps,
    fork_steps_executed=baseline_horizon_steps,
    final_fork_timestep=fork_W.T,
    registered_visit_count=registered_visit_count,
)
```

- `collector` に取得済み・未取得情報を保持。`target_node_names` は tuple。
- `configured_horizon_steps` と `fork_steps_executed` を区別する。
- 0 件時は `fork_steps_executed == 0`。通常時は `fork_steps_executed == configured_horizon_steps`。
- 情報未取得は `None` のまま。全固定 visit の通過完了を成功条件にしない。
- `fork_W` は返さない。result 取得後の collector と dataclass は可変（非 frozen は §25.25.28 で確定した仕様。後続が誤って変更しない責任を持つ）。

独立監査では、dataclass 非 frozen 自体の専用テストがないことは **Minor** と判定し、今回の監査後補修対象にはしなかった。

#### 25.25.29.14 snapshot docstring

`uxsim/order_control_baseline_snapshot.py` の `register_snapshot_fixed_visits` の **docstring のみ** を修正した。

**修正後の説明順：**

```text
real_W を baseline 開始時点 T まで通常実行
→ real_W.copy()
→ copy 直後の fork_W を渡す
→ fork baseline forward 前に snapshot 登録
```

- `fork_W.T == T` では timestep T は未処理。
- 関数本体、引数、戻り値、validation は変更していない。
- 以前の「fork forward 後に登録する」と誤読できる表現を修正した。
- 独立監査でも、変更が docstring のみであり、§25.25.28、snapshot 設計、fork probe と整合すると確認された。

#### 25.25.29.15 内部helper

| helper | 責任 |
|--------|------|
| `_validate_and_freeze_target_node_names` | 容器型、空拒否、tuple 固定 |
| `_validate_baseline_horizon_steps` | horizon の型と範囲 |
| `_count_exported_baseline_visits` | 対象 Node 別 export 件数の合計 |
| `_validate_registered_visit_count` | 登録数と export 件数の照合 |
| `_validate_copied_fork` | copy 直後の identity、T、collector |
| `_validate_remaining_baseline_steps` | horizon 後の 1 timestep 余白 |
| `_validate_completed_fork_forward` | T 進行と World 終端非到達 |
| `_validate_real_world_unchanged` | `real_W` の T、TIME、collector |
| `_build_empty_baseline_result` | 全対象 Node 合計 0 件の result |
| `_build_completed_baseline_result` | 通常完了 result |

helper 構成は §25.25.28.17 の第一候補どおり。短い高度な Python 表現へ詰め込まず、公開関数から処理順を追える構造を採用した。

#### 25.25.29.16 初回専用テストと実装後補修

**初回実装後：** 専用テスト **56 件**。

**初回レビュー・補修後：** **60 件**。

**初回実装・テスト作業中の補修（制度設計変更ではない）：**

- `_junction_target_names` の typo 修正
- `exec_simulation` mock の再帰・pickle 問題修正
- `Analyzer.basic_analysis` と `simulation_terminated` の追跡方法修正
- 未到着・未通過テストの World 配置調整
- passage 記録テスト追加
- World 終端テストを helper 直接検証へ調整
- 未使用 import 削除

**初回レビューで 60 件までに補修した内容：**

- horizon 不正メッセージへ実際の値と型名を追加
- 空 Node 一覧メッセージへ、全対象 Node 合計 0 件との違いを追加
- snapshot 登録順序を event list で確認するテストへ強化
- 固定集合外 Vehicle 通知を fork forward 中に発生させるテストへ変更
- 登録直後の件数不一致テスト追加
- forward 後の件数不一致テスト追加
- `real_W` 不変違反テスト追加
- `World.copy()` 元例外伝播テスト追加
- 未取得情報テスト名を `test_succeeds_when_baseline_information_remains_unresolved` へ変更

これらは正式 driver の制度設計変更ではなく、実装・テスト・診断の正確性を高める補修である。

#### 25.25.29.17 Cursor Grok 4.6による独立監査

**監査の実施方法：**

- 実装担当時には **Composer 2.5** を使用していた。
- ダブルチェックでは、**現在の Cursor チャット内でモデルを Cursor Grok 4.6 へ変更**した（新しい Cursor チャットは使用していない）。
- 過去の完了報告、自己評価、テスト成功報告を正解として扱わないよう明示した。
- §25.25.28 と実ファイルだけを根拠として監査した。
- コード、テスト、診断、Markdown を変更せず、**テストや診断も実行しない静的監査**だった。

**監査内容：**

- 仕様から実装への順方向照合
- 実装から仕様への逆方向照合
- 全 60 テスト（当時）について、名前だけでなく準備状態、patch、mock、assertion を確認
- mock と `World.copy()` の pickle の関係を確認
- `real_W` 不変性の静的追跡
- collector 件数照合の限界の検討
- snapshot docstring 差分の確認
- 変更範囲の確認
- 反証型の境界検討

**独立監査の判定：**

| 区分 | 結果 |
|------|------|
| Critical 問題 | **なし** |
| Major 問題 | **なし** |
| 本番 driver と §25.25.28 | 公開契約、処理順、例外境界と **一致** |
| snapshot 変更 | docstring のみ、仕様と整合 |
| コミット前必須の本番コード修正 | **なし** |
| Moderate | 回帰テストで直接固定されていない経路を指摘（Q1〜Q5） |
| Minor | 限定的なテスト重複や未確認項目 |
| 本番への追加 validation / identity 再照合 | **不要**（登録時保証済み不変条件の重複検査は行わない方針を維持） |

非技術的には、実装とテストを作ったときと異なるモデルに、「正しいという報告を信用せず、設計と実ファイルを一から照合する」監査を行わせた。

#### 25.25.29.18 独立監査後のテスト補強

独立監査で本番 driver に Critical または Major 問題はなかった。将来の回帰を防ぐため、Moderate 指摘 **Q1 から Q5** をコミット前に補修した。**本番 driver、snapshot docstring、設計メモは変更せず、`tests_order_control_baseline_driver.py` だけ**を変更した。

##### Q1：全対象 Node 合計 0 件で余白検査をスキップ

**追加：** `test_zero_total_registered_visits_skips_insufficient_margin_validation`（詳細は §25.25.29.8）。

##### Q2：T 過剰と World 終端異常

**追加（いずれも公開 `run_snapshot_fixed_baseline_fork()` 経由）：**

- `test_runtime_error_when_forward_advances_more_than_configured_horizon`
- `test_runtime_error_when_public_driver_forward_reaches_world_termination`

Q2-2 では進行量確認が World 終端確認より先のため、公開 driver は T 進行量不一致として拒否する。終端専用分岐は `test_runtime_error_when_world_reaches_termination_after_forward`（helper 直接）が担当する。

##### Q3：real_W 不変確認

**追加：**

- `test_runtime_error_when_real_world_time_changes_before_success_return`（T と collector は変更しない）
- `test_runtime_error_when_real_world_collector_changes_before_success_return`（T と TIME は変更しない）

**強化：** `test_no_result_on_exec_simulation_exception`（例外後の `real_W` T / TIME / collector 不変）。

人工的な変更は `finally` で復元する。

##### Q4：余白不足メッセージ

**強化：** `test_rejects_when_remaining_steps_equals_horizon_only`（§25.25.29.9 の必須値・意味を assert）。

##### Q5：テスト名と確認内容の一致

| 改名前 | 改名後 |
|--------|--------|
| `test_fork_world_is_distinct_from_real_world` | `test_zero_visit_run_leaves_real_world_unchanged` |

同一オブジェクト copy の異常検出は `test_runtime_error_when_copy_returns_same_object` が担当する。

#### 25.25.29.19 最終的な専用テスト構成

**独立監査後補修を含む最終状態（2026-09-01）：**

| 項目 | 値 |
|------|-----|
| `test_*` 関数定義数 | **65** |
| `TESTS` 一覧要素数 | **65** |
| `TESTS` 一覧にない `test_*` | なし |
| `test_*` ではない `TESTS` 要素 | なし |
| `TESTS` 重複 | なし |
| `test_*` 関数名の重複定義 | なし |
| 改名前 `test_fork_world_is_distinct_from_real_world` | 残っていない |
| 改名後 `test_zero_visit_run_leaves_real_world_unchanged` | 定義・登録済み |
| 実行結果 | **65 件すべて成功** |

**主なテスト区分：** 入力 validation、copy と collector、snapshot 登録、全対象 Node 合計 0 件、1 timestep 余白、固定 horizon 一括実行、collector 結果、不整合と例外、result 契約。

**重要テスト名（代表）：**

- `test_register_snapshot_fixed_visits_called_once_before_exec_simulation`
- `test_partial_node_zero_still_forwards_when_other_node_has_visits`
- `test_zero_total_registered_visits_returns_zero_step_result`
- `test_zero_total_registered_visits_skips_insufficient_margin_validation`
- `test_succeeds_when_remaining_steps_equals_horizon_plus_one`
- `test_rejects_when_remaining_steps_equals_horizon_only`
- `test_runtime_error_when_forward_advances_more_than_configured_horizon`
- `test_runtime_error_when_public_driver_forward_reaches_world_termination`
- `test_simulation_terminated_not_called`
- `test_analyzer_basic_analysis_not_called`
- `test_succeeds_when_baseline_information_remains_unresolved`
- `test_outside_fixed_set_vehicle_does_not_increase_count`
- `test_runtime_error_when_registration_count_mismatch_after_snapshot_registration`
- `test_runtime_error_when_registration_count_mismatch_after_baseline_forward`
- `test_runtime_error_when_real_world_changes_before_success_return`
- `test_runtime_error_when_real_world_time_changes_before_success_return`
- `test_runtime_error_when_real_world_collector_changes_before_success_return`
- `test_world_copy_propagates_original_exception`
- `test_no_result_on_exec_simulation_exception`
- `test_completed_result_fields`

##### 監査で Minor と判断し、今回整理しなかった事項

- snapshot 登録例外のテストに一部重複がある
- 両方の情報が `None` となるシナリオに一部重複がある
- 空 list と空 tuple のメッセージ assertion は完全には同一でない
- 0 件 result で除外フィールドを再確認していない
- keyword-only を `TypeError` で確認する専用テストがない
- dataclass 非 frozen の専用テストがない

これらは研究結果または主要な正式 driver 契約へ実質的な影響を与えない Minor 事項であり、今回のコミット前補修対象にはしなかった。

#### 25.25.29.20 回帰テストと診断

監査後補修後に実行済み（2026-09-01）：

1. `python -m py_compile tests_order_control_baseline_driver.py`
2. `python tests_order_control_baseline_driver.py`
3. `python tests_order_control_baseline_collector.py`
4. `python tests_order_control_baseline_snapshot.py`
5. `python tests_order_control_baseline_collector_uxsim.py`
6. `python diagnostics/order_control/tvt_baseline_snapshot_fork_probe.py`
7. `git diff --check`
8. `git status --short`

**結果：**

| 対象 | 結果 |
|------|------|
| driver tests | **65 件すべて成功** |
| collector tests | 成功 |
| snapshot tests | 成功 |
| collector_uxsim tests | 成功 |
| fork probe | 成功 |
| py_compile | 成功 |
| git diff --check | 成功 |

初回実装時の driver モジュール import 確認も成功している。

#### 25.25.29.21 欠陥探索レビュー結果

- 初回実装レビューでテストの実効性と例外メッセージを補強した。
- Cursor Grok 4.6 による独立監査を行った。
- 独立監査で **Critical 問題は確認されなかった**。
- 独立監査で **Major 問題は確認されなかった**。
- 本番 driver の仕様違反は確認されなかった。
- 独立監査で指摘された Moderate の回帰テスト不足（Q1〜Q5）をコミット前に補修した。
- 補修後、専用テスト 65 件と関係テスト・診断が成功した。
- 本番 driver を補修のために変更していない。
- snapshot docstring を監査後補修で変更していない。
- 登録時の保証を本番 driver で重複検査する変更を加えていない。
- 初期 driver へ早期終了や TVT 制度処理を追加していない。
- **現時点で、コミットを妨げる Critical または Major な未解決問題は確認されていない**（将来の変更で再確認が必要である）。

#### 25.25.29.22 現在の変更範囲

**本記録作業前の作業ツリー：**

```text
 M uxsim/order_control_baseline_snapshot.py
?? tests_order_control_baseline_driver.py
?? uxsim/order_control_baseline_driver.py
?? diagnostics/order_control.zip
```

**本記録作業によりさらに変更：**

- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`（§25.25.29 追加、§25.25.28.23 追記）
- `ORDER_EXCHANGE_PROGRESS.md`（2026-09-01 エントリ追加）

**明記：**

- driver と driver テストは新規未追跡
- snapshot は docstring だけの変更
- ZIP は既存の未追跡ファイルであり未接触・コミット対象外
- `uxsim.py`、collector、analyzer、`uxsim/__init__.py`、既存テスト、既存診断は変更していない
- **git add、git commit、git push はまだ行っていない**

**基準コミット（2026-09-01 時点）：**

- 今回の未コミット実装およびメモ更新の基準となる最新保存済みコミットは `6d30a9f`（`Document implementation-ready specification for the fixed-horizon full-World baseline driver`）。
- `6d30a9f` は `origin/feature/intersection-order-control` へ push 済みである。
- driver、driver テスト、snapshot docstring、§25.25.29、進捗メモは、`6d30a9f` の上にある未コミット変更である。
- `diagnostics/order_control.zip` は、その未コミット変更とは別の既存未追跡ファイルであり、今回のコミット対象外である。

#### 25.25.29.23 実装再開情報

**完了済み：**

- 正式 driver 本体、snapshot docstring、専用テストの実装
- 専用テスト 65 件と関係回帰テスト・診断の成功
- 初回レビューで見つかった不足の補修
- Cursor Grok 4.6 による独立監査
- 独立監査の Moderate 指摘 Q1〜Q5 のコミット前テスト補強
- 本記録（§25.25.29、進捗メモ 2026-09-01）

**次の直接作業：**

1. コード差分、テスト差分、docstring 差分、メモ差分、変更範囲の **最終確認**
2. 確認後、`uxsim/order_control_baseline_driver.py`、`tests_order_control_baseline_driver.py`、snapshot docstring、設計メモ、進捗メモを **同じコミット** へ保存する
3. コミット前に `git diff --check`、変更ファイル一覧、テスト件数（65）を再確認する
4. コミット後に最新コミットと残存変更を確認する
5. **git push はコミット確認後に別の指示で行う**

**基準コミットとコミット対象（2026-09-01 時点）：**

- 実装差分とメモ差分の最終確認を再開する場合の基準コミットは `6d30a9f` である。
- `6d30a9f` から現在の作業ツリーに、正式 driver 本体、専用テスト、snapshot docstring、設計メモ、進捗メモの変更がある。
- コミット対象は次の **5 ファイル** である。
  - `uxsim/order_control_baseline_driver.py`
  - `tests_order_control_baseline_driver.py`
  - `uxsim/order_control_baseline_snapshot.py`
  - `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`
  - `ORDER_EXCHANGE_PROGRESS.md`
- `diagnostics/order_control.zip` はコミット対象に含めない。

**再開時に最初に読む節：** §25.25.29 → §25.25.28（実装前仕様）→ `uxsim/order_control_baseline_driver.py` → `tests_order_control_baseline_driver.py`

**行わないこと：**

- `diagnostics/order_control.zip` をコミットしない
- 次の制度実装（TVT 形成、早期終了等）へ自動的に進まない
- 初期 driver へ早期終了を追加しない

**2026-09-01 更新（正式 driver 保存後・順位状態仕様確定）：**

- 正式 baseline driver はコミット `bd24ad1` として `origin/feature/intersection-order-control` へ push 済みである。
- Node 別 TVT **順位状態**（確定順位ブロック・未確定 visit 集合）の実装前仕様を **§25.25.30** で確定した。
- **次の直接作業：** §25.25.30 に従い `uxsim/order_control_tvt_node_rank_state.py` と `tests_order_control_tvt_node_rank_state.py` を実装する。
- 評価状態、baseline driver 呼出管理、実交通上の未確定 visit 登録タイミング、uxsim.py 接続は §25.25.30 の対象外のままである。
- 最新の順位状態部品仕様は **§25.25.30** を参照する。
- 本節の「次の直接作業」（正式 driver のコミット保存）は完了済みである。上記 `6d30a9f` 基準・5 ファイルコミット対象の記録は歴史的記録として残す。

#### 25.25.30 Node別TVT順位状態の実装前仕様

**記録日：** 2026-09-01

本 **§25.25.30** を、Node 別の確定順位ブロック、未確定 visit 集合、visit identity、状態更新 API、不変条件、例外、専用テストに関する**最新の正本**とする。

- **§25.25.28** は正式 baseline driver の実装前仕様として維持する。
- **§25.25.29** は正式 baseline driver の実装・検証・独立監査結果として維持する。
- 既存の設計記録は削除しない。

##### 25.25.30.1 位置づけ

正式 baseline driver 完成後の次の制度実装へ進むため、Node 別の順位状態を独立部品として設計した。

今回の部品は、**確定順位ブロック**と**未確定 visit 集合**を保存する。TVT 評価済みかどうかなどの**評価状態は保存しない**。外部制度処理が確定した visit 列を安全に保存する部品である。誰を、なぜ、どの制度ケースで確定するかは判断しない。状態部品は順位保存と整合性検査だけを担当する。

- 正式 baseline driver、collector、snapshot は変更しない。
- `uxsim.py` へ今回接続しない。
- 早期終了は扱わない。

非技術的には、各交差点（Node）について「順番が決まった車両」と「まだ順番が決まっていない車両」を分けて保存する**帳簿**である。ただし、順位の単位は Vehicle そのものではなく、**対象 Node についての特定 visit**（その Node への 1 回の通過・接近イベント）である。同一 Vehicle が同じ Node を複数回通過する場合、visit ごとに別の順位エントリとなる。

**順位状態部品の能力（確定対象の範囲）：**

- 順位状態部品は、確定対象を**意思決定窓内 visit だけ**に限定しない
- **意思決定窓外**の visit でも、未確定 visit として**事前登録済み**なら、`confirm_visits_in_order()` の対象にできる
- `confirm_visits_in_order()` は、意思決定窓内外を検査しない。参加・非参加も検査しない
- 外部制度処理が渡した有序 VisitKey 列を、その順序のまま確定する
- 確定 API が要求するのは、各 VisitKey が正しい形式で、確定済みではなく、**未確定集合へ事前登録済み**であること
- 意思決定窓内外の区別は、順位状態部品の保存契約ではなく、**外部制度処理が最終確定 visit 列を作る際の制度判断**である

非技術的には、順位帳簿は「この Vehicle が意思決定窓の内側か外側か」を判断せず、外部で確定した順番を書き込む。

**§25.25.30 で実装可能な仕様として確定したもの：** Node 別 **TVT 順位状態部品**（確定順位ブロック、未確定 visit 集合、登録 API、一括確定 API、`K_confirmed`、原子的更新、読取・export、不変条件、例外、専用テスト契約）。

**まだ実装可能な仕様として確定していないもの（本順位状態部品の外）：** 意思決定窓内 baseline 順位の構築、right_of_entry vehicle の選定、P の取得、P-1 条件による TVT 候補集合の形成、意思決定窓外を含む取引候補の選定、TVT 取引順位の計算、TVT 取引結果による最終確定 visit 列の作成、最終確定 visit 列を順位状態部品へ渡す上位制度処理、§14.4 を適用するかどうかの判断。

「Node 別 TVT 順位状態を実装可能な仕様として確定した」という記述を、「TVT 候補 Vehicle の順位計算まで実装可能になった」という意味に**しない**。

##### 25.25.30.2 対象範囲と対象外

**今回含むもの：**

- Node 別の確定順位ブロック
- Node 別の未確定 visit 集合
- 未確定 visit の明示的登録
- 外部制度処理が決めた有序 visit 列の一括確定
- `K_confirmed_before`
- `K_confirmed_after`
- visit identity
- 読取 API
- export API
- 原子的更新
- 不変条件
- 例外
- 専用テスト

**今回含まないもの：**

- 到着済み Vehicle の判定
- baseline 到着順位の構築
- 意思決定窓の検知
- 先頭に連続する非参加 Vehicle の抽出
- right_of_entry vehicle 選定
- P 取得
- P-1 候補集合
- 候補 Vehicle 全員の情報充足判定
- TVT 取引成立・不成立の判断
- TVT 取引順位の計算
- §14.4 を適用するかどうかの判断
- 残余 baseline 順位の抽出
- Node 別評価状態
- 同一実 timestep 内の評価済み管理
- baseline driver 呼出管理
- 未確定 visit を実交通から収集するタイミング
- `uxsim.py` への接続
- `World.copy()` との統合
- 早期終了
- 経済評価
- 支払い・補償
- 意思決定窓外を含む取引候補の選定
- TVT 取引結果による最終確定 visit 列の作成
- 最終確定 visit 列を順位状態部品へ渡す上位制度処理

**§25.25.30 で実装可能な仕様の範囲：** 上記「今回含むもの」は、**順位状態部品**の実装前仕様として確定した。「今回含まないもの」は、順位状態部品の外に残る別設計・別実装である。TVT 候補 Vehicle の抽出や取引順位の計算を、本節の確定だけで実装可能になったと解釈しない。

**順位状態と評価状態を混同しない理由：** 順位状態は複数 timestep にわたって残る**順位帳簿**である。一度確定した順位は後から変更しない。一方、評価状態は「この timestep で処理済みか」などの**一時的な制御情報**である。両者を同一オブジェクトに混在させると、順位の不変性と評価の一時性が衝突し、二重確定や部分更新の事故を招く。本設計では順位帳簿だけを独立部品として切り出す。

##### 25.25.30.3 確定順位ブロックと未確定 visit

確定順位ブロックは、その Node について割当権利行使順位が確定した visit の、**1 位から始まる連続した順位列**である。

- 順位は **1 始まり**
- 空状態では確定順位なし（`k_confirmed() == 0`）
- 最初に確定する visit は **1 位**
- 確定順位は**連続**（欠番なし）
- **欠番を許さない**（同じ事故防止：順位の飛び番号）
- **順位重複を許さない**（同じ事故防止：2 台が同じ順位）
- **同じ visit の二重確定を許さない**（同じ事故防止：1 回決まった順位の上書き）
- **一度確定した順位は上書きしない**
- **確定済み visit を未確定へ戻さない**
- **確定済み visit と未確定 visit は排他的**（同じ visit が両方に同時所属しない）
- **Node ごとに独立した状態**を持つ

未確定 visit は、その Node で割当権利行使順位が**まだ確定していない** visit である。snapshot 固定集合、意思決定窓内 Vehicle、対象 inlink 上の全 Vehicle、到着済み Vehicle だけの集合とは**同一ではない**。**未確定 visit 集合は、意思決定窓内 visit だけの集合でもない。** 将来の TVT 制度処理によって候補となり得る**意思決定窓外**の visit も、外部から登録されれば未確定集合に含まれ得る。

- snapshot 固定集合と未確定 visit 集合は**同一ではない**
- TVT 候補集合と未確定 visit 集合も**同一ではない**
- TVT 候補集合は、未確定 visit 集合などから外部制度処理が条件に従って選ぶ**部分集合**になり得る
- 状態部品は TVT 候補集合を**作らない**
- **どの**意思決定窓外 visit を未確定集合へ登録するか、および実交通上の登録タイミングは、今回の状態部品の**外**に残る（登録範囲そのものは本節で新たに確定しない）

状態部品は、外部から登録された visit を未確定として保持するだけである。どの visit を登録するかは外部制度処理が決める。

##### 25.25.30.4 段階的な順位確定と K_confirmed

**K_confirmed** は、確定順位ブロックの**末尾順位**（確定済み visit 数）を表す。空状態では 0。

**K_confirmed_before まで（TVT 判断直前）：**

1. 意思決定窓の検知時点で、到着済みと判断された未確定 visit を外部制度処理が選ぶ
2. その有序 visit 列を状態部品へ渡して**先行確定**する
3. 意思決定窓内 baseline 順位の先頭に連続する非参加 visit を外部制度処理が選ぶ
4. その有序 visit 列を状態部品へ渡して**先行確定**する
5. すべての先行確定を反映した後、状態から現在の確定ブロック末尾を**再取得**する
6. この再取得値が、TVT 判断直前の **`K_confirmed_before`**
7. **意思決定窓内**の baseline 順位に残る未確定 visit のうち、最上位の**参加** visit を right_of_entry vehicle として外部制度処理が選ぶ（§4.5。参加・非参加を理由に同着順位の優劣を付けず、既存の baseline 順位を用いる）。意思決定窓**外**の未確定 visit から right_of_entry vehicle を選ばない
8. right_of_entry vehicle が存在しなければ TVT を形成しない
9. TVT 判断後に接続する新しい確定 visit 列がなければ、そのまま処理を終了する

**重要：** `K_confirmed_before` を、意思決定窓検知**前**から固定された値として扱ってはいけない。先行確定操作の古い戻り値（`ConfirmResult.k_confirmed_before` 等）を、後続の `K_confirmed_before` として固定利用してはいけない。TVT 判断直前に、必ず現在の状態から再取得する。これにより、先行確定の反映漏れや古い値参照による順位欠落を防ぐ。

**意思決定窓内がすべて非参加の場合（§4.5・§14.2）：** 全非参加専用の確定アルゴリズムは設けない。手順 3〜4 の**共通処理**（意思決定窓内 baseline 順位の先頭から連続する非参加 visit の先行確定）を適用した結果、**意思決定窓内の全** visit が先行確定される。手順 5〜6 で得た末尾が `K_confirmed_before` である。手順 7 の時点で**意思決定窓内に**未確定 visit が残らない（共通の先頭連続非参加 visit 確定処理の結果、意思決定窓内の全 visit が確定し、意思決定窓内には未確定 visit が残らない）ため、意思決定窓内に right_of_entry vehicle となる未確定参加 visit が存在せず、手順 8 により TVT を形成しない。手順 9 により追加の確定 visit 列（後続の最終確定列は**空**）を接続せず、制度処理上の `K_confirmed_after` も別途計算せずに処理を終了する。処理終了時の確定順位ブロック末尾は `K_confirmed_before` で表す。

**全非参加時に確定する「全 visit」の範囲：** 意思決定窓**内**の全 visit である。Node に関係する現在および将来の全 visit、snapshot 固定集合全体、後の timestep で意思決定窓へ入る visit を確定する意味ではない。**意思決定窓外**の未確定 visit は残り得る。

全非参加時に特別な K の計算方式は設けない。確定対象の visit 列が空の場合、`confirm_visits_in_order()` を呼ぶことは必須ではない。確定対象がなければ、確定 API を呼ばずに処理を終了してよい。`confirm_visits_in_order()` へ空の list または tuple を渡すこと自体は許可する。空列が渡された場合、状態を変更せず、`k_confirmed_before` と `k_confirmed_after` が等しく、`newly_confirmed_count` が 0 の結果を返す。

非技術的には、先頭から非参加 visit が連続していればその順番を確定する既存ルールを通常どおり最後まで適用する。意思決定窓内の全 Vehicle が非参加なら、その共通ルールだけで**意思決定窓内の**順番がすべて確定し、意思決定窓内に取引を始める未確定参加 visit も後から順番を決める未確定 visit も残らないため、そのまま処理が終了する。意思決定窓外には未確定 visit が残り得る。全非参加だけを別の特別な方法で処理するのではない。

**K_confirmed_after まで（最終確定後）：**

TVT 判断後に接続する最終確定 visit 列が存在する場合のみ、次を行う。

1. 外部制度処理が、今回さらに確定する全 visit の**最終的な順序列**を作る
2. 状態部品が、その列を確定ブロック末尾の次から接続する
3. 接続後の確定順位ブロック末尾が **`K_confirmed_after`**

更新式：

```text
K_confirmed_after
=
K_confirmed_before
+
今回新たに接続した visit 数
```

ただし、ここでいう `K_confirmed_before` は、**最終確定 visit 列を接続する直前**に状態から取得した値である。

TVT 判断後に接続する最終確定 visit 列が存在しない場合（全非参加など、共通の先行確定後に**意思決定窓内に**未確定 visit が残らない場合）は、上記手順 9 のとおり制度処理上の `K_confirmed_after` を別途計算しない。処理終了時の確定順位ブロック末尾は、先行確定後の `K_confirmed_before` で表す。残存する意思決定窓内の未確定 visit が 0 件なら、接続対象の列は空である。空列の確定 API 呼出しは必須ではない。確定 API を呼ばずに処理を終了してよい。空列を `confirm_visits_in_order()` へ渡した場合も no-op として正常に処理できる。

##### 25.25.30.5 状態部品へ渡す確定 visit 列

状態部品へ渡される列は、**未確定参加 Vehicle だけの列ではない**。外部制度処理が決めた有序 visit 列であり、制度ケースにより **先行確定列**（§25.25.30.4）として渡される場合と、TVT 判断後に **`K_confirmed_before` の次から接続する最終確定列**として渡される場合がある。後者は、

```text
今回新たに確定順位ブロックへ接続する全 visit の最終的な有序列
```

である。

次の visit が、TVT 判断後の**最終確定列**として外部制度処理から状態部品へ渡される（**先行確定後に意思決定窓内に未確定 visit が残らない場合**——全非参加を含む——は最終確定列は**空**であり、下記 §25.25.30.4 手順 9 のとおり接続しない）。

**TVT 取引不成立：** right_of_entry vehicle が存在し TVT を検討したが取引が不成立となった場合を含む。先行確定後に**意思決定窓内**に未確定 visit が **1 件以上**残っていれば、それらを baseline 順位で並べた最終確定列を `K_confirmed_before` の後へ接続し、順位を確定する。残存する意思決定窓内の未確定 visit が **0 件**なら、接続対象の列は空である。空列の確定 API 呼出しは必須ではない。確定 API を呼ばずに処理を終了してよい。空列を渡した場合も no-op として正常に処理できる。参加・非参加の両方を含み得る。

**TVT 形成に必要な情報を取得できない：** 部分的 TVT は行わない。§14.4 に従い、先行確定後に残る**意思決定窓内**の未確定 visit が **1 件以上**あれば、それらを baseline 順位で並べた最終確定列を接続し、順位を確定する。残存する意思決定窓内の未確定 visit が **0 件**なら、接続対象の列は空である。空列の確定 API 呼出しは必須ではない。確定 API を呼ばずに処理を終了してよい。空列を渡した場合も no-op として正常に処理できる。意思決定窓**外**の未確定 visit は、**情報未取得だけを理由に**列へ含めない。

**TVT 成立と情報未取得の区別（意思決定窓外 visit）：**

| 制度ケース | 意思決定窓外 visit の扱い |
|-----------|-------------------------|
| **TVT 取引成立** | TVT 候補集合と取引結果に基づき、意思決定窓外の候補 visit まで最終確定列へ含まれ、順位確定される**場合がある**（TVT 取引結果に基づく正式な順位確定） |
| **情報未取得（§14.4）** | 意思決定窓外の未確定 visit を、**情報を取得できなかったという理由だけでは確定しない** |

意思決定窓外 visit を**常に**確定するとも、**常に**確定しないとも記録しない。確定理由と制度ケースによって異なる。

**意思決定窓内がすべて非参加（§4.5・§14.2）：** 全非参加専用の先行確定列を別に作るのではない。手順 3〜4 の共通処理「意思決定窓内 baseline 順位の**先頭に連続する非参加 visit**の先行確定」を適用すると、この場合は「先頭に連続する非参加 visit」が結果として意思決定窓内の**全** visit となり、その列が通常どおり先行確定列として状態部品へ渡される（baseline 到着順位のまま）。すべての先行確定を反映した後の末尾が `K_confirmed_before` である。共通処理後に**意思決定窓内に**未確定 visit が残らないため、意思決定窓内に right_of_entry vehicle となる未確定参加 visit が存在せず、TVT を形成しない。`K_confirmed_before` の後へ新しい確定 visit 列を接続せず、制度処理上の `K_confirmed_after` も別途計算しない。意思決定窓外の未確定 visit は残り得る。

**全非参加と一般的な TVT 不成立の関係（専用アルゴリズムは設けない）：**

| | 全非参加 | 一般的な TVT 不成立 |
|---|---------|-------------------|
| 共通処理 | 先頭連続非参加 visit 先行確定により、**意思決定窓内の全** visit が先行確定 | 同左（該当する場合） |
| 手順 7 後 | 意思決定窓**内**に未確定参加 visit が残らない | 意思決定窓**内**に未確定 visit が残り得る |
| right_of_entry | 存在しない | 存在し TVT を検討したが不成立 |
| 後続最終確定列 | **空**（空列の確定 API 呼出しは必須ではない） | 残存 visit が 1 件以上なら baseline 順位で**確定** |

両者の違いは専用アルゴリズムの有無ではなく、共通処理後の**意思決定窓内**の状態と TVT 検討の有無である。

**TVT 取引成立：** TVT 取引結果による順位部分を含む。**TVT 取引順位部分**には、意思決定窓内の visit だけでなく、P-1 条件などによって TVT 候補となった**意思決定窓外**の visit も含まれ得る。意思決定窓外の候補 visit が実際に最終確定列へ含まれるかは、**外部の TVT 制度処理**が取引結果に従って決める。順位状態部品は、意思決定窓外であることを理由にその VisitKey を**拒否しない**。ただし、その VisitKey は未確定集合へ**事前登録済み**でなければならない。

取引当事者の最後尾順位が意思決定窓内の最後尾より前なら、その後ろに残る意思決定窓内の未確定 visit を baseline 順位で接続する。したがって、外部制度処理が完成させる最終確定列は、概念的に次の組合せになり得る（**固定的な列構造として状態部品へ要求しない**）。

```text
TVT 取引順位部分
  - 意思決定窓内の取引関係 visit
  - TVT 候補となった意思決定窓外の visit を含み得る
+
必要な場合の残余意思決定窓内 baseline 順位部分
```

状態部品が受け取るのは、外部制度処理が完成させた **1 本の有序 VisitKey 列**である。状態部品は、その列のどこまでが取引順位部分で、どこからが残余 baseline 部分かを**判定または保存しない**。

残余部分にも参加・非参加の両方が含まれ得る。最終確定列全体にも、意思決定窓内外・参加・非参加の visit が混在し得る。

状態部品は、各 visit が取引順位、baseline 順位、参加、非参加、意思決定窓内外のどれに由来するかを**判断しない**。渡された順序を保持して接続するだけである。参加 Vehicle だけを確定対象だと誤解しないよう、外部処理が渡す列をそのまま受け入れる設計とする。

##### 25.25.30.6 確定済み visit の保持方針

- 順位状態オブジェクトが存続する間、**確定済み visit を削除しない**
- Node 通過後も**確定履歴として保持**する
- 未確定 visit は、確定時に未確定集合から除外する
- 通過済みなのに未確定の visit を検出する責任は**上位制度処理**に置く
- 状態部品は Vehicle の交通状態を探索しない
- 確定済み順位は **1 位から連続**して保持する
- 現在の確定ブロック末尾は確定 visit 数と一致する
- **`K_confirmed` を別の mutable フィールドとして重複保存しない**

これは将来の作り直しを予定した設計ではない。**現在の正式な研究設計**として採用する。長期実験で記録数が増える可能性は、順位状態の**正しさ**とは分け、将来の**性能評価事項**として扱う。

##### 25.25.30.7 保存場所と状態の寿命

- **独立した Node 順位状態クラス**を作る
- 将来の上位 TVT 制御が **Node 名別 dict** で保持する
- 今回は **Node 属性へ追加しない**
- 今回は **World 属性へ追加しない**
- **`uxsim.py` を変更しない**
- 順位状態オブジェクトは **1 回の TVT 判断終了時に破棄しない**
- **複数の実 timestep** をまたいで維持する
- 上位 TVT 制御が対象 World の順位を管理する期間、状態を保持する
- `real_W` または `fork_W` 自体を状態オブジェクトへ保持しない
- Vehicle、Node、Link オブジェクトへの参照を保持しない
- **plain な Node 名と visit identity だけ**を保持する
- `World.copy()` との統合は今回対象外

概念：

```text
rank_states_by_node_name
  "junction_a" -> OrderControlTvtNodeRankState
  "junction_b" -> OrderControlTvtNodeRankState
```

「上位 TVT 制御」は、将来 TVT 処理を順番に呼ぶまとめ役を意味する。その関数名、クラス名、実装場所は今回確定しない。

非技術的には、各 Node の順位帳簿を Node 本体へ直接埋め込まず、将来の TVT 管理処理が Node 名別に保管する。これにより、シミュレーション本体（Node、World）と順位帳簿の責務を分離する。

##### 25.25.30.8 未確定 visit 登録 API と登録タイミングの境界

順位状態オブジェクトは、外部から明示的に渡された visit を未確定集合へ登録する API を持つ。

状態オブジェクト自身は次を**行わない**：

- Vehicle 一覧の探索
- Node の探索
- inlink の探索
- snapshot 固定集合からの抽出
- 意思決定窓の判定
- 到着済み判定
- 登録対象 visit の制度判断

登録 API を実交通上のどの時点で呼ぶかは、**今回の状態部品の外**に残す。次の 2 方式のどちらにも、今回の登録 API を利用できる。

- current visit 生成時に登録する方式
- TVT 評価開始時に上位制御が対象 visit を一括登録する方式

今回、どちらを採用するかは**決めない**。各方式に残る接続上の問題は、状態部品を実装するだけでは解決しない。

状態部品が保証するのは、渡された visit を**重複や部分更新なし**で登録することである。

**未確定 visit 集合と登録対象の範囲：**

- 未確定 visit 集合は、意思決定窓内 visit だけの集合ではない（§25.25.30.3 参照）
- 意思決定窓外の visit も、外部から明示的に渡されれば登録され得る
- snapshot 固定集合からの自動抽出、TVT 候補集合の自動形成、意思決定窓の判定は行わない
- どの意思決定窓外 visit をいつ登録するかは、今回の状態部品の外に残る

##### 25.25.30.9 VisitKey

公開型 alias として次を採用する。

```python
OrderControlTvtVisitKey = tuple[str, int]
```

意味：

```text
(vehicle_name, visit_id)
```

「公開型 alias」とは、`tuple[str, int]` という一般的な型に、TVT 用 visit 識別子であることが分かる名前を付け、他のモジュールからも使用可能にすることである。

**validation：**

- value は長さ 2 の tuple
- `vehicle_name` は非空 `str`
- `visit_id` は bool ではない Python `int`
- `visit_id` は **1 以上**
- 同一 Node 順位状態内で VisitKey は一意
- 同一 `vehicle_name` でも `visit_id` が異なれば別 visit
- 同一 VisitKey を確定済みと未確定の両方へ置かない
- Vehicle ID は VisitKey へ含めない
- Node 名は Node 別状態が保持するため VisitKey へ含めない

collector および snapshot と同じ `(vehicle_name, visit_id)` を使う理由：既存 order-control 基盤（collector、snapshot、fork probe）と visit identity を統一し、別の識別子体系を導入する混乱を防ぐためである。

##### 25.25.30.10 公開型と公開 API

**モジュール名：**

```text
uxsim/order_control_tvt_node_rank_state.py
```

**公開状態クラス名：**

```text
OrderControlTvtNodeRankState
```

**公開確定結果型：**

```text
OrderControlTvtConfirmResult
```

**公開型 alias：**

```text
OrderControlTvtVisitKey
```

**公開 API：**

```python
OrderControlTvtVisitKey = tuple[str, int]
```

```python
@dataclass(frozen=True)
class OrderControlTvtConfirmResult:
    k_confirmed_before: int
    k_confirmed_after: int
    newly_confirmed_count: int
```

`confirmed_visit_keys` は結果型へ**含めない**。理由：

- 確定対象の visit 列は呼出側がすでに保持している
- 結果型へ同じ列を複製する必須性がない
- 大きな確定列では余分な tuple 作成と参照保持が生じ得る
- コードと結果型を必要以上に複雑にしない
- 結果型は、更新前末尾、更新後末尾、更新件数だけで十分に意味が分かる
- 計算時間とメモリへの不要な負荷を避ける
- Python 初学者が理解しやすい単純な結果型を優先する

負荷が常に大きいと断定しない。現時点では明確な利点が小さいため、重複フィールドを採用しないという判断である。

`frozen=True` の意味：確定操作の結果を作成後に書き換えられないようにする設定である。状態本体は今後も更新されるため mutable だが、一回の確定操作の結果は後から変更する必要がないため、frozen とする。誤った再代入による `K_confirmed` 参照事故を防ぐ。

**状態クラスの正式なシグネチャ：**

```python
class OrderControlTvtNodeRankState:
    def __init__(self, node_name: str) -> None:
        ...
```

**公開読取・更新 API：**

```python
@property
def node_name(self) -> str:
    ...
```

```python
def k_confirmed(self) -> int:
    ...
```

```python
def register_undetermined_visit(
    self,
    visit_key: OrderControlTvtVisitKey,
) -> None:
    ...
```

```python
def register_undetermined_visits(
    self,
    visit_keys: list[OrderControlTvtVisitKey]
    | tuple[OrderControlTvtVisitKey, ...],
) -> None:
    ...
```

```python
def confirm_visits_in_order(
    self,
    visit_keys_in_order: list[OrderControlTvtVisitKey]
    | tuple[OrderControlTvtVisitKey, ...],
) -> OrderControlTvtConfirmResult:
    ...
```

```python
def confirmed_visit_keys_in_order(
    self,
) -> tuple[OrderControlTvtVisitKey, ...]:
    ...
```

```python
def undetermined_visit_keys(
    self,
) -> frozenset[OrderControlTvtVisitKey]:
    ...
```

```python
def is_confirmed(
    self,
    visit_key: OrderControlTvtVisitKey,
) -> bool:
    ...
```

```python
def is_undetermined(
    self,
    visit_key: OrderControlTvtVisitKey,
) -> bool:
    ...
```

```python
def assigned_rank(
    self,
    visit_key: OrderControlTvtVisitKey,
) -> int | None:
    ...
```

```python
def export_state(self) -> dict[str, object]:
    ...
```

実装時に既存 Python バージョンとの型注釈上の整合が必要な場合は、意味を変えない範囲で表記を調整できる。

##### 25.25.30.11 内部データ構造

状態本体は **mutable な通常クラス**とする。

**内部データ構造：**

- `_node_name: str`
- `_confirmed_visit_keys_in_order: list[OrderControlTvtVisitKey]`
- `_confirmed_rank_by_visit_key: dict[OrderControlTvtVisitKey, int]`
- `_undetermined_visit_keys: set[OrderControlTvtVisitKey]`

各構造の役割：

- **list** は確定順位順を保持する（1 位から末尾まで）
- **dict** は VisitKey から確定順位を O(1) で取得する
- **set** は未確定 visit の重複検出と所属確認に使う

未確定集合の登録順は保持しない。baseline 順位は外部制度処理が必要な時点で構築するため、未確定集合自体に順序は不要である。

`K_confirmed` は別フィールドとして保存しない。確定ブロックの長さから派生させる。これにより、ブロックと K の値が食い違う二重管理を防ぐ。

内部 list、dict、set を公開 API から**直接返さない**。基本的な Python の list、dict、set、tuple、str、int だけを保持し、Vehicle、Node、World への参照を持たせないため、**pickle 可能**な構造とする。

##### 25.25.30.12 未確定 visit の登録

単数登録と複数一括登録を提供する。

**単数登録（`register_undetermined_visit`）：**

渡された VisitKey を validation し、次を確認する。

- すでに未確定集合へ登録されていない
- すでに確定済みではない

問題がなければ未確定集合へ追加する。

**複数一括登録（`register_undetermined_visits`）：**

受け付ける容器型は **list または tuple**。set や generator などの一般 Iterable は受け付けず、既存 order-control API との一貫性を保つため list または tuple に限定する。

次の順序で処理する。

1. 容器型を確認する
2. tuple へ固定する
3. 全 VisitKey を validation する
4. 入力列内重複を確認する
5. 既存未確定集合との重複を確認する
6. 確定済み visit の混入を確認する
7. 全件に問題がなければ一括追加する（§25.25.30.17 のローカル更新候補方式に従う）

空の list または tuple は **no-op** とする。一件でも不正なら、**どの visit も登録しない**（部分登録を防ぐ）。

##### 25.25.30.13 visit 列の一括確定

`confirm_visits_in_order()` は、外部制度処理が決めた有序 VisitKey 列を受け取る。

受け付ける容器型は **list または tuple** とする。

次の順序で処理する。

1. 容器型が list または tuple であることを確認する
2. 入力を tuple へ固定する
3. 全 VisitKey の型と内容を validation する
4. 入力列内の VisitKey 重複を確認する
5. 各 VisitKey が**すでに確定済みでない**ことを確認する
6. 確定済みでない各 VisitKey が**未確定集合に登録済み**であることを確認する
7. 全件の入力・操作要求 validation に成功した後、現在の `k_confirmed_before` を取得する
8. 更新後に使用する確定 list、順位 dict、未確定 set の**ローカル更新候補**を作成する（§25.25.30.17 参照）
9. 渡された順序のまま、`k_confirmed_before + 1` から連番で更新候補へ接続する
10. 対象 VisitKey を更新候補の未確定 set から除外する
11. 更新候補から `k_confirmed_after` を計算する
12. 更新候補について必要最小限の内部整合を確認する（§25.25.30.17・§25.25.30.18 参照）
13. 整合確認に成功した場合だけ、更新候補を正式な内部状態へ一括反映する
14. `OrderControlTvtConfirmResult` を返す

**検査順序の理由：** 確定済み visit は未確定集合から除外されるため、未確定集合の有無を先に確認すると、再確定要求と未登録要求を区別できない。確定済みかどうかを**先に**確認し、確定済みでなければ未確定登録済みかを確認する。

**例外の区別（いずれも `ValueError`、メッセージは別）：**

**確定済み visit の再確定：** すでに `_confirmed_rank_by_visit_key` に存在する VisitKey が入力された場合。メッセージには少なくとも次を含める。

- 対象 VisitKey
- すでに確定済みであること
- 現在の確定順位

**未登録 visit の確定要求：** 確定済みではなく、未確定集合にも存在しない VisitKey が入力された場合。メッセージには少なくとも次を含める。

- 対象 VisitKey
- 未確定 visit として事前登録されていないこと

再確定と未登録を同じ一般的なエラーメッセージへまとめない。

空の list または tuple は **no-op** である。空の場合も結果を返す。

```text
k_confirmed_before == k_confirmed_after
newly_confirmed_count == 0
```

状態は変化しない。

**制度処理との関係（空列）：** 確定対象の visit 列が空の場合、`confirm_visits_in_order()` を呼ぶことは必須ではない。確定対象がなければ、確定 API を呼ばずに処理を終了してよい。`confirm_visits_in_order()` へ空の list または tuple を渡すこと自体は許可する。

状態部品は、渡された列の制度的な並びが正しいかを**再判定しない**。外部制度処理が決めた順序をそのまま接続する。

**`confirm_visits_in_order()` が確認する項目：**

- 入力容器型
- VisitKey の型と内容
- 入力列内重複
- 確定済みか
- 未確定集合へ登録済みか

**`confirm_visits_in_order()` が確認しない項目：**

- 意思決定窓内か外か
- TVT 参加 Vehicle か非参加 Vehicle か
- TVT 候補集合に含まれるか
- P-1 条件を満たすか
- 取引順位部分か残余 baseline 部分か
- TVT 成立、不成立、情報未取得のどのケースか

これらを確認しない理由：確定列の制度的な正しさは**外部制度処理**が保証し、順位状態部品はそれを**安全に保存する**責任だけを持つためである。

##### 25.25.30.14 ConfirmResult

次の 3 フィールドで確定する。

```python
@dataclass(frozen=True)
class OrderControlTvtConfirmResult:
    k_confirmed_before: int
    k_confirmed_after: int
    newly_confirmed_count: int
```

各フィールドの意味：

- **`k_confirmed_before`** — その一括確定操作の直前の確定ブロック末尾
- **`k_confirmed_after`** — その一括確定操作の直後の確定ブロック末尾
- **`newly_confirmed_count`** — その操作で新たに確定した visit 数

整合条件：

```text
newly_confirmed_count
==
k_confirmed_after - k_confirmed_before
```

`confirmed_visit_keys` を含めない理由：入力列は呼出側がすでに保持しており、結果へ同じ情報を重複して持たせる明確な必要性がない。大きな確定列では余分な tuple 作成と参照保持が生じ得る。結果型は更新前末尾・更新後末尾・更新件数だけで十分に意味が分かり、Python 初学者にも理解しやすい。

`frozen=True` は、一回の確定操作の記録を後から誤って書き換えないためである。

##### 25.25.30.15 K_confirmed の取得と整合条件

`k_confirmed()` は現在の確定順位ブロック末尾を返す。空状態では **0**。

確定済み visit を削除せず、順位を 1 位から連続して保持するため、次が成立する。

```text
k_confirmed()
==
len(_confirmed_visit_keys_in_order)
==
len(_confirmed_rank_by_visit_key)
```

別の mutable フィールドへ `K_confirmed` を保存しない。これにより、ブロックと K の値が食い違う可能性を減らす。

先行確定操作の後に、TVT 判断用の `K_confirmed_before` を必要とする場合は、必ず次のように**現在値を再取得**する。

```python
k_confirmed_before = rank_state.k_confirmed()
```

先行確定操作の古い `ConfirmResult.k_confirmed_before` を使用してはいけない。

##### 25.25.30.16 読取 API と export

**確定 visit 列：** `confirmed_visit_keys_in_order()` は、1 位から順位順に並んだ VisitKey の **tuple** を返す。内部 list を直接返さない。

**未確定 visit 集合：** `undetermined_visit_keys()` は **frozenset** を返す。内部 set を直接返さない。未確定 visit には制度上の順序を持たせない。

**所属確認と確定順位（`is_confirmed()`、`is_undetermined()`、`assigned_rank()`）：**

これら 3 API は、受け取った VisitKey について**型と内容の validation を行う**。不正な VisitKey を渡した場合は **`ValueError`** とする。

正しい形式だが状態へ未登録の VisitKey の場合は次とする。

```text
is_confirmed() == False
is_undetermined() == False
assigned_rank() is None
```

確定済み VisitKey では `is_confirmed() == True`、`assigned_rank()` は 1 以上。未確定 VisitKey では `is_undetermined() == True`、`assigned_rank()` は `None`。未確定と未登録を区別する場合は `is_undetermined()` を併用する。

**読取時の再検査方針：** 「登録・更新時に保証済みの不変条件を読取時に全面再検査しない」とは、内部 list、dict、set **全体**を毎回再検査しないという意味である。読取 API へ新たに渡された VisitKey 自体の validation を省略する意味ではない。

**export：** `export_state()` の公開シグネチャは次で確定する。

```python
def export_state(self) -> dict[str, object]:
    ...
```

既存 Python バージョンとの整合で必要な場合だけ、意味を変えない範囲で型注釈表記を調整できる。

返却形式を次で確定する。

```python
{
    "node_name": str,
    "k_confirmed": int,
    "confirmed_visits": [
        {
            "vehicle_name": str,
            "visit_id": int,
            "assigned_rank": int,
        },
        ...
    ],
    "undetermined_visits": [
        {
            "vehicle_name": str,
            "visit_id": int,
        },
        ...
    ],
}
```

**`node_name`：** 状態オブジェクトの Node 名。

**`k_confirmed`：** 現在の確定順位ブロック末尾。空状態では 0。

**`confirmed_visits`：** 確定順位の昇順、すなわち 1 位から順に並べる。各要素は新しく作成した dict とし、次を含める。

- `vehicle_name`
- `visit_id`
- `assigned_rank`（1 以上の連続順位）

**`undetermined_visits`：** 制度上の順位は持たない。診断・テスト出力を安定させるため、次の順で固定 sort する。

1. `vehicle_name`
2. `visit_id`

各要素は新しく作成した dict とし、次を含める。

- `vehicle_name`
- `visit_id`

**可変状態の非漏洩：** export 結果の次を呼出側が変更しても、内部状態へ影響してはいけない。

- 最上位 dict
- `confirmed_visits` の list
- `confirmed_visits` 内の各 dict
- `undetermined_visits` の list
- `undetermined_visits` 内の各 dict

Vehicle、Node、Link、World オブジェクトを含めない。

VisitKey の tuple をそのまま含める形式ではなく、キー名の分かる plain dict へ分解する。非技術的には、診断出力を見た人が tuple の 1 番目と 2 番目の意味を覚えていなくても、Vehicle 名、visit ID、順位を理解できるようにするためである。

##### 25.25.30.17 更新の原子性

未確定 visit の複数登録と visit 列の一括確定は、次の方針で確定する。

- 入力全体を先に tuple へ固定する
- 全件を先に validation する
- 入力内重複を検査する
- 現在状態との矛盾を確認する
- 全件に問題がない場合だけ状態を更新する
- 一件でも問題があれば**正式な内部状態を変更しない**
- rollback を必要とする途中更新を作らない

非技術的には、5 件を確定する依頼の 4 件目に問題があった場合、最初の 3 件だけを確定済みにして状態を残さないための設計である。validation 途中で一部だけ状態が更新される事故を防ぐ。

**ローカル更新候補方式（一括更新の正式方式）：**

更新前の内部状態から、更新に必要なローカル候補を作る。概念名は次のとおり（正式な属性名ではなく、処理を説明する概念名。実装時には意味の分かるローカル変数名を使用する）。

```python
candidate_confirmed_visit_keys_in_order
candidate_confirmed_rank_by_visit_key
candidate_undetermined_visit_keys
```

処理順序：

1. 呼出入力と操作要求を全件 validation する
2. 現在状態を基にローカル更新候補を作る
3. ローカル更新候補だけを変更する
4. ローカル更新候補の必要最小限の内部整合を確認する（§25.25.30.18）
5. すべて成功した場合だけ、内部 list、dict、set を更新候補へ一括で置き換える
6. 結果を返す

これにより、入力不正だけでなく、更新候補の内部整合確認で `RuntimeError` となった場合も、**正式な内部状態を更新前のまま維持**する。非技術的には、5 件を確定する処理の途中や、更新候補の検査中に問題が見つかっても、最初の数件だけが確定済みとして残る事故を防ぐ方式である。

**単数登録（`register_undetermined_visit`）：** 1 件だけの単純更新。VisitKey validation、既存未確定との重複、確定済みとの重複をすべて確認した後にだけ set へ追加する。

**複数登録（`register_undetermined_visits`）：** 入力全体を tuple へ固定し、全件 validation と重複確認に成功した後でのみ一括追加する。既存 set を直接変更しながら validation しない。必要ならローカル更新候補 set を作り、その候補の確認後に正式 set へ反映する。

**確定操作（`confirm_visits_in_order`）：** 正式な内部 list、dict、set を**直接変更しながら**更新後検査を行わない。更新候補の検査成功後に、正式な内部状態へ一括反映する。

**性能と可読性：** この方式は更新時に list、dict、set のコピーを作る可能性がある。ただし、今回の順位状態では次を優先する。

- 研究結果の正確性
- 部分更新を残さないこと
- 実装者が処理順を追いやすいこと
- rollback 処理を追加しないこと

高度な差分更新や複雑な rollback より、明示的なローカル候補を作る方式を採用する。長期・大規模実験で更新候補生成の負荷が問題になるかは、実測に基づく性能評価事項として分けて扱う。

**更新候補に対して確認する必要最小限の内部整合（登録・確定の更新候補反映前）：**

```text
len(candidate_confirmed_visit_keys_in_order)
==
len(candidate_confirmed_rank_by_visit_key)
```

```text
candidate_k_confirmed_after
==
len(candidate_confirmed_visit_keys_in_order)
```

順位順 list の各 VisitKey について、1 始まりの位置と rank dict の順位が一致すること：

```text
candidate_confirmed_rank_by_visit_key[visit_key]
==
position
```

（`position` は 1 から始まる順位）

- 確定 list 内の VisitKey に重複がないこと
- 確定 list 内の VisitKey が未確定候補 set に存在しないこと
- 今回確定したすべての VisitKey が未確定候補 set から除外されていること

`OrderControlTvtConfirmResult` について次が成立すること：

```text
newly_confirmed_count
==
k_confirmed_after - k_confirmed_before
```

更新候補のこれらの不整合は **`RuntimeError`** とする。

すべての読取操作で全状態を全面再検査しない。内部整合確認は、状態を変更する登録・確定処理の適切な節目で行う。

##### 25.25.30.18 不変条件

- Node 名は非空 `str`
- VisitKey は長さ 2 の tuple
- `vehicle_name` は非空 `str`
- `visit_id` は bool ではない Python `int` で 1 以上
- 確定順位は **1 から連続**
- 確定順位に**欠番がない**
- 確定順位に**重複がない**
- 確定 VisitKey に**重複がない**
- 未確定 VisitKey に**重複がない**
- 同じ VisitKey が確定済みと未確定の**両方に存在しない**
- 確定ブロック末尾と確定件数が**一致**
- 一度確定した順位は**上書きしない**
- 確定操作は**未確定登録済み VisitKey だけ**を対象にする
- 空確定操作は状態を変えない
- validation 失敗時は状態を**部分変更しない**

**検査の責任分担：**

| タイミング | 検査内容 |
|-----------|---------|
| 生成時 | Node 名 |
| VisitKey 受付時 | VisitKey の型と内容 |
| 登録時 | 重複、確定済みとの排他 |
| 確定時 | 入力列内重複、**確定済みでないこと（先）**、**未確定登録済みであること（後）**、一括更新 |
| 更新候補反映前 | §25.25.30.17 の必要最小限の内部整合 |
| 読取時（`is_confirmed` / `is_undetermined` / `assigned_rank`） | 渡された VisitKey の型と内容。内部 list、dict、set 全体の全面再検査はしない |
| 読取時（その他） | 登録・更新時に保証済みの不変条件を**全面再検査しない** |

##### 25.25.30.19 ValueError と RuntimeError

**ValueError** — 呼出側が渡した入力または操作要求が契約に合わない場合。

少なくとも次を `ValueError` とする：

- Node 名が不正
- VisitKey の型または内容が不正
- 複数登録 API の容器型が不正
- 確定 API の容器型が不正
- 未確定 VisitKey の重複登録
- 確定済み VisitKey の未確定再登録
- 確定済み VisitKey の再確定（対象 VisitKey、確定済みであること、現在の確定順位をメッセージに含める）
- 未登録 VisitKey の確定要求（対象 VisitKey、未確定として事前登録されていないことをメッセージに含める。再確定と同じ一般的メッセージにまとめない）
- 同じ登録要求内の VisitKey 重複
- 同じ確定要求内の VisitKey 重複

- 読取 API（`is_confirmed`、`is_undetermined`、`assigned_rank`）への不正 VisitKey

**RuntimeError** — 状態部品内部で、本来発生しない不整合を検出した場合。

少なくとも次を **`RuntimeError`** とする：

- confirmed list と rank dict の件数不一致
- confirmed list と rank dict の VisitKey 不一致（順位対応不一致を含む）
- 確定順位の欠番
- 確定順位の重複
- 確定 VisitKey が未確定集合にも残る
- 更新後の末尾順位と確定件数が一致しない
- `ConfirmResult` の件数差分が一致しない（`newly_confirmed_count != k_confirmed_after - k_confirmed_before`）

`RuntimeError` は、呼出側が入力を直せば解決する通常の契約違反ではなく、順位状態の**内部破壊**を示す重大な異常である。

通過済みなのに未確定の visit を検出する責任は、交通状態を知る**上位制度処理**へ置く。状態部品自身は Vehicle の通過状態を探索しない。

##### 25.25.30.20 K_confirmed の具体例

**例 1：先行確定後に TVT 判断用 K_confirmed_before を再取得**

開始時：

```text
1位 A
2位 B
```

現在の末尾：

```text
k_confirmed = 2
```

到着済み visit として C、D を先行確定：

```text
3位 C
4位 D
```

次に、先頭連続非参加 visit として E を先行確定：

```text
5位 E
```

TVT 判断直前に状態から再取得：

```text
K_confirmed_before = 5
```

その後、外部制度処理が最終確定列を作る：

```text
G
F
H
```

この列には TVT 取引順位と残余 baseline 順位が含まれ得る。

状態部品が接続：

```text
6位 G
7位 F
8位 H
```

結果：

```text
K_confirmed_after = 8
newly_confirmed_count = 3
```

状態部品は、G、F、H がどの制度的理由でこの順序になったかを判断しない。

**例 2：TVT 不成立または情報未取得**

先行確定後：

```text
K_confirmed_before = 4
```

外部処理が意思決定窓内の残る未確定 visit を baseline 順で作る：

```text
J
K
L
```

状態部品が接続：

```text
5位 J
6位 K
7位 L
```

結果：

```text
K_confirmed_after = 7
newly_confirmed_count = 3
```

**例 3：TVT 成立後の残余 baseline 順位**

先行確定後：

```text
K_confirmed_before = 3
```

外部処理が作る最終確定列：

```text
TVT 取引順位部分：N、M
残余 baseline 部分：O、P
```

状態部品へ渡す一つの有序列：

```text
N
M
O
P
```

状態部品が接続：

```text
4位 N
5位 M
6位 O
7位 P
```

結果：

```text
K_confirmed_after = 7
newly_confirmed_count = 4
```

**例 4：空の確定要求**

開始時：

```text
k_confirmed = 5
```

空列を確定：

```text
[]
```

結果：

```text
k_confirmed_before = 5
k_confirmed_after = 5
newly_confirmed_count = 0
```

状態は変化しない。

`confirm_visits_in_order()` へ空の list または tuple を渡すことは許可される。空列の確定 API 呼出しは必須ではない。

**例 5：意思決定窓内がすべて非参加（共通処理の自然な終了）**

意思決定窓内 baseline 順位が次のとおりで、すべて非参加 visit であるとする。

```text
A（非参加）
B（非参加）
C（非参加）
```

先行確定開始時：

```text
k_confirmed = 2
```

共通処理（先頭から連続する非参加 visit の先行確定）により、A、B、C を先行確定列として接続：

```text
3位 A
4位 B
5位 C
```

TVT 判断直前に状態から再取得：

```text
K_confirmed_before = 5
```

未確定 visit は**意思決定窓内に**残らないため right_of_entry vehicle は存在せず、TVT を形成しない。接続する最終確定 visit 列はないため、制度処理上の `K_confirmed_after` を別途計算せず、確定 API を呼ばずに処理を終了する。確定対象がないため呼出しは必須ではないが、`confirm_visits_in_order([])` を呼んだ場合も no-op として正常に処理できる。処理終了時の末尾は `K_confirmed_before = 5` である（意思決定窓外の未確定 visit は残り得る）。

**例 6：TVT 成立時に意思決定窓外候補 visit を含む最終確定列**

本例は、TVT 候補の選定規則や取引順位計算を状態部品が行うという意味ではない。外部制度処理が完成させた列を、状態部品が保存できることを示す。

先行確定後：

```text
K_confirmed_before = 3
```

外部制度処理が作った最終確定列（すべて未確定集合へ事前登録済み）：

```text
Q  意思決定窓内の取引関係 visit
R  意思決定窓外の TVT 候補 visit（外部制度処理上、窓外候補を表す VisitKey）
S  意思決定窓内の取引関係 visit
T  残余の意思決定窓内 baseline 順位 visit
```

状態部品は窓内外や順位の由来を判断せず、1 本の有序列として接続：

```text
4位 Q
5位 R
6位 S
7位 T
```

結果：

```text
K_confirmed_after = 7
newly_confirmed_count = 4
```

##### 25.25.30.21 専用テスト契約

新規テストファイル：

```text
tests_order_control_tvt_node_rank_state.py
```

既存 order-control テストと同じ直接実行形式を使用する。

- `test_*` 関数
- `TESTS` 一覧
- `if __name__ == "__main__":`
- リポジトリルートから直接実行可能
- `TESTS` 一覧と `test_*` 定義数を照合
- 重複テスト名を拒否

**少なくとも次をテストする：**

**初期化：** 正常な Node 名、空 Node 名拒否、非文字列 Node 名拒否、空確定ブロック、空未確定集合、`k_confirmed() == 0`

**VisitKey：** 正常な vehicle_name と visit_id、空 vehicle_name 拒否、非文字列 vehicle_name 拒否、bool の visit_id 拒否、非 int visit_id 拒否、0 以下の visit_id 拒否、tuple 以外拒否、長さ 2 以外の tuple 拒否、同じ vehicle_name で異なる visit_id を別 visit として扱う

**未確定 visit 登録：** 単数登録、複数一括登録、空列 no-op、入力列内重複拒否、既存未確定 VisitKey の再登録拒否、確定済み VisitKey の再登録拒否、validation 失敗時に部分登録しない、Node 間状態の独立

**一括確定：** 空列 no-op、1 件確定、複数 visit 確定、入力順を保持、最初の順位が 1、既存末尾の次から連番、`k_confirmed_before`、`k_confirmed_after`、`newly_confirmed_count`、`newly_confirmed_count == after - before`、確定後に未確定集合から除外、未登録 VisitKey の確定拒否、確定済み VisitKey の再確定拒否、入力列内重複拒否、validation 失敗時に状態不変、複数回の確定操作で連番維持、先行確定後に `k_confirmed()` を再取得できる、TVT 判断後の最終確定列を同じ API で接続できる、参加・非参加や制度理由を状態部品が要求しない

**再確定と未登録の区別：**

- 確定済み VisitKey の再確定は、確定済みであることと現在順位が分かる `ValueError`
- 一度も未確定登録されていない VisitKey の確定要求は、未登録であることが分かる `ValueError`
- 両者のメッセージを区別する

**意思決定窓外 visit を含む確定列：**

- 意思決定窓内 visit と意思決定窓外 visit を表す VisitKey を未確定集合へ事前登録する（VisitKey 自体は窓内外情報を持たない。テスト名・コメントで「外部制度処理上、窓外候補を表す VisitKey」と位置づける）
- 状態部品自体には意思決定窓情報を渡さない
- 外部で完成済みと仮定した有序 VisitKey 列を `confirm_visits_in_order()` へ渡す
- 入力順のまま連続順位が付く
- 意思決定窓外の visit も、窓外であることを理由に拒否されない
- `k_confirmed_before`、`k_confirmed_after`、`newly_confirmed_count`
- 確定後に対象 visit が未確定集合から除外される
- テスト内で意思決定窓の判定、P-1 候補抽出、TVT 取引順位計算、§14.4 判断を実装しない

非技術的には、順位帳簿が窓内外を判断せず、外部で決まった順番をそのまま安全に保存できることを確認するテストである。

**ローカル更新候補と原子性：**

- 複数登録の入力不正時に正式状態が完全に不変
- 複数登録の重複時に正式状態が完全に不変
- 一括確定の途中要素が未登録でも正式状態が完全に不変
- 一括確定入力に確定済み VisitKey が混入しても正式状態が完全に不変
- 更新候補の内部整合検査で `RuntimeError` となる人工条件を作れる場合、正式状態が更新前のまま
- rollback 処理に依存していないこと

**ConfirmResult：** frozen である、3 フィールドだけを持つ、`confirmed_visit_keys` を持たない、空操作の値、通常操作の値

**読取 API：** 確定 VisitKey を順位順で返す、内部 list を漏らさない、未確定 VisitKey を frozenset で返す、内部 set を漏らさない、`is_confirmed()`、`is_undetermined()`、`assigned_rank()`、未確定の assigned_rank は None、未登録の assigned_rank は None、不正 VisitKey を `is_confirmed()` へ渡すと `ValueError`、不正 VisitKey を `is_undetermined()` へ渡すと `ValueError`、不正 VisitKey を `assigned_rank()` へ渡すと `ValueError`、正しい形式の未登録 VisitKey では False、False、None

**export の正確な構造：**

- top-level キーが次の 4 つである：`node_name`、`k_confirmed`、`confirmed_visits`、`undetermined_visits`
- `confirmed_visits` の各 dict が次の 3 キーを持つ：`vehicle_name`、`visit_id`、`assigned_rank`
- `undetermined_visits` の各 dict が次の 2 キーを持つ：`vehicle_name`、`visit_id`
- `confirmed_visits` が `assigned_rank` 昇順
- `undetermined_visits` が `vehicle_name`、`visit_id` の固定順
- 入れ子の list や dict を変更しても内部状態に影響しない
- Vehicle、Node、Link、World 参照を含まない

**内部不整合（`RuntimeError`、必要最小限）：** private 状態を人工的に壊すテストは代表例だけに限定する。少なくとも次を記録する。

- confirmed list と rank dict の件数不一致
- confirmed list と rank dict の順位対応不一致
- 確定 VisitKey が未確定集合にも存在
- 更新後の `ConfirmResult` 差分不一致を検出する責任

本番 API から作れない内部不整合を過度に細分化しない。

**制度処理との境界（状態部品のテストへ含めない）：** 到着済み Vehicle の選定、非参加 Vehicle の抽出、baseline 順位 sort、right_of_entry 選定、TVT 成立判断、P-1 候補集合、§14.4 判断、取引順位の算出。状態部品のテストでは、外部制度処理が作った有序 VisitKey 列を安全に保存できることだけを確認する。

##### 25.25.30.22 実装ファイルと変更範囲

**新規作成：**

- `uxsim/order_control_tvt_node_rank_state.py`
- `tests_order_control_tvt_node_rank_state.py`

**実装時に変更しない：**

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_driver.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/order_control_baseline_snapshot.py`
- `uxsim/__init__.py`
- 既存テスト
- 既存診断

状態部品は専用モジュールから直接 import する。

実装中に既存ファイルの動作変更が必要と判明した場合は、勝手に変更範囲を広げず、作業を停止して理由を報告する方針とする。

##### 25.25.30.23 今回の状態部品が判断しない事項

- 到着済み visit を誰とするか
- 先頭連続非参加 visit を誰とするか
- 意思決定窓内 baseline 順位
- 意思決定窓内外の判定
- 意思決定窓外の TVT 候補 visit の抽出
- P-1 条件の判定
- TVT 候補集合の形成
- 意思決定窓外候補を最終確定列へ含めるかどうか
- TVT 取引結果による順位計算
- right_of_entry vehicle
- TVT を形成するか
- TVT が成立したか
- どの Vehicle が取引当事者か
- P
- P-1 候補集合
- 情報充足
- §14.4 を使うか
- 残余 baseline 順位
- 参加・非参加状態
- 意思決定窓内がすべて非参加かどうかの判定（上位制度処理が共通の先頭連続非参加処理を適用し、残存未確定 visit の有無で自然に終了する）
- 通過済み未確定の検出
- 実交通上の未確定 visit 登録タイミング
- Node 別評価状態
- baseline driver 呼出
- 早期終了

状態部品へ渡される確定列は、外部制度処理が**最終決定したもの**として扱う。

##### 25.25.30.24 実装再開情報

- **§25.25.30 で実装可能な仕様として確定したのは、Node 別 TVT 順位状態部品である**
- TVT 候補 visit の抽出、P-1 条件、意思決定窓外候補を含む取引順位の計算、最終確定 visit 列の作成、状態部品への接続処理は、**今回の実装範囲外**であり、**別途設計・実装が必要**である
- 順位状態部品自体は、未確定集合へ事前登録済みであれば、**意思決定窓内外を区別せず**、外部から渡された有序 VisitKey 列を確定できる
- **次の直接作業：** 順位状態本体と専用テストの実装
- **次の実装によって TVT 候補順位計算まで完成するわけではない**
- 状態部品実装後、候補選定や制度処理の次段階を改めて設計する
- Node 別 TVT 順位状態の実装前仕様は **§25.25.30** で確定した
- 新規モジュールは `uxsim/order_control_tvt_node_rank_state.py`
- 新規テストは `tests_order_control_tvt_node_rank_state.py`
- `uxsim.py`、baseline driver、collector、snapshot、`uxsim/__init__.py` は変更しない
- 実装中に制度判断を状態部品へ追加しない
- 状態部品は外部が決定した有序 VisitKey 列の保存だけを担当する
- `K_confirmed_before` は先行確定後に状態から再取得する
- 最終確定列を参加 Vehicle だけに限定しない
- `OrderControlTvtConfirmResult` は **3 フィールド**
- `confirmed_visit_keys` は採用しない
- 最新保存済みコミットは **`bd24ad1`**
- `bd24ad1` は `origin/feature/intersection-order-control` へ push 済み
- 今回のメモ更新は**未コミット、未 push**
- `diagnostics/order_control.zip` は未接触、コミット対象外

実装完了後に、設計メモと進捗メモへ実装・テスト・レビュー結果を記録する方針とする。
