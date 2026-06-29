# ORDER_EXCHANGE_PHASE4-5_CLEARANCE_FCFS_DESIGN_NOTES

UXsim Order Exchange 改変作業における、phase 4-5：クリアランスありFCFSの正式設計メモ。

進捗の詳細は [ORDER_EXCHANGE_PROGRESS.md](ORDER_EXCHANGE_PROGRESS.md) を参照してください。フェーズ4-3以前のFCFS transfer詳細は [ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md](ORDER_EXCHANGE_FCFS_TRANSFER_DESIGN_NOTES.md) を参照してください。

---

## 1. このメモの位置づけ

- 本メモは **phase 4-5：クリアランスありFCFS** の設計メモである。
- **まだコード実装は行わない。**
- 目的は、案B：クリアランスありFCFSを安全に実装する前に、判定ロジック・状態変数・テスト方針を整理することである。
- ここでいう **案B** は、将来の実験・評価で用いる **本来のFCFSモデル** である。

---

## 2. ここまでの完了済み事項

- **phase 4-3**：初期版クリアランスなしFCFS transfer を実装済み。
- **phase 4-3追加検証**：arrival-order behavior と blocked-outlink skip behavior を確認済み。
- **phase 4-4**：同時到着時の固定tiebreaker を実装済み。
- **phase 4-4**：`tests_fcfs_order_control_tiebreaker.py` により、同時到着時に tiebreaker 順で通過することを確認済み。
- 現在のFCFS候補Vehicleのソートキーは **`(arrival_time, tiebreaker, veh.id)`** である。
- tiebreaker まで偶然同値だった場合には、**`veh.id`** により決定的に順序を固定する。

ソートキーの内訳：

| キー | 参照先 | 意味 |
|------|--------|------|
| 第1キー | `order_control_node_arrival_times[node.name]` | 実際の初回到着時刻 |
| 第2キー | `order_control_node_arrival_tiebreakers[node.name]` | 同時到着時の固定tiebreaker |
| 第3キー | `veh.id` | tiebreaker 同値時の決定的な最終タイブレーク |

したがって、同時到着時の順位は単に tiebreaker だけではなく、正確には以下の順序で固定される。

1. arrival_time
2. tiebreaker
3. veh.id

---

## 3. 案Aと案Bの位置づけ

### 案A：クリアランスなしFCFS

- phase 4-3で実装した初期版である。
- **実装検証用・デバッグ用・退避用** として位置づける。
- 交差点内での方向切替安全性を考慮していないため、**研究上の本命FCFSモデルとしては使わない。**
- `incoming_vehicles` に含まれる複数方向のVehicleが、条件次第で同一タイムステップ内に通過できてしまう可能性があり、現実の交差点安全制約としては不十分である。

### 案B：クリアランスありFCFS

- **本研究で評価対象とする本来のFCFSモデル** である。
- inlinkが異なる場合を異方向切替とみなし、方向切替時にクリアランス制約を課す。
- 同時到着時の順位は phase 4-4で実装済みの **`(arrival_time, tiebreaker, veh.id)`** により固定される。

---

## 4. 既存 transfer_fcfs() の扱い

- 現在の `transfer_fcfs()` は **クリアランスなし版** である。
- phase 4-5実装時には、既存の `transfer_fcfs()` を **`transfer_fcfs_no_clearance()`** に改名する方針とする。
- `transfer_fcfs_no_clearance()` は、**回帰確認・デバッグ・比較用** に残す。
- `transfer_fcfs_no_clearance()` には、研究用FCFSモデルとしては使用しない旨のコメントを付ける。
- 案B用には **`transfer_fcfs_clearance()`** を新設する。
- 最終的に `order_control_type="fcfs"` は **`transfer_fcfs_clearance()`** を呼ぶ想定とする。

コメント案：

```python
# クリアランスなしFCFS。回帰確認・デバッグ用に残す。
# 本研究で評価対象とするFCFSモデルとしては使用しない。
def transfer_fcfs_no_clearance(s):
    ...
```

---

## 5. transfer_fcfs_clearance() が踏襲するもの・変更するもの・追加するもの

`transfer_fcfs_clearance()` は、既存のクリアランスなしFCFS処理を完全に捨てるのではなく、必要な部分を踏襲し、方向切替・クリアランス制約を追加する。

