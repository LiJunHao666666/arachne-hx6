# G4 Offline Configuration-Space Contract (G4-D0)

```text
contract_status: GPT_APPROVED_CONTRACT_TEXT
contract_approval_scope: CONTRACT_TEXT_ONLY
project_status: ANALYSIS_ONLY
procurement_allowed: false
implementation_allowed: false
hardware_assembly_allowed: false
gazebo_allowed: false
px4_allowed: false
```

**ANALYSIS_ONLY**
**NOT_FOR_PROCUREMENT**
**NOT_AN_IMPLEMENTATION_AUTHORIZATION**
**overall_system_readiness: UNDETERMINED**
**readiness_gate: UNDETERMINED_REQUIREMENTS**
**g3_evidence_gate: not EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS**

This document is the GPT-approved G4-D0 contract text for Arachne-HX6.
Approval is limited to the contract text. It is not a G4 implementation,
not a G3 evidence closure, and not authorization for procurement,
physical assembly, simulation dynamics, or flight control.

本文件是已经通过 GPT 审核的 G4-D0 合同文本。批准范围仅限合同文本，
不代表 G4 已实施，不代表 G3 证据门控已闭合，也不授权采购、实体组装、
仿真动力学、飞控或分析代码实施。

---

## 1. 阶段名称

- **阶段族：** G4 Offline Configuration-Space Analysis（离线构型空间分析）
- **本文件对应子阶段：** **G4-D0 合同定义**
- **官方文件名：** `docs/G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md`
- **建议分支：** `feature/g4-offline-analysis-contract`
- **本子阶段允许的工作：** 仅起草并审查本分析合同
- **本子阶段禁止的工作：** 任何分析代码、YAML、测试、报告生成、URDF 修改、仿真或采购

G4 作为阶段族 **尚未正式实施**。本合同文本已通过审核，但在后续子阶段被单独批准之前，仓库中不存在已授权的 G4 分析实现。

Acceptance of this file as GPT-approved contract text still does **not**
authorize G4 analysis code. A later implementation sub-gate would require
its own independent approval.

---

## 2. 本文件是什么，以及不是什么

G4-D0 **是：**

- 一份 ANALYSIS_ONLY 工程合同文本
- 对 G2 已记录缺口
  `SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF`
  的后续分析边界定义
- 对未来（尚未批准的）离线构型空间分析的目标、输入、输出、门控和禁止事项的书面约束

G4-D0 **不是：**

- G4 已正式实施
- G3 已达到 `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`
- 采购、选型、下单或结构冻结授权
- 实体组装、台架、CAD 实测或硬件验证授权
- Gazebo、PX4、实时控制或可飞结论授权
- 修改已合并 G1 URDF / Xacro / link / joint / 拓扑的授权
- 把 `analysis_stowed` 升级为合格收拢姿态的授权
- 把名义 `CLEARANCE_MET` 升级为稳健几何通过的授权
- 把 G1.5 条件能量闭合升级为整机质量闭合的授权

---

## 3. 永久边界（继承，不可被本合同放宽）

Arachne-HX6 remains simulation-first and non-weaponized. Official work is
limited to disaster response, environmental sensing, hazardous-area
inspection, and non-weaponized reconnaissance / remote inspection.

本合同保持并继承：

- `project_status: ANALYSIS_ONLY`
- `procurement_allowed: false`
- `implementation_allowed: false`（G4-D0）
- `hardware_assembly_allowed: false`
- `gazebo_allowed: false`
- `px4_allowed: false`
- 非武器化
- 不授权采购
- 不授权实体组装
- 不开发自由飞行、自推进、穿透、投射、毁伤或武器化控制链
- 不把视觉识别直接连接到任何危险动作
- 不修改已合并的 G1 URDF/Xacro、link、joint 或拓扑，除非后续有独立、明确批准的范围
- G3 完成不自动授权 G4 实施、采购或实体制造

Completing G3 does **not** automatically allow procurement, physical
assembly, or the next stage. Completing G4-D0 also does **not** allow
those things. Procurement status may change only after:

- safety requirements are met
- mass / evidence ledgers are complete
- risk assessment is complete
- site rules are defined and accepted
- formal approval is recorded
- an independent official gate explicitly authorizes the change

Until that independent gate exists, `procurement_allowed` remains `false`.

