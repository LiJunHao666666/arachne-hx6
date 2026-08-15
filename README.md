# Arachne-HX6

非武器化、仿真优先的六足 + 六旋翼机器人，用于灾害搜救、环境侦察和传感器搭载。侧舱仅为不可发射的传感器 / 救援载荷占位结构，不包含武器、弹药、瞄准或伤害功能。

## 当前阶段：G1 低负载数字骨架

本仓库当前实现的是 G1 结构数字骨架：用参数化 Xacro / URDF 和基础几何体（box、cylinder、sphere）在 RViz 中显示整机，并通过 `joint_state_publisher_gui` 操纵 18 个腿部旋转关节。

本阶段不接入 Gazebo、PX4、真实硬件或旋翼升力 / 动力学。上部六旋翼为固定在机身上的平面 X 构型视觉骨架；左右 `sensor_pod` 为固定的非发射式任务舱占位。

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