### 踏襲するもの

- `incoming_vehicles` から候補Vehicleを作る。
- `route_next_link` を持ち、対象Nodeへの初回到着時刻が記録されているVehicleを候補にする。
- 候補Vehicleを **`(arrival_time, tiebreaker, veh.id)`** で並べる。
- 通過可能なVehicleは、標準 `Node.transfer()` と同等のリンク間移動処理で次Linkへ移す。
- `capacity_in_remain`, `capacity_out_remain`, `flow_capacity_remain` などを通過ごとに更新する。
- trip end待ちVehicleの処理を維持する。
- `incoming_vehicles` のクリア処理など、既存FCFS transferで必要な後処理を維持する。

### 変更するもの

- `order_control_type="fcfs"` の本体として、研究用にはクリアランスあり処理を使う。
- 異方向切替時にクリアランス判定を追加する。
- 異方向かつクリアランス未充足のVehicleが現れた場合は、容量・物理制約を見る前に **break** する。
- クリアランス不要またはクリアランス充足後に限り、容量・物理制約を評価する。

### 追加するもの

- `order_control_clearance_timesteps`
- `last_order_control_inlink`
- `last_order_control_entry_timestep`
- 通過後の `last_order_control_inlink` と `last_order_control_entry_timestep` の更新
- World共通clearance設定と、それをNodeへ反映する仕組み

---

## 6. order_control_type の考え方

- 研究上、**`order_control_type="fcfs"` は最終的にクリアランスありFCFSを意味する。**
- クリアランスなしFCFSを別の `order_control_type` として積極的に使う予定はない。
- ただし、検証用・退避用コードとして `transfer_fcfs_no_clearance()` は残す。
- 標準UXsimとの比較実験に用いるFCFSは、**原則としてクリアランスありFCFS** である。

---

## 7. 方向の定義

- **inlink が異なれば異方向切替** とみなす。
- 今回の単車線・簡易交差点制御では、右左折・対向・交錯関係までは詳細に扱わない。
- **inlink を方向の代理変数** とする。

```python
current_inlink = veh.link
last_inlink = s.last_order_control_inlink

if last_inlink is None:
    # まだ通過Vehicleなし。クリアランス不要。
elif current_inlink == last_inlink:
    # 同方向。クリアランス不要。
else:
    # 異方向切替。クリアランス判定が必要。
```

---

## 8. clearance_timesteps の意味

- 本研究では、inlink が異なる場合を異方向切替とみなす。
- **`order_control_clearance_timesteps`** は、直近の通過Vehicleの inlink とは異なる inlink からの進入を禁止するタイムステップ数として定義する。
- 初期値は **1** を想定する。ただし可変にする。

例：

- `last_order_control_entry_timestep = 3`
- `order_control_clearance_timesteps = 1`

この場合、

- `current_timestep = 4` では異方向進入はまだ不可
- `current_timestep = 5` から異方向進入を可能とする

異方向進入が可能かどうかは、概念的には以下で判定する。

**判定式：**

```
current_timestep - last_order_control_entry_timestep > order_control_clearance_timesteps
```

実装上は概念的に：

```python
s.W.T - s.last_order_control_entry_timestep > s.order_control_clearance_timesteps
```

---

## 9. clearance_timesteps = 0 の意味

- **`clearance_timesteps = 0` の場合でも、案A：クリアランスなしFCFSとは同じではない。**

同方向の場合：

- `incoming_vehicles` 内の連続する複数Vehicleが、容量・物理条件を満たす限り、**同一タイムステップ内に通過できる可能性がある。**

異方向の場合：

- たとえ `incoming_vehicles` 内に既に入っていても、先の異方向Vehicleに続いて **同一タイムステップ内に通過することは不可。**
- **次のタイムステップ** に移行すれば、同方向でも異方向でも通過可能。

これは現実交通として完全ではないが、**最低限の現実性を持つFCFSモデルとして無難な下限的クリアランス設定** である。

将来の交差点安全技術を考えると、`clearance_timesteps = 0` のモデルも全くの絵空事ではない、という位置づけにする。

---

## 10. clearance_timesteps の適用範囲