This contract does not design or compute real launch, self-propulsion,
explosive, penetrative, destructive, ballistic, automatic-attack, or
weaponized control chains. Vision or perception outputs must not connect
directly to any hazardous action. Side pods remain fixed, non-launching
sensor placeholders.

If a physical concept demonstration is ever discussed, the inert
demonstration model must remain constrained by enclosed rails, tethers,
or mechanical stops for
the entire demonstration. It must not free-fly or self-propel. Speed,
kinetic energy, materials, pinch distances, and stopping distance must be
safety assessed. Guards, e-stop, and human control are required. **No
such demonstration is authorized by G4-D0.**

---

## 4. 与 G1 / G1.5 / G2 / G3 的关系

### 4.1 G1

G1 数字骨架保持不变。G4-D0 不修改已验收的 identifiers、joints、topology、
站立姿态或 Xacro / URDF 实现。

明确禁止修改：

- URDF / Xacro
- link / joint 名称
- joint 类型
- 拓扑
- mesh
- collision
- inertial
- standing pose
- `left_sensor_pod` / `right_sensor_pod` 标识符

README 已记录、且本合同不得当作已关闭的 G1 限制：

- 站立角不是硬件标定值
- 质量、惯性和碰撞几何都是占位估算
- `sensor_pod` 与 coxa 静态间隙约 1 mm，机械冻结前必须重构
- femur 与旋翼盘最近约 2 cm，必须进行扫掠体积和自碰撞分析
- 当前没有旋翼动力学、飞行控制或模式切换
- 当前版本不允许作为硬件采购依据

README 中约 1 mm 和约 2 cm 的字面状态是
`BASELINE_REPORTED_ESTIMATE_ONLY`。它们只是历史基线报告的名义估计，
不是经过测量、验证或公差分析的数值。它们不得直接作为安全阈值、
通过阈值、制造公差或结构冻结依据，也不得直接作为未来求解器的权威
数值输入。该记录只允许作为待复核的基线观察 / 回归提示。未来分析
必须从冻结的几何来源和关节变换重新计算名义距离，并报告来源与模型
限制。

### 4.1.1 允许分析的构件对

未来实施最多允许分析下列 pair。旋翼盘仅为 `ANALYSIS_PROXY_ONLY`，
不是硬件验证几何。

- 各腿结构 link 与各旋翼盘 `ANALYSIS_PROXY_ONLY`
- `left_sensor_pod` / `right_sensor_pod` 与腿部 coxa / femur / tibia links
- 腿部 links 与机身
- 腿部 links 与固定六旋翼骨架 / 机臂
- 不同腿之间的 link pairs
- 站立姿态到 `analysis_stowed` 路径上的上述构件对

只能分析正式清单中的 pair。pair 的包含和排除必须显式记录。不得静默
排除相邻构件或碰撞对。未声明的 pair 或 proxy 必须失败关闭。不得加入
任务舱释放、推进、载荷轨迹、飞控或危险动作。

### 4.2 G1.5

G4-D0 不改变 G1.5 数学或报告合同。

保持：

- `overall_propulsion_feasibility: UNDETERMINED`
- 能量–质量闭合只是条件电池反馈解，不是整机质量闭合，不是可飞结论
- 7.16 / 12 / 16 kg 只是整体非电池规划边界，不是部件证据
- 不启动 Gazebo / RViz / PX4 作为本阶段授权

### 4.3 G2

G4-D0 的分析主题直接来自 G2 已记录缺口，而不是新的飞行或收拢阶段。

G2 正式标记：

- `SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF`
- `analysis_stowed` 的证据状态是 `UNQUALIFIED_ANALYSIS_POSE`
- `stow_requirements_status: INCOMPLETE`
- `robust_geometry_status: UNDETERMINED`
- `geometry_uncertainty_allowance_m: null`
- `mass_ledger_status: INCOMPLETE`
- `overall_architecture_feasibility: UNDETERMINED`
- 当 `R != 0.30 m` 时 `UNMODELED_ARM_EXTENSION_MASS`

G2 默认站立到 `analysis_stowed` 使用关节空间线性插值、101 个采样点。未采样的
中间构型、连续时间轨迹、以及站立以外的其它折叠方式都没有被穷尽。G4 若在未来
获准实施，也不得把更密的采样写成完整构型空间证明，除非该后续合同明确改变
证明声明，并且仍保持失败关闭。

