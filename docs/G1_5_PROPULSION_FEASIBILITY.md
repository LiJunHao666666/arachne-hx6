# G1.5 推进可行性分析（ANALYSIS_ONLY）

**ANALYSIS_ONLY**
**NOT_FOR_PROCUREMENT**
**overall_propulsion_feasibility: UNDETERMINED**

本文档描述 Arachne-HX6 在 G1 数字骨架之后的离线推进可行性计算框架。当前没有真实硬件。所有数值都是可修改的规划输入或由其推导的计算结果，**不得作为采购、选型或下达订单的依据**。本阶段不修改已验收的 G1 URDF / Xacro / 站立姿态。

能量—质量闭合（`energy_mass_closure`）只回答：在给定非电池质量和规划效率下，电池质量反馈方程是否存在较小的物理解。它**不是**整机质量闭合，也**不是**可飞结论。12 / 15 英寸桨径即使存在根，也只能标记为 `CONDITIONAL_ENERGY_CLOSURE`。整机推进可行性保持 `UNDETERMINED`。

## 范围

- 比较 4.7、12、15 英寸六旋翼桨径。
- 在三个非电池质量场景、三组不确定性规划边界下，用动量理论估算悬停推力、桨盘载荷、理想诱导功率、电功率、母线电流和电池质量。
- 电池质量反馈整理为 \(F(m)=m_{\mathrm{nb}}+c+k m^{3/2}-m\)。先用解析极小值判定是否存在闭合解，再用二分法求较小物理解。固定点迭代只作交叉检查，不是存在性证明。
- 对比当前 G1 `hex_arm_span = 0.30 m` 能否容纳该桨径与最小桨尖间隙，并输出当前骨架联合门控。
- 给出六旋翼 N-1 静态推力参考，并标记它不是操纵性证明。
- **不**自动改 URDF，**不**启动 Gazebo / RViz / PX4。

## 运行

在工作区根目录（示例 `~/arachne_hx6_ws`，可换成实际路径）：

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
colcon build --symlink-install --packages-select arachne_hx6_analysis
source install/setup.bash
ros2 run arachne_hx6_analysis propulsion_report \
  --output-dir /tmp/arachne_g1_5_report
