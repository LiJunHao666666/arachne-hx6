# G2 参数化整机架构包络（ANALYSIS_ONLY）

**ANALYSIS_ONLY**
**NOT_FOR_PROCUREMENT**
**overall_architecture_feasibility: UNDETERMINED**
**SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF**

本文档描述 Arachne-HX6 在 G1 数字骨架与 G1.5 推进可行性之后的离线整机架构包络分析。当前没有真实硬件。所有数值都是可修改的规划输入或由其推导的计算结果，**不得作为采购、选型、结构冻结或下达订单的依据**。本阶段不修改已验收的 G1 URDF / Xacro / 关节命名 / 站立姿态。

G2 **不是**飞行控制阶段。它不接入 PX4、Gazebo、RViz 或任何实时控制器，也不证明可飞、可采购或结构已冻结。

## 为什么增加 8 英寸和 10 英寸

G1.5 只比较了 4.7、12、15 英寸。4.7 英寸接近 G1 视觉桨盘，但在标称能量—质量模型下通常无法闭合；12 / 15 英寸有条件能量闭合，但在 G1 `hex_arm_span = 0.30 m` 上无法满足 20 mm 相邻桨尖间隙。8 英寸与 10 英寸是这两个极端之间的规划中间候选，用来观察桨尖间隙、机身/传感器舱间隙和能量闭合是否可能同时改善。它们仍然只是规划网格，不是最终桨径。

## 几何通过 ≠ 能量通过

相邻桨尖间隙、圆盘—盒体、圆盘—腿段 capsule 的名义 `CLEARANCE_MET` 只回答当前理想名义几何是否低于设定阈值。`geometry_uncertainty_allowance_m` 当前为 `null`（尚无 CAD 公差、装配误差、结构挠度或旋翼挥舞证据），因此每个间隙的 `robust_gate` 为 `UNDETERMINED_UNQUANTIFIED_GEOMETRY_UNCERTAINTY`，顶层 `robust_geometry_status: UNDETERMINED`。名义通过不得自动变成稳健通过。不得用 5 mm 或其他猜测值填补该空缺。

G1.5 能量—质量闭合是另一道门：同一桨径可以几何失败而能量有根，或几何通过而能量无根。联合门控把二者分开记录。

## 条件能量闭合 ≠ 整机质量闭合

G1.5 的 7.16 / 12 / 16 kg 只是整体非电池规划边界。G2 另建部件级质量证据账本。账本中任何 `MISSING` 都使 `mass_ledger_status: INCOMPLETE`。即使几何与条件能量闭合同时成立，只要账本不完整，`architecture_gate` 也只能是 `UNDETERMINED_MASS_LEDGER`。这不是可飞结论，更不是采购就绪。

当 `motor_center_radius_m = 0.30 m` 时，`arm_radius_mass_coupling_status = BASELINE_RADIUS_NO_EXTENSION_MODEL`。当 `R != 0.30 m` 时为 `UNMODELED_ARM_EXTENSION_MASS`，联合行写入 `arm_extension_mass_not_coupled_into_energy_closure`。不得把加长机臂候选仅根据当前 7.16 / 12 / 16 kg 边界写成已完成整机能量闭合；不得发明每米机臂质量。

## 离散腿部路径采样不是完整构型空间证明

站立姿态到 `analysis_stowed` 使用关节空间线性插值，默认 101 个采样点（含两端）。每个采样点检查六条腿的 capsule 与六个有面积水平旋翼圆盘的最小间隙。未采样的中间构型、连续时间轨迹、以及站立以外的其它折叠方式都没有被穷尽。结果标记：

`SAMPLED_TRANSITION_ONLY_NOT_FULL_CONFIGURATION_SPACE_PROOF`

`analysis_stowed` 配置键保留，但正式证据状态是 `UNQUALIFIED_ANALYSIS_POSE`：当前姿态只是向下折叠的一条可计算分析路径，**不是**已验证收拢姿态。`stow_requirements` 的硬件限值全部为 `null`，因此 `stow_requirements_status: INCOMPLETE`。`stow_pose_is_hardware_validated: false`。不得输出 `STOWED_PASS`、`VALID_STOWED_POSE` 或类似结论。该姿态不证明飞行收拢要求、锁定要求或机械可实现性。

## 当前没有真实硬件数据

