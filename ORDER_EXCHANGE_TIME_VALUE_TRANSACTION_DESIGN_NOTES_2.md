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

**2026-09-21更新（候補別局所仮想計算・入力境界順位拘束の途中確定）：** 下流境界observerまでの実装は完了済みである。候補別局所仮想計算は未実装である。今回は完全な実装前仕様を作らず、利用者との明示的な採否判断により、入力、下流境界近似、horizon、早期終了、順位拘束範囲を途中確定した。Python実装と専用テストは未着手である。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」を参照する。2026-09-18の設計検討記録は当時の検討正本として残す。

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

**2026-09-21更新注記：** 本節は2026-09-18時点の設計検討記録であり、削除しない。当時は有力案または基本方針として残した事項のうち、条件付き平均流出率の正式採用、流出許可残高、T以後の新規流入なし、`configured_horizon_steps`をlocal horizon上限とすること、buyer/sellerの必要通過時刻、`K_fixed`に基づく局所拘束範囲等は、後続の「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」を最新とする。当時の「`trade_order`全体を通過試行順とする」記述は、当時の基本方針である。2026-09-21時点では、局所仮想計算の拘束順位は`trade_order`全体ではなく、TVT形成前の未通過確定済みVisitと、`K_fixed`まで新たに確定されるVisit列である。完全な拘束順位列は`trade_order`の単純prefixと同一とは限らない。通過試行のskip / continue / clearance時breakの規則そのものは、拘束順位へ適用する範囲で維持する。本節を現在も未確定のままの正本として読まない。

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

**2026-09-21更新注記：** 通過試行の一時スキップ、clearance未充足時の走査終了、保存済み進路の使用は維持する。ただし、走査対象を`trade_order`全体とする当時の記述は、後続の途中確定記録で更新した。最新の拘束順位は`K_fixed`に基づく完全な局所拘束順位列であり、「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」を参照する。

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

**2026-09-21更新注記：** local horizon上限を対応する全World baselineの`configured_horizon_steps`とし、別の自由入力horizonを設けないことは、後続の途中確定記録で採用した。必要情報が揃った時点の早期終了も同記録で採用した。当時の「有力案」「受渡し方法は未確定」は歴史的記録として残す。

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

**2026-09-21更新注記：** 条件付き平均流出率の正式採用、観測countを正本として局所計算側で算出すること、active>0かつtransfer=0のhorizon内サービス率0、active=0の制約付きsink分岐、流出許可残高の候補別・outlink別独立性と小数および未使用整数の繰越しは、後続の「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」で途中確定した。active=0時の制約付きsinkの具体的コード契約は、同記録でも未確定のままである。

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

**2026-09-21更新注記：** 見出しの「未確定」は2026-09-18時点の状態である。初期実装では時点T以後のinlink始端新規流入なしを採用した。最新正本は「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」である。本小節の当時の限界説明（楽観的になり得ること、新規Vehicleの順位設計が必要になること）は、採用理由の補足として残す。新規流入の影響が存在しないという意味ではない。

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

**2026-09-21更新注記：** 本一覧は2026-09-18時点の未確定事項である。後続で途中確定した事項（新規流入なしの初期方針、条件付き平均流出率の正式採用、count正本、残高繰越し、`configured_horizon_steps`上限、buyer/sellerの必要通過時刻、`K_fixed`に基づく局所拘束範囲、resolved/unresolvedの基本契約等）は、「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」を最新とする。公開API、結果型、制約付きsinkの具体契約、拘束順位外の標準transfer相当処理、完全な`K_fixed`拘束順位列の入力接続等は、同記録でも未確定のままである。

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

**2026-09-21更新注記：** 上記「次の作業候補」のうち、inlink始端の新規流入なし、条件付き平均境界サービス率の正式採用、観測countからの平均率算出位置、流出許可残高、局所mimic Worldの基本範囲、resolved / unresolvedの基本契約は、後続の「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」で途中確定した。active=0時の制約付きsinkの具体的コード契約、公開API、結果型は同記録でも未確定である。本2026-09-20節は下流境界observerの実装完了正本として残す。

# TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録

**記録日：2026-09-21**

本節は、候補別局所仮想計算の残る入力・境界・順位拘束設計について、利用者との明示的な採否判断により途中確定した事項を記録する。

候補別局所仮想計算全体の完全な実装前仕様ではない。

公開API、正式結果型、完全な`K_fixed`拘束順位列の入力接続、拘束順位外Vehicleに対する標準transfer相当処理の詳細、active=0時の制約付きsink、最終確定列との上位接続、例外契約、専用テスト契約等には未確定事項が残る。

Python実装と専用テストは未着手である。今回のMarkdown変更は作業時点では未コミットである。新しい実装コミットhashを推測しない。

実装済みの下流境界observer、UXsim transfer hook、`DELTAN=1`前提、baseline driver接続、一般形順位の制度ロジックと順位アルゴリズム、FIFO検査接続は再考しない。ただし、完全な`K_fixed`拘束順位列を後段で構築するために、既存結果型へ必要最小限の公開材料を追加する必要があるかは未確認である。

状態表現:

- 設計途中確定
- Python実装未着手
- 専用テスト未着手
- 完全な実装前仕様ではない
- 下流境界観測の実装済み部分は再考しない
- 一般形順位の制度ロジックと順位アルゴリズムは再考しない
- FIFO検査接続の実装済み部分は再考しない
- 今回はMarkdown記録だけを更新する

後続のPython実装では、研究用コードとして正しく動くことを最優先する。その上で、短さや高度なPython技法よりも、Python初学者が交通上の意味と状態変化を後から追える、明示的で可読性の高い実装を優先する。複雑なone-liner、過度な内包表記、結果設定漏れをデフォルト値で隠す書き方は避ける。

直前の「TVT-MP候補別局所仮想計算の設計検討記録」（2026-09-18）および下流境界観測の基本設計・実装完了記録は削除しない。本節は、それらの観測結果を将来の局所仮想計算でどう使うか、および入力・境界・順位拘束の途中確定を正本とする。

## 何のための局所仮想計算か

候補別局所仮想計算は、一つの対象Nodeについて、一つの具体的TVT-MP候補が成立した場合の局所交通状態と、関係Visitの通過timestepを予測する計算である。

全World baselineの順位をそのまま再生する計算ではない。

全World baselineで得た予想通過timestepと、候補別局所仮想計算で得た予想通過timestepを比較し、後続の経済性評価に必要な時間差の材料を得る。

局所予測は、将来の実Worldを完全に予言または再現する計算ではない。同じ対象Nodeの複数候補を比較するための局所的な予測である。局所予測と実World実績が一致することは保証しない。その差は、研究上の事後評価対象となり得る。

## 三つの計算世界

次を明確に区別する。既存制度は旧メモ§16、§25.25.34および本ファイルの2026-09-18設計検討記録と一致する。本節で再考しない。

1. 全World baseline仮想計算
2. Node別・具体的TVT-MP候補別の局所仮想計算
3. 最終的に選択したTVTを反映して進む実World

全World baselineは、時点`T-1`までのTVT結果を引き継ぎ、時点`T`では新しいTVTを追加しない比較基準である。全対象Nodeを含む一つの共通Worldとして計算し、各Nodeが自Nodeの情報を参照する。

候補別局所仮想計算は、一つの対象Nodeにおいて一つの具体的TVT-MP候補を仮に実行した場合の到着・通過等を予測する。入力候補はFIFOを満たした具体的候補（実装済み接続後は`preserves_inlink_fifo=True`）である。

実Worldは、全対象Nodeがそれぞれ最終的に選択したTVTを反映して進む。同一timestepでは各対象Nodeが共通の全World baselineを参照し、それぞれ独立に候補を局所評価する構想である。

候補別全World計算を採用しない制度上の第一の理由は、同じ実時点`T`に他NodeのTVT結果が未確定であり、一つの候補だけを全Worldへ適用した計算が実際の将来Worldを正確に表さないことである。計算負荷削減だけが理由ではない。

## 局所mimic Worldの基本範囲

初期実装では、一つの対象Nodeと一つの具体的TVT-MP候補ごとに、独立した局所mimic Worldを構築する。

局所mimic Worldには、時点`T`における次を含める。

- 対象Node
- 対象Nodeへ接続する全inlink
- 対象Nodeから出る全outlink
- 全inlink上に存在する全Vehicle
- 全outlink上に存在する全Vehicle
- 対象Node、inlink、outlinkの交通進行に必要な状態
- 容量とsnapshot時点の残容量
- Vehicleの位置
- Vehicleの速度
- Vehicleの車線
- leader
- follower
- move_remain
- link_arrival_time
- clearance履歴
- その他、既存BATCH Level 2 mimic World（`uxsim/order_control_batch_level_2_reference.py`）で必要性が確認されている状態

候補Visitだけを抜き出して局所mimic Worldを構築する方式は採用しない。

ただし、局所mimic Worldへ含めた全VehicleへTVT順位を付与するわけではない。含めることと、拘束順位を付けることは別である。

BATCH Level 2のmimic World構築と限定loopは参考にする。次は流用しない。

- BATCH service queue
- trigger用pseudo service unit
- trigger通過時の終了条件
- Level 1 fallback
- BATCH固有の未到着規則

## 時点T以後のinlink始端新規流入

初期実装では、時点`T`より後にdummy upstream Node等から新しいVehicleを発生させない。

時点`T`に局所範囲内に存在するVehicleだけを進める。

この方針は、新規流入の影響が存在しないという意味ではない。次の限界を記録する。

- 新規流入を無視するため、局所予測が楽観的になる可能性がある
- local horizonが長いほど影響が大きくなる可能性がある
- 局所予測と実World実績との差として事後検証する
- 将来の感度分析または発展実装の対象とする
- 新規流入Vehicleの順位、進路、clearanceへの影響は初期実装では設計しない
- 新規流入が影響しないとは主張しない

2026-09-18記録の例（inlink Yへ実Worldでは`T`以後に新規進入し、clearanceへ影響し得ること）は、この限界の説明として残す。

## 条件付き平均下流境界サービス

実装済みの`OrderControlBaselineDownstreamBoundaryResult`に保存されたoutlink別countを使用する。

使用する値:

```text
active_timestep_count
transferred_vehicle_count
```

`active_timestep_count > 0`の場合:

```text
downstream_mean_service_rate
=
transferred_vehicle_count
/
active_timestep_count
```

条件付き平均流出率はbaseline結果へ新たに保存しない。観測countを正本とし、候補別局所仮想計算側で必要時に算出する。

場合分け:

`active_timestep_count > 0` かつ `transferred_vehicle_count > 0`

- 正の条件付き平均流出率を算出する

`active_timestep_count > 0` かつ `transferred_vehicle_count == 0`

- baseline共通horizon内の境界サービス率を0とする
- 局所計算でも同じlocal horizon内は途中通過Vehicleを流出させない
- horizon後も永久に閉塞すると断定しない

`active_timestep_count == 0`

- 境界サービス能力を観測できていない
- 条件付き平均流出率を算出しない
- 制約付きsinkへ分岐する

`active_timestep_count == 0`を、「下流混雑がないことを確認した」と表現しない。

「下流境界待ちが観測されなかったため、制約付きsinkを使用する近似」と記録する。制約付きsinkの具体的コード契約は本節では未確定である。

## 流出許可残高

条件付き平均流出率を使用するoutlinkごとに、流出許可残高を持つ。

残高は次の単位で独立する。

```text
一つの具体的TVT-MP候補
×
一つのoutlink
```

別候補間で残高を共有しない。同じ候補内でも、別outlink間で残高を共有しない。

初期残高は0である。

各局所timestepの下流境界サービス前:

```text
新残高
=
前timestepからの残高
+
downstream_mean_service_rate
```

小数部分を繰り越す。使用されなかった整数部分も繰り越す。

初期実装では次を設けない。

- 人工的な残高上限
- 繰越期間上限
- 独自のburst上限

流出許可残高は、実Worldで物理的に貯蔵された容量ではない。

baselineで観測された平均的なサービス機会を、候補ごとに異なる需要発生時刻へ再配分する局所近似である。

残高が大きくても、後述の物理容量を超えて流出させない。

## 一つのtimestepの途中通過Vehicle流出条件

途中通過Vehicleを局所World外へ流出させるには、少なくとも次のすべてを満たす。

1. 流出許可残高の整数部分が1台以上である
2. outlink終端で待っている途中通過Vehicleである
3. outlinkの`capacity_out_remain`が1台分以上である
4. 終端Nodeの`flow_capacity_remain`が1台分以上である、またはNode容量が無制限である
5. Vehicleが単車線outlinkの物理先頭である
6. `DELTAN=1`である

初期研究は単車線を前提とする。

途中通過Vehicleを1台流出させた場合:

- 流出許可残高を1減らす
- outlink流出容量残を1台分消費する
- 終端Node容量が有限なら1台分消費する
- Vehicleを局所Worldの対象外へ出す

次は使用しない。

- 下流Linkの流入容量
- 存在しない下流Linkの仮想容量
- 独自の人工的な一括流出台数上限

「その他の物理条件」という曖昧な残余を正式条件にしない。初期実装で使用する必須条件は上記1から6である。

## 目的地到着Vehicle

outlink終端で目的地に到着したVehicleは、通常のUXsimと同じtrip-end処理を行う。

目的地到着Vehicleは次を消費しない。

- 条件付き平均流出率
- 流出許可残高

ただし、単車線outlinkの物理先頭順は守る。

前方に流出不能な途中通過Vehicleがいる場合、後方の目的地到着Vehicleを追い越してtrip-endさせない。

## outlink終端の単車線FIFO

outlink終端では物理先頭から順に処理する。

同じtimestep内で、物理先頭Vehicleが処理された後は、新しい物理先頭Vehicleを続けて検討できる。

途中通過Vehicleが次のいずれかで流出不能なら、同じoutlinkの境界処理をそのtimestepについて終了する。

- 流出許可残高不足
- outlink流出容量不足
- 終端Node容量不足
- 物理先頭でない
- 途中通過Vehicleでない
- `DELTAN=1`前提の不充足

後方Vehicleを先に処理しない。

「一つのtimestepにつき一台」という独立した制限は追加しない。

## TVT専用限定timestep loop

TVT候補別局所仮想計算は、通常の`World.exec_simulation()`を使用せず、TVT専用の限定timestep loopで実行する。

ここでいうTVT専用限定timestep loopとは、対象Node周辺だけを、候補固有の順位と下流境界制約に従って進める、小さな専用シミュレーションループである。

最初の局所timestep:

- 容量を更新し直さない
- snapshotからコピーした`capacity_out_remain`、`capacity_in_remain`、`flow_capacity_remain`等をそのまま使用する

2 timestep目以降:

- UXsim通常処理と整合する順序でLink容量とNode容量を更新する

既存の`Node.transfer()`を局所loopの後段でそのまま丸ごと呼ぶ方式は採用しない。

## 局所timestep内の基本処理順

各局所timestepの処理順の現時点での正本は次とする。

1. 2 timestep目以降なら、Link容量とNode容量を更新する。最初の局所timestepでは、snapshotからコピーした残容量をそのまま使用する
2. 条件付き平均流出率を使用する各outlinkの流出許可残高へ、そのtimestep分の平均率を加算する
3. timestep開始時点ですでにoutlink終端で待っているVehicleを、outlinkの物理先頭順に境界処理する
   - 目的地到着Vehicleは通常のtrip-endを行う
   - 途中通過Vehicleは、流出許可残高と明示した物理条件の範囲で局所World外へ流出させる
   - active=0のoutlinkは、後続で確定する制約付きsink契約に従う
4. 対象Nodeにおいて、その具体的候補について拘束力を持つ通過試行順位を適用する
5. 拘束順位を持たないVehicleについて、後続で確定するUXsim標準transfer相当処理を行う
6. inlink上のVehicleを前進させる
7. outlink上のVehicleを前進させる
8. 今回の前進で新たにoutlink終端へ到達したVehicleは、次の局所timestepから境界サービス対象にする
9. 必要なbuyerとsellerの局所通過timestepがすべて揃ったか確認する

重要事項:

- timestep開始時点ですでに終端で待っていたVehicleは、そのtimestepで境界サービスを受けられる
- そのtimestepの前進で新たに終端へ到着したVehicleは、同じtimestepでは境界サービスを受けない
- 新たに到着したVehicleは、次timestepから境界サービス対象となる
- この順序は、通常UXsimでNodeのtransfer処理がVehicle前進より先に行われる時間順と整合する
- outlink上のVehicleを先に前進させてから、すでに終端で待っていたVehicleを探す順序にはしない

**2026-09-21処理順への2026-09-24注記：** 上記の「境界処理を対象Node通過より前に置く」「その時刻の前進で終端へ着いたVehicleは同じ時刻に境界サービスを受けない」は、2026-09-21時点の処理順である。削除しない。最新の仮想timestep順は、完全な実装前仕様のとおり、対象Node通過、局所前進、新着incoming登録のあと、同じ仮想時刻にoutlink終端境界を行う。実装済み範囲と未実装の境界処理は「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」を参照する。

## local horizonと早期終了

local horizonの上限には、対応する全World baseline結果の`configured_horizon_steps`を使用する。

別の自由入力local horizonを設けない。

ただし、候補別局所仮想計算は、全World baselineと異なり、必ず上限まで実行するわけではない。

候補の経済評価に必要な全buyerと全sellerの局所通過timestepが揃った時点で早期終了する。

上限前に必要情報が全件揃う

- resolved
- その時点で早期終了する

`configured_horizon_steps`までに一つでも必要情報が揃わない

- unresolved
- 当該候補だけを経済評価対象から除外する

一部だけ取得した通過時刻を使って経済評価しない。

不足値を次で補わない。

- 0
- 任意の推定値
- 利益0
- 余剰0
- その他の便宜的な値

`configured_horizon_steps`は、局所仮想計算を必ず最後まで動かす長さではなく、最大計算期間である。

全World baseline側は、snapshot固定Visitが1件以上ある通常経路では設定horizon全体を実行し、途中で早期終了しない。局所仮想計算の早期終了と混同しない。

## buyerとsellerの識別

必須通過timestep取得対象は、候補の取引で時間的な得失が生じる次のVisitである。

- 全buyer
- 全seller

既存一般形順位結果`OrderControlTvtMpGeneralTradeRankResult`では、次が別々に保持されている。

```text
buyers_sorted
sellers_sorted
```

したがって、コード上でbuyerとsellerを区別したまま、局所通過timestepを保存できる。

後段の時間差計算では役割を保持する。

概念上:

```text
buyer側の時間差
=
baseline予想通過timestep
-
局所予想通過timestep

seller側の時間差
=
局所予想通過timestep
-
baseline予想通過timestep
```

ただし、buyerだから必ず時間短縮になるとは仮定しない。

sellerだから必ず遅延になるとも仮定しない。

実際に計算した符号付き差を保持する。

buyerとsellerの役割は、差を取る向きを決めるために必要である。

役割から計算結果の正負を決めつけない。

局所計算結果型に時間差そのものを保存するか、後続の経済評価側で算出するかは、現時点では未確定として残す。

## 局所mimic World内Vehicleの役割

局所mimic World内Vehicleは、候補生成過程の名称ではなく、局所計算上の扱いにより次の2種類へ分けて考える。

A. 今回の局所計算で拘束力を持つ通過試行順位に含まれるVisit

B. 交通状態の再現には必要だが、今回の拘束順位には含まれないVehicle

Bも次へ影響する。

- car-following
- inlink物理順
- outlink混雑
- outlink入口空間
- 容量消費
- clearance
- buyerとsellerの通過時刻

Bへ新しいTVT順位を付与しない。

「候補上限外」「候補ではなかった」等の候補生成過程の分類を、局所サービス処理の主要分類として使用しない。

候補上限外のVisitが時点`T`に局所範囲内に実在する場合、交通状態再現用Vehicleとなり得るが、この生成過程上の分類を局所処理の中心概念にはしない。

## TVT形成前の確定済み順位

局所仮想計算で守るべき先行順位には、TVT候補形成前にすでに確定済みであり、時点`T`に対象Nodeをまだ通過していないVisitを含める。

確定済みには少なくとも次を含める。

- `baseline_arrival_timestep`が`T`以下のVisit
- snapshot時点ですでに到着していたVisit
- snapshot時点のtimestep内に到着するVisit
- 意思決定窓の先頭に連続する非参加Visitとして先行確定したVisit

意思決定窓は次である。

```text
T < baseline_arrival_timestep <= T + 6
```

`baseline_arrival_timestep`が`T`のVisitは意思決定窓には含めない。

`baseline_arrival_timestep`が`T`のVisitは、上流の到着済み確認により先に確定する。

したがって、snapshot時点ですでに到着していたVisitだけでなく、snapshot時点のtimestep内に到着するVisitも確定済みブロックへ入る。

`OrderControlTvtNodeRankState`は確定済み順位ブロックを保持する。本節でその実装を再考しない。

確定済み順位ブロックのうち、局所計算開始時点ですでに対象Nodeを通過済みのVisitを、対象Nodeで再びサービスしてはならない。

局所計算で使用するのは、確定済み順位ブロックのうち、対象Nodeをまだ通過していないVisitである。

## candidate_visits、意思決定窓、trade_scopeの違い

次を混同しない。

```text
candidate_visits
意思決定窓内Visit
trade_scope
```

これらは同じ集合とは限らない。

`candidate_visits`は、権利保有Visitのbaseline通過時刻`P`に対し、P−1条件を満たす順位未確定Visitを並べ、さらにTVT固有候補数上限`N`を適用した限定集合である。意思決定窓内Visit集合と同一ではない。

意思決定窓は次の到着時間範囲である。

```text
T < baseline_arrival_timestep <= T + 6
```

`trade_scope`は、ある具体的buyer候補について、最後尾buyerのbaseline順位までを取引対象範囲としたものである。`trade_scope`は候補ごとに変わり得る。

現在の一般形順位再構成では、概念的に次である。

```text
trade_scope
=
baseline_order[:last_buyer_rank]
```

既存コード`uxsim/order_control_tvt_mp_general_trade_rank.py`がこの関係を内部確認している。本節で変更しない。

## trade_scope、trade_order、局所拘束順位

既存の一般形順位結果では、次のように順位を構築している。

`trade_scope`内

- TVT取引後順位

`trade_scope`外だが限定`candidate_visits`集合内

- baseline順位を保持

その上で、上限`N`適用後の限定`candidate_visits`全体について`trade_order`を構築している。

FIFO検査は`trade_scope`と`trade_order[:last_buyer_rank]`を材料にする。既存FIFO検査接続は再考しない。

`trade_order`全体を局所仮想計算の拘束順位として使用する処理は、まだ実装されていない。最終確定列を構築する上位処理もまだ実装されていない。

局所仮想計算で拘束すべき順位は、`trade_order`全体ではない。

局所仮想計算で守る完全な拘束順位列の概念は次である。

```text
A. TVT形成前から確定済みであり、
   局所計算開始時に対象Nodeをまだ通過していないVisit

その後に、

B. 今回の具体的候補が成立した場合に、
   K_fixedまで新たに順位確定されるVisit列
```

TVT成立時に新たに拘束される範囲は、制度上、旧正本の次で決まる。本節は計算式を変更しない。

```text
K_fixed = max(K_last_buyer, K_decision_window)
```

記号の意味は旧正本どおりである。

```text
K_last_buyer
=
採用された具体的候補における最後のbuyerの、
現在の未確定範囲内baseline順位

K_decision_window
=
今回の意思決定窓内Visitのうち、
現在の未確定範囲内baseline順位が最後のVisitの順位

K_fixed
=
今回新たに確定する、
現在の未確定範囲の終端順位
```

旧正本では、TVT成立時について次も確定している。

- `K_fixed`までを確定する
- TVT当事者は取引後順位で確定する
- 取引によって順位を変更されないVisitはbaseline順位を維持して確定する
- 意思決定窓外の未確定Visitは、今回の処理だけを理由に当然には確定しない

可変上限`N`実装後の注記では、さらに次が確定している。

- `N+1`位以降が意思決定窓内なら、TVT成立、不成立、未解決時の既定処理に従う
- `N+1`位以降が意思決定窓外なら、上限外であることや情報不足だけを理由に今回確定しない
- `N`以内でも意思決定窓外Visitは、成立したTVTの確定範囲へ含まれる場合に確定され得る
- `N`以内という理由だけでは順位確定しない
- 最終順位確定の上位接続は未実装である

したがって、Bの内部は制度上、概念的に次である。

```text
trade_scope内
→ 当該具体的候補のTVT取引後順位

trade_scope外だがK_fixed内
→ 正式baseline順位
```

`K_fixed`より後方のVisitは、今回の候補成立によって順位拘束しない。そのVisitへ、今回のTVT成立を理由にbaseline順位を強制しない。

### 既存trade_orderの位置づけ

既存`trade_order`は、TVT固有上限`N`適用後の`candidate_visits`について構築される。

既存一般形順位再構成では、`candidate_visits`の範囲について次を保持する。

```text
trade_scope内
→ 当該具体的候補のTVT取引後順位

trade_scope外だがcandidate_visits内
→ baseline順位
```

したがって、`trade_order`は、`trade_order`に含まれているVisitについては、局所拘束順位列を構築する材料になり得る。

しかし、意思決定窓内に`N+1`位以降のVisitが存在する場合、そのVisitは次の状態となる。

```text
TVT成立時にはK_fixed内に含まれ得る
しかし
candidate_visitsには含まれない
したがって
trade_orderにも含まれない
```

そのため、完全な局所拘束順位列を`trade_order`の単純prefixだけから構築してはならない。

`trade_order`全体を使用しないという結論は維持する。

ただし、「`trade_order`の単純prefixを使えば足りる」という結論も採用しない。

完全な拘束順位列は、次の単純な列とは限らない。

```text
trade_orderのprefix
```

`trade_order`の必要部分は材料となり得るが、完全な拘束順位列は次のVisitも含み得る。

```text
trade_orderに含まれない、
N+1位以降の意思決定窓内Visit
```

既存一般形順位再構成が、上限`N`適用後の`candidate_visits`について`trade_order`を構築していること自体は否定しない。

一般形順位の制度ロジック、空き順位枠方式、`trade_scope`内の取引後順位構築を再考しない。

ただし、局所仮想計算で必要な完全な`K_fixed`拘束順位列を、現在の公開結果だけで構築できるかは未確認である。

追加調査の結果、局所計算接続側の新規helperだけで足りる可能性と、既存結果型へ必要最小限の公開材料を追加する可能性の両方を残す。

現時点では一般形順位アルゴリズムを変更しないが、既存の公開結果型を含めて一切変更不要であるとは確定しない。

既存一般形順位アルゴリズムが誤っているとは記載しない。現時点で確認されたのは、局所計算の完全な入力として現在の`trade_order`だけでは不足し得ることである。

最終確定列の構築とrank stateへの最終反映は未実装のままである。局所仮想計算では、当該候補が成立したと仮定した場合に`K_fixed`まで確定される範囲を、通過試行の拘束範囲として使う。

### 完全な局所拘束順位列の構築方法は未確定

完全な拘束順位列を、現行のどの公開結果から構築するかは、今回の時点では未確定である。確定事項として書かない。

少なくとも、次の材料を調査する必要がある。

- `OrderControlTvtNodeRankState.confirmed_visit_keys_in_order()`
- `remaining_decision_window_visit_keys`
- `candidate_visits`
- `trade_scope`
- `trade_order`
- `trade_rank`
- `K_last_buyer`
- `K_decision_window`
- `K_fixed`
- collectorに保存された正式baseline順位材料
- `N+1`位以降の意思決定窓内Visit
- `inlink_name`
- `route_next_link_name`
- `baseline_arrival_timestep`
- `baseline_passage_timestep`
- VisitKeyによる重複排除
- TVT形成前に確定済みだが対象Nodeをまだ通過していないVisitの特定材料

## 順位は通過試行順である

確定済み順位および候補成立時の拘束順位は、対象NodeでVehicleの通過を試す順序である。

実際の通過順位を無条件に保証するものではない。

次により、制度上の通過試行順位と、局所World上の実通過順位が異なる可能性がある。

- 未到着
- inlinkの物理先頭でない
- outlink入口空間不足
- inlink流出容量不足
- outlink流入容量不足
- 対象Node容量不足
- clearance未充足
- その他、本節で明示された物理条件

この差は、順位違反ではなく、物理交通条件を伴うサービス結果である。

2026-09-18に採用したskip / continue / clearance時breakの規則は、拘束順位へ適用する範囲で維持する。当時の「`trade_order`全体を走査する」記述は、`K_fixed`制度に基づいて構築される完全な局所拘束順位列を走査する、という記述へ更新する。

完全な局所拘束順位列は、`trade_order`の必要部分を材料として含み得るが、`trade_order`の単純prefixと同一とは限らない。`N+1`位以降の意思決定窓内Visitも、`K_fixed`により拘束順位列へ含まれ得る。

## 拘束順位での通過試行規則

各局所timestepで、未通過のVisitを、完全な局所拘束順位列の先頭から再評価する。

未到着の場合:

- そのtimestepでは一時的にスキップする
- 後順位Visitを検討可能とする
- 拘束順位自体は変更しない
- 次timestepでは再び完全な拘束順位列の先頭から評価する

inlinkの物理先頭でない場合:

- そのtimestepでは一時的にスキップする
- 後順位Visitを検討可能とする
- 拘束順位自体は変更しない

outlink入口空間不足、inlink流出容量不足、outlink流入容量不足、対象Node容量不足等の場合:

- そのtimestepでは一時的にスキップする
- 後順位Visitを検討可能とする
- 具体的条件はTVT専用サービス処理の完全実装前仕様で既存UXsimコードと再照合する

clearance未充足の場合:

- そのtimestepの拘束順位走査を終了する
- 後順位Visitへ進まない
- 拘束順位外Vehicleの処理へも進まない
- 次timestepで、再び完全な拘束順位列の先頭から評価する
- clearance待ちVehicleへ新しい予約順位を与えない

通過可能な場合:

- baseline保存済み`route_next_link_name`に対応するoutlinkへ通過させる
- 局所通過timestepを記録する
- clearance履歴を更新する
- 残る拘束順位Visitの走査を続ける

同じinlinkの連続Visitは、物理条件と容量が許せば、同じtimestep内に複数通過できる。

