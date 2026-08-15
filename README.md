# Arachne-HX6

非武器化、仿真优先的六足 + 六旋翼机器人，用于灾害搜救、环境侦察和传感器搭载。侧舱仅为不可发射的传感器 / 救援载荷占位结构，不包含武器、弹药、瞄准或伤害功能。

## 当前阶段：G1 低负载数字骨架

本仓库当前实现的是 G1 结构数字骨架：用参数化 Xacro / URDF 和基础几何体（box、cylinder、sphere）在 RViz 中显示整机，并通过 `joint_state_publisher_gui` 操纵 18 个腿部旋转关节。

本阶段不接入 Gazebo、PX4、真实硬件或旋翼升力 / 动力学。上部六旋翼为固定在机身上的平面 X 构型视觉骨架；左右 `sensor_pod` 为固定的非发射式任务舱占位。

## 构建

```bash
source /opt/ros/jazzy/setup.bash
cd /home/lijunhao/arachne_hx6_ws
colcon build --symlink-install
source install/setup.bash
```

## 在 RViz 中显示并操纵关节

默认以站立姿态启动（`initial_pose:=standing`）：

```bash
source /opt/ros/jazzy/setup.bash
source /home/lijunhao/arachne_hx6_ws/install/setup.bash
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
cd /home/lijunhao/arachne_hx6_ws
xacro src/arachne_hx6_description/urdf/arachne_hx6.urdf.xacro > /tmp/arachne_hx6.urdf
check_urdf /tmp/arachne_hx6.urdf
```

## 关节命名

每条腿（`lf` / `lm` / `lr` / `rf` / `rm` / `rr`）有 3 个旋转关节：

- `<leg>_coxa_joint`
- `<leg>_femur_joint`
- `<leg>_tibia_joint`

零位时腿沿安装偏航水平伸出。`coxa` 左右摆动，`femur` / `tibia` 俯仰用于抬腿、展开和收拢演示。