G4-D0 不改变 G2 数学、候选矩阵生成规则或报告合同。

### 4.4 G3

G3 生产姿态在本合同中保持原值，不得被本文件改写为已闭合：

- `requirements_total = 48`
- `requirements_specified = 23`
- `requirements_incomplete_specification = 25`
- `requirements_verified = 0`
- `requirements_satisfied = 0`
- `sufficient_evidence_requirement_ids = 0`
- `overall_system_readiness = UNDETERMINED`
- `readiness_gate = UNDETERMINED_REQUIREMENTS`
- `procurement_allowed = false`
- evidence levels: `MISSING=52`, `PLANNING_ASSUMPTION=14`,
  `VENDOR_DECLARED=0`, `MEASURED=0`, `TEST_VALIDATED=0`

G3 最高可能结局仍是 `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`。当前 **未达到**。
G4-D0 不得把自身解释成该门控已满足，也不得用本合同去跳过
`UNDETERMINED_REQUIREMENTS`、`UNDETERMINED_EVIDENCE`、
`UNDETERMINED_MASS_LEDGER`、`UNDETERMINED_GEOMETRY_UNCERTAINTY`、
`UNDETERMINED_STOW_REQUIREMENTS` 或 `UNDETERMINED_ARM_MASS_COUPLING`。

G3 正式测试全部保持 `NOT_PERFORMED`。G4-D0 不把任何测试标为已执行。

### 4.4.1 候选追溯

未来候选追溯对象仅限：

- `SYS-STOW-001`～`SYS-STOW-011`
- `SYS-GEO-001`～`SYS-GEO-004`
- `SYS-SAFE-001`～`SYS-SAFE-005`
- `SYS-TRACE-001`～`SYS-TRACE-003`

G4-D0 不修改 G3 YAML。候选追溯不等于需求已验证或已满足。G4 离线结果
不能单独把任何需求升级为 `verified` 或 `satisfied`，也不能单独升级成
`VENDOR_DECLARED`、`MEASURED` 或 `TEST_VALIDATED`。是否可登记为任何
正式证据，必须经过未来独立证据审查。G3 的双向 requirement↔evidence、
requirement↔test 规则继续适用。

---

## 5. 目标

G4-D0 的 **唯一目标** 是定义未来离线构型空间分析的合同边界。

本合同文本已通过审核。未来单独批准的实施子阶段（当前 **未批准**）的分析目标仅限：

1. 在不修改 G1 拓扑的前提下，深化站立姿态与 `analysis_stowed` 之间、以及
   README 已记录干涉附近的离线几何/扫掠/自碰撞分析。
2. 继续把离散采样结果标记为非完整构型空间证明。
3. 将 README 中约 1 mm / 约 2 cm 记录仅作为
   `BASELINE_REPORTED_ESTIMATE_ONLY` 的待复核基线观察 / 回归提示，
   并从冻结几何与关节变换重新计算名义距离；不冻结结构。
4. 保持质量账本、稳健几何、收拢硬件和机臂质量耦合为
   `INCOMPLETE` / `UNDETERMINED`，直到存在真实硬件证据。
5. 输出仍为 ANALYSIS_ONLY，不得产生采购、可飞、合格收拢或结构冻结结论。

G4-D0 本身不实现上述 1–5 项计算。

---

## 6. 输入

G4-D0 作为合同文本，输入仅为已合并的只读基线：

- G1 `arachne_hx6_description` 数字骨架（只读）
- G1.5 `propulsion_scenarios.yaml` 与推进报告合同（只读，不改数学）
- G2 `architecture_envelope.yaml` 与架构报告合同（只读，不改数学）
- G3 四份 YAML 合同与 `docs/G3_REQUIREMENTS_EVIDENCE_GATES.md`（只读）
- README 已知限制中约 1 mm、约 2 cm 的记录，状态为
  `BASELINE_REPORTED_ESTIMATE_ONLY`；只允许作为待复核的基线观察 /
  回归提示，不是测量值、验证值、公差、安全阈值或求解器权威输入

未来若单独批准分析实施，允许读取、不允许在该实施中修改的输入还包括：