異なるinlinkへの切替ではclearanceを適用する。

## baseline保存済み進路

拘束順位を持つ候補Visitについては、baselineで保存済みの`route_next_link_name`を使用する。

局所計算中に`route_next_link_choice()`を呼び直さない。

候補ごとに進路をランダムに選び直さない。

baselineと局所候補の比較において、同じ保存済み進路を使用する。

右折、左折、直進は、保存済み`route_next_link_name`に対応するoutlinkに従う。

## 拘束順位を持たないVehicle

TVT形成前の確定済み順位にも、今回の候補成立時に新たに確定する順位にも含まれないVehicleへ、baseline順位を強制しない。

これらのVehicleには、新しいTVT順位を付与しない。

これらには、UXsim標準transferと同等の規則により通過を試す方向を採用する。

ただし、既存の`Node.transfer()`を局所loopの後段でそのまま丸ごと呼ぶ方式は採用しない。

理由:

- 拘束順位を持つVehicleまで再評価する可能性がある
- TVT順位と異なる順序で拘束順位Vehicleを通過させる可能性がある
- 同一timestepに同じVehicleを二重評価する可能性がある
- 拘束順位処理で既に消費したLink容量およびNode容量との整合が必要である
- 拘束順位処理で更新したclearance状態との整合が必要である

したがって、TVT専用局所loop内で、次を設計する必要がある。

拘束順位を持つVehicleを対象外とした、UXsim標準transfer相当処理

この標準相当処理の具体的な次の事項は、現時点では未確定として残す。

- Vehicle選択順
- inlink選択順
- 乱数使用
- 局所RNG
- merge_priority
- acceptable outlink
- route_next_link
- outlink選択
- clearanceとの関係
- 拘束順位処理後に残る容量の使用
- 同一timestep内での二重評価防止

## resolved / unresolved

具体的TVT-MP候補について、全buyerと全sellerの局所通過timestepが揃った場合、その候補をresolvedとする。

`configured_horizon_steps`までに、全buyerと全sellerのうち一つでも局所通過timestepが得られない場合、その候補をunresolvedとする。

未解決候補については次を行わない。

- 不足情報を任意値で補う
- buyer利益を0と置く
- seller不利益を0と置く
- 経済余剰を0と置く
- 自動的に経済的不成立と分類する
- resolved候補との経済比較へ加える
- 未解決のまま採用する

一部候補だけがunresolvedの場合、その候補だけを除外し、他のresolved候補は維持する。

全候補がunresolvedの場合は、経済条件による不成立とは区別し、局所仮想計算未解決によるTVT不成立として扱う既存方針を維持する。

## 既存コードを変更しない範囲

一般形順位の制度ロジックと順位アルゴリズムは再考しない。空き順位枠方式、FIFO検査接続、候補上限`N`、`K_fixed`制度も再考しない。

現時点では次を変更しない。

- 一般形順位の制度ロジックと順位アルゴリズム
- 空き順位枠方式
- FIFO検査接続
- `preserves_inlink_fifo()`
- 候補Visit集合構築の制度ロジック
- TVT固有候補数上限`N`の制度
- `K_fixed`制度
- 下流境界observer
- UXsim transfer hook
- baseline driverの下流境界結果接続
- `DELTAN=1`検証

ただし、完全な`K_fixed`拘束順位列を後段で構築するために、既存結果型へ必要最小限の公開材料を追加する必要があるかは、次の調査事項として残す。

既存の公開結果型を含めて一切変更不要であるとは確定しない。

今後必要なのは、局所仮想計算接続側の次の処理である。

- `K_fixed`に従う完全な局所拘束順位列を構築する。構築方法は未確定である
- 局所mimic Worldを構築する
- TVT専用限定timestep loopを実行する
- 必要なbuyerとsellerの局所通過timestepを取得する
- resolved / unresolvedを返す

## 未確定事項

今回の記録で確定したように書いてはいけない事項を、独立して残す。少なくとも次は未確定である。

1. `K_fixed`を、局所仮想計算用の具体的なVisit列へ変換する正式処理
2. 意思決定窓内の`N+1`位以降Visitを取得する正式な公開材料
3. `remaining_decision_window_visit_keys`を局所計算入力へ接続するか
4. `trade_order`に含まれるVisitと、`trade_order`に含まれない`K_fixed`内Visitを重複なく接続する方法
5. `trade_scope`外かつ`K_fixed`内のVisitを、正式baseline順位で並べるために使用する正本データ
6. `K_fixed`内Visitについて、局所計算に必要な次の情報をどこから取得するか
   - VisitKey
   - `inlink_name`
   - `route_next_link_name`
   - `baseline_arrival_timestep`
   - `baseline_passage_timestep`
   - `vehicle_id`
   - `arrival_tiebreaker`
   - その他の必要情報
7. 現行の一般形順位結果または上流結果型へ、必要最小限の公開材料を追加する必要があるか
8. 局所計算接続側に新しいhelperを追加するだけで足りるか
9. 最終確定列構築部品と、局所仮想計算用拘束順位列構築部品が、同じ`K_fixed`列構築helperを共有すべきか
10. TVT形成前確定済みVisitのうち、局所計算開始時に対象Nodeを未通過のVisitだけを抽出する方法
11. 上流結果に保存されたVisit情報と、局所mimic World上のVehicleをVisitKeyで対応付ける方法
12. active=0時の制約付きsinkの具体的コード契約
13. 拘束順位を持たないVehicleへ適用するUXsim標準transfer相当処理
14. 標準transfer相当処理のVehicle選択順
15. 標準transfer相当処理のinlink選択順
16. 標準transfer相当処理での乱数使用
17. 局所RNG
18. merge_priorityの扱い
19. acceptable outlinkの扱い
20. `route_next_link_name`を持たない交通状態再現用Vehicleの扱い
21. 拘束順位処理と標準相当処理の間のclearance接続
22. 拘束順位処理後に残るinlink、outlink、Node容量の使用方法
23. 同一Vehicleの同一timestep二重評価を防ぐ正式方法
24. 局所mimic Worldの正式公開API
25. 正式モジュール名
26. 結果型名
27. 結果型の全フィールド
28. unresolved reasonのenumまたは正式形式
29. simulated timestep数等の診断情報
30. 軽量カウンター
31. 例外契約
32. 局所結果と経済評価部品の接続
33. buyer / sellerの時間差を局所結果側で計算するか、経済評価側で計算するか
34. 成立候補選択
35. 最終確定列の構築
36. rank stateへの最終反映
37. 実WorldへのTVT反映
38. 専用テスト契約
39. 性能測定
40. horizon感度分析
41. 境界近似感度分析
42. 新規流入あり方式の将来拡張

## 反証および誤読防止

- `trade_order`全体が、TVT成立時に全件確定される順位とは限らない
- 完全な拘束順位列は、`trade_order`の単純prefixと同一とは限らない
- `N+1`位以降の意思決定窓内Visitも、`K_fixed`により拘束順位列へ含まれ得る
- 局所仮想計算の完全な入力として、現在の`trade_order`だけでは不足し得る
- 既存の公開結果型を含めて一切変更不要であるとは確定しない
- 既存一般形順位アルゴリズムが誤っているとは記載しない
- `candidate_visits`は、意思決定窓内Visit集合と同一ではない
- `trade_scope`と意思決定窓は別概念である
- baseline順位は局所計算へ無条件に適用しない
- `trade_scope`外の全candidate Visitを局所計算でbaseline順位へ固定するとは限らない
- 今回の候補成立時にも順位未確定のまま残るVehicleが存在し得る
- buyerだから必ず時間短縮とは限らない
- sellerだから必ず遅延とは限らない
- 順位は通過試行順であり、実通過順を保証しない
- `active=0`は無混雑の直接観測ではない
- 流出許可残高は物理的に保存された容量ではない
- 残高が大きくても、物理容量を超えて流出させない
- 目的地到着Vehicleは流出許可残高を消費しない
- 新規流入を扱わないことは、その影響を否定する意味ではない
- 局所予測と実World実績は異なり得る
- 既存`Node.transfer()`を局所loopの後段でそのまま呼ぶ設計ではない
- 今回は完全な実装前仕様ではない
- 今回はPython実装へ進まない
- 今回は専用テスト実装へ進まない

## 次の再開地点

**2026-09-21更新注記：** この再開地点は、当該途中確定記録（「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」）を作成した時点の歴史的記録である。その後、上流結果の調査を完了した。完全な局所拘束順位列の4区分を途中確定した。順位確定時の対象Node向け正式進路保存を途中確定した。順位と正式進路の原子的保存を途中確定した。採用候補あり、全候補却下、baseline情報不足、意思決定窓内Visit 0件の最終分岐を途中確定した。現在の最新正本は、後続の次の新節である。「TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録」。現在の直接作業は、拘束順位外Vehicleの対象Node向け進路と処理方式の確定である。古い再開地点を現在の作業指示として読まない。

次の直接作業は、今回すでに確定した事項の再検討ではない。

次の再開地点:

`K_fixed`に従う完全な局所拘束順位列を構築するために、現行の上流結果から取得できるVisitと情報を調査し、不足する公開材料と最小の接続方法を確定する。

次の調査対象として、少なくとも以下を挙げる。

- `confirmed_visit_keys_in_order`
- `remaining_decision_window_visit_keys`
- `candidate_visits`
- `trade_scope`
- `trade_order`
- `trade_rank`
- `K_last_buyer`
- `K_decision_window`
- `K_fixed`
- `N+1`位以降の意思決定窓内Visit
- collectorのbaseline正式順位材料
- `inlink_name`
- `route_next_link_name`
- `baseline_arrival_timestep`
- `baseline_passage_timestep`
- `vehicle_id`
- `arrival_tiebreaker`
- VisitKeyによる重複排除
- TVT形成前確定済みVisitのうち未通過Visitだけを抽出する方法
- 局所mimic WorldのVehicleとの対応付け
- 上流結果型への必要最小限の追加が必要か
- 最終確定列構築と局所拘束順位列構築でhelperを共有すべきか

その調査後に、次の順で残設計へ進む方向とする。

1. 完全な局所拘束順位列の構築契約
2. 拘束順位を持たないVehicleへのUXsim標準transfer相当処理
3. active=0時の制約付きsink
4. 公開API
5. 正式モジュール名
6. 結果型
7. unresolved理由
8. 例外契約
9. 専用テスト契約
10. 候補別局所仮想計算全体の完全な実装前仕様

# TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録

**記録日：2026-09-21**

**2026-09-22更新注記：** 本節は保存済みcommit `1613eb9` の正本であり、削除しない。本節作成時点では、拘束順位外Vehicleの処理とactive=0時の制約付きsinkは未確定であった。その後、2026-09-22の「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」で、拘束順位外Vehicleの進路4分類と一時的試行順、clearance、状態更新、active=0を含む下流境界3分岐、候補別局所仮想計算の統合仕様を確定した。本節の4区分、正式進路の永続保存、原子的確定、原因別最終分岐は維持する。それらを本節の「未確定」記述で上書きして読まない。現在の最新正本は当該2026-09-22節である。完全な実装前仕様は、同節でもまだ作成していない。

本節は、2026-09-21の「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」の後続である。

利用者との明示的な採否判断により、その後追加確定した内容を記録する。

候補別局所仮想計算全体の完全な実装前仕様ではない。

Python実装と専用テストは未着手である。

完全な局所拘束順位列の4区分、順位確定時の正式進路保存、順位表構築と正式確定の分離、最終分岐は途中確定した。

拘束順位外Vehicleの処理は調査済みだが、進路を含む正式契約は未確定である。

active=0時の制約付きsinkも未確定である。

一般形順位再構成、空き順位枠方式、FIFO検査、候補数上限N、K_fixed制度、baseline collectorの対象Node到着時進路記録は再考しない。

状態表現:

- 設計途中確定
- Python実装未着手
- 専用テスト未着手
- 完全な実装前仕様ではない
- 本節は2026-09-21途中確定記録の後続である
- 完全な局所拘束順位列の基本設計と正式進路保存は途中確定した
- 拘束順位外Vehicleの進路を含む正式契約は未確定である
- active=0時の制約付きsinkは未確定である
- 一般形順位再構成、空き順位枠方式、FIFO検査、候補数上限N、K_fixed制度、collectorの対象Node到着時進路記録は再考しない
- 今回はMarkdown記録だけを更新する

後続のPython実装では、研究用コードとして正しく動くことを最優先する。その上で、短さや高度なPython技法よりも、Python初学者が交通上の意味と状態変化を後から追える、明示的で可読性の高い実装を優先する。

## 1. 完全な局所拘束順位列の4区分

完全な局所拘束順位列は、次の4区分で構成する。

### 区分1

今回のbaseline開始前から順位確定済みであり、局所計算開始時点で対象Nodeをまだ通過していないVisitである。

区分1は、過去のサイクルですでに確定済みのVisitである。今回のbaseline結果によって新たに確定するVisitではない。

### 区分2

今回のbaseline結果により、TVT候補形成前に先行確定するVisitである。

区分2には次を含む。

- baseline到着timestepがT以下と判明したVisit
- 意思決定窓先頭の連続する非参加Visit

区分2は、過去のbaselineで確定済みだったVisitではない。

これらは、今回のbaseline結果により、今回の候補形成前に確定するVisitである。

区分1と区分2を混同しない。区分1は今回のbaseline開始前から確定済みである。区分2は今回のbaseline結果によって先行確定する。

### 区分3

今回の具体的TVT-MP候補の`trade_scope`内のVisitである。

区分3では次を適用する。

- buyerには取引後順位
- sellerには取引後順位
- 非参加Visitには固定されたbaseline順位枠

区分3を単純に「全Visitの順位が変わる範囲」と表現しない。

buyerとsellerの順位は変わる。非参加Visitは固定されたbaseline順位枠を維持する。

したがって、「`trade_scope`内のVisitはすべて順位が変わる」とは記載しない。

### 区分4

`trade_scope`外だが`K_fixed`内にあり、baseline順位で追加確定されるVisitである。

区分4を、候補数上限N以内だけに限定しない。N+1位以降の意思決定窓内Visitも`K_fixed`内に含まれ得る。

### 連結順

完全な局所拘束順位列の連結順は次である。

```text
区分1
→ 区分2
→ 区分3
→ 区分4
```

## 2. 4区分の取得時点と取得元

### 区分1の取得

区分1は、今回のbaseline開始前の確定状態から取得する。

具体的には、今回のbaseline開始前のNode別確定順位台帳を正本とし、今回のsnapshot固定集合に存在するVisitだけを、確定順位順に抽出する。

区分1取得後に今回のbaselineを実行する。

区分1を、区分2確定後の順位台帳から再抽出してはならない。

その方法では、今回新たに先行確定した区分2まで区分1へ混入するためである。

### 区分2の取得

区分2は、今回実行した次の先行確定処理が返したVisit列を直接使用する。

- 既到着未確定Visitの先行確定結果
- 意思決定窓先頭の連続する非参加Visitの先行確定結果

区分2の条件を後段で再推定しない。

### 区分3の取得

区分3は、一つの具体的候補について構築された`trade_scope`内の取引後順位を使用する。

### 区分4の取得

区分4は、`trade_scope`外だが`K_fixed`内にあるVisitを、今回baselineの正式baseline順位で並べる。

`K_fixed`は既存制度どおり次である。

```text
K_fixed = max(K_last_buyer, K_decision_window)
```

`trade_order`全体を完全な拘束順位列として使用しない。

`trade_order`の単純prefixだけで完全な拘束順位列を構築できるとも扱わない。

N+1位以降の意思決定窓内Visitも`K_fixed`内に含まれ得る。

## 3. Visitの識別と結果に保持する内容

各項目はVehicle名だけで識別しない。

次を正本とする。

```text
VisitKey = (vehicle_name, visit_id)
```

同じVehicleが同じNodeを再訪した場合も、`visit_id`により別Visitとして扱う。

各Visit項目には少なくとも次を保持する方向とする。

- VisitKey
- 完成した拘束順位列内での通過試行順
- 対象Nodeから出る正式進路
- 4区分のどれに属するか

結果全体には少なくとも次を保持する方向とする。

- 対象Node
- 対象となる具体的候補
- 区分1のVisit列
- 区分2のVisit列
- 区分3のVisit列
- 区分4のVisit列
- 完成した全体Visit列
- `K_last_buyer`
- `K_decision_window`
- `K_fixed`

正式なクラス名、フィールド名、公開APIは未確定である。完全実装前仕様で確定する。

この結果には次を重複保存しない。

- Vehicleの位置
- Vehicleの速度
- 局所仮想計算による通過結果
- 金銭
- 利益
- 効用

## 4. 重複と不整合

次を必須とする。

- 各区分内部に同じVisitKeyが重複しない
- 区分1から4の間でも同じVisitKeyが重複しない
- 完成列が区分1→区分2→区分3→区分4の単純連結結果と完全一致する
- 完成列内の各Visitに、そのVisitへ適用すべき正式進路が存在する

重複または正式進路欠落を見つけても、次を行わない。

- 自動削除
- 片方を優先して継続
- 推測による進路補完
- 新しい進路の再選択

明示的な入力不整合として停止する。

各Visitへ区分名の文字列を重複保存するかは、正式結果型設計まで未確定でよい。

ただし、4区分のVisit列を別々に保持し、どのVisitがどの理由で拘束されたかを判別可能にする。

## 5. 正式進路の定義

局所仮想計算で使用する正式進路は、単なる最新の`route_next_link`でも、最初に得た`route_next_link`でもない。

正式進路は次である。

「そのVisitの順位確定をもたらした全World baselineにおいて、対象Nodeへの到着時にcollectorへ記録された`route_next_link_name`」

同じVehicleは、異なる時点Tで実行される複数の全World baselineにおいて、対象Nodeへの到着と進路選択を複数回予測され得る。

順位確定対象にならなかったbaselineで得た進路は、そのbaseline限りの予測情報である。

局所仮想計算で将来使用する正式進路は、そのVisitの順位を実際に確定させたbaselineの進路である。

対象Node通過後に下流Nodeで選ばれた別の`route_next_link`を、対象Node用正式進路として使用しない。

baseline終了時のVehicleオブジェクトが現在保持する`route_next_link`も、対象Node用正式進路として使用しない。

候補ごとに`route_next_link_choice()`を呼び直さない。

既存collectorは、対象Node到着時の進路をVisitKeyで保存する。下流Nodeでは新しい`visit_id`となるため、同じcollector内で対象Node用recordが上書きされないことは確認済みである。

ただし、collectorは一つのbaseline forkの寿命であり、次のサイクルまで永続しない。

現在の`OrderControlTvtNodeRankState`はVisitKeyと順位だけを保存し、正式進路は保存していない。

そのため、順位確定時の正式進路をサイクル間で保持する仕組みを追加する必要がある。

## 6. コード調査で確認済みの進路記録事実

次はコード調査済みの事実である。

- `route_next_link_choice()`は、対象Nodeの`incoming_vehicles`への登録および`record_order_control_node_arrival()`より先に呼ばれる
- `record_order_control_node_arrival()`は、その時点の`route_next_link.name`を`route_next_link_name`としてcollectorへ渡す
- collector recordはVisitKeyで識別される
- 下流Nodeへ進んだ後は新しい`visit_id`となるため、下流Node向け進路は、同じcollector内の対象Node用recordを上書きしない
- collectorは一つのbaseline forkの寿命であり、次のサイクルまで永続しない
- `Vehicle.route_next_link`は、Vehicleが下流へ進むと別Node向け進路へ更新され得る
- baseline終了時の`Vehicle.route_next_link`を対象Node用正式進路として使用してはならない
- 現在の`OrderControlTvtNodeRankState`はVisitKeyと確定順位だけを保存し、正式進路を保存していない
- 現在の`confirm_visits_in_order()`も正式進路を保存しない。VisitKeyと順位だけを保存する
- 最終確定列を構築してrank stateへ接続する本番上位処理は未実装である
- collector出力順は正式baseline順位ではない
- baseline正式順位は、baseline到着timestep、固定`arrival_tiebreaker`、Vehicle IDの順で決まる

## 7. 正式進路の永続保存

正式進路は、Node別順位台帳である`OrderControlTvtNodeRankState`へ、確定順位と一体として保存する方針を採用する。

別の独立台帳へ分離しない。

理由:

- 順位と正式進路の対応を一つの正本で管理できる
- 順位だけ確定し、進路だけ保存に失敗する同期ずれを防げる
- サイクルをまたいで形成前確定済みVisitの進路を取得できる
- VisitKeyでNode再訪を区別できる
- Python初学者が後から追いやすい

永続保存する最小情報は次とする。

- VisitKey
- assigned rank
- `route_next_link_name`

次は制度上の必須保存情報にしない。

- `inlink_name`
- `baseline_arrival_timestep`
- `arrival_tiebreaker`
- `baseline_passage_timestep`
- `vehicle_id`
- `baseline_timestep_T`
- 確定理由

診断目的で追加情報を保持するかは未確定である。

区分1は、過去の確定時に保存済みの確定順位と正式進路をそのまま使用する。

区分1の順位と進路を、今回のbaseline結果で上書きしない。

区分2から4のうち今回正式確定されるVisitには、今回のbaselineで対象Node到着時にcollectorへ記録された正式進路を使用する。

進路の取得元を区分ごとに整理すると、次である。

- 区分1は、過去の順位確定時に順位台帳へ保存された正式進路を使う
- 区分2は、今回baseline collectorの正式進路を使う
- 区分3は、今回baseline collectorの正式進路を使う
- 区分4は、今回baseline collectorの正式進路を使う

## 8. 順位と正式進路の原子的保存

順位を正式に確定するすべてのVisitについて、その確定順位と、順位確定に用いたbaselineで記録された対象Node向け進路を、必ず同時に保存する。

ただし区分1は過去に保存済みなので、今回改めて保存しない。

今回新たに確定するVisitについては、次の順で処理する。

1. 確定対象Visit列を準備する
2. 各Visitの正式進路を取得する
3. VisitKey、入力順、進路、重複、現在の未確定状態等を全件検証する
4. 候補の確定順位状態と候補の正式進路状態をメモリ上で構築する
5. 全件が正しい場合だけ一括反映する
6. 一件でも不整合があれば、順位も進路も一件も反映しない

順位だけ保存され、正式進路が欠ける部分更新を認めない。

## 9. 進路付き確定API

既存`confirm_visits_in_order()`は直ちに削除しない。

既存テストとの互換または移行期間の内部用途として残してよい。

ただし、今後の本番TVT順位確定経路は、順位と正式進路を原子的に保存する新しい進路付き確定APIへ移行する。

rank state自身がcollectorを直接参照しない。

順位確定を行う処理が、順位確定をもたらしたbaseline collectorから正式進路を取得する。

その処理が、VisitKeyと進路を対応付けた入力を作り、rank stateへ渡す。

rank stateは全件検証後、順位と進路を原子的に保存する。

非技術的には次を意味する。

- 今回の予測計算で各Vehicleの進行方向を確認する
- 順位を確定するとき、その順位と進行方向をセットで記録する
- 例えば「Vehicle AのVisit 2は2番目で、対象Nodeから右方向へ進む」と一体で保存する

進路付き確定APIの正式名称、正式入力型、rank state内部の正式進路保存フィールド名は未確定である。

## 10. `baseline_passage_timestep`の位置付け

順位と正式進路を保存する処理に限れば、`baseline_passage_timestep`は必須入力ではない。

理由:

- `route_next_link_name`は、対象Nodeへの到着時点で判明する
- 順位先行確定は、対象Node通過前でも行われ得る
- 既到着Visitと意思決定窓先頭の連続する非参加Visitは、対象Node通過前でも先行確定され得る
- 正式進路の保存に必要なのは、対象Nodeへの到着時点で記録された進路である

ただし、次のように一般化しない。

```text
baseline_passage_timestepは不要である
```

正確には次である。

```text
順位と正式進路を保存する処理に限れば、
baseline_passage_timestepは必須入力ではない
```

`baseline_passage_timestep`が候補形成、局所評価、経済評価等の別目的で必要になることは否定しない。

「通過時刻は一切不要」とも記載しない。

## 11. 候補別順位表と正式確定の分離

完全な局所拘束順位表を構築する処理は読取専用とする。

完全な局所拘束順位表を構築する処理と、順位を正式確定する処理を分離する。

候補別順位表を構築する処理は次を行う。

- 4区分を構築する
- 各Visitへ正式進路を対応付ける
- 重複と進路欠落を検証する
- `K_fixed`との整合を確認する
- 完成した通過試行順を返す
- 順位台帳を変更しない

候補評価中は、区分3と区分4を含む候補別順位表を仮の読取専用結果として保持する。

不採用候補の順位と進路を順位台帳へ保存しない。

正式確定は、最終結果が決定した後の別処理とする。

正式確定処理は、検証済み順位表またはbaseline順位確定用の検証済み列を使う。今回新たに確定するVisitについて、順位と正式進路を一括保存する。

採用候補が決まった場合は、候補評価に使用した検証済み順位表を参照し、今回新たに確定するVisitの順位と進路を順位台帳へ一括反映する。

採用後に同じ候補順位表を再構築しない。

同じ内容の「確定後順位表」を別に複製保存する必要はない。

この点は既に採用済みの「候補評価中は台帳を変更せず、採用後に検証済み順位表を使って正式確定する」方針の再確認であり、新しい制度変更ではない。

## 12. 区分2の確定時点

区分2は候補形成前に正式確定する。

区分2は具体的候補の内容に依存しない。

今回baselineで得た正式baseline順位と対象Node向け正式進路を、候補形成前に原子的に保存する。

区分2を正式確定した後の順位台帳末尾を`K_confirmed_before`とする。

その後に権利保有Visitを選び、具体的候補を形成する。

区分3と区分4は候補ごとに異なるため、候補評価中は順位台帳へ保存しない。

最終結果決定後にのみ、採用候補またはbaseline順位確定分岐に従って正式保存する。

## 13. 最終分岐

「TVT検討なし」を、原因を区別しない一括表現として使用しない。

次の分岐を区別する。

### 採用候補がある場合

採用候補の`trade_scope`内は、その候補の順位で確定する。

採用候補の`trade_scope`が意思決定窓より小さい場合は、`trade_scope`内を採用候補の順位で確定し、残る意思決定窓内Visitをbaseline順位で確定する。

この場合は「残る意思決定窓内Visit」と表現する。

採用候補の`trade_scope`が意思決定窓以上へ達する場合は、`K_fixed`制度に従って`trade_scope`側の確定範囲まで扱う。

正式確定対象の順位と正式進路を一括保存する。

### 候補を評価した結果、全候補が却下された場合

次のすべてを含む。

- 全候補が不採用
- 全候補が未解決
- 不採用候補と未解決候補が混在し、結果的に採用候補が0

この場合は、意思決定窓内Visit全体をbaseline順位で確定する。

この場合は「残る意思決定窓内Visit」ではなく、「意思決定窓内Visit全体」と表現する。

意思決定窓内Visit全体について、baseline順位と今回baselineで記録された正式進路を一括保存する。

全候補不採用だけをbaseline順位確定分岐とし、全候補未解決または不採用・未解決混在を落とす扱いにはしない。

### 必要なbaseline情報不足により候補形成・評価へ進めない場合

TVT候補の形成と評価自体を行わない。

主な不足は、必要なbaseline通過情報をhorizon内に得られないことである。

一方、意思決定窓はT+6までであり、通常のbaseline horizonは30または50程度であるため、意思決定窓内Visitの到着情報と対象Node向け進路情報は取得できる。

この場合も、意思決定窓内Visit全体をbaseline順位で確定し、今回baselineで記録された正式進路と一括保存する。

baseline情報不足であることから、意思決定窓内Visitの進路まで不足すると推定しない。

「baseline情報不足のVisitは進路も不明かもしれない」とは記載しない。baseline情報不足の中心は通過情報の不足であり、意思決定窓内Visitの到着情報と進路情報は取得される。

### 意思決定窓内Visitが0の場合

TVT検討を行わない。

意思決定窓内にVisitが存在しないため、意思決定窓内Visitの順位確定処理も存在しない。

確定対象は0件である。

「意思決定窓内Visit全体をbaseline順位で確定する」とは記載しない。

## 14. `K_fixed`拘束順位列構築部品

`K_fixed`に従う完全な局所拘束順位列を構築する独立部品を新設する方向を採用する。

局所仮想計算用と将来の最終確定処理用に、別々の`K_fixed`制度ロジックを実装しない。

同じ制度ロジックを共有する。

一般形順位再構成へ`K_fixed`後方列の構築責務を戻さない。

一般形順位結果は、これまでどおり`candidate_visits`内の`trade_scope`、`trade_order`、`trade_rank`等を提供する。

後段の`K_fixed`拘束順位列構築部品が、次を組み合わせる。

- baseline開始前の確定状態
- 今回の先行確定結果
- 一般形順位結果
- 意思決定窓結果
- baseline collector
- 順位台帳に保存された過去確定時正式進路

完全な`K_fixed`拘束順位列構築部品は、それらの材料を組み合わせる後段部品とする。

## 15. 明示的に撤回した案

次は採用しない。撤回済みの案として記録する。採用事項として残さない。

1. `trade_order`全体を完全な拘束順位列として使用する案
2. `trade_order`の単純prefixだけで完全な拘束順位列を構築する案
3. baseline終了時のVehicleオブジェクトの現在の`route_next_link`を使用する案
4. 候補ごとに`route_next_link_choice()`を呼び直す案
5. 正式進路がない形成前確定Visitへ、局所RNGで新しい進路を与える案
6. 最新baselineの進路で、過去の確定時に保存した正式進路を上書きする案
7. collectorをサイクル間で保持し、正式進路台帳の代わりにする案
8. 正式進路を候補別順位表だけへ載せ、順位台帳へ永続保存しない案
9. 順位と正式進路を別々に反映し、部分更新を許す案
10. 「TVT検討なし」を原因別に区別せず一括表現する案
11. 全候補却下から、全候補未解決または不採用・未解決混在を除外する案
12. 意思決定窓内Visitが0件の場合も、意思決定窓内Visit全体をbaseline順位で確定すると表現する案
13. baseline情報不足時には意思決定窓内Visitの進路も不明であると推定する案
14. `trade_scope`内の全Visitを単純に「順位が変わるVehicle」と表現する案

