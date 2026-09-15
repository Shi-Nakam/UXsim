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