质量账本默认全部为 `MISSING`，`mass_kg` 为 `null`（JSON）/ 空（CSV）/ `—`（Markdown），禁止用 0 冒充未知质量。不得把 URDF 占位质量、G1.5 规划边界或本分析输出写成 `VENDOR_DECLARED` 或 `MEASURED`。

## 当前不允许采购

顶层保持：

- `status: ANALYSIS_ONLY`
- `procurement_allowed: false`
- `overall_architecture_feasibility: UNDETERMINED`
- `mass_ledger_status: INCOMPLETE`
- `stow_requirements_status: INCOMPLETE`
- `robust_geometry_status: UNDETERMINED`

正式状态枚举不使用 `VIABLE`、`FLYABLE`、`SAFE_TO_FLY`、`PROCUREMENT_READY`、`RECOMMENDED_FOR_PURCHASE`、`VALID_STOWED_POSE`、`STOWED_PASS`。

## 运行

在工作区根目录（示例 `~/arachne_hx6_ws`，可换成实际路径）：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
colcon build --symlink-install --packages-select arachne_hx6_analysis
source install/setup.bash
ros2 run arachne_hx6_analysis architecture_report \
  --output-dir /tmp/arachne_g2_report
```

可选 `--config` 指向自定义 YAML。默认读取包内 `config/architecture_envelope.yaml`。规划候选由程序从直径列表 × 半径列表生成，禁止把结果表硬编码进源码。长度一律用 SI 单位计算；英寸只作输入和显示。

非法输入（布尔冒充数字、整数被截断、NaN/Inf、零桨径、零采样数、重复直径/半径、姿态不是恰好 18 个合法关节、嵌套节点类型错误）会变成 `InvalidInputError`。CLI 在 stderr 输出单行 `ERROR`，退出码 1，不打印 traceback，也不写伪成功报告。

## 几何算法

- 六台电机均布在同一水平圆周，G1 X 构型首臂 +30°。
- 相邻中心距：\(d_{\mathrm{adj}} = 2 R \sin(\pi/n)\)。六旋翼时 \(d_{\mathrm{adj}}=R\)。
- 相邻桨尖净间隙：\(\delta = d_{\mathrm{adj}} - D\)。
- 最小电机半径：\(R_{\min}=(D+\delta_{\min})/(2\sin(\pi/n))\)。
- 旋翼外接直径：\(D_{\mathrm{env}}=2R+D\)。
- 旋翼是有面积的水平圆盘，不是圆心或圆周点。
- 机身与左右非发射式 `sensor_pod` 是参数化盒体。
- 腿部按 coxa / femur / tibia 三段 URDF 运动学，用 capsule（线段 + 半径）作保守碰撞近似；足端为球。
- 检查：圆盘—圆盘、圆盘—机身盒、圆盘—sensor_pod 盒、圆盘—腿段 capsule。
- 线段—水平圆盘距离只在 Lipschitz 误差上界满足 `upper_bound - lower_bound <= geometry_solver_tolerance_m` 时返回；达到求值预算仍未满足时失败关闭，不返回距离，也不把未证明精度的结果标为 `CLEARANCE_MET`。
- 展开/收拢包络是上述几何体的轴对齐包围盒长/宽/高，不是整机二维外接圆代替碰撞。

G1 重复尺寸（`hex_arm_span`、腿段、机身、sensor_pod、旋翼平面高度）会与 Xacro 比较；漂移则分析失败，不会静默使用两套尺寸。Xacro 属性缺失、同名重复、非数值或无法解析的 `${expr}` 同样失败，不使用静默默认值。属性解析使用严格正则：只匹配单行、自闭合、先 `name` 后 `value` 的双引号 `<xacro:property>`，不展开 `xacro:include`。G1 Xacro 不被本阶段修改。

报告写入先在内存中生成 JSON/CSV/Markdown，校验严格有限数值（禁止 NaN/Infinity），写入临时目录后再替换正式文件。失败时不留下部分官方报告。

能量结果通过 `load_analysis_config` / `apply_uncertainty_case` / `solve_battery_feedback` 复用 G1.5 公开接口，不复制推进公式。

## 后续才能升级证据等级

要把本阶段从 `UNDETERMINED` 往前推进，至少还需要：真实 CAD 实体与机构、称重或供应商质量证据、推进台架与电机/桨数据、连续构型空间或完整扫掠体、以及折叠锁定机构。在此之前不得冻结结构，也不得采购硬件。