## 16. 拘束順位外Vehicleについて調査済みの事実

**2026-09-22更新注記：** 本小節は2026-09-21時点の調査記録である。当時は正式採用に至っていなかった。2026-09-22の「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」で、進路4分類、一時的FCFS走査、clearance、incoming保持、物理移動の制度を確定した。本小節の調査事実は削除しない。本小節を現在も未確定の正本として読まない。

拘束順位外Vehicleの処理は重要だが、正式採用には至っていない。調査済みだが、未確定である。

確定済みまたは調査で確認済みの範囲は次である。

- 既存`Node.transfer()`を局所loop後段でそのまま呼ばない
- そのまま呼ぶと拘束順位Vehicleを再評価する
- 同一timestepの二重評価が起こり得る
- clearanceを無視する
- `incoming_vehicles`を全消去するため、局所loopと整合しない
- 拘束順位処理で消費した容量との整合が必要である
- 拘束順位Vehicleが未到着、物理先頭でない、容量不足等で一時スキップされても、拘束順位外処理でそのVehicleを再評価してはならない
- 拘束順位走査がclearance未充足で終了した場合、同じtimestepでは拘束順位外処理へ進まない
- 同じtimestep内で拘束順位処理後に容量が残り、clearance breakが起きていなければ、拘束順位外Vehicleの処理へ進む構想である
- 拘束順位Vehicle全員が将来通過し終わるまで待ってから、拘束順位外Vehicleを処理する意味ではない
- 同じtimestepに容量を再充填せず、拘束順位処理後の残容量だけを使う
- 局所loopでは`incoming_vehicles`を全消去せず、通過したVehicleだけを除く方向である

したがって、拘束順位外Vehicle処理については、次を正式採用事項として書かない。

- 除外付きFCFS clearance方式を正式採用した
- 乱数を使わないことを最終確定した
- `merge_priority`を使わないことを最終確定した
- mimic上の`route_next_link`をそのまま使うことを最終確定した

現時点では、調査済み有力案および継続検討事項である。

## 17. BATCH Level 2から確認できた進路状態

BATCH Level 2仮想計算では、対象Nodeからの進路がsnapshot時点で決定済みかどうかを区別している。

進路状態A:

- 対象Nodeからの進路が決定済み
- snapshot時点の固定進路を使用する
- 仮想計算中に進路を選び直さない
- 固定進路が通れないからといって、別outlinkへ変更しない

進路状態B:

- 対象Nodeへ未到着で、対象Nodeから出る進路がまだ決定していない
- UXsim本来の`route_next_link_choice()`を呼ばない
- その時点で受入可能なoutlinkを列挙する
- Vehicle IDによる決定的方法で一つを選ぶ
- 選択結果を`virtual_outlink_choices`へ記録する
- 実Worldの乱数を消費しない

ただし、BATCH Level 2の状態B方式をTVTでそのまま採用したとは記載しない。

Vehicle IDによるoutlink選択は、BATCH Level 2の局所近似であり、UXsim本来の進路選択の再現ではない。

TVTでは参考となる先例だが、正式採否は未確定である。

**2026-09-22更新注記：** 上記「正式採否は未確定」は2026-09-21時点の記録である。その後、分類4（snapshotでも今回baselineでも対象Node向け進路が未判明の拘束順位外Vehicle）に限り、受入可能なoutlink集合へ実Vehicle IDの剰余を適用するBATCH Level 2型の仮想進路を採用した。分類3のbaseline進路を捨ててVehicle ID方式へ置き換える案は撤回済みである。全物理outlinkへ剰余を適用してから循環探索する旧案も撤回済みである。詳細は2026-09-22の「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」を参照する。

## 18. 拘束順位外Vehicleの未確定事項

**2026-09-22更新注記：** 本小節の「まだ正式採用していない」は2026-09-21時点の記録である。一時的FCFS走査、clearance未充足時の当該timestep終了、残容量の共有、incoming保持、分類4のVehicle ID方式は、2026-09-22節で確定した。公開API名、結果型名、helper名、診断フィールドのPython型は、同節でも未確定のままである。本小節を現在の未確定一覧として読まない。

拘束順位外Vehicleについて、次はまだ正式採用していない。

- FCFS clearance相当の到着順処理を採用するか
- `merge_priority`を使用するか
- 乱数を使用するか
- 局所RNGを使用するか
- 進路決定済みVehicleの進路取得契約
- 対象Nodeからの進路が未決定のVehicleへの進路付与
- BATCH Level 2状態B方式を再利用するか
- 全World baselineで後に判明した進路を使用するか
- UXsim本来の進路選択を候補間で同一結果となるよう再現するか
- 拘束順位外Vehicleのclearance正式契約
- trip-end待ち処理
- 拘束順位外Vehicle処理の正式結果と診断情報
- 物理移動helperを新設するか

拘束順位外Vehicleの対象Node向け進路をどこから取得するかは未確定である。拘束順位外Vehicleに保存済み正式進路があるとは限らない。mimic Worldへコピーした時点で進路が決定済みのVehicleと、未決定のVehicleを区別する必要がある。FCFS相当処理を正式採用する前に、進路設計を確定する必要がある。`merge_priority`を使わない制度上の理由をさらに詰める必要がある可能性がある。trip-end待ち処理をどこまで残すかも未確定である。

調査上の有力案として、次は存在する。

- 拘束順位Vehicleを除外する
- 到着時刻、固定tiebreaker、Vehicle ID順で走査する
- clearance未充足なら同じtimestepの残り処理を終了する
- 拘束順位処理後の残容量だけを使う
- `incoming_vehicles`を全消去しない
- 通過Vehicleだけを除く
- 既存`transfer_fcfs_clearance()`をそのまま呼ばず、局所専用処理を作る
- 物理移動はTVT局所モジュール内の専用関数とする

ただし、進路契約が未確定なので、これらを正式採用済みと記載しない。

## 19. その他の未確定事項

少なくとも次を未確定として残す。

1. 進路付き確定APIの正式名称
2. 進路付き確定APIの正式入力型
3. rank state内部の正式進路保存フィールド名
4. 既存`confirm_visits_in_order()`の移行方法
5. 確定理由または`baseline_timestep_T`を診断情報として保存するか
6. `K_fixed`列構築部品の正式モジュール名
7. `K_fixed`列結果型の正式名称
8. 4区分の正式フィールド名
9. 各Visit項目へ区分文字列を重複保存するか
10. `K_decision_window`と`K_fixed`の正式公開形式
11. 形成前確定済みVisitのsnapshot所属確認の正式API
12. collector recordとのVisitKey対応helper
13. 正式進路と対象Node outlinkの整合確認
14. 拘束順位外Vehicleの進路取得
15. 拘束順位外Vehicleの正式な処理順
16. 拘束順位外VehicleへFCFS clearance相当処理を採用するか
17. 拘束順位外Vehicleに`merge_priority`を使用するか
18. 拘束順位外Vehicle処理の乱数契約
19. 拘束順位外Vehicleのclearance契約
20. 拘束順位外Vehicle処理後のtrip-end待ち処理
21. 拘束順位外Vehicle処理の専用結果・診断
22. active=0時の制約付きsink
23. 局所仮想計算の公開API
24. 局所仮想計算の正式結果型
25. unresolved理由
26. 例外契約
27. 専用テスト契約
28. 完全な実装前仕様
29. 最終確定上位処理の正式API
30. 実WorldへのTVT反映

## 20. 次の再開地点

**2026-09-22更新注記：** この再開地点は、2026-09-21の追加途中確定記録を作成した時点の歴史的記録である。その後、拘束順位外Vehicleの対象Node向け進路4分類、一時的試行順、clearance、状態更新、物理移動、active=0を含む下流境界3分岐、候補別局所仮想計算の統合仕様を確定した。現在の最新正本は、後続の「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」である。現在の直接作業は、公開API、結果型、helper責務、診断型、例外契約、モジュール構成、専用テスト契約、既存上流結果との接続を含む完全な実装前仕様の作成である。この再開地点を現在の作業指示として読まない。

次の直接作業は、今回確定した4区分、正式進路保存、原子的確定、最終分岐の再検討ではない。

次の直接作業は次である。

「拘束順位外Vehicleについて、対象Node向け進路をどこから取得し、進路未決定Vehicleをどう扱うかを確定する。その結果を踏まえ、同一timestep内の拘束順位外Vehicleの選択順、clearance、merge_priority、乱数、incoming保持、物理移動処理を正式確定する。」

特に次を確認する。

- 拘束順位外Vehicleがmimic World構築時に持つ`route_next_link`
- snapshot時点で未到着のVehicleの進路状態
- BATCH Level 2の進路状態AとB
- 進路決定済みVehicleの進路固定
- baselineで対象Nodeへ到着した拘束順位外Vehicleのcollector進路
- baselineで対象Nodeへまだ到着していない拘束順位外Vehicle
- 候補間で交通再現条件を同一にする方法
- `route_next_link_choice()`の再実行を避ける方法
- Vehicle IDによる決定的選択のTVTへの適否
- 除外付きFCFS clearance方式
- `merge_priority`
- 局所RNG
- `incoming_vehicles`保持
- trip-end待ちVehicle
- 単車線研究範囲で必要な最小処理

この論点が確定した後に、active=0時の制約付きsinkへ進む。

# TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録

**記録日：2026-09-22**

本節は、保存済みcommit `1613eb9`（`Document the four-part TVT-MP binding order and confirmation-time route preservation for local virtual calculation, and outcome-specific final rank confirmation rules`）以後に確定し、同commit時点では未記録だった事項の詳細正本である。

本節は実装完了記録ではない。候補別局所仮想計算の制度設計、および次に作る完全な実装前仕様へ向けた確定記録である。

Python実装と専用テストは未着手である。

直前の「TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録」（記録日2026-09-21、保存済みcommit `1613eb9`）は削除しない。同節で確定済みの次は、本節で再確定せず、接続に必要な範囲で参照する。

- 完全な局所拘束順位列の4区分
- 順位確定時の対象Node向け正式進路
- 順位と正式進路の原子的保存
- 候補別順位表の構築と正式確定の分離
- 採用候補あり、全候補却下、baseline情報不足、意思決定窓内Visitが0件の原因別最終分岐

同節の作成時点では、拘束順位外Vehicleの処理とactive=0時の制約付きsinkは未確定であった。本節で、拘束順位外Vehicleの進路と通過処理、下流境界の3分岐、候補別局所仮想計算の統合仕様を確定する。

公開API名、結果型名、private helper名、診断フィールドのPython型、モジュール名、専用テストファイル名を含む完全な実装前仕様は、本節ではまだ作成しない。

一般形順位再構成、空き順位枠方式、FIFO検査、候補数上限N、`K_fixed`制度、baseline collectorの対象Node到着時進路記録は再考しない。

状態表現:

- 制度設計の主要採否は本節の範囲で確定
- 完全な実装前仕様は未作成
- Python実装未着手
- 専用テスト未着手
- 前回commit `1613eb9`の4区分、正式進路保存、原子的確定、原因別最終分岐は維持する
- 拘束順位外Vehicle処理は、本節で進路4分類とtimestep手順まで確定した
- active=0時の制約付きsinkは、本節で確定した
- 公開API、結果型、helper名、診断のPython型は未確定
- 今回はMarkdown記録だけを更新する

後続実装では、本節末尾の可読性方針を必ず守る。正しく動くことを最優先とし、Python初学者が交通上の意味と処理順を追える明示的な実装を、短さや巧妙さより優先する。

## 1. 完全な拘束順位列と拘束順位外Vehicleの関係

完全な拘束順位列は、前回確定済みの4区分を次の順で連結したVisit列である。本節で4区分の中身を変更しない。

区分1は、今回のbaseline開始前から順位確定済みで、局所計算開始時点で対象Nodeをまだ通過していないVisitである。

区分2は、今回のbaseline結果により、TVT候補形成前に先行確定するVisitである。baseline到着timestepがT以下と判明したVisitと、意思決定窓先頭の連続する非参加Visitを含む。過去のbaselineで確定済みだったVisitではない。

区分3は、今回の具体的TVT-MP候補の`trade_scope`内のVisitである。buyerとsellerには取引後順位を使う。非参加Visitは固定されたbaseline順位枠を維持する。区分3を「全Visitの順位が変わる範囲」とは扱わない。

区分4は、`trade_scope`外だが`K_fixed`内にあり、baseline順位で追加確定されるVisitである。N+1位以降の意思決定窓内Visitも`K_fixed`内に含まれ得る。

連結順は次である。

```text
区分1
→ 区分2
→ 区分3
→ 区分4
```

`trade_order`全体をこの列として使わない。`trade_order`の単純prefixだけでこの列を作れるとも扱わない。

完全な拘束順位列内のVisitがすべて到着する前に、拘束順位外Vehicleが対象Nodeへ到着することがあり得る。

局所的な通過試行上、拘束順位外Vehicleの一時的な試行順は、各仮想timestepにおける完全な拘束順位列の走査後に置く。

ただし、拘束順位Vehicle全員が将来通過し終わるまで、拘束順位外Vehicleを一切処理しないという意味ではない。

ある仮想timestepで拘束順位Visitが未到着、inlink物理先頭でない、または通常の物理条件や容量条件を満たさないため一時スキップされた場合でも、clearanceによる停止がなく、残容量があれば、その同じ仮想timestepに拘束順位外Vehicleまで処理順が進み得る。

したがって、拘束順位列の後方にまだ未通過のVisitが残っていても、そのtimestepの拘束順位走査がclearanceで止まっていなければ、余った容量を同じtimestepの拘束順位外Vehicleに使ってよい。

## 2. 対象Node向け進路の4分類

局所仮想計算で対象Nodeから出るときに使う進路は、Vehicleの状態に応じて4分類する。分類番号は、完全な拘束順位列の区分1から区分4とは別である。混同しない。

### 分類1：snapshot時点で対象Node向け進路が決定済みのVehicle

扱い:

- snapshot進路を候補別局所仮想計算で固定使用する
- 当該進路のoutlinkが一時的に受入不能でも、別outlinkへ変更しない
- 通過可能になるまで待つ
- 実Worldの進路を局所仮想計算から強制しない

この分類は、拘束順位内Visitにも拘束順位外Vehicleにもなり得る。判定基準は「snapshot時点で対象Node向け進路が既に決まっているか」であり、拘束順位列に含まれるかではない。

前回節の「区分1の正式進路は、過去の確定時に順位台帳へ保存した進路であり、今回のbaselineで上書きしない」は維持する。分類1は、局所仮想計算中にどのoutlinkへ進ませるかの使用規則である。順位台帳上の過去保存進路を、今回の局所計算結果で置き換えない。

### 分類2：snapshot時点では進路未決定だが、今回の全World baselineで対象Node向け進路が判明し、完全な拘束順位列に含まれるVisit

扱い:

- そのVisitの順位確定をもたらしたbaselineの対象Node到着時進路を、候補別局所仮想計算で使用する
- この進路の意味は、前回節の正式進路と同じである。対象Node通過後に下流Nodeで選ばれた別進路や、baseline終了時の`Vehicle.route_next_link`は使わない
- 候補評価中は読取専用で一時使用する
- 候補評価中に正式順位台帳を変更しない
- その候補が最終採用された場合、またはbaseline順位で正式確定する分岐となった場合だけ、今回正式確定するVisitについて、確定順位と正式進路を順位台帳へ原子的に保存する
- 実Worldで実際に走行する際には、このbaseline進路をVehicleへ強制しない
- 実Worldの進路は通常のUXsim経路選択に任せる
- 当該進路のoutlinkが一時的に受入不能でも、別outlinkへ変更しない

前回節のとおり、区分1は過去に保存済みなので今回改めて保存しない。区分2は候補形成前に、順位と正式進路をすでに原子的に保存する。候補評価中に読取専用で使う分類2のうち、今回新たに正式確定する対象は、最終結果決定後の採用候補またはbaseline正式確定分岐に含まれるVisitである。不採用候補の順位表にだけ現れるVisitは、順位台帳へ保存しない。

### 分類3：snapshot時点では進路未決定だが、今回の全World baselineで対象Node向け進路が判明した拘束順位外Vehicle

扱い:

- baseline進路を当該候補の局所仮想計算内で読取専用として一時使用する
- 順位台帳へ保存しない
- 正式進路とは呼ばない
- 実Worldの進路を強制しない
- 当該進路のoutlinkが一時的に受入不能でも、別outlinkへ変更しない

分類3のbaseline進路は、分類2と同じく「今回の全World baselineで対象Node到着時に判明した進路」を候補評価中に読む。相違は保存である。分類3はこの局所計算を理由として順位台帳へ保存しない。最終結果が採用でも却下でも、分類3を正式進路として永続化しない。

### 分類4：snapshot時点でも、今回の全World baselineでも、対象Node向け進路が判明しなかった拘束順位外Vehicle

扱い:

- 仮想通過を実際に試す時点で、BATCH Level 2型の仮想進路割当を行う
- 順位台帳へ正式進路として保存しない
- 実Worldの進路を強制しない

分類4の具体手順は次節で定める。Nodeへの仮想到着時点では割り当てない。

### 分類2と分類3の表現

分類2と分類3のbaseline進路は、候補評価中はいずれも読取専用で一時使用する。

相違は、最終結果決定後に正式保存対象になり得るかどうかである。

分類2は、採用候補またはbaseline正式確定分岐において今回確定対象になったVisitだけが、順位と正式進路の原子的保存対象になり得る。

分類3は、この局所計算を理由として順位台帳へ保存しない。分類3の一時使用進路を正式進路と呼ばない。

いずれの分類でも、候補ごとに`route_next_link_choice()`を呼び直さない。局所仮想計算から実Worldの進路を書き換えない。

## 3. 分類4のBATCH Level 2型仮想進路

分類4のVehicleは、仮想通過を実際に試す時点で、次の順に処理する。

1. Nodeへの仮想到着時点では進路を割り当てない
2. 当該Vehicleの仮想通過を実際に試す時点で`acceptable_outlinks`を作る
3. `acceptable_outlinks`を`outlink.id`昇順に並べる
4. 実Vehicle IDを使って次を計算する

```text
selection_index = real_vehicle.id % len(acceptable_outlinks)
```

5. `acceptable_outlinks[selection_index]`を選ぶ
6. 選択した処理内で直ちに仮想通過させる
7. 実Worldの`W.rng`、局所乱数、`route_next_link_choice()`は使用しない
8. 選択結果は候補別局所計算の診断情報として記録する
9. 順位台帳へ正式進路として保存しない

`acceptable_outlinks`は、評価時点で次の両方を満たす対象Nodeのoutlink集合である。

- `outlink.capacity_in_remain >= DELTAN`
- outlink入口にVehicleが入れる空間がある

`acceptable_outlinks`が空の場合:

- そのtimestepでは仮想進路を割り当てない
- Vehicleを通過させない
- 次の仮想timestepで再評価し得る

この空集合は、通常の物理条件・容量条件による通過不能である。clearance未充足とは区別する。当該Vehicleを止め、別inlinkに属する後続の拘束順位外候補の通過可否は確認できる。

位置付け:

- 本当の将来進路を予測するものではない
- 楽観的な仮想流入先への決定論的な分散である
- 実Worldの乱数を消費しない
- 局所乱数にも依存しない
- 同じ入力なら同じ結果になる
- 最適な負荷分散を保証しない
- UXsim本来の`route_next_link_choice()`を再現したものではない
- 候補によって交通状態と`acceptable_outlinks`集合が変われば、同じ拘束順位外Vehicleでも候補ごとに異なる仮想進路が選ばれ得る
- この候補間の違いは許容する
- ただし、それをUXsim本来の経路選択の再現とは説明しない

採用方式の経緯:

- 旧案では、全物理outlink数にVehicle ID剰余を適用し、選択先が受入不能なら次のoutlinkを循環探索する案があった
- この旧案は、受入不能outlinkの直後に位置するoutlinkへ選択が偏る可能性があるため撤回された
- 現行方式は、最初から`acceptable_outlinks`だけを抽出し、その集合へVehicle ID剰余を適用する

この方式は分類4だけに使う。分類1、分類2、分類3の保存済みまたはbaseline上の進路を、受入不能だからといってVehicle ID方式へ切り替えない。

## 4. 拘束順位外Vehicleの対象集合と一時的試行順

拘束順位外Vehicleは、局所仮想計算の複数のtimestepにわたって順次対象Nodeへ到着する。最初の仮想timestepに全員が揃っているとは扱わない。

各仮想timestepで、次をすべて満たすVehicleを処理対象集合として更新する。

- その時点までに対象Nodeへ到着済み
- 未通過
- 完全な拘束順位列に含まれない
- trip-end Vehicleではない

次の仮想timestepでは、前timestepから残っている未通過Vehicleと、新たに到着したVehicleを合わせ、処理対象集合を再構成する。前timestepの走査順を固定したまま持ち越さない。

各仮想timestepの一時的な走査順は、次の昇順である。

1. 現在Visitの対象Node到着時刻
2. 固定`arrival_tiebreaker`
3. Vehicle ID

この順序は、当該仮想timestepにおける一時的な通過試行順である。

この順序は、正式なbaseline順位でもTVT順位でもない。順位台帳へ保存しない。次の仮想timestepでは、最新の到着済み未通過集合から再構成する。`merge_priority`を使用しない。乱数を使用しない。

完全な拘束順位列に含まれるVisitを、この一時順へ混ぜない。拘束順位列側で一時スキップされたVisitを、拘束順位外集合へ移して再評価しない。

## 5. 通過不能とclearanceの区別

拘束順位内Visitと拘束順位外Vehicleの双方について、通常の物理条件または容量条件による通過不能と、clearance未充足を区別する。

通常の物理条件・容量条件は、少なくとも次である。

- 対象Nodeへ未到着
- inlinkの物理先頭でない
- 保存済み進路のoutlink入口空間不足
- `outlink.capacity_in_remain`不足
- `inlink.capacity_out_remain`不足
- `node.flow_capacity_remain`不足
- 分類4で`acceptable_outlinks`が空

通常の物理条件・容量条件により通過不能の場合:

- 当該Vehicleを通過させない
- 拘束順位列そのものを変更しない
- 別inlinkに属する後続候補の通過可否を確認できる
- 同じinlinkの後続Vehicleは物理先頭条件により追い越せない
- 次の仮想timestepで再評価する

clearance未充足の場合:

- 当該仮想timestepの残りの通過処理を終了する
- 拘束順位走査中なら拘束順位外Vehicle処理へ進まない
- 拘束順位外Vehicle走査中なら、それ以降の候補を確認しない
- 次の仮想timestepで再評価する

clearance待ちVehicle専用の新しい制御状態は必須としない。

次の既存状態から、各仮想timestepで再判定する。

- `last_order_control_inlink`
- `last_order_control_entry_timestep`
- `order_control_clearance_timesteps`
- `incoming_vehicles`に残っているVehicle

clearance充足条件は次である。

```text
current_virtual_timestep - last_order_control_entry_timestep
> order_control_clearance_timesteps
```

診断用には、clearance待ちとなったVehicleと仮想timestepを記録する。この診断は局所結果に残し、順位台帳や実World baseline collectorへは書かない。

一つの拘束順位Visitが通常の物理条件で通れないことは、clearance停止ではない。その場合は当該Visitを一時スキップし、走査を続ける。clearance未充足のときだけ、そのtimestepの残り通過処理を終える。

## 6. 各仮想timestepの統合手順

各仮想timestepで、次の順に処理する。

### 6.1 容量状態を準備する

局所計算開始timestepでは、snapshotの残容量をそのまま使用する。

2つ目以降のtimestepでは、通常処理と整合する順で、transfer前に容量を補充する。

同一仮想timestepの途中では補充しない。拘束順位走査の後、拘束順位外走査の前に容量を再補充しない。

### 6.2 完全な拘束順位列を先頭から走査する

- 未到着は一時スキップ
- inlink物理先頭でなければ一時スキップ
- 通常の物理条件または容量条件不足は一時スキップ
- 通過可能なら、そのVehicleに対応する分類1または分類2の進路を使用して通過させる
- 拘束順位列自体は変更しない
- 受入不能を理由に、分類1または分類2の進路を別outlinkへ変えない

通過に成功したVisitは、そのtimestepでは通過済みになる。列上の順位は変えない。次のtimestepでは、未通過の拘束順位Visitだけを、同じ完成列の先頭から再び見る。

### 6.3 拘束順位走査でclearance未充足が発生した場合

当該仮想timestepの通過処理を終了する。拘束順位外Vehicle処理へ進まない。

### 6.4 clearance停止がなく、容量が残っている場合

次をすべて満たす拘束順位外Vehicleを抽出する。

- 到着済み
- 未通過
- 完全な拘束順位列に含まれない
- trip-end Vehicleではない

`node.flow_capacity_remain < DELTAN`であれば、この抽出と走査には進まず、当該timestepの通過処理を終了する。

### 6.5 拘束順位外Vehicleを一時的なFCFS順で走査する

走査順は次の昇順である。

1. 到着時刻
2. 固定`arrival_tiebreaker`
3. Vehicle ID

分類1または分類3なら、その固定進路または一時的baseline進路で通過を試す。分類4なら、試行時点で`acceptable_outlinks`を作り、空でなければVehicle ID方式で選んで直ちに通過させる。

### 6.6 通過不能時

通常の物理条件または容量条件なら、当該Vehicleを通過させず、別inlinkに属する後続候補の通過可否を確認できる。同じinlinkの後続は物理先頭でないため追い越せない。

clearance未充足なら、当該仮想timestepの処理を終了する。それ以降の拘束順位外候補は確認しない。

### 6.7 Node容量不足

`node.flow_capacity_remain < DELTAN`となった場合、当該仮想timestepの通過処理を終了する。同じtimestep中に容量を再補充しない。

### 6.8 次の仮想timestep

完全な拘束順位列の先頭から再評価する。前timestepで一時スキップした拘束順位Visitも再評価する。

拘束順位外Vehicleの一時的順序も、最新の到着済み未通過集合から再構成する。新たに到着したVehicleを加え、通過済みVehicleは含めない。

### 6.9 この手順で守る意味

- 完全な拘束順位列内の全Visitが将来通過し終わるまで、拘束順位外Vehicleを待たせるのではない
- 各仮想timestep内で、拘束順位走査の後に余力があれば、拘束順位外Vehicleを処理する
- 拘束順位Vehicleを後段で二重評価しない
- 一つの拘束順位Vehicleが通常の物理条件で通れないだけで、拘束順位外処理を禁止しない
- 同一仮想timestep内で複数Vehicleの通過を認める
- 両走査は同じ残容量とclearance履歴を共有する

## 7. 状態更新と物理移動

### 7.1 `incoming_vehicles`

局所仮想計算では、timestep末に`incoming_vehicles`を全消去しない。

通過成功Vehicleだけを削除する。未通過Vehicleは残し、次の仮想timestepで再評価する。新たにNode端へ到着したVehicleは重複なく追加する。

通常Worldの全消去後に`Vehicle.update()`が再登録する流れには依存しない。UXsim標準とは異なる局所専用処理を行う。

### 7.2 容量

最初の局所timestepはsnapshot残容量を使用する。

2つ目以降は、transfer前に補充する。

同一timestep内では、拘束順位処理と拘束順位外処理が同じ残容量を共有する。拘束順位処理後に再補充しない。

### 7.3 通過成功時

既存UXsimのLink間移動と同じ交通上の意味になるよう、少なくとも次を更新する。

- 累積流出台数
- 累積流入台数
- Link旅行時間関連
- inlink、outlink、Nodeの残容量
- inlink物理先頭からの削除
- outlinkへの追加
- `Vehicle.link`
- `link_arrival_time`
- `x`
- `v`
- `lane`
- leader
- follower
- `move_remain`
- `vehicles_enter_log`
- 新しいorder-control Visit
- `incoming_vehicles`からの削除
- `last_order_control_inlink`
- `last_order_control_entry_timestep`

Vehicleごとに仮想時刻を進めない。同一仮想timestep内の次Vehicleは、先行Vehicleの移動後の最新状態を使用する。

### 7.4 clearance履歴

実際に仮想通過した場合だけ更新する。通過不能の場合は更新しない。

拘束順位処理で更新した履歴を、同じ仮想timestep内の拘束順位外Vehicleへ引き継ぐ。拘束順位外走査用に履歴を分割しない。

### 7.5 inlink物理順

物理先頭でなければ通過不可とする。同じinlinkの後続Vehicleは追い越し不可とする。別inlink候補の通過可否は確認可能とする。単車線研究条件を前提とする。複数車線への一般化は本節で確定しない。

### 7.6 trip-endとsignal

対象Nodeを目的地とするtrip-end Vehicleは研究対象外である。拘束順位外の通過候補へ含めない。

signal統合は研究対象外である。局所通過判定へsignal条件を入れない。

### 7.7 baseline collector

候補別局所仮想計算から、実World baseline collectorへ書き込まない。

仮想通過時刻、仮想進路、停止理由等は、局所結果および診断へ記録する。

## 8. outlink終端境界

下流側の方式が次のいずれであっても、局所Worldで個別に再現しない。

- signalized UXsim
- 標準unsignalized transfer
- FCFS
- BATCH
- TVT

baseline horizon内の下流境界観測結果を使う。

### 8.1 条件付き平均流出率

baseline observerが保持するcountを正本とする。平均率は局所計算側で算出する。目的地到着Vehicleを含めず、途中通過Vehicleだけを観測対象とする。

観測countの意味、`active`の判定、実流出台数の数え方は、実装済みの下流境界observer契約を再解釈しない。

### 8.2 `active > 0`かつ総実流出台数 `> 0`

条件付き平均流出率を、候補別・outlink別の流出許可残高へ、毎仮想timestep加算する。

流出許可残高は候補別・outlink別に独立する。小数部分を繰り越す。未使用の整数部分も繰り越す。

実際の流出台数は、流出許可残高だけで決めない。次のすべてが許す範囲で流出させる。

- 流出許可残高の整数台数分
- outlink終端の待機Vehicle数
- 物理FIFO順
- `outlink.capacity_out_remain`
- 終端Nodeの`flow_capacity_remain`
- `DELTAN=1`
- その他、UXsim既存の物理条件

独立した人工的なburst上限は新設しない。使用しなかった残高は次の仮想timestepへ繰り越す。