- 本研究の基本設定では、`clearance_timesteps` は **FCFSだけでなく、将来のBatch Processing、Time-value Transactionにも共通に適用する。**
- つまり、order-control対象Node全体に共通する実験条件として扱う。
- 各Nodeで異なる `clearance_timesteps` を設定することは、現時点の研究では主目的ではない。
- ただし、実装上はNodeにも `order_control_clearance_timesteps` を持たせることで、将来のNode別拡張に対応できる余地を残す。

---

## 11. World共通設定とsetter方針

- `clearance_timesteps` は **World共通の実験条件** として持たせる方針とする。
- 例：`W.order_control_clearance_timesteps = 1`
- World共通値を設定するsetterとして、`W.set_order_control_clearance_timesteps(clearance_timesteps)` のような関数を用意する案が有力。
- **setter** とは、外から設定値を入れるための関数である。
- 既存の `W.set_order_control_for_nodes(...)` も setter の一種である。
- 本研究では、まずWorld共通値を設定し、その後 order-control対象Nodeに設定値を反映する流れが自然。

概念例：

```python
W.set_order_control_clearance_timesteps(1)
W.set_order_control_for_nodes(["merge1", "merge2"], order_control_type="fcfs")
```

**本メモの時点では、上記はまだ実装しない。**

---

## 12. Nodeに必要な状態

Nodeには少なくとも以下を持たせる方針とする。

```python
s.order_control_clearance_timesteps = 1
s.last_order_control_inlink = None
s.last_order_control_entry_timestep = None
```

| 属性 | 意味 |
|------|------|
| `order_control_clearance_timesteps` | 方向切替に必要なクリアランス時間 |
| `last_order_control_inlink` | 直近でこのNodeを通過したVehicleのinlink |
| `last_order_control_entry_timestep` | 直近でVehicleがこのNodeへ進入したタイムステップ |

初期値：

- `order_control_clearance_timesteps` は World共通値から反映する
- `last_order_control_inlink = None`
- `last_order_control_entry_timestep = None`

---

## 13. 通過後に更新する状態

Vehicleが実際にNodeを通過したら、同方向・異方向に関係なく、以下を毎回更新する。

```python
s.last_order_control_inlink = inlink
s.last_order_control_entry_timestep = s.W.T
```

この更新は、そのNodeにおける「最後に進入した方向とタイムステップ」を保持するために必要である。

---

## 14. 同一タイムステップ内の複数通過ルール

- **同じinlinkが連続する場合、クリアランス不要。**
- 容量・物理条件が許せば、**同一タイムステップ内に同じinlinkから複数台通過してよい。**
- **異なるinlinkへ切り替わる場合** は、クリアランス制約を満たすまで通過不可。
- **同一タイムステップ内で異方向へ切り替わることは、`clearance_timesteps = 0` の場合でも不可。**
- この点が **案A：クリアランスなしFCFSとの重要な違い** である。

---

## 15. X/Y/Z問題：単純なcontinue/break設計の落とし穴

当初は、以下の単純ルールを考えていた。

| 状況 | 処理 |
|------|------|
| 容量・物理制約NG | `continue` |
| クリアランスNG | `break` |

しかし、このルールには落とし穴がある。

### 問題例

| 順位 | Vehicle | 方向 |
|------|---------|------|
| 1 | 車X | 方向A |
| 2 | 車Y | 方向B |
| 3 | 車Z | 方向A |

もし、

- Xが容量制約等で通れない
- Yも容量制約等で通れない

という場合、単純ルールでは、

```
X → continue
Y → continue
Zを検討
```

となってしまう。

すると、Zが容量・物理制約を満たす場合には、**方向Bの先順位Vehicle Yを、方向Aの後順位Vehicle Zが追い越す可能性がある。** これは案B：クリアランスありFCFSの趣旨に反する。

この問題を、本メモでは **X/Y/Z問題** と呼ぶ。

---

## 16. 修正版の判定順

X/Y/Z問題を踏まえ、設計上の判定順を以下のように整理する。

候補Vehicleは、既存のFCFS順序に従い、以下の順で評価する。

```
(arrival_time, tiebreaker, veh.id)
```

各候補Vehicleについて、以下の順で判定する。