- G1 关节限制与站立姿态
- G2 `analysis_stowed` 关节值，仅作为 `UNQUALIFIED_ANALYSIS_POSE`
- G2 规划桨径网格与电机半径网格
- G2 capsule / 有面积水平圆盘 / 参数化盒体几何表示
- G2 认证距离求解容差合同（`<= 1e-9 m` 的既有误差界不得被放宽为未证明精度）

禁止作为本阶段输入或填补值：

- 猜测的毫米公差或 `geometry_uncertainty_allowance_m`
- 猜测的 kg/m 机臂质量
- 把 URDF 占位质量、G1.5 规划边界或分析输出写成 `VENDOR_DECLARED` 或 `MEASURED`
- 供应商选型表、采购报价、未批准的硬件清单
- Gazebo / PX4 / 实机传感器流

---

## 7. 输出

### 7.1 G4-D0 允许的输出

本子阶段唯一允许的输出是本文件：

`docs/G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md`

以及后续若经明确要求而产生的 git commit / PR 元数据。本文件写入仓库 **不等于**
G4 已实施。

### 7.2 未来实施子阶段若被单独批准，才允许讨论的输出

下列输出 **未被 G4-D0 授权生成**：

- 新的分析模块、CLI、YAML 或测试
- JSON / CSV / Markdown 构型空间报告
- 对 G1 URDF 的任何写回
- 把 `analysis_stowed` 写回 `standing_pose.yaml`

若未来单独批准实施，报告仍必须携带：

- `ANALYSIS_ONLY`
- `NOT_FOR_PROCUREMENT`
- `procurement_allowed: false`
- `SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF`
  或更严格的未穷尽声明
- `stow_pose_evidence_status: UNQUALIFIED_ANALYSIS_POSE`，除非硬件验证证据
  已按 G3 规则存在（当前不存在）

JSON / CSV / Markdown 若被未来子阶段授权，必须作为三件套一致写入，失败关闭。
空值保持 `null` / 空 / `—`，不得当作 0。三件套必须来自同一个内存结果对象；
集合、计数、状态和 `limitation_reasons` 必须一致。本次 G4-D0 不实现这些
格式或字段。

### 7.3 未来结果记录字段合同

状态字段必须按层级分离。单样本字段、样本集合字段和构型空间字段不得
混用枚举。

#### 7.3.1 每个离散样本记录

每条未来离散样本结果至少必须包含：

- `sample_id`
- `source_state_or_path`
- `evaluated_pair`
- `joint_values`
- `geometry_source`
- `proxy_status`
- `hardware_validation_status`
- `nominal_separation_or_intersection`
- `result_status`
- `limitation_reasons`

同时明确：

- `sample_id` 非空且唯一
- `joint_values` 必须使用正式 joint 标识和单位
- 数值必须有限
- `nominal_separation_or_intersection` 缺失时不得写成 0
- JSON / CSV / Markdown 必须来自同一个内存结果对象
- 三件套集合、计数、状态和 `limitation_reasons` 必须一致
- 本次 G4-D0 不实现这些格式或字段

每个样本的 `result_status` 只允许：

- `SAMPLED_INTERSECTION_DETECTED`
- `NO_INTERSECTION_AT_EVALUATED_SAMPLE`

定义：

- `SAMPLED_INTERSECTION_DETECTED`：当前有效离散样本的已声明构件对发生
  代理几何相交。
- `NO_INTERSECTION_AT_EVALUATED_SAMPLE`：只表示当前这个有效离散样本未
  发现相交，不表示其它样本或连续路径。
- 输入或模型无效时不得生成上述两种肯定性样本结果。

`proxy_status` 必须为 `ANALYSIS_PROXY_ONLY`。
`hardware_validation_status` 必须为 `NOT_HARDWARE_VALIDATED`。
这两个是限定标签，不得写入 `result_status`。

#### 7.3.2 样本集合摘要

未来三件套必须包含独立字段：

- `sample_set_status`
- `configuration_space_status`

`sample_set_status` 只允许：

- `SAMPLED_INTERSECTION_DETECTED`
- `NO_INTERSECTION_IN_EVALUATED_SAMPLES`
- `UNDETERMINED_GEOMETRY_MODEL`
- `UNDETERMINED_MISSING_INPUT`

聚合优先级必须按下列顺序，不得重排或跳过：