大きな残高は、実Worldの物理容量を保存したものではない。baselineから推定した平均的な境界サービス機会を、候補固有の需要時刻へ再配分する近似である。

### 8.3 `active > 0`かつ総実流出台数 `= 0`

baselineの共通horizon中に途中通過待ちVehicleが存在したが、一台も流出しなかった場合である。

観測した共通horizon内の下流境界サービス率を0とする。局所仮想計算でも、同じlocal horizon内は境界閉塞として扱う。horizon後も永続的に閉塞すると断定しない。

この分岐では、条件付き平均流出率に基づく流出を行わない。流出許可残高を正にして流し始めない。

### 8.4 `active = 0`

baseline horizon中に、下流境界待ちが一度も観測されなかった場合である。下流混雑がないと断定しない。

条件付き平均流出率と流出許可残高は使わない。無制約sinkではなく、制約付きsinkへ分岐する。

処理:

- outlink終端に到達した物理FIFO先頭Vehicleから処理する
- 次のUXsim条件が許す範囲で、標準`end_trip()`により局所Worldから除去する
  - outlink終端の待機Vehicle数
  - 物理FIFO順
  - `outlink.capacity_out_remain`
  - 終端Nodeに`flow_capacity`がある場合の`flow_capacity_remain`
  - `DELTAN=1`
  - その他、既存UXsim上必要な物理条件
- 流出成功時には、outlink流出容量と終端Node容量を通常どおり消費する
- 下流Linkは局所Worldに存在しないため、下流Linkの`capacity_in_remain`は使わない
- 人工的な最大1台制限は設けない
- 同一timestepに複数台を流出できるかは、人工的上限ではなく、UXsim既存の容量条件、物理条件、FIFOによって決まる

局所Worldではsink Nodeが仮想目的地として構成されるため`end_trip()`を使用する。これは実World上の本来の旅行終了を意味しない。

「UXsim既存の物理的なtrip-end条件を満たすVehicle」という曖昧な追加条件は設けない。使う条件は、物理FIFO先頭、outlink終端到達、outlink流出容量、終端Node容量、`DELTAN=1`、および上記の既存UXsim上必要な物理条件である。

`active = 0`を、境界流出の完全停止として扱わない。

### 8.5 BATCH Level 2の単純sinkとの差

BATCH Level 2参照コードのsinkは、物理FIFO先頭を確認し、outlink終端到達後に`end_trip()`で除去する単純sinkである。

BATCH Level 2のsinkでは、sink流出時に`outlink.capacity_out_remain`や終端Nodeの`flow_capacity_remain`を確認・消費しない。

TVT-MPの`active = 0`時は、BATCH Level 2の単純sinkをそのまま使わない。

TVT-MPでは、outlink流出容量および終端Node容量等を確認し、流出成功時に消費する制約付きsinkとする。

この相違を今後混同しない。BATCH Level 2がFIFO制約を持つ単純sinkであることと、TVT-MPの`active = 0`分岐がFIFOに加えてoutlink流出容量と終端Node容量等を確認・消費する制約付きsinkであることは、別契約である。

## 9. 実装境界と診断契約

### 9.1 局所仮想計算から直接呼ばない処理

局所仮想計算から次を直接呼ばない。

- `Node.transfer()`
- `transfer_fcfs_clearance()`
- BATCHのservice queue処理全体

理由:

- 拘束順位Vehicleの再評価
- `incoming_vehicles`全消去
- 対象外状態変更
- 二重評価
- TVT局所契約との不整合

### 9.2 局所専用処理の2責務

TVT局所専用処理を、少なくとも次の2責務に分ける。

A. 通過試行統括

- 完全な拘束順位列の走査
- 拘束順位外Vehicleの一時的FCFS走査
- clearance停止
- 通過不能時の後続候補確認
- 同一仮想timestepの終了判断

B. 1台分の物理移動

- 容量消費
- inlinkからの除去
- outlinkへの追加
- Vehicle位置とLink更新
- leaderとfollower
- `move_remain`
- `incoming_vehicles`からの削除
- clearance履歴更新

既存`Node.transfer()`から大規模な共通helperを直ちに抽出しない。まずTVT局所モジュール内に、BATCH Level 2の`_transfer_vehicle_reference()`相当の局所専用処理を設ける方向とする。

この「方向」は責務分割の採用である。関数名、引数、戻り値、配置モジュール名は本節で確定しない。

### 9.3 候補別結果に最低限残す情報

候補別結果に、最低限次を残す。フィールドのPython型、クラス名、公開API名は本節で確定しない。

- 候補識別
- resolved / unresolved
- unresolvedまたは終了理由
- Vehicleごとの対象Node仮想通過timestep
- 拘束順位内または拘束順位外
- 使用進路の種類
  - snapshot進路
  - 拘束順位内のbaseline進路
  - 拘束順位外の一時的baseline進路
  - Vehicle ID方式の仮想進路
- Vehicle ID方式で選択したoutlink
- 各仮想timestepの通過Vehicle
- clearance待ちのtimestepとVehicle
- 仮想計算で進めたtimestep数
- outlink別の条件付き平均流出率
- outlink別の流出許可残高推移
- `active > 0`かつ流出0の境界閉塞
- `active = 0`用制約付きsinkの使用
- outlink境界で流出したVehicle
- horizon末の必要な状態

これらは局所結果へ記録する。次へは書き込まない。

- 順位台帳
- 実World baseline collector
- 実WorldのVehicle、Link、Node
- 他候補の状態

### 9.4 正常なunresolved候補

次は、候補を壊れた計算として扱わず、理由を持つ正常なunresolvedとする。

- virtual horizonまでに必要な評価対象Vehicleが通過しない
- 条件付き平均境界近似下でも閉塞が解消しない
- `active > 0`かつ総実流出台数0の境界閉塞がhorizonまで影響する
- clearance待ちまたは容量不足がhorizonまで継続する
- 分類4Vehicleにhorizon中`acceptable_outlinks`が得られない
- 下流境界条件により必要な評価情報が揃わない

全buyerおよび全sellerについて、経済性評価に必要な対象Node通過timestepが揃えば、`configured_horizon_steps`へ達する前でも早期終了し、resolvedとする。必要情報が揃わないまま`configured_horizon_steps`へ達した場合は、上記のような具体的理由を持つ正常なunresolvedとする。

理由を表す正式なEnum名または文字列定数は、本節で確定しない。

### 9.5 重大不整合

次は推測で修復せず、例外停止する。

- 完全な拘束順位列のVisitKey重複
- 拘束順位内Visitの進路欠落
- 保存進路が対象Nodeのoutlinkではない
- VisitとVehicle状態の対応不整合
- 同じVehicleの同一timestep二重通過
- 容量が不正な負値
- inlink物理先頭でないVehicleを移動させようとする
- 必須状態欠落

例外クラス名とメッセージ文言は、本節で確定しない。自動削除、片側採用、進路の再選択、容量の切り上げでは継続しない。

### 9.6 候補ごとの独立性

候補ごとに独立したmimic状態を使用する。

候補別局所計算は次を変更しない。

- 実WorldのVehicle
- 実WorldのLink
- 実WorldのNode
- 実Worldの乱数状態
- 正式順位台帳
- baseline collector
- 他候補のmimic状態

不採用候補の順位、正式進路、分類3の一時進路、分類4の仮想進路を、順位台帳へ残さない。

## 10. 最終統合仕様

次の統合仕様を採用済みとする。

1. 候補ごとに、実Worldから独立した局所状態を構築する
2. 各仮想timestepで、完全な拘束順位列を先に走査し、clearance停止がなく余力があれば、拘束順位外Vehicleを一時的FCFS順で走査する
3. 両走査は、同じ物理状態、残容量、clearance履歴を共有する
4. outlink終端境界は観測結果により次へ分岐する
   - `active > 0`かつ総実流出台数 `> 0`
   - `active > 0`かつ総実流出台数 `= 0`
   - `active = 0`
5. `active > 0`かつ総実流出台数 `> 0`では、条件付き平均流出率と流出許可残高だけでなく、終端待機Vehicle数、物理FIFO、outlink流出容量、終端Node容量、`DELTAN=1`、その他のUXsim物理条件をすべて適用する
6. `active = 0`では、BATCH Level 2の単純sinkと異なる、outlink流出容量および終端Node容量を確認・消費する制約付きsinkを使用する
7. 全buyerおよび全sellerについて経済性評価に必要な対象Node通過timestepが得られれば、local horizon上限前でも早期終了し、resolvedとする
8. 必要情報が揃わないまま`configured_horizon_steps`へ達した場合は、具体的な理由を持つ正常なunresolvedとする
9. 候補評価中は、実World、正式順位台帳、baseline collector、実World乱数、他候補の状態を変更しない
10. 候補評価後にのみ、採用候補またはbaseline正式確定分岐に応じて、今回確定するVisitの順位と正式進路を原子的に保存する

この統合後、新たな制度上の論理矛盾は確認されていない。

前回節の原因別最終分岐は維持する。採用候補がある場合の確定範囲、全候補却下時およびbaseline情報不足時の意思決定窓内Visit全体、意思決定窓内Visitが0件のときの確定対象なし、は本節で変更しない。本節の統合項目10は、その分岐が選んだ「今回確定するVisit」について、順位と正式進路を評価後に原子的保存する、という前回契約の接続である。

## 11. Python実装時に必ず守る可読性方針

今後の完全な実装前仕様およびPython実装で、必ず次を守る。

- 正しく動くことを最優先とする
- 高度で巧妙なPythonテクニックより、Python初学者が処理を順番に追える明示的で可読性の高い実装を選ぶ
- 複数の実装方法がある場合は、短さや美しさより可読性を優先する
- 条件分岐や状態更新を過度に圧縮しない
- 複雑な内包表記、多重処理、暗黙的な副作用を避ける
- TVT-MPの根幹処理では、少し長くなっても処理段階と判断理由がコード上で追える構造にする
- 変数名、関数名、結果型名、診断フィールド名は、長くても見ただけで交通上および処理上の意味をイメージできる名称にする
- Vehicle、Visit、Node、inlink、outlink、timestep、順位、進路、境界観測、流出許可残高を曖昧な短縮名で混同しない
- 登録時に保証済みの不変条件を、実行時に不要に重複検証しない
- 実行時検証は、実行中に変化し得る状態と、原因不明の停止や誤計算を招く重大不整合に限定する
- 確定済み制度設計を、実装の都合で簡略化、再解釈、変更しない
- コードコメントとdocstringでは、Python上の動作だけでなく交通上の意味も説明する

本節は、この方針に合わせて関数名や型名を今決めない。名前を短く確定すること自体が、次の実装前仕様の作業である。

## 12. 撤回済み誤案

次は採用事項ではない。採用済み仕様に混入させない。誤って再提案しないための撤回済み案としてだけ記録する。

- `active = 0`で境界流出を完全停止する案
- `active = 0`で人工的に最大1台／timestepとする案
- `active = 0`で未使用sink枠を繰り越さない案
- `active = 0`で同一timestepに2台以上を無条件に禁止する案
- BATCH Level 2の単純sinkをTVT-MPの`active = 0`分岐へそのまま適用する案
- `route_pref`に基づく確率と局所仮想乱数を使う案
- 分類3のbaseline進路を捨て、分類3と分類4を両方Vehicle ID方式で処理する案
- 全物理outlink数にVehicle ID剰余を適用し、受入不能なら次のoutlinkを循環探索する案

`route_pref`と局所仮想乱数の案は撤回済みである。今後の推奨案または未確定候補として復活させない。

分類3をVehicle ID方式へ置き換える案も撤回済みである。分類3はbaseline進路の読取専用一時使用のままとする。

BATCH Level 2はFIFO制約を持つ単純sinkである。TVT-MPの`active = 0`分岐は、FIFOに加えてoutlink流出容量と終端Node容量等を確認・消費する制約付きsinkである。この差を消す実装を採用しない。

## 13. 今回確定しない実装契約

次は、本節で独自に確定しない。次の完全な実装前仕様で確定する実装契約として残す。

- 公開API名
- 公開結果型名
- private helper名
- 新規本番モジュール名
- 専用テストファイル名
- 診断フィールドの具体的なPython型
- unresolved reasonの正式なEnumまたは文字列名
- 各helperの最終シグネチャ
- 既存上流結果型へ追加する具体フィールド
- 完全な拘束順位列を上流結果から受け渡す具体API
- mimic状態を構築する具体的クラス構成
- 実装単位の分割順
- 性能最適化
- 複数車線対応
- `DELTAN`が1以外の場合の一般化

これらが未確定であることは、本節の制度採否が未確定という意味ではない。通過順、進路4分類、clearance、状態更新、下流境界3分岐、候補独立性、正常unresolvedと重大不整合の区別は確定している。未確定なのは、それをPythonの名前と型とファイル境界へ落とす契約である。

## 14. 次の再開地点

**2026-09-22更新注記：** この再開地点は、拘束順位外処理・下流境界・統合仕様の確定記録を作成した時点の歴史的記録である。その後、公開API、結果型、helper責務、例外契約、診断契約、モジュール構成、専用テスト契約、実装区分を含む完全な実装前仕様を確定した。現在の最新正本は、後続の「TVT-MP候補別局所仮想計算の完全な実装前仕様」である。現在の直接作業は、その追記を独立確認し、利用者がMarkdownをcommitおよびpushしたあと、最初の実装区分「正式進路付き順位台帳と原子的確定」の目的と範囲を利用者へ提示し、合意後にその区分だけへ着手することである。直ちにPython実装へ進む指示ではない。この再開地点を現在の作業指示として読まない。

次の直接作業は、本節で確定した拘束順位外処理、下流境界3分岐、統合仕様の再検討ではない。

次の直接作業は、公開API、結果型、helper責務、診断型、例外契約、モジュール構成、専用テスト契約、既存上流結果との接続を含む、完全な実装前仕様の作成である。

その実装前仕様では、本節の制度を簡略化しない。可読性方針を守る。撤回済みの`route_pref`案、分類3のVehicle ID置換、`active = 0`の流出停止、`active = 0`の人工的な最大1台制限、BATCH Level 2単純sinkの流用を、採用候補へ戻さない。

Python実装と専用テストは、その実装前仕様が確定するまで着手しない。

# TVT-MP候補別局所仮想計算の完全な実装前仕様

**記録日：2026-09-22**

本節は、保存済みcommit `5235089` までに確定した制度、その後の現行コード接続調査、およびその調査に基づく完全な実装前仕様案を、Python実装前の完全仕様として統合した正本である。

本節の作成は、新しい制度の採否ではない。確定済みの制度を、公開API、結果型、helper責務、状態の受渡し、例外契約、診断契約、モジュール構成、テスト契約、実装区分へ落とす。

候補別局所仮想計算のPython実装と専用テストは、本節を記録した時点では未着手である。本節の記録と同時に実装を開始しない。

**2026-09-23補修：** 独立レビューの3点を、現行コードで確認したうえで本節へ補った。制度の採否は変えていない。補ったのは、区分2の先行確定を原子的確定APIへ接続する実装契約、`real_W.copy()` 後に対象外オブジェクトを残したまま局所対象だけを更新する契約、`configured_horizon_steps` の端点と `simulated_timestep_count` の計数である。根拠は本節の該当箇所に書く。

**2026-09-23補修（resolvedとなる仮想timestepの完了契約）：** buyerとsellerの必要な対象Node通過timestepが揃った場合でも、対象Node通過処理の直後に候補計算全体を終了しない。その仮想timestepについて、inlink前進、対象Node端到着登録、outlink前進、outlink終端境界処理、容量と状態と診断の更新を完了した後に、resolvedとして終了する。BATCH Level 2のtrigger通過時早期終了は採用しない。詳細は本節の「仮想timestep loop」「早期終了とhorizon」「結果型と診断型」「専用テスト契約」に書く。

直前の次の節は削除しない。本節はそれらを置き換えず、実装契約として接続する。

- 「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」
- 「TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録」（保存済みcommit `1613eb9`）
- 「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」

## 何のための処理か

時点Tの交通を、候補ごとに実Worldから切り離して写す。候補ごとに、守る順番と対象交差点から出る進路を、仮想実行の前に整理する。実Worldは変えず、その候補が成立した場合の交通を写しの上で試す。得るものは、その候補のbuyerとsellerが対象交差点を通過する予想時刻である。損得、支払、採用候補の選択は、この局所計算の仕事ではない。

既存の候補形成、一般形順位、FIFO検査、baseline collector、下流境界observerは維持する。新しく追加する主要部分は、正式進路付き順位台帳、完全な拘束順位列、候補別局所状態、局所仮想計算、候補別結果である。

役割は次のとおり分け、混同しない。

- 正式進路付き順位台帳は、過去に確定したVisitの確定順位と正式進路を読むため、および最終結果決定後に今回確定する順位と正式進路を原子的に保存するために使う。
- 完全な拘束順位列の構築処理は、既存結果と順位台帳を読み、4区分を整理して連結するために使う。
- 候補別局所状態は、完成済みの拘束順位列に従って、候補ごとの交通を実Worldから独立して仮想実行するために使う。
- 候補別結果型は、対象Node通過時刻、resolvedまたはunresolved、診断を返すために使う。

候補別局所状態と候補別結果型は、完全な拘束順位列を構築するために必要なものではない。完成済みの拘束順位列を使って計算し、その結果を返すために必要である。

## モジュール構成

既存の `uxsim/order_control_tvt_node_rank_state.py` を、正式進路付き順位台帳へ拡張する。別の順位台帳は作らない。既存の順位読取は維持する。正式進路の読取と、順位および正式進路の原子的確定を同じモジュールへ追加する。

新規モジュールは次の3つとする。

`uxsim/order_control_tvt_mp_local_binding_rank_sequence.py`

- 既存結果連鎖と順位台帳を読み取る
- `k_decision_window` と `k_fixed` を算出する
- 完全な拘束順位列の4区分を構築する
- VisitKey重複、進路欠落等を検証する
- 読取専用の構築結果を返す
- Vehicleを物理的に動かさない
- 順位台帳を変更しない

`uxsim/order_control_tvt_mp_candidate_local_state.py`

- 時点Tの実Worldから、候補ごとに独立した局所状態を構築する
- 対象Node、全inlink、全outlink、対象範囲のVehicle、残容量、clearance履歴等を保持する
- 実Worldのオブジェクトを変更しない
- 候補間で状態を共有しない

`uxsim/order_control_tvt_mp_candidate_local_virtual_calculation.py`

- 候補別局所仮想計算の公開入口
- 仮想timestep loop
- 拘束順位列の走査
- 拘束順位外Vehicleの一時的FCFS走査
- 1台分の対象Node通過
- outlink終端境界の3分岐
- 早期resolvedおよび正常なunresolved
- 候補別結果と診断結果の作成

準備、局所状態、仮想計算の順でファイルを追える構成を優先する。これより細かいモジュールには分けない。

**2026-09-24注記：** 上記は実装前のモジュール予定である。保存済み実装は、仮想計算を1ファイルにまとめず、仮想時計、拘束順位の対象Node通過、局所Vehicle前進を別モジュールにした。統括ファイル `order_control_tvt_mp_candidate_local_virtual_calculation.py` は未作成である。最新の実装状況は、本ファイルの「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」を参照する。

`Node.transfer()`、`transfer_fcfs_clearance()`、BATCHのservice queue全体は直接呼ばない。BATCH Level 2の `_transfer_vehicle_reference()` も直接呼ばない。既存 `Node.transfer()` から大規模な共通helperを直ちに抽出しない。交通上同じ意味となる更新は、TVT専用処理として明示的に書く。

対応する専用テストは、既存の `tests_order_control_tvt_node_rank_state.py` へ原子的確定のケースを追加し、新規3モジュールに対応する次のテストファイルを置く。

- `tests_order_control_tvt_mp_local_binding_rank_sequence.py`
- `tests_order_control_tvt_mp_candidate_local_state.py`
- `tests_order_control_tvt_mp_candidate_local_virtual_calculation.py`

## 公開入口

公開入口は `evaluate_tvt_mp_candidate_local_virtual_calculations` とする。

入力は次の3つである。

- `real_W`：`baseline_timestep_T` と同じ時点Tにある実World。局所計算は `real_W` を変更しない
- `fifo_inspection_set_result`：既存のFIFO検査結果。内部の結果連鎖から、一般形順位、候補集合、意思決定窓、baselineの `fork_result` を取得する
- `rank_states_by_node_name`：対象Node名ごとの `OrderControlTvtNodeRankState`。候補評価中は読取専用である

戻り値は `OrderControlTvtMpLocalVirtualCalculationSetResult` である。

評価単位は、FIFOを通過した候補をまとめて評価することである。候補ごとに独立した局所状態を作る。FIFOで却下された候補は仮想実行しない。baseline情報不足等により候補自体が形成されていないNodeは、無理に実行しない。

呼出前提は `real_W.T == fork_result.baseline_timestep_T` である。一致しない場合、過去の時点Tを推測して復元しない。`ValueError` とする。凍結された周辺状態の公開結果は現行コードにないため、実WorldがTから進んだ後には呼べない。

評価中に変更できるのは、候補ごとに作成した局所状態だけである。変更しない対象は、実World、実Worldの乱数状態、正式順位台帳、baseline collector、downstream boundary結果、他候補の局所状態である。

この公開入口は、順位と正式進路の原子的確定APIを呼ばない。

## 完全な拘束順位列の公開構築処理

公開構築処理は `build_tvt_mp_local_binding_rank_sequence` とする。

局所仮想計算本体は、この関数が返した完成済みの拘束順位列を受け取る。局所計算の途中で、順位情報を各結果から場当たり的に探し直さない。

構築結果は、候補評価と、最終結果決定後の正式確定の双方で再利用できる形にする。候補評価のあと、同じ列を再計算して内容が変わる構造にはしない。構築済みの読取専用結果を、候補評価結果と関連付けて保持する。

この関数はVehicleを動かさない。順位台帳も変更しない。

## 正式進路付き順位台帳

既存 `OrderControlTvtNodeRankState` の確定済み1件は、少なくとも次を保持する。

- VisitKey。`(vehicle_name, visit_id)`
- `assigned_rank`
- `formal_route_next_link_name`

正式進路は、そのVisitの順位確定をもたらしたbaselineにおいて、対象Node到着時に得られた対象Node向けoutlink名である。実Worldの将来進路を強制するものではない。局所候補評価で、確定済みVisitを再現するための進路である。

読取は次を維持または追加する。

- `confirmed_visit_keys_in_order()`
- `assigned_rank(visit_key)`
- `formal_route_next_link_name(visit_key)`

`formal_route_next_link_name` が保存されていない場合は `None` を返す。空文字で代用しない。保存済みであるように見せない。

原子的確定APIは `confirm_visits_and_formal_target_node_routes_atomically` とする。

入力は、確定順に並んだVisitKeyと `formal_route_next_link_name` の組、および対象Nodeのoutlink名集合である。台帳自身はcollectorもWorldも参照しない。呼出側が、その順位を確定させたbaselineの対象Node到着時進路を組にして渡す。

反映前に、メモリ上の候補状態だけで全件検証する。

- VisitKeyの形
- 呼出入力内のVisitKey重複
- 全Visitが現在未確定であること
- 既確定Visitを再確定しないこと
- 正式進路が `None` でも空文字でもないこと
- 正式進路が、渡された対象Nodeのoutlink名集合に含まれること
- 入力順が、現在の確定末尾の次から連続する新しい順位になること

入力不整合は `ValueError` とする。これは既存 `confirm_visits_in_order()` が、重複、未登録、再確定を `ValueError` としている契約に合わせる。検証用の候補状態を作ったあと、台帳内部の対応が崩れていた場合は `RuntimeError` とする。どちらの場合も、実台帳への代入は検証成功の後だけに行う。1件でも不整合なら、順位も進路も1件も変更しない。全件正常な場合だけ全件を一括反映する。部分反映はしない。

候補評価中は、このAPIを呼ばない。

このAPIを呼ぶ時点は2つある。1つは、候補形成より前の区分2の先行確定である。もう1つは、最終結果決定後の、採用候補またはbaseline順位による正式確定である。後者は既定の原因別最終分岐に従う。

区分2の接続は、2026-09-23に現行コードで確認した。本番の先行確定関数は次の2つだけであり、どちらも今は `confirm_visits_in_order()` をNodeごとに1回呼ぶ。これらより上の、TVTサイクル全体を束ねる本番関数は未実装である。

- `confirm_already_arrived_undetermined_visits`
- `confirm_leading_nonparticipating_decision_window_visits`

新しいTVT-MP本番経路では、この2関数が順位だけの旧APIを使わない。各Visitへ、その順位確定をもたらしたbaselineの対象Node到着時進路を対応付け、原子的確定APIで保存する。既到着の列を先に確定し、その後に先頭連続非参加の列を確定する。この順序は変えない。候補形成の前に、区分2の確定を終える。

進路の取得元は、その場にある `fork_result.collector.get_baseline_visit_snapshot(vehicle_name, visit_id)` の `route_next_link_name` である。alignmentの解決済みVisitは到着時刻とtiebreakerだけを持ち、進路は持たない。collector側では、snapshot時に到着済みのVisitも、baseline中に到着を記録するVisitも、空でない `route_next_link_name` を要求する。したがって、この2関数が確定するVisitの進路は、その呼出位置でcollectorから読める。読めない場合は補完せず、原子的確定の入力不整合として止める。順位だけを残さない。

outlink名集合は、この2関数の現行引数には無い。baseline driverはfork Worldを返さず、実Worldの時刻はTのままである。検証材料は、時点Tの実Worldにおける対象Nodeの `outlinks` の名前を、呼出側が原子的確定APIへ渡す。台帳自身はWorldを見ない。

返す `confirmed_arrived_visit_keys` と `confirmed_leading_nonparticipating_visit_keys` は、これまでどおりVisitKeyの列である。列の中身を進路付きの組へ変えなくてよい。進路は台帳へ保存する。確定対象が0件のときは、現行の空列確定と同じく台帳を変えず、進路欠落にもしない。

`confirm_visits_in_order()` を本番コードから呼んでいるのは、上記2関数だけである。ほかの呼出は専用テストと、テストが台帳を直接準備する箇所である。したがって、この2関数を原子的確定APIへ移せば、新しいTVT-MP本番経路の区分2は旧APIを使わない。旧API自体は、既存テストと互換のために残す。

完全な拘束順位列の構築は、区分2の正式進路が台帳に保存済みであることを前提にする。構築処理は区分2を再確定しない。

既存 `confirm_visits_in_order()` は削除しない。既存テストと既存互換性のため残す。このAPIで確定したVisitの `formal_route_next_link_name` は `None` である。新しいTVT-MP本番経路では使用しない。新しい正式確定経路は、原子的確定APIへ移行する。

`export_state()` は、確定済み各Visitに `formal_route_next_link_name` を追加する。既存APIで確定したVisitは `None` のまま出力する。

実行時検証は、登録時に保証済みの不変条件を毎回台帳全体へ重複して行わない。今回の入力、未確定状態、正式進路、原子的反映に必要な重大条件に限定する。

区分1として局所計算に必要になったVisitについて、局所通過に必要な正式進路が台帳から取得できず、かつsnapshot進路の使用規則にも該当しない場合に限り、その候補を推測で続行せず重大不整合として停止する。collectorの進路、現在の `Vehicle.route_next_link`、今回baselineの進路で自動補完しない。古いAPIで確定されたVisitのすべてを、それだけで重大不整合とはしない。

## 完全な拘束順位列の結果型

読取専用結果型は `OrderControlTvtMpLocalBindingRankSequence` とする。

最低限、次を保持する。

- `node_name`
- `concrete_buyer_candidate_set`
- 区分別Visit列4本
- 4本をこの順に連結した完成列
- `k_last_buyer`
- `k_decision_window`
- `k_fixed`

Visit要素型は `OrderControlTvtMpLocalBindingRankVisit` とする。

最低限、次を保持する。

- `visit_key`
- `vehicle_id`
- `binding_partition`
- `binding_rank`。完成列の中の1始まりの通過試行順
- `route_next_link_name`。局所通過に使う進路
- `route_origin`
- `inlink_name`
- `baseline_arrival_timestep`
- `arrival_tiebreaker`
- `trade_role`。buyer、seller、非参加、または今回の取引範囲外

`binding_partition` は番号だけで表さない。進路4分類の名前とも別の列挙にする。

区分名と構築方法は次である。

`confirmed_before_this_baseline`

今回のbaseline開始前から確定済みで、時点Tに対象Nodeを未通過のVisitである。既到着先行確定結果の `confirm_result.k_confirmed_before` が、今回の先行確定前の台帳長さである。確定後の `confirmed_visit_keys_in_order()` のその長さまでのprefixを、collectorにrecordがあるVisitだけに限る。snapshot登録はincomingとinlink上のVehicleだけなので、すでに通過して対象範囲を離れたVisitはここへ入らない。順序は台帳の確定順を維持する。

`preconfirmed_by_this_baseline`

今回のbaseline結果による既到着先行確定Visitの列の後へ、意思決定窓先頭の連続する非参加Visitの先行確定列を続ける。既存結果が返した順序を維持し、後段で条件を推定し直さない。局所通過に使う進路は、候補形成前に原子的確定APIで台帳へ保存済みの `formal_route_next_link_name` である。未保存なら、collectorの値で埋めず重大不整合として止める。

`trade_scope_of_this_candidate`

当該候補の `trade_scope` 内である。通過試行順は `trade_order` の先頭 `last_buyer_rank` 件である。これは取引後順位である。`trade_scope` 自体の並びはbaseline順なので、通過試行順として使わない。buyerとsellerの順位は変わり、非参加Visitは固定されたbaseline順位枠を維持する。この区分を、全Visitの順位が変わる範囲とは記録しない。

`outside_trade_scope_inside_k_fixed`

`trade_scope` 外かつ `k_fixed` 内であり、baseline順位を維持するVisitである。N+1位以降の意思決定窓内Visitを含み得る。P-1条件の外だが意思決定窓内の遅いVisitも含み得る。これらは `trade_order` には含まれない。

完成列は、上記4区分をこの順に連結する。完成列が4本の連結と一致しない場合は重大不整合とする。同一VisitKeyの重複は、区分内でも区分間でも禁止する。重複時は自動除外しない。局所通過に使う進路が欠ける場合も自動補完しない。