1. 候補Vehicleの inlink を取得する。
2. 直近通過 inlink と比較する。
3. 異方向で、かつクリアランス未充足なら、容量・物理制約を見る前に **break** する。
4. クリアランス不要またはクリアランス充足の場合に限り、容量・物理制約を見る。
5. 容量・物理制約NGなら **continue** する。
6. 容量・物理制約OKなら通過させる。
7. 通過後、`last_order_control_inlink` と `last_order_control_entry_timestep` を更新する。

### 概念コード

```python
current_inlink = veh.link

clearance_required = (
    s.last_order_control_inlink is not None
    and current_inlink != s.last_order_control_inlink
)

if clearance_required:
    clearance_ok = (
        s.W.T - s.last_order_control_entry_timestep
        > s.order_control_clearance_timesteps
    )
    if not clearance_ok:
        break

capacity_ok = ...
if not capacity_ok:
    continue

# 通過処理
s.last_order_control_inlink = current_inlink
s.last_order_control_entry_timestep = s.W.T
```

**これは設計概念であり、まだ実装ではない。**

---

## 17. 修正版判定順の意味

- **異方向かつクリアランス未充足** のVehicleは、容量制約の充足可否にかかわらず、その時点で **break** する。
- これは、そのVehicleが先順位Vehicleとしてクリアランス待ちをしているため、**後順位Vehicleが先順位Vehicleを追い越せない** ようにするためである。
- 一方、**クリアランス不要またはクリアランス充足後** に容量・物理制約で通れないVehicleは、もはやクリアランス待ちではない。
- その場合は容量・物理制約による通過不能として扱い、**continue** により後順位Vehicleを検討してよい。
- したがって、重要なのは「通過不能理由だけでcontinue/breakを決める」のではなく、**「クリアランス未充足かどうかを容量判定より前に見る」** ことである。

---

## 18. シナリオ1〜3との整合確認

前提：

- `order_control_clearance_timesteps = 1`
- 判定式は `current_timestep - last_entry_timestep > clearance_timesteps`
- したがって、**差分0と差分1はクリアランス未充足、差分2でクリアランス充足**

### シナリオ1

- 直前通過は方向A、タイムステップ **i-1**
- タイムステップ **i** で、Xは方向Aかつ容量OKなので通過
- Yは方向Bで、Xと異方向、同一タイムステップなので差分0となり **break**
- タイムステップ **i+1** でもYは差分1で **break**
- タイムステップ **i+2** でYは差分2となりクリアランスOK。容量OKなら通過
- その後ZはYと異方向で同一タイムステップ差分0となるため **break**

### シナリオ2

- タイムステップ **i** でXが通過し、Yは異方向差分0で **break**
- タイムステップ **i+1** でYは差分1で **break**
- タイムステップ **i+2** でYはクリアランスOKだが容量NGなら **continue**
- この時点で直近通過はタイムステップ **i** のXなので、現在 **i+2** との差分は2
- したがってZは方向にかかわらずクリアランス条件を満たし、容量・物理制約を満たせば通過可能

### シナリオ3

- 直前通過は方向A、タイムステップ **i-1**
- タイムステップ **i** でXは方向Aだが容量NGなので **continue**
- 直近通過はまだ **i-1** の方向A
- 同じタイムステップ **i** でYは方向B、差分1なのでクリアランス未充足で **break**
- タイムステップ **i+1** でXが容量OKなら通過し、lastはA, **i+1** に更新
- 同じ **i+1** でYは異方向差分0となるため **break**
- タイムステップ **i+2** でYは差分1なので **break**
- タイムステップ **i+3** でYは差分2となりクリアランスOK
- Yが容量OKなら通過
- Yが容量NGなら **continue**
- その場合、Zは直近通過 **i+1** のXとの差分2により、方向にかかわらずクリアランス条件を満たす

---

## 19. 通過不能理由の扱い

- 初回実装では、通過不能理由を文字列で管理する補助関数は **導入しない** 方針とする。
- つまり、`"blocked_by_capacity"` や `"blocked_by_clearance"` のような文字列を返す関数は現時点では作らない。
- 代わりに、`transfer_fcfs_clearance()` 内でロジックを直接書く方針とする。
- ただし、単純に `capacity_ok` / `clearance_ok` で `continue` / `break` するだけでは不十分である（X/Y/Z問題参照）。
- 修正版では、**異方向かつクリアランス未充足なら容量を見る前に break** し、それ以外の場合に容量・物理制約を評価する。
- 初回実装では、`capacity_ok` や `clearance_ok` のような分かりやすい一時変数を使い、判定内容が読めるようにする。