1. 任一必需输入缺失 → `UNDETERMINED_MISSING_INPUT`
2. 任一必需几何来源、代理或模型无效/不一致 →
   `UNDETERMINED_GEOMETRY_MODEL`
3. 全部必需输入和模型有效，且任一有效样本发现相交
   → `SAMPLED_INTERSECTION_DETECTED`
4. 全部必需输入和模型有效，样本集非空，且所有有效样本均未发现相交
   → `NO_INTERSECTION_IN_EVALUATED_SAMPLES`

不得因部分有效样本产生肯定性集合结论而掩盖其它无效输入。

对于任何有限离散采样，本合同下
`configuration_space_status` 必须保持为
`UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE`。
它不能被 `NO_INTERSECTION_IN_EVALUATED_SAMPLES` 覆盖。

---

## 8. 门控

### 8.1 G4-D0 自身门控

G4-D0 通过的唯一含义是：本合同文件被独立审核接受为合同文本。

G4-D0 通过 **不会** 打开：

- G4 分析代码实施
- G3 `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`
- `procurement_allowed`
- Gazebo / PX4 / 飞控
- G1 拓扑修改
- 实体组装

### 8.2 继承的失败关闭就绪门控（G3，保持有效）

优先级保持 G3 定义，不得重排或跳过：

1. `UNDETERMINED_REQUIREMENTS`
2. `UNDETERMINED_EVIDENCE`
3. `UNDETERMINED_MASS_LEDGER`
4. `UNDETERMINED_GEOMETRY_UNCERTAINTY`
5. `UNDETERMINED_STOW_REQUIREMENTS`
6. `UNDETERMINED_ARM_MASS_COUPLING`
7. `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`

当前生产配置停在第 1 项。G4-D0 不得宣称已离开该门。

### 8.3 继承的 G2 联合门控（保持有效）

允许的架构门仍仅为：

- `REJECTED_GEOMETRY`
- `REJECTED_ENERGY_CLOSURE`
- `UNDETERMINED_MASS_LEDGER`
- `UNDETERMINED_MODEL_LIMITATION`

名义间隙门与稳健间隙门保持分离。`geometry_uncertainty_allowance_m` 为 `null`
时，每个间隙的 `robust_gate` 保持
`UNDETERMINED_UNQUANTIFIED_GEOMETRY_UNCERTAINTY`。

### 8.4 证据充分性（保持 G3 规则）

`SPECIFIED` 表示条款已写，不是 verification，也不是 satisfaction。

Evidence is sufficient only when every required evidence item is
`VENDOR_DECLARED`, `MEASURED`, or `TEST_VALIDATED`.

The following are **not** sufficient:

- no required evidence IDs
- every required item is `MISSING`
- every required item is `PLANNING_ASSUMPTION`
- a mixed set that still contains `MISSING` and/or `PLANNING_ASSUMPTION`
- any other level outside the hardware-sufficient set

`PLANNING_ASSUMPTION` cannot increase `requirements_verified` or
`requirements_satisfied`. Evidence levels cannot auto-upgrade.

Requirement-evidence and requirement-test links remain bidirectional.
Orphan evidence, orphan tests, or `traceability_status != CONSISTENT`
cannot open `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`.

### 8.5 禁止的官方状态词

正式状态枚举不使用：

- `VIABLE`
- `FLYABLE`
- `SAFE_TO_FLY`
- `PROCUREMENT_READY`
- `RECOMMENDED_FOR_PURCHASE`
- `VALIDATED_HARDWARE`
- `STOWED_PASS`
- `VALID_STOWED_POSE`

G4-D0 自身也不得使用这些词作为结论。不得使用 `collision-free system`
或 `safe configuration space` 作为正式结论。

### 8.6 G4 正式结果状态词

未来 G4 离线结果只允许使用下表。每个状态词只允许写入其适用字段。
本次 G4-D0 不实现求解器或报告生成。