## `k_decision_window` と `k_fixed`

`k_last_buyer` は、既存の `last_buyer_rank` をそのまま使う。これは上限N適用後の `candidate_visits` 内における、最後のbuyerの1始まりbaseline位置である。

`k_decision_window` は、`remaining_decision_window_visit_keys` の件数である。この列は、先頭の連続する非参加を確定したあとに残る意思決定窓全体であり、上限Nでは切られていない。到着時刻、`arrival_tiebreaker`、`vehicle_id` の順である。先行確定後に残る未確定列の先頭部分でもある。

`k_fixed` は `max(k_last_buyer, k_decision_window)` である。3つの整数は構築結果へ明示して返す。baseline順位の新しい整数フィールドは追加しない。並びは、既存の時刻、`arrival_tiebreaker`、`vehicle_id` と、既存結果がすでにその順で持つ列を使う。

`trade_order` 全体を完全な拘束順位列としない。`trade_order` の単純prefixだけでも完成列にしない。`trade_order` の先頭 `last_buyer_rank` 件は、区分3の通過試行順としてだけ使う。

区分4の構築と、Pythonの0始まりindexの対応は次である。制度上の順位は1始まりである。`remaining_decision_window_visit_keys[0]` は制度上の1位である。

`k_last_buyer` が `k_decision_window` 以上のとき、取引範囲は意思決定窓の末尾まで届いている。区分4は空である。

`k_last_buyer` が `k_decision_window` より小さいとき、区分4は `remaining_decision_window_visit_keys[k_last_buyer:]` である。1始まりの順位 `k_last_buyer` までのVisitを除くため、0始まりの開始位置は `k_last_buyer` そのものとする。例えば `k_last_buyer` が2なら、窓の先頭2件は区分3側にあり、区分4はindex 2から始まる。このスライスには、上限Nで `candidate_visits` から落ちた窓内Visitと、P-1条件で候補母集団に入らなかった遅い窓内Visitが入り得る。

区分3に含める `trade_order[:last_buyer_rank]` も、1始まりの件数 `last_buyer_rank` を、0始まりスライスの終端indexとして使う。`trade_order[:2]` は制度上の1位と2位である。

## 候補別局所状態

**2026-09-23補修：** `World.copy()` は `pickle` によるWorld全体の複製である。コピーは実Worldと別オブジェクトであり、leader、follower、`NODES`、`LINKS`、`VEHICLES` の参照はコピーの内側で閉じる。対象外のNode、Link、Vehicleをコピー後に削除する方式は、`route_next_link`、目的地、leader、車両登録を壊す危険があるため採用しない。BATCH Level 2のように小さなmimic Worldを手で組み立てる方式も、今回の局所状態の構築方式にはしない。採用するのは、World全体をコピーしたまま、更新する対象だけを固定する方式である。

候補ごとに、時点Tの `real_W.copy()` で独立したWorld全体のコピーを作る。コピー後に対象外のNode、Link、Vehicleを削除しない。対象外オブジェクトはコピーの中に存在するが、局所計算の更新対象にしない。存在する対象外オブジェクトをシミュレーションすることとは別である。残す理由は、削除によってWorld内部の参照を壊さないことにある。

構築時に、TVT専用loopが更新する局所対象集合を明示して固定する。その集合は次である。

コピー後の局所計算が対象にする範囲は、次に限定する。

- 対象Node
- 対象Nodeの全inlink
- 対象Nodeの全outlink
- 時点Tに対象inlinkまたは対象outlink上にいるVehicle
- 時点Tに対象Nodeの `incoming_vehicles` へ登録されているVehicle
- outlink終端境界の初期占有に必要な、outlink上のVehicle

候補のVisitだけを抜き出したWorldにはしない。

Vehicleについて保持する状態は、`state`、`link`、`x`、`x_old`、`x_next`、`v`、`lane`、leader、follower、`link_arrival_time`、`move_remain`、現在のorder-control Visit、`visit_id`、到着情報、snapshot進路、必要なbaseline進路の参照である。

Linkについて保持する状態は、vehiclesの物理順、`capacity_out_remain`、`capacity_in_remain`、`cum_arrival`、`cum_departure`、`traveltime_actual`、`vehicles_enter_log`、laneおよび入口空間の判定に必要な状態である。

Nodeについて保持する状態は、`flow_capacity`、`flow_capacity_remain`、`incoming_vehicles`、`last_order_control_inlink`、`last_order_control_entry_timestep`、`order_control_clearance_timesteps` である。

候補Aの更新が候補Bへ影響しない。実Worldへ影響しない。実Worldの乱数を消費しない。写しの中のオブジェクトから、実WorldのLinkやVehicleを更新できる参照構造にはしない。

コピーしたWorldに対して `World.exec_simulation()` を呼ばない。コピーWorld全体への `Node.update()`、`Link.update()`、`Vehicle.update()` も呼ばない。対象Node、その全inlink、その全outlink、それらに属する対象Vehicleだけを、TVT専用処理で更新する。T以後に、対象外の領域から新しいVehicleを局所対象集合へ流入させない。対象外Vehicleは走行させない。

初期研究範囲は、単車線、`DELTAN=1`、対象Nodeを目的地とするtrip-end Vehicleは通過候補外、signal条件は扱わない、inlink始端からT以後の新規流入なし、である。

inlink上の車がNode端へ進む移動は、写しの上の既存の車両移動を使ってよい。その到着登録では `route_next_link_choice()` を呼ばない。対象Nodeへの到着は、局所側が `incoming_vehicles` へ重複なく追加する。

## 進路4分類

拘束順位の4区分とは、名前を分けて保持する。分類名は次の4つである。

`snapshot_route_already_decided`

snapshot時点で対象Nodeからの進路が決まっている。拘束順位内にも、拘束順位外にもあり得る。局所通過にはsnapshot進路を固定して使う。そのoutlinkが一時的に入れなくても、別outlinkへ変更しない。通過できるまで待つ。実Worldの進路は強制しない。collector上では、`was_arrived_at_snapshot` が真であり、`route_next_link_name` が空でない記録がこの分類の材料である。この値は、到着済みVisitへの再記録が拒否されるため、baseline中に上書きされない。

`baseline_route_inside_binding_sequence`

snapshot時点では進路が未決定であり、今回の全World baselineで対象Node到着時に進路が判明し、完全な拘束順位列に含まれる。候補評価中は読取専用で一時使用する。候補評価中に順位台帳を変更しない。最終結果のあと、今回確定対象になったVisitだけが、確定順位と正式進路の原子的保存対象になり得る。実Worldの進路は強制しない。受入不能でも別outlinkへ変更しない。

`baseline_route_outside_binding_sequence_temporary`

snapshot時点では進路が未決定であり、今回の全World baselineで対象Node到着時に進路が判明した、拘束順位外のVehicleである。候補評価中だけ、そのbaseline進路を読取専用で一時使用する。正式進路とは呼ばない。順位台帳へ保存しない。実Worldの進路は強制しない。受入不能でも別outlinkへ変更しない。

`vehicle_id_among_acceptable_outlinks`

snapshotでも今回baselineでも対象Node向け進路が判明していない、拘束順位外のVehicleだけに使う。Nodeへの仮想到着時点では進路を割り当てない。仮想通過を実際に試す時点で `acceptable_outlinks` を作る。条件は、その時点で `outlink.capacity_in_remain >= DELTAN` であり、かつoutlink入口にVehicleが入る空間があることである。`outlink.id` 昇順に並べ、`selection_index = real_vehicle.id % len(acceptable_outlinks)` で1つ選ぶ。選択した同じ処理の中で直ちに通過させる。`acceptable_outlinks` が空なら、そのtimestepでは選択せず、通過させない。次の仮想timestepで再評価し得る。実Worldの `W.rng`、局所乱数、`route_next_link_choice()` は使わない。選択結果は診断へ残す。順位台帳へ正式進路として保存しない。

この分類は、本当の将来進路の予測ではない。楽観的な仮想流入先への決定論的な分散である。同じ入力なら同じ結果になる。最適な負荷分散は保証しない。UXsim本来の `route_next_link_choice()` の再現ではない。候補によって `acceptable_outlinks` が変われば、同じ車でも候補ごとに異なる仮想進路になり得る。その差は許容する。それを本来の経路選択の再現とは説明しない。

`route_pref`、局所乱数、実Worldの乱数、`route_next_link_choice()` は、どの分類でも使わない。保存済みまたはbaselineの進路が受入不能であることを理由に、Vehicle ID方式へ切り替えない。

区分1の過去正式進路は、台帳に保存されていることが原則である。snapshot進路の使用規則に該当する区分1は、局所通過にsnapshot進路を使う。台帳上の過去正式進路を、今回のbaselineや局所結果で上書きしない。局所通過に必要な進路を、台帳からもsnapshot進路の規則からも取得できない区分1だけを、自動補完せず重大不整合として止める。

## 仮想timestep loop

ここでの番号は、1つの仮想timestepの内部の処理順である。作業管理のためのStep体系ではない。新しいStep名称を、この番号から作らない。

**2026-09-23補修：** 端点は、名前からではなく、baseline driverとBATCH Level 2の `_run_limited_virtual_loop()` を突き合わせて決める。baselineは `duration_t2 = configured_horizon_steps * DELTAT` で `exec_simulation()` する。この呼出が交通を実行するのは時刻Tから `T + configured_horizon_steps - 1` までであり、その後に時計だけを `T + configured_horizon_steps` へ進める。したがって `final_fork_timestep` は `T + configured_horizon_steps` だが、その時刻の交通はbaselineでは未実行である。局所loopの容量規則は、BATCH Level 2の `offset == 0` がsnapshot残容量、`offset >= 1` が時刻を進めてから補充、という構造をすでに採用している。端点も同じloopに合わせる。`virtual_horizon` に相当する値を `configured_horizon_steps` とし、通過試行する仮想時刻は `T + offset`（`offset` は0以上 `configured_horizon_steps` 以下）である。両端を含む。別のhorizon引数は受け取らない。

`simulated_timestep_count` は、snapshotの時刻Tから仮想時計を進めた回数である。Tだけの試行では0である。上限まで進めたときは `configured_horizon_steps` である。BATCH Level 2が `offset > 0` のときだけこの計数を増やすのと同じである。

`configured_horizon_steps == 0` のとき、通過試行するのはTだけである。時計は進めない。baseline driverは1未満のhorizonを拒否するため、通常のbaseline結果は0にならない。定義自体は、0を受け取った局所loopがTの次の時刻へ進まないために残す。

`configured_horizon_steps` が2のとき、処理する仮想時刻はT、T+1、T+2である。Tの通過試行で必要なbuyerとsellerの対象Node通過timestepが揃えば、計数は0のまま、その仮想timestepの時刻末処理を完了した後にresolvedとする。T+1の試行で揃えば、計数は1で、同様にそのtimestep末処理の後にresolvedとする。T+2の試行で揃えば、計数は2で、同様にそのtimestep末処理の後にresolvedとする。T+2の仮想timestep全体が終わっても不足なら、計数は2のままunresolvedとする。T+3は実行しない。

buyerとsellerの必要通過timestepが揃ったかどうかの記録は、その時刻の対象Node通過走査が終わり、通過できたbuyerとsellerの対象Node通過timestepを記録した直後に行う。通過走査の前には行わない。候補計算全体の終了と `resolved` フラグの設定は、その仮想timestepの時刻末処理がすべて完了した後に行う。最終許容時刻 `T + configured_horizon_steps` の試行で揃った場合も、同じtimestepの時刻末処理の後にresolvedとする。その試行の時刻末処理の後も不足している場合だけunresolvedとする。

各仮想timestepの全体順序は次である。ここでの番号は、1つの仮想timestep内部の処理順である。作業管理のためのStep体系ではない。

1. `offset > 0` の場合だけ、仮想時刻を進め、対象Linkおよび対象Nodeの容量を補充する。最初のtimestep（`offset == 0`）は、snapshotの残容量をそのまま使う。2つ目以降は、UXsimの `Link.in_out_flow_constraint()` と `Node.flow_capacity_update()` と同じ補充を行う。
2. 必要な累積配列を現在の仮想時刻まで延長する。
3. 完成した拘束順位列を先頭から走査する。未到着、inlinkの物理先頭でないこと、通常の容量不足または入口空間不足は、そのVisitを残して次を見る。通過できるVisitは、そのVisitの進路分類に対応する進路で通過させる。拘束順位列の順番は変えない。拘束順位の走査中にclearanceが未充足なら、対象Node通過処理を終える。拘束順位外Vehicleの処理へ進まない。
4. clearanceで止まっておらず、対象Nodeの `flow_capacity_remain` が `DELTAN` 以上あるとき、その時刻までに到着済み、未通過、完成した拘束順位列に含まれない、trip-endではないVehicleを抽出し、現在Visitの対象Node到着時刻、固定 `arrival_tiebreaker`、Vehicle IDの昇順で走査する。この順は正式なbaseline順位でもTVT順位でもなく、順位台帳へ保存しない。通常の物理条件または容量条件で通れないときは、そのVehicleだけを残す。別inlinkに属する後続の通過可否は確認できる。同じinlinkの後続は、物理先頭でないため追い越せない。clearance未充足なら、拘束順位外の残りを確認しない。対象Nodeの `flow_capacity_remain` が `DELTAN` 未満になったら、対象Node通過処理を終える。拘束順位走査のあと、拘束順位外走査の前、および対象Node通過処理の途中では、容量を再補充しない。

**2026-09-24注記：** 保存済みの拘束順位走査では、Node流量容量不足は走査終了ではない。未到着、物理先頭でないこと、容量不足、入口空間不足と同じ一時スキップであり、同じ走査で後続Visitを試す。走査を途中で終えるのはclearance未充足だけである。`binding_sequence_completed` は、Node流量が残っているという意味ではない。最新契約は「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」を参照する。

5. 対象Node通過成功Vehicleの通過timestepを記録する。
6. buyerとsellerの必要な対象Node通過timestepが揃った場合は、「この仮想timestep末でresolvedとして終了する」ことを記録する。ここでは候補計算全体は終了しない。
7. inlink上の局所対象Vehicleを前進させる。
8. 新たに対象Node端へ到達したVehicleを `incoming_vehicles` へ重複なく追加する。通過したVehicleだけを `incoming_vehicles` から削除する。timestep末に `incoming_vehicles` を全消去しない。未通過のVehicleは次のtimestepへ残す。通常Worldの全消去後に `Vehicle.update()` が再登録する流れには依存しない。
9. outlink上の局所対象Vehicleを前進させる。
10. outlink終端へ到達したVehicleについて、該当する下流境界処理を行う。下流待ちあり・実流出あり（`active_timestep_count > 0` かつ `transferred_vehicle_count > 0`）、下流待ちあり・実流出なし（`active_timestep_count > 0` かつ `transferred_vehicle_count == 0`）、下流待ち観測なしの制約付きsink（`active_timestep_count == 0`）のいずれかである。詳細は「outlink終端境界」に従う。
11. 容量、流出許可残高、累積台数、Vehicle状態、境界流出、診断を完成させる。
12. 手順6でresolved終了が決まっていれば、ここで候補計算を終了する。`resolved` フラグと終了時点の情報は、この時刻末処理完了後の候補結果へ設定する。
13. resolvedでなく、最終許容時刻で必要情報が不足していれば、理由付きunresolvedとする。
14. resolvedでも最終許容時刻でもなければ、次の仮想timestepへ進む。次のtimestepでは、拘束順位列を再び先頭から評価する。前のtimestepで一時スキップした拘束順位Visitも再評価する。拘束順位外の処理対象集合は、残っている未通過Vehicleと新たに到着したVehicleから作り直す。`merge_priority` も乱数も使わない。

**resolvedとなる仮想timestepの完了契約**

buyerとsellerの必要な対象Node通過timestepが揃った場合、対象Node通過処理の直後に候補計算全体を終了しない。その仮想timestepについて、次の時刻末処理を完了した後にresolvedとして終了する。

1. 対象Node通過処理によって生じた全状態更新を完了する
2. inlink上の局所対象Vehicleを前進させる
3. 新たに対象Node端へ到達したVehicleを `incoming_vehicles` へ重複なく追加する
4. outlink上の局所対象Vehicleを前進させる
5. outlink終端へ到達したVehicleについて、下流待ちあり・実流出あり、下流待ちあり・実流出なし、下流待ち観測なしの制約付きsinkのいずれかの下流境界処理を行う
6. 実際に発生した容量消費、累積台数、Vehicle状態、流出許可残高、境界流出、診断情報をすべて更新する
7. その仮想timestep末の整合した状態を候補結果へ残す
8. その後にresolvedとして候補計算を終了する

buyerとsellerの対象Node通過timestep自体は、対象Node通過時に記録した値をそのまま使用する。時刻末処理によって書き換えない。

**resolvedとなる仮想timestepでも更新する容量と状態**

対象Node通過成功時は、通常どおり `inlink.capacity_out_remain`、outlinkの `capacity_in_remain`、対象Nodeの `flow_capacity_remain`（有限のとき）、`cum_departure`、`cum_arrival`、`traveltime_actual`、Vehicle、Link、leader、follower、`move_remain`、Visit、clearance履歴等を更新する。

outlink終端境界処理時は、該当する下流境界状態に応じて、下流待ちあり・実流出ありでは条件付き平均流出率、流出許可残高、物理FIFO、outlink流出容量、終端Node容量、`DELTAN=1` およびその他の既定物理条件を適用し、実際に境界流出した台数分だけ流出許可残高と流出容量を減らす。終端Nodeの `flow_capacity` が有限のときは、流出成功時に終端Node容量も消費する。下流待ちあり・実流出なしでは、local horizon内の境界閉塞を維持し、終端から流出させず、流出許可残高を正にして流し始めない。horizon後も永久閉塞とは断定しない。下流待ち観測なしの制約付きsinkでは、条件付き平均流出率と流出許可残高を使わず、物理FIFO、outlink流出容量、終端Node容量（有限のとき）、`DELTAN=1` およびその他の既定物理条件を適用する。下流Linkの `capacity_in_remain` は使わない。人工的な最大1台制限を設けない。BATCH Level 2の容量未確認の単純sinkは使わない。

**同じ仮想timestep内で行わないこと**

buyerとsellerが揃った後も時刻末処理は完了するが、次は同じ仮想timestep内では行わない。

- 容量を同じ仮想timestep内で再補充しない
- Vehicle前進または境界流出によってoutlink入口空間が回復しても、対象Node通過処理へ戻らない
- 完全な拘束順位列を同じ仮想timestep内で再走査しない
- 拘束順位外Vehicleを同じ仮想timestep内で再走査しない
- 新たに `incoming_vehicles` へ到着したVehicleを、その同じ仮想timestepに対象Node通過させない
- 次の仮想timestepへ進めない
- 実Worldを変更しない
- 正式順位台帳を変更しない
- baseline collectorを変更しない
- 他候補の局所状態を変更しない

**clearanceまたはNode容量による通過処理終了後**

clearance未充足またはNode容量不足により対象Node通過処理が終了した場合も、その仮想timestep全体を直ちに打ち切る意味にはしない。

**2026-09-24注記：** 前進と境界処理を続ける、という後半は維持する。ただし保存済みの拘束順位走査は、Node流量容量不足では走査を終えず、一時スキップとして後続を試す。走査終了はclearance未充足だけである。詳細は「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」を参照する。

その仮想timestep内で引き続き、inlink上の局所対象Vehicleの前進、新たな対象Node端到着Vehicleの登録、outlink上の局所対象Vehicleの前進、outlink終端境界処理、容量および状態の更新、診断の完成、resolvedまたはunresolvedの判定を行う。ただし、対象Node通過処理へは戻らない。

**BATCH Level 2との違い**

BATCH Level 2参照コードでは、triggerが対象Nodeを通過すると、そのoffsetのinlink前進、outlink前進、sink処理を行わずに早期終了する。TVT-MPでは、このBATCH固有の早期終了を採用しない。TVT-MPはbuyerとsellerの通過timestepだけでなく、候補別の診断結果と終了時状態を返す。仮想timestep途中の状態ではなく、同じ時刻の交通処理を完了した整合状態を結果へ残す。buyerとsellerの対象Node通過timestep自体は、対象Node通過時に既に確定しており、時刻末処理によって変更しない。

1台が通常の理由で通れなくても、拘束順位外の処理を禁止しない。拘束順位のVisitが将来全員通過し終わるまで、拘束順位外を待たせない。同じtimestepに複数台の対象Node通過を認める。拘束順位走査と拘束順位外走査は、同じ残容量と同じclearance履歴を共有する。clearance履歴は、実際に通過したときだけ更新する。Vehicleごとに仮想時刻を進めない。同じtimestepの次のVehicleは、先行Vehicleの移動後の最新状態を使用する。

clearanceの充足は、専用の新しい制御状態を作らず、次で毎timestep再判定する。

```text
current_virtual_timestep - last_order_control_entry_timestep
> order_control_clearance_timesteps
```

通常の通過不能には、未到着、物理先頭でないこと、保存進路の入口空間不足、`capacity_in_remain` 不足、`capacity_out_remain` 不足、`flow_capacity_remain` 不足、分類 `vehicle_id_among_acceptable_outlinks` で `acceptable_outlinks` が空であることを含める。これらはclearance未充足と区別する。

## 1台分の対象Node通過

局所専用の1台分の通過処理は、写しの上で次を更新する。

- 出たinlinkの `cum_departure`
- 入ったoutlinkの `cum_arrival`
- 出たinlinkの `traveltime_actual`
- inlinkの `capacity_out_remain`
- outlinkの `capacity_in_remain`
- 対象Nodeの `flow_capacity_remain`。`flow_capacity` が有限のときだけ消費する
- inlink物理先頭からの削除
- outlinkの `vehicles_enter_log`
- `Vehicle.link`
- `link_arrival_time`
- `x`
- `v`
- `lane`
- leader
- follower
- `move_remain`
- outlinkの `vehicles` への追加
- 新しいorder-control Visit
- `incoming_vehicles` からの削除
- `last_order_control_inlink`
- `last_order_control_entry_timestep`

Vehicleごとに仮想時刻を進めない。同じtimestepの次のVehicleは、この更新が終わった後の状態を見る。clearance履歴は、実際に通過したときだけ更新する。容量が負になる場合は例外とする。inlinkの物理先頭でないVehicleを移動しようとした場合は例外とする。実Worldへ書き戻さない。

BATCH Level 2の `_transfer_vehicle_reference()` は、累積台数、旅行時間、容量、車両列、位置、leader、Visit、incomingからの削除、clearance履歴を更新する。TVTはその関数を呼ばず、上記の項目をTVT側の関数に明示する。BATCHのservice unitは使わない。

## outlink終端境界

対象Nodeより下流のsignal、標準transfer、FCFS、BATCH、TVTは、写しの中で個別に再現しない。既存のoutlink別countを正本とする。平均率はobserverへ追加保存しない。局所計算側で算出する。途中通過Vehicleだけを観測対象とし、目的地到着Vehicleは観測countに含まれていない、という既存observer契約を再解釈しない。

`downstream_boundary_result is None` は、登録Visitが0の空baselineであり、`active = 0` ではない。候補を評価する経路で `None` なら、待ちなしや流出0と推測せず、不整合として停止する。

countがあるoutlinkは、次の3分岐である。

分岐Aは、`active_timestep_count > 0` かつ `transferred_vehicle_count > 0` である。条件付き平均流出率は、`transferred_vehicle_count / active_timestep_count` を局所側で計算する。候補別、outlink別の流出許可残高を0から始める。毎仮想timestep、その率を加算する。小数部分を繰り越す。未使用の整数部分も繰り越す。実際の流出台数は残高だけで決めない。残高の整数部分、終端で待っている台数、物理FIFO、`outlink.capacity_out_remain`、終端Nodeの `flow_capacity_remain`、`DELTAN=1`、および写しの上のその他の物理条件が、すべて許す範囲で流出させる。人工的なburst上限は設けない。使用した整数台数分だけ残高から減算する。大きな残高は、保存された物理容量ではない。baselineから推定した平均的な境界サービス機会を、候補固有の需要時刻へ再配分する近似である。

分岐Bは、`active_timestep_count > 0` かつ `transferred_vehicle_count == 0` である。baselineの共通horizon中に途中通過待ちが存在し、一台も流出しなかった場合である。同じlocal horizonの間は境界閉塞として扱い、終端から流出させない。horizonの後も永久に閉塞しているとは断定しない。この分岐で流出許可残高を正にして流し始めない。

分岐Cは、`active_timestep_count == 0` である。下流待ちが一度も観測されなかったことであり、下流混雑がないとは断定しない。条件付き平均率も流出許可残高も使わない。BATCH Level 2の単純sinkは使わない。終端に到達した物理FIFO先頭から、終端到達、終端の待ち台数、`outlink.capacity_out_remain`、終端Nodeの `flow_capacity_remain`、`DELTAN=1`、および写しの上で必要なその他の物理条件を適用する。成功時にはoutlinkの流出容量と終端Node容量を消費する。下流Linkの `capacity_in_remain` は使わない。人工的な最大1台制限は設けない。同一timestepに複数台を出せるかは、人工的上限ではなく、既存の容量、物理条件、FIFOで決まる。局所Worldから除くために `end_trip()` を使う。これは実Worldの本来の旅行終了ではない。

BATCH Level 2のsinkは、物理FIFO先頭と終端到達のあと、sink流出時の `outlink.capacity_out_remain` と終端Nodeの `flow_capacity_remain` を確認せず、消費せずに `end_trip()` する。TVTの分岐Cは、それらを確認し、成功時に消費する制約付きsinkである。この差を実装で消さない。

## 早期終了とhorizon

resolvedとする条件は、その候補の全buyer Visitと全seller Visitについて、局所の対象Node通過timestepが得られたことである。必要な通過timestepが揃った仮想timestepについて、対象Node通過走査の直後では終了せず、そのtimestepの時刻末処理（inlink前進、到着登録、outlink前進、outlink終端境界処理、容量と状態と診断の更新）を完了した後に仮想実行を終える。`configured_horizon_steps` に達する前でも、上記の完了契約を満たしたあとで終えてよい。

buyerとsellerは別の集合として識別する。buyerだから短縮する、sellerだから遅延する、とは決めない。時間差も効用も、このモジュールでは計算しない。非参加Visitや拘束順位外Vehicleが残っていても、そのことだけでは計算を継続しない。それらの残存だけではunresolvedにもしない。

`configured_horizon_steps` は、snapshotの時刻Tから進めてよい最大回数である。通過試行する最後の時刻は `T + configured_horizon_steps` であり、その時刻も試行に含める。この端点、計数、判定位置は、直前の「仮想timestep loop」の2026-09-23補修に従う。最終許容時刻の仮想timestepについても、時刻末処理を完了した後にresolvedまたはunresolvedを判定する。その最後の試行の時刻末処理の後も、必要なbuyerまたはsellerの対象Node通過時刻が揃わなければ、正常なunresolvedとする。理由を結果へ記録する。

経済性評価、成立候補の選択、実WorldへのTVT反映は、このモジュールの責務に含めない。

## 結果型と診断型

候補1件の結果型は `OrderControlTvtMpCandidateLocalVirtualCalculationResult` とする。

Node結果は、そのNodeの候補結果を読取専用の列で持つ型とする。名前は `OrderControlTvtNodeMpLocalVirtualCalculationResult` とする。`node_name` と候補結果の列を持つ。

全体結果は `OrderControlTvtMpLocalVirtualCalculationSetResult` とする。既存のFIFO検査結果と、Node結果の列を保持し、既存の結果連鎖へ接続する。Node順は `fork_result.target_node_names` に合わせ、候補順はFIFO検査結果の順に合わせる。

候補結果に最低限含めるものは次である。

- `concrete_buyer_candidate_set`
- `binding_rank_sequence`。評価に使った構築済みの読取専用列であり、評価後に再計算しない
- `resolved`
- unresolved理由の列
- `simulated_timestep_count`
- VisitKeyごとの対象Node仮想通過timestep。未通過は空文字にせず、通過していないことが分かる `None` または同等の明示的な不在で残す
- buyer、seller、またはその他
- 拘束順位内か、拘束順位外か
- 拘束順位列に含まれる場合の `binding_partition`
- 進路4分類の名前
- 実際に使用した進路名
- 進路の由来 `route_origin`
- Vehicle ID方式で選択したoutlink。選択していない場合は空文字ではなく明示的な不在
- timestepごとの対象Node通過Vehicle
- clearance待ちになったVehicleとtimestep
- 通常の理由で通過できなかったVehicle、timestep、理由
- outlink別の境界分岐名
- 条件付き平均流出率。分岐Bと分岐Cでは、率を使っていないことが分かること
- 流出許可残高の、timestepごとの値
- 分岐Cの制約付きsinkで除いたVehicle
- horizon末に、対象範囲へ残っているVehicleのLinkと位置

resolvedとなる候補結果には、その最終仮想timestepについて、次まで反映する。

- 対象Node通過Vehicle
- inlink上のVehicle前進後状態
- outlink上のVehicle前進後状態
- 新たな対象Node端到着Vehicle
- outlink終端境界処理
- 使用した下流境界状態（下流待ちあり・実流出あり、下流待ちあり・実流出なし、下流待ち観測なしの制約付きsinkのいずれかが分かること）
- 条件付き平均流出率を使用した場合の値
- 流出許可残高の最終値
- 制約付きsinkまたはその他の境界流出Vehicle
- outlinkおよびNodeの容量最終値
- 終了時の局所対象Vehicle状態
- その他の既定診断

`resolved` フラグおよび終了時点の情報は、時刻末処理完了後の候補結果へ設定する。buyerとsellerの対象Node通過timestepは、対象Node通過時に記録した値をそのまま使用する。時刻末処理によって書き換えない。

診断情報を一つの巨大な無名dictへ押し込まない。意味の分かるfrozen dataclass等の読取専用型を使う。時刻ごとの通過、clearance待ち、通常の通過不能、残高推移は、それぞれ項目が読める小さな読取専用の列にする。それ以上に、1フィールドごとに別モジュールへ分けることはしない。

これらの診断は、順位台帳、baseline collector、downstream boundary結果、実World、他候補へ書き込まない。

