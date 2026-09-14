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