| 状态词 | 适用字段/层级 | 含义边界 |
|---|---|---|
| `SAMPLED_INTERSECTION_DETECTED` | 单样本 `result_status` 或有效样本集合 `sample_set_status` | 当前有效离散样本的已声明构件对发生代理几何相交；或全部必需输入和模型有效且任一有效样本发现相交 |
| `NO_INTERSECTION_AT_EVALUATED_SAMPLE` | 仅单样本 `result_status` | 只表示当前这个有效离散样本未发现相交，不表示其它样本或连续路径 |
| `NO_INTERSECTION_IN_EVALUATED_SAMPLES` | 仅 `sample_set_status` | 全部必需输入和模型有效、样本集非空，且所有有效样本均未发现相交 |
| `UNDETERMINED_GEOMETRY_MODEL` | 仅 `sample_set_status` | 几何模型不足以支持肯定性结论 |
| `UNDETERMINED_MISSING_INPUT` | 仅 `sample_set_status` | 必需输入缺失 |
| `UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE` | 仅 `configuration_space_status` | 未采样构型仍未确定；任何有限离散采样下必须保持成立 |
| `ANALYSIS_PROXY_ONLY` | 仅 `proxy_status` | 所用几何仅为分析代理，不是硬件几何 |
| `NOT_HARDWARE_VALIDATED` | 仅 `hardware_validation_status` | 结果未经硬件验证 |

`NO_INTERSECTION_AT_EVALUATED_SAMPLE` 和
`NO_INTERSECTION_IN_EVALUATED_SAMPLES` 都不能表示连续构型空间安全、
硬件安全、收拢合格、结构可制造、可飞或可采购。
`NO_INTERSECTION_IN_EVALUATED_SAMPLES` 不能覆盖
`configuration_space_status` 的
`UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE`。

### 8.7 明确的失败关闭条件

下列任一情况必须拒绝生成肯定性结果，返回第 8.6 节中与失败原因对应的
具体 `UNDETERMINED_MISSING_INPUT` 或 `UNDETERMINED_GEOMETRY_MODEL`，
或者在生成任何正式结果前以明确输入错误终止。
不得用默认值静默绕过。

禁止把未列入合同的通用 `UNDETERMINED` 字符串序列化为正式状态。
禁止用 `NO_INTERSECTION_*` 表示未计算、缺失或模型无效。

- 必需输入缺失
- 非有限数值
- 单位缺失
- 未知 joint / link
- 几何来源不一致
- 未声明的 analysis proxy
- 未声明的 evaluated pair
- 空样本集
- `sample_id` 空白或重复
- JSON / CSV / Markdown 三件套不一致
- G1 基线 SHA 与批准值不一致
- 使用未批准的猜测值
- 将 `null` 当作 0
- 试图修改 G1 或向 G1 写回结果

JSON / CSV / Markdown 必须先写入临时位置。三件套全部生成后进行集合、
计数、状态、字段和 `limitation_reasons` 交叉验证。只有全部验证通过后，
才能作为一个整体发布。任一生成或验证失败时，不得留下部分更新的正式
文件；必须清理临时文件。若已有上一套完整正式报告，失败时必须保留上一
套，不得形成新旧混合集。本合同只定义规则，G4-D0 不实现写入代码。

---

## 9. 禁止事项

G4-D0 以及任何尚未单独批准的后续 G4 子阶段，必须继续排除：

- 修改 `procurement_allowed`
- 采购或选购实体执行机构、电机、ESC、螺旋桨、电池、飞控或传感器
- 实体组装、结构冻结
- 自由飞行、自推进、穿透、投射、毁伤、武器化控制链
- 弹药、瞄准、伤害功能
- 把 `sensor_pod` 写成可发射或打击装置
- 视觉或感知输出直接连接任何危险动作
- 接入或声称 Gazebo 动力学、PX4、实时飞控或可飞控制器
- 修改已合并 G1 identifiers、joints、topology、mesh、collision、inertial
  或站立姿态
- 改变 G1.5 或 G2 数学或报告合同
- 把名义几何通过写成稳健通过
- 把条件能量闭合写成整机质量闭合或可飞
- 把 `analysis_stowed` 写成合格或通过的收拢姿态
- 用猜测值填补质量、公差、收拢限值或机臂线密度
- 把本合同写成已批准的分析实施
- 在 `main` 上直接实施下一阶段
- 运行 RViz、Gazebo、PX4 或实体设备作为本子阶段工作
- 新增代码、YAML、测试或生成报告（G4-D0）

---

## 10. 明确排除、不得纳入最小 G4 实施的项目

即使未来有独立门控批准 G4 分析代码，下列项目仍 **不得** 被本 G4-D0 合同偷偷纳入：