## 正常なunresolvedと重大不整合

正常なunresolved理由の名前は次とする。複数が該当するときは、優先順位で1件に潰さない。読取専用の理由列として全部保持する。

- `required_buyer_or_seller_did_not_pass_within_horizon`
- `downstream_boundary_remained_blocked_within_horizon`
- `downstream_boundary_had_waiting_vehicles_but_no_transfer`
- `clearance_or_capacity_blocked_through_horizon`
- `no_acceptable_outlink_for_route_undetermined_vehicle_within_horizon`
- `downstream_boundary_prevented_required_passage_information`

重大不整合は推測で修復しない。削除、片側採用、進路の再選択、容量の切り上げで継続しない。

- VisitKey重複
- 拘束順位内Visitの、局所通過に必要な進路の欠落
- 進路が対象Nodeのoutlinkでない
- Visitと局所Vehicle状態の不一致
- 同一Vehicleの同一timestep二重通過
- 容量の不正な負値
- inlink物理先頭でないVehicleを移動しようとする
- 必須状態の欠落
- 原子的確定の全件検証失敗
- 評価対象の候補があるにもかかわらず `downstream_boundary_result` が `None`
- `real_W.T` と `baseline_timestep_T` の不一致

例外の型は次で固定する。

- 呼出引数の形の誤り、および `real_W.T` と `baseline_timestep_T` の不一致は `ValueError`
- 原子的確定の入力不整合も `ValueError`。既存台帳が重複、未登録、再確定を `ValueError` としている契約に合わせる。代入前に検証し、失敗時は無変更である
- 実行中に検出した状態不整合、負の容量、二重通過、物理先頭でない移動、評価対象があるのに下流境界結果が `None` であることは `RuntimeError`
- 原子的確定で、代入前の内部整合検査が失敗した場合も `RuntimeError` とし、その場合も代入しない

## 専用テスト契約

テストはモジュールの責務ごとに分ける。性能測定は含めない。複数車線、`DELTAN` が1以外、signal対応を、成功条件にしない。

順位台帳では、順位と正式進路が一緒に保存されること、`export_state()` で `formal_route_next_link_name` が読めること、原子的確定の成功、1件失敗時に順位も進路も変化しないこと、既存 `confirm_visits_in_order()` の正式進路が `None` であることを固定する。新しい本番経路が旧APIを呼ばないことの確認は、台帳だけのテストでは完了扱いにしない。区分2の先行確定接続のテストで固定する。

区分2の先行確定接続では、既到着確定が先頭非参加確定より先であること、両方のVisitKey列の順序が現行結果と同じであること、各Visitの正式進路がcollectorの対象Node到着時 `route_next_link_name` であること、空列は台帳を変えないこと、進路が読めないVisitでは順位も進路も保存しないこと、この2関数が `confirm_visits_in_order()` を呼ばないことを固定する。

局所状態では、コピー後も対象外のNode、Link、Vehicleが残っていること、それらを更新しないこと、`exec_simulation()` とWorld全体の `Node.update()`、`Link.update()`、`Vehicle.update()` を呼ばないことを固定する。

horizonでは、`configured_horizon_steps` が2のとき試行時刻がT、T+1、T+2であること、Tで揃えば計数が0でそのtimestepの時刻末処理後にresolvedであること、T+2で揃えば計数が2で同様にresolvedであること、T+2の時刻末処理の後も不足なら計数が2でunresolvedであること、0のときはTだけを試すことを固定する。

拘束順位列では、4区分の連結順、区分3が `trade_order` の先頭 `last_buyer_rank` 件という取引後順であること、区分4がbaseline順であること、N+1位以降の意思決定窓内Visitが区分4に入ること、P-1対象外だが意思決定窓内のVisitが区分4に入り得ること、VisitKey重複と進路欠落で停止すること、`trade_order` 全体を完成列にしないことを固定する。1始まり順位と0始まりindexの対応も、`k_last_buyer` が2のときに区分4がindex 2から始まる例で固定する。

局所状態では、実Worldとの独立、候補間の独立、Node、Link、Vehicleの初期状態、残容量、outlink上の既存Vehicle、snapshot進路、clearance履歴、実World乱数の不変を固定する。

進路4分類では、4つの分類名、分類 `snapshot_route_already_decided` が拘束順位の外にも付くこと、分類 `baseline_route_inside_binding_sequence` だけが最終確定の保存対象になり得ること、分類 `baseline_route_outside_binding_sequence_temporary` を正式進路と呼ばず台帳へ保存しないこと、分類 `vehicle_id_among_acceptable_outlinks` が入れるoutlinkだけへVehicle ID剰余を適用し同じ入力なら同じoutlinkを選ぶこと、`acceptable_outlinks` が空ならその時刻は通過させないこと、保存進路が受入不能でも別進路へ変えないこと、`route_pref`、乱数、`route_next_link_choice()` を使わないことを固定する。

仮想timestepでは、通常理由の一時スキップ、clearance未充足での対象Node通過処理の終了（ただしそのtimestepの前進と境界処理は継続）、拘束順位走査のあとに順位外へ進むこと、同じinlinkの追い越し禁止、別inlinkの後続確認、`incoming_vehicles` の保持、同じ時刻の複数通過、残容量の共有、次の時刻での先頭からの再評価、最初の時刻はsnapshot残容量で2時刻目以降だけ通過前に補充し時刻の途中では補充しないこと、各仮想timestepの14手順の全体順序を固定する。

resolvedとなる仮想timestepの完了契約では、次を固定する。

- 対象Node通過処理で最後のbuyerまたはsellerが通過しても、その仮想timestepのinlink前進、到着登録、outlink前進、境界処理が実行される
- resolvedとなる時刻でも、対象Node通過に伴う容量消費が反映される
- 下流待ちあり・実流出ありの場合に、実流出した台数分の流出許可残高と流出容量が更新される
- 下流待ちあり・実流出なしの場合には流出しない
- 下流待ち観測なしの制約付きsinkでは、TVT固有の容量条件を確認し、成功時に容量を消費する
- 前進または境界流出で入口空間が回復しても、同じ仮想timestepの対象Node通過処理へ戻らない
- 新たに `incoming_vehicles` へ入ったVehicleを同じ仮想timestepに通過させない
- clearance未充足またはNode容量不足で通過走査が終了しても、その仮想timestepのVehicle前進と境界処理は実行される
- resolved結果の診断が、最終仮想timestep末まで記録される
- BATCH Level 2のtrigger早期終了と異なること
- buyerとsellerの対象Node通過timestep自体は、時刻末処理の有無で変わらないこと

物理通過では、本節に列挙した全状態の更新、容量消費、leaderとfollower、`move_remain`、新しいVisit、clearance履歴、二重通過の防止、負容量の防止を固定する。

下流境界では、分岐Aの平均率、小数残高、未使用整数残高、FIFOと容量の併用、分岐Bのhorizon内閉塞、分岐Cの制約付きsink、BATCHの単純sinkと同じ結果にならないこと、人工的な最大1台制限がないこと、`downstream_boundary_result is None` を分岐Cとして扱わないことを固定する。

終了条件では、buyerとsellerの対象Node通過時刻が揃った仮想timestepの時刻末処理完了後の早期resolved、無関係なVehicleが残っていてもresolvedであること、horizon上限での理由付きunresolved、複数理由を1件に潰さないこと、経済性評価を行わないことを固定する。

不変性では、実World、実Worldの乱数、順位台帳、collector、downstream boundary結果、他候補の状態が、候補評価の前後で変わらないことを固定する。

初期範囲では、単車線、`DELTAN=1`、trip-endを通過候補へ入れないこと、signalを見ないこと、T以後にinlink始端から新しい車を入れないことを前提として固定する。

## 実装区分

本節は実装順序を、番号付きの作業管理Stepとして確定しない。内容の分かる作業区分名だけを定める。新しいStep体系を使う場合は、その前に、Step名称、目的、対象範囲、全体構成を利用者へ提示し、合意を得てから使う。

各区分の着手前にも、その区分の名称、目的、対象範囲を利用者へ提示する。合意の前に、その区分のPython実装を開始しない。本節の記録、追記内容の独立確認、利用者によるMarkdownのcommitとpushが、最初の実装区分の提示より前である。

区分「正式進路付き順位台帳と原子的確定」の目的は、確定順位と対象Node向け正式進路を同じ台帳へ持ち、全件成功時だけ反映することである。変更対象は `uxsim/order_control_tvt_node_rank_state.py` と `tests_order_control_tvt_node_rank_state.py` である。候補形成、一般形順位、FIFO検査、collector、下流境界observer、既到着確定、先頭非参加確定は変更しない。完了条件は、保存、`export_state()`、成功時の一括反映、失敗時の無変更、既存APIの進路 `None` のテストが成功することである。この区分の完了だけでは、本番経路が `confirm_visits_in_order()` を呼ばないことの確認を終えたことにはしない。その確認は、次の先行確定接続の完了条件である。

区分「既到着Visitと先頭連続非参加Visitの原子的先行確定接続」の目的は、区分2を、順位だけの確定ではなく、対象Node到着時進路と一緒に候補形成前へ保存することである。変更対象は `uxsim/order_control_tvt_arrived_undetermined_confirmation.py`、`uxsim/order_control_tvt_leading_nonparticipating_confirmation.py`、および `tests_order_control_tvt_arrived_undetermined_confirmation.py` と `tests_order_control_tvt_leading_nonparticipating_confirmation.py` である。確定順は、既到着のあと先頭連続非参加であり、変えない。進路は `fork_result.collector` の `route_next_link_name` から取る。outlink名集合は、時点Tの実Worldの対象Nodeから呼出側が渡す。接続先は `confirm_visits_and_formal_target_node_routes_atomically` である。返すVisitKey列の型と順序は変えない。完了条件は、両方の先行確定が原子的確定APIを使うこと、正式進路が保存されること、空列と失敗時に台帳が変わらないこと、この本番接続が `confirm_visits_in_order()` を呼ばないことである。候補形成、一般形順位、FIFO検査は変更しない。

区分「完全な拘束順位列の構築」の目的は、既存結果と台帳から4区分の読取専用列を作ることである。変更対象は新規の構築モジュールとその専用テストである。Vehicleは動かさない。台帳の確定APIは呼ばない。区分2の正式進路が台帳に無い場合は補完せず停止する。完了条件は、4区分、N+1位以降、重複、進路欠落、1始まりと0始まりの対応のテストが成功することである。

区分「候補別局所状態の構築」の目的は、時点Tの実Worldから候補ごとの独立したWorld全体のコピーを作り、更新対象だけを固定することである。変更対象は新規の局所状態モジュールとその専用テストである。仮想通過の本計算はまだ含めない。対象外オブジェクトは削除しない。完了条件は、実World不変、候補間独立、対象外を更新しないこと、対象範囲の初期状態のテストが成功することである。

区分「1台分の対象Node通過」の目的は、写しの上で1台を対象Nodeから出す更新を明示することである。変更対象は局所仮想計算モジュールのうち、この通過関数と、その専用テストである。`Node.transfer()` とBATCHの通過関数は呼ばない。完了条件は、本節の更新項目と、通過できない車を動かさないテストが成功することである。

区分「拘束順位と拘束順位外の同一timestep統括」の目的は、完成列を先に走査し、余力があれば順位外を一時的FCFSで走査し、続けてinlink前進、到着登録、outlink前進、outlink終端境界処理、容量と状態と診断の更新まで1仮想timestepを完結させることである。変更対象は同じ局所仮想計算モジュールの統括関数と専用テストである。完了条件は、一時スキップ、clearance、incoming保持、複数通過、容量補充時点、通過走査終了後も前進と境界処理を継続すること、resolved仮想timestepでも時刻末処理を完了することのテストが成功することである。

区分「outlink終端境界3分岐」の目的は、既存countから分岐A、B、Cを局所側で計算することである。変更対象は同じモジュールの境界処理と専用テストである。完了条件は、残高繰越、閉塞、制約付きsink、空baselineの `None`、BATCH単純sinkとの差のテストが成功することである。

区分「公開入口、早期resolved、理由付きunresolved」の目的は、FIFOを通過した候補をまとめて評価し、buyerとsellerの通過時刻が揃った仮想timestepの時刻末処理完了後に終えることである。変更対象は公開入口と専用テストである。経済性評価は含めない。完了条件は、本節のhorizon端点と計数、resolved仮想timestepの完了契約、最終仮想timestep末の診断、最終許容時刻の時刻末処理後のunresolved、複数のunresolved理由、実World、台帳、collector、他候補の不変のテストが成功することである。

区分「最終結果後の正式確定接続」の目的は、採用、全候補却下、baseline情報不足、意思決定窓内Visitが0件の既定分岐に従い、今回確定するVisitだけを原子的確定APIで保存することである。採用時は、評価に使った構築済み列の区分3と区分4を再利用し、列を再計算しない。全候補却下とbaseline情報不足では、意思決定窓内Visit全体をbaseline順位と今回baselineの正式進路で保存する。意思決定窓内Visitが0件のときは確定対象がなく、窓全体を確定するとは扱わない。区分1と区分2は、この区分で再保存しない。変更対象は、この接続関数と専用テストである。経済性評価と実Worldへの反映は含めない。完了条件は、4つの分岐で保存されるVisitの範囲が既定どおりであり、評価中には台帳が変わらないテストが成功することである。

いずれの区分でも、最初から性能最適化をしない。正しい明示的な実装と専用テストを先に完了する。

## Python実装時の可読性方針

今後のPython実装で、次を守る。

- 正しく動くことを最優先とする
- 高度で巧妙なPythonテクニックより、初学者が処理を順に追える実装を選ぶ
- 複数の書き方がある場合は、短さや美しさより可読性を優先する
- 少し長くても、明示的な条件分岐にする
- 暗黙的な副作用を避ける
- 複雑な内包表記や多重処理で短縮しない
- 変数名、関数名、型名、フィールド名は、長くても意味が分かる名称にする
- Vehicle、Visit、Node、inlink、outlink、timestep、順位、進路、境界状態を、曖昧な短縮名で混同しない
- コメントとdocstringには、Python上の処理だけでなく交通上の意味を書く
- 登録時に保証した不変条件を、実行時に重複して検証しすぎない
- 実行中に変化し得る状態と、重大不整合だけを、必要最小限検証する
- 確定済み制度を、実装の都合で簡略化、再解釈、変更しない
- 性能最適化は、正しい基本実装とテストの後にする

## 次の再開地点

次の直接作業は、本節の制度契約やAPI名の再検討ではない。

次の直接作業は、本節の2026-09-23補修（独立レビュー3点およびresolvedとなる仮想timestepの完了契約）を含めて追記を独立して確認することである。その後、Markdownのcommitとpushは利用者がTerminalで行う。それが終わったあと、最初の実装区分「正式進路付き順位台帳と原子的確定」について、目的、変更するファイル、変更しない制度、完了条件を利用者へ提示する。この区分の完了では、本番経路が `confirm_visits_in_order()` を呼ばないことまでは確認しない。その確認は、次の実装区分「既到着Visitと先頭連続非参加Visitの原子的先行確定接続」の完了条件である。利用者の合意後に、提示した区分だけへ着手する。

直ちにPython実装へ進まない。全区分を一度に実装しない。事前合意のないStep体系は導入しない。

**2026-09-24注記：** 上記は、完全な実装前仕様を記録した時点の再開情報である。現在の作業指示としては読まない。実装済み範囲、未実装、未確定、および次の直接作業は、直後の「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」を参照する。

# TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録

**記録日：2026-09-24**

本節は、直前の「TVT-MP候補別局所仮想計算の完全な実装前仕様」（2026-09-22、2026-09-23補修）を削除せず、その後に保存された実装と、outlink終端境界へ追加した設計判断を記録する。

完全な実装前仕様に基づき、候補別局所仮想計算を複数モジュールへ分けて実装した。当初予定の単一モジュール `order_control_tvt_mp_candidate_local_virtual_calculation.py` は、まだ存在しない。仮想時計、拘束順位に従う対象Node通過、局所Vehicle前進は、責務別の別モジュールとして実装済みである。仮想timestep全体を統括する上位loopは、まだ未実装である。

本節のうち「実装済み」は、保存済みcommit `d23a385` までのコードに対応する。outlink終端の専用境界退出は、設計として確定したが、コードへは未実装である。未確定欄にある事項は、境界処理本体の実装を始める前に決める必要がある。

**2026-09-24追加確定：** 専用境界退出の累積index、旅行時間の式、`arrival_time`、`World.VEHICLES`、leader・follower解除順、退出理由名、境界状態型と結果型の名称、一台単位とoutlink単位の原子性は、「19. 専用outlink境界退出のフィールド単位確定契約」で確定した。`OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord` は `vehicle_name` を必須識別子とし、VisitKey fieldは設けない。境界処理本体は未実装である。第17節の専用退出項目は、当時の未確定一覧として残し、現在の未確定としては読まない。

## 1. 記録の位置付けと参照関係

最新の実装前仕様は、2026-09-22の完全な実装前仕様と、その2026-09-23補修である。本節は、その仕様を置き換えず、その後の実装結果を足す追加記録である。

2026-09-18の設計検討、2026-09-19の下流境界基本設計、2026-09-21の途中確定、2026-09-22の統合仕様は、歴史的記録として残す。それらを現在の作業指示として読まない。食い違う箇所では、本節の実装済み契約、または本節の未実装追加設計を最新参照先とする。

実装済みと、設計確定済みだが未実装と、未確定は、混ぜない。

- 実装済みは、`d23a385` までの保存済みコードで確認できる契約である。
- 設計確定済みだが未実装は、outlink終端境界の3状態と、下流待ちあり・実流出ありの専用境界退出である。フィールド単位の契約は「専用outlink境界退出のフィールド単位確定契約」にある。境界処理の本番モジュールは無い。
- 未確定は、第17節の「現在も未確定として残すもの」である。専用境界退出の添字と式は、そこへ残さない。推測で埋めない。

## 2. 保存済みコミットと実装区分

前提となる詳細設計の保存済みcommitは `c35f944` である。そのMarkdownが、両メモの最終更新である。その後、次の実装commitが保存されている。各commitの作成時に、その区分の専用テストと関連する回帰テストを確認した。今回の文書更新では、それらのテストを再実行していない。

棚卸し時に、現行の専用テストファイルにある `def test_` の数を数えた。これは成功件数ではない。

| commit | 実装区分 | 主な本番モジュール | 専用テスト | 後続接続上の意味 |
|---|---|---|---|---|
| `df3e27c` | 順位と正式進路の原子的確定 | `uxsim/order_control_tvt_node_rank_state.py` | `tests_order_control_tvt_node_rank_state.py`（棚卸し時の `def test_` は71） | 順位と正式進路を、全件成功のときだけ一緒に保存する |
| `a6285e3` | 既到着Visitと先頭連続非参加Visitの原子的先行確定 | `uxsim/order_control_tvt_arrived_undetermined_confirmation.py`、`uxsim/order_control_tvt_leading_nonparticipating_confirmation.py` | 両モジュールの専用テスト。権利保有選定のテストも、新しい引数に合わせて更新されている | 候補形成前に、区分2の順位と正式進路が台帳へ残る。結果型の形は変えていない |
| `2052674` | 完全な拘束順位列 | `uxsim/order_control_tvt_mp_local_binding_rank_sequence.py` | `tests_order_control_tvt_mp_local_binding_rank_sequence.py` | 仮想計算の前に、通過順と正式進路の完成列を作る。車は動かさない |
| `4916556` | 拘束順位列への `baseline_timestep_T` 追加 | 同上 | 同上（棚卸し時の `def test_` は46） | 局所状態が、コピー前に実Worldの時刻Tと照合できる |
| `03aed6a` | 候補別局所状態 | `uxsim/order_control_tvt_mp_candidate_local_state.py` | `tests_order_control_tvt_mp_candidate_local_state.py`（棚卸し時の `def test_` は14） | 候補ごとに独立したWorld全体のコピーと、更新してよい範囲を固定する |
| `07ca0d9` | 仮想時計、局所容量補充、累積台数延長 | `uxsim/order_control_tvt_mp_candidate_virtual_time.py` | `tests_order_control_tvt_mp_candidate_virtual_time.py`（棚卸し時の `def test_` は12） | offset 0はsnapshot残容量のまま。2時刻目以降だけ、対象範囲の容量を1段補充する |
| `dfdd0d6` | 一時スキップとclearance停止による拘束順位Node通過 | `uxsim/order_control_tvt_mp_candidate_binding_transfer.py` | `tests_order_control_tvt_mp_candidate_binding_transfer.py`（棚卸し時の `def test_` は15） | 完成列の順に、通れるVisitだけを正式進路へ出す |
| `d23a385` | 局所Vehicle前進と新着incoming登録 | `uxsim/order_control_tvt_mp_candidate_local_vehicle_advance.py` | `tests_order_control_tvt_mp_candidate_local_vehicle_advance.py`（棚卸し時の `def test_` は14） | 通過走査のあと、対象Link上の車を1回進め、今回新着した車だけをincomingへ足す |

`df3e27c` より前の下流境界観測は、`f475294`、`c72e38a`、`7f00520` で実装済みである。本節は、その結果の受け渡しだけを追加で書く。観測そのものの契約は再考しない。

## 3. 正式進路付き順位台帳と原子的確定

実装済みである。保存済みcommitは `df3e27c` である。

交通上の意味は、確定したVisitについて、交差点での順番と、その交差点から出る正式進路を、別々のタイミングで片方だけ残さないことである。

公開APIは `confirm_visits_and_formal_target_node_routes_atomically` である。入力は、確定順の VisitKey と `formal_route_next_link_name` の組、および対象Nodeのoutlink名集合である。全件を検証し、成功したときだけ台帳へ書く。1件でも不整合なら、順位も正式進路も変えない。入力の形の誤りは `ValueError` である。代入前の内部整合が崩れていた場合は `RuntimeError` であり、その場合も代入しない。0件のときは台帳を変えない。

読取は次を維持する。

- `confirmed_visit_keys_in_order()`
- `assigned_rank()`
- `formal_route_next_link_name()`

未保存の正式進路は `None` である。空文字ではない。古い `confirm_visits_in_order()` は、既存テストと互換のために残す。そのAPIで確定した正式進路は `None` である。新しい本番経路で、正式進路の保存が必要な確定に、この古いAPIは使わない。

台帳上の正式進路が `None` であることだけでは、そのVisitを一律に重大不整合とはしない。局所通過にその進路が必要になった時点で、snapshot進路の規則にも当たらなければ、そのとき停止する。

候補評価中は、この原子的確定APIを呼ばない。

## 4. 既到着Visitの原子的先行確定

実装済みである。保存済みcommitは `a6285e3` である。

交通上の意味は、baseline開始時点Tまでに、すでに対象Nodeへ到着しているVisitを、候補を作る前に、順位と正式進路付きで確定することである。到着順は並べ直さない。

公開関数は次である。

```text
confirm_already_arrived_undetermined_visits(
    alignment_fork_result,
    *,
    rank_states_by_node_name,
    real_W,
)
```

`real_W.T` が `fork_result.baseline_timestep_T` と違うときは `ValueError` である。台帳は変えない。過去の時刻へ戻して確定しない。

対象Nodeは `real_W.get_node(node_name)` で得る。`get_node` が callable でないときは `ValueError` である。UXsimが Node 欠落時に出す `'{node_name}' is not Node in this World` と一致する例外だけを、Node欠落の `ValueError` へ変換する。それ以外の例外は、変換せずそのまま再送出する。

有効なoutlink名は、`Node.outlinks.values()` の各Linkの名前である。確定するVisitの進路から、この集合を作らない。

正式進路は、`fork_result.collector.get_baseline_visit_snapshot` の `route_next_link_name` である。これは対象Nodeへ到着したときの進路であり、baseline終了時の進路ではない。snapshotが無い、または進路が空なら `ValueError` である。台帳は、そのNodeの原子的確定に入る前には変えない。原子的確定の失敗時も、台帳は変えない。

Nodeごとに、原子的確定を1回呼ぶ。`target_node_names` と alignment の Node 名が一致しないときは `RuntimeError` である。0件のNodeも、原子的APIを呼ぶ。その戻りは台帳不変であり、`newly_confirmed_count` は0である。

結果型 `OrderControlTvtArrivedUndeterminedConfirmationResult` と、Node結果の `confirmed_arrived_visit_keys` は、従来どおり VisitKey の列である。進路付きの組へは変えていない。進路は台帳側に保存する。

実World、baseline fork、alignment、collectorの中身は、この関数が書き換えない。

## 5. 先頭連続非参加Visitの原子的先行確定

実装済みである。保存済みcommitは `a6285e3` である。

交通上の意味は、既到着Visitを確定したあと、意思決定窓の先頭に連続する非参加Visitを、正式進路付きで先行確定することである。参加するVisitが現れたところで、この先行確定は止まる。

入力は、既到着確定の結果である。既到着確定の後に実行する。公開関数は `confirm_leading_nonparticipating_decision_window_visits` であり、キーワード引数に `rank_states_by_node_name`、`participates_by_visit_key`、`real_W` を取る。

`real_W.T` と `baseline_timestep_T` の一致、`get_node`、outlink名、collector進路、Nodeごとの原子的確定、例外時の台帳不変は、既到着確定と同じである。`configured_horizon_steps >= 6` という既存契約は維持する。

確定する列は `confirmed_leading_nonparticipating_visit_keys` である。順位は、既到着確定の末尾の次から連続する。正式進路は、collectorの対象Node到着時 `route_next_link_name` だけを使う。

権利保有Visitの選定は、これまでどおり `remaining_decision_window_visit_keys` を使う。結果型のフィールドは変えていない。実Worldは変えない。

## 6. 完全な拘束順位列

実装済みである。保存済みcommitは `2052674` と `4916556` である。

交通上の意味は、仮想計算を始める前に、その候補ではどのVisitを、どの順番で、どの正式進路へ通すかを、完成した一覧にすることである。この段階では車を動かさない。順位台帳もcollectorも書き換えない。

公開関数は次である。

```text
build_tvt_mp_local_binding_rank_sequence(
    fifo_inspection_set_result,
    candidate_fifo_inspection_result,
    rank_state,
)
```

候補は、FIFO検査結果の中にあるオブジェクトそのもので探す。一般形順位、既到着確定、先頭非参加確定、`fork_result` を、別引数として重ねて渡さない。

結果型は `OrderControlTvtMpLocalBindingRankSequence` である。要素型は `OrderControlTvtMpLocalBindingRankVisit` である。区分は `OrderControlTvtMpLocalBindingPartition`、進路由来は `OrderControlTvtMpLocalBindingRouteOrigin`、役割は `OrderControlTvtMpLocalBindingTradeRole` である。結果は frozen である。

4区分の値と意味は次である。連結順もこの順である。

1. `confirmed_before_this_baseline`。今回のbaselineより前から確定済みで、時点Tに対象範囲へ残っているVisit。
2. `preconfirmed_by_this_baseline`。今回のbaselineで、候補形成前に先行確定したVisit。
3. `trade_scope_of_this_candidate`。この候補の取引範囲のうち、最後のbuyerまで。
4. `outside_trade_scope_inside_k_fixed`。取引範囲の外だが、`k_fixed` の中にあるVisit。

完成列の `binding_rank` は1から連続する。`k_last_buyer` は既存の `last_buyer_rank` である。`k_decision_window` は `remaining_decision_window_visit_keys` の件数である。`k_fixed` は両者の最大である。`baseline_timestep_T` は `fork_result.baseline_timestep_T` を保存する。boolではない Python int であり、0以上である。

区分1は、既到着確定結果の `k_confirmed_before` までの台帳prefixを、台帳の確定順のまま見る。collectorにsnapshotがあるVisitだけを列へ入れる。すでに対象範囲を離れてcollectorに記録が無い過去確定Visitは、列へ入れない。正式進路が `None` であることだけを理由に、構築全体を止めない。snapshot時点で進路が決まっていれば、そのsnapshot進路を使う。そうでなければ、台帳の過去正式進路を使う。両方無ければ `RuntimeError` である。collectorの別の値や、現在の `Vehicle.route_next_link` では補わない。役割は `outside_trade_scope` である。

区分2は、既到着Visitのあとへ、先頭連続非参加Visitを続ける。使う進路は台帳の正式進路だけである。空なら `ValueError` であり、collectorの値では埋めない。役割は `outside_trade_scope` である。両 confirm result の確定範囲が、台帳の対応するprefixと一致することを確認する。一致しなければ停止する。

区分3は `trade_order[:last_buyer_rank]` である。`trade_scope` 自体のbaseline順ではない。1始まりの件数 `last_buyer_rank` を、0始まりスライスの終端として使う。各Visitは buyer、seller、非参加のいずれかちょうど1つである。0個または2個以上は `RuntimeError` である。`trade_scope` と、この prefix は、順序ではなくVisitの集合が一致することを確認する。

区分4は、`k_last_buyer` が `k_decision_window` 以上なら空である。小さいときは `remaining_decision_window_visit_keys[k_last_buyer:]` である。0始まりの開始位置は `k_last_buyer` そのものである。baseline順を維持する。上限Nで候補から落ちた窓内Visitも、P-1の対象外でも意思決定窓の中にあるVisitも、落とさない。役割は `outside_trade_scope` である。

`decision_window_visit_keys` は、先頭連続非参加と `remaining_decision_window_visit_keys` の連結と一致することを確認する。

区分3と区分4の進路は、snapshot時点で決まっていればsnapshot進路、そうでなければbaselineの対象Node到着時進路である。空なら `ValueError` である。

区分内でも区分間でも、同じVisitKeyが2回出れば `RuntimeError` である。黙って除外しない。

downstream boundaryの観測結果は、この型へ保持していない。

## 7. 候補別局所状態

実装済みである。保存済みcommitは `03aed6a` である。

交通上の意味は、実Worldを変えずに、候補ごとに別のWorld全体のコピーを作り、後続の局所処理が更新してよいNode、Link、Vehicleを明示することである。候補Aの更新が候補Bや実Worldへ届かないようにする。

公開関数は次である。

```text
build_tvt_mp_candidate_local_state(
    real_W,
    binding_rank_sequence,
)
```

コピーする前に、`real_W.T` と `binding_rank_sequence.baseline_timestep_T` を照合する。違うときは `ValueError` であり、コピーしない。過去の時刻へ戻さない。