```

可选 `--config` 指向自定义 YAML。默认读取包内 `config/propulsion_scenarios.yaml`。

## 公式与单位（SI）

| 名称 | 公式 | 单位 |
|---|---|---|
| 英寸转米 | \(D = D_{\mathrm{in}} \times 0.0254\) | m |
| 单桨盘面积 | \(A = \pi (D/2)^2\) | m² |
| 六桨总面积 | \(A_{\mathrm{total}} = n A\) | m² |
| 悬停总推力 | \(T = m g\) | N |
| 悬停总推力 | \(T_{\mathrm{kgf}} = T / g\) | kgf |
| 单电机悬停推力 | \(T_{\mathrm{motor}} = T / n\) | N 与 kgf |
| 目标推重比最大推力 | \(T_{\max} = (T/W)\, m g / n\) | N 与 kgf |
| 桨盘载荷 | \(\mathrm{DL} = T / A_{\mathrm{total}}\) | N/m² |
| 桨盘载荷 | \(\mathrm{DL}_{kg} = m / A_{\mathrm{total}}\) | kg/m² |
| 理想诱导功率（单桨） | \(P_{\mathrm{ideal}} = T_{\mathrm{motor}}^{3/2} / \sqrt{2\rho A}\) | W |
| 理想诱导功率（总计） | \(P_{\mathrm{ideal,tot}} = n\, P_{\mathrm{ideal}}\) | W |
| 估算悬停电功率 | \(P_{\mathrm{elec}} = P_{\mathrm{ideal,tot}} / (\mathrm{FoM}\,\eta_{\mathrm{m}}) + P_{\mathrm{avio}}\) | W |
| 电池母线直流电流 | \(I_{\mathrm{bus}} = P_{\mathrm{elec}} / V_{\mathrm{bus,nom}}\) | A |
| 所需电池质量 | \(m_{\mathrm{batt}} = (P_{\mathrm{elec}} t / 3600) / (e_{\mathrm{pack}} \eta_{\mathrm{use}})\) | kg |
| 能量质量残差 | \(F(m) = m_{\mathrm{nb}} + c + k m^{3/2} - m\) | kg |
| 临界总质量 | \(m_{\mathrm{critical}} = (2/(3k))^2\) | kg |
| 能量质量闭合 | 仅当 \(F(m_{\mathrm{critical}})\le 0\)；较小根在 \([m_{\mathrm{nb}}, m_{\mathrm{critical}}]\) 二分 | kg |
| 相邻电机中心距 | \(d_{\mathrm{adj}} = 2 R \sin(\pi / n)\) | m |
| 最低电机中心半径 | \(R_{\min} = (D + \delta) / (2\sin(\pi / n))\) | m |
| 旋翼外接直径 | \(D_{\mathrm{env}} = 2R + D\) | m |
| N-1 静态剩余推力 | \(T_{N-1} = T / (n-1)\)；负担增量 \(n/(n-1)-1\) | N 与 kgf |

其中 \(n=6\)。六旋翼均布时 \(d_{\mathrm{adj}} = R\)。六旋翼 N-1 负担增量为 20%。

\(c\) 是航电固定功率对应的电池质量；\(k\) 由旋翼面积、空气密度、figure of merit、驱动效率、续航和电池包比能量组成。

非法输入（非正数、效率不在 \((0,1]\)）会抛出错误。若 \(F_{\min}>0\)，该行标记 `ENERGY_MASS_CLOSURE_INFEASIBLE`：`battery_mass_kg`、`total_mass_kg` 以及所有依赖闭合质量的推力 / 功率 / 电流字段为 JSON/CSV 空值，Markdown 写 `—`。一次开环结果只进入 `diagnostic_first_iteration_battery_mass_kg` 与 `diagnostic_non_battery_mass_power_w`。固定点迭代失败不得当作数学无解。

`battery_bus_current_a` 是按标称母线电压计算的总直流输入电流。它不是单电机相电流，也不模拟电压下陷、线损或峰值电流。报告同时给出单电机悬停理想 / 机械功率参考 `ideal_induced_power_per_motor_w`，但不能由此推导真实电机电流。

## 解析质量闭合算法

1. 计算 \(c\)、\(k\) 与 \(m_{\mathrm{critical}}=(2/(3k))^2\)。
2. \(F_{\min}=F(m_{\mathrm{critical}})\)。
3. 仅当 \(F_{\min}\le 0\) 才存在能量质量闭合解。
4. \(F_{\min}>0\) 标记 `ENERGY_MASS_CLOSURE_INFEASIBLE`。
5. \(F_{\min}\le 0\) 时在 \([m_{\mathrm{nb}}, m_{\mathrm{critical}}]\) 内二分求较小物理解。
6. 最终根必须满足 \(|F(m)|\le\) `mass_tolerance_kg`。
7. 报告 `critical_total_mass_kg`、`maximum_non_battery_mass_for_closure_kg`、`closure_margin_kg`、`root_method`、`root_iterations`、`residual_kg`。
8. 固定点法只作交叉检查。

## 当前骨架联合门控

每行分别输出：

- `current_geometry_fit`
- `energy_mass_closure_status`
- `combined_current_baseline_gate`

只有当前 0.30 m 半径可以容纳，并且存在条件能量闭合时，联合门控才可为 `CONDITIONAL_CANDIDATE`；否则为 `REJECTED_FOR_CURRENT_BASELINE`。这不是采购或最终飞行可行性结论。

在标称规划输入下，当前三个桨径应为：

- 4.7 in：几何通过，能量闭合失败
- 12 in：能量条件闭合，当前几何失败
- 15 in：能量条件闭合，当前几何失败
- 当前骨架没有联合候选

## 规划假设（可修改，非实测）

见 `src/arachne_hx6_analysis/config/propulsion_scenarios.yaml`。摘要：

- \(g = 9.80665\,\mathrm{m/s^2}\)（标准重力）
- 标称 \(\rho = 1.225\,\mathrm{kg/m^3}\)（ISA 海平面）
- 推重比目标 \(1.8\)
- 标称 figure of merit \(0.65\)
- 标称电机+电调效率 \(0.80\)
- 母线 \(22.2\,\mathrm{V}\)
- 标称航电 \(20\,\mathrm{W}\)
- 标称电池可用比例 \(0.80\)
- 标称电池包比能量 \(180\,\mathrm{Wh/kg}\)
- 目标续航 \(600\,\mathrm{s}\)
- 当前电机中心半径 \(0.30\,\mathrm{m}\)（G1 `hex_arm_span`）
- 最小桨尖间隙 \(0.02\,\mathrm{m}\)
- 非电池质量：G1 占位 \(7.16\,\mathrm{kg}\)、规划 \(12\,\mathrm{kg}\)、增长 \(16\,\mathrm{kg}\)

G1 占位 \(7.16\,\mathrm{kg}\) 是 URDF 链接质量之和，**可能不包含**真实电池、电机、电调、线束和结构加固。

YAML 中另有明确命名的 `conservative` / `nominal` / `optimistic` 规划边界，至少变化空气密度、figure of merit、驱动效率、电池包比能量、电池可用比例和航电功率。它们全部是可修改规划边界，不是实测值。报告必须展示同一质量和桨径在三种假设下的结果范围，而不是只给单点精确值。

## 尚未计入闭合质量的项目

条件能量闭合**尚未包含**：

- 真实电机质量
- ESC 质量
- 螺旋桨和桨毂质量
- 加长机臂与连接件质量
- 高电流线束、连接器和保险保护质量
- 结构加固质量
- 散热质量
- 防护结构质量

因此 12 / 15 英寸的闭合结果不能称为整机质量闭合或可飞结论。

## N-1 静态参考

计算正常悬停单电机推力、单电机失效后剩余 5 台平均悬停推力、相对正常悬停的负担增量（六旋翼为 20%），以及指定推重比下的单电机推力要求。必须标记 `STATIC_THRUST_ONLY_NOT_CONTROL_AUTHORITY_PROOF`。真实单电机失效还取决于旋翼布局、偏航力矩、控制分配、剩余电机饱和和飞控；静态推力计算不能证明可安全容错飞行。

## 未建模因素

- 无叶素、失速、马赫数或雷诺数模型。
- 无电机 Kv、电流限制、热降额或桨谱。
- 无前飞、爬升或六足步行功率。
- 无超出 \(\eta_{\mathrm{m}}\) 的线损/BEC 细节。
- 无电池 Peukert、温度或循环寿命。
- 无旋翼—腿—机身气动干扰。
- 无结构/振动引起的质量增长闭环。
- 几何结论只对比 G1 视觉骨架，不改 URDF。

当前版本**不允许**作为硬件采购依据。
