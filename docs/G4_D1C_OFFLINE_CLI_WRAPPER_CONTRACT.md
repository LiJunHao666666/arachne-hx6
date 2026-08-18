# G4-D1C Offline CLI Wrapper Contract

```text
contract_status: GPT_APPROVED_CONTRACT_TEXT
contract_approval_scope: CONTRACT_TEXT_ONLY
project_status: ANALYSIS_ONLY
implementation_allowed: false
procurement_allowed: false
hardware_assembly_allowed: false
gazebo_allowed: false
px4_allowed: false
```

**ANALYSIS_ONLY**
**NOT_FOR_PROCUREMENT**
**NOT_AN_IMPLEMENTATION_AUTHORIZATION**
**NOT_A_CLI_REGISTRATION_AUTHORIZATION**
**NOT_A_REPORT_GENERATION_AUTHORIZATION**
**NOT_A_D1D_AUTHORIZATION**

This document is the GPT-approved G4-D1C contract text for Arachne-HX6.
Approval is limited to the contract text. It does not
authorize implementation, CLI registration, report generation, procurement,
physical assembly, Gazebo, PX4, D1A evaluator changes, D1B report-core
changes, or D1D.

本文件是已经通过 GPT 审核的 G4-D1C 合同文本。批准范围
仅限合同文本。本合同文本不授权实施、CLI 注册、报告生成、采购、硬件、
Gazebo、PX4、D1A 求值器修改、D1B 报告核心修改或 D1D。

---

## 1. 阶段名称

- **阶段族：** G4 Offline Configuration-Space Analysis（离线构型空间分析）
- **本文件对应子阶段：** **G4-D1C 离线 CLI 包装层合同定义**
- **官方文件名：** `docs/G4_D1C_OFFLINE_CLI_WRAPPER_CONTRACT.md`
- **建议分支：** `feature/g4-d1c-offline-cli-contract`
- **本子阶段允许的工作：** 仅起草并审查本合同
- **本子阶段禁止的工作：** 任何分析代码、YAML、测试、CLI 注册、报告生成、
  URDF 修改、仿真、采购，或进入 D1D

Future implementation, if independently approved, may use only:

```text
implementation_scope: G4_D1C_OFFLINE_CLI_WRAPPER_ONLY
```

That scope string is frozen by this contract. It is not authorized by
accepting this file.

---

## 2. 本文件是什么，以及不是什么

G4-D1C **是：**

- 一份 ANALYSIS_ONLY 工程合同文本
- 对已合并 G4-D1A 内存求值器和已合并 G4-D1B 报告三件套写入器的
  **离线 CLI 包装层** 边界定义
- 对未来（尚未批准的）CLI 入口、参数、授权 YAML、退出码、测试和
  文件白名单的书面约束

G4-D1C **不是：**

- G4-D1C 已实施
- CLI 已注册
- 生产报告已授权生成或入库
- D1A 求值器或 D1B 报告核心的修改授权
- D1D 或任何后续子阶段授权
- 采购、选型、下单或结构冻结授权
- 实体组装、Gazebo、PX4、飞控或可飞结论授权
- 把有限采样写成完整构型空间证明的授权
- 把 G4 结果升级为 G3 硬件证据的授权

G4-D1A 与 G4-D1B 已经合并到 `main`。它们排除 CLI，但没有定义名为 D1C
的正式合同。本合同填补该缺口。填补缺口不等于批准包装层代码。

---

## 3. 永久边界（继承，不可被本合同放宽）

Arachne-HX6 remains simulation-first and non-weaponized. Official work is
limited to disaster response, environmental sensing, hazardous-area
inspection, and non-weaponized reconnaissance / remote inspection.

本合同保持并继承：

- `project_status: ANALYSIS_ONLY`
- `procurement_allowed: false`
- `implementation_allowed: false`（G4-D1C 合同文本阶段）
- `hardware_assembly_allowed: false`
- `gazebo_allowed: false`
- `px4_allowed: false`
- G4-D0 合同文本及其失败关闭规则
- G4-D1A `implementation_scope: G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY`
- G4-D1B `implementation_scope: G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY`
- D1A YAML 与 D1B YAML 中的 `cli_registration_allowed: false` **不得修改**
- 非武器化；不授权采购、实体组装、自由飞行或危险动作链
- 不修改已合并 G1 URDF / Xacro / link / joint / 拓扑
- 有限离散采样下 `configuration_space_status` 必须保持
  `UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE`