コピーは `real_W.copy()` によるWorld全体である。対象外のNode、Link、Vehicleは削除しない。削除すると、進路、目的地、leaderの参照が壊れるためである。対象外がコピーの中に残ることと、対象外を走行させることは別である。局所更新の対象には入れない。

型は `OrderControlTvtMpCandidateLocalState`、Link上の車列は `OrderControlTvtMpLocalLinkVehicleState`、拘束Visitとコピー車の組は `OrderControlTvtMpBindingVisitLocalVehiclePair` である。構成を指すフィールドは frozen である。`local_world` の内部は、後続処理が変えてよい。

対象Nodeは、コピーWorldの `get_node()` で得る。inlinkとoutlinkは、そのNodeの登録順である。`Link.vehicles` は物理順である。`incoming_vehicles` は、コピー時点の既存順である。

`local_vehicles` の初回出現順は、次である。

1. inlinkの登録順。各Linkの中は物理順。
2. outlinkの登録順。各Linkの中は物理順。
3. まだ入っていない incoming。

同じコピーVehicleは、`local_vehicles` へ1回だけ入れる。inlink、outlink、incomingの所属は、別の列で持つ。各inlinkを1台へ縮約しない。incomingに同じinlinkの車が複数いても、そのまま残す。

実Vehicle名とコピーVehicleの対応は、双方向のmappingで持つ。コピー後の名前は、実Worldの名前と同じである。

拘束順位列の各Visitは、コピーWorldの同名Vehicleと組む。現在Visitの `visit_id` が VisitKey と一致し、そのVisitの node がコピー側の対象Nodeであることを確認する。同じ車の再訪は、`visit_id` で区別する。

`link`、`route_next_link`、leader、follower が、実Worldのオブジェクトを指していれば `RuntimeError` である。コピー側の登録オブジェクトであることを確認する。

この構築は、Vehicleを動かさない。実Worldの乱数状態も変えない。候補ごとに別のコピーを作るので、World、Node、Link、Vehicle、mappingを候補間で共有しない。

## 8. 候補別仮想時計、容量補充、累積台数延長

実装済みである。保存済みcommitは `07ca0d9` である。

交通上の意味は、候補のコピーWorldの時計を、baseline開始時刻Tから1段ずつ進めることである。最初の時刻は、snapshotに残っていた容量のまま使う。2時刻目以降だけ、対象のLinkと対象Nodeへ、通常のUXsimと同じ補充を1回入れる。

型は `OrderControlTvtMpCandidateVirtualTimeState` である。公開関数は次である。

```text
initialize_tvt_mp_candidate_virtual_time_state(
    candidate_local_state,
)

advance_tvt_mp_candidate_virtual_time_one_step(
    virtual_time_state,
)
```

`current_offset` が0のとき、`current_virtual_timestep` は `baseline_timestep_T` である。一般に `current_virtual_timestep = baseline_timestep_T + current_offset` である。`simulated_timestep_count` は、時刻Tから時計を進めた回数である。offset 0では0である。offsetが h のときは h である。snapshotの時刻そのものは数えない。これらの値は property であり、外から代入して時計を進められない。進めるのは、1段前進の関数だけである。

初期化では、容量を補充しない。`cum_arrival` と `cum_departure` だけ、indexがTまで届く最短の長さへ延長する。延長は、直前の値を後ろへコピーする。空のlistは0から始める。過去の要素は書き換えない。`traveltime_actual` と `vehicles_enter_log` は延長しない。

1段前進は、必ず1timestepだけ進む。次の残容量と、次の累積listを先に計算する。その計算が通ったあとで、コピーWorldの `T`、対象Linkの残容量、対象Nodeの `flow_capacity_remain`、累積list、offset、`simulated_timestep_count` を書く。

Linkの補充式は `Link.in_out_flow_constraint` と同じである。`capacity_in is None` のときは、流入残りと流出残りを、どちらも UXsim の無制限表現 `10e10` にする。有限なときは、残りが `DELTAN * number_of_lanes` 未満のときだけ、`capacity * DELTAT` を足す。閾値以上なら、その側は足さない。

Nodeの補充式は `Node.flow_capacity_update` と同じである。`flow_capacity is None` のときは残りを `10e10` にする。有限なときは、残りが `DELTAN * number_of_lanes` 未満のときだけ、`flow_capacity * DELTAT` を足す。

補充と累積延長の対象は、対象Nodeと、対象inlinkおよび対象outlinkだけである。同じLinkオブジェクトは1回だけ補充する。自己ループのように、inlinkとoutlinkの両方に同じLinkが出ても、二重に補充しない。対象外のLinkとNodeは変えない。Vehicle、`incoming_vehicles`、clearance履歴は、この段階では変えない。

## 9. 拘束順位に従う対象Node通過

実装済みである。保存済みcommitは `dfdd0d6` である。

交通上の意味は、各仮想時刻で、完成した拘束順位列を先頭から見て、今通せるVisitだけを、保存済みの正式進路へ出すことである。通常の理由で通れないVisitは、列から消さず、その場に残して後続を試す。その仮想時刻の通過走査を途中で終えるのは、clearanceが足りないときだけである。

公開関数は次である。

```text
initialize_tvt_mp_candidate_binding_transfer_state(
    virtual_time_state,
)

scan_and_transfer_tvt_mp_binding_visits_at_current_timestep(
    binding_transfer_state,
)
```

型は `OrderControlTvtMpCandidateBindingTransferState`、1回の走査結果は `OrderControlTvtMpBindingTransferScanResult`、1件の一時スキップは `OrderControlTvtMpBindingVisitTemporarySkip` である。停止理由と一時スキップ理由は、それぞれ Enum である。

一時スキップの理由は、次の6つだけである。

- 未到着。対象Nodeの `incoming_vehicles` にまだいない。
- inlinkの物理先頭でない。
- inlinkの流出容量が `DELTAN` 未満。
- 正式進路のoutlinkの流入容量が `DELTAN` 未満。
- Node流量容量不足。対象Nodeの流量残りが `DELTAN` 未満。
- 正式進路のoutlinkの入口に、車が入る空間が無い。

一時スキップしたVisitは、拘束順位列から削除しない。その走査の通過済み列へも入れない。同じ走査の中で、後ろのVisitを試す。次の仮想時刻では、通過済みを除き、列の先頭からもう一度評価する。

走査を途中で返すのは、clearance未充足だけである。停止理由は `clearance_not_satisfied` である。止まったVisitより後ろは、その走査では見ない。clearanceの判定は、前回通ったinlinkと違うinlinkのとき、`current_virtual_timestep - last_order_control_entry_timestep > order_control_clearance_timesteps` である。記録が片方だけ入っているときは `RuntimeError` である。同じinlinkの連続通過は、clearanceでは止めない。

列の最後まで見たときの停止理由は `binding_sequence_completed` である。この理由は、Nodeの流量容量が残っているという意味ではない。Node流量が `DELTAN` 未満でも、走査は終えず、流量不足の一時スキップとして後続を試す。容量はNodeで共有するので、有限容量が `DELTAN` 未満の間は、後続も同じ理由で残ることがある。

`incoming_vehicles` には、同じinlinkから来た既到着Vehicleが複数いてよい。先頭が通過したあと、新しい物理先頭が条件を満たせば、同じ仮想時刻の同じ走査で、その次の車も通過できる。同じinlinkの、まだ物理先頭でない車は、追い越さない。

通過に使うoutlinkは、binding Visitの `route_next_link_name` である。`route_next_link_choice()` は呼ばない。その名前が対象Nodeのoutlinkに無ければ、交通を変える前に `ValueError` である。コピーVehicleの `route_next_link` が別のoutlinkを指していれば、交通を変える前に `RuntimeError` である。`route_next_link` が `None` のときは、この不一致検査では止めない。使う進路は、あくまで binding Visit の正式進路名である。

1台の移動は、`Node.transfer` の内側と、BATCH Level 2の1台分参照処理が更新する項目に合わせる。`Node.transfer()` 自体は呼ばない。`end_trip()` も呼ばない。`incoming_vehicles` を全消去しない。通過した1台だけを incoming から除く。`begin_order_control_visit_on_link_entry()` を呼び、outlink進入時の新しい order-control Visit を始める。

成功時に消費する量は `DELTAN` である。対象Nodeの `flow_capacity` が有限なときだけ、`flow_capacity_remain` から `DELTAN` を引く。無制限の `10e10` は、有限容量として減算しない。

書き換える主な状態は次である。

- 出たinlinkの `cum_departure` の末尾。仮想時計が累積を現在時刻まで延長したあとでは、この末尾が現在の仮想時刻の枠である。
- 入ったoutlinkの `cum_arrival` の末尾。
- 出たinlinkの `traveltime_actual`。
- inlinkの `capacity_out_remain` と、outlinkの `capacity_in_remain`。
- 有限な対象Nodeの `flow_capacity_remain`。
- inlink物理先頭からの削除と、outlinkの `vehicles` への追加。
- outlinkの `vehicles_enter_log`。
- `Vehicle.link`、`link_arrival_time`、`x`、`v`、`lane`、leader、follower、`move_remain`。
- 新しい order-control Visit。
- incomingからの、その1台の削除。
- `last_order_control_inlink` と `last_order_control_entry_timestep`。

容量が負になる移動は、それらの書き込みの前に `RuntimeError` とする。物理先頭でない車を動かそうとした場合も `RuntimeError` である。

通過済みのVisitKeyだけを、状態側に残す。公開の `transferred_binding_visit_keys` は tuple であり、外から要素を足せない。通過済みは、次の走査で再通過しない。

この走査関数自体は、同じ仮想時刻の2回目を拒否しない。2回目では、通過済みは飛ばす。一時スキップしたVisitは、もう一度試す。将来の統括loopは、1仮想時刻につき、この走査を原則1回だけ呼ぶ。これは、まだ未実装の統括loopが守る契約である。

拘束順位外Vehicleの一時的FCFS走査は、未実装である。このモジュールは扱わない。

## 10. 局所Vehicle前進と新着incoming登録

実装済みである。保存済みcommitは `d23a385` である。

交通上の意味は、その仮想時刻の対象Node通過が終わったあと、対象inlinkと対象outlinkの上にいる車を1回だけ前へ進め、今回はじめて対象Nodeの端へ着いた車だけを `incoming_vehicles` の後ろへ足すことである。今回新着した車は、同じ仮想時刻には交差点を通さない。次の仮想時刻の通過走査で、はじめて評価する。

通常のUXsimでは、LinkとNodeの更新のあと、走っている車の追従位置を先に計算し、livingの登録順で位置を反映し、Link終端へ着いた車を incoming へ足す。この段階は、その順の交通上の意味に合わせる。`Vehicle.update()`、`Vehicle.carfollow()`、`route_next_link_choice()`、`end_trip()` は呼ばない。追従の式と、到着記録の公式メソッドだけを使う。

公開関数は次である。

```text
initialize_tvt_mp_candidate_local_vehicle_advance_state(
    binding_transfer_state,
)

advance_tvt_mp_candidate_local_vehicles_and_register_new_arrivals(
    advance_state,
    binding_transfer_scan_result,
)
```

型は `OrderControlTvtMpCandidateLocalVehicleAdvanceState` と `OrderControlTvtMpLocalVehicleAdvanceResult` である。

前進の入力である走査結果は、同じNode、同じ仮想時刻の、拘束順位通過がすでに戻った証明である。走査結果の転送キーが空でないときは、状態側の通過済み列の末尾と一致しなければならない。空のときは、Pythonの `[-0:]` が列全体になるため、別に判定する。時刻かNodeが違えば `RuntimeError` であり、車は動かさない。この前進関数は、拘束順位走査を再呼び出ししない。時計も容量も進めない。

動かす車は、今、対象inlinkまたは対象outlinkの `Link.vehicles` にいる車である。処理順は `VEHICLES_LIVING` の登録順である。`state` は `"run"`、`mode` は `"single_trip"`、`VEHICLES_RUNNING` に登録されていること。taxiは扱わず、`RuntimeError` である。leaderまたはfollowerが別Linkにいる、または相互参照が切れているときは、位置を書く前に `RuntimeError` である。

位置は、全車の次位置を、まだ誰も動いていない `leader.x` で先に計算する。式は `Vehicle.carfollow` と同じである。そのあとで、`v`、`x_old`、`x_next`、`move_remain`、`x` を書く。自由流がLink長を超える分は `move_remain` に残し、`x` はLink終端へ揃える。超えないときは、既存の `move_remain` を維持する。inlinkとoutlinkの両方を、この1回で進める。

既存incomingは、前進を始める前から `incoming_vehicles` にいる車である。同じinlinkに複数いてよい。その順を維持する。各inlinkを1台へ縮約しない。重複削除しない。同じ車が incoming に2回入っていれば、重大不整合として `RuntimeError` である。既存の車を再追加しない。`arrival_time` と `arrival_tiebreaker` を記録し直さない。

新着は、その前進前のincomingに無く、今回の `x_next` がinlink長と等しく、Linkの終端Nodeが対象Nodeであり、そのNodeが目的地ではなく、行き止まりの trip abort でもない車である。目的地がそのNodeの車は、incomingへ足さず、この段階では `end_trip()` もしない。追加順は `VEHICLES_LIVING` 順であり、既存列の後ろへ足す。記録は、コピーVehicleの `record_order_control_node_arrival()` である。対象Nodeへの初回到着の tiebreaker は、コピーWorldの `rng` から1回引く。再訪は、コピーWorldの `order_control_rng` から1回引く。レガシーの初回到着辞書は、初回だけ更新する。実Worldの乱数は使わない。

新着として足す車の現在Visitは、dictであり、nodeはコピー側の対象Nodeであり、`visit_id` は bool ではない Python int であり、`arrival_time` と `arrival_tiebreaker` が両方 `None` であること。片方または両方がすでに入っていれば、書き込み前に `RuntimeError` である。既存incomingの車には、この未記録条件を要求しない。

`record_order_control_node_arrival()` は、呼んだ瞬間に Visit、初回到着辞書、コピーWorldの乱数を書く。そのため、位置を書く前に次を保存する。

- 対象車の位置、速度、`move_remain`。
- incoming列。
- 新着Visitの到着2項目。
- 初回到着の2辞書。
- `rng` と `order_control_rng` の状態。
- コピーWorldに baseline collector があるときは、既存記録の `baseline_arrival_timestep`、`arrival_tiebreaker`、`route_next_link_name`。新しい記録は作らない。正式な候補コピーでは、この collector は `None` である。

2台目以降の記録が失敗しても、1台目を含む、その呼出で書いた更新をすべて戻す。戻したあと、元の例外を再送出する。戻すこと自体が失敗したときは、元の例外を原因に持つ `RuntimeError` とする。`completed_virtual_timesteps` は、全件が成功したあとだけ増やす。同じ仮想時刻の2回目は `RuntimeError` であり、車、Link、incoming、乱数、完了記録を変えない。

outlinkの終端へ着いた車は、終端へ揃えたまま、そのoutlinkの上に残す。下流Nodeの `incoming_vehicles` へ足さない。`end_trip()` しない。後続のoutlink終端境界処理へ渡す状態である。境界処理そのものは、このモジュールに無い。

同じ仮想時刻の拘束順位通過へは戻らない。この関数が走査を再呼び出ししないことで保たれている。統括loopは未実装である。

## 11. downstream boundary観測結果の受渡し

下流境界の観測自体は、候補別局所計算より前に実装済みである。本節で足すのは、その結果を後続の境界処理へどう渡すかである。境界処理本体は未実装である。

既存の型は次である。どれも frozen である。

- `OrderControlBaselineDownstreamBoundaryResult`。`node_results` を持つ。
- `OrderControlBaselineDownstreamBoundaryNodeResult`。`node_name` と `outlink_results` を持つ。
- `OrderControlBaselineDownstreamBoundaryOutlinkResult`。`outlink_name`、`terminal_node_name`、`active_timestep_count`、`transferred_vehicle_count` を持つ。

平均率は、この結果へ保存しない。公開経路は `OrderControlBaselineForkResult.downstream_boundary_result` だけである。型は、上記の全体結果または `None` である。

`downstream_boundary_result is None` は、downstream boundary結果なしである。snapshot固定Visitが0件で、baseline forwardも観測もしていない空baselineである。count 0 ではない。観測未実施である。

`active_timestep_count == 0` は、horizonを実行したあとの観測済み0である。途中通過の終端待ちが一度も無かったことを意味する。結果なしとは別である。

`active_timestep_count > 0` は、下流終端で途中通過の待ちが観測されたことである。`transferred_vehicle_count` が0より大きいか0かで、実流出の有無が分かれる。

Node順は `fork_result.target_node_names` と同じ登録順である。各Nodeのoutlink順は、その対象Nodeの `outlinks` の登録順である。名前または順序が、局所状態のoutlinkと一致しなければ停止する。欠落を0で補わない。

現行の後続実装は、この結果を保持していない。拘束順位列、候補別局所状態、仮想時計、対象Node通過、局所前進のどれにもフィールドが無い。実Worldの observer は `None` のままなので、コピーWorldからも読めない。

採用する渡し方は、新しいoutlink境界状態を初期化するとき、対象Nodeの既存 `OrderControlBaselineDownstreamBoundaryNodeResult` を、明示的な引数として渡すことである。新しい正規化profile型は作らない。`OrderControlBaselineForkResult` 全体を境界処理へ渡さない。拘束順位列や候補別局所状態へ、同じcountを重複して持たせない。共有する観測結果は読取専用であり、候補の計算が書き換えない。候補ごとに変わる流出許可残高は、境界状態の側で、outlink別に0から始める。

候補を評価する経路で downstream boundary結果なしが現れた場合は `RuntimeError` である。待ちなしにも、観測済み0にも、正常なunresolvedにもしない。

## 12. outlink終端境界の意味別3状態

この小節は、設計として確定している。境界処理の本番モジュールは、まだ無い。未実装である。

歴史的本文の「分岐A・B・C」は残す。本節の主表記は、次の意味名である。括弧内は旧称であり、新しい正式名ではない。

下流待ちあり・実流出あり（歴史的本文の分岐A）の条件は、`active_timestep_count > 0` かつ `transferred_vehicle_count > 0` である。率は `transferred_vehicle_count / active_timestep_count` であり、局所側で計算する。観測結果へは保存しない。流出許可残高は、候補別かつoutlink別である。初期値は0である。各仮想時刻に、その率を1回だけ足す。小数と、使わなかった整数は、次の仮想時刻へ繰り越す。正本上の上限は無い。実際に流出した台数の整数だけを、残高から引く。

流出できるのは、outlink終端へ着いていること、物理先頭からであること、残高の整数が許すこと、`outlink.capacity_out_remain` が `DELTAN` 以上であること、終端Nodeの流量容量が有限ならその残りが `DELTAN` 以上であること、が同時に成り立つときである。下流Linkの `capacity_in_remain` は使わない。同じ仮想時刻に複数台出せるかは、残高、容量、物理順で決まる。最大1台という人工的な上限は置かない。先頭が通常の待ちで出られないときは、そのoutlinkのその時刻の境界処理を止める。後ろの車を先に出さない。

下流待ちあり・実流出なし（歴史的本文の分岐B）の条件は、`active_timestep_count > 0` かつ `transferred_vehicle_count == 0` である。同じlocal horizonの間は、終端から出さない。率は使わない。残高を正にして流し始めない。車はoutlinkの上に残す。`capacity_out_remain` も、終端Nodeの容量も消費しない。horizonのあとまで永久に閉塞している、とは断定しない。

下流待ち観測なしの制約付きsink（歴史的本文の分岐C）の条件は、`active_timestep_count == 0` である。これは観測済みの0であり、downstream boundary結果なしではない。率も残高も使わない。終端到着、物理順、`outlink.capacity_out_remain`、有限な終端Nodeの `flow_capacity_remain`、`DELTAN` を確認する。下流Linkの `capacity_in_remain` は使わない。成功したとき、outlinkの流出容量と、有限な終端Node容量を消費する。その確認と消費のあと、コピーWorldの上で `end_trip()` を使い、局所範囲から除く。これは実Worldの旅行終了ではない。最大1台の人工的な上限は無い。BATCH Level 2の単純sinkは、容量を確認せず `end_trip()` する。その単純sinkは使わない。

downstream boundary結果なしは、上の3状態に含めない。空baselineにより観測していない状態である。count 0へ変換しない。候補評価の経路で現れたら `RuntimeError` である。正常なunresolvedではない。

## 13. 下流待ちあり・実流出ありの専用境界退出

これは、2026-09-24に採用した確定判断である。コードへはまだ実装していない。完全な実装前仕様は、この状態を「流出させる」と書き、`end_trip()` を書くのは下流待ち観測なしの制約付きsinkだけである。本節は、その未記載だった退出後の基本状態を追加する。未確定の式は、確定したことにはしない。

交通上の意味は、実旅行の完了ではない。その候補の局所計算の範囲から、車を出すことである。

成功したとき採用する基本契約は、次である。

- `end_trip()` を使わない。
- outlinkの `vehicles` から、物理先頭の車を除く。
- leaderとfollowerを解除する。解除のフィールド順は、未確定欄に残す。
- `outlink.capacity_out_remain` から `DELTAN` を引く。
- 終端Nodeの `flow_capacity` が有限なときだけ、`flow_capacity_remain` から `DELTAN` を引く。無制限の `10e10` は減算しない。
- `cum_departure` を更新する。どのindexへ、どの量を足すかは未確定である。
- `traveltime_actual` を更新する。更新式は未確定である。
- `VEHICLES_RUNNING` から除く。
- `VEHICLES_LIVING` から除く。
- `vehicle.link` を `None` にする。
- `vehicle.state` を `"end"` にする。
- `arrival_time` を、実旅行の完了時刻としては記録しない。属性を無変更にするかは未確定である。
- `record_log()` を、旅行終了としては呼ばない。
- 専用の境界退出理由と、退出したVehicleの列へ記録する。理由と結果型の正式な名前は未確定である。
- 下流待ち観測なしの制約付きsinkが使う `end_trip()` と、記録の上で区別する。
- 実Worldと、別候補のコピーは変えない。
- 下流Nodeの `incoming_vehicles` へ、通常の到着として登録しない。
- 退出のあと、同じ仮想時刻の拘束順位通過へ戻らない。入口空間が戻っても、戻らない。

次は未確定である。これらを決める前に、境界処理本体は実装しない。

- `cum_departure` の正確なindex。
- `traveltime_actual` の正確な更新式。
- `vehicle.arrival_time` を、まったく変更しないか。
- `World.VEHICLES` の辞書へ残すか。
- leaderとfollowerを外すときの、フィールド単位の順序。
- 専用の退出理由のEnum、または結果型の正式名称。

`end_trip()` が行う `cum_departure[-1]` への加算、`(T+1)` を使う旅行時間、`arrival_time = W.T`、`record_log()` を、この専用退出へ無条件に流用しない。

> 2026-09-24追加確定: 上記の未確定一覧は、本節を書いた時点の記録である。削除しない。`cum_departure` のindex、`traveltime_actual` の式、`arrival_time` を変更しないこと、`World.VEHICLES` へ残すこと、leader・followerの解除順、退出理由名、境界状態型と結果型の名称、一台単位とoutlink単位の原子性は、後続調査により確定した。最新契約は「19. 専用outlink境界退出のフィールド単位確定契約」を参照する。`cum_departure[-1]` と `(T + 1) * DELTAT` は、その最新契約で採用する。`arrival_time = W.T` と、旅行終了としての `record_log()` は、引き続き専用境界退出では使わない。

## 14. 実装済み処理順

現在、コードとしてつながっている局所処理の順は、次である。統括loopは無いので、呼出側がこの順を守る。

1. 候補別局所状態を構築する。
2. offset 0の仮想時計を初期化する。容量は補充しない。累積だけ、時刻Tの枠まで延長する。
3. その仮想時刻で、拘束順位の対象Node通過を1回走査する。
4. 通過のあと、局所Vehicleを1回前進させる。
5. 対象inlinkの終端へ今回着いた車を、incomingの後ろへ登録する。
6. outlinkの終端へ着いた車は、outlinkの上に残す。

未実装の続きは、次である。

7. outlink終端境界処理。
8. 拘束順位外Vehicleの一時的FCFS走査。
9. 診断の完成。
10. resolved判定。
11. その仮想時刻の時刻末処理の完了。
12. 次の仮想時刻へ進むか、horizonで終えるか。

守る順は、次である。

- 1仮想時刻の拘束順位走査は、原則1回である。走査関数自体には、同じ時刻の再呼出を拒むガードが無い。
- 局所前進には、同じ仮想時刻の2回目を拒むガードがある。
- 新着をincomingへ入れたあと、同じ仮想時刻の拘束順位走査へ戻らない。
- 将来、境界流出でoutlinkの入口空間が戻っても、同じ仮想時刻の拘束順位走査へ戻らない。
- 次の仮想時刻では、一時スキップしたVisitを含め、拘束順位列を先頭から再評価する。通過済みは再通過しない。
- 2時刻目以降の容量補充は、その時刻の通過走査より前に、1段前進を1回だけ行う。走査の途中や、前進のあとでは補充しない。

## 15. 古い記述との齟齬と最新参照

古い本文は削除しない。次の読み替えだけを、本節を最新参照先として固定する。

- 「Python実装は未着手」「次の直接作業は正式進路付き順位台帳」は、完全な実装前仕様を書いた時点の再開情報である。現在の作業指示ではない。実装済み範囲は本節の第2節から第10節である。
- Node流量不足で対象Node通過走査を終える、と読める文は、実装前仕様の仮想timestep手順と、clearanceまたはNode容量の見出しにある。保存済み実装では、Node流量不足は一時スキップである。走査を途中で終えるのはclearance未充足だけである。
- 仮想計算を1ファイルにまとめ、それより細かく分けない、という文は実装前の予定である。保存済み実装は、時計、通過、前進を別ファイルにした。統括ファイルは未作成である。
- 2026-09-21の「境界処理を通過より前に置く」処理順は、当時の記録である。最新の順は、完全な実装前仕様の、前進と新着登録のあとに同じ仮想時刻で境界処理を行う順である。境界処理本体は未実装である。
- 「分岐A・B・C」は歴史的表記として残す。2026-09-24以降の最新記録では、意味名を主表記にする。

該当する歴史的箇所の末尾へ、本節への短い参照を付けた。同じ文を、ファイル中のすべての再開情報へは繰り返していない。

## 16. 未実装事項

次は、コードに無い。

- outlink終端境界処理の本体。
- 拘束順位外Vehicleの一時的FCFS走査。
- 仮想timestep全体の統括loop。
- buyerとsellerの対象Node通過時刻の収集。
- resolved判定。
- resolvedとなる仮想時刻の、時刻末処理の完了。
- horizon終了。
- unresolvedの理由と診断。
- 候補別局所計算の結果型の完成。仕様上の名前はある。クラスは無い。
- 経済性評価。
- 候補の採用と却下。
- 最終順位と正式進路の確定接続。
- 上位driverへの統合。

仮想時計、拘束順位の対象Node通過、局所Vehicle前進と新着incoming登録は、未実装に含めない。これらは `d23a385` まで実装済みである。

## 17. 未確定事項

次は、設計確定済みの一覧に入れない。実装を始める前に決める。

- 拘束順位外Vehicleの一時的FCFSの、具体的な実装契約。進路4分類の制度は、2026-09-22の統合仕様にある。コードは無い。
- buyerとsellerの通過時刻を持つ、正式な結果型とフィールド。
- resolved判定を、未実装の統括loopのどこで行うか。完全な実装前仕様は、時刻末処理の完了後とする。統括が無いので、コード上の位置はまだ無い。
- unresolved理由を複数保持する実装。
- 最終確定接続が、評価に使った拘束順位列をどう受け取るか。
- 専用境界退出の `cum_departure` のindex。
- 専用境界退出の `traveltime_actual` の更新式。
- 専用境界退出のとき、`vehicle.arrival_time` を変更するか。
- 専用境界退出のあと、`World.VEHICLES` へ残すか。
- leaderとfollowerを外す、フィールド単位の順序。
- 専用境界退出の理由名と、退出結果型の名称。

> 2026-09-24追加確定: 上記6項目は後続調査により確定した。最新契約は「19. 専用outlink境界退出のフィールド単位確定契約」を参照する。現在の未確定一覧として読まない。

現在も未確定として残すものは、次だけである。

- 拘束順位外Vehicleの一時的FCFSの、具体的な実装契約。進路4分類の制度は、2026-09-22の統合仕様にある。コードは無い。
- buyerとsellerの通過時刻を持つ、正式な結果型とフィールド。
- resolved判定を、未実装の統括loopのどこで行うか。完全な実装前仕様は、時刻末処理の完了後とする。統括が無いので、コード上の位置はまだ無い。
- unresolved理由を複数保持する実装。
- 最終確定接続が、評価に使った拘束順位列をどう受け取るか。
- Node流量不足のあと、未実装の拘束順位外FCFSへ進むかを、統括loopがどう判定するか。走査完了は、流量が残っているという意味ではない。
- 境界処理モジュール内部の共通helperの関数分割。第19節は共通helper候補の責務だけを書き、関数名は実装時命名とする。

## 18. 次の実装再開地点

次の直接作業は、outlink終端境界処理である。ただし、その本体を書く前に、第17節のうち専用境界退出の未確定細部を確定する。式が決まる前に、境界処理の本番コードは書かない。

> 2026-09-24追加確定: 専用境界退出の未確定細部を文章で決める作業は完了した。現在の次の直接作業は、outlink終端境界処理本体を新規モジュールと専用テストとして実装することである。フィールド契約は「19. 専用outlink境界退出のフィールド単位確定契約」である。下記「最初に文章で決める事項」は、当時の再開条件であり、現在の作業指示としては読まない。

予定する入力は、次の3つである。

- local vehicle advance state。
- local vehicle advance result。
- 対象Nodeの `OrderControlBaselineDownstreamBoundaryNodeResult`。

入力の契約は、次である。

- downstream boundary結果なしは `RuntimeError` である。正常なunresolvedではない。
- Node名とoutlinkの順序を、局所状態のoutlinkと照合する。一致しなければ停止する。0で補わない。
- 終端Node名を、コピーWorldの `outlink.end_node` と照合する。
- 観測結果を候補間で共有してよい。書き換えない。
- 候補別の流出許可残高は、境界状態の側で、outlink別に0から始める。