- 19 项质量账本称重或供应商数据填写
- 推进台架 `TEST-PROP-001`
- CAD 公差、装配误差、挠度、挥舞的实测填入
- 折叠锁定机构硬件、锁载荷、收拢包络实测
- 发明 kg/m 的机臂延伸质量模型
- 电池、母线、可用能量分数的硬件替换
- 飞控 / 导航 / 载荷传感器选型
- walk/flight 模式切换的控制实现
- 任何把 25 条 `INCOMPLETE_REQUIREMENT` 用“合理猜测值”填满的做法

这些项目仍受 G3 失败关闭约束。关闭它们需要硬件充分证据和独立门控，不是 G4-D0
的范围。

---

## 11. 建议的未来实施范围（仅备忘，未批准）

下列内容只是合同备忘，**implementation_allowed: false**。不得据此开始编码。

若未来独立批准一个 G4 分析实施子阶段，最小分析范围应不超过：

1. 离线、只读使用 G1 运动学与 G2 几何原语。
2. 加密或扩展站立到 `analysis_stowed` 的采样，或增加扫掠体 / 自碰撞记录。
3. 将 README 约 1 mm / 约 2 cm 记录仅作为
   `BASELINE_REPORTED_ESTIMATE_ONLY` 待复核基线观察 / 回归提示，
   并从冻结几何重新计算名义距离。
4. 每个字段只能使用第 8.6 节为该字段规定的枚举；不得输出禁止状态词。
5. 不写回 URDF；不改 G1.5/G2/G3 合同文件；不改 `procurement_allowed`。

该备忘不是实施授权。

---

## 12. 分支、PR 与审核

- G4-D0 必须在独立 feature 分支上起草，不得在 `main` 上直接修改。
- 本合同的审核结论只能是：接受合同文本、要求修改合同文本、或拒绝。
- 接受本合同 **不等于** 批准分析代码 PR。
- 若需实施，必须另开独立分支和独立 PR，并再次通过明确的实施授权。
- 不在本子阶段 commit、push 或创建 PR，除非调用方另给明确指令。

未来开始任何 G4 代码实施前，必须再次独立批准，并全部满足：

- G4-D0 合同已经审核并合并到 `main`
- `main` 工作区干净并与 `origin/main` 同步
- G1 输入基线 commit SHA 已明确冻结
- 允许修改的文件集合已经逐项列出
- 输入、输出、状态词和失败关闭规则已经批准
- 允许的构件对和代理清单已经批准
- 不修改 G1、G1.5、G2、G3 合同
- `procurement_allowed` 仍为 `false`
- `implementation_allowed` 只能由新的明确指令改变
- 未经该门控不得创建 G4 分析代码、YAML、测试或报告生成器

---

## 13. 本合同的验收标准（仅针对合同文本）

GPT 审核本合同文本时，应确认：

1. 顶部状态块完整，且 `implementation_allowed: false`、
   `procurement_allowed: false`、`gazebo_allowed: false`、
   `px4_allowed: false`、`hardware_assembly_allowed: false`。
2. 明确写有：G4-D0 是合同文本已通过审核；G4 未实施；G3 证据门未闭合。
3. 阶段名称、目标、输入、输出、门控、禁止事项均已定义。
4. G1 拓扑不变式、G1.5/G2 数学不变式、G3 失败关闭门控均被继承。
5. 未把候选分析写成已批准实施。
6. 除本文件外无其它仓库修改。

---

## 14. 当前仓库姿态快照（合同引用，非新计算）

本合同引用 G3 合并后的正式姿态，不重新计算、不生成报告：

| 项 | 值 |
|---|---|
| 正式 HEAD（合同基线） | `033bc83d5c00805ff31e6f01f6b8243727f5e350` |
| G3 文档 | `docs/G3_REQUIREMENTS_EVIDENCE_GATES.md` |
| `overall_system_readiness` | `UNDETERMINED` |
| `readiness_gate` | `UNDETERMINED_REQUIREMENTS` |
| `procurement_allowed` | `false` |
| G3 最高可能门控 | `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`（未达到） |
| G2 构型空间声明 | `SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF` |
| `analysis_stowed` | `UNQUALIFIED_ANALYSIS_POSE` |

---

**End of the GPT-approved G4-D0 contract text.**
**Approval scope is contract text only. G4 analysis implementation remains prohibited.**
