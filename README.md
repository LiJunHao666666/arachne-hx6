# Arachne-HX6

非武器化、仿真优先的六足 + 六旋翼机器人，用于灾害搜救、环境侦察和传感器搭载。侧舱仅为不可发射的传感器 / 救援载荷占位结构，不包含武器、弹药、瞄准或伤害功能。

## 当前阶段：G1 低负载数字骨架

本仓库当前实现的是 G1 结构数字骨架：用参数化 Xacro / URDF 和基础几何体（box、cylinder、sphere）在 RViz 中显示整机，并通过 `joint_state_publisher_gui` 操纵 18 个腿部旋转关节。

本阶段不接入 Gazebo、PX4、真实硬件或旋翼升力 / 动力学。上部六旋翼为固定在机身上的平面 X 构型视觉骨架；左右 `sensor_pod` 为固定的非发射式任务舱占位。

## G1.5 推进可行性分析（ANALYSIS_ONLY）

离线质量—桨盘—推力—功率—电池—几何计算见 `docs/G1_5_PROPULSION_FEASIBILITY.md` 与包 `arachne_hx6_analysis`。结果标记为 **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**。能量质量闭合只是条件电池反馈解，不是整机质量闭合或可飞结论；整机推进可行性保持 `UNDETERMINED`。JSON 顶层候选标志区分为标称（`*_nominal`）与分不确定性（`*_by_uncertainty`），不得把标称结果当成全局结论。本阶段不修改 G1 URDF。

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
source install/setup.bash
ros2 run arachne_hx6_analysis propulsion_report --output-dir /tmp/arachne_g1_5_report
```

## G2 参数化整机架构包络（ANALYSIS_ONLY）

离线几何候选矩阵、站立到分析姿态的离散扫掠、以及与 G1.5 能量—质量闭合的联合门控见 `docs/G2_ARCHITECTURE_ENVELOPE.md`。结果标记为 **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**。G2 不是飞行控制阶段。名义几何通过不代表稳健几何通过；条件能量闭合不代表整机质量闭合；当前分析姿态不是已验证收拢姿态。质量账本、收拢需求均为 `INCOMPLETE`，稳健几何与整机架构可行性保持 `UNDETERMINED`，不允许采购。本阶段不修改 G1 URDF。

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
source install/setup.bash
ros2 run arachne_hx6_analysis architecture_report --output-dir /tmp/arachne_g2_report
```

## G3 需求、证据账本与不确定性门控（ANALYSIS_ONLY）

离线需求合同、证据等级、G2 19 项质量区间、几何不确定性预算、收拢机构需求和双向追踪见包 `arachne_hx6_analysis` 的 G3 模块，以及 `docs/G3_REQUIREMENTS_EVIDENCE_GATES.md`。结果标记为 **ANALYSIS_ONLY / NOT_FOR_PROCUREMENT**。G3 不会把缺失证据、PLANNING_ASSUMPTION 或混合不充分证据写成通过，也不会输出可飞、采购或硬件验证结论。最高正式门控是 `EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`。当前生产配置保持 `procurement_allowed: false`，`overall_system_readiness: UNDETERMINED`。

完成 G3 不会自动允许采购、实体组装或进入下一阶段。只有安全需求、质量/证据账本、风险评估、场地规则及正式审批全部满足，并由独立正式门控明确批准后，采购状态才可能改变。本阶段不修改 G1 URDF，也不改变 G1.5 / G2 的数学或报告合同。

若后续讨论实体概念演示，模型必须全程由封闭导轨、系留或机械限位约束，不得自由脱离或自推进；速度、动能、材料、夹伤距离和停止距离必须经过安全评估，并具备防护罩、急停和人工控制。视觉识别结果不得直接连接到任何危险动作。

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
source install/setup.bash
ros2 run arachne_hx6_analysis requirements_report --output-dir /tmp/arachne_g3_report
```

## 工作区路径

以下命令默认从工作区根目录执行。示例使用 `~/arachne_hx6_ws`，你可以把工作区放在任意其他路径，把该目录换成实际位置即可。

```bash
cd ~/arachne_hx6_ws
```

## 构建

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
colcon build --symlink-install
source install/setup.bash
```

## 在 RViz 中显示并操纵关节

先进入工作区并加载环境：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
source install/setup.bash
```

默认以站立姿态启动（`initial_pose:=standing`）。RViz 地面网格位于约 `z = -0.22 m`，与当前站立足端高度对齐；`base_link` 仍在机身中心。

```bash
ros2 launch arachne_hx6_description display.launch.py
```

显式指定站立姿态：

```bash
ros2 launch arachne_hx6_description display.launch.py initial_pose:=standing
```

零位姿态（URDF 关节零点，腿沿安装偏航水平伸出）：

```bash
ros2 launch arachne_hx6_description display.launch.py initial_pose:=zero
```

该 launch 会启动 `robot_state_publisher`、`joint_state_publisher_gui` 和 `rviz2`。当前站立姿态只是运动学展示值，用于 RViz 观察与关节联动演示，不代表真实硬件标定值。

## 模型检查（可选）

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
xacro src/arachne_hx6_description/urdf/arachne_hx6.urdf.xacro > /tmp/arachne_hx6.urdf
check_urdf /tmp/arachne_hx6.urdf
```

## 关节命名

每条腿（`lf` / `lm` / `lr` / `rf` / `rm` / `rr`）有 3 个旋转关节：

- `<leg>_coxa_joint`
- `<leg>_femur_joint`
- `<leg>_tibia_joint`

零位时腿沿安装偏航水平伸出。`coxa` 左右摆动，`femur` / `tibia` 俯仰用于抬腿、展开和收拢演示。

## 已知限制与采购边界

- 站立角不是硬件标定值或步态工作点，仅用于 RViz 运动学展示。
- 质量、惯性和碰撞几何都是占位估算，不能用于动力学、负载或结构强度结论。
- `sensor_pod` 与 coxa 静态间隙约 1 mm，机械冻结前必须重构。
- femur 与旋翼盘最近约 2 cm，必须进行扫掠体积和自碰撞分析。
- 当前没有旋翼动力学、飞行控制或模式切换。
- 当前版本不允许作为硬件采购依据。