---

## 20. 実装順序案

1. Nodeに clearance用状態を追加する。
   - `order_control_clearance_timesteps`
   - `last_order_control_inlink`
   - `last_order_control_entry_timestep`

2. Worldに `order_control_clearance_timesteps` の共通設定を追加する。

3. World共通clearance設定用setterを追加する。
   - 候補名：`set_order_control_clearance_timesteps(clearance_timesteps)`

4. 既存の `transfer_fcfs()` を `transfer_fcfs_no_clearance()` に改名する。
   - コメントで研究用FCFSとしては使わないことを明示する。

5. `transfer_fcfs_clearance()` を新設する。

6. `Node.transfer()` の `order_control_type=="fcfs"` 分岐を `transfer_fcfs_clearance()` に切り替える。

7. 既存FCFS系テストを点検・必要に応じて調整する。
   - 現在のクリアランスなし挙動を前提とするテストは、no_clearance版の検証として残す。
   - phase 4-5用には、新しいクリアランスありFCFSテストを追加する。

8. phase 4-5用のクリアランスありFCFSテストを追加する。

---

## 21. テスト方針

phase 4-5実装後は、少なくとも以下のテストが必要である。

### 1. clearance_timesteps=0 のテスト

- 同方向連続通過は同一タイムステップ内に可能
- 異方向連続通過は同一タイムステップ内には不可
- 次タイムステップでは異方向通過可能

### 2. clearance_timesteps=1 のテスト

直近の通過が timestep **i** で起き、その後に異方向Vehicleを通そうとする場合を考える。

| タイムステップ | 状況 |
|----------------|------|
| **i** | 同一タイムステップ内の異方向通過は不可 |
| **i+1** | `current_timestep - last_entry_timestep = 1` なので、異方向通過はまだ不可 |
| **i+2** | `current_timestep - last_entry_timestep = 2` となり、`2 > 1` を満たすため、異方向通過が可能 |

つまり、`clearance_timesteps = 1` では、直前通過の **次のタイムステップではまだ異方向通過不可** であり、**その次のタイムステップから異方向通過可能** となる。

### 3. X/Y/Z問題のテスト

- X方向A, Y方向B, Z方向A の順序で、YをZが追い越さないこと
- ただし、Yがクリアランス充足後に容量制約で通れない場合、Zを検討できること

### 4. 既存挙動維持のテスト

- arrival-order behavior
- blocked-outlink skip behavior
- simultaneous-arrival tiebreaker behavior
- 標準UXsim baseline
- `example_00en_simple.py` の主要結果

---

## 22. 未解決・注意事項

- 修正版判定順で、シナリオ1〜3は整合的に処理できる見通しが立った。
- ただし、落とし穴が全くないとは断言しない。
- 実装時には、X/Y/Z問題を含む具体テストで確認する必要がある。
- `transfer_fcfs_clearance()` をどこまで関数分割するかは、初回実装では慎重に判断する。
- **標準UXsim挙動を壊さない** 方針は引き続き最重要である。
- クリアランスありFCFSは、標準UXsimと **service discipline が異なる** ため、比較時にはその違いを研究メモ・論文内で明示する必要がある。

---

## 23. まとめ

- **phase 4-5** では、案B：クリアランスありFCFSを実装する。
- そのためには、クリアランスなしFCFSを退避し、`transfer_fcfs_clearance()` を新設する。
- inlinkを方向代理変数とし、異方向切替時には `clearance_timesteps` に基づく制約を課す。
- クリアランス未充足の異方向Vehicleは、後順位Vehicleに追い越されないよう **break** する。
- クリアランス不要またはクリアランス充足後に容量・物理制約で通れないVehicleは **continue** できる。
- この修正版判定順により、少なくとも現在検討したシナリオ1〜3には整合的に対応できる。
- 正式実装前に本設計を確認し、実装時にはテストで潰していく。