境界処理が実装されたあとに守る契約は、次である。

- 実Worldと別候補を変えない。
- 当該候補のコピーの中では、下流待ちあり・実流出ありと、下流待ち観測なしの制約付きsinkで、終端Nodeの流量容量が有限なときに `DELTAN` を消費する。
- 下流Nodeの `incoming_vehicles` へ、通常の到着として登録しない。
- 境界処理のあと、同じ仮想時刻の拘束順位通過へ戻らない。
- 3状態は意味名で区別する。downstream boundary結果なしは、その3状態に入れない。
- 下流待ちあり・実流出ありは、第13節の専用境界退出を使う。
- 下流待ち観測なしの制約付きsinkは、容量を確認して消費したあと、コピーWorld上で `end_trip()` を使う。

実装を再開するとき、最初に文章で決める事項は、次である。

- 専用境界退出の累積の添字。
- 旅行時間の式。
- `arrival_time` を変えるか。
- `World.VEHICLES` へ残すか。
- leaderとfollowerを外す順。
- 結果型と、退出理由の名前。

境界処理のあとにも、拘束順位外の走査、仮想時刻の統括loop、resolved、unresolved、候補結果型、最終確定接続は残る。

現在の直接作業は、上の注記のとおり、outlink終端境界処理本体と専用テストの実装である。入力は local vehicle advance state、local vehicle advance result、対象Nodeの `OrderControlBaselineDownstreamBoundaryNodeResult` の3つである。downstream boundary結果なしは `RuntimeError` である。3状態は意味名で扱う。下流待ちあり・実流出ありは第19節の専用境界退出である。下流待ちあり・実流出なしは、local horizonの間、終端から出さない。下流待ち観測なしの制約付きsinkは、容量を確認して消費したあと、コピーWorld上で `end_trip()` を使う。境界処理のあと、同じ仮想timestepの binding transfer へ戻らない。

## 19. 専用outlink境界退出のフィールド単位確定契約

**追記日：2026-09-24（残存契約の追加確定）**

本節は、第13節の基本契約を削除せず、その時点で未確定だったフィールド単位の契約を確定する。対象は、下流待ちあり・実流出ありの専用境界退出だけである。下流待ち観測なしの制約付きsinkは、容量確認と容量消費のあと、コピーWorld上で `end_trip()` を使う既存契約を維持する。

コードは未実装である。本節を実装済みと読まない。

交通上の意味は、実際の trip completion ではない。Vehicleが目的地へ到着したことでもない。意味は、TVT-MP候補別局所仮想計算の対象outlink終端から、その候補の局所計算範囲外へ退出したことである。

行わない更新:

- `Vehicle.end_trip()` の呼出し。
- 実旅行完了時刻としての `vehicle.arrival_time` の記録。
- `vehicle.travel_time` の旅行完了値への更新。
- 旅行終了としての `record_log()` の呼出し。

行う更新:

- `outlink.cum_departure`
- `outlink.traveltime_actual`
- `outlink.capacity_out_remain`
- 有限な終端Nodeの `flow_capacity_remain`
- `Link.vehicles`
- leaderとfollower
- 走行中および更新対象のWorld登録
- 専用境界退出記録
- 候補別outlink流出許可残高

### 1. cum_departure

専用境界退出に成功したVehicle 1台ごとに、退出前に所属していたoutlinkについて次を行う。

```python
outlink.cum_departure[-1] += local_world.DELTAN
```

意味は、当該仮想timestepに、そのVehicle 1台分がoutlink終端境界から退出した累積流出量を記録することである。増加量はVehicle数の1ではなく、UXsimの車群単位 `DELTAN` である。同一仮想timestepに複数Vehicleが退出した場合、退出成功1台ごとに `DELTAN` を加算する。

記録先は、現行UXsimの `Vehicle.end_trip()`、`Node.transfer()`、BATCH Level 2参照、TVT-MP binding transferと同じく、累積listの末尾 `[-1]` を、現在処理中の時刻枠として用いる。

境界処理の反映前に、次を検証する。

```python
len(outlink.cum_departure) == local_world.T + 1
```

この検証の意味は、次である。

- `cum_departure` は、時刻ごとの累積流出台数を index 0 から順に保持する。
- 現在の仮想timestepが `T` であれば、index 0 から index `T` までの `T+1` 個の時刻枠が必要である。
- 長さが `T+1` であれば、list末尾 `[-1]` は index `T` であり、現在の仮想timestepの累積流出台数欄を指す。
- 長さが `T+1` より短い場合、現在時刻の記録欄が存在しない。
- 長さが `T+1` より長い場合、list末尾は現在時刻より後の時刻枠を指す。`[-1]` への加算は、現在時刻の退出を将来時刻へ誤記録する。
- この確認は、境界退出台数を過去または将来の誤った時刻欄へ書き込まないために行う。

不一致のときは `RuntimeError` である。別indexへ自動補正しない。listを境界処理内で延長または切詰めしない。Vehicle、容量、allowance、累積値を変更しない。

仮想時計モジュールは、正常な候補状態で `cum_departure` を `current_virtual_timestep` まで延長する。コピー元が将来時刻の枠まで持つ可能性がある場合も、境界処理で黙って末尾へ記録しない。現行UXsimの `[-1]` 契約と、現在仮想時刻への正確な記録の双方を守るため、長さの一致を境界処理の事前条件とする。実装時には、現在時刻に対応する枠を別indexで補正して使うのではなく、入力状態の時刻整合が崩れている重大不整合として停止する。

### 2. traveltime_actual

専用境界退出するVehicleがoutlinkへ進入した時刻以降について、outlinkの実旅行時間を更新する。

開始index:

```python
start_timestep = int(
    vehicle.link_arrival_time / local_world.DELTAT
)
```

更新:

```python
outlink.traveltime_actual[start_timestep:] = (
    (local_world.T + 1) * local_world.DELTAT
    - vehicle.link_arrival_time
)
```

各値の意味は、次である。

- `vehicle.link_arrival_time` は、そのVehicleがoutlinkへ入った時刻を秒で保持する。
- `local_world.DELTAT` は、1 timestepが表す秒数である。
- `vehicle.link_arrival_time / local_world.DELTAT` により、そのVehicleがoutlinkへ入ったtimestepのindexを得る。
- `start_timestep:` は、その進入時刻以降の旅行時間推定値を同じ実績値で更新する、現行UXsimのslice契約である。
- `local_world.T` は、現在処理中の仮想timestepである。
- outlink終端境界処理は、その仮想timestepのVehicle前進後に実行される。
- 境界退出時刻は、当該仮想timestepの開始時点ではなく、当該timestepの移動を終えた終了時点として扱う。
- `(local_world.T + 1) * local_world.DELTAT` は、その終了時点を秒へ変換した値である。
- 退出時刻秒からoutlink進入時刻秒を引いた値が、そのVehicleのoutlink上の実旅行時間となる。

`Node.transfer()` との差は、次である。

- `Node.transfer()` は、対象timestepにおけるVehicle前進より前に、inlinkからoutlinkへVehicleを移す。
- そのため、`Node.transfer()` のinlink離脱時間は、現在timestepの開始境界である `T * DELTAT` を用いる。
- 専用outlink境界退出は、Vehicle前進後にoutlink終端から退出させる。
- そのため、現在timestepの終了境界である `(T + 1) * DELTAT` を用いる。
- 専用outlink境界退出は、処理順の意味として `Vehicle.end_trip()` のLink終端離脱と同じ端点を使用する。

単一indexだけでなく、`start_timestep:` のsliceへ同じ値を設定する。現行UXsimのLink離脱時の `traveltime_actual` 更新契約に合わせる。

現行UXsimの `Vehicle.end_trip()` には、`T + 1` の端点について精査余地を示すTODOがある。TVT-MPだけ独自に `T` へ変更しない。現行UXsimの「Vehicle前進後の時刻末離脱」契約へ合わせる。将来UXsim本体の端点契約が変更された場合、TVT-MP境界退出との再整合が必要である。

第13節の「`(T+1)` を使う旅行時間を無条件に流用しない」は、`end_trip()` 一式の流用を禁じた記録である。本節は、そのうち旅行時間の端点だけを、前進後の時刻末退出として採用する。`end_trip()` の呼出し、`arrival_time = W.T`、`record_log()` は採用しない。

### 3. Vehicleの時刻情報

専用境界退出では、次を変更しない。

- `vehicle.arrival_time`
- `vehicle.travel_time`
- `vehicle.link_arrival_time`
- order-control Visitの `arrival_time`
- order-control Visitの `arrival_tiebreaker`

理由は、次である。

- 専用境界退出は実旅行完了ではない。
- `vehicle.arrival_time` と `vehicle.travel_time` を設定すると、通常の trip completion と誤認される。
- `link_arrival_time` は、`outlink.traveltime_actual` の計算に使用したoutlink進入時刻であり、退出後も診断用の元情報として保持する。
- order-control Visit到着記録は対象Node到着の記録であり、下流局所境界退出では変更しない。

専用境界退出時刻は、Vehicleの通常旅行完了fieldへ書かず、境界処理の専用退出記録へ次を保存する。

- `virtual_timestep`
- `boundary_exit_time_seconds`
- `outlink_name`
- `terminal_node_name`
- `vehicle_name`
- `removal_kind`

`boundary_exit_time_seconds` は次である。

```python
(local_world.T + 1) * local_world.DELTAT
```

### 4. VehicleのWorld登録

専用境界退出後も、Vehicle objectはコピーWorld内で診断および候補結果から参照可能にする。

採用契約:

- `World.VEHICLES` には残す。
- `World.VEHICLES_RUNNING` から除く。
- `World.VEHICLES_LIVING` から除く。
- 新しいWorld共通Vehicle登録列は追加しない。
- candidate local stateの既存Vehicle mappingは変更しない。
- 専用境界状態または結果の `OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord` に、`vehicle_name` を必須識別子として保持する。

理由は、次である。

- `World.VEHICLES` は、全生成Vehicleを名前で保持する参照辞書として機能する。
- 通常の `end_trip()` も、`World.VEHICLES` からVehicleを削除しない。
- `World.VEHICLES` から削除すると、Vehicle名による診断および候補結果参照を壊す。
- `VEHICLES_RUNNING` と `VEHICLES_LIVING` から除けば、後続のcar-following、位置更新、局所前進の対象にならない。

コピーWorldの用途制限は、次である。

- 専用境界退出Vehicleは `state == "end"` だが、`arrival_time` および `travel_time` を旅行完了値へ更新しない。
- したがって、この候補別コピーWorldを通常のUXsim全体解析や通常の旅行完了統計へ渡さない。
- 候補別コピーWorldは、TVT-MP局所候補評価と専用診断だけに用いる。
- 通常Analyzerによる completed trip 集計を、このコピーWorldへ適用しない。
- 専用境界退出Vehicleの正式な意味は、`state` 単独ではなく、専用Vehicle除去記録の `removal_kind` によって判定する。

### 5. 退出後のVehicle field

変更するfield:

```text
state = "end"
link = None
leader = None
follower = None
```

World登録:

```text
VEHICLES_RUNNINGから除去
VEHICLES_LIVINGから除去
World.VEHICLESには残す
```

変更しないfield:

```text
arrival_time
travel_time
link_arrival_time
x
x_old
x_next
v
move_remain
route_next_link
flag_waiting_for_trip_end
order_control_current_visit
order_control_visit_id
order-control Visit履歴
```

位置関連fieldを変更しない理由は、次である。

- Vehicleはoutlink終端へ到達した状態で専用境界退出する。
- 最後に到達した位置、前時刻位置、次位置、速度、未使用移動量を診断情報として保持する。
- `x` を 0 へ変更すると、outlink入口へ戻ったように見える。
- 通常の `end_trip()` が行う `x = 0` は、専用境界退出へ流用しない。

`route_next_link` 等を変更しない理由は、次である。

- 局所境界退出後は `VEHICLES_RUNNING` および `VEHICLES_LIVING` から外れるため、通常のroute処理へ戻らない。
- 診断時に退出直前の状態を確認できるよう保持する。
- 実装時に、これらのfieldを使ってVehicleを再び処理対象へ戻してはならない。

### 6. leader・followerの検証と解除順

対象は、単車線研究条件におけるoutlink終端側の物理先頭Vehicleである。

`Link.vehicles` の物理先頭は `outlink.vehicles[0]` である。除去は `outlink.vehicles.popleft()` である。

正常状態:

- 退出Vehicleは `outlink.vehicles[0]` である。
- `vehicle.link is outlink` である。
- 物理先頭Vehicleの `leader` は `None` である。
- 後続Vehicleがいる場合、退出Vehicleの `follower` が次の物理先頭候補である。
- `follower.leader is exiting_vehicle` である。

一台分の反映前検証:

1. `outlink.vehicles` が空でない。
2. `outlink.vehicles[0] is exiting_vehicle`。
3. `exiting_vehicle.link is outlink`。
4. `exiting_vehicle.leader is None`。
5. followerがある場合、`follower.link is outlink`、`follower.leader is exiting_vehicle`、followerが `Link.vehicles` 内の次の物理位置と整合する。
6. `World.VEHICLES` の同名登録が `exiting_vehicle`。
7. `VEHICLES_RUNNING` と `VEHICLES_LIVING` の同名登録が `exiting_vehicle`。
8. `state == "run"`。

不整合のときは `RuntimeError` である。当該outlinkについて境界状態を変更しない。自動修復しない。

解除と除去の順:

1. 退出前に `cum_departure`、`traveltime_actual`、容量、allowance等に必要な値を計算する。
2. followerがあれば、`follower.leader = None`。
3. `exiting_vehicle.follower = None`。
4. `exiting_vehicle.leader = None`。
5. `outlink.vehicles.popleft()`。
6. `World.VEHICLES_RUNNING` から除去する。
7. `World.VEHICLES_LIVING` から除去する。
8. `exiting_vehicle.link = None`。
9. `exiting_vehicle.state = "end"`。
10. 専用退出記録へ追加する。

実装では、1台分の検証と更新を原子的に扱う。

`end_trip()` は `follower.leader = None` のあと `popleft()` し、退出Vehicle自身の `leader` と `follower` はクリアしない。専用境界退出は、診断上の残留参照を残さないため、退出Vehicleの `follower` と `leader` も `None` にする。この差は、`end_trip()` を呼ばない専用退出に限る。

### 7. 同一outlinkの連続退出

同じ仮想timestepに、同一outlinkから複数Vehicleを退出させ得る。

処理順:

1. `outlink.vehicles[0]` を現在の物理先頭として評価する。
2. 終端到着、allowance、outlink流出容量、有限終端Node容量を確認する。
3. 1台分の専用境界退出を反映する。
4. `popleft()` 後の新しい `outlink.vehicles[0]` を次の物理先頭として再評価する。
5. 条件を満たす限り繰り返す。

各Vehicleを1台ずつFIFO順に処理する。人工的な最大1台制限は設けない。

通常停止条件:

- 次の物理先頭Vehicleがoutlink終端へ到達していない。
- allowanceの整数部分がVehicle 1台分に足りない。
- `outlink.capacity_out_remain` が `DELTAN` 未満。
- 有限な terminal Node の `flow_capacity_remain` が `DELTAN` 未満。
- 下流待ちあり・実流出なし。
- その他、正本で通常待ちとされる条件。

通常停止時は、例外にしない。それまでに成功したVehicleの退出を維持する。待機Vehicleをoutlink上へ残す。未使用allowanceを次時刻へ繰り越す。容量を追加消費しない。後続Vehicleを飛ばさない。

### 8. 原子性単位

採用する原子性は、次の2段階である。

一台単位:

- 1台分の必要条件と更新値をすべて検証・計算してから反映する。
- 1台分の途中状態を残さない。

outlink単位:

- 当該仮想timestepに、そのoutlinkで境界処理の対象になり得る物理先頭側Vehicle列について、登録、Link所属、物理順、leader・followerの重大不整合を、outlinkへの最初の書込み前に事前検証する。
- 重大不整合を事前に検出した場合、そのoutlinkを無変更で `RuntimeError` とする。
- 別outlinkですでに正常完了した処理は戻さない。
- 別outlinkは登録順に独立処理する。

正常な部分成功:

- 1台目が正常退出し、2台目が通常待ち条件になった場合、1台目は戻さない。
- これは異常ではなく、当該時刻に許可された正常な部分流出である。

重大不整合:

- 事前全件検証で検出することを基本とする。
- 反映中に予期しない例外が起きる可能性に備え、実装時には当該outlinkの限定snapshotとrollbackを実装する。
- 当該outlinkについて、反映中の予期しない例外が発生した場合は、同じ呼出しで当該outlinkへ反映した退出、容量、allowance、累積台数、旅行時間、Vehicle登録、leader・follower、退出記録を呼出前へ戻す。
- 別outlinkですでに正常完了した処理は戻さない。
- 予見可能な重大不整合を、1台目退出後まで放置しない。

仮想timestepの全outlinkを一括transactionにはしない。理由は、次である。

- outlinkごとの下流境界状態とallowanceは独立している。
- 後続outlinkの不整合により、先行outlinkの正常な境界流出を戻す必要はない。
- 可読性と交通上の独立性を維持する。

既存の局所前進は、新着incoming登録の失敗時にその呼出全体を戻す。binding transferと `end_trip()` には、2台目の失敗で1台目を戻す契約は無い。専用境界退出のoutlink単位rollbackは、この境界処理のために新しく採用する実装契約であり、UXsim本体の `end_trip()` の挙動ではない。

### 9. 専用退出理由と境界状態型の名称

実装時の正式名称は、次である。

境界状態種別Enumは `OrderControlTvtMpOutlinkBoundaryMode` である。memberは次である。

```text
OBSERVED_WAIT_WITH_OUTFLOW
OBSERVED_WAIT_WITHOUT_OUTFLOW
NO_OBSERVED_WAIT_CONSTRAINED_SINK
```

それぞれ、下流待ちあり・実流出あり、下流待ちあり・実流出なし、下流待ち観測なしの制約付きsinkに対応する。downstream boundary結果なしは、このEnumに入れない。

Vehicle除去理由Enumは `OrderControlTvtMpOutlinkBoundaryRemovalKind` である。memberは次である。

```text
OBSERVED_OUTFLOW_BOUNDARY_EXIT
CONSTRAINED_SINK_END_TRIP
```

`ExitKind` ではなく `RemovalKind` を採用する理由は、次である。

- 専用境界退出と `end_trip()` による除去の双方を、一つの診断軸で表せる。
- 制約付きsink側を、専用境界退出と誤って同一視しない。
- 境界処理によって local World の通常更新対象から除かれた理由を表現できる。

### 10. 境界状態型と結果型

次の型名を、実装時の正式名称とする。

- 候補全体の可変状態: `OrderControlTvtMpCandidateOutlinkBoundaryState`
- outlink別の可変状態: `OrderControlTvtMpCandidateOutlinkBoundaryLinkState`
- 一回の全体処理結果: `OrderControlTvtMpOutlinkBoundaryProcessResult`
- 一回のoutlink別処理結果: `OrderControlTvtMpOutlinkBoundaryLinkProcessResult`
- 専用Vehicle除去記録: `OrderControlTvtMpOutlinkBoundaryVehicleRemovalRecord`

Vehicle除去記録のfield:

```text
vehicle_name
outlink_name
terminal_node_name
virtual_timestep
boundary_exit_time_seconds
removal_kind
```

専用境界退出と制約付きsinkの `end_trip()` の双方で、上記6 fieldだけを使う。`visit_key` fieldは設けない。`current_visit_key_at_removal` などの別名fieldも設けない。

> 歴史的記録: 境界処理実装着手前の検討では、除去記録へ `visit_key` または `current_visit_key_at_removal` を載せる案があった。後続検討で撤回済みである。最新契約は上記6 fieldのみである。

Vehicle除去記録にVisitKey fieldを設けない理由は、次である。

- 対象Node通過後にoutlinkへ進入したVehicleでは、outlink終端Nodeがorder-control対象外であることが正常にある。
- その場合、既存の `begin_order_control_visit_on_link_entry()` により `order_control_current_visit` は `None` になる。
- 境界退出時点の現在VisitからVisitKeyを取得できるとは限らない。
- 取得できるVehicleだけVisitKeyを記録しても、境界除去記録の識別契約として一貫しない。
- 境界除去Vehicleの必須識別子には `vehicle_name` を使う。
- `order_control_visit_id` の残存値からVisitKeyを推測しない。
- 拘束順位列や通過済みVisit列から過去VisitKeyを逆算しない。
- 境界退出記録へ過去の対象Node Visitを曖昧に混在させない。
- 将来、対象Node通過Visitとの正式な対応が必要になった場合は、別の明示的な対応情報として設計する。

候補全体状態の最低限field:

```text
local_vehicle_advance_state
downstream_boundary_node_result
outlink_states
completed_virtual_timesteps
vehicle_removal_records
```

outlink別可変状態の最低限field:

```text
outlink_name
terminal_node_name
boundary_mode
active_timestep_count
transferred_vehicle_count
observed_average_outflow_rate
flow_allowance
cumulative_observed_outflow_exit_vehicle_names
cumulative_constrained_sink_end_trip_vehicle_names
```

全体処理結果の最低限field:

```text
node_name
virtual_timestep
outlink_results
```

outlink別結果の最低限field:

```text
outlink_name
terminal_node_name
boundary_mode
flow_allowance_before
flow_allowance_added
flow_allowance_after
vehicle_names_at_end_before
observed_outflow_boundary_exit_vehicle_names
constrained_sink_end_trip_vehicle_names
waiting_vehicle_names_after
capacity_out_remain_before
capacity_out_remain_after
terminal_node_flow_capacity_remain_before
terminal_node_flow_capacity_remain_after
```

型設計原則:

- 結果型とVehicle除去記録は frozen dataclass である。
- 順序を持つ列は tuple である。
- 可変allowanceと処理済み時刻は、境界状態だけに保持する。
- baseline観測結果は読取専用である。書き換えない。
- 専用退出Vehicleと制約付きsink Vehicleを、別列で診断可能にする。

内部helperのファイル内分割は、実装時のコード構造に残してよい。上の型名、Enum member、field契約は、その分割で変えない。

### 11. 制約付きsinkとの共通部分と相違

共通事前条件:

- outlink終端へ到達している。
- 物理FIFOである。
- `outlink.capacity_out_remain >= DELTAN`。
- terminal Nodeの `flow_capacity` が有限なら、`flow_capacity_remain >= DELTAN`。
- 下流Linkの `capacity_in_remain` は使わない。
- terminal Nodeの `incoming_vehicles` へ登録しない。
- 同じ仮想timestepの binding transfer へ戻らない。
- 人工的な最大1台制限を設けない。

下流待ちあり・実流出あり:

- observed average outflow rate を使う。
- `flow_allowance` を使う。
- 専用境界退出を使う。
- `end_trip()` を呼ばない。
- `arrival_time` と `travel_time` を変更しない。
- `record_log()` を呼ばない。
- `removal_kind` は `OBSERVED_OUTFLOW_BOUNDARY_EXIT` である。

下流待ち観測なしの制約付きsink:

- rateを使わない。
- allowanceを使わない。
- 容量確認と容量消費のあと `end_trip()` を呼ぶ。
- `removal_kind` は `CONSTRAINED_SINK_END_TRIP` である。
- `end_trip()` の通常副作用を、コピーWorld内で受ける。
- 実Worldの旅行終了を意味しない。
- 除去記録へ書く識別子は、専用境界退出と同じく `vehicle_name` だけである。`end_trip()` の前にVisitKeyを保存しない。

実装時の共通helper候補:

- outlinkとterminal Nodeの対応検証。
- 物理先頭検証。
- `capacity_out_remain` 検証。
- 有限な terminal Node 容量の検証。
- FIFO候補抽出。
- outlink別診断値の取得。

別処理にする部分:

- allowanceの更新と消費。
- 専用境界退出本体。
- `end_trip()` 呼出し。
- Vehicle除去後field。
- `RemovalKind`。
- 累積退出Vehicle列。

### 12. 注意事項

今回確定した専用境界退出は、候補別コピーWorld専用である。

- 実Worldへ適用しない。
- 通常UXsimの trip completion へ適用しない。
- 通常Analyzerの旅行完了統計を、候補コピーWorldへ適用しない。
- `state == "end"` だけを見て、通常旅行完了と解釈しない。
- 専用Vehicle除去記録を正本とする。
- 実装後のテストでは、`World.VEHICLES` へ残ることと、`VEHICLES_RUNNING` および `VEHICLES_LIVING` から外れることを、別々に確認する。

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

**2026-09-21更新（最新の再開情報）：** 下流境界observerまでの実装は完了済みである。候補別局所仮想計算は未実装である。今回、入力、下流境界、horizon、早期終了、順位拘束範囲について途中確定した。条件付き平均流出率方式を正式採用し、観測countを正本として局所計算側で算出する。流出許可残高は具体的候補別・outlink別に独立し、小数部分と未使用整数部分を繰り越す。`active=0`は制約付きsinkへ分岐するが、具体実装は未確定である。時点`T`以後の新規流入なしを初期実装方針として採用した。local horizon上限は`configured_horizon_steps`であり、全buyerと全sellerの必要情報が揃えば早期終了する。buyerとsellerは別に識別し、役割から短縮・遅延を決めつけない。局所仮想計算では`trade_order`全体を拘束順位として使用しない。完全な局所拘束順位列は、TVT形成前の未通過確定済みVisitと、`K_fixed`まで新たに確定されるVisit列である。この完全な拘束順位列は`trade_order`の必要部分を材料に含み得るが、`N+1`位以降の意思決定窓内Visitも含み得るため、`trade_order`の単純prefixとは限らない。完全な拘束順位列を構築するための公開材料と接続方法は未確定である。それより後方のVehicleへbaseline順位を強制しない。拘束順位外Vehicleは標準transfer相当処理を用いる方向だが、詳細は未確定である。既存の`Node.transfer()`を局所loop後段でそのまま呼ばない。一般形順位の制度ロジックと順位アルゴリズム、FIFO検査接続は再考しない。ただし、既存の公開結果型を含めて一切変更不要であるとは確定しない。Python実装と専用テストは未着手である。完全な実装前仕様ではない。次の直接作業は、`K_fixed`に従う完全な局所拘束順位列を構築するために、現行の上流結果から取得できるVisitと情報を調査し、不足する公開材料と最小の接続方法を確定することである。標準transfer相当処理の詳細設計はその次の作業である。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の入力・境界・順位拘束設計の途中確定記録」を参照する。今回のMarkdown追記は未コミットである。`diagnostics/order_control.zip`は対象外である。

**2026-09-22更新（最新の再開情報）：** 上記2026-09-21の再開情報、および保存済みcommit `1613eb9`の「TVT-MP完全局所拘束順位列・確定時正式進路保存・最終分岐設計の追加途中確定記録」は歴史的記録として残す。`1613eb9`では4区分、確定時正式進路、原子的保存、原因別最終分岐を記録し、拘束順位外Vehicleとactive=0時の制約付きsinkは未確定のままであった。2026-09-22に、拘束順位外Vehicleの進路4分類、一時的FCFS走査、clearanceと通常の通過不能の区別、incoming保持と物理移動、下流境界の3分岐、active=0の制約付きsink、候補別統合仕様を確定した。候補別局所仮想計算は未実装である。Python実装と専用テストは未着手である。完全な実装前仕様は未作成である。公開API名、結果型名、helper名、診断のPython型は未確定である。次の直接作業は、公開API、結果型、helper責務、診断型、例外契約、モジュール構成、専用テスト契約、既存上流結果との接続を含む完全な実装前仕様の作成である。実装時は初学者が処理順を追える可読性を、短さより優先する。撤回済みの`route_pref`局所乱数案、分類3のVehicle ID置換、active=0の流出停止、active=0の人工的な最大1台制限、BATCH Level 2単純sinkの流用は再採用しない。最新詳細は、本ファイルの「TVT-MP候補別局所仮想計算の拘束順位外処理・下流境界・統合仕様の確定記録」を参照する。今回のMarkdown追記は未コミットである。Git操作は利用者がTerminalで行う。

**2026-09-22追記（最新の再開情報）：** 上記の「完全な実装前仕様は未作成」は、拘束順位外処理・下流境界・統合仕様を記録した時点の歴史的記録である。その後、公開API、結果型、helper責務、例外契約、診断契約、モジュール構成、専用テスト契約、実装区分を含む完全な実装前仕様を確定した。現在の最新正本は、本ファイルの「TVT-MP候補別局所仮想計算の完全な実装前仕様」である。候補別局所仮想計算のPython実装と専用テストは未着手である。直ちにPython実装へ進まない。次の直接作業は、この追記を独立確認し、利用者がMarkdownをcommitおよびpushしたあと、最初の実装区分「正式進路付き順位台帳と原子的確定」の目的と範囲を利用者へ提示し、合意後にその区分だけへ着手することである。事前合意のないStep体系は導入しない。上記の再開情報を現在の作業指示として読まない。今回のMarkdown追記は未コミットである。Git操作は利用者がTerminalで行う。

**2026-09-23更新（最新の再開情報）：** 上記の実装前仕様へ、コード確認後の3点を補った。区分2の既到着確定と先頭連続非参加確定は、新しい本番経路で原子的確定APIへ接続する。その接続は、台帳実装の次の実装区分「既到着Visitと先頭連続非参加Visitの原子的先行確定接続」である。台帳区分の完了だけでは、本番経路が `confirm_visits_in_order()` を使わないことの確認を終えたことにはしない。局所状態はWorld全体のコピーを残し、対象外は更新しない。局所通過試行の最後の時刻は `T + configured_horizon_steps` である。Python実装と専用テストは未着手である。直ちに実装へ進まない。最新の作業順は、本ファイルの完全な実装前仕様にある「次の再開地点」に従う。

**2026-09-24注記：** 上記「未着手」と「最初の実装区分は正式進路付き順位台帳」は、2026-09-23時点の再開情報である。現在の実装済み範囲と次の直接作業は「TVT-MP候補別局所仮想計算の実装進捗・確定実装契約・下流境界追加設計記録」を参照する。

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