Completing G4-D0, G4-D1A, or G4-D1B does **not** automatically authorize
G4-D1C implementation. Accepting this contract text also does **not**
authorize implementation.

---

## 4. 与 G4-D0 / D1A / D1B 的关系

### 4.1 G4-D0

G4-D0 仍是阶段族合同。G4-D0 的 `implementation_allowed: false` 是历史
合同字段，本合同不得改写 G4-D0 文件。G4-D0 §12 要求每个新的 G4 实施
子阶段独立批准。G4-D1C 实施（若发生）必须满足该独立门控。

G4-D0 §7.2 允许未来讨论「新的分析模块、CLI、YAML 或测试」。那是备忘，
不是 D1C 实施授权。本合同是 CLI 包装层的已审核合同文本；在
另发实施授权之前，CLI 仍禁止。

### 4.2 G4-D1A

已合并的五个 D1A 文件保持只读冻结（对本合同和实施候选均不得修改）：

1. `src/arachne_hx6_analysis/config/configuration_space.yaml`
2. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_types.py`
3. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_registry.py`
4. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_evaluate.py`
5. `src/arachne_hx6_analysis/test/test_configuration_space.py`

D1A 只授权内存求值。`report_file_generation_allowed` 与
`cli_registration_allowed` 必须保持 `false`。未来 CLI 可以**调用**
`load_configuration_space_config` 和 `evaluate_configuration_space`，
但不得复制或重写求值器、注册表或几何算法，也不得向求值器增加
`file_bytes`、隐藏采样缩减或写文件 API。

### 4.3 G4-D1B

已合并的六个 D1B 文件中，五个生产模块/YAML 保持只读冻结：

1. `src/arachne_hx6_analysis/config/configuration_space_report.yaml`
2. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report.py`
3. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report_payload.py`
4. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report_csv.py`
5. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_report_markdown.py`

D1B 测试文件是候选允许修改的**唯一** D1B 文件，见第 5.2 节。不得修改
D1B 生产模块或 YAML。

D1B 只授权从已有 `ConfigurationSpaceResult` 生成 JSON/CSV/Markdown
三件套。D1B YAML 注释与测试明确排除 CLI 注册。未来 CLI 可以**调用**
`write_configuration_space_reports`，但不得复制或重写渲染器、交叉验证
或 process-local all-or-rollback 算法。

D1B YAML 的 `cli_registration_allowed: false` 必须保持。该字段表示
**D1B 本层不授权 CLI**，不是禁止未来独立 D1C 包装层存在。打开包装层
不得通过把该字段改为 `true` 实现。

---

## 5. 冻结的未来实施文件白名单

若未来独立批准 G4-D1C 实施，允许的仓库变更恰好为下列集合。不得扩大。

### 5.1 候选新增文件（恰好三个）

1. `src/arachne_hx6_analysis/config/configuration_space_cli.yaml`
2. `src/arachne_hx6_analysis/arachne_hx6_analysis/configuration_space_cli.py`
3. `src/arachne_hx6_analysis/test/test_configuration_space_cli.py`

### 5.2 候选修改既有文件（恰好两个）

1. `src/arachne_hx6_analysis/setup.py`
2. `src/arachne_hx6_analysis/test/test_configuration_space_report.py`

### 5.3 为何必须修改 D1B 测试文件

当前 D1B 测试 `test_no_cli_or_argparse_in_d1b_modules` 断言
`setup.py` 的 `console_scripts` 段不含 `configuration_space`。该断言把
**包装层入口尚未存在** 误写成 **D1B 永久冻结条件**。

未来 D1C 若注册唯一批准入口，过宽断言会失败，但它检验的不是 D1B
报告完整性。因此该测试必须收窄，而不是删除 D1B 防护：

- 不得保留“`console_scripts` 不含 `configuration_space`”的过宽断言
- 删除或改写“四个报告模块不包含 CLI”这种字面字符串要求
- 冻结为对四个 D1B 报告模块的 AST/结构检查：
  - `configuration_space_report.py`
  - `configuration_space_report_payload.py`
  - `configuration_space_report_csv.py`
  - `configuration_space_report_markdown.py`
  - 不 `import argparse`
  - 不存在模块级函数 `main`
  - 不存在 `if __name__ == '__main__'`
  - 不实例化 `argparse.ArgumentParser`
  - 不注册或声明 `console_scripts` 入口
  - 不把 CLI 参数解析加入 D1B 模块
- 允许源码继续包含：
  - `cli_registration_allowed`
  - “No CLI”文档文字
  - 授权元数据中的 CLI 字段
- D1B AST 收窄测试不得因合法的 `cli_registration_allowed` 或
  “No CLI”文本误报
- `setup.py` 的唯一新入口改由 **D1C 测试**精确验证：
  - 恰好新增一个
    `configuration_space_report = arachne_hx6_analysis.configuration_space_cli:main`
  - 既有三个入口不变
  - 无第二个 G4 CLI 入口
- `setup.py` 不再作为 D1B 永久冻结文件
- 不得削弱 D1B 的报告完整性、回滚、安全字段或无自动写入测试

This test-file edit is a boundary correction. It is not permission to
change D1B production modules, YAML, rollback, or safety fields.

### 5.4 明确不得修改

未来 D1C 实施不得修改：

- `src/arachne_hx6_analysis/package.xml`
- `README.md`
- `docs/G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md`
- 全部五个 D1A 文件
- D1B 五个生产模块/YAML（第 4.3 节）
- G1 / G1.5 / G2 / G3 文档、YAML、代码或测试
- 任何 URDF / Xacro
- 任何其它既有文件

`package.xml` 不是 ament_python `console_scripts` 的注册面，因此不在
最小白名单内。README 更新不是 CLI 功能前置，排除出最小 D1C。

---

## 6. 目标

G4-D1C 合同文本的 **唯一当前目标** 是定义未来离线 CLI 包装层边界。

本合同本身不实现 CLI。未来单独批准的实施子阶段（当前 **未批准**）
的唯一分析目标是：

1. 提供一个离线、显式参数的 CLI 包装层。
2. 从 `--configuration-space-cli-yaml` 加载独立 D1C 授权 YAML。
3. 原样调用 D1A 配置加载和求值器。
4. 将返回的 `ConfigurationSpaceResult` 原样交给 D1B 写入器。
5. 返回规定退出码。
6. 不复制求值、注册表、几何、渲染、交叉验证或回滚逻辑。
7. 不默认写入仓库，不提交生成报告，不进入 D1D。

---

## 7. 输入

G4-D1C 作为合同文本，输入仅为已合并只读基线：

- G4-D0 合同
- 已合并 G4-D1A 五文件
- 已合并 G4-D1B 六文件
- 现有 G1.5 / G2 / G3 CLI 先例（参数与退出码参考，不是要复制其
  可省略 config 路径的宽松默认）
- 当前 `setup.py` 的三个既有 `console_scripts` 入口

未来实施若被单独批准，CLI 运行时输入必须由调用方显式提供，见第 8 节。
禁止把仓库内默认路径、cwd、`src/`、`build/`、`install/` 或 share
当作隐式输出位置。

---

## 8. CLI 固定边界

### 8.1 唯一候选入口

未来实施若被批准，`setup.py` 的 `console_scripts` 只允许新增这一条：

```text
configuration_space_report = arachne_hx6_analysis.configuration_space_cli:main
```

既有入口必须保持不变：

- `propulsion_report = arachne_hx6_analysis.cli:main`
- `architecture_report = arachne_hx6_analysis.architecture_cli:main`
- `requirements_report = arachne_hx6_analysis.requirements_cli:main`

不得注册第二个 G4 入口，不得把入口放到 D1A 或 D1B 模块里。

### 8.2 五个全部 required 的参数

```text
--approved-root
--output-dir
--configuration-space-cli-yaml
--configuration-space-yaml
--configuration-space-report-yaml
```

全部 required。禁止默认值。禁止默认输出目录。禁止默认写入仓库、cwd、
`src/`、`build/`、`install/` 或 share。

G1.5 / G2 / G3 CLI 允许省略部分 config 路径。G4-D1C **不得**模仿该宽松
行为。G4 依赖冻结 `approved_root` 与三份显式 YAML（D1C 授权、D1A 配置、
D1B 报告授权），缺省路径会把求值或写入绑到源码树。

### 8.3 CLI 只允许做的四步

1. 从 `--configuration-space-cli-yaml` 加载独立 D1C 授权 YAML（第 9 节），
   并在开始 D1A 求值之前完成全部授权校验与 D1A/D1B YAML 交叉核对。
2. 原样调用 D1A 配置加载和求值器，使用调用方提供的
   `--approved-root` 与 `--configuration-space-yaml`。
3. 将 `ConfigurationSpaceResult` 原样交给 D1B 写入器，使用调用方提供的
   `--output-dir` 与 `--configuration-space-report-yaml`。
4. 返回退出码。

CLI 不得：

- 复制或重写求值器、注册表、几何算法、报告渲染器、交叉验证或回滚
- 修改 D1A / D1B YAML 字段
- 向结果对象写入覆盖后的安全字段
- 提供隐藏 `--test` 参数或降低采样规模
- 新增时间戳命令行参数
- `configuration_space_cli.py` 不得直接对三个正式 basename 调用 `open`、
  `write_text`、`write_bytes`、`os.replace`、`unlink` 或自行实现
  staging/backup。正式三件套的创建、替换、删除新生部分文件和恢复旧
  三件套，只能由已合并 D1B `write_configuration_space_reports` 执行。
  CLI 调用 D1B 后产生正式三件套属于批准候选行为，不与上述禁止冲突。

测试需要确定时间时，可在模块内部使用可注入 `clock` / helper。这不是
命令行标志，不得降低 101×162 生产采样规模。

### 8.4 输出

CLI 成功时的唯一文件系统输出是 D1B 写入器在调用方 `--output-dir` 中
发布的正式三件套。该三件套不得被 git add、commit 或作为仓库产物提交。

失败时 CLI 不得自行写任何正式文件。回滚语义全部委托 D1B。
正式三件套若产生，只能来自已合并 D1B `write_configuration_space_reports`。

---

## 9. 授权层级

未来 D1C YAML（`configuration_space_cli.yaml`）顶层恰好包含以下键。
顺序不作为语义，但不得缺失或增加未知键：

```text
status: ANALYSIS_ONLY
implementation_authorization_status: GPT_AUTHORIZED
implementation_scope: G4_D1C_OFFLINE_CLI_WRAPPER_ONLY
cli_wrapper_registration_allowed: true
source_evaluator_scope: G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY
source_evaluator_cli_registration_allowed: false
source_evaluator_report_file_generation_allowed: false
source_reporter_scope: G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY
source_reporter_cli_registration_allowed: false
source_reporter_report_triplet_generation_allowed: true
procurement_allowed: false
hardware_assembly_allowed: false
gazebo_allowed: false
px4_allowed: false
```

加载规则：

- 未知键 → `InvalidInputError`
- 缺少任一键 → `InvalidInputError`
- scope、status 或授权值不精确匹配 → `InvalidInputError`
- 任一持续禁止字段不为 `false` → `InvalidInputError`
- 两个允许字段不为 `true` → `InvalidInputError`
  （`cli_wrapper_registration_allowed` 与
  `source_reporter_report_triplet_generation_allowed`）
- 必须在开始 D1A 求值之前完成全部授权校验

D1C 加载器还必须把上述 `source_*` 声明与调用方显式提供并实际加载的
D1A/D1B YAML 交叉核对：

- D1A `implementation_scope`、`cli_registration_allowed`、
  `report_file_generation_allowed` 必须匹配
- D1B `implementation_scope`、`cli_registration_allowed`、
  `report_triplet_generation_allowed` 必须匹配
- 任一不一致 → `InvalidInputError`，禁止求值和写报告

不得修改 D1A/D1B YAML。

含义：

- D1C YAML 只授权包装层注册与编排
- D1A 求值器层仍禁止 CLI 注册与报告文件生成
- D1B 报告层仍禁止 CLI 注册，且仍要求三件套生成被允许
- D1A / D1B 原 YAML 的 `cli_registration_allowed: false` 不得修改
- 包装层不得把 D1A `report_file_generation_allowed` 改为 `true`，也不得
  把 D1B `cli_registration_allowed` 改为 `true`
- 任一禁止字段为 `true` 必须失败关闭，不得生成肯定性报告

`cli_wrapper_registration_allowed: true` 只存在于独立 D1C YAML。它不是
把 D1A/D1B 的 `cli_registration_allowed` 翻成 `true`。

---

## 10. 退出码与失败关闭

| 退出码 | 条件 |
|---|---|
| 0 | D1A 求值与 D1B 完整三件套发布成功 |
| 1 | `AnalysisError`、`InvalidInputError`、`OSError`；stderr 单行 `ERROR:`，无 traceback |
| 2 | argparse 参数错误（含缺 required 参数），表现为 `SystemExit(2)` |

失败必须委托 D1B 的 all-or-rollback 机制。CLI 不得自行写任何正式文件。

继续继承，不得放宽：

- `output_dir` 与三个正式 basename 的普通符号链接和悬空符号链接拒绝
- 失败后零正式文件，或保留上一套完整旧三件套；不得留下新旧混合集
- timezone-aware UTC 时间戳；`generated_at` 与 `clock` 不得同时提供
- `configuration_space_status` 恒为
  `UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE`
- 有限采样不是完整构型空间证明，不是硬件安全、收拢合格、可飞或可采购

最小 CLI 不新增时间戳命令行参数。

---

## 11. 测试合同

未来 D1C 测试（仅 `test_configuration_space_cli.py`，外加第 5.2 节对
D1B 测试的收窄）至少覆盖：

- 三文件新增、两文件修改的精确范围；无第七个新文件，无白名单外修改
- 五个 required 参数均存在且无默认输出目录
- 缺任一 required 参数 → `SystemExit(2)`
- 缺 `--configuration-space-cli-yaml` → `SystemExit(2)`
- 合法调用返回 0
- 输入 / 求值 / 写入错误返回 1，stderr 单行 `ERROR:`，无 traceback
- D1C YAML 未知键 / 缺键 / 错误 true/false → 返回 1，求值器未调用
- D1C `source_*` 与实际 D1A/D1B YAML 不一致 → 返回 1，求值器和写入器均未调用
- D1C YAML 禁止字段为 `true` 时失败关闭
- D1A 与 D1B 的 scope / false 字段不得被 CLI 篡改
- CLI 只编排 D1A→D1B，AST 或源码检查证明不复制核心逻辑
- CLI 模块不直接执行正式文件 I/O
- D1B AST 收窄测试不会因合法的 `cli_registration_allowed` 或
  “No CLI”文本误报
- `setup.py` 恰好新增一个批准入口，既有三个入口不变，无第二个 G4 CLI 入口
- 失败不产生部分三件套
- 不生成或提交生产报告到仓库
- 既有 D1A / D1B 功能测试继续通过
- production 16362 记录 / 606 样本集合路径只能作为冻结集成回归，
  不能写入 CLI 通用逻辑，不能用隐藏开关缩短采样

测试应像 G3 CLI 那样直接调用 `main(argv_list) -> int`，而不是依赖
`sys.exit`，也不得增加隐藏 `--test` 参数。

---

## 12. 门控

### 12.1 本合同文本门控

G4-D1C 合同文本通过的唯一含义是：本文件被独立审核接受为合同文本。

该通过 **不会** 打开：

- CLI 实施或 `console_scripts` 注册
- 生产报告生成
- D1A / D1B 核心修改
- D1D
- `procurement_allowed`
- Gazebo / PX4 / 飞控
- G1 拓扑修改

### 12.2 未来实施门控（当前未打开）

开始任何 G4-D1C 代码实施前，必须再次独立批准，并全部满足：

- 本合同已经审核并合并到 `main`
- `main` 工作区干净并与 `origin/main` 同步
- 允许修改的文件集合仍然恰好是第 5 节白名单
- 五个 required 参数、退出码和授权层级已经批准
- 不修改 D1A 五文件、D1B 生产模块/YAML、G4-D0、package.xml、README、
  G1–G3 或 URDF/Xacro
- D1A/D1B `cli_registration_allowed` 仍为 `false`
- `procurement_allowed` 仍为 `false`
- 未经该门控不得创建 D1C YAML、CLI 模块、CLI 测试，也不得修改
  `setup.py`

### 12.3 继承的结果状态词

G4-D0 §8.6 与 D1A/D1B 已冻结的状态词继续适用。CLI 不得引入
`VIABLE`、`FLYABLE`、`SAFE_TO_FLY`、`PROCUREMENT_READY`、
`collision-free system` 或 `safe configuration space` 作为正式结论。

---

## 13. 禁止事项

G4-D1C 合同文本以及任何尚未单独批准的后续实施，必须继续排除：

- 采购或选购实体执行机构、电机、ESC、螺旋桨、电池、飞控或传感器
- 实体组装、结构冻结
- Gazebo、PX4、实时飞控或可飞控制器
- 修改已合并 G1 identifiers、joints、topology、mesh、collision、
  inertial 或站立姿态
- 修改 D1A 求值器、注册表、类型或 D1A YAML
- 修改 D1B 生产报告模块或 D1B YAML
- 把 D1A/D1B `cli_registration_allowed` 改为 `true`
- 自动生成并提交生产报告入库
- 把有限采样写成完整构型空间安全证明
- 把 G4 结果升级为 G3 `verified` / `satisfied` / `MEASURED` /
  `TEST_VALIDATED`
- 在 `main` 上直接实施
- 进入 D1D 或任何未定义的后续子阶段
- 复制核心逻辑到 CLI 模块
- 默认输出目录或默认写入仓库

---

## 14. 明确排除、不得纳入最小 D1C 实施的项目

即使未来有独立门控批准 CLI 包装层，下列项目仍不得被本合同偷偷纳入：

- 新的几何 pair、采样密度或证明声明
- 新的报告格式或 basename
- 时间戳命令行参数
- 隐藏 `--test` 或缩短生产 16362/606 路径的开关
- `package.xml` 或 README 修改
- G4-D0 文本修改
- 把包装层写成 D1A 或 D1B 的一部分
- 硬件证据、采购放行或仿真接入

---

## 15. 分支、PR 与审核

- G4-D1C 合同必须在独立 feature 分支上起草，不得在 `main` 上直接修改。
- 本轮唯一允许的仓库变更是新增本文件。
- 本合同的审核结论只能是：接受合同文本、要求修改合同文本、或拒绝。
- 接受本合同 **不等于** 批准 CLI 代码 PR。
- 若需实施，必须另开独立分支和独立 PR，并再次通过明确的实施授权。
- 不在本子阶段 commit、push 或创建 PR，除非调用方另给明确指令。

---

## 16. 当前仓库姿态快照（合同引用，非新计算）

| 项 | 值 |
|---|---|
| 正式 HEAD（合同起草基线） | `38efaf5adeab0d41cae3f1e4460e20a0acdbd761` |
| 基线提交 | `feat(analysis): add G4-D1B offline report triplet (#7)` |
| G4-D0 | `docs/G4_OFFLINE_CONFIGURATION_SPACE_CONTRACT.md` |
| G4-D1A scope | `G4_D1A_OFFLINE_IN_MEMORY_ANALYSIS_ONLY` |
| G4-D1B scope | `G4_D1B_OFFLINE_REPORT_TRIPLET_ONLY` |
| 现有 `console_scripts` | `propulsion_report`, `architecture_report`, `requirements_report` |
| D1A/D1B `cli_registration_allowed` | `false` |
| `procurement_allowed` | `false` |
| `configuration_space_status` | 有限采样下保持 `UNDETERMINED_UNSAMPLED_CONFIGURATION_SPACE` |

---

## 17. 本合同的验收标准（仅针对合同文本）

GPT 审核本合同文本时，应确认：

1. 顶部状态块完整，且 `implementation_allowed: false`、
   `procurement_allowed: false`、`gazebo_allowed: false`、
   `px4_allowed: false`、`hardware_assembly_allowed: false`。
2. 明确写有：合同文本不授权实施、CLI 注册、报告生成、采购、硬件、
   Gazebo、PX4 或 D1D。
3. 未来 `implementation_scope` 冻结为
   `G4_D1C_OFFLINE_CLI_WRAPPER_ONLY`。
4. 文件白名单恰好为三个新增文件与两个既有文件修改，并解释了 D1B
   测试收窄为 AST/结构检查的必要性。
5. 五个 CLI 参数全部 required；禁止默认输出目录。
6. 授权层级区分 D1C 包装层与 D1A/D1B 原 `cli_registration_allowed=false`，
   且 D1C YAML 精确 schema 与 D1A/D1B 交叉核对已定义。
7. 退出码 0/1/2 与 D1B rollback 委托已定义。
8. 未把候选 CLI 写成已批准实施。
9. 除本文件外无其它仓库修改。

---

**End of the GPT-approved G4-D1C contract text.**
**Approval scope is contract text only. G4-D1C CLI implementation remains prohibited.**
**Do not implement.**
