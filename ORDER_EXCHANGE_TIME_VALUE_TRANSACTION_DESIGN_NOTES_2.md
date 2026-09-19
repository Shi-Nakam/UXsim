# ORDER EXCHANGE TIME-VALUE TRANSACTION DESIGN NOTES 2

**作成日：2026-09-14**

## 本メモの位置づけ

- 本ファイルは、`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`の継続版である。
- 本ファイルはTVT-MPだけの専用メモではない。
- 既存メモは、歴史的記録および実装済み事実の記録として削除せず維持する。
- 今後のTVT設計・実装記録の主要な追加先は、本ファイルとする。
- TVT-MP一般形アルゴリズムについては、本ファイルに収録した「非参加Visitの有無を統一して扱うTVT-MP一般形アルゴリズム」を最新正本とする。
- 旧メモの§25.25.34.51までに記録された実装済み事実は、引き続き有効である。
- 実装済み事実について新旧メモに齟齬がある場合は、実コードおよび旧メモの最新実装完了記録を優先する。
- 未実装の制度設計について新旧メモに齟齬がある場合は、本ファイルで最新正本と明記した節を優先する。
- チャットまたはCursorの報告だけで、設計や実装の完了を確定しない。必要な実コード、差分、テスト結果をTerminalで確認する。
- Git操作は利用者がTerminalで実行する。
- コミットまでの操作と`git push`は分ける。
- メモを含むコミット名には`document`を含める。
- 設計・実装の節目ごとに、本ファイルの主要本文と`ORDER_EXCHANGE_PROGRESS.md`の双方への反映要否を確認する。
- 既存の歴史的記述を、最新状態と異なるという理由だけで削除または無注記で書き換えない。
- 新しいチャットでは、原則として本ファイルを先に読み、必要な過去経緯だけ旧メモの指定節を参照する。

## 文書保守方針

本ファイルでは、旧メモで採用済みの文書保守方針を引き継ぐ。

- 過去の設計方針、実装状態、診断結果、未解決事項、当時の再開地点は、歴史的記録として原則保存する。
- 古い記述と最新状態が異なる場合は、古い記述を削除せず、更新日、現在状態、最新参照先を追記する。
- 残すべきか判断できない記述は、保守的に残す。
- 誤字脱字、Markdown崩れ、明白な転記ミスは、意味を変えない範囲で修正できる。
- 最新正本となる節には、日付、適用範囲、旧記述との関係を明示する。
- 実装前設計と実装完了記録を区別する。
- Cursor報告だけを根拠として、未確認の処理を実装済みと記録しない。
- 各節目で、現在地、実装済み範囲、未実装境界、次の作業開始点、新しいチャットでの再開情報を残す。

## 作成前のGit状態

- ブランチ：`feature/intersection-order-control`
- 作成前の最新保存済み・push済みコミット：`b5af3da`
- コミット名：`Implement, test and document TVT candidate Visit organization by inlink snapshot physical order`
- `HEAD`と`origin/feature/intersection-order-control`の差：`0 / 0`
- Markdown、Python、テストの未コミット変更：なし
- 既存未追跡ファイル：`diagnostics/order_control.zip`
- `diagnostics/order_control.zip`は今回の対象外、未接触、コミット対象外である。
- 本ファイルの作成時点では、`git add`、`git commit`、`git push`は未実行である。
- 本ファイルを作成するコミットのhashは、作成時点では存在しないため記載しない。

## 旧メモの主要参照先

- timestep T到着Visit：旧メモ§5、§25.25.34.38、§25.25.34.39
- 既到着Visit先行確定：旧メモ§5、§25.25.34.38、§25.25.34.39
- 先頭連続非参加Visit先行確定：旧メモ§4.5、§25.25.34.40、§25.25.34.41
- 権利保有Visit選定：旧メモ§8、§25.25.34.42、§25.25.34.43
- P取得とP−1条件：旧メモ§7.2、§8.3、§25.25.34.44、§25.25.34.45
- TVT固有可変上限N：旧メモ§25.25.34.46、§25.25.34.47
- snapshot inlink物理順：旧メモ§25.25.34.48、§25.25.34.49
- candidate Visitのinlink別snapshot物理順：旧メモ§25.25.34.50、§25.25.34.51
- 非参加Visitなし順位計算：旧メモ§11、§25.25.32、§25.25.33
- FIFO：旧メモ§13、§25.25.32、§25.25.33
- 局所仮想計算未解決：旧メモ§14.4、§16、§25.25.34
- 経済性評価：旧メモ§15
- 成立、不成立、情報未解決時の順位確定：旧メモ§14.3、§14.4、§25.25.30
- 確定順位ブロック：旧メモ§14、§25.25.31
- 作成前の最新実装完了記録：旧メモ§25.25.34.51

---

# 非参加Visitの有無を統一して扱うTVT-MP一般形アルゴリズム

## 1. 本説明の位置づけ

本説明は、TVT-MPについて、非参加Visitが存在する場合と存在しない場合の双方を、同じ候補生成規則と順位再構成規則によって扱う一般形アルゴリズムの最新設計を整理したものである。

現在までに、次の上流処理は実装済みである。

- snapshot固定Visitの登録
- 全World baseline仮想計算
- 既到着Visitの先行確定
- timestep T中に到着するVisitの識別と先行確定
- 正式baseline順位列の構築
- 正式baseline順位列の先頭に連続する非参加Visitの先行確定
- 権利保有Visitの選定
- 権利保有Visitのbaseline予想通過timestep `P` の取得
- `P - 1`条件によるTVT候補Visit母集団の構築
- TVT固有可変上限`N`の適用
- `candidate_visits`のinlink別分類
- 各inlink内でのsnapshot物理順整理

また、非参加Visitが存在しない一つの具体的取引候補について、選択済み買い手から順位を構築する独立部品も実装済みである。

実装済みの主な部品は次である。

```text
build_tvt_trade_rank_without_nonparticipants()
OrderControlTvtNoNonparticipantTradeRankResult
preserves_inlink_fifo()
```

一方、次は現在の上位TVT処理へ未実装である。

- 買い手候補inlinkの抽出
- inlink別の買い手prefix生成
- 具体的買い手候補集合の列挙
- 非参加Visitあり・なしを統一した一般形順位再構成
- 候補別局所仮想計算との接続
- 経済性評価との接続
- TVT成立、不成立、情報未解決後の最終確定列の構築
- 最終確定列の確定順位ブロックへの接続

今回の一般形は、現在の上流実装を作り直すものではない。実装済みの候補Visit母集団とinlink別snapshot物理順結果を入力として、その直後にある未実装処理を具体化するものである。

---

## 2. TVT-MPを直接実装する方針

今回の一般形TVT-MPは、次の組合せを単一の枠組みで扱える。

- 単一inlinkから単一買い手
- 単一inlinkから複数買い手
- 複数inlinkから単一買い手
- 複数inlinkから複数買い手
- 非参加Visitなし
- 非参加Visitあり

そのため、当面はTVT-MP一般形を直接実装する。

```text
当面の実装対象：
TVT-MP一般形

当面の実装対象外：
TVT-SB
TVT-MH
TVT-SP
```

TVT-SB、TVT-MH、TVT-SPは、TVT-MP一般形へ制約条件を加えた派生方式とみなせる。

時間的余裕があり、研究上の比較価値があると判断した場合に限り、将来追加する。今回のTVT-MP実装へ、これらの方式固有の制約を混在させない。

---

## 3. アルゴリズム完成までの経緯

### 3.1 ユーザーが考案した当初方式

ユーザーが最初に考案した一般形では、非参加Visitのbaseline順位を固定したうえで、各売り手の後退順位を個別に計算する方式を採っていた。

中心となる考え方は次のとおりである。

1. 非参加Visitの順位をbaseline順位のまま固定する
2. 買い手を、非参加Visitの順位を飛ばしながら前方へ配置する
3. 各売り手について、その売り手を追い抜く買い手数を数える
4. 売り手のbaseline順位へ、追い抜く買い手数を加える
5. 売り手が後退する途中でまたぐ、または重なる非参加Visit数を加える
6. 暫定位置が非参加Visitの順位である場合、さらに後方の空き順位へ移す
7. 完成した順位について同一inlink FIFOを検査する

交通上の意味は次である。

```text
買い手に追い抜かれた数だけ売り手が後退する
+
非参加Visitの固定順位を避ける分だけ追加で後退する
```

### 3.2 当初方式で判明した一般形上の問題

非参加Visitの影響を一度だけ数えて加算する方式では、一般形の最終順位を正しく求められない場合がある。

例えば、次の条件を考える。

```text
売り手のbaseline順位：1位
売り手を追い抜く買い手数：5
非参加Visitのbaseline順位：2位、4位、7位、9位
```

買い手の影響だけを反映すると、売り手の暫定順位は6位となる。

```text
1 + 5 = 6位
```

1位から6位までには、2位と4位の非参加Visitが存在する。その2件を反映すると8位になる。

```text
6 + 2 = 8位
```

しかし、6位から8位へ追加的に後退したことで、7位の非参加Visitを新たにまたいでいる。

8位そのものは非参加Visitの順位ではないため、「暫定位置が非参加Visitと重なるか」だけを確認しても、7位をまたいだ影響を検出できない。

7位の影響を反映して9位へ移ると、9位にも非参加Visitが存在する。最終的には10位へ移す必要がある。

したがって、個別補正式を使う場合は、新たにまたぐ非参加Visitがなくなるまで繰り返し補正する必要がある。

この繰り返し補正は実装可能ではあるが、処理の理解、検証、例外判定が複雑になる。

### 3.3 空き順位枠方式への転換

当初方式が求めていた最終結果は、次の条件を満たす順位である。

- 非参加Visitはbaseline順位を維持する
- 買い手はbaseline相対順を維持して前方へ移る
- 売り手はbaseline相対順を維持して残りの順位へ移る

そこで、各売り手の後退量を個別計算するのではなく、順位枠へ直接配置する方式へ転換した。

一般形は次のとおりである。

```text
非参加Visitのbaseline順位枠を固定する
↓
非参加Visitが使用していない空き順位を昇順で取得する
↓
買い手をbaseline相対順で空き順位の先頭側へ配置する
↓
売り手をbaseline相対順で残りの空き順位へ配置する
```

この方式は、ユーザーが考案した個別補正方式と同じ最終結果を、より簡潔に直接構築する。

非参加Visitによる追加後退は、非参加Visitの順位を最初から使用不可にすることで自動的に反映される。

---

## 4. 非参加Visitが0件の場合との統一

空き順位枠方式は、非参加Visitが存在しない場合にもそのまま使用できる。

非参加Visitが0件なら、固定される順位枠も0件となり、すべての順位が空き順位になる。

例えば、`trade_scope`が5件なら、空き順位は次のとおりである。

```text
1位、2位、3位、4位、5位
```

その先頭側へ買い手をbaseline相対順で配置し、残りへ売り手をbaseline相対順で配置する。

したがって、非参加Visitの有無によって順位再構成アルゴリズムを分ける必要はない。

```text
非参加Visitあり：
一部の順位を固定してから、残りへ買い手と売り手を配置する

非参加Visitなし：
固定順位が空の状態で、全順位へ買い手と売り手を配置する
```

既存の非参加Visitなし順位計算部品は実装済みである。

一般形実装時には、非参加Visit数を0件とした一般形が、既存部品と同じ結果を返すことを回帰テストで確認する。

確認対象は少なくとも次である。

- `buyers_sorted`
- `sellers_sorted`
- `last_buyer_rank`
- Visitごとの取引後順位
- `trade_order`
- `trade_scope`外Visitの順位

同値性確認後に、既存関数を残すか、一般形を呼ぶ互換入口に変更するか、将来廃止するかを判断する。

---

## 5. timestep Tに到着するVisit

### 5.1 snapshot時点の分類

timestep Tに対象Nodeへ到着するVisitは、snapshot取得時点ではまだ到着していない。

したがって、snapshot時点ではB型である。

```text
was_arrived_at_snapshot = False
```

### 5.2 baseline実行後の状態

timestep Tの`Vehicle.update()`によって対象Nodeへ到着すると、collectorには次が記録される。

```text
baseline_arrival_timestep = T
```

したがって、固定horizon 30または50の経過後にcollectorを読む段階では、T到着Visitも到着情報取得済みとして扱える。

### 5.3 意思決定窓との関係

意思決定窓の到着条件は次である。

```text
T < baseline_arrival_timestep <= T + 6
```

したがって、T到着Visitは意思決定窓へ含めない。

T到着Visitはsnapshot時点の既到着A型とは区別されるが、TVT起点にはしない。既存の先行順位確定処理によって、権利保有Visitの選定前に処理される。

後続処理では、単に「snapshot時点でB型だった」という情報だけを使わない。

次を組み合わせて扱う。

- `was_arrived_at_snapshot`
- `baseline_arrival_timestep`
- 現在の順位状態
- 既到着VisitとT到着Visitの先行確定結果

---

## 6. `candidate_visits`

`candidate_visits`は、具体的買い手候補集合を作る前のTVT候補Visit母集団である。

対象Nodeについて、次を満たすVisitから構成される。

- snapshot固定集合内のB型Visit
- 現在順位未確定
- `baseline_arrival_timestep`が取得済み
- 権利保有Visitのbaseline予想通過timestepを`P`とした場合、次を満たす

```text
baseline_arrival_timestep <= P - 1
```

- 正式baseline順の先頭から、TVT固有可変上限`N`以内

正式baseline順位は、対象Nodeへ向かう複数inlink上のVisitを統合し、次の順により決定する。

1. `baseline_arrival_timestep`
2. `arrival_tiebreaker`
3. `vehicle_id`

参加・非参加は正式baseline順位の決定に使用しない。

`candidate_visits`には、次が含まれ得る。

- 権利保有Visit
- 買い手候補になり得る参加Visit
- 売り手になり得る参加Visit
- 非参加Visit

`candidate_visits`は、買い手集合、売り手集合、取引当事者集合のいずれでもない。

---

## 7. 参加Mapping

各Vehicleの既存属性は次である。

```text
participates_in_order_exchange
```

後続処理では、Vehicleオブジェクトへ戻らず、Visit単位のMappingを使用する。

```text
participates_by_visit_key:
VisitKey → participates_in_order_exchange
```

MappingのキーはVehicle名だけではなく、既存のVisitKeyである。

```text
VisitKey = (vehicle_name, visit_id)
```

候補生成および一般形順位再構成では、少なくとも次を確認する。

- 必要なVisitKeyがMappingに存在する
- 値がPythonの`bool`である
- 買い手候補がすべて参加Visitである
- 権利保有Visitが参加Visitである
- 非参加Visitが買い手または売り手に分類されない

参加状態は、正式baseline順位の決定には使用しない。

---

## 8. 全World baseline情報不足

上限`N`適用後の`candidate_visits`のうち、1件以上で`baseline_passage_timestep`が未取得の場合、statusは次となる。

```text
UNRESOLVED_CANDIDATE_PASSAGES
```

この場合、`candidate_visits`自体は、`P - 1`条件と上限`N`によって確定済みである。

また、inlink別snapshot物理順への整理も実行済みである。これは候補母集団を道路別に整理する中立的な情報整理だからである。

一方、prefixおよび具体的買い手候補集合は生成しない。

```text
UNRESOLVED_CANDIDATE_PASSAGES
→ candidate_visitsは保持
→ inlink別snapshot物理順も保持
→ prefixは生成しない
→ 具体的買い手候補集合は生成しない
→ TVT形成へ進まない
```

情報取得済みVisitだけを使って買い手候補を作ることは、部分的TVTに該当するため禁止する。

その理由は、除外されたVisitが実際には買い手、売り手、非参加固定順位Visitのいずれかとして順位再構成に関係する可能性があるためである。

情報不足Visitを除いて取引を形成すると、除外されたVisitが順位を下げられても補償を受けないなど、不公正な結果が生じ得る。

したがって、全World baselineにおいて、対象Nodeの上限`N`以内の候補全員について共通情報が揃わなければ、その対象NodeではTVT形成へ進まない。

prefix生成へ進めるのは次の場合だけである。

```text
BASELINE_INFORMATION_COMPLETE
```

---

## 9. inlink別snapshot物理順

実装済み部品は、`candidate_visits`をinlink別に分け、各inlink内でsnapshot時点に対象Nodeへ近かったVisitから後方へ並べている。

各inlinkの結果は、次の列を持つ。

```text
candidate_visit_keys_head_to_tail
```

index 0が、snapshot時点で対象Nodeに最も近いcandidate Visitである。

この列は、そのinlinkに属する`candidate_visits`だけを含む。

次の意味は持たない。

- 全inlink横断の正式baseline順位が連続している
- 買い手prefixが確定している
- 買い手または売り手が確定している
- 取引後順位が決まっている

同じVisitKeyが複数inlinkに現れないことは、実装済み部品が保証している。

---

## 10. 買い手候補inlink

### 10.1 権利保有inlinkの除外

権利保有Visitと同じinlinkからは買い手を選ばない。

同じinlink上で権利保有Visitより後方を走るVisitは、権利保有Visitを物理的に追い越せないためである。

ただし、権利保有inlink自体を順位再構成から除外するわけではない。

権利保有inlink上のVisitが`trade_scope`に含まれる場合は、次のように扱う。

- 買い手でない参加Visitなら売り手
- 非参加Visitなら固定順位Visit

したがって、次を明確に区別する。

```text
買い手候補生成：
権利保有inlinkを除外する

trade_scopeと順位再構成：
権利保有inlink上のVisitも含める
```

### 10.2 非空prefixを作れないinlink

権利保有inlink以外でも、inlink別Visit列の物理先頭が非参加Visitなら、そのinlinkから非空の買い手prefixを作ることはできない。

作れるprefixは空prefixだけである。

空prefixしか持たないinlinkを直積に含めても、生成される非空の具体的買い手候補集合は変化しない。

そのため、買い手候補inlinkは次をすべて満たすinlinkとする。

- 権利保有inlinkではない
- inlink別candidate Visit列が存在する
- snapshot物理先頭のcandidate Visitが参加Visitである
- 1件以上の非空prefixを生成できる

空prefixしか作れないinlinkは、組合せ生成対象から除外する。

ただし、そのinlink上のVisitを`candidate_visits`から削除するわけではない。`trade_scope`に入る場合は順位再構成へ含める。

### 10.3 買い手候補inlinkが0本の場合

買い手候補inlinkが0本なら、具体的買い手候補集合は0件である。

これは異常ではなく、正常な「具体的買い手候補なし」である。

---

## 11. 買い手prefix

### 11.1 prefixの基準

各inlinkの買い手prefixは、順位未確定TVT候補Visit列から当該inlinkに属するVisitを抽出し、snapshot物理順で並べたVisit列の先頭から連続して選ぶ。

prefixの連続性は、対象Nodeへ向かう複数inlinkを統合した正式baseline順位ではなく、同一inlink内のsnapshot物理順を基準とする。

### 11.2 最大prefix

各買い手候補inlinkについて、inlink別candidate Visit列をsnapshot物理先頭から確認する。

- 参加Visitが続く間、最大prefixへ追加する
- 最初の非参加Visitへ到達したら停止する
- 最初の非参加Visit自身は含めない
- 最初の非参加Visitより後方は含めない
- 非参加Visitが存在しなければ、inlink別Visit列の末尾まで含める

例えば、snapshot物理順が次の場合を考える。

```text
A、B、C、D
```

AとBが参加Visit、Cが最前方の非参加Visitなら、最大prefixは次である。

```text
A、B
```

C自身と、その後方のDは買い手prefixへ含めない。

非参加Visitが存在しない場合は、inlink別Visit列の末尾までを最大prefixにできる。

### 11.3 全prefixの生成

非参加Visitの有無にかかわらず、空prefixから最大prefixまでのすべてのprefixを生成する。

最大prefixが次の場合、

```text
A、B、C
```

生成するprefixは次である。

```text
空prefix
A
A、B
A、B、C
```

最大prefixより短いprefixを選べることは、非参加Visitが存在するときだけの規則ではない。

非参加Visitは、存在する場合に最大prefixを短くする。実際に選択するprefixは、空prefixから最大prefixまでのいずれでもよい。

各prefixは、変更不能なVisitKeyのtupleとして表す方向が適切である。

prefixの列挙順は、候補の優先順位を意味しない。

---

## 12. 具体的買い手候補集合

### 12.1 定義

**具体的買い手候補集合**とは、各買い手候補inlinkからprefixを1つずつ選び、それらを統合して正式baseline相対順へ並べた、空でない参加Visit列である。

これは経済性評価前の候補であり、確定した買い手集合ではない。

### 12.2 prefixの組合せ

各買い手候補inlinkについて、空prefixを含むprefix候補を用意する。

そのうえで、各inlinkからprefixを1つずつ選ぶ直積を生成する。

例えば、次の場合を考える。

```text
inlink X：
空
A
A、B

inlink Y：
空
C
```

組合せは次となる。

```text
空 ＋ 空
A ＋ 空
A、B ＋ 空
空 ＋ C
A ＋ C
A、B ＋ C
```

すべてのinlinkで空prefixを選択した組合せだけを除外する。

一部のinlinkが空で、別のinlinkが非空である組合せは残す。

### 12.3 正式baseline順への並べ替え

各組合せで選ばれたVisitKeyを統合した後、`candidate_visits`内の位置に従って正式baseline順へ並べる。

到着timestepなどの順位キーを再計算する必要はない。すでに正式baseline順である`candidate_visits`の位置を利用する。

### 12.4 用語の統一

経済性評価前は、次の表現に統一する。

```text
具体的買い手候補集合
```

取引候補が経済性評価を通過して採用された後に、そのVisit列を確定買い手集合として扱う。

### 12.5 重複候補

一つのVisitKeyは一つのsnapshot inlinkにだけ属する。

また、単一inlinkのprefixは選択した長さによって一意に決まる。

したがって、異なるprefix組合せから同じ具体的買い手候補集合が生成されることは、構造上起こらない。

本番処理では重複除去を行わない。

重複除去を入れると、本来発生してはならない重複を静かに隠す可能性がある。

専用テストで、具体的買い手候補集合に重複がないことを確認する。

---

## 13. 候補数

買い手候補inlink `i`の最大prefix長を`M_i`とする。

空prefixを含むprefix数は次である。

```text
M_i + 1
```

全inlinkの組合せ数から全空組合せ1件を除くため、具体的買い手候補集合数は次となる。

```text
∏(M_i + 1) - 1
```

権利保有inlinkは積へ含めない。

空prefixしか作れないinlinkを含めた場合、その係数は1となり候補数は変わらない。実装上は組合せ対象から除外する。

`candidate_visits`は最大`N`件に制限されている。

権利保有Visitを除く最大`N - 1`件が、すべて異なる買い手候補inlinkに1件ずつ存在する場合の粗い候補数上限は次である。

```text
2^(N - 1) - 1
```

例えば`N = 10`なら、粗い上限は511候補である。

初期実装では、性能問題が実測される前に複雑な枝刈りを導入しない。

---

## 14. `trade_scope`

### 14.1 正式名称

既存の実装名および設計名として、次を維持する。

```text
trade_scope
```

日本語表記は次とする。

> **取引候補別順位再構成範囲**

### 14.2 定義

一つの具体的買い手候補集合について、正式baseline順位が最も後ろの買い手候補Visitを特定する。

このVisitを最後尾買い手候補とする。

`trade_scope`は次である。

> 正式baseline順に並んだ`candidate_visits`の先頭から、最後尾買い手候補までのVisit列

既存コードでは、概念上次の処理に対応する。

```text
最後尾買い手候補のbaseline順位を取得する
↓
candidate_visitsの先頭から、その順位までを切り出す
```

`trade_scope`の末尾は必ず買い手候補Visitである。

### 14.3 `candidate_visits`との違い

```text
candidate_visits
=
P - 1条件と可変上限Nによって確定した候補母集団

trade_scope
=
一つの具体的買い手候補集合について、
最後尾買い手候補までを切り出した順位再構成範囲
```

`candidate_visits`全体が常に`trade_scope`になるわけではない。

### 14.4 局所順位

`trade_scope`内では、先頭を1位とする1始まりの局所順位を使う。

例えば、`trade_scope`が5件なら、使用する局所順位は次である。

```text
1位、2位、3位、4位、5位
```

`trade_scope`は現在の未確定候補列の先頭から始まる。そのため、`trade_scope`内の1位、2位、3位は、未確定候補列の先頭から数えた1位、2位、3位と一致する。

順位再構成完了後、`trade_scope`より前に存在する確定順位ブロックの件数を加え、対象Nodeへ向かう複数inlinkを統合した順位へ接続する。

---

## 15. `trade_scope`内の3分類

`trade_scope`内のVisitを次の3種類へ重複なく分類する。

### 15.1 買い手

具体的買い手候補集合に含まれる参加Visit。

### 15.2 非参加Visit

参加Mappingの値が`False`であるVisit。

非参加Visitは買い手にも売り手にもならない。

### 15.3 売り手

`trade_scope`内の参加Visitのうち、具体的買い手候補集合に含まれないVisit。

権利保有Visitは買い手にならず、参加Visitであるため、TVTが成立する具体的候補では売り手となる。

一般形では、次の関係が成立する。

```text
買い手
＋
売り手
＋
非参加Visit
=
trade_scope
```

3集合は互いに重複しない。

---

## 16. 売り手は必ず順位を後退する

`trade_scope`の末尾は必ず買い手候補Visitである。

そのため、`trade_scope`内の任意の売り手よりbaseline順位が後ろに、少なくとも1件の買い手候補Visitが存在する。

後方の買い手候補Visitが売り手より前へ移るため、売り手は少なくとも1順位後退する。

非参加Visitの固定順位は、売り手の後退を打ち消さない。売り手が使用できる順位枠を減らし、追加的に後退させる可能性があるだけである。

したがって、すべての売り手について次が成立する。

```text
取引後順位 > baseline順位
```

この性質は一般形順位再構成の専用テストで確認する。

順位構築後に、後退した参加Visitだけを改めて売り手として抽出する処理は不要である。

---

## 17. 一般形順位再構成

### 17.1 非参加Visitの順位固定

`trade_scope`内の非参加Visitを、そのVisitのbaseline局所順位と同じ順位枠へ固定する。

例えば、`trade_scope`が9件で、非参加Visitのbaseline局所順位が2位、5位、7位なら、次を固定する。

```text
2位：非参加Visit
5位：非参加Visit
7位：非参加Visit
```

### 17.2 空き順位の作成

`trade_scope`内の全順位から、非参加Visitが固定した順位を除外する。

前記の例では、空き順位は次となる。

```text
1位、3位、4位、6位、8位、9位
```

### 17.3 買い手の配置

具体的買い手候補集合は正式baseline相対順に並んでいる。

その相対順を維持したまま、空き順位の先頭側から配置する。

買い手が4件なら、前記の空き順位のうち次を使用する。

```text
1位、3位、4位、6位
```

### 17.4 売り手の配置

買い手配置後に残った空き順位へ、売り手を正式baseline相対順のまま配置する。

前記の例では、残る空き順位は次となる。

```text
8位、9位
```

### 17.5 非参加Visitが0件の場合

非参加Visitが0件なら、空き順位は1位から連続する。

買い手は先頭側へ連続して配置され、売り手はその後へ配置される。

一般形実装時には、この結果が既存の非参加Visitなし順位計算部品と一致することをテストする。

---

## 18. `trade_rank`と`trade_order`

### 18.1 `trade_rank`

`trade_rank`は取引後順位の正本である。

```text
VisitKey → 取引後順位
```

例えば、次のような対応を保持する。

```text
Visit B → 1位
Visit N → 2位
Visit D → 3位
Visit A → 4位
```

`trade_scope`外のVisitについては、baseline順位と同じ順位を保存する。

### 18.2 `trade_order`

`trade_order`は、Visitを`trade_rank`の値が小さい順に並べたVisit列である。

前記の例では次となる。

```text
B、N、D、A
```

`trade_rank`が順位の正本であり、`trade_order`はそこから派生させる。

### 18.3 VisitKey集合の一致

次の確認は、順位関係がbaselineと同じという意味ではない。

```text
trade_rankのVisitKey集合
=
正式baseline順のVisitKey集合
```

これは、取引前に存在したVisitが取引後にも過不足なく存在するという意味である。

- Visitが欠落していない
- 不明なVisitが追加されていない
- 順位再構成によってVisit集合そのものが変化していない

### 18.4 `trade_rank`と`trade_order`の一致

`trade_order`内の位置が、そのVisitの`trade_rank`と一致することを意味する。

例えば、`trade_order`の3番目にVisit Dがいるなら、次でなければならない。

```text
trade_rank[D] = 3
```

### 18.5 `trade_order`の用途

`trade_order`は主に次のために必要である。

- 取引後のVisit列を明示する
- `trade_rank`の重複、欠番、位置不一致を確認する
- `preserves_inlink_fifo()`へ取引後順序を渡す

---

## 19. 一般形の内部整合確認

順位再構成後、少なくとも次を確認する。

- 買い手、売り手、非参加Visitが`trade_scope`を重複なく分割する
- 非参加Visitの順位がbaseline局所順位から変化していない
- 買い手間のbaseline相対順が維持されている
- 売り手間のbaseline相対順が維持されている
- 全Visitに順位が1つずつ付いている
- 同じ順位が複数Visitへ割り当てられていない
- 順位に欠番がない
- 順位が1から全Visit件数までの範囲にある
- `trade_order`内の位置と`trade_rank`が一致する
- `trade_scope`が正式baseline順の先頭から`last_buyer_rank`までである
- `trade_scope`外Visitの順位が変化していない
- すべての売り手がbaseline順位より後退している

上流で保証済みの条件を、候補ごとに不要に重複確認しない。

専用テストで広く確認し、本番処理には原因不明の停止や誤順位確定を防ぐ重大な不整合確認だけを残す方針とする。

---

## 20. FIFO検査

既存の`preserves_inlink_fifo()`を一般形でも利用する。

この関数は、参加・非参加を区別しない。

取引前後で、同じinlinkに属するVisitの相対順が一致するかを確認する。

### 20.1 検査材料

取引前の材料は次である。

```text
trade_scope
```

取引後の材料は次である。

```text
trade_orderの先頭からlast_buyer_rank件
```

ただし、両方のVisit列を全体として同一順序か比較するわけではない。

各inlinkについて、取引前後の材料からそのinlinkに属するVisitだけを抽出し、抽出されたVisit列同士を比較する。

```text
各inlinkについて：

取引前のtrade_scopeから抽出したVisit列
対
取引後部分列から抽出したVisit列
```

一つでも相対順が異なればFIFO違反である。

複数inlink間のVisit順序が変化しても、各inlink内の相対順が維持されていればFIFO違反ではない。

### 20.2 非参加Visit

FIFO検査には、`trade_scope`内の次のVisitをすべて含める。

- 買い手
- 売り手
- 非参加Visit

これにより、売り手と非参加Visitの逆転も検出できる。

### 20.3 検査範囲

FIFO検査範囲は`trade_scope`である。

未確定候補列全体をFIFO検査する案は採用しない。

次の不変条件があるため、`trade_scope`外との境界へ毎候補の追加FIFO検査を行わない。

- 確定順位ブロックは既にFIFOを満たす
- `trade_scope`は未確定候補列の先頭から始まる
- `trade_scope`内のVisitは`trade_scope`内の順位へ配置される
- `trade_scope`外のVisitの順位を変更しない
- 買い手prefixは各inlinkのsnapshot物理先頭から連続する
- `trade_scope`内の全順位枠を`trade_scope`内のVisitだけで埋める

### 20.4 FIFO違反

FIFO違反は正常な候補棄却である。

```text
FIFO違反
→ 当該具体的買い手候補集合を棄却
→ 別候補の検討を続ける
```

FIFO違反を理由に、同じ具体的候補の順位を別方式で作り直さない。

---

## 21. 正常な候補棄却と重大不整合

### 21.1 正常な候補棄却または評価対象外

次は制度上あり得る結果である。

- 同一inlink FIFO違反
- 局所仮想計算で当該候補の必要情報が揃わない
- 買い手の利益条件を満たさない
- `G >= R`を満たさない
- その他の確定済み経済性条件を満たさない

これらは当該候補だけを除外し、他候補の検討を続ける。

### 21.2 重大不整合

次は、本来発生しない構造上の矛盾である。

- 同じVisitへ複数順位を割り当てる
- 同じ順位を複数Visitへ割り当てる
- 順位に欠番がある
- 順位が範囲外である
- `trade_rank`と正式baseline順のVisitKey集合が一致しない
- `trade_order`と`trade_rank`が一致しない
- 買い手、売り手、非参加Visitの分類が重複または不足する
- 非参加Visitの順位がbaseline局所順位から変化する
- 買い手間のbaseline相対順が変化する
- 売り手間のbaseline相対順が変化する
- 売り手がbaseline順位と同順位または前順位になる
- 参加Mappingに必要なVisitKeyがない
- 参加Mappingの値がPythonの`bool`でない
- 権利保有Visitが非参加として渡される
- VisitKey、対象Node、inlink、snapshot物理順の対応が壊れている

重大不整合は、通常の候補棄却として隠さず、原則として例外で停止する。

---

## 22. 候補別局所仮想計算

FIFOを満たした具体的候補について、候補別局所仮想計算を行う。

その後、経済性評価に必要な情報がすべて取得できたか確認する。

```text
FIFOを満たす
↓
候補別局所仮想計算
↓
必要情報の充足確認
↓
情報が揃った候補だけ経済性評価
```

一部候補だけ必要情報を取得できない場合は、その候補だけを評価対象から除外する。

他の評価可能候補まで破棄しない。

すべての候補が局所仮想計算で未解決なら、次として扱う。

```text
局所仮想計算未解決によるTVT不成立
```

### 22.1 全World baselineとの扱いの違い

扱いを分けることは合理的である。

全World baselineは、候補形成に必要な共通比較基準である。

上限`N`以内の候補全員について共通情報が揃っていなければ、正しい具体的候補を形成できない。そのため、その対象NodeではTVT形成へ進まない。

一方、候補別局所仮想計算は、すでに形成済みの各具体的候補を個別に評価する処理である。

一つの候補だけが未解決でも、別候補の共通比較基準や局所計算結果まで無効になるわけではない。

したがって、次の区別とする。

```text
全World baselineの候補共通情報不足
→ その対象NodeではTVT形成へ進まない

候補別局所仮想計算の一部候補未解決
→ 未解決候補だけ除外
→ 他の評価可能候補は維持
```

---

## 23. 売り手の順位後退と通過timestep変化

売り手は必ず順位を後退する。

ただし、順位が後退しても、通過timestepが必ず遅くなるとは限らない。

したがって、次を区別する。

```text
売り手であるか
→ 順位再構成上の役割で決まる

売り手が補償を受けるか
→ baselineと順位再構成後の通過timestep差で決まる
```

### 23.1 通過timestepが遅くなる売り手

```text
順位再構成後の予想通過timestep
>
baseline予想通過timestep
```

正の予想遅延時間に基づいて、必要補償額または留保額を計算する。

### 23.2 通過timestepが変わらない売り手

```text
順位再構成後の予想通過timestep
=
baseline予想通過timestep
```

当該売り手に関する受取額と支払額はともに0とする。

### 23.3 通過timestepが早くなる売り手

```text
順位再構成後の予想通過timestep
<
baseline予想通過timestep
```

順位は後退しているが、補償対象となる時間遅延はない。

当該Visitを買い手へ役割変更しない。

また、買い手とは異なり、時間短縮を理由とする支払義務を売り手へ課さない。

当該売り手に関する受取額と支払額はともに0とする。

---

## 24. 経済性評価

局所仮想計算で必要情報が揃った候補だけを経済性評価へ進める。

各買い手の利益を次とする。

```text
G_b
```

各買い手について、次を必要条件とする。

```text
G_b > 0
```

1件でも`G_b <= 0`となる買い手を含む候補は成立候補としない。

買い手側総価値は次である。

```text
G = Σ G_b
```

各売り手の必要補償額または留保額を`R_s`とする。

売り手側必要補償総額は次である。

```text
R = Σ R_s
```

経済的成立条件は次である。

```text
G >= R
```

候補の余剰は次である。

```text
surplus = G - R
```

---

## 25. 成立候補の選択規則

既存設計では、`surplus`が同値の場合、取引当事者総数が多い候補を優先していた。

今回、この第二比較基準を変更する。

### 25.1 変更前

```text
surplusが最大
↓
同値なら取引当事者総数が多い
↓
それも同じならランダム
```

### 25.2 最新方針

```text
surplusが最大
↓
同値なら買い手数が多い
↓
買い手数も同じならランダム
```

### 25.3 変更理由

取引当事者総数が多くても、買い手が多いとは限らない。

売り手が多いために取引当事者総数が大きくなった候補を、同じ`surplus`を持つ別候補より優先することは、時間価値の高いVehicleを前進させるTVTの目的と必ずしも一致しない。

同じ`surplus`なら、より多くの買い手へ時間短縮機会を提供する候補を優先する方が制度目的に合う。

`surplus`最大化を最優先にする原則は変更しない。同じ`surplus`を持つ候補間の第二比較基準だけを変更する。

最後のランダム選択に使う具体的なRNG設計は、引き続き未確定である。

prefix列挙順や具体的候補生成順を、ランダム選択の代用にしない。

---

## 26. TVT成立時の最終確定

TVTが成立した場合、採用候補の取引当事者だけを確定すればよいわけではない。

TVT当事者が意思決定窓内Visitの一部に限られる場合でも、既存のTVT成立時確定ルールに従い、TVT当事者外を含む意思決定窓内Visitの順位も決定する。

したがって、成立時には次を行う。

```text
採用候補の取引後順位を取得する
↓
TVT当事者外を含む意思決定窓内Visitについて、
既存の成立時確定ルールに従って順位を補う
↓
成立時に確定すべきVisit全体の最終確定列を構築する
↓
最終確定列を確定順位ブロックへ接続する
```

TVT成立時の確定範囲は、採用候補の`trade_scope`だけと無条件に同一視しない。

既存ルール上、最後尾買い手の順位と意思決定窓の確定範囲の双方を考慮する必要がある。

---

## 27. TVT不成立時および情報未解決時の最終確定

### 27.1 成立可能候補がない場合

次のいずれかにより、成立可能候補が0件になる場合がある。

- 具体的買い手候補集合が存在しない
- 全具体的候補がFIFO違反
- 全候補が局所仮想計算で未解決
- すべての候補が買い手利益条件を満たさない
- すべての候補が`G >= R`を満たさない

この場合、理由を区別してTVT不成立とする。

その後、TVT不成立時の既存ルールに従い、残存する意思決定窓内の未確定Visitをbaseline順で並べた最終確定列を構築し、確定順位ブロックへ接続する。

### 27.2 全World baseline情報未解決

全World baselineで必要な共通情報が揃わない場合は、経済条件によるTVT不成立と同一視しない。

情報未解決として扱う。

その後、情報未解決時の既存ルールに従い、残存する意思決定窓内の未確定Visitから最終確定列を構築し、確定順位ブロックへ接続する。

意思決定窓外の未確定Visitは、情報不足や上限外であることだけを理由に確定しない。

---

## 28. 一般形アルゴリズムの全処理順

1. TVT固有可変上限`N`の適用後に確定した、対象Nodeの`candidate_visits`を取得する

2. 対象Nodeの候補集合statusを確認する

3. `UNRESOLVED_CANDIDATE_PASSAGES`その他の情報不足statusなら、prefixと具体的買い手候補集合を生成せず、情報未解決時処理へ進む

4. `BASELINE_INFORMATION_COMPLETE`なら、実装済みのinlink別snapshot物理順結果を取得する

5. 参加Mappingについて、必要なVisitKeyの存在とPythonの`bool`値を確認する

6. 権利保有Visitが参加Visitであることを確認する

7. 権利保有inlinkを買い手候補inlinkから除外する

8. 物理先頭が非参加Visitで、空prefixしか作れないinlinkを組合せ対象から除外する

9. 各買い手候補inlinkについて最大prefixを作る

10. 最前方非参加Visitがある場合はその直前まで、存在しない場合はinlink別candidate Visit列の末尾までを最大prefixとする

11. 各inlinkについて、空prefixから最大prefixまでの全prefixを生成する

12. 各買い手候補inlinkからprefixを1つずつ選ぶ全組合せを生成する

13. 全inlinkが空prefixとなる組合せを除外する

14. 各組合せのVisitKeyを統合する

15. 統合したVisitKeyを`candidate_visits`内の正式baseline相対順へ並べる

16. 空でないVisitKey tupleを、一つの具体的買い手候補集合とする

17. 各具体的買い手候補集合の最後尾買い手候補を特定する

18. `candidate_visits`の先頭から最後尾買い手候補までを`trade_scope`とする

19. `trade_scope`内のVisitを、買い手、売り手、非参加Visitへ分類する

20. `trade_scope`内で1から始まる局所順位枠を作る

21. 非参加Visitをbaseline局所順位と同じ順位枠へ固定する

22. 非参加Visitが使用していない空き順位を昇順で取得する

23. 買い手をbaseline相対順で空き順位の先頭側へ配置する

24. 売り手をbaseline相対順で残りの空き順位へ配置する

25. `trade_rank`を取引後順位の正本として作る

26. `trade_scope`外Visitへbaseline順位を設定する

27. `trade_rank`から`trade_order`を作る

28. 買い手、売り手、非参加Visitによる`trade_scope`の分割、順位の一意性、連続性、相対順、非参加順位固定、売り手後退、`trade_rank`と`trade_order`の一致、`trade_scope`外順位不変を確認する

29. 取引前の`trade_scope`と、取引後の`trade_order`先頭`last_buyer_rank`件をFIFO検査の材料とする

30. 各inlinkについて、取引前後の材料から同じinlinkのVisit列を抽出して比較する

31. FIFO違反候補を正常に棄却する

32. FIFOを満たした候補について候補別局所仮想計算を行う

33. 局所仮想計算で必要情報が揃った候補だけを経済性評価へ進める

34. 局所仮想計算未解決候補だけを除外し、他の評価可能候補は維持する

35. 各買い手について`G_b > 0`を確認する

36. 買い手側総価値`G`と売り手側必要補償総額`R`を計算する

37. `G >= R`を満たす候補を成立可能候補とする

38. 成立可能候補から`surplus = G - R`が最大の候補を選ぶ

39. `surplus`が同値なら、買い手数が多い候補を選ぶ

40. 買い手数も同じならランダムに選ぶ

41. 成立候補がある場合は、採用候補の取引後順位と、既存成立時ルールによるTVT当事者外の順位を統合し、成立時の最終確定列を作る

42. 成立時の最終確定列を確定順位ブロックへ接続する

43. 成立候補がない場合は、不成立理由を確定する

44. 不成立時の既存ルールに従い、残存する意思決定窓内の未確定Visitをbaseline順に並べた最終確定列を作る

45. 不成立時の最終確定列を確定順位ブロックへ接続する

46. 全World baseline情報が未解決の場合は、TVT不成立と混同せず、情報未解決時の既存ルールに従って最終確定列を構築・接続する

---

## 29. 専用テストで固定する事項

### 29.1 prefix生成

- 権利保有inlinkから買い手を選ばない
- 物理先頭が非参加Visitのinlinkから非空prefixを生成しない
- 各買い手候補inlinkに空prefixが存在する
- 非参加Visitの有無にかかわらず、空から最大までの全prefixを生成する
- prefixはsnapshot物理先頭から連続する
- 最前方非参加Visit自身をprefixへ含めない
- 最前方非参加Visitより後方のVisitをprefixへ含めない
- 非参加Visitがなければinlink別Visit列の末尾まで最大prefixにできる
- 全空組合せだけを除外する
- 一部inlinkだけ空の組合せを残す

### 29.2 具体的買い手候補集合

- 空でない
- 全Visitが参加Visitである
- 権利保有Visitを含まない
- 権利保有inlink上のVisitを含まない
- 正式baseline相対順に並ぶ
- VisitKeyの重複がない
- 同一候補集合が重複生成されない
- 非参加Visitが存在しない場合にも正しく生成できる
- `UNRESOLVED_CANDIDATE_PASSAGES`では生成しない

### 29.3 `trade_scope`

- `candidate_visits`の先頭から始まる
- 末尾が最後尾買い手候補である
- `last_buyer_rank`と件数が一致する
- `trade_scope`外Visitの順位が変化しない

### 29.4 順位再構成

- 買い手、売り手、非参加Visitが`trade_scope`を重複なく分割する
- 非参加Visitの順位がbaseline局所順位から変化しない
- 買い手が空き順位の先頭部分を使用する
- 売り手が残りの空き順位を使用する
- 買い手間のbaseline相対順を維持する
- 売り手間のbaseline相対順を維持する
- 全売り手について取引後順位がbaseline順位より後ろになる
- 順位重複がない
- 順位欠番がない
- 順位が正しい範囲内にある
- `trade_rank`と`trade_order`が一致する
- 非参加Visit0件で既存の非参加Visitなし関数と同じ結果を返す

### 29.5 FIFO

- 同一inlink相対順を維持した候補を受理する
- 売り手と非参加Visitの逆転を検出する
- 買い手と非参加Visitの逆転を検出する
- 複数inlink間の順序変更をFIFO違反と誤判定しない
- FIFO違反時に例外を出さず`False`を返す
- FIFO違反時に順位を自動再計算しない

### 29.6 baseline情報と局所仮想計算

- 全World baseline情報不足時にprefixを生成しない
- 情報取得済みVisitだけによる部分的TVTを形成しない
- 局所仮想計算未解決候補だけを除外する
- 他の評価可能候補を維持する
- 全候補が局所仮想計算で未解決なら専用理由でTVT不成立とする

### 29.7 経済性と候補選択

- 順位後退かつ通過遅延ありの売り手へ補償を計上する
- 順位後退かつ通過timestep不変なら金銭移転を0とする
- 順位後退かつ通過timestep短縮でも金銭移転を0とする
- 通過timestepが短縮した売り手へ支払義務を課さない
- `G_b <= 0`の買い手を含む候補を除外する
- `G >= R`を満たす候補だけを成立可能とする
- `surplus`最大候補を選ぶ
- 同一`surplus`なら買い手数が多い候補を選ぶ
- 買い手数も同じ場合の選択は、RNG設計確定後にテストする

### 29.8 最終確定列

- TVT成立時にTVT当事者だけでなく、既存ルール上確定すべき当事者外Visitも含める
- TVT成立時の最終確定列を確定順位ブロックへ接続する
- TVT不成立時に意思決定窓内の残存未確定Visitをbaseline順で確定する
- 情報未解決と経済条件による不成立を区別する
- 意思決定窓外Visitを、情報不足や上限外だけを理由に確定しない

---

## 30. 実装時に残る判断事項

一般形アルゴリズムの制度ロジックは整理できたが、次は実装設計時に決める。

- prefix生成部品の正式な公開関数名
- 具体的買い手候補集合を表す結果型名
- prefix生成結果を全Node単位とするかNode単位とするか
- 上流結果への参照を結果型へ保持するか
- 一般形順位結果型の正式名称
- 既存の非参加Visitなし結果型との移行方法
- 既存関数を互換入口として残すか
- `_verify_local_trade_rank_state()`を一般化するか、新しい検証関数を追加するか
- 同値候補のランダム選択に使用するRNG
- RNG選択を候補列挙順から独立させる方法
- 局所仮想計算結果型との接続
- 経済性評価結果型との接続
- TVT成立時、不成立時、情報未解決時の既存確定ルールとの具体的なAPI接続

これらは一般形アルゴリズムの中核を変更する事項ではなく、主としてAPI、結果型、互換性、責任分離に関する実装上の判断である。

**2026-09-14更新：** 具体的買い手候補集合生成部品について、次の実装前仕様を確定した。Python実装と専用テストは未着手である。最新詳細は、本ファイルの「具体的買い手候補集合生成部品の実装前仕様」を正本とする。

- 公開関数名は`build_tvt_mp_concrete_buyer_candidate_sets`とする。
- 具体的買い手候補集合の結果型名は`OrderControlTvtMpConcreteBuyerCandidateSet`とする。
- inlink別の空prefixから最大prefixまでの全prefixを、公開結果へ保持する。
- 全体結果は、上流の`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`を同一オブジェクト参照で保持する。
- 一般形順位結果型、既存非参加Visitなし結果型との移行、RNG、局所仮想計算・経済性評価・最終確定とのAPI接続は、本部品の範囲外として残す。

**2026-09-15更新：** 一般形順位再構成部品について、次の実装前仕様を確定した。Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP一般形順位再構成部品の実装前仕様」を正本とする。

- 公開関数名は`build_tvt_mp_general_trade_ranks`とする。
- 一候補結果型は`OrderControlTvtMpGeneralTradeRankResult`とする。既存の`OrderControlTvtNoNonparticipantTradeRankResult`は再利用しない。
- `_verify_local_trade_rank_state()`は一般化しない。一般形専用のprivate内部整合確認を新規モジュールへ設ける。
- 既存の非参加Visitなし順位計算部品と`preserves_inlink_fifo()`は今回変更しない。既存関数を互換入口にするか、将来廃止するかは別途判断する。
- RNG、局所仮想計算・経済性評価・最終確定とのAPI接続は、本部品の範囲外として残す。

---

## 31. 現時点の結論

今回整理したTVT-MP一般形は、非参加Visitありと非参加Visitなしを、同一の候補生成規則および順位再構成規則で扱える。

中核処理は次である。

```text
上限N適用済みcandidate_visitsを取得
↓
全候補のbaseline情報が完全な場合だけ候補生成へ進む
↓
各inlinkで空prefixを含む全prefixを生成
↓
最前方非参加Visitがある場合は最大prefixをその直前までに制限
↓
prefixの全組合せから具体的買い手候補集合を作る
↓
最後尾買い手候補までをtrade_scopeとする
↓
非参加Visitのbaseline局所順位枠を固定する
↓
残る空き順位の先頭側へ買い手を配置する
↓
さらに残る空き順位へ売り手を配置する
↓
trade_rankからtrade_orderを作る
↓
各inlinkの取引前後の相対順を比較してFIFOを確認する
↓
FIFOを満たした候補だけ局所仮想計算を行う
↓
局所仮想計算の必要情報が揃った候補だけ経済性評価へ進める
↓
surplus最大候補を選ぶ
↓
同値なら買い手数を優先する
↓
さらに同じならランダムに選ぶ
↓
成立、不成立、情報未解決の各既存ルールに従って最終確定列を構築する
↓
最終確定列を確定順位ブロックへ接続する
```

この順位再構成方式は、ユーザーが考案した売り手後退量の個別計算が目指していた最終順位を、非参加Visitの順位枠を先に固定し、残った空き順位へ買い手と売り手を配置することで、より簡潔かつ検証しやすく実現する。

現時点では、一般形アルゴリズムの中核に大きな論理矛盾は見つかっていない。

同値候補の第二比較基準を「取引当事者総数」から「買い手数」へ変更する点は、今回合意した最新方針である。正式メモへ反映する際は、既存の歴史的記述を削除せず、最新方針への更新として明示する必要がある。

### 主な改善点

- `candidate_visits`、具体的買い手候補集合、`trade_scope`を明確に区別した。
- timestep T到着Visitと上限`N`の扱いを既存実装に合わせた。
- 全World baseline未解決と局所候補未解決の処理差を明示した。
- `trade_rank`、`trade_order`、FIFO検査の関係を具体化した。
- TVT成立時も、当事者外の意思決定窓内Visitを含む最終確定列が必要であることを反映した。
- 売り手の通過が早まった場合に支払義務を課さない規則を明記した。
- 同一`surplus`時の第二比較基準を、取引当事者総数から買い手数へ変更した。

# 旧メモとの差分と現在の適用関係

## 旧メモから更新する制度設計

- 非参加Visitなし専用方式と、非参加Visitあり単一買い手向け固定順位枠方式を、非参加Visitあり・なしを統一する一般形へ更新する。
- 非参加Visitあり複数買い手一般形が未確定であった状態から、TVT-MP一般形を最新設計として確定する。
- TVT-SB、TVT-MH、TVT-SP、TVT-MPを順番に実装する旧方針から、TVT-MP一般形を直接実装する方針へ更新する。
- 売り手ごとの個別後退式を一般形順位構築の正本とせず、空き順位枠方式を一般形の正本とする。
- `surplus`同値時に取引当事者総数を優先する旧規則から、買い手数を優先する最新規則へ更新する。
- prefix規則が未確定であった状態から、本メモ記載のprefix規則を最新正本とする。ただし、Python実装はまだ行っていない。
- `UNRESOLVED_CANDIDATE_PASSAGES`でもinlink別snapshot物理順を整理する実装済み方針は維持する。
- `UNRESOLVED_CANDIDATE_PASSAGES`ではprefixおよび具体的買い手候補集合を生成しない。
- 売り手が順位を後退するという制度上の扱いは維持する。
- 売り手の通過timestepが不変または短縮した場合は、当該売り手の受取額・支払額をともに0とし、買い手へ役割変更しない。

## 維持する実装済み事実

- 旧メモ§25.25.34.51までに記録された実装済み事実を維持する。
- `candidate_visits`の構築、可変上限`N`、inlink別snapshot物理順整理を維持する。
- 非参加Visitなしの一具体的候補向け順位計算部品が実装済みであるという事実を維持する。
- `preserves_inlink_fifo()`の実装済み事実を維持する。
- 本メモ作成時点では、これら既存Pythonコードを変更しない。

# 未実装境界

本メモ作成時点では、次は未実装である。

- 買い手候補inlinkの抽出
- 買い手prefix
- 具体的買い手候補集合
- 非参加Visitあり・なしを統一した一般形順位再構成
- 一般形順位再構成の結果型
- 候補別局所仮想計算への上位接続
- 経済性評価
- 成立候補選択
- 支払いと補償
- TVT成立時の最終確定列
- TVT不成立時の最終確定列
- 情報未解決時の最終確定列
- 確定順位ブロックへの上位接続
- 上位TVT制御
- TVT-MP一般形の性能測定

**2026-09-14更新：** 買い手候補inlink、買い手prefix、具体的買い手候補集合は、実装前仕様まで確定した。Python実装と専用テストは未着手である。一般形順位再構成、一般形順位再構成の結果型、およびそれ以降の項目は引き続き未実装である。最新詳細は、本ファイルの「具体的買い手候補集合生成部品の実装前仕様」を参照する。

**2026-09-15更新：** 買い手候補inlinkの抽出、買い手prefix、具体的買い手候補集合は、新規本番モジュールと専用テストとして実装・検証済みである。上記3項目は、本メモ作成時点の未実装一覧に歴史的に残す。最新の実装完了事実は、本ファイルの「具体的買い手候補集合生成部品の実装完了記録」を参照する。一般形順位再構成以降は引き続き未実装である。

**2026-09-15追記：** 次は実装前仕様まで確定したが、Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP一般形順位再構成部品の実装前仕様」を参照する。

**2026-09-15更新（実装完了）：** 非参加Visitあり・なしを統一した一般形順位再構成、一般形順位再構成の結果型、`trade_scope`の一般形実装、買い手・売り手・非参加Visitの3分類、非参加Visitのbaseline局所順位枠固定、空き順位枠方式のPython実装、一般形`trade_rank`、`trade_order`は、新規本番モジュールと専用テストとして実装・検証済みである。上記8項目は、本メモ作成時点の未実装一覧に歴史的に残す。最新の実装完了事実は、本ファイルの「TVT-MP一般形順位再構成部品の実装完了記録」を参照する。候補別FIFO接続以降は引き続き未実装である。

- 非参加Visitあり・なしを統一した一般形順位再構成
- 一般形順位再構成の結果型
- `trade_scope`の一般形実装
- 買い手、売り手、非参加Visitの3分類
- 非参加Visitのbaseline局所順位枠固定
- 空き順位枠方式のPython実装
- 一般形`trade_rank`
- `trade_order`

候補別FIFO接続、局所仮想計算、経済性評価、成立候補選択、支払いと補償、各場合の最終確定列、確定順位ブロックへの上位接続、上位TVT制御は引き続き未実装である。空き順位枠方式の制度ロジック自体は本ファイル§3.3、§4、§17で確定済みである。今回確定したのは、その制度ロジックを既存公開型へ接続する実装前仕様である。

**2026-09-15追記（FIFO検査接続）：** 次は実装前仕様まで確定したが、Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP FIFO検査接続部品の実装前仕様」を参照する。

**2026-09-15更新（FIFO検査接続・実装完了）：** 候補別FIFO接続、`preserves_inlink_fifo()`の候補ごとの呼出し、FIFO違反候補のTrue/False結果保持、FIFO違反候補を結果から削除しない一対一対応、FIFO違反候補の正常な後続除外契約は、新規本番モジュールと専用テストとして実装・検証済みである。上記5項目は、本メモ作成時点の未実装一覧に歴史的に残す。最新の実装完了事実は、本ファイルの「TVT-MP FIFO検査接続部品の実装完了記録」を参照する。局所仮想計算以降は引き続き未実装である。

- 候補別FIFO接続
- `preserves_inlink_fifo()`の呼出し
- FIFO違反候補のTrue/False結果保持
- FIFO違反候補の正常な後続除外契約

局所仮想計算、経済性評価、成立候補選択、支払いと補償、各場合の最終確定列、確定順位ブロックへの上位接続、上位TVT制御は引き続き未実装である。FIFO検査の制度ロジック自体は本ファイル§20、§21で確定済みである。実装前仕様は、本ファイルの「TVT-MP FIFO検査接続部品の実装前仕様」に保存済みである。実装完了事実は、同ファイルの「TVT-MP FIFO検査接続部品の実装完了記録」を参照する。

**2026-09-18更新（候補別局所仮想計算・設計検討）：** FIFO検査接続までは実装・検証・push済みである（保存済み実装コミット`33e6101`）。候補別局所仮想計算は未実装である。今回は完全な実装前仕様を作らず、設計検討記録を追加した。通過試行順の基本方針は採用した。outlink終端の条件付き平均境界サービス方式は有力案である。ただし、baseline境界観測、inlink始端、新規流入、公開API、結果型等は未確定である。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の設計検討記録」を参照する。

**2026-09-19更新（下流境界観測の基本設計確定）：** FIFO検査接続までは実装・検証・push済みである（保存済み実装コミット`33e6101`）。保存済み最新の局所仮想計算設計検討コミットは`5dd4be9`（`Document the TVT-MP candidate local virtual calculation design study`）である。候補別局所仮想計算は未実装である。下流境界観測の基本設計を確定した。`DELTAN=1`をTVT初期研究範囲の制度上の前提とする。activeは終端`Node.transfer()`直前の途中通過Vehicle待機で判定する。実流出台数は、transfer前に保持した途中通過Vehicleがtransfer後に元のoutlinkを離れた数とする。目的地到着Vehicleは集計対象外である。Node固定分類ではなくVehicleごとの目的地判定を使う。下流境界専用observerと、`OrderControlBaselineForkResult`から参照できる独立した読取専用結果を使う方向である。公開API、結果型、例外契約、局所適用処理は未確定である。Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の設計検討記録」にある「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」を参照する。

**2026-09-19更新（下流境界観測部品・完全実装前仕様確定）：** 保存済み基本設計コミットは`c2c98c0`（`Document the TVT downstream boundary observation basic design`）である。下流境界観測部品の完全な実装前仕様を確定した。Python実装とテストは未着手である。observer正式名は`OrderControlBaselineDownstreamBoundaryObserver`、World属性名は`_order_control_baseline_downstream_boundary_observer`である。正式APIは`register_target_node_outlinks()`、`capture_before_transfer()`、`commit_after_transfer()`、`clear_pending()`、`export_result()`である。結果は重複を避けた3段frozen構造である。`OrderControlBaselineForkResult`へ必須フィールド`downstream_boundary_result`を追加する。空baselineは`None`であり、観測済みcount 0と区別する。対象Nodeは`target_node_names`順、各Nodeのoutlinkはネットワーク登録順である。同一outlinkの二重登録はbaseline開始前の`ValueError`である。transfer例外時はbaseline停止し、部分結果を返さない。`DELTAN=1`はFCFS、BATCH、TVTに共通するorder control設定時検査であり、処理名は`_validate_order_control_deltan`である。平均率はbaseline observerの責務外である。次は保存済み完全仕様に従うPython実装である。最新詳細は、本ファイルの「全World baseline下流境界観測部品の完全な実装前仕様」を参照する。

# 具体的買い手候補集合生成部品の実装前仕様

本節は、具体的買い手候補集合生成部品の実装前仕様の最新正本である。

- 制度ロジックは、本ファイル§7から§13、§28、§29.1、§29.2に従う。
- 今回確定するのは、既存公開型との接続、公開API、結果型、status、参加Mapping、例外契約、専用テスト契約である。
- Python実装とテストは未着手である。
- 実装・検証後は、別の実装完了記録を追加する。
- 旧メモは変更しない。

## 非技術的な説明

すでに、P−1条件と可変上限Nの適用後に最大N件まで選ばれたTVT候補Visitと、各inlink内でのsnapshot時点の前後順は取得できている。

次の部品では、権利保有車両と同じinlinkを買い手候補から外す。その他のinlinkでは、対象Nodeに近い先頭側から参加Visitが続く範囲を最大prefixとする。最初の非参加Visitに到達したら、そのVisitと後方のVisitを買い手候補prefixへ含めない。

各inlinkについて、空prefixから最大prefixまでのすべてのprefixを作る。各inlinkからprefixを一つずつ選ぶ全組合せを作り、すべて空の組合せだけを除外する。選ばれたVisitを、対象Nodeへ向かう全inlink横断の正式baseline相対順へ並べたものが、一つの具体的買い手候補集合である。

これは経済性評価前の候補であり、確定した買い手集合ではない。この段階では売り手、`trade_scope`、取引後順位を決めない。

## 責任分離

新しい独立した読取専用部品とする。既存部品へ統合しない。

新規本番ファイルの正式候補:

```text
uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py
```

新規専用テスト:

```text
tests_order_control_tvt_mp_concrete_buyer_candidate_set.py
```

変更しない既存部品:

- `order_control_tvt_candidate_visit_set.py`
- `order_control_tvt_inlink_candidate_physical_order.py`
- `order_control_tvt_trade_rank.py`
- その他の上流処理

理由:

- `candidate_visits`の選定は上流の責務である。
- inlink別snapshot物理順整理も実装済み上流部品の責務である。
- 今回の責務はprefixと具体的買い手候補集合の生成である。
- 一般形順位再構成は次の別部品とする。
- 上流処理を再実行しない。
- World、Vehicle、collector、順位台帳へ戻らない。
- 入力結果を変更しない。

## 公開関数

正式名称:

```text
build_tvt_mp_concrete_buyer_candidate_sets
```

署名候補:

```python
def build_tvt_mp_concrete_buyer_candidate_sets(
    inlink_candidate_physical_order_result:
        OrderControlTvtInlinkCandidatePhysicalOrderSetResult,
    *,
    participates_by_visit_key:
        Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtMpConcreteBuyerCandidateSetResult:
```

契約:

- 第一引数は位置引数として受け取る。
- `participates_by_visit_key`はkeyword-only必須引数である。
- 追加のWorld、Vehicle、collector、rank stateを受け取らない。
- 上流処理を再実行しない。
- 入力オブジェクトを変更しない。

## 既存入力への参照経路

第一入力は`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`である。

この入力から次へ到達する。

- `candidate_visit_set_result`
- `node_inlink_candidate_physical_order_results`

`candidate_visit_set_result`から次を読む。

- `node_candidate_set_results`
- 各対象Nodeの`build_status`
- `right_of_entry_visit_key`
- `candidate_visits`

各candidate Visitから次を読む。

- `visit_key`
- `inlink_name`
- baseline情報

各対象Nodeのinlink別結果から次を読む。

- `node_name`
- `build_status`
- `inlink_candidate_physical_orders`

各inlink結果から次を読む。

- `node_name`
- `inlink_name`
- `candidate_visit_keys_head_to_tail`

全体結果は、入力`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`と同じオブジェクトを参照保持する。

`candidate_visit_set_result`だけを重複して保存しない。候補Visitの完全情報を複写しない。永続的なbaseline順位dictを結果型へ保存しない。

## 結果型

すべて公開frozen dataclassとする。

### inlink別prefix結果

正式名称:

```text
OrderControlTvtMpInlinkBuyerPrefixResult
```

フィールド:

- `node_name: str`
- `inlink_name: str`
- `buyer_prefixes_empty_to_max: tuple[tuple[OrderControlTvtVisitKey, ...], ...]`

意味:

- 買い手候補となる一つのinlinkについて、空prefixから最大prefixまでの全prefixを保持する。
- 最初の要素は必ず空tupleである。
- その後は、物理先頭1件、先頭2件、先頭3件という順に長くなる。
- 最後の要素が最大prefixである。
- prefix内のVisitKey順は、同一inlink内のsnapshot物理順である。
- prefix列挙順は、候補の優先順位を意味しない。
- 権利保有inlinkは、この結果へ含めない。
- 物理先頭のcandidate Visitが非参加で、非空prefixを作れないinlinkも含めない。

`max_prefix`を別フィールドとして保存しない。

理由:

- `buyer_prefixes_empty_to_max`の最後の要素から最大prefixを取得できる。
- `max_prefix`と全prefixの二重管理を避ける。
- 両者の不一致を生じさせない。

### 一つの具体的買い手候補集合

正式名称:

```text
OrderControlTvtMpConcreteBuyerCandidateSet
```

フィールド:

- `buyers_sorted: tuple[OrderControlTvtVisitKey, ...]`

意味:

- 一つのprefix組合せから作られた、経済性評価前の具体的買い手候補集合である。
- 空でない。
- 全VisitKeyが参加Visitである。
- `candidate_visits`内の位置に従って、対象Nodeへ向かう全inlink横断の正式baseline相対順に並ぶ。
- 権利保有Visitを含まない。
- 権利保有inlink上のVisitを含まない。
- 確定した買い手集合ではない。

保存しないもの:

- 候補ID
- 選択元prefix組合せ
- 売り手
- 非参加Visit
- `trade_scope`
- `last_buyer_rank`
- `trade_rank`
- `trade_order`
- FIFO結果
- 局所仮想計算結果
- 経済性評価結果
- `surplus`
- 支払額
- 補償額

### Node別結果

正式名称:

```text
OrderControlTvtNodeMpConcreteBuyerCandidateSetResult
```

フィールド:

- `node_name: str`
- `build_status: OrderControlTvtCandidateVisitSetStatus`
- `buyer_candidate_inlink_prefix_results: tuple[OrderControlTvtMpInlinkBuyerPrefixResult, ...]`
- `concrete_buyer_candidate_sets: tuple[OrderControlTvtMpConcreteBuyerCandidateSet, ...]`

`excluded_right_of_entry_inlink_name`は追加しない。

理由:

- 権利保有Visitおよび`inlink_name`は上流結果から取得可能である。
- 同じ情報の重複保存を避ける。
- 権利保有inlinkは生成処理で買い手候補から除外するだけで十分である。

### 全体結果

正式名称:

```text
OrderControlTvtMpConcreteBuyerCandidateSetResult
```

フィールド:

- `inlink_candidate_physical_order_result: OrderControlTvtInlinkCandidatePhysicalOrderSetResult`
- `node_concrete_buyer_candidate_set_results: tuple[OrderControlTvtNodeMpConcreteBuyerCandidateSetResult, ...]`

入力`inlink_candidate_physical_order_result`と同じオブジェクトを参照保持する。

対象Node別結果は、上流の`node_inlink_candidate_physical_order_results`と同じ順序で保持する。

## status設計

新しいstatus Enumは追加しない。

既存の`OrderControlTvtCandidateVisitSetStatus`を対象Node別結果へ保持する。

`BASELINE_INFORMATION_COMPLETE`:

- 参加Mappingを検証する。
- 権利保有Visitの参加状態を確認する。
- prefixを生成する。
- 具体的買い手候補集合を生成する。

`BASELINE_INFORMATION_COMPLETE`以外の正式4 status:

- `NOT_BUILT_NO_RIGHT_OF_ENTRY`
- `NOT_BUILT_UNRESOLVED_ARRIVALS`
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`
- `UNRESOLVED_CANDIDATE_PASSAGES`

これらでは:

- 参加Mappingを検証しない。
- prefixを生成しない。
- 具体的買い手候補集合を生成しない。
- `buyer_candidate_inlink_prefix_results=()`
- `concrete_buyer_candidate_sets=()`

特に`UNRESOLVED_CANDIDATE_PASSAGES`では:

- `candidate_visits`は確定済みである。
- inlink別snapshot物理順も整理済みである。
- ただし、部分的TVTを防ぐためprefix生成へ進まない。

想定外status:

- `RuntimeError`とする。
- 正常な空結果として扱わない。
- 対象Node名と実際のstatusをエラーメッセージへ含める。
- 後続の対象Nodeを処理せず、部分的な全体結果を返さない。

次の三状態は、既存statusとtupleの内容で区別する。

1. 上流情報により生成対象外
   - `build_status`が`BASELINE_INFORMATION_COMPLETE`以外
   - 両結果tupleが空
2. 情報は完全だが買い手候補inlinkが0本
   - `build_status`が`BASELINE_INFORMATION_COMPLETE`
   - 両結果tupleが空
3. 具体的買い手候補集合を生成
   - `build_status`が`BASELINE_INFORMATION_COMPLETE`
   - prefix結果および具体候補結果が非空

## 参加Mapping

必須入力:

```text
participates_by_visit_key:
Mapping[OrderControlTvtVisitKey, bool]
```

契約:

- `BASELINE_INFORMATION_COMPLETE`の対象Nodeだけ検証する。
- その対象Nodeの`candidate_visits`全件について参加情報を確認する。
- 必要なVisitKeyが欠けていれば`ValueError`とする。
- 値が厳密なPythonの`bool`でなければ`ValueError`とする。
- `bool`の代わりに`1`、`0`、文字列、`numpy.bool_`を受け入れない。
- Mapping内の余分なVisitKeyは許容する。
- 余分なVisitKeyは使用しない。
- Mapping全体の完全一致は要求しない。
- Mappingを変更しない。
- 参加状態を、対象Nodeへ向かう全inlink横断の正式baseline順の決定へ使用しない。

権利保有Visit:

- `BASELINE_INFORMATION_COMPLETE`の対象Nodeでは参加Visitでなければならない。
- `participates_by_visit_key[right_of_entry_visit_key]`が`False`なら`RuntimeError`とする。
- これはTVT形成直前の重大不整合確認として行う。
- 権利保有Visitを買い手候補へ含めない。

## 権利保有inlink

`BASELINE_INFORMATION_COMPLETE`の対象Nodeについて:

1. 対象Node別candidate結果から`right_of_entry_visit_key`を取得する。
2. `None`なら`RuntimeError`とする。
3. `candidate_visits`からVisitKeyと`inlink_name`の一時dictを作る。
4. 権利保有Visitを一時dictから検索する。
5. 見つからなければ`RuntimeError`とする。
6. その`inlink_name`を権利保有inlinkとする。
7. 権利保有inlinkはprefix生成および直積の対象から除外する。
8. 上流の`candidate_visits`とinlink別物理順結果は変更しない。
9. 権利保有inlink上のVisitを上流結果から削除しない。
10. 後続の`trade_scope`と順位再構成では、権利保有inlink上のVisitも必要に応じて扱う。

## prefix生成

`BASELINE_INFORMATION_COMPLETE`の各対象Nodeについて:

1. `candidate_visits`全件の参加Mappingを検証する。
2. candidate VisitKeyから`inlink_name`への一時dictを作る。
3. candidate VisitKeyから正式baseline位置への一時dictを作る。
4. 権利保有Visitの参加状態を確認する。
5. 権利保有inlinkを特定する。
6. `inlink_candidate_physical_orders`を既存tuple順に走査する。
7. 権利保有inlinkはprefix生成対象から除外する。
8. その他のinlinkでは`candidate_visit_keys_head_to_tail`を先頭から走査する。
9. 参加Visitなら最大prefix用listへ追加する。
10. 最初の非参加Visitに到達したら停止する。
11. 最初の非参加Visit自身を最大prefixへ含めない。
12. 最初の非参加Visitより後方のVisitも含めない。
13. 最大prefixが空なら、そのinlinkを直積対象から除外する。
14. 最大prefixが非空なら、空prefixから最大prefixまでの全prefixを作る。
15. inlink別prefix結果を作る。

各inlinkの`buyer_prefixes_empty_to_max`は次の順序とする。

- 空tuple
- 物理先頭1件
- 物理先頭2件
- 物理先頭3件
- 以下同様
- 最大prefix

例えば最大prefixがA、B、Cなら:

- `()`
- `(A,)`
- `(A, B)`
- `(A, B, C)`

この順序は候補の優先順位を意味しない。

## 具体的買い手候補集合生成

1. 買い手候補inlinkが0本なら、具体的買い手候補集合は空tupleとする。
2. 各inlinkの`buyer_prefixes_empty_to_max`を直積の軸とする。
3. 標準ライブラリ`itertools.product`を使用してよい。
4. 全inlinkで空prefixを選んだ組合せだけを除外する。
5. 一部のinlinkが空で、別のinlinkが非空の組合せは残す。
6. 各prefix組合せのVisitKeyを一時listへ統合する。
7. `candidate_visits`内の位置から作った一時dictで、対象Nodeへ向かう全inlink横断の正式baseline相対順へ並べる。
8. 空でないVisitKey tupleを`buyers_sorted`として保存する。
9. `OrderControlTvtMpConcreteBuyerCandidateSet`を作る。
10. すべての具体的買い手候補集合をtupleで保持する。

直積軸となるinlinkの順序:

- 上流の`inlink_candidate_physical_orders`における出現順。
- 権利保有inlinkと最大prefixが空のinlinkを除いた順。

prefix組合せと具体候補の列挙順:

- 決定論的な列挙順として維持する。
- 候補の優先順位に使用しない。
- 経済性評価の同値判定に使用しない。
- 将来のランダム選択の代用にしない。

## 重複候補

本ファイル§12.5に従う。

- 一つのVisitKeyは一つのsnapshot inlinkにだけ属する。
- 一つのinlinkのprefixは選択した長さにより一意に決まる。
- 異なるprefix組合せから同じ具体的買い手候補集合は生成されない。
- 本番処理で重複除去しない。
- 本番処理で候補ごとの重複検出用seen setも作らない。
- 専用テストで、生成された具体的買い手候補集合に重複がないことを確認する。
- 具体候補内のVisitKey重複も、正常な生成経路では構造上発生しない。
- 候補ごとの重複検査を本番へ追加しない。
- 上流のVisitKey所属とinlink別物理順の既存保証を利用する。

## 必要最小限の検査

本番に残す外部入力検査:

`ValueError`:

- `BASELINE_INFORMATION_COMPLETE`の対象Nodeで、必要なcandidate VisitKeyが`participates_by_visit_key`にない。
- 参加状態の値が厳密なPythonの`bool`でない。

本番に残す既存結果間の重大不整合検査:

`RuntimeError`:

- 対象Node別candidate結果とinlink別物理順結果の件数不一致。
- 対応する対象Node別結果の`node_name`不一致。
- 対応する対象Node別結果の`build_status`不一致。
- 想定外`build_status`。
- `BASELINE_INFORMATION_COMPLETE`なのに`right_of_entry_visit_key`が`None`。
- 権利保有Visitが`candidate_visits`に存在しない。
- 権利保有Visitが非参加。
- `candidate_visits`のVisitKey集合と、inlink別candidate物理順のVisitKey集合が一致しない場合。

上記の集合一致については、上流部品がすでに保証した内容の全面的な再検証にはしない。ただし、異なる上流結果オブジェクトを誤って組み合わせた場合に、誤った買い手候補を生成する重大不整合を防ぐため、対象Node単位の軽量な対応確認は行う第一候補とする。

本番で再検証しない:

- P−1条件。
- 可変上限N。
- `candidate_visits`の正式baseline sort規則。
- baseline passage値そのもの。
- snapshot物理順の内部重複。
- snapshot entriesと物理順の集合一致。
- 単車線条件。
- candidate Visitの対象Node・inlink所属について、既存上流部品が保証済みの詳細。
- 具体的買い手候補集合の重複。
- 具体候補内のVisitKey重複。

重大不整合時:

- 後続の対象Nodeを処理しない。
- 部分的な全体結果を返さない。
- 新しい独自例外型を作らない。

## 可読性

実装では、正しさを最優先とし、次に初学者が後から追いやすい可読性を優先する。

複数の実装方法がある場合は、短さ、巧妙さ、高度なPython技法より、明示的な処理を選ぶ。

責務を少なくとも次へ分ける方針とする。

- statusの分類
- 対象Node別結果の対応確認
- 参加Mappingの検証
- candidate VisitKeyから`inlink_name`への一時dict作成
- candidate VisitKeyから正式baseline位置への一時dict作成
- 権利保有inlinkの特定
- 一つのinlinkの最大prefix作成
- 空prefixから最大prefixまでの全prefix作成
- 対象Nodeの買い手候補inlink別prefix結果作成
- prefix直積
- prefix組合せの統合
- 対象Nodeへ向かう全inlink横断の正式baseline相対順への並べ替え
- 対象Node別結果作成
- 全体結果作成

避ける:

- 長い内包表記。
- 複雑な多重ジェネレーター式。
- 多段階処理を一つの式へ詰め込むこと。
- 高度なPython技法による短縮。
- 不要な抽象化。
- 実測前の性能最適化。

`itertools.product`は使用してよい。ただし、prefix組合せ、統合済みVisitKey、並べ替え後VisitKeyを、意味の分かる中間変数へ分ける。

## 専用テスト契約

新規専用テスト:

```text
tests_order_control_tvt_mp_concrete_buyer_candidate_set.py
```

期待値は、実装と同じ処理で自動生成せず、テスト本文へ明示する。

正常系:

- 単一対象Node・単一買い手候補inlink。
- 単一対象Node・複数買い手候補inlink。
- 複数対象Node。
- 権利保有inlinkをprefix対象から除外する。
- 権利保有Visitを具体的買い手候補集合へ含めない。
- 全参加ならinlink別candidate Visit列の末尾まで最大prefixとなる。
- 途中の最前方非参加Visitで最大prefixを打ち切る。
- 最前方非参加Visit自身を含めない。
- 最前方非参加Visitより後方を含めない。
- 物理先頭が非参加なら、そのinlinkを直積対象から除外する。
- 各買い手候補inlinkのprefix列の先頭が空tuple。
- 空prefixから最大prefixまで全prefixがある。
- 全空組合せだけを除外する。
- 一部inlinkだけ空の組合せを残す。
- 統合後は`candidate_visits`内の位置に従って、対象Nodeへ向かう全inlink横断の正式baseline相対順へ並ぶ。
- inlink内snapshot物理順と、対象Nodeへ向かう全inlink横断の正式baseline順の用途を混同しない。
- 非参加Visitが0件でも同じ一般形処理で生成する。
- 買い手候補inlinkが0本なら具体的候補0件。
- 権利保有Visitだけのcandidate集合なら具体的候補0件。
- 具体的買い手候補集合に重複がない。
- 候補数が`∏(M_i + 1) - 1`と一致する小規模例。

status:

- `BASELINE_INFORMATION_COMPLETE`で生成する。
- `UNRESOLVED_CANDIDATE_PASSAGES`では生成しない。
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`では生成しない。
- `NOT_BUILT_NO_RIGHT_OF_ENTRY`では生成しない。
- `NOT_BUILT_UNRESOLVED_ARRIVALS`では生成しない。
- 想定外statusは`RuntimeError`。
- 生成対象外の対象Nodeでは参加Mappingを検証しない。

参加Mapping:

- 必要なVisitKey欠落を`ValueError`。
- 値`1`を拒否。
- 値`0`を拒否。
- 文字列`"True"`を拒否。
- `numpy.bool_`を拒否。
- 余分なVisitKeyを許容する。
- 余分なVisitKeyが結果へ影響しない。
- 権利保有Visitが`False`なら`RuntimeError`。
- 非参加Visitが具体的買い手候補集合へ入らない。

結果型:

- 4つの公開結果型がfrozen dataclassである。
- すべての列がtupleである。
- `buyer_prefixes_empty_to_max`の先頭要素が空tupleである。
- 最後の要素が最大prefixである。
- `max_prefix`の重複フィールドがない。
- 全体結果が入力上流結果と同じオブジェクトを参照保持する。
- `buyers_sorted`は空でない。
- 結果型に候補IDがない。
- 結果型に売り手、非参加分類、`trade_scope`、`trade_rank`、`trade_order`、FIFO、経済評価フィールドがない。
- `excluded_right_of_entry_inlink_name`の重複フィールドがない。
- 永続baseline順位dictがない。
- 更新API、rollback API、export APIを追加していない。

重大不整合:

- 対象Node別結果件数不一致。
- `node_name`不一致。
- `build_status`不一致。
- `BASELINE_INFORMATION_COMPLETE`なのに`right_of_entry_visit_key`が`None`。
- 権利保有Visitが`candidate_visits`に存在しない。
- candidate Visit集合とinlink別candidate物理順集合の不一致。
- 後続の対象Nodeで重大不整合が起きた場合に部分結果を返さない。
- 重大不整合後に後続の対象Nodeを処理しない。

読取専用:

- 入力上流結果を変更しない。
- `candidate_visits`を変更しない。
- inlink別candidate物理順を変更しない。
- `participates_by_visit_key`を変更しない。
- World、Vehicle、collector、順位台帳へ戻らない。
- 上流公開処理を呼び直さない。

## 今回実装しない範囲

- `trade_scope`。
- 最後尾買い手候補の順位計算。
- 買い手、売り手、非参加Visitの3分類。
- 非参加Visitのbaseline局所順位枠固定。
- 空き順位枠方式。
- 一般形`trade_rank`。
- `trade_order`。
- FIFO検査の実行。
- 局所仮想計算。
- 経済性評価。
- `surplus`比較。
- 同値候補のRNG選択。
- 支払い。
- 補償。
- TVT成立時の最終確定。
- TVT不成立時の最終確定。
- 情報未解決時の最終確定。
- 確定順位ブロックへの接続。
- 上位TVT制御。
- TVT-SB。
- TVT-MH。
- TVT-SP。
- 性能最適化。
- 研究対象外Vehicle対応の拡張。

## 実装後の次の作業

具体的買い手候補集合生成部品を実装・検証した後は、次へ進む。

- 非参加Visitあり・なしを統一する一般形順位再構成部品の実装前仕様。
- `candidate_visits`と具体的買い手候補集合から`trade_scope`を構築する。
- `trade_scope`内を買い手、売り手、非参加Visitへ分類する。
- 非参加Visitのbaseline局所順位枠を固定する。
- 空き順位の先頭側へ買い手を配置する。
- 残る空き順位へ売り手を配置する。
- `trade_rank`と`trade_order`を構築する。
- 非参加Visit0件で既存の非参加Visitなし関数と結果が一致することを確認する。

局所仮想計算と経済性評価には、まだ進まない。

# 具体的買い手候補集合生成部品の実装完了記録

**実装完了日：2026-09-15**

本節は、上記「具体的買い手候補集合生成部品の実装前仕様」に対応する実装完了記録である。制度ロジックの正本は、引き続き本ファイル§7から§13、§28、§29.1、§29.2および当該実装前仕様である。実装前仕様は、実装時に用いた正本として削除・置換せず維持する。

実装前仕様の保存済みコミットは`8d57cd9`（メモへの記録のみ。実装前仕様のdocumentコミットとして利用者が保存・push済み）である。その保存済み仕様に従い、新規本番と専用テストを実装した。本実装完了記録時点では、新規コード・新規テスト・本節の追記は、まだ`git add`、`git commit`、`git push`していない。

Copilotと利用者が、実コード、専用テスト、回帰テスト、テスト件数、Git状態をTerminalで確認済みである。Cursor報告だけでは実装完了を確定しない。

## 新規ファイルと公開API

新規本番:

- `uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py`

新規専用テスト:

- `tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`

公開関数:

- `build_tvt_mp_concrete_buyer_candidate_sets`

公開frozen dataclass（4つ）:

1. `OrderControlTvtMpInlinkBuyerPrefixResult`
2. `OrderControlTvtMpConcreteBuyerCandidateSet`
3. `OrderControlTvtNodeMpConcreteBuyerCandidateSetResult`
4. `OrderControlTvtMpConcreteBuyerCandidateSetResult`

## 既存入力型との接続

第一入力は`OrderControlTvtInlinkCandidatePhysicalOrderSetResult`である。keyword-only必須入力は`participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool]`である。

`OrderControlTvtMpConcreteBuyerCandidateSetResult`は、渡された`inlink_candidate_physical_order_result`と**同一オブジェクト参照**を保持する。候補Visit完全情報の複写、`candidate_visit_set_result`の重複フィールドは追加していない。

## status別動作

`BASELINE_INFORMATION_COMPLETE`の対象Nodeだけで、prefixと具体的買い手候補集合を生成する。

次の正式4 statusでは、参加Mappingを検証せず、prefixも具体的候補も生成しない。

- `NOT_BUILT_NO_RIGHT_OF_ENTRY`
- `NOT_BUILT_UNRESOLVED_ARRIVALS`
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`
- `UNRESOLVED_CANDIDATE_PASSAGES`

非生成4 statusでは、`buyer_candidate_inlink_prefix_results=()`、`concrete_buyer_candidate_sets=()`とする。

特に`UNRESOLVED_CANDIDATE_PASSAGES`では、`candidate_visits`とinlink別snapshot物理順が保持されていても、部分的TVTを防ぐため、参加Mapping検証、prefix生成、具体的候補生成へ進まない。

想定外`build_status`は`RuntimeError`とし、正常な空結果として隠さない。重大不整合時は後続の対象Nodeを処理せず、部分的な全体結果を返さない。

## 実装済み処理の要約

実装済みの主な処理は次である。

- candidate Node結果とinlink別物理順Node結果の件数・`node_name`・`build_status`の対応確認。
- `BASELINE_INFORMATION_COMPLETE`の対象Nodeについて、`candidate_visits`全件の参加Mapping検証（欠落・非strict `bool`は`ValueError`。`1`、`0`、文字列、`numpy.bool_`は受け入れない。余分キーは許容し使用しない）。
- candidate VisitKeyから`inlink_name`および`candidate_visits`内正式baseline位置への一時dict構築。
- `candidate_visits`のVisitKey集合とinlink別candidate物理順のVisitKey集合の、対象Node単位の一致確認（不一致は`RuntimeError`）。
- 権利保有Visitの特定、非参加・欠落・`right_of_entry_visit_key is None`の重大不整合検出（`RuntimeError`）。
- 権利保有inlinkをprefix結果とprefix直積から除外（上流の権利保有inlink上Visitは削除しない）。
- 上流`inlink_candidate_physical_orders`の出現順で、snapshot物理先頭からの参加連続範囲を最大prefixとし、最初の非参加Visit自身と後方を含めない。
- 最大prefixが空のinlinkを公開prefix結果と直積軸から除外。
- `buyer_prefixes_empty_to_max`を空tupleから最大prefixまで生成・保存。
- `itertools.product`によるprefix直積、全空組合せのみ除外、一部inlinkだけ空の組合せは維持。
- 選択prefixのVisitKey統合後、`candidate_visits`内の位置に従い、対象Nodeへ向かう全inlink横断の正式baseline相対順へ並べ替え（到着timestep、tiebreaker、Vehicle IDによる再計算は行わない）。
- 買い手候補inlinkが0本のとき、具体的買い手候補集合は正常な空tuple。
- 具体的買い手候補集合の重複除去および重複検出用seen setは行わない。
- 入力結果、`candidate_visits`、inlink別物理順、参加Mappingを変更しない。上流処理を再実行しない。World、Vehicle、collector、順位台帳へ戻らない。

## 結果型の実装結果

`OrderControlTvtMpInlinkBuyerPrefixResult`: `node_name`, `inlink_name`, `buyer_prefixes_empty_to_max`

`OrderControlTvtMpConcreteBuyerCandidateSet`: `buyers_sorted`

`OrderControlTvtNodeMpConcreteBuyerCandidateSetResult`: `node_name`, `build_status`, `buyer_candidate_inlink_prefix_results`, `concrete_buyer_candidate_sets`

`OrderControlTvtMpConcreteBuyerCandidateSetResult`: `inlink_candidate_physical_order_result`, `node_concrete_buyer_candidate_set_results`

次は結果型に保存していない。候補ID、選択元prefix組合せ、`max_prefix`の重複フィールド、`excluded_right_of_entry_inlink_name`、売り手、非参加Visit分類、`trade_scope`、`last_buyer_rank`、`trade_rank`、`trade_order`、FIFO結果、局所仮想計算結果、経済性評価結果、`surplus`、支払額、補償額、永続baseline順位dict、`candidate_visit_set_result`の重複参照。

## 可読性

本番実装は、時間価値取引の根幹部分を初学者が後から追いやすくするため、短さや高度なPython技法より可読性を優先している。参加Mapping検証、一時dict構築、VisitKey集合対応確認、権利保有inlink特定、最大prefix生成、全prefix生成、prefix直積、VisitKey統合（明示的ループ）、正式baseline相対順への並べ替え、結果構築を分離している。複雑な多重ジェネレーター式や巧妙なone-linerへ処理を詰め込んでいない。意味の分かる中間変数を使用している。実測前の性能最適化は行っていない。可読性のために、保存済みの制度仕様、公開API、status契約、例外契約、未実装境界は変更していない。

## 本番の必要最小限の検査

`ValueError`:

- `BASELINE_INFORMATION_COMPLETE`の対象Nodeで、必要なcandidate VisitKeyが`participates_by_visit_key`にない。
- 参加状態が厳密なPythonの`bool`でない。

`RuntimeError`:

- candidate Node結果とinlink別物理順Node結果の件数不一致。
- 対応するNode別結果の`node_name`不一致。
- 対応するNode別結果の`build_status`不一致。
- 想定外`build_status`。
- `BASELINE_INFORMATION_COMPLETE`なのに`right_of_entry_visit_key`が`None`。
- 権利保有Visitが`candidate_visits`に存在しない。
- 権利保有Visitが非参加。
- `candidate_visits`のVisitKey集合とinlink別candidate物理順のVisitKey集合が一致しない。

新しい独自例外型は追加していない。

## 本番で繰り返していない上流保証済み検査

P−1条件、可変上限N、`candidate_visits`の正式baseline sort規則、baseline passage値、candidate Visitの一般的なフィールド型、VisitKeyの一般的な型検証、`candidate_visits`内VisitKey重複、snapshot物理順内部の重複、snapshot entriesと物理順の集合一致、単車線条件、candidate Visitの詳細なNode・inlink所属、具体的買い手候補集合の重複、具体候補内VisitKey重複、FIFOは、本番で再検証していない。異なる上流結果の誤結合により誤った具体的候補を生成する重大不整合だけを、対象Node単位で軽量に確認している。

## 確認済みテスト結果

新規2ファイルの`py_compile`は成功した。

| 区分 | 結果 |
|------|------|
| 新規専用テスト直接実行 | 63 tests passed |
| 新規専用テスト pytest | 63 passed |
| pytest収集 | 63 collected |
| 定義済み`test_`関数 | 63件 |
| `TESTS`登録 | 63件（重複なし、登録漏れなし、未知参照なし） |
| 直接実行件数とpytest収集 | 一致 |

関係する既存回帰テスト5ファイルは200 passedである。

- `tests_order_control_tvt_candidate_visit_set.py`
- `tests_order_control_tvt_inlink_candidate_physical_order.py`
- `tests_order_control_tvt_leading_nonparticipating_confirmation.py`
- `tests_order_control_tvt_right_of_entry_selection.py`
- `tests_order_control_tvt_trade_rank.py`

新規専用テスト63件と既存回帰200件を合わせ、263件成功を確認した。

## 今回実装しなかった境界

`trade_scope`、最後尾買い手候補の順位計算、買い手・売り手・非参加Visitの3分類、非参加Visitのbaseline局所順位枠固定、空き順位枠方式のPython実装、一般形`trade_rank`、`trade_order`、FIFO検査の実行、局所仮想計算、経済性評価、`surplus`比較、RNG、支払い、補償、TVT成立・不成立・情報未解決時の最終確定、確定順位ブロックへの接続、上位TVT制御、TVT-SB、TVT-MH、TVT-SP、性能最適化は、今回も実装していない。

## 次の作業開始点（本部品完了後）

次の直接作業は、一般形順位再構成部品を直ちにコーディングすることではない。

1. 非参加Visitあり・なしを統一する一般形順位再構成部品について、既存の非参加Visitなし順位計算部品と`preserves_inlink_fifo()`の契約を再確認する。
2. 継続版メモで確定済みの空き順位枠方式を基礎に、一般形順位再構成部品の公開API、結果型、入力、責任分離、必要最小限の検査、専用テスト契約を**実装前仕様**として確定する。

一般形順位再構成の制度ロジックを新しく考え直す必要はない。空き順位枠方式は確定済みである。次に必要なのは、その確定済み制度ロジックを既存公開型へ接続する実装前仕様である。局所仮想計算と経済性評価には、まだ進まない。

# TVT-MP一般形順位再構成部品の実装前仕様

本節は、TVT-MP一般形順位再構成部品のPython実装に使用する**唯一の最新実装前仕様**である。

- 制度ロジックは、本ファイル§3.3、§4、§7、§10.1、§14から§21、§28（該当段階）、§29.3から§29.5に従う。空き順位枠方式は確定済みである。本節で制度ロジックを新しく考え直さない。
- 今回確定するのは、実装・検証済みの具体的買い手候補集合生成部品および既存の非参加Visitなし順位計算部品へ接続する公開API、結果型、入力経路、処理順、validation、例外、内部整合確認、専用テスト契約、未実装境界である。
- Python実装と専用テストは未着手である。実装済み、テスト済み、コミット済み、push済みとは記載しない。
- 実装・検証後は、別の実装完了記録を追加する。
- 旧メモは変更しない。旧メモに一般形が未確定だった当時の記述があっても、それは歴史的記録である。
- 上流の具体的買い手候補集合生成部品の保存済み実装コミットは`2764f0c`である。このhashを、本部品の実装コミットとして扱わない。

## 非技術的な説明

具体的買い手候補集合生成部品が作った一つ一つの買い手候補について、今回並べ直す範囲を決め、非参加Visitの席を元の位置に固定し、残りの席の前方へ買い手、その後方へ売り手を配置して、取引後の順位結果票を作る。

非参加Visitが0件の場合も、固定する席が0件になるだけで、同じ一般形を使用する。

この部品は順位結果を作るが、FIFO検査そのもの、局所仮想計算、経済性評価、最終候補選択は行わない。

## 責任分離と新規ファイル

新しい独立した読取専用部品とする。既存の非参加Visitなし専用モジュールへ一般形を追加しない。

新規本番モジュールの正式名称:

```text
uxsim/order_control_tvt_mp_general_trade_rank.py
```

新規専用テストの正式名称:

```text
tests_order_control_tvt_mp_general_trade_rank.py
```

変更しない既存部品:

- `uxsim/order_control_tvt_trade_rank.py`
- `tests_order_control_tvt_trade_rank.py`
- `uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py`
- `tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`
- その他の上流処理

理由:

- 既存部品は非参加Visitなし専用の実装済み部品である。
- 既存の内部確認には非参加Visitなし専用の売り手後退式が含まれる。
- 一般形の順位構築の正本は空き順位枠方式である。
- 一般形と既存専用部品の責任を混在させない。
- 一般形完成後に既存関数を残すか、互換入口にするか、将来廃止するかは別途判断する。
- 今回は既存部品を変更しない。

## 公開関数

正式名称:

```text
build_tvt_mp_general_trade_ranks
```

署名:

```python
def build_tvt_mp_general_trade_ranks(
    concrete_buyer_candidate_set_result:
        OrderControlTvtMpConcreteBuyerCandidateSetResult,
    *,
    participates_by_visit_key:
        Mapping[OrderControlTvtVisitKey, bool],
) -> OrderControlTvtMpGeneralTradeRankSetResult:
```

契約:

- 第一引数は位置引数として受け取る。
- `participates_by_visit_key`はkeyword-only必須引数とする。
- World、Vehicle、collector、Node、Link、順位台帳を受け取らない。
- `candidate_visit_set_result`を重複入力として受け取らない。
- inlink別物理順結果を重複入力として受け取らない。
- 上流処理を再実行しない。
- 第一入力から必要な上流結果へ参照で到達する。
- 入力オブジェクトを変更しない。
- 参加Mappingを変更しない。

## 上流入力との接続

第一入力は`OrderControlTvtMpConcreteBuyerCandidateSetResult`である。

第一入力から次を参照する。

- `inlink_candidate_physical_order_result`
- `node_concrete_buyer_candidate_set_results`

`inlink_candidate_physical_order_result`から次へ到達する。

- `candidate_visit_set_result`
- `node_inlink_candidate_physical_order_results`

`candidate_visit_set_result`から次を参照する。

- `node_candidate_set_results`

各対象Nodeのcandidate結果から次を参照する。

- `node_name`
- `build_status`
- `right_of_entry_visit_key`
- `candidate_visits`

各candidate Visitから次を参照する。

- `visit_key`
- `inlink_name`

各対象Nodeの具体的買い手候補集合生成結果から次を参照する。

- `node_name`
- `build_status`
- `concrete_buyer_candidate_sets`

各具体的買い手候補集合から次を参照する。

- `buyers_sorted`

`candidate_visits`は、対象Nodeへ向かう全inlink横断の正式baseline順に並んでいる。

一般形順位再構成部品で、`baseline_arrival_timestep`、`arrival_tiebreaker`、`vehicle_id`を使った正式baseline順の再計算を行わない。`candidate_visits`内の位置だけを正式baseline順位の正本として使用する。

## 処理単位

処理は次の二段構造とする。

1. 対象Node別に処理する。
2. 各対象Nodeの具体的買い手候補集合を一つずつ処理する。

一つの`OrderControlTvtMpConcreteBuyerCandidateSet`につき、一つの一般形順位結果を作る。

各対象Nodeの結果順は、第一入力の`node_concrete_buyer_candidate_set_results`の順序を維持する。

各具体的候補の順位結果は、上流の`concrete_buyer_candidate_sets`のtuple順を維持する。

候補IDは追加しない。

列挙順を次に使用しない。

- 候補の優先順位
- FIFO違反時の代替順位
- 経済性評価の比較規則
- `surplus`同値時の優先順位
- 将来のRNGの代用

## 公開結果型

次の3つを公開結果型とする。

1. `OrderControlTvtMpGeneralTradeRankResult`
2. `OrderControlTvtNodeMpGeneralTradeRankResult`
3. `OrderControlTvtMpGeneralTradeRankSetResult`

### 一つの具体的候補に対する順位結果

正式名称:

```text
OrderControlTvtMpGeneralTradeRankResult
```

これは一般形固有の順位結果票である。既存の`OrderControlTvtNoNonparticipantTradeRankResult`を再利用しない。読取専用クラスとする。Node別結果および全体結果のようなfrozen dataclassではない。既存の非参加Visitなし順位結果型と同じく、キーワード専用コンストラクター、privateな順位辞書、公開propertyと読取メソッドを持つ。

次を読取専用で保持する。

- `concrete_buyer_candidate_set`
- `buyers_sorted`
- `sellers_sorted`
- `nonparticipating_visits_sorted`
- `last_buyer_rank`
- `trade_scope`
- `trade_order`
- privateな`_trade_rank_by_visit_key`

#### フィールドの型と意味

`concrete_buyer_candidate_set`: `OrderControlTvtMpConcreteBuyerCandidateSet`

- 上流の具体的買い手候補オブジェクトを同一参照で保持する。
- 複製しない。
- どの上流候補から作られた順位結果かを示す。

`buyers_sorted`: `tuple[OrderControlTvtVisitKey, ...]`

- 上流の`concrete_buyer_candidate_set.buyers_sorted`と同じ買い手列。
- 空でない。
- 対象Nodeへ向かう全inlink横断の正式baseline相対順。
- 参加Visitだけで構成される。

`sellers_sorted`: `tuple[OrderControlTvtVisitKey, ...]`

- `trade_scope`内の参加Visitのうち、買い手に含まれないVisit。
- 空tupleを認める。
- 正式baseline相対順を維持する。
- 権利保有Visitは参加Visitであり、買い手にはならないため、`trade_scope`に含まれる場合は売り手となる。

`nonparticipating_visits_sorted`: `tuple[OrderControlTvtVisitKey, ...]`

- `trade_scope`内で`participates_by_visit_key`が`False`のVisit。
- 空tupleを認める。
- 正式baseline相対順を維持する。
- 買い手にも売り手にも含めない。

`last_buyer_rank`: `int`

- 最後尾買い手候補の正式baseline局所順位。
- 1以上。
- `candidate_visits`内の1始まり順位。
- `trade_scope`の件数と一致する。

`trade_scope`: `tuple[OrderControlTvtVisitKey, ...]`

- `candidate_visits`の先頭から最後尾買い手候補まで。
- 空でない。
- 末尾は必ず最後尾買い手候補。
- 後続FIFO検査の取引前材料として使用できる。

`trade_order`: `tuple[OrderControlTvtVisitKey, ...]`

- `candidate_visits`全件を取引後順位順に並べた列。
- `trade_rank`から派生させる。
- `trade_scope`外Visitも含む。
- `trade_order`の先頭`last_buyer_rank`件が、FIFO検査の取引後材料となる。

privateな順位辞書`_trade_rank_by_visit_key`: `dict[OrderControlTvtVisitKey, int]`

- `candidate_visits`全件のVisitKeyから取引後順位への対応。
- 順位の正本。
- 結果構築時に防御コピーする。
- 内部dictを直接公開しない。

#### 公開読取property

- `concrete_buyer_candidate_set`
- `buyers_sorted`
- `sellers_sorted`
- `nonparticipating_visits_sorted`
- `last_buyer_rank`
- `trade_scope`
- `trade_order`

#### 公開読取メソッド

```python
def assigned_rank(
    self,
    visit_key: OrderControlTvtVisitKey,
) -> int:
    ...

def trade_rank_items(
    self,
) -> tuple[tuple[OrderControlTvtVisitKey, int], ...]:
    ...
```

`assigned_rank`の契約:

- 不正なVisitKeyは`ValueError`。
- 結果に存在しないVisitKeyは`ValueError`。
- `None`を返さない。
- 対象VisitKeyについて、1以上のPython `int`を返す。

`trade_rank_items`の契約:

- `trade_order`の順序、すなわち取引後順位昇順で返す。
- 変更不能なtupleとして返す。
- 内部dictを返さない。

持たない公開API:

- property setter
- `update`
- `rollback`
- `export`
- `export_state`
- `to_dict`
- 順位変更用の公開メソッド

コンストラクターは既存順位結果型と同じく、キーワード専用とする。

順位計算と内部整合確認の完了後に一度だけ構築する。

通常の上位利用では、結果クラスを直接構築せず、公開順位計算関数から受け取る。

専用テストでは、結果型固有の入力契約、防御コピー、読取APIの確認のため、直接構築を認める。

コンストラクターでは最低限の型・形式確認だけを行い、公開順位計算関数内で完了済みの一般形内部整合確認を全面的に繰り返さない。

### Node別結果

正式名称:

```text
OrderControlTvtNodeMpGeneralTradeRankResult
```

公開frozen dataclassとする。

フィールド:

- `node_name: str`
- `build_status: OrderControlTvtCandidateVisitSetStatus`
- `candidate_trade_rank_results: tuple[OrderControlTvtMpGeneralTradeRankResult, ...]`

意味:

- 一つの対象Nodeに対応する一般形順位再構成結果。
- `candidate_trade_rank_results`は、上流の`concrete_buyer_candidate_sets`と同じ順序。
- `BASELINE_INFORMATION_COMPLETE`でも具体的買い手候補が0件なら空tuple。
- 正式な非生成statusでも空tuple。

### 全体結果

正式名称:

```text
OrderControlTvtMpGeneralTradeRankSetResult
```

公開frozen dataclassとする。

フィールド:

- `concrete_buyer_candidate_set_result: OrderControlTvtMpConcreteBuyerCandidateSetResult`
- `node_trade_rank_results: tuple[OrderControlTvtNodeMpGeneralTradeRankResult, ...]`

意味:

- 公開関数へ渡された第一入力を同一オブジェクト参照で保持する。
- 複製しない。
- `node_trade_rank_results`は、上流の対象Node別結果と同じ順序。
- `candidate_visit_set_result`やinlink物理順結果を重複フィールドとして保存しない。

## 結果型へ保存しないもの

次を一般形順位結果型へ保存しない。

- 候補ID
- prefix組合せ
- 最大prefix
- `excluded_right_of_entry_inlink_name`
- FIFO判定結果
- FIFO違反理由
- 局所仮想計算結果
- 経済性評価結果
- `surplus`
- 買い手価値`G`
- 売り手必要補償`R`
- 支払額
- 補償額
- 成立候補フラグ
- 採用候補フラグ
- RNG結果
- 最終確定列
- 確定順位ブロック
- 永続baseline順位dict
- World
- Vehicle
- Node
- Link
- collector
- 順位台帳

## Node別status契約

既存の`OrderControlTvtCandidateVisitSetStatus`を使用する。新しいstatus Enumを作らない。

次の場合だけ一般形順位再構成を行う。

- `BASELINE_INFORMATION_COMPLETE`

ただし、`BASELINE_INFORMATION_COMPLETE`でも`concrete_buyer_candidate_sets`が空なら、`candidate_trade_rank_results`を空tupleとする。これは正常な「具体的買い手候補なし」であり、例外ではない。

次の正式4 statusでは順位再構成を行わない。

- `NOT_BUILT_NO_RIGHT_OF_ENTRY`
- `NOT_BUILT_UNRESOLVED_ARRIVALS`
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`
- `UNRESOLVED_CANDIDATE_PASSAGES`

これらの場合:

- 参加Mappingを検証しない。
- `trade_scope`を作らない。
- 3分類を作らない。
- `trade_rank`を作らない。
- `trade_order`を作らない。
- `candidate_trade_rank_results`を空tupleとする。

想定外status:

- `RuntimeError`
- 正常な空結果として隠さない。
- 対象Node名と実際のstatusをエラーメッセージへ含める。
- 後続の対象Nodeを処理しない。
- 部分的な全体結果を返さない。

## 上流Node結果の対応確認

次の対象Node別結果の件数一致を確認する。

- `concrete_buyer_candidate_set_result.node_concrete_buyer_candidate_set_results`
- その上流`candidate_visit_set_result.node_candidate_set_results`

件数不一致は`RuntimeError`。

各indexについて次を確認する。

- `node_name`一致
- `build_status`一致

不一致は`RuntimeError`。

エラーメッセージには少なくとも次を含める。

- index
- 対象Nodeを識別できる情報
- expected
- actual

重大不整合後は後続の対象Nodeを処理せず、部分的な全体結果を返さない。

## 参加Mappingの検証

買い手は最初に具体的買い手候補集合への所属で分類する。その後、`trade_scope`内の非買い手Visitを`participates_by_visit_key`により、売り手と非参加Visitへ分ける。したがって、買い手も3分類の対象である。

分類順:

1. 具体的買い手候補集合に含まれるVisitは買い手。
2. 買い手でなく、`participates_by_visit_key`が`False`なら非参加Visit。
3. 買い手でなく、`participates_by_visit_key`が`True`なら売り手。

`BASELINE_INFORMATION_COMPLETE`で具体的買い手候補集合が1件以上ある対象Nodeについて、`candidate_visits`全件の参加Mappingを対象Node単位で一度検証する。候補ごとに同じ参加Mapping検証を繰り返さない。

外部入力検査は`ValueError`:

- 必要なcandidate VisitKeyが`participates_by_visit_key`に存在しない。
- 参加状態の値が厳密なPythonの`bool`でない。

厳密なPythonの`bool`だけを許可する。概念上は次の判定とする。

```text
type(participation_value) is bool
```

次を拒否する。

- `1`
- `0`
- 文字列
- `numpy.bool_`
- その他のbool類似値

余分なVisitKeyは許容する。余分なVisitKeyは処理に使用しない。Mapping全体の完全一致は要求しない。`participates_by_visit_key`を変更しない。

正式な非生成statusでは参加Mappingを検証しない。

`BASELINE_INFORMATION_COMPLETE`でも具体的買い手候補集合が0件の場合:

- 順位再構成対象が0件なので、参加Mappingは検証しない。
- `candidate_trade_rank_results`は空tupleとする。
- 存在しない順位候補のために外部入力検査を行わない。

上流契約の重大不整合は`RuntimeError`:

- 権利保有Visitが`participates_by_visit_key`で`False`。
- 具体的買い手候補集合内のVisitが`False`。
- 具体的買い手候補集合のVisitKeyが`candidate_visits`に存在しない。

権利保有Visitが`candidate_visits`に存在しない場合も`RuntimeError`とする。権利保有Visitの特定には、対象Node別candidate結果の`right_of_entry_visit_key`を使用する。`BASELINE_INFORMATION_COMPLETE`で具体的候補が存在するのに`right_of_entry_visit_key`が`None`なら`RuntimeError`とする。

## `candidate_visits`とbaseline順位

`candidate_visits`は、対象Nodeへ向かう全inlink横断の正式baseline順である。

次の一時情報を作る。

- `baseline_order`: `tuple[OrderControlTvtVisitKey, ...]`
- `baseline_rank_by_visit_key`: `dict[OrderControlTvtVisitKey, int]`

`baseline_order`は`candidate_visits`の`visit_key`を既存tuple順に取り出して作る。`baseline_rank_by_visit_key`は1始まりとする。`candidate_visits`の正式baseline sortを再実行しない。参加状態をbaseline順位の決定に使用しない。

`baseline_rank_by_visit_key`は一時dictであり、全体結果や対象Node別結果へ重複保存しない。一候補結果のprivateな`_trade_rank_by_visit_key`とは別物である。

## 一つの具体的候補の処理順

可読性を優先し、次の各処理を別々の段階と中間変数で実装できる仕様とする。

1. `concrete_buyer_candidate_set`から`buyers_sorted`を取得する。
2. `buyers_sorted`が空でないことを確認する。
3. `buyers_sorted`の全VisitKeyが`baseline_order`に存在することを確認する。
4. `buyers_sorted`の全VisitKeyが`participates_by_visit_key`で`True`であることを確認する。
5. `buyers_sorted`の正式baseline相対順が維持されていることを確認する。
6. `buyers_sorted[-1]`を最後尾買い手候補とする。
7. 最後尾買い手候補のbaseline順位を`last_buyer_rank`とする。
8. `baseline_order`の先頭から`last_buyer_rank`件を`trade_scope`とする。
9. `trade_scope`を正式baseline順に一度走査する。
10. Visitが買い手集合に含まれる場合、`buyers_sorted`側へ分類する。
11. 買い手でなく参加状態が`False`なら`nonparticipating_visits_sorted`へ分類する。
12. 買い手でなく参加状態が`True`なら`sellers_sorted`へ分類する。
13. `trade_scope`内で1から`last_buyer_rank`までの局所順位枠を作る。
14. 非参加Visitを、そのVisitのbaseline局所順位と同じ順位枠へ固定する。
15. 全局所順位から非参加Visitの固定順位を除いた空き順位を、昇順で作る。
16. `buyers_sorted`をbaseline相対順のまま、空き順位の先頭側へ配置する。
17. `sellers_sorted`をbaseline相対順のまま、残る空き順位へ配置する。
18. `trade_scope`外Visitへbaseline順位と同じ順位を設定する。
19. `candidate_visits`全件に対応する`trade_rank`を完成させる。
20. `trade_rank`の値が小さい順に`baseline_order`を並べ、`trade_order`を作る。
21. 一般形専用の内部整合確認を行う。
22. 確認成功後に`OrderControlTvtMpGeneralTradeRankResult`を一度だけ構築する。

## `trade_scope`

`trade_scope`は、正式baseline順の`candidate_visits`の先頭から、最後尾買い手候補までのVisit列である。日本語表記は本ファイル§14.1のとおり「取引候補別順位再構成範囲」である。

契約:

- 空でない。
- `candidate_visits`の先頭から始まる。
- 末尾は最後尾買い手候補。
- `len(trade_scope) == last_buyer_rank`。
- `last_buyer_rank`は`candidate_visits`内の1始まり順位。
- `trade_scope`外Visitは順位再構成の影響を受けない。
- `trade_scope`外Visitはbaseline順位を維持する。

`candidate_visits`全体を無条件に`trade_scope`としない。

## 3分類

`trade_scope`内のVisitを、次の3集合へ重複なく分類する。

1. `buyers_sorted`
2. `sellers_sorted`
3. `nonparticipating_visits_sorted`

関係:

```text
buyers
+
sellers
+
nonparticipating visits
=
trade_scope
```

3集合は互いに重複しない。順序はすべて正式baseline相対順を維持する。

権利保有inlink上のVisitも`trade_scope`に含まれる場合は分類対象になる。

- 買い手でない参加Visitなら売り手。
- 非参加Visitなら固定順位Visit。

権利保有inlink上のVisitを順位再構成から除外しない。買い手候補生成時の権利保有inlink除外と混同しない。

## 空き順位枠方式

一般形順位構築の唯一の正本は空き順位枠方式である。既存の非参加Visitなし専用の売り手後退式を、一般形順位構築の正本として使用しない。

処理:

1. `trade_scope`内の非参加Visitのbaseline局所順位を固定する。
2. 1から`last_buyer_rank`までの順位から固定順位を除く。
3. 残る空き順位を昇順に保持する。
4. `buyers_sorted`を空き順位の先頭側へ配置する。
5. `sellers_sorted`を残る空き順位へ配置する。

非参加Visitが0件の場合:

- 固定順位は空。
- 1から`last_buyer_rank`までの全順位が空き順位。
- 買い手を先頭側へ連続配置する。
- 売り手を後続順位へ配置する。
- 既存の非参加Visitなし順位計算部品と同じ結果になる。

可読性のため、次を一つの式へ詰め込まない。

- 固定順位の作成
- 空き順位の作成
- 買い手の順位割当て
- 売り手の順位割当て
- `trade_scope`外順位の割当て
- `trade_order`の構築

長い内包表記、複雑な多重ジェネレーター式、巧妙なone-linerを避ける。意味の分かる中間変数と明示的なforループを優先する。

## 売り手の順位後退

制度上、`trade_scope`内のすべての売り手について次が成立する。

```text
取引後順位 > baseline順位
```

理由:

- `trade_scope`の末尾は必ず買い手候補Visit。
- 各売り手よりbaselineで後方に、少なくとも1件の買い手候補Visitが存在する。
- 後方の買い手が前進するため、売り手は少なくとも1順位後退する。
- 非参加Visitの固定順位は、売り手の後退を打ち消さない。

順位構築後に、後退した参加Visitだけを改めて売り手として抽出しない。売り手は3分類時点で決定する。売り手後退は、一般形専用内部整合確認で確認する。

## `trade_rank`と`trade_order`

`trade_rank`は取引後順位の正本とする。対応は`VisitKey -> 取引後順位`である。`candidate_visits`全件について順位を保持する。

`trade_scope`内:

- 非参加Visitはbaseline局所順位を維持する。
- 買い手は空き順位の先頭側へ配置される。
- 売り手は残りの空き順位へ配置される。

`trade_scope`外:

- baseline順位を維持する。

`trade_order`:

- `baseline_order`を`trade_rank`の値が小さい順へ並べたtuple。
- `trade_rank`から派生させる。
- `trade_order`を独立の順位正本にしない。

`trade_order`内の位置と`trade_rank`が一致しなければならない。

## 一般形専用の内部整合確認

既存の`uxsim/order_control_tvt_trade_rank.py`にある`_verify_local_trade_rank_state()`を一般形で使用しない。

理由:

- 非参加Visitなし専用である。
- 買い手と売り手だけで`trade_scope`を分割する前提である。
- 非参加Visitの固定順位を扱わない。
- 非参加Visitなし専用の売り手後退式を検査する。
- 一般形の正本である空き順位枠方式と一致しない検査を含む。

一般形専用のprivate内部整合確認を、新規モジュール内へ設ける。少なくとも次を確認する。

- `buyers_sorted`が空でない。
- `buyers_sorted`の全VisitKeyが`baseline_order`に存在する。
- `buyers_sorted`の全Visitが参加Visitである。
- `buyers_sorted`が正式baseline相対順を維持する。
- `last_buyer_rank`が1以上である。
- `last_buyer_rank`が`baseline_order`件数以下である。
- `last_buyer_rank`が最後尾買い手のbaseline順位と一致する。
- `trade_scope`が`baseline_order[:last_buyer_rank]`と一致する。
- `trade_scope`の末尾が最後尾買い手である。
- `buyers_sorted`、`sellers_sorted`、`nonparticipating_visits_sorted`が相互に重複しない。
- 3集合の和集合が`trade_scope`と一致する。
- `sellers_sorted`が正式baseline相対順を維持する。
- `nonparticipating_visits_sorted`が正式baseline相対順を維持する。
- 非参加Visitの`trade_rank`がbaseline局所順位から変化していない。
- 買い手が非参加Visit固定後の空き順位の先頭部分を使用している。
- 売り手が買い手配置後の残りの空き順位を使用している。
- すべての売り手の取引後順位がbaseline順位より後ろである。
- `trade_rank`のVisitKey集合が`baseline_order`と一致する。
- `trade_order`のVisitKey集合が`baseline_order`と一致する。
- `trade_order`の件数が`baseline_order`と一致する。
- 順位値が厳密なPythonの`int`である。
- `bool`を順位値として受け入れない。
- 順位値が1以上である。
- 順位値が1から`baseline_order`件数まで過不足なく存在する。
- 順位重複がない。
- 順位欠番がない。
- `trade_order`内の位置と`trade_rank`が一致する。
- `trade_scope`外Visitの順位がbaseline順位から変化していない。

内部整合確認の失敗は`RuntimeError`とする。内部整合確認が成功する前に結果オブジェクトを返さない。

途中候補で重大不整合が発生した場合:

- 後続候補を処理しない。
- 後続の対象Nodeを処理しない。
- 部分的な全体結果を返さない。

## `ValueError`と`RuntimeError`

外部入力または結果クラス直接構築時の型・形式契約違反は`ValueError`。

順位構築後または上流結果間に見つかった重大な構造矛盾は`RuntimeError`。

少なくとも外部入力の`ValueError`:

- 必要な`participates_by_visit_key`のVisitKey欠落。
- 参加状態が厳密なPythonの`bool`でない。
- 結果クラス直接構築時の最低限の型・形式違反。
- `assigned_rank`へ不正VisitKeyを渡した場合。
- `assigned_rank`へ結果に存在しないVisitKeyを渡した場合。

少なくとも`RuntimeError`:

- 対象Node別結果件数不一致。
- `node_name`不一致。
- `build_status`不一致。
- 想定外status。
- `BASELINE_INFORMATION_COMPLETE`で具体的候補があるのに`right_of_entry_visit_key`が`None`。
- 権利保有Visitが`candidate_visits`にない。
- 権利保有Visitが非参加。
- 具体的買い手候補集合の`buyers_sorted`が空。
- 買い手候補が`candidate_visits`にない。
- 買い手候補が非参加。
- `buyers_sorted`の正式baseline相対順が壊れている。
- 一般形内部整合確認の失敗。
- 順位重複、欠番、範囲外。
- 3分類の重複または不足。
- 非参加Visitの固定順位変化。
- 買い手または売り手の相対順変化。
- 売り手がbaselineと同順位または前順位。
- `trade_rank`と`trade_order`の不一致。
- `trade_scope`外順位の変化。

FIFO違反は、この部品の`ValueError`または`RuntimeError`ではない。FIFO違反は後続検査で`False`となる正常な候補棄却である。

対象Nodeについて具体的買い手候補集合が0件であることは、上記の「`buyers_sorted`が空」とは別である。前者は正常な空tupleであり、後者は一件の具体的候補が空の買い手列を持っていた場合の重大不整合である。

## 結果クラスの最低限の入力確認

`OrderControlTvtMpGeneralTradeRankResult`のコンストラクターはキーワード専用とする。最低限、次を確認する。

- `concrete_buyer_candidate_set`が`OrderControlTvtMpConcreteBuyerCandidateSet`である。
- `buyers_sorted`がtupleである。
- `buyers_sorted`が空でない。
- `buyers_sorted`の各要素が有効なVisitKeyである。
- `buyers_sorted`内に重複がない。
- `sellers_sorted`がtupleである。
- `sellers_sorted`は空tupleを認める。
- `sellers_sorted`の各要素が有効なVisitKeyである。
- `sellers_sorted`内に重複がない。
- `nonparticipating_visits_sorted`がtupleである。
- `nonparticipating_visits_sorted`は空tupleを認める。
- 各要素が有効なVisitKeyである。
- `nonparticipating_visits_sorted`内に重複がない。
- `last_buyer_rank`が`bool`ではないPython `int`である。
- `last_buyer_rank`が1以上である。
- `trade_scope`が非空tupleである。
- `trade_scope`内の各要素が有効なVisitKeyである。
- `trade_scope`内に重複がない。
- `trade_order`が非空tupleである。
- `trade_order`内の各要素が有効なVisitKeyである。
- `trade_order`内に重複がない。
- `trade_rank_by_visit_key`が非空dictである。
- 順位dictの全キーが有効なVisitKeyである。
- 全順位値が`bool`ではないPython `int`である。
- 全順位値が1以上である。

これらの違反は`ValueError`。

コンストラクターで次を全面的に繰り返さない。

- 3分類と`trade_scope`の集合関係。
- baseline相対順。
- 非参加Visitの順位固定。
- 空き順位枠の正しい利用。
- 売り手後退。
- `trade_scope`外順位不変。
- 順位の完全な一意性・連続性。
- `trade_rank`と`trade_order`の完全対応。
- `baseline_order`との集合一致。

これらは公開関数内で結果構築前に一般形専用helperが確認する。順位dictは防御コピーする。列はtupleとして保持する。

## 本番で再検証しない上流保証済み事項

次を一般形順位再構成部品で再検証しない。

- P−1条件。
- TVT固有可変上限N。
- `candidate_visits`の正式baseline sortキー。
- baseline passage timestepそのもの。
- inlink別snapshot物理順。
- prefixの物理的連続性。
- 具体的買い手候補集合の生成方法。
- prefix直積。
- 全空組合せ除外。
- 権利保有inlinkから買い手候補を選んでいないことの候補ごとの再確認。
- 具体的買い手候補集合間の重複。
- 各具体的買い手候補内のVisitKey重複。
- `candidate_visits`の一般的なフィールド型。
- 単車線条件。
- FIFO。

ただし、異なる上流結果または異なる参加Mappingの誤結合によって誤順位を生成する重大不整合は、必要最小限に確認する。

## 読取専用契約

次を変更しない。

- `concrete_buyer_candidate_set_result`
- `inlink_candidate_physical_order_result`
- `candidate_visit_set_result`
- `node_candidate_set_results`
- `candidate_visits`
- `node_concrete_buyer_candidate_set_results`
- `concrete_buyer_candidate_sets`
- `concrete_buyer_candidate_set`
- `buyers_sorted`
- `participates_by_visit_key`
- collector
- rank state
- World
- Vehicle
- Node
- Link

上流関数を再実行しない。次を呼び直さない。

- `build_tvt_candidate_visit_set`
- `build_tvt_inlink_candidate_physical_orders`
- `build_tvt_mp_concrete_buyer_candidate_sets`
- `select_right_of_entry_decision_window_visits`
- `confirm_leading_nonparticipating_decision_window_visits`
- baseline alignment
- baseline fork
- collector export

既存の`build_tvt_trade_rank_without_nonparticipants`も、一般形の本番処理から呼ばない。一般形は独自の空き順位枠方式で順位を構築する。既存関数は同値性テストの比較対象としてのみ使用する。

## FIFO検査との責任分離

一般形順位再構成部品では、`preserves_inlink_fifo()`を呼ばない。これはFIFOを不要とする意味ではない。この部品は、FIFO検査前の順位結果を構築する。後続部品が既存の`preserves_inlink_fifo()`を呼ぶ。

後続FIFO検査に渡す材料:

- 取引前: `result.trade_scope`
- 取引後: `result.trade_order[:result.last_buyer_rank]`
- inlink mapping: `candidate_visits`から作るVisitKey → `inlink_name`の対応

一般形順位再構成の結果型へFIFO判定結果を保存しない。FIFO違反は後続処理で`False`となる。FIFO違反候補だけを正常に棄却し、他候補の検討を続ける。FIFO違反を理由に、同じ候補の順位を別方式で作り直さない。

## 非参加Visit0件での既存部品との同値性

専用テストで、非参加Visitが0件の一般形結果を、既存の次の関数と比較する。

```text
build_tvt_trade_rank_without_nonparticipants
```

既存関数と既存結果型は変更しない。

比較対象:

- `buyers_sorted`
- `sellers_sorted`
- `last_buyer_rank`
- Visitごとの取引後順位
- `trade_order`
- `trade_scope`外Visitの順位

一般形の`trade_scope`は`baseline_order[:last_buyer_rank]`で確認する。

複数の明示的ケースを用意する。少なくとも次を含める。

- 買い手1件。
- 買い手複数。
- 売り手0件。
- 売り手複数。
- buyers入力相当の順序とbaseline順が異なることを上流結果の手書き不整合として確認するケース。
- `trade_scope`外Visitが1件以上あるケース。
- 最後尾のcandidate Visitが買い手となるケース。

期待値を一般形実装と同じ空き順位計算から自動生成しない。同値性テストでは既存関数の結果と比較してよいが、一般形固有の期待値も可能な範囲で明示する。

一般形が既存部品と同値であることを確認した後でも、今回の作業で既存関数を削除、変更、または互換入口へ変更しない。

## 一般形専用テスト契約

新規専用テスト:

```text
tests_order_control_tvt_mp_general_trade_rank.py
```

既存テストのhelperを直接importしない。必要なfixtureを新規専用テスト内へ明示的に作る。期待値を本番と同じ処理で自動生成しない。明示的なVisitKey列、分類、順位dict、`trade_order`を期待値として記述する。

少なくとも次をテストする。

### 公開APIと結果型

- 3つの公開結果型をimportできる。
- 公開関数をimportできる。
- 対象Node別結果と全体結果がfrozen dataclassである。
- 一候補結果が読取専用である。
- 一候補結果のコンストラクターがキーワード専用である。
- 各公開propertyが存在する。
- property setterがない。
- `assigned_rank`が正しい順位を返す。
- `assigned_rank`が不正VisitKeyを`ValueError`とする。
- `assigned_rank`が結果外VisitKeyを`ValueError`とする。
- `trade_rank_items`が取引後順位順のtupleを返す。
- `trade_rank_items`が内部dictを返さない。
- 順位dictを防御コピーする。
- `update`、`rollback`、`export`、`export_state`、`to_dict`がない。
- 全体結果が第一入力を同一参照保持する。
- 一候補結果が上流の`concrete_buyer_candidate_set`を同一参照保持する。
- 禁止フィールドを持たない。

### status

- `BASELINE_INFORMATION_COMPLETE`で具体的候補がある場合だけ順位を生成する。
- `BASELINE_INFORMATION_COMPLETE`で具体的候補0件なら正常な空tuple。
- 正式4非生成statusで空tuple。
- 正式4非生成statusでは参加Mappingを検証しない。
- 想定外statusで`RuntimeError`。
- 想定外statusのメッセージに対象Node名とstatusを含む。
- 途中の対象Nodeの想定外statusで部分結果を返さない。

### `trade_scope`

- `candidate_visits`の先頭から始まる。
- 最後尾買い手までを含む。
- 末尾が最後尾買い手である。
- `len(trade_scope) == last_buyer_rank`。
- `candidate_visits`全体と一致しないケース。
- `trade_scope`外Visitを含むケース。
- `trade_scope`外Visitの順位が変化しない。

### 3分類

- 買い手、売り手、非参加Visitが`trade_scope`を過不足なく分割する。
- 3集合が相互に重複しない。
- 各集合が正式baseline相対順を維持する。
- 権利保有Visitが`trade_scope`内で売り手となる。
- 権利保有inlink上の別参加Visitも売り手になり得る。
- 権利保有inlink上の非参加Visitは固定順位Visitになる。
- 非参加Visitが買い手にも売り手にも入らない。
- 買い手でない参加Visitが売り手になる。

### 空き順位枠方式

- 非参加Visit1件。
- 非参加Visit複数。
- 非参加Visitが`trade_scope`先頭にある場合。
- 非参加Visitが`trade_scope`中間にある場合。
- 非参加Visitが複数の離れた順位にある場合。
- 非参加Visitのbaseline局所順位が維持される。
- 買い手が空き順位の先頭側を使用する。
- 売り手が残りの空き順位を使用する。
- 買い手間のbaseline相対順が維持される。
- 売り手間のbaseline相対順が維持される。
- 全売り手がbaseline順位より後退する。
- 順位重複がない。
- 順位欠番がない。
- 順位が1から`candidate_visits`件数まで連続する。
- `trade_rank`と`trade_order`が一致する。
- `trade_scope`外順位が不変。

複数の非参加Visitを売り手が追加的にまたぐケースを含める。個別の売り手後退補正式ではなく、明示的な最終順位期待値で空き順位枠方式を確認する。

### 参加Mapping

- candidate VisitKey欠落で`ValueError`。
- `trade_scope`外candidate VisitKeyの欠落も、対象Node単位の全件検証により`ValueError`。
- 値`1`で`ValueError`。
- 値`0`で`ValueError`。
- 文字列で`ValueError`。
- `numpy.bool_`で`ValueError`。
- 余分なVisitKeyを許容する。
- 余分なVisitKeyが結果へ影響しない。
- Mappingを変更しない。
- 権利保有Visitが`False`で`RuntimeError`。
- 買い手候補が`False`で`RuntimeError`。
- 非参加Visitは正常に固定順位へ分類される。
- 非生成statusでは欠落・非boolを検証しない。
- `COMPLETE`でも具体的候補0件ならMappingを検証しない。

### 重大不整合

- 対象Node別結果件数不一致。
- `node_name`不一致。
- `build_status`不一致。
- 想定外status。
- `right_of_entry_visit_key`が`None`。
- 権利保有Visitが`candidate_visits`にない。
- 買い手候補が`candidate_visits`にない。
- 買い手候補が非参加。
- `buyers_sorted`が空。
- `buyers_sorted`の正式baseline相対順が壊れている。
- 3分類が重複する。
- 3分類が`trade_scope`を完全に覆わない。
- 非参加Visitの順位が変化する。
- 買い手相対順が変化する。
- 売り手相対順が変化する。
- 売り手が後退しない。
- 順位重複。
- 順位欠番。
- 順位範囲外。
- `trade_rank`と`trade_order`の不一致。
- `trade_scope`外順位の変化。
- 途中候補の異常で後続候補を処理しない。
- 途中の対象Nodeの異常で後続の対象Nodeを処理しない。
- 部分結果を返さない。
- 公開関数経由で内部確認が失敗した場合に`RuntimeError`が伝播する。

各内部不整合テストでは、別の不整合を混在させず、狙った検査まで到達する入力を手書きする。

### 非参加Visit0件の同値性

- 既存`build_tvt_trade_rank_without_nonparticipants`との比較。
- `buyers_sorted`一致。
- `sellers_sorted`一致。
- `last_buyer_rank`一致。
- Visitごとの順位一致。
- `trade_order`一致。
- `trade_scope`外順位一致。
- 複数ケース。
- 既存関数を一般形本番処理から呼んでいないこと。

### 読取専用

- 第一入力を変更しない。
- `candidate_visits`を変更しない。
- `concrete_buyer_candidate_sets`を変更しない。
- `buyers_sorted`を変更しない。
- 参加Mappingを変更しない。
- 上流処理を再実行しない。
- World、Vehicle、collector、順位台帳へ戻らない。
- 既存順位計算関数を一般形本番処理から呼ばない。
- `preserves_inlink_fifo`を一般形順位再構成部品から呼ばない。

### FIFO責任分離

一般形順位再構成の専用テストでは、順位結果から次の材料を取得できることを確認する。

- `trade_scope`
- `trade_order[:last_buyer_rank]`

ただし、一般形順位再構成の公開関数が`preserves_inlink_fifo`を呼ばないことをpatch等で確認する。FIFOそのものの正常・違反判定は、既存`tests_order_control_tvt_trade_rank.py`の契約を維持する。今回の新規部品ではFIFO結果を返さない。

### テスト登録

`TESTS`リストを設ける場合:

- `test_`関数の重複登録なし。
- 定義済み`test_`関数の登録漏れなし。
- 未知の関数参照なし。
- AST確認。
- 直接実行件数を表示。
- pytest収集件数と一致。

既存`tests_order_control_tvt_trade_rank.py`の堅牢な登録確認方法を参考にしてよい。ただし、必要以上に複雑な仕組みへ変更しない。

## 今回実装しない範囲

今回の実装前仕様には、一般形順位再構成までを含める。次は実装対象外とする。

- FIFO検査の実行。
- FIFO違反候補の除外。
- 候補別局所仮想計算。
- 経済性評価。
- 買い手価値`G`。
- 売り手必要補償`R`。
- `G >= R`判定。
- `surplus`。
- 成立候補選択。
- `surplus`同値時の買い手数比較。
- RNG。
- 支払い。
- 補償。
- 成立時の最終確定列。
- 不成立時の最終確定列。
- 情報未解決時の最終確定列。
- 確定順位ブロックへの接続。
- 上位TVT制御。
- TVT-SB。
- TVT-MH。
- TVT-SP。
- 性能最適化。
- World、Vehicle、collector、順位台帳への接続。
- 既存非参加Visitなし順位計算部品の変更。
- `preserves_inlink_fifo`の変更。

## 可読性方針

研究用コードとして正しく動くことを最優先とする。複数の実装方法を選べる場合は、短さ、巧妙さ、高度なPythonテクニックより、Python初学者が後から処理を追いやすい、明示的で可読性の高い方法を優先する。

必ず次を守る。

- 長い内包表記を避ける。
- 複雑な多重ジェネレーター式を避ける。
- 巧妙なone-linerを避ける。
- 多段階処理を一つの式へ詰め込まない。
- 意味の分かる中間変数を使う。
- baseline順位構築、`trade_scope`、3分類、非参加固定順位、空き順位、買い手配置、売り手配置、`trade_scope`外順位、`trade_order`、内部確認、結果構築を分ける。
- helperは責務が明確な場合だけ作る。
- 不要な一般化と抽象化を行わない。
- 実測前の性能最適化を行わない。
- コメントとdocstringで交通上の意味も説明する。
- 「Node全体」という曖昧な表現を避ける。
- 必要な場合は「対象Nodeへ向かう全inlink横断の正式baseline順」と書く。

この可読性方針を理由に、確定済み制度仕様、公開API、結果型、status契約、例外契約、未実装境界を変更しない。

## 実装後の次の作業

一般形順位再構成部品を実装・検証した後は、FIFO検査の実行、局所仮想計算、経済性評価へ進む前に、実装完了記録を本ファイルと進捗メモへ残す。その後の直接作業は、本部品が構築した`trade_scope`と`trade_order[:last_buyer_rank]`を材料とするFIFO検査接続の実装前仕様である。

# TVT-MP一般形順位再構成部品の実装完了記録

**実装完了日：2026-09-15**

本節は、上記「TVT-MP一般形順位再構成部品の実装前仕様」に対応する実装完了記録である。制度ロジックの正本は、引き続き本ファイル§3.3、§4、§7、§10.1、§14から§21、§28（該当段階）、§29.3から§29.5および当該実装前仕様である。実装前仕様は、実装時に用いた正本として削除・置換せず維持する。

一般形順位再構成部品の実装前仕様の保存済み・push済みコミットは`3932f21`（`Document the TVT-MP general trade rank reconstruction implementation specification`）である。その保存済み仕様に従い、新規本番と専用テストを実装した。本実装完了記録時点では、新規コード・新規専用テスト・本節の追記・進捗メモ追記は、まだ`git add`、`git commit`、`git push`していない。

Copilotと利用者が、本番コード、専用テスト、独立反証レビュー、Terminalでのテスト結果、テスト登録件数、Git状態を確認済みである。Cursor報告だけでは実装完了を確定しない。

## 新規ファイルと公開API

新規本番:

- `uxsim/order_control_tvt_mp_general_trade_rank.py`

新規専用テスト:

- `tests_order_control_tvt_mp_general_trade_rank.py`

公開関数:

- `build_tvt_mp_general_trade_ranks`

公開結果型（3つ）:

1. `OrderControlTvtMpGeneralTradeRankResult`
2. `OrderControlTvtNodeMpGeneralTradeRankResult`
3. `OrderControlTvtMpGeneralTradeRankSetResult`

## 公開関数と結果型

第一入力は`OrderControlTvtMpConcreteBuyerCandidateSetResult`を位置引数として受け取る。keyword-only必須入力は`participates_by_visit_key: Mapping[OrderControlTvtVisitKey, bool]`である。`participates_by_visit_key`は位置引数では渡せず、キーワード名が必要である。

World、Vehicle、collector、Node、Link、順位台帳は受け取らない。`candidate_visit_set_result`やinlink別物理順結果を重複入力として受け取らない。

`OrderControlTvtMpGeneralTradeRankResult`は、一般形の一候補順位結果を保持する読取専用の通常クラスである。キーワード専用コンストラクターを持つ。公開propertyは`concrete_buyer_candidate_set`、`buyers_sorted`、`sellers_sorted`、`nonparticipating_visits_sorted`、`last_buyer_rank`、`trade_scope`、`trade_order`である。公開読取メソッドは`assigned_rank()`と`trade_rank_items()`である。順位辞書はprivateな`_trade_rank_by_visit_key`として保持し、コンストラクターへ渡された順位辞書を防御コピーする。内部dictは直接返さない。property setter、`update`、`rollback`、`export`、`export_state`、`to_dict`、順位変更用公開APIは追加していない。

`OrderControlTvtNodeMpGeneralTradeRankResult`と`OrderControlTvtMpGeneralTradeRankSetResult`は公開frozen dataclassとして実装した。

全体結果は、公開関数へ渡された`OrderControlTvtMpConcreteBuyerCandidateSetResult`を同一オブジェクト参照で保持する。一候補結果は、対応する上流の`OrderControlTvtMpConcreteBuyerCandidateSet`を同一参照で保持する。

## status別動作

`BASELINE_INFORMATION_COMPLETE`かつ具体的買い手候補集合が1件以上ある対象Nodeだけで一般形順位再構成を実行する。

`BASELINE_INFORMATION_COMPLETE`でも具体的買い手候補集合が0件なら正常な空結果とする。参加Mappingを検証せず、`candidate_trade_rank_results`は空tupleとする。

次の正式4 statusでは順位再構成を行わない。参加Mappingを検証せず、`trade_scope`、3分類、`trade_rank`、`trade_order`を作らず、`candidate_trade_rank_results`は空tupleとする。

- `NOT_BUILT_NO_RIGHT_OF_ENTRY`
- `NOT_BUILT_UNRESOLVED_ARRIVALS`
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`
- `UNRESOLVED_CANDIDATE_PASSAGES`

想定外statusは`RuntimeError`とする。対象Node名と実際のstatusをエラーメッセージへ含める。後続の対象Nodeを処理せず、部分的な全体結果を返さない。

## 参加Mappingと上流Node結果の対応

`BASELINE_INFORMATION_COMPLETE`かつ具体的候補が1件以上ある対象Nodeについて、`candidate_visits`全件の参加Mappingを対象Node単位で一度だけ検証する。候補ごとに同じ検証を繰り返さない。

必要なcandidate VisitKeyの欠落、厳密なPythonの`bool`以外（`1`、`0`、文字列、`numpy.bool_`、その他のbool類似値）は`ValueError`とする。余分なVisitKeyは許容し、処理には使用しない。参加Mappingは変更しない。

上流candidate Node結果と具体的買い手候補集合のNode結果について、件数・各indexの`node_name`・`build_status`を確認する。不一致は`RuntimeError`とする。重大不整合後は後続候補、後続の対象Nodeを処理せず、部分的結果を返さない。

## baseline順位、`trade_scope`、3分類、空き順位枠方式

`candidate_visits`の既存tuple順を、対象Nodeへ向かう全inlink横断の正式baseline順として使用する。`baseline_order`と1始まりの`baseline_rank_by_visit_key`を一時dictとして構築する。`baseline_arrival_timestep`、`arrival_tiebreaker`、`vehicle_id`による再ソートは行わない。参加状態を正式baseline順位の決定へ使用しない。上流の`buyers_sorted`を一般形部品内で再ソートしない。`buyers_sorted`の正式baseline相対順が壊れている場合は`RuntimeError`とする。

一つの具体的買い手候補について、`buyers_sorted[-1]`を最後尾買い手とし、その1始まり正式baseline順位を`last_buyer_rank`とする。`trade_scope`は`candidate_visits`の先頭から最後尾買い手までである。`candidate_visits`全件を無条件に`trade_scope`としない。`trade_scope`外Visitはbaseline順位を維持する。`trade_scope`外の非参加Visitは、買い手・売り手・`nonparticipating_visits_sorted`の3分類には含めない。参加状態が`False`であることを理由に、`trade_scope`外Visitのbaseline順位を変更しない。

`trade_scope`内のVisitを正式baseline順に一度走査し、買い手候補集合所属→非買い手かつ非参加→非買い手かつ参加の順で3分類する。3集合は相互に重複せず、和集合は`trade_scope`と一致する。権利保有Visitは買い手にならず、参加Visitであり、`trade_scope`に含まれる場合は売り手となる。権利保有inlink上の別の参加Visitも、`trade_scope`に含まれ、買い手でなければ売り手となる。権利保有inlink上の非参加Visitは、`trade_scope`に含まれる場合、固定順位Visitとなる。買い手候補生成時の権利保有inlink除外と、一般形順位再構成時の3分類を混同していない。

一般形順位構築は、確定済みの空き順位枠方式で実装した。非参加Visitへbaseline局所順位を設定し、固定順位を除いた空き順位へ買い手を先頭側、売り手を残りへ配置し、`trade_scope`外へbaseline順位を設定し、`trade_rank`を完成させ、`trade_rank`から`trade_order`を派生させる。既存の非参加Visitなし専用の売り手後退式は、一般形の順位構築には使用していない。`build_tvt_trade_rank_without_nonparticipants`は本番処理から呼んでいない。非参加Visitが0件の場合も同じ空き順位枠方式を使用する。

売り手は3分類時点で決定する。順位構築後に、後退した参加Visitだけを改めて売り手として抽出していない。すべての売り手について、取引後順位がbaseline順位より後ろであることを一般形内部整合確認で確認する。

正常なTVT-MPの公開関数経路では、権利保有Visitが`trade_scope`内の売り手となる。したがって、正常な公開関数経路で売り手0件となる候補は生じない。ただし、`OrderControlTvtMpGeneralTradeRankResult`のコンストラクターは、結果クラス単体の最低限の形式契約として`sellers_sorted=()`を受け入れる。このコンストラクター契約は、正常な公開関数経路で売り手0件が発生することを意味しない。

制度上の誤解を招くため、権利保有Visitを買い手にして正常な売り手0件候補として扱っていた次の2専用テストを削除した。

- `test_zero_sellers`
- `test_zero_nonparticipants_zero_sellers_matches_existing`

同内容の別名テストへ置き換えていない。結果クラス単体の空`sellers_sorted`契約は、`test_constructor_accepts_empty_sellers_and_nonparticipants`とコメントで明示している。

## `trade_rank`、`trade_order`、一般形専用内部整合確認

`trade_rank`を取引後順位の正本とする。`candidate_visits`全件について順位を保持する。`trade_order`は`baseline_order`を`trade_rank`の値が小さい順へ並べたtupleであり、`trade_rank`から一方向に派生させる。`trade_order`を独立した順位正本として別計算していない。`trade_order`内の位置と`trade_rank`の一致を確認する。

新規モジュール内に一般形専用helper `_verify_general_trade_rank_state`を実装した。既存の非参加Visitなし専用`_verify_local_trade_rank_state`は使用していない。実装前仕様が列挙する一般形固有の不変条件（3分類、`trade_scope`、非参加固定、空き順位の先頭/残り配置、売り手後退、`trade_scope`外不変、順位の完全性、`trade_order`対応など）を確認する。失敗は`RuntimeError`とし、成功する前に結果オブジェクトを返さない。

## 例外区分、FIFO責任分離、読取専用

参加Mappingの形式違反、結果クラス直接構築時の最低限の型・形式違反、`assigned_rank()`への不正VisitKeyまたは結果外VisitKeyは`ValueError`とする。上流Node結果不一致、想定外status、権利保有不整合、空の`buyers_sorted`、baseline相対順破壊、一般形内部整合確認の失敗は`RuntimeError`とする。FIFO違反は、この部品の`ValueError`または`RuntimeError`ではない。

`preserves_inlink_fifo()`は呼んでいない。FIFO検査前の順位結果を構築する。後続FIFO検査の材料は、取引前`result.trade_scope`、取引後`result.trade_order[:result.last_buyer_rank]`、`candidate_visits`から作るVisitKeyと`inlink_name`の対応である。FIFO判定結果は一般形順位結果へ保存していない。FIFO違反候補の棄却は未実装である。

第一入力、`candidate_visits`、具体的買い手候補集合、`buyers_sorted`、参加Mapping、その他の上流結果を変更していない。上流処理を再実行していない。World、Vehicle、Node、Link、collector、順位台帳へ戻っていない。

## 非参加Visit0件での既存部品との同値性

専用テストで、非参加Visitが0件の一般形結果を、既存の`build_tvt_trade_rank_without_nonparticipants`と比較した。`buyers_sorted`、`sellers_sorted`、`last_buyer_rank`、各Visitの取引後順位、`trade_order`、`trade_scope`外順位、`trade_scope`を確認した。既存関数は本番処理から呼んでいない。専用テストの比較対象としてのみ使用した。既存関数、既存結果型、`preserves_inlink_fifo`は変更していない。

## 独立反証レビューとテスト補強

実装後、Cursor Grok 4.6による独立反証レビューを実施した。反証レビューでは、ファイル変更とGit操作を行っていない。結果は重大問題0、要修正問題0、軽微問題・改善候補6であった。軽微6件は仕様違反ではなく、任意改善またはテストの弱点であった。

反証レビュー後、制度ロジックと本番コードは変更しなかった。専用テストについて、公開関数のkeyword-only契約の直接確認、`trade_scope`外の非参加Visitのbaseline順位維持、結果クラスコンストラクターのlist拒否・重複拒否・非dict順位辞書拒否、不適切な売り手0件の公開関数経由テスト2件の削除、結果クラス単体の空`sellers_sorted`契約の意味をコメントで明示する補強を行った。private順位dictを`MappingProxyType`へ変更していない。指定した2件以外の既存テストを、重複を理由に削除していない。

## 可読性

本番実装は、baseline順位構築、`trade_scope`、3分類、非参加固定順位、空き順位、買い手配置、売り手配置、`trade_scope`外順位、`trade_order`、一般形内部確認、結果構築を分離した。長い内包表記、複雑な多重ジェネレーター式、巧妙なone-linerへ処理を詰め込んでいない。意味の分かる中間変数と明示的なforループを使用した。実測前の性能最適化は行っていない。

## 確認済みテスト結果

新規2ファイルの`py_compile`は成功した。

| 区分 | 結果 |
|------|------|
| 新規専用テスト直接実行 | 132 tests passed |
| 新規専用テスト pytest | 132 passed |
| pytest収集 | 132 collected |
| 定義済み`test_`関数 | 132件 |
| `TESTS`登録 | 132件（重複なし、登録漏れなし、未知参照なし） |
| 直接実行件数とpytest収集 | 一致 |

関係する既存回帰テスト6ファイルは263 passedである。

- `tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`
- `tests_order_control_tvt_trade_rank.py`
- `tests_order_control_tvt_candidate_visit_set.py`
- `tests_order_control_tvt_inlink_candidate_physical_order.py`
- `tests_order_control_tvt_right_of_entry_selection.py`
- `tests_order_control_tvt_leading_nonparticipating_confirmation.py`

新規専用132件と既存回帰263件を合わせ、395件成功を確認した。新規2ファイルについて、未追跡ファイル用のdiff checkを実施し、空白エラーがないことを確認した。

## 今回実装しなかった境界

FIFO検査の実行、FIFO違反候補の除外、候補別局所仮想計算、経済性評価、買い手価値`G`、売り手必要補償`R`、`G >= R`判定、`surplus`、成立候補選択、`surplus`同値時の買い手数比較、RNG、支払い、補償、成立時・不成立時・情報未解決時の最終確定列、確定順位ブロックへの接続、上位TVT制御、TVT-SB、TVT-MH、TVT-SP、性能最適化、既存非参加Visitなし順位計算部品の変更、`preserves_inlink_fifo`の変更は、今回も実装していない。

## 次の作業開始点（本部品完了後）

次の直接作業は、本部品が構築した`trade_scope`と`trade_order[:last_buyer_rank]`を、既存`preserves_inlink_fifo()`へ接続するFIFO検査接続部品の**実装前仕様**を確定することである。

- 一般形順位再構成のPython実装を再考しない。
- `preserves_inlink_fifo()`自体を変更しない。
- FIFO検査接続部品では、正常なFIFO違反候補を`False`として除外し、別候補の検討を継続できる契約を設計する。
- 局所仮想計算、経済性評価、成立候補選択にはまだ進まない。

# TVT-MP FIFO検査接続部品の実装前仕様

本節は、TVT-MP FIFO検査接続部品のPython実装に使用する**唯一の最新実装前仕様**である。

- 制度ロジックは、本ファイル§20、§21、および「TVT-MP一般形順位再構成部品の実装前仕様」「TVT-MP一般形順位再構成部品の実装完了記録」に従う。FIFO検査の規則と一般形順位再構成を本節で新しく考え直さない。
- 今回確定するのは、実装・検証済みの一般形順位再構成結果と既存`preserves_inlink_fifo()`へ接続する公開API、結果型、入力経路、status、処理順、正常なFIFO違反、重大不整合、読取専用契約、専用テスト契約、未実装境界である。
- Python実装と専用テストは未着手である。実装済み、テスト済み、コミット済み、push済みとは記載しない。
- 実装・検証後は、別の実装完了記録を追加する。
- 旧メモは変更しない。
- 一般形順位再構成部品の保存済み実装コミットは`1e23174`である。このhashを、本部品の実装コミットとして扱わない。

## 非技術的な説明

一般形順位再構成部品が作った各順位案をFIFO検査へ一つずつ通し、同じ道路から交差点へ向かうVisitの前後関係が守られているかを確認する。

各候補について、FIFOを維持するか、FIFO違反かという検査票を作る。

FIFO違反候補は異常停止ではなく、その候補だけを後続対象から外す。別の候補の検討は継続する。

検査に不合格だった候補を結果から消して対応関係を失うのではなく、各候補の検査結果をTrueまたはFalseとして残す。

この部品では、局所仮想計算、経済性評価、成立候補選択はまだ行わない。

## 責任分離と新規ファイル

新しい独立した読取専用部品とする。既存の`preserves_inlink_fifo()`へ一般形接続処理を追加しない。一般形順位再構成部品へFIFO検査を追加しない。

新規本番モジュールの正式名称:

```text
uxsim/order_control_tvt_mp_fifo_inspection.py
```

新規専用テストの正式名称:

```text
tests_order_control_tvt_mp_fifo_inspection.py
```

変更しない既存部品:

- `uxsim/order_control_tvt_trade_rank.py`
- `tests_order_control_tvt_trade_rank.py`
- `uxsim/order_control_tvt_mp_general_trade_rank.py`
- `tests_order_control_tvt_mp_general_trade_rank.py`
- その他の上流処理

理由:

- `preserves_inlink_fifo()`自体は既に完成している。
- 一般形順位再構成部品はFIFO検査前の順位結果を作る責務である。
- 新しい部品は、一般形順位結果からFIFO検査材料を取り出し、既存FIFO関数を候補ごとに呼ぶ責務である。
- 順位再構成と候補検査を混在させない。
- FIFO違反の正常な候補棄却と、順位構造の重大不整合を区別する。

## 公開関数

正式名称:

```text
build_tvt_mp_fifo_inspection_results
```

署名:

```python
def build_tvt_mp_fifo_inspection_results(
    general_trade_rank_set_result:
        OrderControlTvtMpGeneralTradeRankSetResult,
) -> OrderControlTvtMpFifoInspectionSetResult:
    ...
```

契約:

- 第一入力は位置引数として受け取る。
- keyword-onlyの追加入力は設けない。
- `participates_by_visit_key`は受け取らない。
- World、Vehicle、Node、Link、collector、順位台帳を受け取らない。
- `candidate_visit_set_result`を重複入力として受け取らない。
- concrete buyer candidate set resultを重複入力として受け取らない。
- inlink別物理順結果を重複入力として受け取らない。
- 第一入力から必要な`candidate_visits`へ参照で到達する。
- 入力結果を変更しない。
- 上流処理を再実行しない。

`participates_by_visit_key`を受け取らない理由:

- `preserves_inlink_fifo()`は参加・非参加を区別しない。
- FIFO検査に必要なのは、取引前後のVisit列とVisitKeyごとのinlink名である。
- 買い手、売り手、非参加Visitはすべて同じFIFO検査対象である。

## 上流入力との接続

第一入力は`OrderControlTvtMpGeneralTradeRankSetResult`である。

第一入力から次を参照する。

- `concrete_buyer_candidate_set_result`
- `node_trade_rank_results`

`concrete_buyer_candidate_set_result`から次へ到達する。

- `inlink_candidate_physical_order_result`
- `node_concrete_buyer_candidate_set_results`

`inlink_candidate_physical_order_result`から次へ到達する。

- `candidate_visit_set_result`

`candidate_visit_set_result`から次を参照する。

- `node_candidate_set_results`

各candidate Node結果から次を参照する。

- `node_name`
- `build_status`
- `candidate_visits`

各candidate Visitから次を参照する。

- `visit_key`
- `inlink_name`

各一般形順位Node結果から次を参照する。

- `node_name`
- `build_status`
- `candidate_trade_rank_results`

各一候補順位結果から次を参照する。

- `concrete_buyer_candidate_set`
- `last_buyer_rank`
- `trade_scope`
- `trade_order`

## 処理単位と順序

処理は次の二段構造とする。

1. 対象Node別に処理する。
2. 各対象Nodeの一般形順位候補を一つずつFIFO検査する。

対象Nodeの結果順は、上流の`node_trade_rank_results`の順序を維持する。

候補検査結果は、上流の`candidate_trade_rank_results`の順序を維持する。

候補IDを追加しない。

列挙順を次に使用しない。

- 候補の優先順位
- 経済性評価順
- `surplus`同値時の選択規則
- 将来のRNGの代用

## 公開結果型

次の3つを公開frozen dataclassとする。

1. `OrderControlTvtMpCandidateFifoInspectionResult`
2. `OrderControlTvtNodeMpFifoInspectionResult`
3. `OrderControlTvtMpFifoInspectionSetResult`

### 一候補のFIFO検査結果

正式名称:

```text
OrderControlTvtMpCandidateFifoInspectionResult
```

公開frozen dataclassとする。

フィールド:

- `general_trade_rank_result: OrderControlTvtMpGeneralTradeRankResult`
- `preserves_inlink_fifo: bool`

`general_trade_rank_result`:

- 対応する上流の一般形順位結果オブジェクトを同一参照で保持する。
- 複製しない。
- どの順位候補に対するFIFO検査結果かを示す。

`preserves_inlink_fifo`:

- 厳密なPythonの`bool`。
- `True`は、対象Nodeへ向かう各inlink内の相対順をすべて維持したことを表す。
- `False`は、1本以上のinlinkで相対順が変化したことを表す。
- `False`は例外ではない。
- `False`は当該候補を後続の局所仮想計算対象から除外するための正常な検査結果である。

フィールド名`preserves_inlink_fifo`と、公開関数`preserves_inlink_fifo()`を混同しない。結果型のフィールドは、既存関数が返した検査票の値である。既存関数そのものではない。docstringでその意味を明示する。

候補を結果から削除せず、上流の候補順と一対一対応する検査結果を残す。

初期結果型へ、FIFO違反理由、違反inlink名、診断ログを保存しない。

### 対象Node別結果

正式名称:

```text
OrderControlTvtNodeMpFifoInspectionResult
```

公開frozen dataclassとする。

フィールド:

- `node_name: str`
- `build_status: OrderControlTvtCandidateVisitSetStatus`
- `candidate_fifo_inspection_results: tuple[OrderControlTvtMpCandidateFifoInspectionResult, ...]`

意味:

- 一つの対象Nodeに対応するFIFO検査結果。
- `candidate_fifo_inspection_results`は、上流の`candidate_trade_rank_results`と同じ順序。
- FIFO合格候補だけを保存しない。
- FIFO違反候補も`preserves_inlink_fifo=False`として同じ順序に残す。
- `BASELINE_INFORMATION_COMPLETE`でも順位候補が0件なら空tuple。
- 正式な非生成statusでも空tuple。

### 全体結果

正式名称:

```text
OrderControlTvtMpFifoInspectionSetResult
```

公開frozen dataclassとする。

フィールド:

- `general_trade_rank_set_result: OrderControlTvtMpGeneralTradeRankSetResult`
- `node_fifo_inspection_results: tuple[OrderControlTvtNodeMpFifoInspectionResult, ...]`

意味:

- 公開関数へ渡された第一入力を同一オブジェクト参照で保持する。
- 複製しない。
- `node_fifo_inspection_results`は上流の`node_trade_rank_results`と同じ順序。
- concrete buyer candidate set resultやcandidate visit set resultを重複フィールドとして保存しない。

## 結果型へ保存しないもの

次を結果型へ保存しない。

- FIFO違反理由
- FIFO違反inlink名
- FIFO診断ログ
- FIFO合格候補だけを集めた重複tuple
- FIFO違反候補だけを集めた重複tuple
- 参加Mapping
- `inlink_name_by_visit_key`
- `trade_scope`の複写
- `trade_order`の複写
- concrete buyer candidate setの重複参照
- 局所仮想計算結果
- 経済性評価結果
- 買い手価値`G`
- 売り手必要補償`R`
- `G >= R`判定
- `surplus`
- 成立候補フラグ
- 採用候補フラグ
- RNG結果
- 支払い
- 補償
- 最終確定列
- 確定順位ブロック
- World
- Vehicle
- Node
- Link
- collector
- 順位台帳

## Node別status契約

既存の`OrderControlTvtCandidateVisitSetStatus`を使用する。新しいstatus Enumを作らない。

次の場合だけFIFO検査を実行する。

- `BASELINE_INFORMATION_COMPLETE`
- `candidate_trade_rank_results`が1件以上

`BASELINE_INFORMATION_COMPLETE`でも`candidate_trade_rank_results`が0件なら、正常な空結果とする。

- inlink対応辞書を作らない。
- `preserves_inlink_fifo()`を呼ばない。
- `candidate_fifo_inspection_results`は空tuple。

次の正式4 statusではFIFO検査を実行しない。

- `NOT_BUILT_NO_RIGHT_OF_ENTRY`
- `NOT_BUILT_UNRESOLVED_ARRIVALS`
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`
- `UNRESOLVED_CANDIDATE_PASSAGES`

これらの場合:

- inlink対応辞書を作らない。
- `preserves_inlink_fifo()`を呼ばない。
- `candidate_fifo_inspection_results`を空tupleとする。

想定外status:

- `RuntimeError`
- 正常な空結果として隠さない。
- 対象Node名と実際のstatusをメッセージへ含める。
- 後続の対象Nodeを処理しない。
- 部分的な全体結果を返さない。

## 対象Node別上流結果の対応確認

次の対象Node別結果について、件数を確認する。

- `general_trade_rank_set_result.node_trade_rank_results`
- 上流`candidate_visit_set_result.node_candidate_set_results`
- 上流`node_concrete_buyer_candidate_set_results`

3つの件数が一致しなければ`RuntimeError`。

各indexについて次を確認する。

- `node_name`が一致する。
- `build_status`が一致する。

比較対象:

- candidate Node結果
- concrete buyer candidate Node結果
- general trade rank Node結果

不一致は`RuntimeError`。

エラーメッセージには少なくとも次を含める。

- index
- expected
- actual
- 対象Nodeを識別できる情報

重大不整合後は後続の対象Nodeを処理せず、部分的な全体結果を返さない。

## 候補結果の対応確認

`BASELINE_INFORMATION_COMPLETE`で順位候補が1件以上ある対象Nodeについて、次の件数が一致することを確認する。

- general trade rank Node結果の`candidate_trade_rank_results`
- concrete buyer candidate Node結果の`concrete_buyer_candidate_sets`

件数不一致は`RuntimeError`。

同じcandidate indexについて、次を確認する。

```text
general_trade_rank_result.concrete_buyer_candidate_set
is
concrete_buyer_candidate_sets[candidate_index]
```

同一オブジェクト参照でなければ`RuntimeError`。

内容が同じだけでは不十分である。異なる候補オブジェクトを誤接続してFIFO検査しないため、同一参照を確認する。

エラーメッセージには少なくとも次を含める。

- 対象Node名
- candidate index
- expected
- actualを識別できる情報

途中候補で不一致が発生した場合:

- 後続候補を処理しない。
- 後続の対象Nodeを処理しない。
- 部分的なNode結果または全体結果を返さない。

## inlink対応辞書

`BASELINE_INFORMATION_COMPLETE`で順位候補が1件以上ある対象Nodeについて、`candidate_visits`から次の一時dictを対象Node単位で一度だけ作る。

```text
inlink_name_by_visit_key:
    dict[OrderControlTvtVisitKey, str]
```

既存`preserves_inlink_fifo()`は第三引数としてPythonの`dict`を要求する。`Mapping`一般ではなく、この一時dictを`dict`として渡す。

候補ごとに同じdictを作り直さない。

`candidate_visits`の既存順を変更しない。

この一時dictを結果型へ保存しない。

candidate Visitの`inlink_name`を再計算しない。World、Vehicle、Node、Linkへ戻らない。

上流でVisitKey重複と所属が保証済みであるため、一般的な重複検査や所属再検査を繰り返さない。

ただし、FIFO検査対象の`trade_scope`内VisitKeyについてinlink名を取得できない場合は重大不整合とする。

`trade_scope`外Visitのinlink情報が同じ一時dictに存在してもよい。既存関数は検査対象VisitKeyだけを参照するため、余分キーは結果へ影響しない。余分キーを結果型へ保存しない。

## 候補ごとのFIFO材料

一つの`general_trade_rank_result`について、次を作る。

取引前:

```text
before_trade = general_trade_rank_result.trade_scope
```

取引後:

```text
after_trade = general_trade_rank_result.trade_order[
    :general_trade_rank_result.last_buyer_rank
]
```

`before_trade`と`after_trade`は、どちらも`trade_scope`に対応するVisit列でなければならない。未確定候補列全体を渡さない。`trade_scope`外VisitをFIFO材料へ追加しない。

既存`preserves_inlink_fifo()`の第一引数名は`baseline_order`、第二引数名は`trade_order`である。意味は、取引前の`trade_scope`列と取引後の同範囲列である。接続部品では位置引数として`before_trade`、`after_trade`を渡す。既存関数の引数名や実装を変更しない。

次を候補ごとに確認する。

- `before_trade`が空でない。
- `last_buyer_rank`が厳密なPythonの`int`である。
- `bool`ではない。
- `last_buyer_rank`が1以上。
- `last_buyer_rank`が`trade_order`の件数以下。
- `len(before_trade) == last_buyer_rank`。
- `len(after_trade) == last_buyer_rank`。
- `before_trade`と`after_trade`のVisitKey集合が一致する。
- `before_trade`と`after_trade`の各VisitKeyについて、`inlink_name_by_visit_key`にinlink名が存在する。

これらの不一致はFIFO違反ではなく`RuntimeError`。

順位再構成部品で保証済みの順位構造を全面的に再検証しない。次を繰り返さない。

- `trade_rank`の1からNまでの連続性。
- 買い手・売り手・非参加Visitの3分類。
- 非参加Visitの固定順位。
- 買い手と売り手の配置。
- 売り手後退。
- `trade_scope`外順位不変。
- `trade_order`全体と`trade_rank`の完全対応。

FIFO接続部品では、既存FIFO関数へ安全に渡すための材料整合だけを確認する。

## 既存`preserves_inlink_fifo()`の呼出し

各候補について、既存関数を次の材料で一度だけ呼ぶ。

```python
preserves_fifo = preserves_inlink_fifo(
    before_trade,
    after_trade,
    inlink_name_by_visit_key,
)
```

`preserves_inlink_fifo()`自体を変更しない。

同じ候補について複数回呼ばない。

`False`だった候補について別の順位を作り直し、再検査しない。

`preserves_inlink_fifo()`へ未確定候補列全体を渡さない。

`trade_scope`外VisitをFIFO材料へ追加しない。

参加MappingをFIFO関数へ渡さない。

既存関数は、対象Nodeへ向かう各inlink内の相対順だけを比較する。複数inlink間の順序変更だけでは`False`を返さない。1本でも相対順が変われば`False`を返す。参加Visitと非参加Visitを区別しない。

## TrueとFalseの扱い

既存`preserves_inlink_fifo()`の戻り値は`bool`である。戻り値が厳密なPythonの`bool`であることを確認する。判定は概念上次とする。

```text
type(preserves_fifo) is bool
```

`True`:

- FIFOを維持した候補。
- 後続の局所仮想計算へ進められる候補。
- この部品ではまだ局所仮想計算を実行しない。

`False`:

- FIFO違反。
- 正常な候補棄却。
- `RuntimeError`または`ValueError`に変換しない。
- 当該候補だけを後続対象から外す。
- 別候補の検査を継続する。
- 同じ候補の順位を作り直さない。
- 結果型には`preserves_inlink_fifo=False`として残す。
- 結果から削除しない。

厳密なPythonの`bool`以外（`1`、`0`、`numpy.bool_`、文字列、`None`など）が返された場合:

- 既存FIFO関数の契約違反または内部不整合。
- `RuntimeError`。
- 対象Node名とcandidate index、実際の型と値を含める。
- 後続候補と後続の対象Nodeを処理しない。
- 部分結果を返さない。

## 既存FIFO関数が送出する`ValueError`

FIFO接続部品が内部で組み立てた材料を既存`preserves_inlink_fifo()`へ渡した際に、`ValueError`が送出された場合は、その`ValueError`を正常な候補棄却として扱わない。

接続部品側では、生成済み上流結果間の重大不整合として`RuntimeError`へ変換する。

`RuntimeError`のメッセージには少なくとも次を含める。

- 対象Node名
- candidate index
- FIFO検査材料の重大不整合であること
- 元の`ValueError`のメッセージ

例外チェーンを維持するため、概念上次の形式を使用する。

```python
try:
    preserves_fifo = preserves_inlink_fifo(
        before_trade,
        after_trade,
        inlink_name_by_visit_key,
    )
except ValueError as error:
    raise RuntimeError(
        ...
    ) from error
```

ただし、`preserves_inlink_fifo()`が`False`を返した場合は例外変換しない。`False`は正常なFIFO違反である。

## 候補検査結果の保持

各`general_trade_rank_result`について、必ず一つの`OrderControlTvtMpCandidateFifoInspectionResult`を作る。

FIFO違反候補を`candidate_fifo_inspection_results`から削除しない。

上流候補順と一対一対応を維持する。

後続処理は、`preserves_inlink_fifo`が`True`の候補だけを選択できる。この部品では、`True`候補だけの別tupleを結果型へ重複保存しない。後続処理が必要に応じて明示的に抽出する。

## 正常な候補棄却と重大不整合

正常な候補棄却:

- `preserves_inlink_fifo()`が`False`を返す。
- 当該候補だけFIFO違反。
- 検査結果へ`False`を保存する。
- 別候補の検査を継続する。
- 例外を送出しない。

重大不整合:

- Node結果件数不一致。
- `node_name`不一致。
- `build_status`不一致。
- 想定外status。
- 順位候補数と具体的買い手候補数の不一致。
- 一般形順位結果が対応する具体的候補を同一参照保持していない。
- `before_trade`が空。
- `last_buyer_rank`の型または範囲が不正。
- `before_trade`または`after_trade`の件数が`last_buyer_rank`と不一致。
- `before_trade`と`after_trade`のVisitKey集合が不一致。
- FIFO対象Visitのinlink名がない。
- `preserves_inlink_fifo()`が`ValueError`を送出する。
- `preserves_inlink_fifo()`がPython `bool`以外を返す。

重大不整合は`RuntimeError`。

正常なFIFO違反として隠さない。

重大不整合発生後は、後続候補および後続の対象Nodeを処理せず、部分結果を返さない。

外部入力または結果クラス直接構築時の型・形式違反が将来の直接構築テストで必要になっても、既存FIFO関数の`False`を`ValueError`へ変換しない。新しい独自例外型を作らない。

## 読取専用契約

次を変更しない。

- `general_trade_rank_set_result`
- `node_trade_rank_results`
- `candidate_trade_rank_results`
- `general_trade_rank_result`
- `concrete_buyer_candidate_set_result`
- `candidate_visits`
- `trade_scope`
- `trade_order`
- `last_buyer_rank`
- concrete buyer candidate set
- その他の上流結果

`preserves_inlink_fifo()`は読取専用検査として呼ぶ。

上流関数を再実行しない。次を呼び直さない。

- `build_tvt_candidate_visit_set`
- `build_tvt_inlink_candidate_physical_orders`
- `build_tvt_mp_concrete_buyer_candidate_sets`
- `build_tvt_mp_general_trade_ranks`
- `build_tvt_trade_rank_without_nonparticipants`
- `select_right_of_entry_decision_window_visits`
- `confirm_leading_nonparticipating_decision_window_visits`
- baseline alignment
- baseline fork
- collector export

World、Vehicle、Node、Link、collector、順位台帳へ戻らない。

## 本番で再検証しない事項

次をFIFO接続部品で再検証しない。

- P−1条件。
- TVT固有可変上限N。
- `candidate_visits`の正式baseline sort。
- baseline passage timestep。
- inlink別snapshot物理順。
- prefixの物理的連続性。
- 具体的買い手候補集合の生成方法。
- 一般形順位の構築方法。
- 3分類。
- 非参加Visitの固定順位。
- 空き順位枠への買い手と売り手の配置。
- 売り手後退。
- `trade_scope`外順位不変。
- `trade_rank`全体の順位連続性。
- 候補間の重複。
- participantかnonparticipantかの再判定。
- 権利保有Visitの参加状態。

FIFO接続に必要な材料の対応と、既存FIFO関数へ渡す範囲だけを必要最小限に確認する。

## 専用テスト契約

新規専用テスト:

```text
tests_order_control_tvt_mp_fifo_inspection.py
```

既存テストのhelperを直接importしない。新規テスト内に必要なfixtureを明示的に作る。期待値を本番と同じ処理で自動生成しない。

少なくとも次を確認する。

### 公開APIと結果型

- 3つの公開frozen dataclassをimportできる。
- 公開関数をimportできる。
- 各結果型がfrozen dataclassである。
- 正確なフィールド集合。
- フィールド変更で`FrozenInstanceError`。
- 全体結果が第一入力を同一参照保持する。
- 一候補結果が一般形順位結果を同一参照保持する。
- 結果フィールド`preserves_inlink_fifo`が厳密なPython `bool`である。
- 禁止フィールドを持たない。
- `update`、`rollback`、`export`、`to_dict`等を持たない。

### status

- `BASELINE_INFORMATION_COMPLETE`かつ順位候補ありでFIFO検査。
- `BASELINE_INFORMATION_COMPLETE`かつ候補0件で正常な空tuple。
- 候補0件ではinlink辞書を作らずFIFO関数を呼ばない。
- 正式4非生成statusで空tuple。
- 正式4非生成statusではFIFO関数を呼ばない。
- 想定外statusで`RuntimeError`。
- 途中の対象Nodeの異常で部分結果を返さない。

### Nodeと候補の対応

- 3種類のNode結果の件数不一致。
- `node_name`不一致。
- `build_status`不一致。
- 順位候補数と具体的候補数の不一致。
- 同じcandidate indexで具体的候補オブジェクトの同一参照不一致。
- 内容が同じ別オブジェクトでも`RuntimeError`。
- 対応が正常なら上流候補順を維持する。
- 複数の対象Nodeで上流Node順を維持する。

### FIFO材料

- `before_trade`が`trade_scope`と同じオブジェクトまたは同じtuple内容である。
- `after_trade`が`trade_order[:last_buyer_rank]`である。
- 未確定候補列全体を渡さない。
- `trade_scope`外Visitを渡さない。
- 買い手、売り手、非参加Visitをすべて含む。
- `before_trade`と`after_trade`の件数が一致する。
- VisitKey集合が一致する。
- `candidate_visits`からinlink対応を対象Node単位で作る。
- 対象Visit全件のinlink名をFIFO関数へ提供する。
- 余分な`trade_scope`外Visitのinlink情報がdictに存在しても結果へ影響しない。

### FIFO合格

- 同一inlink内相対順を維持する候補が`True`。
- 複数inlink間のVisit順が変わっても、対象Nodeへ向かう各inlink内の相対順が同じなら`True`。
- 買い手、売り手、非参加Visitを含む正常な`True`ケース。
- `True`候補の検査結果を上流候補順で保持する。

### FIFO違反

- 買い手と売り手の同一inlink内逆転で`False`。
- 買い手と非参加Visitの逆転で`False`。
- 売り手と非参加Visitの逆転で`False`。
- 複数inlinkのうち1本だけ違反しても`False`。
- `False`で例外を出さない。
- `False`候補を結果から削除しない。
- `False`の後に続く別候補も検査する。
- 同じ`False`候補の順位を作り直さない。
- `preserves_inlink_fifo()`を一候補につき一度だけ呼ぶ。
- 全候補が`False`でも正常な結果を返す。
- `True`と`False`が混在しても上流候補順を維持する。

### 重大不整合

- `before_trade`が空。
- `last_buyer_rank`が`bool`。
- `last_buyer_rank`が非int。
- `last_buyer_rank`が0。
- `last_buyer_rank`が`trade_order`件数を超える。
- `len(before_trade)`と`last_buyer_rank`の不一致。
- `len(after_trade)`と`last_buyer_rank`の不一致。
- `before_trade`と`after_trade`のVisitKey集合不一致。
- FIFO対象VisitKeyのinlink名欠落。
- `preserves_inlink_fifo()`が`ValueError`を送出した場合に`RuntimeError`へ変換する。
- `RuntimeError`のメッセージに対象Node名、candidate index、元の`ValueError`内容を含む。
- 例外チェーンが維持される。
- FIFO関数が`1`、`0`、`numpy.bool_`、文字列、`None`等のPython `bool`以外を返した場合に`RuntimeError`。
- 途中候補の重大不整合で後続候補を処理しない。
- 途中の対象Nodeの重大不整合で後続の対象Nodeを処理しない。
- 部分的な全体結果を返さない。

内部不整合テストでは、複数の異常を混在させず、狙った検査へ到達する手書きfixtureを使用する。

### 読取専用

- 第一入力を変更しない。
- Node結果を変更しない。
- 一般形順位結果を変更しない。
- `trade_scope`を変更しない。
- `trade_order`を変更しない。
- `candidate_visits`を変更しない。
- 上流処理を再実行しない。
- World、Vehicle、Node、Link、collector、順位台帳へ戻らない。
- `preserves_inlink_fifo()`自体を変更しない。

### 呼出し回数

patch等を用いて確認する。

- 順位候補1件につき`preserves_inlink_fifo()`を1回だけ呼ぶ。
- 候補0件では0回。
- 正式非生成statusでは0回。
- `False`候補を再検査しない。
- 途中候補で重大不整合が発生した後、後続候補のFIFO関数を呼ばない。

### テスト登録

`TESTS`リストを設ける場合:

- 定義済み`test_`関数の登録漏れなし。
- 重複登録なし。
- 未知関数参照なし。
- AST確認。
- 直接実行件数を表示する。
- pytest収集件数と一致する。

既存の堅牢なテスト登録方式を参考にしてよいが、必要以上に複雑化しない。

## 今回実装しない範囲

今回の実装前仕様には、一般形順位結果のFIFO検査接続と、候補ごとのTrue/False結果保持までを含める。次は実装対象外とする。

- FIFO違反理由の詳細診断。
- 違反inlink名の保存。
- FIFO棄却数や棄却率の集計。
- True候補だけを集めた永続結果型。
- 局所仮想計算。
- 局所仮想計算未解決候補の除外。
- 経済性評価。
- 買い手価値`G`。
- 売り手必要補償`R`。
- `G >= R`判定。
- `surplus`。
- 成立候補選択。
- `surplus`同値時の買い手数比較。
- RNG。
- 支払い。
- 補償。
- 成立時の最終確定列。
- 不成立時の最終確定列。
- 情報未解決時の最終確定列。
- 確定順位ブロックへの接続。
- 上位TVT制御。
- TVT-SB。
- TVT-MH。
- TVT-SP。
- 性能最適化。
- `preserves_inlink_fifo()`の変更。
- 一般形順位再構成部品の変更。

## 可読性方針

研究用コードとして正しく動くことを最優先とする。複数の実装方法を選べる場合は、短さ、巧妙さ、高度なPythonテクニックより、Python初学者が後から処理を追いやすい、明示的で可読性の高い方法を優先する。

実装では次を分ける。

- 上流Node結果の対応確認。
- 候補結果の対応確認。
- inlink対応辞書の作成。
- `before_trade`の取得。
- `after_trade`の取得。
- FIFO材料の整合確認。
- `preserves_inlink_fifo()`の呼出し。
- `ValueError`の`RuntimeError`変換。
- `bool`戻り値の確認。
- 一候補結果の構築。
- Node結果の構築。
- 全体結果の構築。

長い内包表記、複雑な多重ジェネレーター式、巧妙なone-linerを避ける。意味の分かる中間変数と明示的なforループを使用する。helperは責務が明確な場合だけ作る。不要な一般化、抽象化、実測前の性能最適化を行わない。コメントとdocstringではPython処理だけでなく交通上の意味も説明する。「Node全体」という曖昧な表現を避ける。必要な場合は「対象Nodeへ向かう各inlink内の相対順」と書く。

この可読性方針を理由に、確定済み制度仕様、公開API、結果型、status契約、例外契約、未実装境界を変更しない。

## 実装後の次の作業

FIFO検査接続部品を実装・検証した後は、局所仮想計算、経済性評価、成立候補選択へ進む前に、実装完了記録を本ファイルと進捗メモへ残す。その後の直接作業は、`preserves_inlink_fifo=True`の候補だけを対象とする局所仮想計算接続の実装前仕様である。

# TVT-MP FIFO検査接続部品の実装完了記録

**実装完了日：2026-09-15**

本節は、上記「TVT-MP FIFO検査接続部品の実装前仕様」に対応する実装完了記録である。制度ロジックの正本は、引き続き本ファイル§20、§21、および「TVT-MP一般形順位再構成部品の実装前仕様」「TVT-MP一般形順位再構成部品の実装完了記録」、当該FIFO検査接続の実装前仕様である。実装前仕様は、実装時に用いた正本として削除・短縮・置換せず維持する。

FIFO検査接続部品の実装前仕様の保存済み・push済みコミットは`25764b8`（`Document the TVT-MP FIFO inspection connection implementation specification`）である。その保存済み仕様に従い、新規本番と専用テストを実装した。本実装完了記録時点では、新規コード・新規専用テスト・本節の追記・進捗メモ追記は、まだ`git add`、`git commit`、`git push`していない。

Copilotと利用者が、本番コード、主要テスト、Terminalでのテスト結果、テスト登録件数、空白エラー、Git状態を確認済みである。Cursor報告だけでは実装完了を確定しない。

## 新規ファイルと公開API

新規本番:

- `uxsim/order_control_tvt_mp_fifo_inspection.py`

新規専用テスト:

- `tests_order_control_tvt_mp_fifo_inspection.py`

公開関数:

- `build_tvt_mp_fifo_inspection_results`

公開frozen dataclass（3つ）:

1. `OrderControlTvtMpCandidateFifoInspectionResult`
2. `OrderControlTvtNodeMpFifoInspectionResult`
3. `OrderControlTvtMpFifoInspectionSetResult`

## 公開APIと結果型

公開関数:

```text
build_tvt_mp_fifo_inspection_results(
    general_trade_rank_set_result
)
```

- 第一入力は位置引数である。追加入力はない。
- `participates_by_visit_key`は受け取らない。
- World、Vehicle、Node、Link、collector、順位台帳は受け取らない。
- 第一入力から`candidate_visits`へ参照で到達する。
- 上流結果を変更しない。上流処理を再実行しない。

3つの結果型は、すべて公開frozen dataclassとして実装した。

`OrderControlTvtMpCandidateFifoInspectionResult`:

- `general_trade_rank_result`
- `preserves_inlink_fifo`（厳密なPython `bool`。既存公開関数`preserves_inlink_fifo()`と同名の検査票フィールドであり、関数そのものではない）

`OrderControlTvtNodeMpFifoInspectionResult`:

- `node_name`
- `build_status`
- `candidate_fifo_inspection_results`

`OrderControlTvtMpFifoInspectionSetResult`:

- `general_trade_rank_set_result`
- `node_fifo_inspection_results`

全体結果は、公開関数へ渡された第一入力を同一オブジェクト参照で保持する。一候補結果は、対応する一般形順位結果を同一オブジェクト参照で保持する。

FIFO違反理由、違反inlink名、診断ログ、True候補だけの重複tuple、False候補だけの重複tupleは保存していない。

## status別動作

FIFO検査を実行するのは、次の場合だけである。

- `BASELINE_INFORMATION_COMPLETE`
- `candidate_trade_rank_results`が1件以上

`BASELINE_INFORMATION_COMPLETE`でも順位候補0件なら正常な空結果である。この場合、inlink対応辞書を作らず、`preserves_inlink_fifo()`を呼ばず、`candidate_fifo_inspection_results`は空tupleとする。

次の正式4非生成statusではFIFO検査を行わず、空tupleを返す。

- `NOT_BUILT_NO_RIGHT_OF_ENTRY`
- `NOT_BUILT_UNRESOLVED_ARRIVALS`
- `UNRESOLVED_RIGHT_OF_ENTRY_PASSAGE`
- `UNRESOLVED_CANDIDATE_PASSAGES`

想定外statusは`RuntimeError`とする。対象Node名と実際のstatusをメッセージへ含める。重大不整合後は後続Nodeを処理せず、部分的な全体結果を返さない。

## 上流結果の対応確認

次の3種類の対象Node別結果について、件数を確認する。

- candidate Node結果
- concrete buyer candidate Node結果
- general trade rank Node結果

同じindexについて、`node_name`と`build_status`を確認する。不一致は`RuntimeError`とする。

`BASELINE_INFORMATION_COMPLETE`で順位候補が存在する対象Nodeでは、`candidate_trade_rank_results`と`concrete_buyer_candidate_sets`の件数を確認する。同じcandidate indexについて、一般形順位結果が対応する具体的買い手候補を同一オブジェクト参照で保持していることを確認する。内容が同じ別オブジェクトでは不十分であり、同一参照でなければ`RuntimeError`とする。

## inlink辞書とFIFO材料

順位候補が存在する対象Nodeについて、`candidate_visits`から次を対象Node単位で一度だけ作る。

```text
inlink_name_by_visit_key:
    dict[OrderControlTvtVisitKey, str]
```

候補ごとに作り直さない。結果型へ保存しない。

候補ごとのFIFO材料は次のとおりである。

取引前:

- `general_trade_rank_result.trade_scope`

取引後:

- `general_trade_rank_result.trade_order[:general_trade_rank_result.last_buyer_rank]`

未確定候補列全体や`trade_scope`外VisitをFIFO材料へ追加しない。買い手、売り手、非参加Visitを区別せず、`trade_scope`内の全VisitをFIFO検査対象とする。

次の材料整合を必要最小限に確認する。

- `before_trade`が空でない
- `last_buyer_rank`がboolではないPython `int`
- `last_buyer_rank`が1以上
- `last_buyer_rank`が`trade_order`件数以下
- `before_trade`と`after_trade`の件数が`last_buyer_rank`と一致
- `before_trade`と`after_trade`のVisitKey集合が一致
- 検査対象VisitKeyのinlink名が存在する

一般形順位再構成で確認済みの順位構造を全面的に再検証していない。

## 既存FIFO関数の呼出し

各候補について、既存の`preserves_inlink_fifo()`を一度だけ呼ぶ。

```python
preserves_fifo = preserves_inlink_fifo(
    before_trade,
    after_trade,
    inlink_name_by_visit_key,
)
```

`preserves_inlink_fifo()`自体は変更していない。同じ候補を複数回検査しない。`False`候補について順位を作り直さず、再検査もしない。

## True、False、非bool

既存FIFO関数の戻り値について、厳密なPythonの`bool`であることを確認する（`type(preserves_fifo) is bool`）。

`True`は、対象Nodeへ向かう各inlink内の相対順を維持した候補である。結果へ`True`として保存する。後続の局所仮想計算へ進められる候補である。この部品では局所仮想計算を実行しない。

`False`は、1本以上のinlinkで相対順が変化したFIFO違反候補である。正常な候補棄却であり、例外へ変換しない。結果から削除せず、`False`として保存する。後続候補の検査を続ける。全候補が`False`でも正常な全体結果を返す。

Python `bool`以外（`1`、`0`、`numpy.bool_`、文字列、`None`等）は`RuntimeError`とする。後続候補と後続Nodeを処理せず、部分結果を返さない。

候補検査結果は上流候補順に一対一対応している。True候補だけの別tupleは重複保存していない。

## ValueErrorの変換

接続部品が組み立てた材料を`preserves_inlink_fifo()`へ渡した結果、既存関数が`ValueError`を送出した場合は、正常なFIFO違反として扱わない。`RuntimeError`へ変換する。対象Node名、candidate index、元の`ValueError`の内容をメッセージへ含める。`raise ... from error`により例外チェーンを維持する。

`preserves_inlink_fifo()`が`False`を返した場合は例外変換しない。

## 読取専用と未実装範囲

次を変更していない。

- 第一入力
- Node結果
- 一般形順位結果
- `trade_scope`
- `trade_order`
- `candidate_visits`
- concrete buyer candidate set
- その他の上流結果

上流処理を再実行していない。World、Vehicle、Node、Link、collector、順位台帳へ戻っていない。

次は未実装のままである。

- FIFO違反理由の詳細診断
- 違反inlink名の保存
- FIFO棄却数と棄却率の集計
- True候補だけの永続結果型
- 局所仮想計算
- 局所仮想計算未解決候補の除外
- 経済性評価
- 買い手価値`G`
- 売り手必要補償`R`
- `G >= R`判定
- `surplus`
- 成立候補選択
- RNG
- 支払い
- 補償
- 成立時・不成立時・情報未解決時の最終確定列
- 確定順位ブロックへの接続
- 上位TVT制御
- TVT-SB
- TVT-MH
- TVT-SP
- 性能最適化
- 一般形順位再構成部品の変更
- `preserves_inlink_fifo()`の変更

## 確認済みテスト

Copilotと利用者がTerminalで確認済みである。

新規2ファイルの`py_compile`は成功した。

| 区分 | 結果 |
|------|------|
| 新規専用テスト直接実行 | 66 tests passed |
| 新規専用テスト pytest | 66 passed |
| pytest収集 | 66 collected |
| 定義済み`test_`関数 | 66件 |
| `TESTS`登録 | 66件（重複なし、登録漏れなし、未知参照なし） |
| 直接実行件数とpytest収集 | 一致 |

新規専用テストと既存回帰を合わせたpytestは461 passedである。

既存回帰の内訳:

- `tests_order_control_tvt_mp_general_trade_rank.py`: 132
- `tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`: 63
- `tests_order_control_tvt_trade_rank.py`: 115
- `tests_order_control_tvt_candidate_visit_set.py`: 21
- `tests_order_control_tvt_inlink_candidate_physical_order.py`: 25
- `tests_order_control_tvt_right_of_entry_selection.py`: 16
- `tests_order_control_tvt_leading_nonparticipating_confirmation.py`: 23

新規66件と既存395件を合わせて461件成功である。未追跡ファイル用diff checkにより、新規2ファイルに空白エラーがないことも確認した。

## 次の作業開始点（本部品完了後）

次の直接作業は、`preserves_inlink_fifo=True`の候補だけを対象とする候補別局所仮想計算接続部品の**実装前仕様**を確定することである。

- FIFO検査接続部品を再考しない。
- `preserves_inlink_fifo()`を変更しない。
- 一般形順位再構成を変更しない。
- 直ちに局所仮想計算を実装しない。まず既存の局所仮想計算関係の設計・部品・入力要件を確認する。
- 経済性評価、成立候補選択にはまだ進まない。

# TVT-MP候補別局所仮想計算の設計検討記録

**記録日：2026-09-18**

本節は、候補別局所仮想計算の**設計検討記録**である。**完全な実装前仕様ではない。** 公開API、結果型、新規モジュール名、専用テスト契約を確定していない。Python実装と専用テストは未着手である。実装済み、テスト済み、コミット済みとは記載しない。

FIFO検査接続部品の保存済み・push済み実装コミットは`33e6101`（`Implement and document the TVT-MP FIFO inspection connection`）である。本節はその後段である候補別局所仮想計算の調査・議論を失わないための記録である。新しい実装コミットhashを推測しない。本節および進捗メモ追記は、記録時点ではまだ`git add`、`git commit`、`git push`していない。

本節では、次を混同しない。

1. 確定済みの制度
2. 既存コードとメモから確認した事実
3. 今回採用した基本方針
4. 現在の有力案
5. 未確定事項
6. 今後の調査事項

有力案を実装前仕様または実装済みと記載しない。未確定事項を独自判断で確定しない。制度ロジックの正本は、引き続き旧メモ§8、§16、§25.25.34、本ファイル§22、FIFO検査接続の実装前仕様および実装完了記録である。既存の実装前仕様、実装完了記録、制度記録は削除・短縮・置換しない。

## 非技術的な目的

候補別局所仮想計算では、一つの対象Nodeについて、一つの具体的TVT候補を仮に採用した場合に、買い手や売り手がいつ交差点を通過できるかを予測する。

取引後順位は、必ずその順番どおりに実際に通過できることを保証するものではなく、その順位で先に通過を試す権利を表す。

実際の通過可否は、到着状態、同一inlink内の物理先頭、outlinkの空間、各容量、方向切替クリアランス等に左右される。

全World baselineでの予想通過timestepと、候補別局所仮想計算での予想通過timestepを比較し、後続の経済性評価に必要な時間短縮と待ち時間増加を求める。

局所仮想計算は、将来の実Worldを完全に予言または再現する計算ではなく、同じ対象Nodeの複数候補を比較するための局所的な予測である。

## 確定済みの制度

旧メモと継続版メモから、候補別局所仮想計算の前提として既に確定している制度は次である。本節で新しく考え直さない。

### 権利保有車両の権利内容

旧メモ§8.2：権利保有車両が持つのは、**最初に通過を試す権利**である。実際に最初に通過できることを保証しない。通過できない場合は、既存FCFSと同様に、通過不能理由に応じて後順位Vehicleへ通過機会を回すことがある。

この権利内容は、候補の`trade_order`を「必ずその順で通過する確定列」ではなく、「通過を試す優先順位」として扱うことと整合する。

### 三つの計算世界と局所候補未解決時の扱い

旧メモ§25.25.34および本ファイル§22：

- 全World baseline仮想計算、Node別・具体的候補別の局所仮想計算、実Worldを区別する。
- 時点`T`の全World baselineは、時点`T-1`までのTVT結果を引き継ぎ、時点`T`では新しいTVTを追加しない比較基準である。
- 候補別局所仮想計算は、一つの対象Nodeにおいて一つの具体的TVT候補を仮に実行した場合の到着・通過等を予測する。
- 実Worldは、全対象Nodeがそれぞれ最終的に選択したTVTを反映して進む。
- 同一timestepでは各対象Nodeが共通の全World baselineを参照し、それぞれ独立に候補を局所評価する。各対象Nodeで最大1件のTVTを選び、全対象Nodeの評価完了後に一括して実Worldへ登録する構想である（旧メモ§16.3）。
- 局所計算である以上、他Nodeで同時に成立するTVTの将来影響を完全には予測できない。この差は予測値と実現値の差として事後評価する（旧メモ§16.4）。
- 入力候補はFIFOを満たした具体的候補である。FIFO検査接続実装後は、`preserves_inlink_fifo=True`の候補である。
- 一部候補だけlocal horizon内に必要情報を取得できなければ、その候補だけを評価対象から除外する。他の解決済み候補は維持する。
- 全候補が未解決なら、経済条件による不成立とは別に、局所仮想計算未解決によるTVT不成立とする。
- 不足情報を任意推定値、利益0、surplus 0等で補わない。未解決のまま採用しない。未解決を自動的に経済的不成立と分類しない。

### 全Worldではなく局所仮想計算にする制度上の理由

同じ実時点`T`に、複数の対象NodeでTVTが検討され得る。

一つの対象Nodeの一つの候補だけを全Worldへ適用して仮想計算しても、他の対象Nodeで最終的にどのTVT候補が採用されるかはまだ決まっていない。

そのため、一つの候補だけを反映した候補別全World計算は、実際に進む将来Worldを正確に表すものではない。

候補別局所仮想計算は、実World全体の将来を完全再現するためではなく、対象Nodeにおける候補間比較のために行う。

各対象Nodeで候補評価と候補選択が終わった後に、全対象Nodeの採用結果を実Worldへまとめて反映する。

局所仮想計算を採用する理由を、単なる計算負荷削減だけにしない。計算負荷が大きいことも事実であるが、制度上の第一の理由は、他Nodeの未確定TVTを含む全World将来を候補単位で正確に表せないことである。

## 既存コードとメモから確認した事実

### BATCH Level 2局所仮想計算の目的

既存コード`uxsim/order_control_batch_level_2_reference.py`およびBATCH設計メモから確認した。

BATCH Level 2の主目的:

- trigger Vehicleの仮想通過時刻`t_virtual_trigger`を求める
- その時刻を使ってBATCH形成の`t_trigger`を補正する
- 既存BATCH service queue、trigger Vehicle、容量、clearance、outlink入口空間等を模倣する
- trigger Vehicleが通過した時点で早期終了する
- virtual horizon内にtriggerが通過しなければ`resolved=False`
- 本体ではunresolved時にLevel 1値へfallbackする
- trigger以外の関係Vehicle全員の最終通過時刻を取得することが目的ではない

BATCH mimic World:

- 対象Node
- 対象Nodeのinlink
- 対象Nodeのoutlink
- dummy upstream Node
- sink Node
- BATCH service queue
- trigger用pseudo service unit
- snapshot時点の車両・容量状態

BATCHでは、dummy upstream Nodeから新しいVehicleを生成しない。Vehicle生成なし、新規流入なし、signalなし、order-controlなしである。

BATCHでは、outlink終端をsink Nodeとし、標準end-tripでVehicleを除去する。

BATCHではtrigger通過時に即座に終了し、同じoffset内のその後のVehicle前進やsink処理も行わない。

この目的と早期終了のため、BATCHのsink境界がTVTより影響しにくい可能性がある。ただし、「影響が必ず小さい」と断定しない。

BATCHでは、一つのservice unitとして登録されたVehicleのまとまりを、正式service queueの順序に従って処理する。処理対象service unitの先頭Vehicleが対象Nodeへ未到着の場合、そのVehicleを飛ばして同じservice unit内の後続Vehicleを処理したり、別inlinkの後続service unitへ移ったりせず、そのtimestepのservice処理を停止する。これにより、現在のservice unitに含まれるVehicleのまとまりを、後続service unitより先に処理する順序を維持する。

BATCH Level 2の未到着Vehicle用kind Bでは、Vehicle IDによる仮想outlink選択がある。snapshot時点で`route_next_link`が対象Nodeから始まる到着済みVehicleはkind Aとして固定outlinkを使う。

### TVT局所仮想計算の目的（BATCHとの違い）

TVTでは:

- 一つの対象Node、一つの具体的候補ごとに別の局所仮想計算を行う
- 入力候補は`preserves_inlink_fifo=True`の候補だけである
- 候補の取引後順位`trade_order`を前提とする
- baseline保存済み`route_next_link_name`を使う
- 買い手、売り手等、経済性評価に必要な関係Visitの予想通過timestepを取得する
- 関係Visit全員について必要情報が揃うまで計算する
- 一部候補だけlocal horizon内に解決できなければ、その候補だけを除外する
- 他の解決済み候補は維持する
- 全候補未解決なら、経済条件による不成立とは別に、局所仮想計算未解決によるTVT不成立とする
- 不足情報を任意推定値、0、利益0、surplus 0等で補わない

BATCHは主としてtrigger Vehicle 1台の通過時刻取得が目的である。

TVTは、候補の経済評価に必要な複数Visitの通過時刻取得が目的である。

このため、BATCHの局所World構築と交通進行は参考にできるが、BATCH service queue、trigger用pseudo unit、Level 1 fallback、trigger通過時早期終了をそのままTVTへ適用しない。

TVTは、複数Vehicleを一つのBATCHとしてまとめて通過させる制度ではない。そのため、BATCHの未到着待機規則をそのままTVTへ適用しない。

### FCFSから確認した通過規則

既存`Node.transfer_fcfs_clearance()`およびFCFSメモから確認した。

FCFSでは、各timestepに到着済みVehicleを現在Visitの固定順位キーで並べる。

固定順位キー:

- `arrival_time`
- `arrival_tiebreaker`
- Vehicle ID

クリアランス未充足:

- `break`
- 後順位Vehicleを検討しない
- そのtimestepの走査を終了する

クリアランス不要または充足済みであるが、物理・容量条件を満たさない:

- `continue`
- 同じtimestepで後順位Vehicleを検討する

物理・容量条件には少なくとも次が含まれる。

- inlinkの物理先頭である
- outlinkに入口空間がある
- `outlink.capacity_in_remain`
- `inlink.capacity_out_remain`
- `Node.flow_capacity_remain`

次のtimestepでは、未通過Vehicleを同じ固定FCFS順位で再び先頭から評価する。

クリアランス待ちVehicleに新しい予約順位を与えない。

クリアランス未充足で`break`する理由:

- 後順位の別方向Vehicleを通すと、`last_order_control_inlink`と`last_order_control_entry_timestep`が更新される
- その結果、先順位Vehicleの方向切替クリアランスが繰り返し必要となる
- 先順位Vehicleが長時間または際限なく通過できなくなる可能性がある
- FCFSでは交通効率だけでなく先順位優先を守るため、クリアランス未充足時には後順位へ進まない

具体例:

正式順位:

```text
A → B
```

timestep T:

- Aは容量不足で`continue`
- Bは方向切替クリアランス未充足で`break`
- 後順位は検討しない

timestep T+1:

- 再び正式順位先頭のAから評価する
- BがTにクリアランス待ちになったことを理由に、BをAより上位へ予約しない
- Aが容量回復済みならAが先に通過する
- Bのクリアランス待ちはB固有の予約権ではなく、Tに後順位を通さないための停止条件である

一台が通過した後も、残る候補の走査を続ける。同じinlinkの連続通過では方向切替クリアランスは不要であり、容量等を満たせば同じtimestep内に続けて通過できる。異なるinlinkでは、直前の通過により`last_order_control_inlink`と`last_order_control_entry_timestep`が現在時刻へ更新されるため、同じtimestep内では方向切替クリアランスを満たさない。

### `route_next_link_name`

`OrderControlTvtCandidateVisit`は`route_next_link_name: str`を保持する。空でない文字列を要求する。

snapshot時点で到着済みのVisit:

- `route_next_link`が対象Nodeから始まるLinkであることをsnapshot登録時に確認する
- `route_next_link.name`を保存する

snapshot時点で未到着のVisit:

- snapshot登録時は`route_next_link_name=None`
- 全World baselineで対象Nodeへ到着する前に`route_next_link_choice()`が実行される
- その後、選択済み`route_next_link.name`がcollectorへ記録される
- candidate Visitになる段階では、空でない`route_next_link_name`を要求する

### baseline driverと`OrderControlBaselineForkResult`

既存`OrderControlBaselineForkResult`は次を保持する。

- `collector`
- `target_node_names`
- `baseline_timestep_T`
- `configured_horizon_steps`
- `fork_steps_executed`
- `final_fork_timestep`
- `registered_visit_count`
- `inlink_physical_orders`

`OrderControlBaselineForkResult`は`fork_W`を保持しない。

snapshot固定Visitが1件以上ある通常経路では、`configured_horizon_steps`全体を実行する。必要情報が途中で揃っても早期終了しない。実行後、設定horizonだけ進んだことを検証する。

登録Visitが0件の空経路だけはforwardせず、`fork_steps_executed=0`である。TVT候補が形成される正常経路では、通常この空経路から局所計算へ進まない。

horizonは可変値である。旧メモは初期検討として50 timestepを中心に述べ、30、50、100などの比較と未解決率の測定が必要としている。30または50は過去の例示または検討例にすぎない。30または50を正式値として確定していない。30または50を上限としていない。正式な研究条件は未確定である。

既存baseline collectorは、主としてsnapshot固定Visitの到着・通過情報を記録する。既存コードには少なくとも次の接続がある。

- `prepare_baseline_passage_recording()`
- `apply_baseline_passage_timestep()`
- `record_baseline_arrival()`

outlink終端境界のactive timestep数と総流出台数は、現時点では正式結果として保存されていない。baseline forward終了後に`fork_W`を参照して後から取得することもできない。

## 今回採用した基本方針

次は、今回の議論で採用した通過試行順の基本方針である。局所仮想計算全体の完全仕様が確定したとは記載しない。公開API、結果型、mimic World範囲、境界処理は未確定のままである。

### TVT通過試行順

各timestepで、未通過Visitを固定された`trade_order`順に確認する。

未到着Visit:

- そのtimestepの走査では一時的にスキップする
- 後順位Visitを検討する
- 未到着を理由に`trade_order`を書き換えない
- 次のtimestepでは再び元の`trade_order`順で評価する

inlinkの物理先頭でないVisit:

- そのtimestepの走査では一時的にスキップする
- 後順位Visitを検討する

outlink閉塞または容量不足:

- そのtimestepの走査では一時的にスキップする
- 後順位Visitを検討する

対象となる制約:

- outlink入口空間
- outlink流入容量
- inlink流出容量
- 対象Node容量
- inlink物理先頭
- その他、既存UXsimで交差点通過に必要な物理条件

クリアランス未充足:

- 後順位Visitへ進まない
- そのtimestepの走査を終了する
- 次のtimestepでは、残る未通過Visitを元の`trade_order`順に先頭から再評価する
- クリアランス待ちVisitへ別の予約順位を与えない

通過可能:

- 保存済み`route_next_link_name`に対応するoutlinkへ通過させる
- 通過timestepを記録する
- 最終通過inlinkと最終通過timestepを更新する
- 残る`trade_order`の走査を続ける

一時的なスキップは、正式な取引後順位の変更ではない。

`trade_order`は、通過を試す優先順位である。

局所仮想計算上の実通過順は、到着、物理条件、容量、clearance等により`trade_order`と異なり得る。

### 同じtimestep内の複数通過

一台が通過した後も、残る`trade_order`の走査を続ける。

次のVisitが同じinlinkである場合:

- 方向切替クリアランスは不要
- 到着済み、物理先頭、容量等の条件を満たせば同じtimestep内に続けて通過できる
- 一台ごとに強制的に1 timestep待たせない

次のVisitが異なるinlinkである場合:

- 直前の通過により`last_order_control_inlink`と`last_order_control_entry_timestep`が現在時刻へ更新される
- 同じtimestep内では方向切替クリアランスを満たさない
- クリアランス未充足として走査を終了する

同じinlinkの次順位Visitが容量等で通れず、その後順位が別inlinkである場合:

- 同じinlinkの容量不能Visitは一時スキップできる
- ただし、別inlinkのVisitには方向切替クリアランスを別途適用する
- クリアランス未充足なら、そのtimestepの走査を終了する

### 未到着Visit（BATCHとの違い）

TVTでは、順位が付いているが対象Nodeへ未到着のVisitを、そのtimestepに物理的に通過できないVisitとして一時スキップする。

別inlinkの後順位Visitが到着済みで通過可能なら、そのVisitを検討できる。

同じinlinkの後順位Visitは、通常は未到着先順位Visitより物理的に後方にいるため、物理先頭条件によって通過できない。

この処理によって同一inlink FIFOを破らない。

### `route_next_link`の使用方針

TVT局所仮想計算では:

- baseline保存済み`route_next_link_name`を使用する
- 局所計算中に`route_next_link_choice()`を呼び直さない
- baseline保存済みの進路に従って直進、右折、左折させる
- BATCHの未到着Vehicle用kind BやVehicle IDによる仮想outlink選択をそのまま使用しない

### horizonの扱い

horizonは可変値である。30または50に限定しない。30または50を正式値または上限としない。計算負荷が許せば100以上も試す。将来さらに大きな値を試す可能性も排除しない。正式な研究条件は未確定である。horizon感度分析を可能にする。

一つの実験条件では、全World baselineと候補別局所仮想計算に同じhorizon値を使用する。

局所仮想計算のhorizonは、baseline側の`configured_horizon_steps`を参照する方向が有力である。局所計算へ別のhorizon値を重複して自由入力する設計は、有力案とはしない。ただし、公開APIと具体的な値の受渡し方法は未確定である。

## 現在の有力案

次は現在の有力案である。正式確定済み、実装前仕様完成、実装済みとは記載しない。

### 局所mimic Worldの対象範囲

実時点`T`を開始点として、一つの対象Node、一つの具体的候補ごとに局所mimic Worldを作る。

局所mimic Worldへ含める有力な範囲:

- 対象Node
- 対象Nodeへ接続する全inlink
- 対象Nodeから出る全outlink
- 時点`T`に全inlink上に存在する全Vehicle
- 時点`T`に全outlink上に存在する全Vehicle
- Node、inlink、outlinkの容量と残容量
- Vehicleの位置
- 速度
- 車線
- leaderとfollower
- `move_remain`
- `link_arrival_time`
- その他、既存BATCH mimic Worldが交通状態再現に使用する必要情報
- 最終通過inlink
- 最終通過timestep

候補Visitだけをmimic Worldへ含める方式は、交通状態再現漏れの可能性があるため、現時点の有力案ではない。

ただし、mimic Worldへ含めた全VehicleへTVT順位を与えるわけではない。

次を区別する。

TVTの仮想サービス順位を持つVisit:

- 候補の`trade_order`に含まれるVisit

交通状態再現のためだけに含めるVehicle:

- car-following
- inlink物理順
- outlink混雑
- outlink入口空間
- 容量消費
- その他の物理交通状態へ影響するVehicle

旧メモ§16.2は、局所仮想計算の対象範囲を対象Nodeの全inlinkと全outlinkを基本とすると既に述べている。本有力案はその記録と整合する。

### outlink終端の条件付き平均境界サービス

BATCHの単純sinkをTVTへそのまま適用する案は保留する。

理由:

- BATCHはtrigger Vehicleが対象Nodeを通過した時点で早期終了する
- TVTでは、経済評価に必要な複数の関係Visitの通過timestepが揃うまで計算する
- 早く対象Nodeを通過したVehicleがoutlinkを長く走り、局所計算終了前に終端へ到達する可能性が高まる
- 終端で無条件にend-tripさせると、outlink空間が実Worldより早く回復する可能性がある
- 後続Visitの予想通過timestepを楽観化する可能性がある
- 時間短縮、待ち時間増加、経済評価、候補選択へ影響し得る

このため、TVTではoutlink終端境界の処理を別途設計する必要がある。

全World baselineの設定horizon全体について、対象Nodeの各outlinkごとに次を観測する有力案である。

1. 当該outlinkの終端Nodeで、transfer処理直前に、当該outlink由来の`incoming_vehicles`が1台以上存在したtimestep数
2. 当該outlinkから終端Nodeを実際に通過した総Vehicle数

観測時点は、終端Nodeのtransfer処理直前に固定する方針である。

**2026-09-19更新注記：** 上記の観測方針は、2026-09-18時点の有力案である。activeの確定定義、途中通過Vehicleに限定した集計、Vehicle参照方式による実流出台数、`cum_departure`差を正本にしないこと、共通`exec_simulation()` hook、専用observerは、後続の「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」を最新とする。条件付き平均境界サービス方式そのものの正式採用、平均率の保存場所、局所適用処理は、引き続き有力案であり未確定である。

同一Vehicleが複数timestep待機した場合は、複数のactive timestepとして数える。

これはVehicle数ではなく、流出需要が存在した時間を分母にするためである。

用語候補:

- `downstream_active_timestep_count`
- `downstream_transferred_vehicle_count`
- `downstream_mean_service_rate`

正式な名称は未確定である。

条件付き平均流出率:

```text
downstream_mean_service_rate
=
downstream_transferred_vehicle_count
/
downstream_active_timestep_count
```

baselineのtimestep別流出台数時系列を、そのまま局所候補へ再生しない。

理由:

- baselineと局所候補では対象Nodeから各outlinkへVehicleが入る時刻と順序が変わる
- baseline固有の時間配置を局所候補へ強制する理由がない
- horizon全体またはactive timestep全体の平均により、瞬間的な有利・不利を平準化する
- 局所候補固有の終端到着時刻に応じて境界サービスを使えるようにする

保存済み`route_next_link_name`はbaselineと局所候補で共通である。

そのため、outlink別の総需要構成には一定期間で概算的な同等性が期待できる可能性がある。

ただし、horizon内のoutlink別進入台数が必ず同じとは断定しない。

### 流出許可残高

局所仮想計算では、各outlinkについて流出許可残高を持つ有力案である。

初期残高:

```text
0
```

各timestep:

```text
流出許可残高
=
前timestepからの残高
+
downstream_mean_service_rate
```

例:

平均流出率1.46の場合

最初のtimestep:

- 残高1.46
- 最大1台分を使用可能
- 1台流出したら残高0.46

次のtimestep:

- 0.46 + 1.46 = 1.92
- 最大1台分を使用可能
- 1台流出したら残高0.92

次のtimestep:

- 0.92 + 1.46 = 2.38
- 最大2台分を使用可能

最初のtimestepに終端待機Vehicleがおらず、1台も流出しなかった場合:

- 残高1.46を維持
- 次のtimestepに1.46を加え、残高2.92
- 最大2台分を使用可能

小数部分の繰越しは必須である。

未使用の整数部分も含め、残高は次のtimestepへ繰り越す有力案である。

無期限繰越しを認める方向で検討している。無期限残高繰越しを、無制約の一括流出と混同しない。

ただし、流出許可残高だけで一つのtimestepの実流出台数を決めない。

### 一つのtimestepの流出台数制限

一つのtimestepに実際に流出させる台数は、次のすべてが許す範囲とする有力案である。

- 流出許可残高の整数台数分
- outlink終端で待機しているVehicle数
- outlinkの流出容量
- 終端Nodeの容量
- `DELTAN`
- その他、既存UXsimにおいて終端Node通過に必要な物理条件

独立した人工的なburst上限を新設する案を基本としない。

既存のoutlink流出容量と終端Node容量を、timestep別の物理上限として使用する方向である。

このため、流出許可残高が20台分あっても、outlink流出容量と終端Node容量が2台分しか許さなければ、そのtimestepでは最大2台だけ流出させる。

使用しなかった18台分は残高に残る。

大きな残高は、局所計算内でそれまで下流境界サービスを十分使用していなかったことを表す。

その後に流出需要が生じた場合、既存物理容量の範囲内で速やかに流出させられることには、境界近似として意味がある。

ただし、残高を実Worldで物理的な容量が保存されたものとは説明しない。

baselineから推定した平均的な境界サービス機会を、局所候補固有の需要時刻に合わせて再配分する近似とする。

### 条件付き平均流出率の場合分け

active timestep数が1以上で、総流出台数が1台以上:

- 条件付き平均流出率を計算する
- 局所計算の流出許可残高へ毎timestep加算する

active timestep数が1以上で、総流出台数が0:

- baselineの共通horizon中に終端待機Vehicleが存在したが、一台も流出しなかった
- 観測した共通horizon内では下流境界サービス率0とする
- 局所仮想計算でも同じhorizon内は境界閉塞として扱う
- horizon後も永続閉塞すると断定するものではない

active timestep数が0:

- baseline horizon中、終端Nodeのtransfer直前に当該outlink由来の`incoming_vehicles`が一度も存在しなかった
- 下流境界待ちは観測されていない
- 境界サービス能力そのものを直接観測できたわけではない
- ただし、horizon全体で終端待ちが生じなかったことは、outlink負荷が小さい、またはhorizon中に下流混雑が軽減した可能性を示唆する
- 初期案として制約付きsinkへfallbackする

「下流混雑がないことを確認した」とは記載しない。「下流境界待ちが観測されなかったため、制約付きsinkを使用する近似」と記載する。

### active timestepが0の場合の制約付きsink

active timestep数が0の場合、無制約sinkではなく制約付きsinkを使う有力案である。

一つのtimestepのsink台数は次で制限する。

- outlink終端で待機しているVehicle数
- outlinkの流出容量
- 終端Nodeの容量
- `DELTAN`
- その他、既存UXsimの物理条件

下流Linkの流入容量は使用しない。

理由:

- active timestepが0の場合にsink fallbackを使うのは、baseline horizon中に終端待ちが観測されず、下流側が比較的空いているとみなす近似だからである
- 局所Worldに実在する下流Linkを追加しない限り、下流Linkの流入容量を形式的に持ち込まない
- sink扱いと下流Link流入容量制約を混在させない

### 条件付き平均流出率の意味

baselineで条件付き平均1.46台が実現した場合:

- baseline条件下で、active timestep当たり平均1.46台の流出が実際に実現したことは事実である
- これを、局所仮想計算の近似的な下流境界サービス率として使う
- 瞬間ごとに最低1.46台の通過を物理的に保証する意味ではない
- 潜在容量そのものと断定しない
- baselineで観測された期間実績から、局所境界の平均サービス条件を近似する

このような仮想計算では誤差を完全に避けられない。

より同程度に実装可能で、局所性を保ち、明らかに優れた代替方式がない場合には、平均化による誤差は近似として引き受ける。

誤差が存在することだけを理由に、この方式を否定しない。

ただし、研究分析で境界近似の限界やhorizon感度を検討できる余地を残す。

### 終端流出要求の詳細化

分母を単純な全horizon timestep数にするより、終端Nodeのtransfer直前に`incoming_vehicles`が存在したactive timestep数にする方が、流出需要がなかった時間を除外できる。

さらに厳密に、

- 物理先頭である
- 到着直後ではない
- 実際に流出要求可能である
- 下流進路が有効である

等を確認する案も考えられる。

しかし、初期方式では実装負担に対する精度向上が限定的である可能性がある。

理由:

- 物理先頭でないVehicleがいる場合、通常は前方Vehicleが存在する
- 到着直後に処理されなくても次のtimestepには通過検討対象となる
- trip-end Vehicleは現在の研究対象外である
- 長めのhorizon平均では1 timestep単位の差が平均上小さくなる可能性がある

したがって、初期案では、

- transfer処理直前に当該outlink由来の`incoming_vehicles`が1台以上存在したか

をactiveの定義とする方向である。

ただし、コード上の観測位置と既存`Node.transfer()`実行順をさらに確認してから正式確定する。

**2026-09-19更新注記：** 上記は2026-09-18時点の検討である。当時の「trip-end Vehicleは研究対象外である」は、旧メモ§1.3の研究シナリオ前提を指す。これを、「監視対象outlink上で目的地到着Vehicleが存在しない」または「端点Nodeが途中通過されない」ことのコード保証として読まない。最新整理では、Nodeを端点・内部で一律分類せず、Vehicleごとに目的地到着か途中通過かを判定する。目的地到着Vehicleはactiveと実流出台数の集計対象外である。途中通過Vehicleだけを集計する。観測位置と実流出台数の数え方は、後続の「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」で確定した。

## inlink始端境界（未確定）

BATCHでは:

- dummy upstream Node
- Vehicle生成なし
- 新規流入なし
- signalなし
- order-controlなし

TVTでも同じ方式を使う案はあるが、まだ正式確定していない。inlink始端からの新規流入なしを確定事項と記載しない。

新規流入なしは楽観的となる可能性がある。

例:

- inlink Xとinlink Yがある
- Y上のTVT順位保有Visitが早くまとめて通過する
- 実Worldでは時点`T`以後にY始端から新しいVehicleが進入する
- そのVehicleが対象Nodeへ到着し、X上の残るTVT順位保有Visitの通過、方向切替、clearance等へ影響する可能性がある
- 局所計算で新規流入を無視すると、この影響を捨象する

ただし、新規Vehicleには当該候補の`trade_order`がないため、局所計算へ入れる場合には次の制度設計が必要になる。

- TVT順位保有Visitと新規流入Vehicleの優先関係
- 新規流入Vehicleをどの順位へ置くか
- baseline到着順位を使うか
- clearanceへどう影響させるか
- `route_next_link`をどう与えるか
- 必要なVehicle流入情報をbaselineからどう取得するか

影響が限定的かもしれないという印象はあるが、根拠なく確定しない。

inlink始端からの新規流入を再現するか、捨象するかは未確定事項として残す。

## 未確定事項

少なくとも次は未確定である。独自判断で確定しない。

- TVT局所仮想計算の具体的な公開API
- 結果型
- 新規本番モジュール名
- 専用テスト名
- local horizonの正式な実験値
- horizon設定の受渡し方法
- 局所計算へ必要な全当事者Visitの厳密な範囲
- 買い手と売り手以外の非参加Visitについて通過timestep取得が必要か
- 局所mimic Worldへ含めるVehicleの最終範囲
- inlink始端から`T`以後の新規流入を再現するか
- 新規流入Vehicleと`trade_order`保有Visitのサービス優先関係
- outlink終端の条件付き平均境界方式の正式採用
- active timestepの厳密な観測位置
- baseline実流出台数の計測方法
- 条件付き平均率と流出許可残高のデータ型
- `DELTAN`が1以外の場合の台数表現
- 複数車線への将来拡張
- 無期限残高の初期化、候補間独立性、結果保存
- 制約付きsinkの具体的実装
- baseline境界観測の保存場所
- 局所計算のresolved条件
- unresolved理由の形式
- diagnostic情報
- 軽量カウンター
- 性能測定
- 精度検証方式
- horizon感度分析
- 境界近似の感度分析
- 局所予測と実World実績の比較方法

baseline境界観測について、次もまだ未確定である。

- 既存`OrderControlBaselineCollector`へ統合するか
- 別の下流境界観測collectorを作るか
- `OrderControlBaselineForkResult`へ直接保存するか
- 対象Node、outlink、終端Nodeのキー設計
- 観測対象を全target Nodeの全outlinkとするか
- 観測開始・終了の厳密な位置
- 終端Nodeのtransfer前後で流出台数をどう計測するか
- 複数inlinkが同じ終端Nodeへ入る場合のoutlink別集計
- 同一timestepに複数台流出した場合の集計

将来の実装には、baseline実行中に終端境界を観測して結果へ受け渡す仕組みが必要である。観測機能自体はまだ存在しない。

**2026-09-19更新注記：** 上記未確定一覧のうち、次は後続の「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」で基本設計として確定した。当時の未確定一覧は削除せず残す。

- active timestepの観測位置は、終端`Node.transfer()`直前である
- 実流出台数の正本は、transfer直前に保持した途中通過Vehicle参照が、transfer後に元のoutlinkを離れた数である
- `cum_departure`差は正式台数の正本にしない
- TVT初期研究範囲では`DELTAN=1`を制度上の前提とする。検証位置と例外文は未確定である
- 下流境界観測は既存Visit collectorへ混在させず、専用observerと独立した結果として返す方向である
- 監視対象は各TVT対象Nodeの実在outlinkであり、終端Nodeの制御方式によらず共通観測する

条件付き平均境界方式の正式採用、平均率の保存場所、局所適用処理、公開API、結果型名、例外契約は引き続き未確定である。

## 採用していない案

現時点で第一候補としない案と理由。永久に排除したとは記載しない。

- 候補ごとに全Worldを計算する方式
  - 他NodeのTVT結果が未確定なので、実際の将来Worldを正確に表さない
  - 計算負荷も大きい
- BATCHの単純sinkを無条件にTVTへ流用する方式
  - TVTでは複数当事者の通過確認まで計算するため、sinkの楽観影響が大きくなる可能性
- baselineのtimestep別下流流出台数を同じ時系列で再生する方式
  - baselineと局所候補でoutlink終端到着時刻と構成が変わる
  - baseline固有の時間配置を局所候補へ固定する理由がない
  - 平均により瞬間変動を平準化する方が今回の目的に合う
- 独立した人工的なburst上限を別パラメータとして追加する方式
  - まず既存outlink流出容量と終端Node容量を物理上限として利用する方が明確

## 今回実装しない範囲

今回は次を実装しない。Python実装済みまたはテスト済みとは記載しない。

- baseline終端境界観測
- collector変更
- baseline driver変更
- `Node.transfer()`変更
- 局所mimic World
- TVT仮想サービス処理
- 流出許可残高
- 条件付き平均流出率
- 制約付きsink
- inlink始端の新規流入
- 局所仮想計算結果型
- unresolved判定
- 経済性評価
- `G`
- `R`
- `surplus`
- 成立候補選択
- 実Worldへの反映
- カウンター
- 診断ログ
- 性能最適化

## 次の調査開始点

次の直接作業は、完全な実装前仕様の作成ではない。

次の直接作業は、全World baseline実行中に、各対象Nodeの各outlinkについて、

- 終端Nodeのtransfer処理直前のactive状態
- 当該outlinkから終端Nodeを実際に通過した台数

をどこで、どの処理順で、どの単位で観測できるかを調査することである。

具体的には次を確認する。

- `Node.transfer()`の実行順
- 標準Nodeで`incoming_vehicles`がいつ作られ、いつclearされるか
- 終端Nodeのtransfer直前へ観測hookを置けるか
- transfer前後の差からoutlink別流出台数を数えられるか
- 同一Nodeへ複数inlinkが接続する場合にoutlink別の由来を識別できるか
- existing baseline collectorへ統合する責任範囲
- 別collectorまたは観測結果型の必要性
- 実Worldへ影響しないこと
- baselineの設定horizon全体を観測できること

この調査が終わるまでは、完全な実装前仕様を作らない。FIFO検査接続部品を再考しない。`preserves_inlink_fifo()`を変更しない。一般形順位再構成を変更しない。直ちに局所仮想計算を実装しない。経済性評価、成立候補選択には進まない。

**2026-09-19更新注記：** 上記「次の調査開始点」は2026-09-18時点の記録である。その調査は実施済みである。調査結果と確定した基本設計は、直後の「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」を最新とする。

## 2026-09-19更新：下流境界観測の調査結果と基本設計の確定

記録日：2026-09-19

本更新節は、全World baselineにおけるoutlink終端境界観測について、調査結果と確定した基本設計を保存する。

- 今回は下流境界観測に関する基本設計を確定した。
- TVT局所仮想計算全体の完全な実装前仕様を確定したわけではない。
- Python実装と専用テストは未着手である。
- Cursor Grok 4.6の調査報告だけで確定せず、既存コードとTerminal出力による独立確認を行った。
- 今回のMarkdown変更は記録時点では未コミットである。
- 保存済み最新の局所仮想計算設計検討コミットは`5dd4be9`である。本更新節はその後の追記である。
- 公開API、クラス名、フィールド名、例外契約、モジュール名、テスト名は、本節で独自判断して確定しない。

前回2026-09-18の設計検討記録は削除しない。前回記録のうち、active観測方針、条件付き平均境界サービス、BATCH式sink、trip-end研究対象外、collector保存場所などは、当時の検討状態である。本更新節が下流境界観測の最新正本である。条件付き平均境界サービス方式そのものの正式採用は、引き続き有力案であり、本節でも正式採用とは記載しない。

### 非技術的な説明

TVT対象交差点から出た道路の先が混雑していると、道路上の車両が先へ進めず、対象交差点から新しいVehicleを受け入れにくくなる。

その影響を局所仮想計算へ反映するため、全World baselineで、対象交差点から出る各道路の終端において、次を観測する。

- 先へ進もうとするVehicleが待っていた時間
- 実際に先へ進めたVehicle数

目的地へ到着してそこで走行を終えるVehicleと、さらに先へ進む途中通過Vehicleは、同じNodeへ到着しても処理が異なる。

目的地到着Vehicleは通常どおり走行を終える。

平均的な下流境界サービス制約を適用するのは、さらに先へ進もうとする途中通過Vehicleだけである。

### 確認済みコード事実と設計契約の位置づけ

本節のコード事実は、少なくとも次を実際に開いて確認した。

- `uxsim/uxsim.py`
- `uxsim/order_control_baseline_driver.py`
- `uxsim/order_control_baseline_collector.py`
- `uxsim/order_control_baseline_snapshot.py`
- `uxsim/order_control_tvt_baseline_fork_alignment.py`
- `uxsim/order_control_batch_level_2_reference.py`
- 関連baseline、FCFS、BATCHテスト
- 旧メモ`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`の研究シナリオ前提、三つの計算世界、局所仮想計算
- BATCH設計メモ`ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md`のLevel 2 mimic World、dummy upstream Node、sink Node、trigger通過時早期終了、outlink Vehicle前進とsink end-trip

行番号は確認時点の目安である。実装前仕様では、その時点のコードを再確認する。

### DELTAN=1の制度上の前提

TVT研究では、初期研究範囲について`DELTAN=1`を制度上の前提とする。これは今回確定した基本設計である。

理由:

- UXsimの`DELTAN`は、一つのVehicleオブジェクトが代表するVehicle台数である。`World.__init__`の`deltan`説明は platoon size であり、既定値は5である。
- `DELTAN`が1より大きい場合、一つのVehicleオブジェクトが複数台を表す。
- TVTではVehicleごとに、参加・非参加、VOT、買い手・売り手、順位、支払い、補償、Visitを扱う。
- 一つのVehicleオブジェクトが複数台を代表すると、個別Vehicle間の順位交換と経済取引の制度が一致しない。
- したがって、TVTの初期研究範囲では、一つのVehicleオブジェクトを一台として扱う必要がある。

これにより、下流境界観測で数えたVehicleオブジェクト数を、そのままVehicle台数として扱う。

`DELTAN`が1より大きいTVTへの一般化は初期実装範囲外である。

既存メモや個別実験にある`deltan=1`という実験条件だけを根拠としない。今回確定したのは、TVT制度がVehicle単位の参加、順位、支払い、補償を扱うための制度上の理由である。

未確定として残す事項:

- `DELTAN=1`をどの公開処理で検証するか
- どの例外を出すか
- 例外文の正式表現

登録時に一度保証した後、各timestepで重複検証する設計にはしない方向である。現行`order_control_baseline_driver.py`は`DELTAN`を検証していない。検証位置は実装前仕様で確定する。

### UXsimのNodeとVehicleごとの目的地判定

UXsimはNode自体を、固定的なsink Nodeまたは途中通過Nodeとして分類していない。

Vehicleが現在Linkの終端へ到着した際に、`Vehicle.update()`がVehicleごとに次を判定する。確認位置は`uxsim/uxsim.py`の`Vehicle.update()`である。

```text
current_link.end_node == vehicle.dest
```

コード上の対応:

```text
s.link.end_node == s.dest
```

一致する場合:

- そのVehicleにとって終端Nodeは目的地Dである
- `single_trip` Vehicleは`flag_waiting_for_trip_end`が設定される
- そのVehicleがLinkの物理先頭であれば`end_trip()`が実行される
- `incoming_vehicles`へは登録されない
- 次Linkを選択しない

一致しない場合:

- そのVehicleにとって終端Nodeは途中通過Nodeである
- `route_next_link_choice()`により次Linkを選択する
- 終端Nodeの`incoming_vehicles`へ登録される
- 後続timestepの`Node.transfer()`で次Linkへの通過を試す

`taxi` modeは目的地一致時に次の目的地へ進み、`incoming_vehicles`へ登録し得る。現在の正式研究対象は`single_trip`である。taxi固有処理をTVT初期実装の一般規則として採用しない。

したがって、同じNodeについて、あるVehicleには目的地D、別のVehicleには途中通過Nodeとなることがコード上可能である。

Nodeを端点か内部Nodeかに固定分類して、境界処理を一律に変える設計にはしない。

### 端点Nodeを途中通過する可能性

UXsimの自動経路選択は、実在する有向Linkと、目的地までの最短経路情報を使う。

あるNodeが他VehicleのOまたはDとして使われる端点Nodeであること自体は、経路選択上の通過禁止条件ではない。

端点Nodeと内部Nodeの間について、一方通行だけを許可する仕組みはない。

Linkは有向Linkとして個別に登録される。`Link`生成時に、開始Nodeの`outlinks`と終了Nodeの`inlinks`へ登録される。確認位置は`uxsim/uxsim.py`のLink初期化である。

```text
start_node.outlinks[link.name] = link
end_node.inlinks[link.name] = link
```

- `O → A`だけ登録すれば一方通行である
- `O → A`と`A → O`の両方を登録すれば両方向通行である
- UXsimが存在しない逆方向Linkを自動生成することはない

端点Nodeへ入るLinkと、端点Nodeから出るLinkの両方が存在し、その端点Nodeを経由する経路が選択された場合、別のVehicleがその端点Nodeを途中通過する可能性をコード上は排除していない。

そのため、

「端点Nodeは必ず全VehicleにとってOまたはDであり、途中通過されない」

という前提をコード保証済み事項として扱わない。

旧メモ§1.3の研究シナリオ前提は維持する。

- 比較対象内部交差点Nodeを目的地としない端点間ODを使用する
- trip-end Vehicleは現在の研究対象外である

これは正式研究ネットワークの作成前提である。UXsimコードが端点途中通過を禁止していること、または監視対象outlink上に目的地到着Vehicleが存在しないことを保証するものではない。

局所境界処理は、Nodeの固定分類ではなくVehicleごとの目的地判定に基づく。

### 目的地到着Vehicleと途中通過Vehicle

下流境界観測と局所仮想計算では、同じ監視対象outlink上のVehicleを次の2種類に分ける。

#### 目的地到着Vehicle

監視対象outlinkの終端Nodeが当該Vehicleの`dest`である。

```text
monitored_outlink.end_node is vehicle.dest
```

このVehicleは:

- 終端Nodeで走行を終了する
- `incoming_vehicles`に入らない
- 下流へ続く通過要求を持たない
- baselineのactive timestepの判定対象に含めない
- baselineの実流出台数に含めない
- 条件付き平均下流境界サービス率の分母と分子に含めない
- 局所仮想計算でも通常のUXsimと同じtrip-end処理を行う
- 途中通過Vehicle向けの平均境界サービス制約を適用しない

#### 途中通過Vehicle

監視対象outlinkの終端Nodeが当該Vehicleの`dest`ではない。

```text
monitored_outlink.end_node is not vehicle.dest
```

このVehicleは:

- さらに次のLinkへ進む
- 終端Nodeの`incoming_vehicles`に入る
- baselineのactive timestep判定対象になる
- baselineの実流出台数集計対象になる
- 局所仮想計算では、条件付き平均下流境界サービス率の制約対象になる

同じoutlink上に、目的地到着Vehicleと途中通過Vehicleの両方が存在し得る。

同じ終端Nodeにおいて、大多数のVehicleが目的地到着としてtrip-endし、一部のVehicleだけが途中通過する場合も扱える必要がある。

平均境界サービス率が2台であっても、その2台制約は途中通過Vehicleだけへ適用する。

目的地到着Vehicleを2台制約で滞留させない。

### 単車線における物理順とtrip-end

現在の正式研究条件は単車線である。

同じoutlink上で、

- 前方Vehicleが途中通過Vehicle
- 後方Vehicleが終端Nodeを目的地とするVehicle

である場合、後方の目的地到着Vehicleは前方Vehicleを追い越して先にtrip-endしない。

`Vehicle.update()`では、目的地到着時に`flag_waiting_for_trip_end`を設定するが、`end_trip()`は`s.link.vehicles[0] == s`のときだけ実行する。

後方Vehicleが目的地Nodeへ到着しても、Linkの物理先頭でなければ、

- `flag_waiting_for_trip_end`は設定される
- `end_trip()`はまだ実行されない

前方の途中通過Vehicleが終端Nodeを通過してLinkを離れ、後方Vehicleが物理先頭になった後に、後方Vehicleの`end_trip()`が実行される。標準transferおよびFCFS transferは、通過後に後続のtrip-end待ち先頭車を処理する。

したがって、目的地到着Vehicleを平均境界サービス率の制約対象から除外しても、前方の途中通過Vehicleを物理的に追い越す処理にはならない。

### active timestepの確定定義

監視単位は、各TVT対象Nodeから出る各実在outlinkである。

各監視対象outlinkについて、終端Nodeの`Node.transfer()`直前にactive状態を観測する。

activeである条件:

- 終端Nodeの`incoming_vehicles`に1台以上のVehicleが存在する
- そのVehicleの現在Linkが、監視対象outlinkと同じfork World内Linkオブジェクトである

概念式:

```text
active
=
any(
    vehicle.link is monitored_outlink
    for vehicle in terminal_node.incoming_vehicles
)
```

目的地到着Vehicleは`incoming_vehicles`に入らないため、このactive判定へ自然に含まれない。

このため、activeは実質的に、監視対象outlinkから来た途中通過Vehicleが、終端Nodeで次Linkへの通過を待っている状態を表す。

同じ途中通過Vehicleが複数timestep待機した場合は、各timestepをそれぞれactiveとして数える。`incoming_vehicles`は当該timestepの`transfer()`後にclearされ、次にリンク終端へ到達したVehicleが後続の`Vehicle.update()`で再登録される。

active timestep countはVehicle数ではなく、途中通過Vehicleによる下流通過要求が存在した時間の長さを表す。

同じ終端Nodeへ複数の監視対象outlinkが接続していても、`vehicle.link is monitored_outlink`によりoutlink別に区別する。

同一timestepに複数の途中通過Vehicleが待機していても、そのoutlinkのactive countは1だけ増える。activeは「待っていたか」であり、「何台待っていたか」ではない。

### 実流出台数の確定した観測方法

`cum_departure`の前後差を、下流境界の実流出台数の正本にはしない。

ただし、正式研究条件では比較対象内部交差点を目的地とせず、trip-end VehicleをTVT対象外としていることも明記する。これは旧メモ§1.3の研究シナリオ前提である。

`cum_departure`を正本にしない主な理由は、今回測りたい意味に直接対応する方法が別にあるためである。補助理由として、一般的なUXsimコードでは`end_trip()`も`cum_departure`を増加させる。

採用する観測方法:

1. 終端Nodeの`transfer()`直前に、監視対象outlink由来で`incoming_vehicles`に入っているVehicle参照を保持する。
2. 終端Nodeの`transfer()`を既存どおり実行する。
3. `transfer()`直後に、保持したVehicleごとに現在Linkを確認する。
4. `vehicle.link is not monitored_outlink`となったVehicleを、そのtimestepに監視対象outlinkから実際に流出した途中通過Vehicleとして数える。

この方式が数えるもの:

- transfer直前に途中通過を要求して待っていた
- 実際に終端Nodeの通過処理を受けた
- その結果、元のoutlinkを離れた

というVehicleである。

目的地到着Vehicleは`incoming_vehicles`に入らないため、保持対象にならず、実流出台数にも含まれない。

`transfer()`終了後は`incoming_vehicles`がclearされる。確認位置:

- 標準`Node.transfer()`
- `Node.transfer_fcfs_clearance()`
- `Node.transfer_batch()`

このため、transfer後の`incoming_vehicles`件数差だけで流出台数を数えない。

また、標準、FCFS、BATCHの各transfer成功箇所へ個別に同じ記録処理を重複実装しない。

### cum_departureの位置付け

UXsimでは、Link間通過成功時に流出元Linkの`cum_departure[-1]`が増加する。確認例:

- 標準transfer
- BATCH service queue内部のLink間遷移
- FCFS transfer

`Vehicle.end_trip()`でも現在Linkの`cum_departure[-1]`が増加する。確認位置は`Vehicle.end_trip()`である。続けて`s.link = None`となる。

したがって、一般的なUXsimコードとしては、`cum_departure`の増加だけから、

- 次Linkへ進んだ途中通過Vehicle
- 目的地でtrip-endしたVehicle

を区別できない場合がある。

本研究ではVehicleごとの目的地判定と`incoming_vehicles`を使って途中通過Vehicleだけを直接保持できるため、Vehicle参照方式を実流出台数の正本とする。

`cum_departure`は、必要なら補助的な整合確認へ使用する余地を残すが、正式台数の正本とはしない。

### UXsimの1 timestep内の実行順

コード確認済み事実として、一つのtimestepの主要実行順は次である。確認位置は`World.exec_simulation()`である。

1. 全Linkの`Link.update()`
2. 全Nodeの`Node.generate()`
3. 全Nodeの`Node.update()`
4. 全Nodeの`Node.transfer()`
5. 全実行中Vehicleの`Vehicle.carfollow()`
6. 全生存Vehicleの`Vehicle.update()`

終端Nodeの`transfer()`直前には、その時点で次Linkへの通過待ちとなっている途中通過Vehicleが`incoming_vehicles`に存在する。それらは前timestepの`Vehicle.update()`でリンク終端到達後に登録され、当該timestepの`transfer()`まで残る。

全Nodeの`transfer()`は、`World.exec_simulation()`内の共通ループから順に呼ばれる。標準、FCFS、BATCHの分岐は各`Node.transfer()`内部で行われる。

### 観測hookの確定配置方針

下流境界観測は、標準、FCFS、BATCH等の個別transfer実装へ重複して追加しない。

`World.exec_simulation()`内の、全Nodeについて`node.transfer()`を呼ぶ共通位置で観測する。

概念的な処理順:

```text
各Nodeについて:

1. baseline下流境界observerが存在し、
   今回のNodeが監視対象outlinkの終端Nodeなら、
   transfer直前の待機Vehicle参照を取得する

2. node.transfer()を既存どおり実行する

3. observerが存在し、
   直前観測を行っていた場合、
   transfer直後に元のoutlinkを離れたVehicleを数える
```

この配置により、終端Nodeの制御方式が、

- UXsim標準
- FCFS
- BATCH
- その他、既存`Node.transfer()`分岐

のいずれであっても、同じ共通観測方法を適用できる。

これは各制御方式をTVTへ取り込む意味ではない。

終端境界で実現した待機と流出を、制御方式にかかわらず共通の方法で観測するためである。

具体的な補助関数名、hookの行単位実装、observerの公開メソッド名は、実装前仕様で確定する。

### 観測hookの非侵襲性

下流境界observerは、全World baselineのfork Worldでのみ有効とする。

実Worldではobserver参照は`None`とする。既存`World.__init__`は`_order_control_baseline_collector = None`である。observer参照も同様に、実Worldでは`None`とする方向である。正式属性名は未確定である。

observerが`None`の通常シミュレーションでは、追加の境界観測処理を行わない。

観測処理は次を行わない。

- RNGを消費しない
- Vehicle順位を変更しない
- `incoming_vehicles`を変更しない
- Link所属を変更しない
- Node状態を変更しない
- capacityを変更しない
- route choiceを実行しない
- User設定の`Node.user_function`を上書きしない
- 実Worldへ観測結果を書き込まない
- Nodeのtransfer順序を変更しない

観測対象外Nodeと観測対象外Linkを記録しない。同じtimestepを重複記録しない。途中失敗時に部分結果を正常結果として返さない。

`World.copy()`は`pickle.loads(pickle.dumps(W))`である。実Worldはobserverが`None`のままcopyされる方向とする。fork Worldへのobserver接続はcopy後に行う方向である。pickle可能性を損なわない。

### 下流境界専用observer

下流境界観測は、既存`OrderControlBaselineCollector`のVisit記録へ直接混在させない。

理由:

- 既存collectorの責務はsnapshot固定Visitの到着・通過記録である
- 既存collectorはVehicle名、Visit ID、Node名等によるVisit台帳である
- 下流境界観測は、対象Node、outlink、終端Node、horizon集計による道路境界情報である
- Visit記録と道路境界集計では、キーと責務が異なる
- 既存のVisit件数照合やsnapshot登録用validation collectorへ影響させない方が明確である

既存コードはcollectorの内部辞書へ直接依存せず、公開メソッドを利用している。確認例:

- `register_snapshot_visit()`
- `record_baseline_arrival()`
- `prepare_baseline_passage_recording()`
- `apply_baseline_passage_timestep()`
- `export_node_baseline_visits()`
- `get_baseline_visit_snapshot()`

fork Worldには、既存baseline collectorとは別に、下流境界専用observerへの参照を持たせる方向とする。

概念上の候補名は次である。正式名称として確定しない。

- `OrderControlBaselineDownstreamBoundaryObserver`
- `_order_control_baseline_downstream_boundary_observer`

正式なクラス名、World属性名、公開メソッド名は完全な実装前仕様で確定する。

### 観測結果の保存先

下流境界の集計結果は、`OrderControlBaselineForkResult`から参照できる独立情報として返す。

既存の`collector`フィールドの意味を変更しない。

`OrderControlBaselineForkResult`は`fork_W`を保持しない。境界観測結果はfork終了後も残る独立情報とする必要がある。

結果は、後続処理から変更されない読取専用構造とする方向である。

候補:

- frozen dataclass
- tuple
- 対象Node別のimmutable result
- outlink別のimmutable result

正式な結果型名とフィールド名は未確定とする。

各outlink境界結果に必要となる情報の候補:

- TVT対象Node名
- 監視対象outlink名
- 終端Node名
- configured horizon
- active timestep count
- transferred Vehicle count
- 必要なら観測状態または補助情報

条件付き平均サービス率そのものをbaseline結果へ保存するか、

- active timestep count
- transferred Vehicle count

だけを保存し、局所仮想計算接続側で平均率を計算するかは、まだ未確定として残す。

### 監視対象の準備位置

通常baseline実行経路`run_snapshot_fixed_baseline_fork()`と、TVT順位台帳登録付きbaseline実行経路`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()`は、いずれも`_complete_baseline_fork_after_registration()`へ合流する。

そのため、下流境界observerと監視対象outlinkの準備は、

- snapshot固定Visit登録完了後
- 登録Visit件数の整合確認後
- `fork_W.exec_simulation(...)`呼出し直前

の共通位置で行う方向とする。

ただし、具体的な補助関数名と行単位の実装は、実装前仕様で確定する。

監視対象の作成には、fork World内の対象Nodeとその実在outlinkを使用する。

対象Node名は、既存の`fixed_target_node_names`を使用する。

各対象Nodeについて、実際に登録されている`node.outlinks`だけを列挙する。

各outlinkの終端Nodeは`outlink.end_node`である。同じ終端Nodeへ複数outlinkが接続しても、監視単位はoutlinkである。

対象Node内のoutlink順をdict登録順にするか、Link名順に固定するかは未確定である。同一outlinkの重複登録時の例外契約も未確定である。

### 有向Linkと存在しない逆方向Link

UXsimのLinkは有向Linkである。

Link登録時に、

- `start_node.outlinks`
- `end_node.inlinks`

へ登録される。

存在しない逆方向Linkは自動生成されない。

したがって、対象Nodeの監視対象は、fork World内で実際に`target_node.outlinks`に登録されているLinkだけである。

例えば、

```text
O → A
```

だけが存在する場合、

```text
A → O
```

をAのoutlinkとして推測、補完、登録しない。

存在しない逆方向Linkがないことを、異常として扱わない。

一方通行または両方向通行のいずれも、ネットワークに実際に登録された有向Linkに従って扱う。

### order control対象Nodeに関する留意事項

既存の自動eligibility判定は、概ね次の構造条件を使用する。確認位置は`World.infer_order_control_eligible_nodes()`である。

```text
inlink数 >= 2
かつ
outlink数 >= 1
```

outlinkが2本以上であることは要求していない。

そのため、outlinkが1本だけの内部合流Nodeもorder control対象になり得る。

自動判定は、NodeがOまたはDとして使われる端点Nodeかどうかを確認しない。

正式な研究シナリオでは次を前提とする。

- OまたはDとして使用する端点Nodeをorder control対象にしない
- 端点Nodeにinlinkが2本以上かつoutlinkが1本以上ある特殊構造は想定しない
- 端点Nodeを手動で`order_control_eligible=True`にすることも想定しない

ただし、ネットワーク定義を誤った場合、端点Nodeが自動eligibility条件を満たす可能性は理論上残る。

これはネットワーク構築上の留意事項として記録する。

この誤設定を防ぐための新しい実行時検査は、現時点では追加しない。

理由:

- 正式研究ネットワークの作成時点で保証する前提である
- 登録時に保証した不変条件を実行時に重複検証しない既存方針に従う
- 現時点で実際に発生していない特殊ケースのために本番処理を複雑化しない

異常が疑われる場合は、まずネットワーク定義と対象Node設定を確認する。

### 目的地到着と途中通過が混在する端点Node

あるTVT対象Node Aから出る監視対象outlinkが、端点Node Oへ接続しているとする。

UXsim上、Oから別の内部Nodeへ戻る有向Linkも存在する場合、Oは次の二つの役割をVehicleごとに持ち得る。

Vehicle P:

```text
P.dest is O
```

- Oでtrip-endする
- active判定対象外である
- transferred count対象外である
- 条件付き平均境界サービス対象外である

Vehicle Q:

```text
Q.dest is not O
```

- Oを途中通過する
- Oの`incoming_vehicles`に入る
- active判定対象である
- Oの`Node.transfer()`で別Linkへの移動を試す
- 実際に監視対象outlinkを離れた場合、transferred countへ加算する
- 局所仮想計算では平均境界サービス制約の対象である

baselineで、Oを目的地とするVehicleが多数trip-endし、Oを途中通過するVehicleが少数だけ存在した結果、途中通過Vehicleの条件付き平均サービス率が2台となった場合:

- 局所仮想計算で2台制約を適用するのは、Oを途中通過するVehicleだけである
- Oを目的地とするVehicleへ2台制約を適用しない
- 目的地到着Vehicleは通常どおりtrip-endする
- ただし、単車線上で前方に途中通過Vehicleが残っている場合、後続の目的地到着Vehicleは前方Vehicleを追い越してtrip-endしない

この例により、Node全体へ一律に平均2台制約を掛けるのではなく、途中通過Vehicleだけへ適用することを明確にする。

### 前回記録からの修正事項

2026-09-18の設計検討記録には、当時の検討として次の趣旨が含まれ得る。既存本文は削除しない。当時の検討段階の記述であり、本更新節が最新である。

当時の考え方と今回の最新整理:

- 「終端Nodeが端点なら一律にsinkとする」
  - 最新: Node固定分類ではなく、Vehicleごとに目的地か途中通過かを判定する。BATCH Level 2のsink NodeはBATCH mimic Worldの参考事実であり、TVT下流境界の正本ではない。
- 「端点Nodeでは平均境界サービス率を作らない」
  - 最新: 端点Nodeでも途中通過Vehicleが存在すれば境界平均の観測対象になり得る。
- 「端点Nodeが途中通過されないことがコード上保証されている」
  - 最新: コード上は保証されていない。研究シナリオで端点途中通過を意図していなくても、UXsimコード上は禁止されていない。
- 「Node単位で内部Nodeと端点Nodeを分類すれば十分である」
  - 最新: 同じNodeがVehicleごとに目的地にも途中通過Nodeにもなり得る。
- 「`cum_departure`差をそのまま正式台数とする」
  - 最新: 実流出台数の正本はVehicle参照方式である。`cum_departure`は補助情報に限る。
- 「trip-end Vehicleが研究対象外なので、あらゆる監視outlinkでend-trip混入を考えなくてよい」
  - 最新: TVT制度の研究対象外であることと、監視outlink上の物理的な目的地到着Vehicleの存在とは別である。目的地到着Vehicleは平均集計対象外とし、途中通過Vehicleだけを集計する。

前回の有力案である条件付き平均境界サービス、流出許可残高、active=0時の制約付きsinkは、局所仮想計算側の近似方式として残る。ただし、分母と分子に入れるのは途中通過Vehicleのactiveとtransferだけである。目的地到着Vehicleを含めない。

### 今回確定していない事項

少なくとも次は未確定である。本節で独自判断して確定しない。

- observerの正式クラス名
- World上の正式属性名
- observerの公開メソッド名
- observerの内部データ構造
- outlink別結果型の正式名称
- 対象Node別結果型の正式名称
- 全体結果型の正式名称
- `OrderControlBaselineForkResult`へ追加する正式フィールド名
- 対象Node内のoutlink順をdict登録順にするか、Link名順に固定するか
- 同一outlinkの重複登録時の例外契約
- `DELTAN=1`の検証位置と例外文
- configured horizonをobserverへどう渡すか
- observerの開始・終了状態
- baseline失敗時の部分結果処理
- 空baseline結果で境界結果を空tupleにするか別状態にするか
- 条件付き平均サービス率をbaseline結果として保存するか
- countだけを保存して局所計算側で平均を算出するか
- active timestep countが0の場合の正式な結果表現
- active>0かつtransferred count=0の場合の正式な結果表現
- 局所仮想計算で平均サービス率を適用する具体的処理
- 流出許可残高の正式データ型
- outlink流出容量と終端Node容量を使う具体的処理
- 目的地到着Vehicleの局所mimic World上のtrip-end処理
- TVT局所仮想計算全体のresolved条件
- inlink始端からの新規流入
- performance counter
- diagnostic情報
- 専用テストの正式ファイル名

条件付き平均境界方式の正式採用も未確定である。本節が確定したのは、全World baselineで途中通過Vehicleのactiveと実流出をどう観測し、どこへ保存する方向かの基本設計である。

### 実装に必要となるテスト観点

今回はテストを実装しない。後続の実装前仕様に必要なテスト観点は次である。正式テスト名は未確定である。

#### DELTAN

- `DELTAN=1`で正常動作すること
- `DELTAN`が1以外の場合の拒否契約は未確定であること
- `DELTAN`検証をtimestepごとに重複実行しないこと

#### 単一境界

- 単一TVT対象Node
- 単一outlink
- 単一終端Node
- active timestepが正しく1回加算されること
- 1台の途中通過Vehicleが流出し、transferred countが1になること

#### 複数outlink

- 一つの対象Nodeに複数outlink
- outlinkごとにactiveとtransferを別集計すること
- 同じ終端Nodeへ複数outlinkが接続すること
- Vehicleの現在Link参照で流出元outlinkを区別すること

#### 複数対象Node

- 複数TVT対象Node
- `target_node_names`の対象外Nodeを観測しないこと
- 各対象Nodeのoutlinkだけを監視すること
- 同じ終端Nodeを複数対象Nodeのoutlinkが共有する場合に区別すること

#### active

- active timestep countが0であること
- 同一Vehicleが複数timestep待機し、複数active timestepとして数えられること
- 同一timestepに複数Vehicleが待機していてもactive countは1だけ増えること
- 目的地到着Vehicleだけが存在する場合、activeに含めないこと
- 途中通過Vehicleが1台以上存在する場合、activeになること

#### transfer

- activeで1台流出すること
- activeで複数台流出すること
- activeだが0台流出すること
- transfer前に保持したVehicleが元のoutlinkを離れた場合だけ数えること
- `incoming_vehicles` clear後の件数差を使わないこと
- destinationでのtrip-endをtransferred countへ含めないこと

#### 制御方式

終端Nodeが次の各方式であっても共通観測できること。

- UXsim標準
- FCFS
- BATCH

個別transfer実装へ境界記録コードを重複追加しないこと。

#### 目的地と途中通過の混在

同じ監視対象outlink上に、目的地到着Vehicleと途中通過Vehicleが混在するケース。

目的地到着Vehicleはtrip-endするが、activeとtransferred countへ含まれない。

途中通過Vehicleだけがactiveとtransferred countへ含まれる。

#### 単車線物理順

- 前方が途中通過Vehicle
- 後方が目的地到着Vehicle
- 後方目的地Vehicleは、前方Vehicleがoutlinkを離れる前にend-tripしない
- 前方Vehicleが離れ、後方Vehicleが物理先頭になった後にend-tripする

#### 一方通行と両方向通行

- 実在する有向Linkだけを監視すること
- 存在しない逆方向Linkを補完しないこと
- 一方通行で正常動作すること
- 両方向Linkが登録されたネットワークでも、実在outlinkだけを扱うこと

#### baseline driver

- 通常baseline経路
- TVT順位台帳登録付きbaseline経路
- 両経路で同じ境界観測結果になること
- configured horizon全体を観測すること
- 空baseline経路
- `real_W`不変
- fork Worldだけにobserverを接続すること
- baseline失敗時に部分結果を正常返却しないこと

#### 非侵襲性

- observerが`None`なら既存動作不変であること
- RNG状態を変えないこと
- Vehicle順序を変えないこと
- route choiceを変えないこと
- capacityを変えないこと
- `user_function`を上書きしないこと
- Python pickleによる`World.copy`を壊さないこと
- 結果が読取専用であること

### 今回実装しない範囲

今回は次を実装しない。Python実装済み、テスト済み、実装前仕様完成とは記載しない。

- observerクラス
- World属性
- `exec_simulation()`へのhook
- baseline driver変更
- baseline result変更
- `DELTAN`検証
- active観測
- transfer後観測
- 結果型
- 専用テスト
- 条件付き平均サービス率
- 流出許可残高
- 制約付きsink
- 局所mimic World
- inlink始端新規流入
- 経済性評価
- TVT成立候補選択
- 実Worldへの順位反映

### 確認したファイル、関数、行番号の目安

実装前仕様作成時に再確認する。行番号は2026-09-19確認時点の目安である。

- `uxsim/uxsim.py`
  - `World.exec_simulation()`の主要ループ、全Node `transfer()`呼出し
  - `Node.transfer()`の標準、FCFS、BATCH分岐
  - 標準transferおよびFCFS、BATCHでの`incoming_vehicles` clear
  - `Vehicle.update()`の`s.link.end_node == s.dest`判定、trip-end待ち、`incoming_vehicles`登録
  - `Vehicle.end_trip()`の`cum_departure`増加と`s.link = None`
  - Link初期化時の`start_node.outlinks`、`end_node.inlinks`登録
  - `World.infer_order_control_eligible_nodes()`の`inlinks >= 2`かつ`outlinks >= 1`
  - `World.__init__`の`deltan`説明と`_order_control_baseline_collector = None`
  - `World.copy()`のpickle複製
- `uxsim/order_control_baseline_driver.py`
  - `OrderControlBaselineForkResult`の既存フィールド。`fork_W`非保持
  - `_prepare_baseline_fork()`のcollector接続
  - `_complete_baseline_fork_after_registration()`への通常経路と順位台帳付き経路の合流
  - 空baseline経路はforwardしない
  - `exec_simulation(duration_t2=...)`によるconfigured horizon実行
- `uxsim/order_control_baseline_collector.py`
  - Visit記録責務と公開メソッド
- `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`
  - §1.3研究シナリオ前提
  - §16局所仮想計算範囲
  - §25.25.34三つの計算世界
- `ORDER_EXCHANGE_PHASE4-6_BATCH_PROCESSING_DESIGN_NOTES.md`
  - Level 2 mimic Worldのdummy upstream、sink、trigger早期終了

### 次の作業開始点

今回の境界観測基本設計を前提に、下流境界観測部品の完全な実装前仕様に必要な残る設計判断を整理する。

少なくとも次を判断対象とする。

- observerの正式名称と責務
- World属性名
- observer登録API
- transfer前後観測API
- outlink別結果型
- 対象Node別結果型
- 全体結果型
- `OrderControlBaselineForkResult`への追加フィールド
- 結果順序
- active=0の表現
- active>0かつtransfer=0の表現
- 条件付き平均率をどこで計算するか
- `DELTAN=1`の検証位置
- 空baseline経路
- baseline失敗時の部分状態
- 専用テスト契約

ただし、inlink始端新規流入、局所mimic World全体、経済性評価にはまだ進まない。FIFO検査接続部品を再考しない。`preserves_inlink_fifo()`を変更しない。一般形順位再構成を変更しない。直ちに局所仮想計算を実装しない。

**2026-09-19更新注記：** 上記「次の作業開始点」は、下流境界観測の基本設計確定時点の記録である。残る設計判断は完了した。Python実装時の最新正本は、直後の「全World baseline下流境界観測部品の完全な実装前仕様」である。

## 全World baseline下流境界観測部品の完全な実装前仕様

記録日：2026-09-19

本節は、下流境界観測部品の**完全な実装前仕様**である。下流境界観測部品については、Python実装へ進むために必要な主要判断を完了した。

本節は、TVT候補別局所仮想計算全体の完全な実装前仕様ではない。

Python実装と専用テストはまだ未着手である。実装済み、テスト済みとは記載しない。

保存済み基本設計コミットは`c2c98c0`（`Document the TVT downstream boundary observation basic design`）である。直前の「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」は調査と基本設計確定の歴史的記録として残す。本節をPython実装時の最新正本とする。既存の基本設計記録は削除・短縮・置換しない。

今回のMarkdown追記は記録時点では未コミットである。

条件付き平均率、流出許可残高、制約付きsink、局所mimic World、inlink始端、経済評価は今回の実装対象外である。

制度ロジックの観測方法（active、途中通過Vehicle、Vehicle参照方式、`cum_departure`非正本、共通`exec_simulation()` hook、専用observer、Vehicleごとの目的地判定、実在有向Linkのみ）は、直前の基本設計を維持する。本節で再考しない。

### 非技術的な目的

TVT対象交差点から出た道路の先が詰まっている場合、その道路は対象交差点から新しいVehicleを受け入れにくくなる。

候補別局所仮想計算でこの影響をおおまかに再現するため、先に行う全World baseline計算で、対象交差点から出る各道路について、次を記録する。

- 道路の終端で、さらに先へ進もうとするVehicleが待っていた時間
- そのうち、実際に先へ進めたVehicle数

この部品は、起きた事実を数えて保存することだけを担当する。

平均値の計算、その平均値の局所仮想計算への適用、使わなかった流出枠の繰越し等は、この部品の仕事ではない。

### 正式な実装範囲

今回の下流境界観測部品の正式な実装範囲は次である。

- TVT対象Nodeから出る実在outlinkの登録
- outlink終端Nodeの`transfer()`直前に、途中通過Vehicleの待機状態を観測
- `transfer()`正常終了後に、元のoutlinkを離れた途中通過Vehicle数を集計
- `transfer()`失敗時に、そのtimestepの一時観測を破棄
- 対象Node別、outlink別の累計を保持
- 名前と非負整数だけからなる読取専用結果を作成
- baseline driverへ結果を受け渡す
- baseline未実行状態を観測済みゼロと区別
- FCFS、BATCH、TVTに共通する`DELTAN=1`の設定時検査

正式な実装範囲外:

- 条件付き平均流出率の算出
- 条件付き平均率の保存
- 流出許可残高
- 流出枠の繰越し
- outlink流出容量と終端Node容量による局所境界処理
- active=0時の制約付きsink
- 目的地Vehicleの局所mimic World上の具体的trip-end処理
- 局所mimic World全体
- inlink始端新規流入
- TVT候補の経済評価
- 成立候補選択
- 実Worldへの順位反映

### DELTAN=1のorder control共通前提

`DELTAN=1`はTVTだけでなく、FCFS、BATCH、TVTに共通するorder control全体の制度前提である。

2026-09-19の基本設計は、TVT初期研究範囲として`DELTAN=1`を述べた。本節では、同じ制度上の理由をorder control全体へ確定する。FCFSとBATCHもVehicleオブジェクトごとに順序を制御するためである。基本設計本文は削除しない。

理由:

- UXsimでは一つのVehicleオブジェクトが`DELTAN`台を代表する
- FCFS、BATCH、TVTはVehicleオブジェクトごとに順序を制御する
- `DELTAN`が1より大きいと、一つのVehicleオブジェクトが複数台を代表し、個別車両順位という研究制度と一致しない
- TVTではさらに、Vehicleごとの参加、VOT、買い手、売り手、支払い、補償を扱う
- 一つのVehicleオブジェクトを実車一台に対応させる必要がある

正式な共通検証処理名:

```python
_validate_order_control_deltan
```

既存の`_validate_order_control_batch_t_trigger_level()`等と同様、`uxsim/uxsim.py`の設定入口から呼ぶvalidatorとする。この処理は、少なくとも次を受け取る、または参照できる構造とする。

- Worldの`DELTAN`
- 必要なら`order_control_type`
- 必要ならNode名

具体的な引数形は、既存のvalidator形式と整合させて実装時に最小限の形を選ぶ。ただし、処理名と責務は確定事項である。

呼出位置:

1. Node作成時に、`order_control_type`として`"fcfs"`、`"batch"`、`"time_value"`のいずれかを直接指定する経路
2. `World.set_order_control_for_nodes()`で、`"fcfs"`、`"batch"`、`"time_value"`のいずれかを設定する経路

`order_control_type="none"`では検証しない。

`World.set_order_control_for_randomly_selected_eligible_nodes()`は、最終的に`set_order_control_for_nodes()`へ合流する。ランダム選択処理内に重複検証を追加しない。

検証時期:

- order controlの設定時
- NodeまたはNode群の設定を変更する前
- シミュレーション実行前

検証しない場所:

- 各timestep
- 各Vehicle
- 各`Node.transfer()`
- 各baseline計算
- 各observer観測
- 各局所仮想計算

`DELTAN != 1`の場合:

- `ValueError`
- 設定変更前に停止
- エラー文へ実際の`DELTAN`値を含める
- FCFS、BATCH、TVTは個別Vehicleオブジェクトの順位を制御するため`DELTAN=1`が必要である旨を含める

エラー文の確定趣旨:

```text
Intersection order control requires DELTAN=1 because FCFS, BATCH, and TVT control individual Vehicle objects; got DELTAN=<actual value>.
```

既存コードの文体に合わせて改行等を調整してよいが、意味を変更しない。

`set_order_control_for_nodes()`では、いずれかの指定Nodeを変更する前に検証する。`DELTAN != 1`なら、複数Nodeの一部だけを先に変更しない。

検査済みフラグは追加しない。

設定関数がネットワーク準備時に複数回呼ばれれば、その設定時に再度検査される可能性はあるが、各timestepや各baselineで繰り返されるものではない。

### 新規本番モジュール

下流境界observer、結果型、登録・観測・export処理は、新しい専用モジュールへ置く。

正式モジュール名:

```text
uxsim/order_control_baseline_downstream_boundary.py
```

このモジュールへ次を実装する。

- outlink単位の読取専用結果型
- 対象Node単位の読取専用結果型
- 全体の読取専用結果型
- observer
- 必要な入力検証helper
- 監視outlink登録
- transfer前capture
- transfer後commit
- pending情報破棄
- 読取専用結果export

このモジュールは次を所有しない。

- Worldの複製
- baseline forwardの実行
- Visit collector
- snapshot固定Visit登録
- TVT順位
- 条件付き平均率
- 局所仮想計算
- 経済性評価

循環参照:

`uxsim.py`の`exec_simulation()`は、World属性上のobserverメソッドをduck typingで呼ぶ。`uxsim.py`は本モジュールを実行時importしない。本モジュールは実行時に`from uxsim.uxsim import World`しない。driverは本モジュールと`World`の両方をimportしてよい。型ヒントが必要なら`TYPE_CHECKING`を使う。過度な抽象化は避ける。

### observerの正式名称と責務

正式クラス名:

```python
OrderControlBaselineDownstreamBoundaryObserver
```

正式な責務:

- 各対象Nodeから出る実在outlinkを監視対象として登録
- 終端Node単位の索引を構築
- transfer直前の途中通過Vehicle参照を一時保持
- transfer正常終了後にactive timestepと実流出台数を確定
- transfer失敗時に、そのtimestepの一時情報だけを破棄
- 登録順を維持した読取専用結果をexport

責務外:

- 平均率計算
- 局所仮想計算
- sink処理
- 流出許可残高
- Vehicleの移動
- Link容量変更
- Node容量変更
- route choice
- order-control順位
- Visit記録
- World複製
- baseline driverの制御

### World上の正式属性

正式属性名:

```python
_order_control_baseline_downstream_boundary_observer
```

`World.__init__`で次の初期値を設定する。

```python
W._order_control_baseline_downstream_boundary_observer = None
```

実Worldでは原則として`None`のままにする。

`World.copy()`後のfork Worldでも、observer接続前は`None`であることを要求する。既存collectorのcopy直後検査と同じ契約である。

baseline driverが、fork Worldのみにobserverを生成・接続する。

実Worldにはobserverを接続しない。

observer自身は通常のpickle可能なPythonオブジェクトとして実装する。

次を持たない。

- lambda
- closure
- generator
- 開いたファイル
- 外部リソース
- pickle不可能な状態

observerのexport結果へ、World、Node、Link、Vehicleオブジェクト参照を残さない。

### observerの正式API

次の正式メソッド名を使用する。

```python
register_target_node_outlinks()
capture_before_transfer()
commit_after_transfer()
clear_pending()
export_result()
```

#### `register_target_node_outlinks()`

- fork World内の一つのTVT対象Nodeについて、そのNodeから出る実在outlinkを登録する
- 対象Nodeの`node.outlinks`に実際に登録されているoutlinkだけを扱う
- 存在しない逆方向Linkは補完しない
- 各outlinkの`end_node`を終端Nodeとして記録する
- 同じ終端Nodeを共有するoutlinkも別々の監視単位として登録する
- 対象Nodeのoutlink登録順を維持する
- 登録時に必要な整合性を一度だけ検証する
- 同じoutlinkの二重登録を拒否する

引数の最終形は、実装時に既存オブジェクト関係を踏まえて明示的で可読性の高い形とする。

少なくとも、対象Node名、対象Nodeオブジェクト、またはそのoutlinkを安全に取得できる情報を受け取る。

一般化のためだけに過度に抽象化しない。driverは`fixed_target_node_names`順に`fork_W.get_node(node_name)`し、各Nodeについて本メソッドを呼ぶ。

登録時に検証する事項:

- 対象Node名が空でない文字列
- 対象Nodeがfork World内のNodeである
- 各outlinkがその対象Nodeの実在`outlinks`に属する
- 終端Nodeが`outlink.end_node`である
- 同一fork World内outlinkオブジェクトの二重登録がない

#### `capture_before_transfer()`

- `World.exec_simulation()`の共通Node transferループから、`node.transfer()`直前に呼ぶ
- 渡されたNodeが監視対象outlinkの終端Nodeでなければ、何もせず正常に返る
- 監視対象終端Nodeなら、そのNodeの`incoming_vehicles`を確認する
- 各監視対象outlinkについて、`vehicle.link is monitored_outlink`となるVehicle参照を一時保持する
- 一台以上保持したoutlinkを、そのtimestepのactive候補とする
- 同一outlinkに複数Vehicleが存在しても、activeは一つのtimestepとして一回だけ数える
- この時点では正式累計へ加算しない
- transferが正常終了した場合だけcommitする
- pendingが残ったまま新しいcaptureが来た場合は、掃除漏れまたは呼出順不整合として`RuntimeError`

目的地判定を各Vehicleへcapture時に再実行しない。`incoming_vehicles`に入っているVehicleを途中通過Vehicleとして扱う。`single_trip`では目的地到着Vehicleは`incoming_vehicles`に入らない。

#### `commit_after_transfer()`

- `node.transfer()`が例外なく正常終了した場合だけ呼ぶ
- captureしたNodeとcommit対象Nodeが一致することを要求する。不一致は`RuntimeError`
- pendingなしのcommitは呼出順不整合として`RuntimeError`
- capture時に途中通過Vehicleが一台以上存在したoutlinkについて、`active_timestep_count`を1増やす
- capture時に保持したVehicleについて、transfer後の`vehicle.link`を確認する
- 次の両条件を満たすVehicleだけを、実際に元のoutlinkを離れた途中通過Vehicleとして数える

```text
vehicle.link is not None
かつ
vehicle.link is not monitored_outlink
```

`vehicle.link is None`なら、trip-endまたは走行終了であり、途中通過成功として数えない。

`vehicle.link is monitored_outlink`のままなら、元のoutlinkに残っているため流出として数えない。

次Linkオブジェクトへ変わっている場合だけ、流出Vehicle数を1増やす。

同一Nodeの一回のtransferで、複数outlinkのVehicleが移動した場合は、それぞれ正しいoutlink結果へ加算する。

正常commit後は、そのtimestepのpending情報を消去可能な状態にする。`finally`の`clear_pending()`が残差を捨てられる。

#### `clear_pending()`

- そのtimestepのcaptureで一時保持した情報だけを消す
- 過去に正常commit済みの累計値は消さない
- transfer正常終了後にも、例外終了後にも、`finally`から必ず呼び出せる構造とする
- pendingがない場合の動作は、実装前仕様上は安全なno-opとする
- baseline全体の累計初期化には使用しない

#### `export_result()`

- 現在までの確定済み累計を、3段構造のfrozen resultへ変換する
- 対象Node順とoutlink順を維持する
- 内部の可変辞書やVehicle参照を返さない
- World、Node、Link、Vehicleオブジェクトを返さない
- 名前と非負整数だけをresultへ保存する
- 平均流出率を計算しない
- pendingが残っている状態でexportしようとした場合は、未確定timestepを正常結果へ混ぜないため`RuntimeError`とする
- export後の結果は、observer内部が後から変化しても変更されない

### 二重登録

正常な構造では、一つの実在outlinkは一つの開始Nodeに属するため、同じoutlinkの二重登録は発生しない前提である。

それでも二重登録が発生した場合は、将来の実装ミスまたは登録処理の不整合である。

確定仕様:

- 同じfork World内outlinkオブジェクトの二重登録を禁止
- 上書きしない
- 無視しない
- 二重集計しない
- baseline forward開始前に`ValueError`
- エラー文へ対象Node名とoutlink名を含める
- 各timestepでは重複検査しない

原因修正後は、実Worldシミュレーションを最初から手動でやり直す。

自動修復、自動再実行、baselineだけの自動再試行は実装しない。

二重登録失敗時、その登録呼出しより前に成功した別outlink登録を自動で巻き戻す必要はない。ただし、その失敗によりbaseline forwardは開始せず、`OrderControlBaselineForkResult`は返さない。既存の正常登録を壊して別の監視単位へ付け替えない。

### 結果型の正式構造

結果は、重複情報を避けた3段構造とする。

すべて`@dataclass(frozen=True)`とする。

#### outlink 1本分

正式名称:

```python
OrderControlBaselineDownstreamBoundaryOutlinkResult
```

正式フィールド:

```python
outlink_name: str
terminal_node_name: str
active_timestep_count: int
transferred_vehicle_count: int
```

保存しないもの:

- 対象Node名
- configured horizon
- 平均流出率
- Nodeオブジェクト
- Linkオブジェクト
- Vehicleオブジェクト
- pending情報

対象Node名は親のNode結果に存在するため、outlink結果へ重複保存しない。

`outlink_name`と`terminal_node_name`は空でない文字列とする。

`active_timestep_count`と`transferred_vehicle_count`は、boolではない非負整数とする。

#### 対象Node 1つ分

正式名称:

```python
OrderControlBaselineDownstreamBoundaryNodeResult
```

正式フィールド:

```python
node_name: str
outlink_results: tuple[
    OrderControlBaselineDownstreamBoundaryOutlinkResult,
    ...
]
```

`node_name`は空でない文字列とする。

`outlink_results`は、そのNodeの実在outlinkをネットワーク登録順で保存する。

outlinkが0本の対象Nodeは正式研究条件では想定しないが、今回のobserverは存在しないoutlinkを補完しない。

対象Nodeの妥当性は、既存のtarget Node準備とeligibility契約を前提とする。端点が誤ってorder control対象になる特殊構造を防ぐ新しい実行時検査は追加しない。

#### baseline全体分

正式名称:

```python
OrderControlBaselineDownstreamBoundaryResult
```

正式フィールド:

```python
node_results: tuple[
    OrderControlBaselineDownstreamBoundaryNodeResult,
    ...
]
```

`node_results`は`target_node_names`順とする。

configured horizonは既存`OrderControlBaselineForkResult.configured_horizon_steps`にあるため、下流境界結果へ重複保存しない。

全体結果へ平均率や観測statusを追加しない。未観測は`OrderControlBaselineForkResult.downstream_boundary_result is None`で表す。

### 同じ終端Nodeを共有するoutlink

次のようなネットワークを正式に扱う。

```text
対象Node A
  A → B

対象Node D
  D → B
```

または、

```text
対象Node A
  A → B
  A → C

対象Node D
  D → B
```

終端Node Bが共通でも、

- `A → B`
- `D → B`

は別の監視対象outlinkである。

結果は終端Node名だけで統合しない。

一回のBの`Node.transfer()`直前に、Bの`incoming_vehicles`から、

- `vehicle.link is A_to_B`
- `vehicle.link is D_to_B`

を別々に識別する。

一回のBの`Node.transfer()`後に、それぞれのcapture済みVehicleが元のoutlinkを離れたかを別々に判定する。

Node結果は、それぞれのorigin対象Nodeの下へ保存する。

内部索引は終端Nodeから監視outlink一覧を引けるようにする。export順の正本は、対象Node登録順と各Nodeのoutlink登録順である。索引用辞書の走査順を結果順にしない。

### 結果順序

正式な結果順序:

1. 対象Nodeは、`fixed_target_node_names`または`target_node_names`の入力順
2. 各対象Nodeのoutlinkは、`node.outlinks`のネットワーク登録順

Link名による追加sortは行わない。

既存snapshot物理順がinlink登録順を利用している方針とも整合させる。

結果順序をsetや辞書の偶然の走査順へ依存させず、登録時に明示的なlistまたはtupleとして固定する。

内部索引として辞書を使う場合も、export順の正本は登録時の明示的な順序構造とする。

### baseline結果への接続

`OrderControlBaselineForkResult`へ、次の必須フィールドを追加する。

正式フィールド名:

```python
downstream_boundary_result: (
    OrderControlBaselineDownstreamBoundaryResult | None
)
```

意味:

```text
None
→ baseline forwardを実行しておらず、下流境界を観測していない
```

```text
OrderControlBaselineDownstreamBoundaryResult
→ baseline forwardを実行し、設定horizonについて下流境界を観測した
```

フィールドにデフォルト値を設けない。

必須引数とする。

理由:

- 設定漏れと意図的な未観測を区別する
- 既存テストhelperも状態を明示する
- 空tupleの暗黙デフォルトで未観測を観測済みゼロに見せない

既存の`collector`フィールドの意味を変えない。

`OrderControlBaselineForkResult`自体は現行どおりnon-frozen dataclassのままとする。

下流境界結果の内部だけをfrozen構造にする。

`fork_W`は返さない。observer本体も`ForkResult`へ載せない。

### 空baseline結果

現在のbaseline driverでは、実時点Tのsnapshotで、指定されたTVT対象Nodeについてsnapshot固定Visitの登録総数が0の場合、

```text
registered_visit_count == 0
```

となり、baseline forwardを実行しない。

これは次の意味ではない。

- World全体にVehicleがいない
- baselineを実行した結果、意思決定窓内Vehicleが0だった
- 下流境界を観測したところ途中通過Vehicleが0だった

snapshot固定Visit登録後、baseline実行前に登録総数が0と判明したため、forward自体を省略した状態である。

この場合:

```python
downstream_boundary_result = None
```

とする。

observerを生成・接続しない。

下流境界のactive countやtransfer countを0として作らない。

理由:

- 0は観測済みを意味する
- この経路ではhorizon観測を実行していない
- TVT候補も形成されない
- 候補別局所仮想計算にも進まない

局所仮想計算が`downstream_boundary_result is None`の通常空経路へ進むことはない。

その不変条件の具体的な後続検査は、局所仮想計算接続仕様で必要に応じて定める。今回は実装しない。

### baseline実行済みでcountが0の場合

baseline forwardを実際に設定horizon全体について実行した場合は、全監視対象outlinkについて結果を返す。

途中通過Vehicleが一度も終端Nodeの`incoming_vehicles`に現れなかったoutlinkは、

```text
active_timestep_count = 0
transferred_vehicle_count = 0
```

となる。

この状態は観測済みである。

考えられる状況には少なくとも次がある。

- そのoutlink上にVehicleが一台も存在しなかった
- Vehicleは存在したが、horizon中にoutlink終端まで到達しなかった
- 終端へ到着したVehicleがすべて目的地到着Vehicleであり、途中通過Vehicleがいなかった
- 途中通過Vehicleによる下流通過要求がhorizon中に生じなかった

このobserverは理由を分類しない。

観測したcountだけを返す。

後段の局所仮想計算では、有力な既存基本設計として次を使う予定である。

- 終端NodeがVehicleの目的地なら通常のtrip-end
- 終端Nodeが目的地でないVehicleには、outlink流出容量と終端Node容量による制約付き境界流出
- 下流Link流入容量は使わない

ただし、この局所処理のPython実装は今回の対象外である。

### activeとtransferの組合せ

正常な観測済み結果では、少なくとも次を区別する。

#### active 0、transfer 0

```text
active_timestep_count == 0
transferred_vehicle_count == 0
```

途中通過Vehicleの終端待ちをhorizon内に観測しなかった。

観測未実行ではない。

観測未実行は`downstream_boundary_result is None`で表す。

#### active 1以上、transfer 0

```text
active_timestep_count >= 1
transferred_vehicle_count == 0
```

途中通過Vehicleが待っていたが、horizon内に一台も次Linkへ進めなかった。

後段ではhorizon内閉塞の材料になる。

observerは閉塞statusや平均率を保存しない。

#### active 1以上、transfer 1以上

```text
active_timestep_count >= 1
transferred_vehicle_count >= 1
```

途中通過Vehicleの待機と実流出があった。

後段で条件付き平均流出率を計算する材料になる。

#### active 0、transfer 1以上

通常の観測契約では起こらない重大不整合である。

途中通過Vehicleがtransferしたなら、その直前には当該outlink由来で`incoming_vehicles`に存在し、activeとなるはずである。

observerの公開結果作成時またはcommit時に、この状態をわざわざ重複検査するかは、明示的な追加検査を増やさない方針に従う。

実装上の処理順から自然に発生しないように構築し、専用テストで保証する。

処理順:

1. capture時に1台以上保持したoutlinkだけをactive候補とする
2. commit時に、そのactive候補だけ`active_timestep_count`を1増やす
3. transferred countは、同じcapture保持Vehicleのうち、`link is not None`かつ`link is not monitored_outlink`の台数だけ増やす

保持Vehicleがいないoutlinkのtransfer countは増やさない。

### 平均率の計算責任

baseline observerとbaseline結果には、次だけを保存する。

- `active_timestep_count`
- `transferred_vehicle_count`

条件付き平均流出率を保存しない。

平均率候補:

```text
transferred_vehicle_count
/
active_timestep_count
```

この計算は、候補別局所仮想計算側で必要になった時点で行う。

observerは次を行わない。

- active=0時の除算
- active>0かつtransfer=0時の閉塞判定
- service rate保存
- 流出許可残高
- sink fallback
- 容量制約適用

理由:

- observerは観測事実を保存する部品である
- 条件付き平均境界方式は局所仮想計算の近似方式である
- 観測部品と近似適用部品の責務を混在させない
- 将来、局所側の境界方式を変更してもbaseline観測結果を再利用できる

### `World.exec_simulation()`への接続

`World.exec_simulation()`内の次の既存共通ループへ、observer hookを追加する。

既存概念:

```python
for node in W.NODES:
    node.transfer()
```

実装後の概念:

```text
for each node:

    observerをWorld属性から取得

    observerが存在する場合:
        node.transfer()直前のcaptureを呼ぶ

    try:
        node.transfer()

        observerが存在する場合:
            正常終了後のcommitを呼ぶ

    finally:
        observerが存在する場合:
            そのtimestepのpendingを破棄する
```

observer取得や条件分岐は、可読性を優先して明示的に書く。

高度なcontext managerやdecoratorへ抽象化しない。

observerが`None`の場合:

- captureしない
- commitしない
- clearしない
- `incoming_vehicles`を走査しない
- RNGを消費しない
- Vehicle、Node、Link、capacityを変更しない
- 通常UXsimの結果を変えない

Nodeのtransfer順序を変更しない。

標準、FCFS、BATCHの`Node.transfer()`内部へ境界observer通知を追加しない。

`W.rng`と`W.order_control_rng`を観測処理から呼ばない。

User設定の`Node.user_function`および`World.user_function`を上書きしない。

### transfer例外時の扱い

`node.transfer()`が例外を出した場合:

- `commit_after_transfer()`を呼ばない
- `finally`で`clear_pending()`を呼ぶ
- 失敗したtimestepのactiveやtransferを正式累計へ加えない
- 例外を捕捉して正常化しない
- 元の例外を上位へ伝える
- baseline計算を停止する
- `OrderControlBaselineForkResult`を返さない
- 候補別局所仮想計算へ進まない

過去の正常timestepでobserver内部に累計済みの値は、例外発生時に全消去しなくてよい。

ただし、baseline driverが結果を返さないため、部分累計を正常結果として外部へ返さない。

例外原因を修正した後は、実Worldシミュレーションを最初から手動でやり直す。

次は実装しない。

- 自動修復
- 自動再実行
- baseline計算だけの自動再試行
- 途中時点からの再開
- 部分結果利用

BATCHの`transfer_batch()`は、例外時に`incoming_vehicles`を変えず例外を伝播する。observerはそれを解釈せず、commitせずpendingを捨てる。

### driverでのobserver準備

通常baseline経路`run_snapshot_fixed_baseline_fork()`と、TVT順位台帳登録付き経路`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()`は、どちらも`_complete_baseline_fork_after_registration()`へ合流する。

監視対象登録とobserver接続は、この共通経路で行う。

処理順:

1. snapshot固定Visit登録
2. registered Visit countの整合確認
3. `registered_visit_count == 0`なら空結果を返す
   - observerを生成しない
   - `downstream_boundary_result=None`
4. 非空経路なら残りhorizonの検証
5. observer生成
6. `fixed_target_node_names`順に対象Nodeを取得
7. 各対象Nodeの`node.outlinks`を登録順でobserverへ登録
8. fork Worldの正式observer属性へ接続
9. `fork_W.exec_simulation(...)`
10. baseline forward完了検証
11. Visit count再整合
12. real_W不変検査
13. observerからfrozen resultをexport
14. completed baseline resultへ格納

observer準備時点は、snapshot登録完了後、登録件数整合確認後、baseline forward開始前とする。

二重登録`ValueError`はforward開始前に起きる。その場合も`ForkResult`を返さない。

export時にpendingが残っていれば`RuntimeError`とし、部分結果を返さない。

### real_W不変

既存driverは、少なくとも次についてreal_W不変を確認する。

- `real_W.T`
- `real_W.TIME`
- `real_W._order_control_baseline_collector`

新observer属性についても、real_Wでは実行前後とも`None`のままであることを確認する契約を追加する。

`_BaselineForkPrepared`へ、必要ならreal Worldのobserver参照を保存する。既存collectorの`real_world_collector_before`と同じ形でよい。

正式研究経路では開始前に`None`を要求する。real_Wにobserverが付いている場合は、既存collector契約と同様に入力エラーとする。

fork側だけにobserverを接続する。

copy直後のfork observerが`None`であることも、既存collectorのcopy検査と同様に確認する。

ただし、同じ不変条件を各timestepで重複検査しない。

### 既存ForkResult生成箇所の更新

`OrderControlBaselineForkResult`へ必須フィールドを追加するため、既存の直接生成箇所をすべて更新する。

本番コード:

- `uxsim/order_control_baseline_driver.py`
  - `_build_empty_baseline_result()` → `downstream_boundary_result=None`
  - `_build_completed_baseline_result()` → observerの`export_result()`

既存テストhelper:

- `tests_order_control_tvt_arrived_undetermined_confirmation.py`
- `tests_order_control_tvt_candidate_visit_set.py`
- `tests_order_control_tvt_inlink_candidate_physical_order.py`
- `tests_order_control_tvt_leading_nonparticipating_confirmation.py`
- `tests_order_control_tvt_right_of_entry_selection.py`

検索により、実装時点の全`OrderControlBaselineForkResult(`を再確認する。

テストhelperでは、当該テストが下流境界を使用しない場合でも、新必須フィールドを明示する。

既存helperの意味に応じて、

- 非空baselineを模擬するなら、最小の読取専用結果
- 空baselineを模擬するなら`None`

を指定する。

無関係なテストを通すためだけにフィールドへ安易なデフォルト値を追加しない。

### 目的地到着Vehicleと途中通過Vehicle

既存基本設計を維持する。

目的地到着Vehicle:

```text
monitored_outlink.end_node is vehicle.dest
```

- `single_trip`では`incoming_vehicles`に入らない
- active対象外
- transferred count対象外
- 平均率対象外
- 通常のtrip-end

途中通過Vehicle:

```text
monitored_outlink.end_node is not vehicle.dest
```

- `incoming_vehicles`に入る
- active対象
- transferred count対象
- 後段の平均率対象

captureは、目的地判定を改めて各Vehicleへ重複実行するのではなく、`incoming_vehicles`に入っている途中通過Vehicleを対象とする。

ただし、commitでは`vehicle.link is not None`を要求し、走行終了を途中通過成功として誤計上しない。

`taxi`固有処理を初期実装の一般規則として採用しない。

### 単車線物理順

現在の正式研究範囲は単車線である。複車線への完全対応は初期実装範囲外である。

前方が途中通過Vehicle、後方が目的地到着Vehicleの場合:

- 後方Vehicleは前方を追い越してtrip-endしない
- 前方Vehicleが元のoutlinkを離れた後、後方Vehicleが物理先頭になってtrip-endする
- 目的地Vehicleを平均境界の対象外としても、追越しを意味しない

observerは物理順を変更しない。

observerがVehicleの`end_trip()`を直接呼ばない。

### 内部状態

登録後に固定し、各timestepで再検証しないもの:

- 対象Node名の明示的な順序tuple
- 各対象Nodeのoutlink名の明示的な順序tuple
- `(origin_node_name, outlink_name)`から累計スロットへの索引
- 終端Nodeから、そのNodeを終端とする監視outlink一覧への索引
- 監視outlinkオブジェクト参照（capture時の`is`判定用。export結果には残さない）

実行中だけ持つもの:

- 現在のpending。終端Node1つ分
- pending対象Node
- outlinkごとの保持Vehicleリスト
- そのtimestepのactive候補

確定累計:

- 各監視outlinkの`active_timestep_count`
- 各監視outlinkの`transferred_vehicle_count`
- 初期値はPythonの`int`の`0`
- 加算は`+= 1`

pendingと確定累計を別属性として持つ。混在させない。

### 実行時検査の方針

登録時に保証済みの不変条件を、各timestepで重複検証しない。

登録時に検証する事項:

- non-empty name
- 対象Node
- 実在outlink
- outlinkと開始Nodeの関係
- 終端Node
- 同一outlink二重登録
- 登録順
- `DELTAN=1`はorder-control設定入口

実行時に確認する事項:

- pending中の二重capture
- captureとcommitのNode不一致
- pendingなしcommit
- pendingありexport
- transfer後の`vehicle.link`
- 例外時のpending破棄

原因不明の停止や誤計上を防ぐ重大不整合だけを必要最小限に検査する。

### 実装時の可読性方針

研究用コードでは正しく動くことを最優先とする。

その上で、時間価値取引の根幹部分では、短さや高度なPython技法より、初学者が後から理解しやすい明示的な実装を優先する。

具体的には次を守る。

- 過度な内包表記を避ける
- 複雑なone-linerを避ける
- 状態遷移を明示する
- pendingと確定累計を別の属性として持つ
- 登録順の正本を明示的なlistまたはtupleで保持する
- 索引用辞書と結果順の正本を混同しない
- capture、commit、clearの責務を分ける
- 例外時の処理を明示的に書く
- World hookを過度に抽象化しない
- 変数名でNode、outlink、terminal Node、Vehicleを区別する
- 実装済みの確定仕様を、巧妙な一般化で置き換えない

### 専用テストファイル

新規専用テストファイルの正式名称:

```text
tests_order_control_baseline_downstream_boundary.py
```

既存プロジェクトのテスト実行方式に合わせる。

既存テストがファイル末尾の`TESTS`一覧と直接実行を使う場合は、その流儀へ合わせる。

pytest専用の仕組みを突然導入しない。

DELTAN validatorの設定入口テストは、実装単位2の対象である。専用observerテストへ無理に混在させず、既存のNode order-control設定テストへ追加するか、専用ファイル内の独立節として明示する。実装時に既存テスト配置を再確認する。

### observer単体テスト契約

少なくとも次を含める。

#### 結果型

- 3つの結果型がfrozen
- outlink結果のフィールドが確定仕様どおり
- Node結果がoutlink tupleを保持
- 全体結果がNode tupleを保持
- 結果にNode、Link、Vehicle、World参照を含めない
- 結果作成後にobserver内部が変化しても、既存結果が変化しない

#### 登録

- 単一対象Node、単一outlink
- 一つの対象Nodeに複数outlink
- 複数対象Node
- 同じ終端Nodeを共有する複数outlink
- target Node順を維持
- outlink登録順を維持
- 存在しない逆方向Linkを補完しない
- 同一outlink二重登録で`ValueError`
- エラー文にNode名とoutlink名
- 二重登録失敗で既存正常登録を壊さない

#### capture

- 対象外Nodeでは何も起きない
- 監視対象終端Nodeで、対象outlink由来のincoming Vehicleを保持
- 同一終端Nodeの別outlinkを区別
- 同一outlinkに複数Vehicleがいてもactive候補は一回
- pending中の二重captureで`RuntimeError`
- captureだけでは正式累計を増やさない

#### commit

- 元のoutlinkのままならtransfer countを増やさない
- 次Linkへ変わったら1増やす
- 複数Vehicleが移動したらその数だけ増やす
- `vehicle.link is None`なら増やさない
- capture時にVehicleがいたoutlinkだけactiveを1増やす
- captureと異なるNodeのcommitを拒否
- pendingなしcommitを拒否
- 同じ終端Nodeを共有するoutlinkを別々に集計
- commit後に正しい結果をexport可能

#### clear_pending

- capture後にpendingだけを破棄
- 過去の確定累計を消さない
- pendingなしでは安全なno-op
- clear後に次のcaptureが可能

#### export

- 登録順で3段結果を返す
- pendingが残る状態で`RuntimeError`
- countが非負整数
- 平均率を含まない
- observer本体を返さない

### UXsim hookテスト契約

少なくとも次を含める。

- observer属性の初期値が`None`
- observerが`None`なら既存の`node.transfer()`呼出順が変わらない
- observerが`None`なら`incoming_vehicles`の追加走査を行わない
- observerが`None`なら乱数状態を変えない
- observerがある場合にcapture、transfer、commit、clearの順
- transfer正常終了後にcommit
- transfer例外時にcommitしない
- transfer例外時にもclear
- 元の例外をそのまま伝える
- 標準Node
- FCFS Node
- BATCH Node
- 各個別transfer実装へobserver通知を追加していない
- Nodeの順序を変えない
- route choice、capacity、Vehicle順序を変えない
- user_functionを上書きしない

### driver統合テスト契約

少なくとも次を含める。

#### 非空baseline

- observerをforkだけへ接続
- real_W observerは`None`
- copy直後のfork observerは`None`
- baseline forward直前に登録
- configured horizon全体を観測
- `downstream_boundary_result`がNoneではない
- target Node順
- outlink登録順
- active 0、transfer 0の観測済み結果
- active 1以上、transfer 0
- active 1以上、transfer 1以上

#### 空baseline

- `registered_visit_count == 0`
- `fork_steps_executed == 0`
- `exec_simulation()`を呼ばない
- observerを生成・接続しない
- `downstream_boundary_result is None`
- 0 countの観測済み結果を作らない

#### 通常経路とTVT順位台帳付き経路

- 両方が同じobserver準備経路へ合流
- 同じWorld状態とtarget Node集合なら、同じ下流境界結果
- 既存Visit collector結果を壊さない

#### 失敗

- observer登録失敗ならbaseline forwardを開始しない
- transfer例外ならForkResultを返さない
- pendingを破棄
- 部分結果を外部へ返さない
- real_W不変
- 自動再実行しない

#### ForkResult

- 新必須フィールドが存在
- 完了結果ではfrozen result
- 空結果ではNone
- `fork_W`を保持しない
- observer本体を保持しない

### DELTAN検証テスト契約

少なくとも次を含める。

#### Node作成時

- `DELTAN=1`かつ`order_control_type="fcfs"`で成功
- `DELTAN=1`かつ`"batch"`で成功
- `DELTAN=1`かつ`"time_value"`で成功
- `DELTAN!=1`かつ各方式で`ValueError`
- `order_control_type="none"`ではDELTANが1以外でもこのvalidatorを理由に拒否しない
- エラー前にNodeのorder-control設定を部分変更しない
- エラー文に実際のDELTAN
- エラー文にFCFS、BATCH、TVT
- エラー文にindividual Vehicle objectsを制御する趣旨

#### `set_order_control_for_nodes()`

- `DELTAN=1`で各方式成功
- `DELTAN!=1`で各方式`ValueError`
- 複数Nodeの一部だけを先に変更しない
- `none`への解除ではこのvalidatorを理由に拒否しない
- ランダム選択経路はsetterへの合流で検査され、別の重複validatorを持たない

#### 頻度

- baseline driverでDELTAN再検証しない
- observerでDELTAN再検証しない
- timestepでDELTAN再検証しない
- VehicleごとにDELTAN再検証しない

### 既存回帰テスト

実装後、少なくとも次を実行する契約とする。実装時にファイル名と実行方法を実リポジトリから再確認する。

- 新規専用テスト
- `tests_order_control_baseline_driver.py`
- `tests_order_control_baseline_collector.py`
- `tests_order_control_baseline_collector_uxsim.py`
- `tests_order_control_baseline_snapshot.py`
- `tests_order_control_tvt_arrived_undetermined_confirmation.py`
- `tests_order_control_tvt_candidate_visit_set.py`
- `tests_order_control_tvt_inlink_candidate_physical_order.py`
- `tests_order_control_tvt_leading_nonparticipating_confirmation.py`
- `tests_order_control_tvt_right_of_entry_selection.py`
- Node order-control属性・設定関連テスト
- FCFS transfer関連テスト
- BATCH transfer関連テスト
- BATCH Level 2関連テスト

全テストを盲目的に一括実行するだけでなく、新規単体、接続、driver、関連回帰の順に確認する。

### 実装順序

#### 実装単位1

新規モジュールとobserver単体テスト。

対象:

- 3つのfrozen結果型
- observer
- 登録
- capture
- commit
- clear
- export
- 二重登録
- pending
- `vehicle.link is None`非加算

この時点では`uxsim.py`へhookしない。

`World.exec_simulation()`、baseline driver、`ForkResult`、DELTAN validator、既存テストhelperはまだ変更しない。

#### 実装単位2

order control共通`DELTAN=1` validatorと設定入口テスト。

対象:

- `_validate_order_control_deltan`
- Node作成時
- `set_order_control_for_nodes()`
- ランダム経路の非重複
- FCFS、BATCH、TVT
- none非対象

observer本体と混同せず、order control全体の不変条件として実装する。

#### 実装単位3

World属性と`exec_simulation()`共通hook。

対象:

- World属性None
- capture
- `node.transfer()`
- commit
- finally clear
- observerなし回帰
- 例外伝播
- RNG非侵襲性

標準、FCFS、BATCH内部へ通知を追加しない。

#### 実装単位4

baseline driver、ForkResult、既存helper更新、統合テスト。

対象:

- observer準備
- target Node/outlink登録
- empty result None
- completed result
- mandatory ForkResult field
- real_W不変
- 通常baseline経路
- 順位台帳付き経路
- 既存ForkResult helper更新
- 統合テスト

#### 実装後

- 詳細正本へ実装完了記録
- `ORDER_EXCHANGE_PROGRESS.md`へ概略
- 実装済み範囲
- テスト結果
- 未実装境界
- 次の作業開始点

### コミット境界

実装途中のコミット境界は、実際の変更状態とテスト結果を見てCopilotと利用者が判断する。

概念上の候補:

1. observer本体と専用単体テスト
2. DELTAN共通validatorと設定入口テスト
3. World hookと接続テスト
4. baseline driver、ForkResult、統合テスト
5. 実装完了の文書記録

ただし、無理に5コミットへ固定しない。

一つの実装単位が次の単位なしでは正常に動かず、独立した安全な保存点にならない場合は、関連単位をまとめてよい。

Git操作は利用者がTerminalで行う。

Cursorは確認・報告だけを行い、Git変更操作をしない。

メモを含むコミット名には`document`を含める。

### 今回の未実装範囲

今回のMarkdown記録時点では、次は未実装である。Python実装済み、テスト済みとは記載しない。

- `uxsim/order_control_baseline_downstream_boundary.py`
- 3つの結果型
- observer
- observer World属性
- `exec_simulation` hook
- `_validate_order_control_deltan`
- order-control設定入口へのvalidator接続
- baseline driver observer準備
- ForkResult新フィールド
- empty result None
- completed result export
- 専用テスト
- 既存helper更新

次も引き続き未実装であり、本部品の後段である。

- 条件付き平均流出率の算出
- 流出許可残高
- 制約付きsink
- 局所mimic World
- inlink始端新規流入
- TVT候補別局所仮想計算全体
- 経済性評価
- 成立候補選択
- 実WorldへのTVT反映

### 次の作業開始点

保存済み完全実装前仕様に従い、まず次を実装する。

- 新規本番モジュール: `uxsim/order_control_baseline_downstream_boundary.py`
- 新規専用テスト: `tests_order_control_baseline_downstream_boundary.py`

最初の実装単位:

- 3つのfrozen結果型
- `OrderControlBaselineDownstreamBoundaryObserver`
- outlink登録
- capture
- commit
- clear
- export
- 二重登録
- pending管理
- `vehicle.link is None`非加算
- 専用単体テスト

この最初の実装単位では、まだ次を変更しない。

- `World.exec_simulation()`
- baseline driver
- ForkResult
- DELTAN validator
- 既存テストhelper
- 局所仮想計算
- 経済性評価

実装開始前に、新規モジュールが`uxsim.py`をimportすると循環参照を起こす可能性を確認する。

必要ならduck typingまたは`TYPE_CHECKING`を使用するが、過度な抽象化は避ける。

基本設計の観測方法は再考しない。条件付き平均率、流出許可残高、局所mimic World、inlink始端、経済評価へ進まない。FIFO検査接続部品を再考しない。

## 全World baseline下流境界観測部品の実装完了記録

記録日：2026-09-20

本節は、直前の「全World baseline下流境界観測部品の完全な実装前仕様」を置き換えない。当該仕様は実装前の設計正本として残す。本節は、2026-09-20時点で実装・検証・commit・push済みとなった事実の正本である。

### 非技術的な完了内容

全World baseline計算（実Worldをcopyしたfork World上で、設定horizonだけ先に進める計算）の実行中に、TVT対象交差点から出る各道路（outlink）の終端Nodeにおいて、途中通過Vehicleが待っていた状態と、実際に先の道路へ進めた台数を観測できるようになった。

observerは実Worldには接続しない。snapshot固定Visitの登録とcollector接続のあと、baseline forwardを実行するのはcopy後のfork Worldだけである。fork Worldの正式属性`_order_control_baseline_downstream_boundary_observer`へだけobserverを接続する。

baseline forwardが正常に完了したあと、呼び出し側へ返るのはWorldオブジェクトやobserver本体ではなく、Link名・終端Node名・非負整数のcountだけを含む読取専用（frozen）結果である。これは`OrderControlBaselineForkResult`の必須フィールド`downstream_boundary_result`から取得する。

この観測結果は、将来の候補別局所仮想計算において、下流側の受入れにくさを近似するための材料である。条件付き平均流出率の計算、平均率の保存、流出許可残高、制約付きsink、局所mimic Worldへの適用は、本実装の範囲外であり、まだ実装していない。

### 実装済み範囲

#### observer本体（専用モジュール）

- 本番モジュール：`uxsim/order_control_baseline_downstream_boundary.py`
- 専用単体テスト：`tests_order_control_baseline_downstream_boundary.py`
- observer正式名：`OrderControlBaselineDownstreamBoundaryObserver`
- World正式属性名：`_order_control_baseline_downstream_boundary_observer`（`uxsim/uxsim.py`上。初期値`None`）
- 公開API：
  - `register_target_node_outlinks(target_node)`
  - `capture_before_transfer(node)` → 監視対象終端なら`True`（pending作成）、非監視なら`False`
  - `commit_after_transfer(node)`
  - `clear_pending()`
  - `export_result()`
- 3段frozen結果型：
  - outlink別：`OrderControlBaselineDownstreamBoundaryOutlinkResult`
  - 対象Node別：`OrderControlBaselineDownstreamBoundaryNodeResult`
  - 全体：`OrderControlBaselineDownstreamBoundaryResult`
- **active**（`active_timestep_count`）：監視対象outlinkの終端Nodeで`Node.transfer()`が呼ばれる直前に、そのoutlink上にさらに先へ進もうとして待っている途中通過Vehicleが1台以上いるtimestepを1回として数える。
- **transfer**（`transferred_vehicle_count`）：capture時に保持した途中通過Vehicleのうち、正常なtransfer処理のあと`vehicle.link`が`None`（trip-end）でもなく、かつ元の監視outlinkでもない台数を数える。
- **目的地到着Vehicle**：監視outlinkの`end_node`がVehicleの目的地である場合、通常のtrip-end経路となり、activeおよびtransferの集計対象外である。
- Nodeを端点・内部で固定分類せず、Vehicleごとの目的地とoutlink終端の関係で判定する。
- `cum_departure`差を正式な実流出台数の正本にしない。
- observerはVehicleの交通状態、物理順、RNGを変更しない。

observer本体の実装・検証コミット（git履歴で確認済み）：

- `68bc8aa` — `Document the pre-implementation specification for TVT downstream boundary observation`（完全実装前仕様の文書。Python本体はこのコミットでは未実装）
- `f475294` — `Implement the downstream boundary observer core and tests`

#### UXsim共通transfer loop hook

- `World.exec_simulation()`内の、全Nodeに対する共通`node.transfer()`呼出位置へ接続済み。
- 標準、`Node.transfer()`、FCFSの`transfer_fcfs_clearance()`、BATCHの`transfer_batch()`の**内部**へobserver通知を重複追加していない。
- observer属性が`None`の通常経路では、capture・commit・clearを行わず、既存UXsimの結果を変えない。
- `capture_before_transfer()`が`True`を返した場合のみ、そのtimestepでcapture → transfer → 成功時commit → `finally`で`clear_pending()`。
- transferが例外を出した場合はcommitせず、`finally`でpendingを破棄する。

実装コミット：

- `c72e38a` — `Connect the downstream boundary observer to the UXsim transfer loop in preparation for TVT local virtual calculation`

専用接続テスト：`tests_order_control_baseline_downstream_boundary_uxsim.py`

### DELTAN=1の共通設定時検査

- `DELTAN=1`はTVTだけでなく、FCFS・BATCH・TVTに共通するorder control前提である。
- `Node`作成時と`World.set_order_control_for_nodes()`で、order controlを有効化する入口において検査する。
- timestepごと、baselineごと、observerごとに重複検査しない。
- 検査処理名：`_validate_order_control_deltan`（`uxsim/uxsim.py`）
- 実装コミット：`7c1d5a4` — `Enforce DELTAN one for FCFS, BATCH, and TVT order control`
- 専用テスト：`tests_order_control_deltan.py`（17件成功）

文献ポジショニング用メモのコミット`9174abf`（`Document the three-stage literature positioning framework for TVT-MP`）は、下流境界observer実装の主要コミットではない。

### baseline driverへの正式接続

observer本体とhookは、baseline driver接続**以前**のコミットで実装済みである。baseline driverへの正式接続は別コミットである。

- 本番ファイル：`uxsim/order_control_baseline_driver.py`
- 通常経路`run_snapshot_fixed_baseline_fork()`と、順位台帳登録付き経路`run_snapshot_fixed_baseline_fork_with_tvt_rank_ledger_registration()`は、従来どおり共通の`_complete_baseline_fork_after_registration()`へ合流する。
- observerの生成、対象Node/outlink登録、fork World属性への接続は、snapshot固定Visit登録と`registered_visit_count`の整合確認のあと、`fork_W.exec_simulation(...)`直前に**一度だけ**行う。
- 準備helper：`_prepare_downstream_boundary_observer_for_fork(fork_W, fixed_target_node_names=...)`
- helperの処理順：
  1. `fork_W._order_control_baseline_downstream_boundary_observer`が`None`であることを確認（非`None`なら`RuntimeError`）
  2. 新しい`OrderControlBaselineDownstreamBoundaryObserver`を生成
  3. `fixed_target_node_names`の入力順に`fork_W.get_node(node_name)`で対象Nodeを取得
  4. 各Nodeで`observer.register_target_node_outlinks(target_node)`（outlink順は`node.outlinks`登録順をobserverへ委ねる）
  5. 全登録が成功した場合にだけ、fork Worldの正式属性へobserverを接続
  6. observerを呼出側へ返す（`export_result()`はhelper内では呼ばない）
- 登録途中で例外が起きた場合、部分登録済みobserverをfork World属性へ接続しない。
- forward開始直前に`fork_timestep_before = prepared.fork_W.T`を保存する。
- forward完了後に、既存の完了検証（`fork_W.T`の進み、終端前余裕）、Visit count再整合、実World不変検査を実行する。
- それらがすべて成功したあと、呼出側で`observer.export_result()`を**一度だけ**実行し、返却されたfrozen結果を完了baseline結果へ格納する。

実装コミット：

- `7f00520` — `Integrate downstream boundary observation into the baseline driver`

専用統合テスト：`tests_order_control_baseline_downstream_boundary_driver.py`（新規）

### OrderControlBaselineForkResultの変更

- 既存フィールドの後方へ、必須フィールドを追加した（デフォルト値なし）：

```python
downstream_boundary_result: (
    OrderControlBaselineDownstreamBoundaryResult | None
)
```

- `None`：baseline forward自体を実行しておらず、下流境界を観測していない（`registered_visit_count == 0`の空baseline経路）。
- frozen結果：設定horizon全体について下流境界を観測した完了baseline。
- 観測済みcountがすべて0でも、forwardを実行した完了baselineではfrozen結果を返す。未観測の`None`と区別する。
- `fork_W`とobserver本体は`ForkResult`へ格納しない。
- 既存の`OrderControlBaselineForkResult(`直接生成箇所（本番driverのempty/completed builder、後続TVTテストhelper）を、新必須フィールド明示で更新した。

### 空baseline

- `registered_visit_count == 0`の場合：
  - observerを生成しない
  - fork Worldへobserverを接続しない
  - `exec_simulation()`を呼ばない
  - `downstream_boundary_result = None`
  - `fork_steps_executed = 0`
  - count 0のfrozen境界結果を作らない
- これは候補別局所仮想計算へ進む通常の非空baseline経路ではない。

### 実World不変条件

- baseline fork開始前：`real_W._order_control_baseline_downstream_boundary_observer`が`None`でなければ`ValueError`。エラー文に`must be None before baseline fork`と実際の値を含む。
- copy直後：`fork_W._order_control_baseline_downstream_boundary_observer`が`None`でなければ`RuntimeError`。エラー文に`must be None immediately after copy`と実際の値を含む。
- `_BaselineForkPrepared`は`real_world_downstream_boundary_observer_before`を保持する（collectorの`real_world_collector_before`と同型の意図）。正式研究経路では開始前後とも`None`。
- return直前の既存実World不変検査に、`real_W.T`、`real_W.TIME`、`real_W._order_control_baseline_collector`とともに、observer属性の同一性（`is`）確認を統合した。各timestepでは重複検査しない。
- observerはreal Worldへ接続しない。

### 失敗時契約

**observer登録失敗時**

- 元の例外をそのまま伝播する。
- baseline forwardを開始しない。
- `OrderControlBaselineForkResult`を返さない。
- 部分observerをfork World属性へ接続しない。

**forward失敗時**（`fork_W.exec_simulation(...)`が例外）

- 例外を正常結果へ変換しない。
- `observer.export_result()`を呼ばない。
- `_build_completed_baseline_result()`を呼ばない。
- 部分`OrderControlBaselineForkResult`を返さない。
- 自動再試行しない。
- 原因修正後は、実Worldシミュレーションを最初から手動でやり直す。

**transfer失敗時**（hook契約）

- そのtimestepのpendingを`clear_pending()`で破棄する。
- 正常完了していないtransferを正式累計へcommitしない。
- baseline全体を停止し、driverは完了結果を返さない。

### 結果順序

- 全体の`node_results`は`target_node_names`（driver入力の固定順）に従う。
- 各Nodeの`outlink_results`は、そのNodeの`node.outlinks`登録順に従う。
- Link名によるsortはしない。
- 同じ終端Nodeを共有する別origin対象Nodeのoutlinkを、終端Node名で統合しない。
- origin対象Nodeごとの独立した境界結果を維持する。

### 更新ファイル（実装コミット`7f00520`）

`7f00520`で変更した8ファイル：

1. `uxsim/order_control_baseline_driver.py`
2. `tests_order_control_baseline_downstream_boundary_driver.py`（新規）
3. `tests_order_control_baseline_driver.py`
4. `tests_order_control_tvt_arrived_undetermined_confirmation.py`
5. `tests_order_control_tvt_candidate_visit_set.py`
6. `tests_order_control_tvt_inlink_candidate_physical_order.py`
7. `tests_order_control_tvt_leading_nonparticipating_confirmation.py`
8. `tests_order_control_tvt_right_of_entry_selection.py`

`7f00520`では、observer本体モジュール、`uxsim/uxsim.py`、Markdownは変更していない。observer本体とUXsim hookは、それ以前のコミット（`f475294`、`c72e38a`等）で実装済みである。

### 検証結果

2026-09-20にTerminalで独立確認したテスト群（単一の一括pytest実行ではない。群ごとに実行し、件数を合算した）。

| 群 | ファイル（代表） | 件数 |
| --- | --- | ---: |
| baseline driver統合（下流境界） | `tests_order_control_baseline_downstream_boundary_driver.py` | 15 |
| baseline driver既存 | `tests_order_control_baseline_driver.py` | 69 |
| observer本体 + UXsim hook | `tests_order_control_baseline_downstream_boundary.py`、`tests_order_control_baseline_downstream_boundary_uxsim.py` | 68 |
| DELTAN | `tests_order_control_deltan.py` | 17 |
| 後続TVT（ForkResult helper更新5群） | arrived / candidate / inlink physical order / leading / right-of-entry | 115 |
| collector・snapshot・BATCH transfer | `tests_order_control_baseline_collector.py`、`tests_order_control_baseline_collector_uxsim.py`、`tests_order_control_baseline_snapshot.py`、`tests_order_control_batch_node_transfer_integration.py`、`tests_order_control_batch_service_queue_transfer.py`、`tests_order_control_batch_transfer.py` | 209 |

**合計：493 tests passed**

上記8ファイルに対する`python -m py_compile`はすべて成功した。

最初の関連回帰確認では、存在しないファイル名`tests_order_control_fcfs_transfer.py`を指定したためpytest実行前に停止した。これはテスト失敗ではない。Terminalで実在する正式な関連テストファイル名を再確認し、collector・snapshot・BATCH transfer系の6ファイル（上表）を再実行して、209件すべて成功した。

### 保存済みコミットとpush状態

下流境界観測に関する主要実装コミット（時系列の概略）：

| hash | 内容 |
| --- | --- |
| `7c1d5a4` | FCFS・BATCH・TVT共通のorder control設定時`DELTAN=1`検査 |
| `f475294` | 下流境界observer本体と専用単体テスト |
| `c72e38a` | UXsim共通transfer loopへのobserver hook |
| `7f00520` | 全World baseline driverへの正式接続と`OrderControlBaselineForkResult`からのfrozen観測結果返却 |

- `7f00520`は`origin/feature/intersection-order-control`へpush済みである。
- 記録時点でローカルHEADと`origin/feature/intersection-order-control`は`7f00520`で一致する想定である（Git操作は文書記録時にCursorは行わない。利用者がTerminalで確認する）。
- 未追跡の`diagnostics/order_control.zip`は対象外である。

### 今回未実装

下流境界観測の**実装完了**は、候補別局所仮想計算全体の完成ではない。次は引き続き未実装である。

- 条件付き平均流出率
- 平均率の保存
- 流出許可残高
- 制約付きsink
- 局所mimic World
- inlink始端新規流入
- 候補別局所仮想計算
- 局所仮想計算結果型
- 経済性評価
- 買い手価値G
- 売り手必要補償R
- G >= R判定
- surplus
- 成立候補選択
- 同値候補選択
- 支払いと補償
- 実WorldへのTVT反映

### 次の直接作業

下流境界observerの本体、UXsim hook、`DELTAN=1`前提、baseline driver接続、および`OrderControlBaselineForkResult.downstream_boundary_result`の返却契約は、保存済み完全実装前仕様と本実装完了記録の範囲で**再考しない**。

次の作業候補は、候補別局所仮想計算へ進むために必要な残りの入力・境界設計を整理することである。少なくとも次が未確定である。

- inlink始端の新規流入
- 条件付き平均境界サービス率の正式採用
- active timestepとtransfer countからの平均率算出位置
- 流出許可残高
- active 0時の制約付きsink
- 局所mimic Worldの正式範囲
- 局所仮想計算の公開API
- 局所仮想計算の結果型
- resolved / unresolved条件

本節（2026-09-20文書記録）では、上記を新たに制度確定しない。

# 次の作業開始点

次の直接作業は、具体的買い手候補集合生成部品の実装前仕様を、既存の公開型と接続できる形で確定することである。

対象は次のとおりである。

- `BASELINE_INFORMATION_COMPLETE`の対象Nodeだけを処理する
- 権利保有inlinkを買い手候補から除外する
- `participates_by_visit_key`を使用する
- 買い手候補inlinkを抽出する
- 各inlinkについて空prefixから最大prefixまでを生成する
- 各inlinkのprefix直積を生成する
- 全空組合せだけを除外する
- 具体的買い手候補集合を正式baseline相対順へ並べる
- Node別結果型を設計する
- 専用テスト契約を確定する

この部品の実装・検証後に、非参加Visitあり・なしを統一する一般形順位再構成へ進む。

**2026-09-14更新：** 具体的買い手候補集合生成部品のAPI、結果型、例外、専用テスト契約を確定した。次の直接作業は、新規本番モジュール`uxsim/order_control_tvt_mp_concrete_buyer_candidate_set.py`と専用テスト`tests_order_control_tvt_mp_concrete_buyer_candidate_set.py`の実装である。実装後に一般形順位再構成の実装前仕様へ進む。局所仮想計算と経済性評価にはまだ進まない。最新詳細は、本ファイルの「具体的買い手候補集合生成部品の実装前仕様」を参照する。

**2026-09-15更新（最新の再開情報）：** 具体的買い手候補集合生成部品は実装・検証済みである。最新の実装完了事実は、本ファイルの「具体的買い手候補集合生成部品の実装完了記録」を参照する。次の直接作業は、非参加Visitあり・なしを統一する一般形順位再構成部品について、既存の非参加Visitなし順位計算部品と`preserves_inlink_fifo()`の契約を再確認し、確定済み空き順位枠方式を基礎に**実装前仕様**を確定することである。一般形順位再構成のコーディングを直ちに開始する、とは読み取らない。局所仮想計算と経済性評価にはまだ進まない。

**2026-09-15追記（最新の再開情報）：** 一般形順位再構成部品の実装前仕様を確定した。Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP一般形順位再構成部品の実装前仕様」を参照する。次の直接作業は、保存済み実装前仕様に従い`uxsim/order_control_tvt_mp_general_trade_rank.py`と`tests_order_control_tvt_mp_general_trade_rank.py`を実装することである。制度ロジックを再考しない。既存の非参加Visitなし順位計算部品と`preserves_inlink_fifo()`は変更しない。FIFO検査の実行、局所仮想計算、経済性評価には進まない。

**2026-09-15更新（最新の再開情報）：** 一般形順位再構成部品は実装・検証済みである。最新の実装完了事実は、本ファイルの「TVT-MP一般形順位再構成部品の実装完了記録」を参照する。実装前仕様の保存済み・push済みコミットは`3932f21`である。次の直接作業は、本部品が構築した`trade_scope`と`trade_order[:last_buyer_rank]`を材料とするFIFO検査接続部品の**実装前仕様**を確定することである。一般形順位再構成のPython実装を再考しない。`preserves_inlink_fifo()`自体は変更しない。局所仮想計算、経済性評価、成立候補選択には進まない。

**2026-09-15追記（最新の再開情報）：** FIFO検査接続部品の実装前仕様を確定した。Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP FIFO検査接続部品の実装前仕様」を参照する。一般形順位再構成部品の保存済み実装コミットは`1e23174`である。次の直接作業は、保存済み実装前仕様に従い`uxsim/order_control_tvt_mp_fifo_inspection.py`と`tests_order_control_tvt_mp_fifo_inspection.py`を実装することである。一般形順位再構成を再考しない。`preserves_inlink_fifo()`自体を変更しない。局所仮想計算、経済性評価、成立候補選択には進まない。

**2026-09-15更新（最新の再開情報）：** FIFO検査接続部品は実装・検証済みである。最新の実装完了事実は、本ファイルの「TVT-MP FIFO検査接続部品の実装完了記録」を参照する。実装前仕様の保存済み・push済みコミットは`25764b8`である。次の直接作業は、`preserves_inlink_fifo=True`の候補だけを対象とする候補別局所仮想計算接続部品の**実装前仕様**を確定することである。FIFO検査接続部品を再考しない。`preserves_inlink_fifo()`自体を変更しない。一般形順位再構成を変更しない。直ちに局所仮想計算を実装しない。まず既存の局所仮想計算関係の設計・部品・入力要件を確認する。経済性評価、成立候補選択には進まない。

**2026-09-18更新（最新の再開情報）：** FIFO検査接続部品は実装・検証・push済みである（保存済み実装コミット`33e6101`）。候補別局所仮想計算は未実装である。今回は完全な実装前仕様を確定せず、設計検討記録を追加した。通過試行順の基本方針は採用した。outlink終端の条件付き平均境界サービス方式は有力案である。inlink始端の新規流入、baseline境界観測の保存場所と観測位置、公開API、結果型等は未確定である。次の直接作業は、全World baseline実行中に各対象Nodeの各outlinkについて、終端Nodeのtransfer処理直前のactive状態と当該outlinkから終端Nodeを実際に通過した台数を、どこで・どの処理順で・どの単位で観測できるかを調査することである。この調査が終わるまでは完全な実装前仕様を作らない。直ちに局所仮想計算を実装しない。経済性評価、成立候補選択には進まない。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の設計検討記録」を参照する。

**2026-09-19更新（最新の再開情報）：** FIFO検査接続部品は実装・検証・push済みである（保存済み実装コミット`33e6101`）。保存済み最新の局所仮想計算設計検討コミットは`5dd4be9`である。候補別局所仮想計算は未実装である。下流境界観測の基本設計を確定した。`DELTAN=1`をTVT初期研究範囲の制度上の前提とする。activeは終端`Node.transfer()`直前の途中通過Vehicle待機で判定する。実流出台数は、transfer前に保持した途中通過Vehicleがtransfer後に元のoutlinkを離れた数とする。目的地到着Vehicleは集計対象外である。Node固定分類ではなくVehicleごとの目的地判定を使う。下流境界専用observerと独立した読取専用結果を使う方向である。公開API、結果型、例外契約、局所適用処理は未確定である。Python実装と専用テストは未着手である。次の直接作業は、今回の境界観測基本設計を前提に、下流境界観測部品の完全な実装前仕様に必要な残る設計判断を整理することである。判断対象は、observerの正式名称と責務、World属性名、登録API、transfer前後観測API、outlink別・対象Node別・全体結果型、`OrderControlBaselineForkResult`への追加フィールド、結果順序、active=0およびactive>0かつtransfer=0の表現、条件付き平均率の計算位置、`DELTAN=1`の検証位置、空baseline経路、失敗時の部分状態、専用テスト契約である。inlink始端新規流入、局所mimic World全体、経済性評価にはまだ進まない。直ちに局所仮想計算を実装しない。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の設計検討記録」にある「2026-09-19更新：下流境界観測の調査結果と基本設計の確定」を参照する。今回のMarkdown追記は記録時点では未コミットである。

**2026-09-19追記（最新の再開情報）：** 下流境界観測部品の完全な実装前仕様を確定した。保存済み基本設計コミットは`c2c98c0`である。Python実装と専用テストは未着手である。次の直接作業は、保存済み仕様に従い`uxsim/order_control_baseline_downstream_boundary.py`と`tests_order_control_baseline_downstream_boundary.py`を実装することである。まず新規observerモジュールと専用単体テストから着手する。3つのfrozen結果型、`OrderControlBaselineDownstreamBoundaryObserver`、登録、capture、commit、clear、export、二重登録、pending、`vehicle.link is None`非加算を最初の実装単位とする。この単位では`World.exec_simulation()`、baseline driver、ForkResult、DELTAN validator、既存テストhelperはまだ変更しない。既存基本設計は再考しない。条件付き平均率、流出許可残高、局所mimic World、inlink始端、経済評価へ進まない。最新詳細は、本ファイルの「全World baseline下流境界観測部品の完全な実装前仕様」を参照する。今回のMarkdown追記は未コミットである。

**2026-09-20更新（最新の再開情報）：** 下流境界observer本体、UXsim transfer loop hook、FCFS・BATCH・TVT共通の`DELTAN=1`設定時検査、全World baseline driverへの正式接続は、実装・検証・commit・push済みである。最新の下流境界関連実装コミットは`7f00520`（`Integrate downstream boundary observation into the baseline driver`）である。observer本体は`f475294`、UXsim hookは`c72e38a`、`DELTAN=1`検査は`7c1d5a4`で実装済みである。観測結果は`OrderControlBaselineForkResult.downstream_boundary_result`から取得する。空baselineは`None`、完了baselineは観測済みcount 0を含むfrozen結果である。専用統合テストを含む493件をTerminalで群ごとに独立確認し、すべて成功した。変更8ファイル（`7f00520`）の`py_compile`も成功した。下流境界observerの実装済み部分（本体・hook・DELTAN前提・driver接続・ForkResult返却契約）を再考しない。条件付き平均率、流出許可残高、局所mimic World、inlink始端新規流入、候補別局所仮想計算、経済性評価、成立候補選択、実WorldへのTVT反映は未実装である。次の直接作業は、候補別局所仮想計算へ進むために必要な残る入力・境界設計を整理することである。本節ではそれらを新たに確定しない。最新詳細は、本ファイルの「全World baseline下流境界観測部品の実装完了記録」を参照する。`diagnostics/order_control.zip`は対象外である。

# 新しいチャットでの再開方法

新しいチャットでは、次の順で確認する。

1. `ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES_2.md`
2. 本ファイルのTVT-MP一般形、旧メモとの差分、未実装境界、次の作業開始点
3. 必要に応じて`ORDER_EXCHANGE_TIME_VALUE_TRANSACTION_DESIGN_NOTES.md`の指定節
4. `ORDER_EXCHANGE_PROGRESS.md`
5. `git status --short`
6. `git log -1 --oneline --decorate`
7. 実装対象の既存Pythonファイルと専用テスト

Cursor報告だけで設計または実装を確定しない。

実コード、差分、テスト結果をTerminalで確認する。

Git操作は利用者がTerminalで行う。

コミットまでの操作と`git push`を分ける。
