# 六电机 Gazebo 首轮演示与复现

状态：ANALYSIS_ONLY；procurement_allowed=false；实物飞行能力未确定。

本文件保留历次实验记录。当前方形航线操作及有效时间表见文末
“保持机头航向的世界坐标方形”；前面的速度、时间表和测试数量是历史结果。

## 本轮实际操作

Gazebo 的 motor world 和 GUI 已在运行，但 ROS bridge 已退出。恢复 bridge 后，
确认里程计回传且机体位于地面，再运行 gazebo_motor_scenario。
没有通过鼠标拖动机体，没有在界面里改参数，也没有使用真实飞控。

在 Ubuntu 项目终端加载环境：

```bash
cd /home/lijunhao/workspace/arachne-hx6
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

仅在 bridge 不在运行时，在独立终端启动通信桥：

```bash
ros2 run ros_gz_bridge parameter_bridge \
  /arachne_hx6/command/motor_speed@actuator_msgs/msg/Actuators@gz.msgs.Actuators \
  /model/arachne_flight_hex/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry
```

本次使用的演示命令（须先确认 motor world 正在运行、模型在地面且无其他控制器）：

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario \
  --output /tmp/arachne_motor_level_first_run.json
```

## 观看与参数说明

Alt+Tab 切换到 Gazebo Sim (Ubuntu)。播放/暂停按钮控制仿真时间，并不是起飞按钮。
本脚本使用墙钟时间，运行过程中不要暂停或拖动机体，否则本轮结果无效。
本轮没有点击界面按钮；动作由上面的终端命令启动。

脚本 reference() 设定目标：0.5 秒等待；约 3 秒上升；2.5 秒悬停；3 秒下降；
随后发送零转速，至 10.5 秒结束。目标上升/下降速度 0.4 m/s，悬停目标 1.22 m。
这些是目标值，不是承诺的实际轨迹。
MotorParameters 中高度比例增益为 4.0 N/m、垂直速度阻尼为 2.0 N/(m/s)。
本轮保持默认值，没有调参。改变这些值属于后续受控实验，不应同时修改多项。

## 本轮证据和边界

原始结果：evidence/motor-level-first-run-2026-09-21.json。
526 个控制采样记录；最高 1.33061 m；结束 0.02000 m；最大水平偏移 0.01415 m；
最大倾斜 0.03081 度。结束后独立读取里程计，仍确认处于地面。
当前 analyze() 基本动作判据返回 PASS，但不检查悬停稳定带、下降速度或限幅比例。
用户视觉确认另行记录，不能把脚本 PASS 当作用户已经看到了演示。

输出限幅计数为 1557：这是累计单电机限幅次数，单次更新最多计六次，
不是 1557 个独立时间点。当前日志缺少分阶段限幅、实际电机转速和偏航角记录，
不能据此推断限幅原因，也不能认定控制器已经调稳。

下一步先补充逐阶段诊断（尤其偏航角、偏航力矩和各电机限幅），再决定是否调参。
模型仍使用未实测动力参数和理想里程计；本结果不证明真实硬件可飞。
## Follow-up diagnostic run

Added raw command samples and per-phase saturation, yaw and requested yaw torque
without changing controller gains or allocation. Focused tests: 13 passed; build
passed. First attempted diagnostic timed out while Gazebo was paused and produced
no result. After explicitly resuming the world, the diagnostic completed FAIL.
Evidence: evidence/motor-diagnostics-2026-09-21.json.

The resumed run started at about 170.3 degrees yaw (world not reset after the
previous run). During TAKEOFF/HOVER/LAND every recorded motor request was limited:
900/900, 744/744 and 900/900 motor samples respectively. Maximum altitude remained
0.0198 m. Requested yaw torque peaked at 0.2911 Nm. These observations identify a
heading-control/allocation problem to investigate, not a verified root cause.
The previous basic PASS does not establish stable yaw control. Next review must
check Gazebo reaction-torque sign, coordinate frames, clean initial state and
heading-aware acceptance criteria before changing gains. No gain change made.
## Yaw sign correction and acceptance v2

Root cause: allocation used rotor spin direction as body yaw torque direction.
Gazebo uses the opposite reaction torque (-turningDirection * thrust *
momentConstant), with ccw=+1. Source:
https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/multicopter_motor_model/MulticopterMotorModel.cc
Only the yaw allocation sign changed; gains and maximum motor thrust did not.
Tests reconstruct reaction torque from the actual SDF rotor order for both
positive and negative requested yaw, and reject good-height traces with bad yaw.
Focused suite: 15 passed.

Reproduction now resets this isolated world before the scenario:

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --output /tmp/arachne_motor_yaw_fixed.json
```

The flag calls /world/arachne_flight/control with reset.all=true and pause=false,
checks the acknowledgement, and waits one second for settling. This resets the
entire isolated simulation world, not just the vehicle. Do not run concurrent
controllers. The script still uses wall-clock scheduling; do not pause mid-run.
No reset is performed when the flag is omitted.

Schema v2 adds required phase coverage, absolute yaw <=10 degrees, cumulative
limited motor fraction <=5%, and hover error <=0.20 m over samples after 4.5 s.
These are planning regression thresholds, not hardware certification criteria.

Saved evidence: evidence/motor-yaw-fixed-2026-09-21.json. Result PASS:
526 samples; peak height 1.30016 m; final height 0.019999 m;
0 limited motor samples; peak absolute yaw 0.00000604 degrees;
late-hover maximum altitude error 0.03333 m. The symmetric idealized environment
explains the very small attitude errors; disturbance robustness is not tested.
The new run also resets the initial state, so compare the evidence with that
initial-condition change in mind. The sign unit test independently exercises
both torque directions. User visual confirmation has not been recorded.
## Small initial-heading recovery (2026-09-21)

Added --initial-yaw-deg in [-8,8], requiring --reset-world. The Gazebo set_pose
service sets a pure yaw quaternion at the ground position after the reset.
This is an initial-condition experiment, not an in-flight wind/torque disturbance.
The heading target, allocation, gains and thrust limits are unchanged.
Acceptance additionally requires the initial sample to match the injected angle
within 0.5 degrees and late-hover heading error to remain below 1 degree.
Missing injection or failure to converge is tested as FAIL. Focused suite: 16 pass.

User operation: keep Gazebo Sim (Ubuntu) visible. Do not pause or drag the model
while the wall-clock scenario runs. No GUI parameter buttons are used. In the
Ubuntu project terminal, after sourcing ROS and install/setup.bash, run:

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --initial-yaw-deg 5 --output /tmp/arachne_yaw_plus5.json
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --initial-yaw-deg -5 --output /tmp/arachne_yaw_minus5.json
```

Run these sequentially, after the previous process exits. The changed parameter
is only the starting heading. Positive/negative angles exercise opposite heading
errors; neither is a physical flight-controller mounting instruction.

Both live Gazebo runs PASS; injection observed as +5/-5 degrees. Late-hover peak
absolute heading error: 0.01313 / 0.01292 degrees. Limited motor samples: zero in
both runs. Maximum late-hover altitude error: 0.03548 / 0.03480 m. Final altitude
about 0.02000 m in both runs. Evidence files:
- evidence/motor-yaw-plus5-2026-09-21.json
- evidence/motor-yaw-minus5-2026-09-21.json

These are two deterministic nominal-model runs, not a robustness or hardware
qualification campaign. In-flight disturbance, sensor noise, stale feedback and
unexpected interruption remain unverified. User visual confirmation is separate.
## Feedback / pause protection

Added a monotonic-time watchdog. No first feedback for 5 seconds aborts; no
advance of the odometry timestamp for 0.3 seconds aborts; a backwards timestamp
also aborts. Duplicate timestamps do not feed the watchdog. Failures latch and
cannot be cleared by later feedback. On abort the node publishes six zero motor
commands for at least 0.2 seconds, saves FAIL with abort_reason, then exits.
The process result now uses the current in-memory outcome, not an old result file.
This protects the simulation exercise only: zeroing motors in airborne hardware
is not a landing failsafe. If the command transport itself fails, delivery is not
guaranteed. Forced process termination and real hardware behavior are not covered.

Focused tests: 17 passed. Live fault injection: pause the world while the exercise
is active using the Gazebo control service (same effect as clicking Pause):

```bash
gz service -s /world/arachne_flight/control --reqtype gz.msgs.WorldControl \
  --reptype gz.msgs.Boolean --timeout 3000 --req 'pause: true'
```

Expected result: FAIL / odometry_stale_or_sim_paused, not a completed-flight PASS.
The model remains frozen while paused. Do not just resume an airborne aborted
scenario; reset the isolated world before another exercise. We reset and ran a
normal exercise afterward: PASS, zero saturation, final height 0.02000 m.

Evidence saved:
- evidence/motor-pause-protection-2026-09-21.json
- evidence/motor-pause-commands-2026-09-21.txt
- evidence/motor-watchdog-nominal-2026-09-21.json

An independent Gazebo command-topic capture ended with six zero velocities.
That demonstrates the bridge delivered the stop command onto Gazebo transport,
not measured rotor speed decay. The report's delivery_confirmed=false is retained
because the controller itself has no delivery acknowledgement. Startup absence,
replayed timestamps and reverse timestamps were unit-tested; only the pause/stale
case and subsequent nominal flight were exercised in live Gazebo this round.
## In-flight motor yaw-command pulse

Added --yaw-pulse-nm, finite and limited to +/-0.01 Nm; requires --reset-world
and cannot combine with initial heading injection. At scenario elapsed 4.0-4.3 s
(during hover), the pulse is added to the controller's requested yaw torque
before the existing allocation and limits. Gains, vehicle geometry and reference
trajectory are unchanged. This tests a motor-command disturbance, not external
wind or an independently applied physical wrench. Samples distinguish feedback
controller requested_yaw_torque_nm from injected_yaw_command_nm.

Acceptance requires at least ten nonzero pulse records matching the requested
amplitude, a yaw response of at least 0.1 degree in the injected direction over
4-5 s, and heading error <=1 degree throughout the sampled 5.5-6 s recovery window.
Existing height, tilt, yaw and saturation gates still apply. Focused tests: 18 pass.

With Gazebo visible, run sequentially from the sourced Ubuntu project terminal:

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --yaw-pulse-nm 0.01 --output /tmp/arachne_yaw_pulse_positive.json
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --yaw-pulse-nm -0.01 --output /tmp/arachne_yaw_pulse_negative.json
```

No dragging or GUI parameter editing was used. Watch takeoff, slight rotation
while hovering, heading recovery and landing; leave simulation running throughout.
The pulse parameter changes disturbance amplitude, not the controller gains.

Both live runs PASS. Positive/negative peak signed yaw excursion: 3.393/3.462 deg;
recovery-window peak absolute error: 0.404/0.420 deg. No motor saturation in either
run; final heights about 0.020 m. Evidence:
- evidence/motor-yaw-pulse-positive-2026-09-21.json
- evidence/motor-yaw-pulse-negative-2026-09-21.json

These are nominal ideal-odometry model results at one amplitude/duration only.
They do not validate wind rejection, roll/pitch disturbances, hardware estimator
behavior, or real-world flight readiness. Visual observation by the user remains
separate from the numerical evidence.

## 前后左右位置脉冲（2026-09-23）

新增单轴位置目标脉冲，用于核对橙色机头标记和控制坐标方向。该实验限定初始
偏航角为零，因此世界坐标与机体坐标暂时重合：+X 为向前，-X 为向后，
+Y 为向左，-Y 为向右。这一等价关系不适用于机体已经转向后的通用导航。

保持 Gazebo Sim (Ubuntu) 窗口可见。播放按钮控制仿真时间；运行命令后不要
暂停、拖动模型或同时启动另一个控制器。每条命令都会重置隔离世界，随后执行
起飞、悬停、0.6 秒单轴目标脉冲、回中和降落：

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --position-pulse-x-m 0.15 \
  --output /tmp/arachne_forward_position.json
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --position-pulse-x-m -0.15 \
  --output /tmp/arachne_backward_position.json
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --position-pulse-y-m 0.15 \
  --output /tmp/arachne_left_position.json
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --position-pulse-y-m -0.15 \
  --output /tmp/arachne_right_position.json
```

每次只能设置一个方向，绝对值上限为 0.20 m；位置脉冲不能与初始偏航注入或
偏航力矩脉冲组合。验收要求目标窗口至少记录 20 个有效请求、沿请求方向响应
至少 3 cm、横轴偏移不超过 5 cm、5.5-6.0 秒恢复窗口末端距原点不超过
8 cm，并且响应阶段航向误差不超过 1 度。恢复检查使用窗口末端值，因为窗口
起点仍处在连续回程过程中。

四次真实 Gazebo 运行均为 PASS。向前、向后、向左、向右的有符号峰值响应
分别为 0.07872、0.07827、0.07969、0.07892 m；恢复窗口末端误差分别为
0.04607、0.04602、0.04239、0.04841 m。最大横轴偏移为
1.36e-9 m，最大绝对航向误差为 1.29e-6 度。包含模型、旋翼顺序、耦合控制
和电机场景的聚焦测试共 47 项，全部通过。可审查的精简证据：

- evidence/motor-position-summary-2026-09-23.json

四份逐采样原始 JSON 保留在本地证据目录，但不提交到 Git；上面的命令可以
重新生成原始记录，精简摘要保留验收结果、全部判据和关键指标。

这些结果只验证理想模型、理想里程计和零初始偏航下的小幅平移方向。它们不
证明转向后的机体系导航、外部风扰、传感器噪声、真实电机响应或实物飞行能力。
脚本的数值 PASS 也不能代替用户对 Gazebo 窗口的视觉确认。

## 转向后的机体前向脉冲（2026-09-24）

该实验验证机头转向后，前进命令仍沿机体前方，而不是固定沿世界 +X。命令先
重置隔离世界，把橙色机头设置到指定航向，并在整个起降过程中保持该航向。
4.0-4.6 秒的机体前向目标会按目标航向旋转到世界 X/Y 坐标。

保持 Gazebo 播放状态，不要拖动模型或同时运行其他控制器。正负 45 度实验：

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --body-heading-deg 45 --body-forward-pulse-m 0.15 \
  --output /tmp/arachne_body_forward_heading45.json
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --body-heading-deg -45 --body-forward-pulse-m 0.15 \
  --output /tmp/arachne_body_forward_heading_minus45.json
```

`--body-heading-deg` 是保持的机头航向，范围为 -180 到 180 度；
`--body-forward-pulse-m` 是机体前后方向目标，绝对值上限为 0.20 m。
该模式要求 `--reset-world`，并且不能与世界轴位置脉冲、初始偏航恢复或
偏航力矩脉冲组合。

首次 +45 度运行按预期触发 FAIL：沿机头响应 0.05705 m，但横向偏差
0.05402 m，超过 0.05 m 上限。根因是位置控制器把世界坐标加速度直接映射为
机体滚转和俯仰，这只在偏航角为零时成立。修复后，控制器先使用当前偏航角将
世界加速度旋转到机体坐标，再计算滚转和俯仰目标。

修复后的 +45/-45 度真实 Gazebo 运行均为 PASS。沿机头方向峰值响应分别为
0.08326/0.08364 m；横向偏差为 0.01334/0.01358 m；恢复窗口末端误差为
0.05041/0.05127 m；最大航向误差为 0.02498/0.02360 度。50 项聚焦测试
全部通过。精简证据：

- evidence/motor-body-frame-summary-2026-09-24.json

原始逐采样 JSON 保留在本机，不提交到 Git。该结果只覆盖理想模型、理想
里程计和正负 45 度两个航向，不证明任意航向导航、路径跟踪、外部扰动抑制或
真实飞行能力。

## 四航点方形航线（2026-09-24）

新增 `--square-path-side-m`，让六旋翼在零航向下依次访问四个世界坐标航点，
形成顺时针方形航线。该模式会把悬停阶段延长到 9.5 秒，之后执行原有的
3 秒下降和停桨。它要求 `--reset-world`，并且不能与其他脉冲实验组合。

保持 Gazebo 播放状态，不要拖动模型。在已加载 ROS 和项目环境的终端运行：

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --square-path-side-m 0.15 \
  --output /tmp/arachne_square_path_015.json
```

边长参数必须大于零且不超过 0.15 m。本轮目标时间表：

- 4.0-5.2 秒：目标 (0.15, 0.00) m，向前；
- 5.2-6.4 秒：目标 (0.15, 0.15) m，向左；
- 6.4-7.6 秒：目标 (0.00, 0.15) m，向后；
- 7.6-8.8 秒：目标 (0.00, 0.00) m，向右回原点。

每条边至少需要 40 个正确目标记录，各段结束时距对应航点不超过 0.08 m，
整个路径的航向误差不超过 1 度。真实 Gazebo 运行 PASS：四个终点误差依次为
0.05762、0.05874、0.05684、0.05288 m，最大绝对航向误差 0.01383 度。
53 项聚焦测试全部通过。精简证据：

- evidence/motor-square-path-summary-2026-09-24.json

原始逐采样结果保留在本机。当前是零航向、单一边长、阶跃航点的理想模型实验，
还没有验证平滑轨迹生成、非零航向方形、路径速度限制、避障或真实定位误差。

## 平滑方形轨迹（Gazebo 已验证，2026-09-24）

方形模式已从航点阶跃改为连续轨迹。每条边占 3.0 秒：前 2.0 秒使用
五次平滑曲线移动，后 1.0 秒保持角点。曲线在每条边的起点和终点速度、加速度
均为零；边长 0.15 m 时，计划速度峰值不超过 0.140625 m/s。目标速度同时
进入位置控制器的阻尼项，用于跟踪移动参考，而不是只追赶静态航点。

启动命令和观看方法不变。运行时 Gazebo 保持播放，不点击参数按钮、不拖动模型：

    ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
      --square-path-side-m 0.15 \
      --output /tmp/arachne_square_path_smooth_015.json

验收新增逐采样参考位置/速度一致性、计划速度上限、全程跟踪误差 10 cm 和
角点速度 0.10 m/s 检查，并保留四个角点 8 cm、航向误差 1 度的限制。
第一轮 0.8 秒移动、0.4 秒稳定的现场运行未通过：虽然四个角点都在 3.8 cm
以内，但第一个转角仍有明显惯性，最大跟踪误差达到 0.162 m。因此没有放宽
阈值，而是将轨迹改为当前较慢的时间表。第二轮把移动时间改为 1.4 秒、稳定
时间改为 0.6 秒后，最大跟踪误差降到 0.0996 m，角点速度通过，但四个角点
误差仍为 8.8-9.1 cm。第三轮把稳定时间增加到 1.0 秒后，角点误差通过，
但角点速度为 0.102-0.108 m/s，略高于 0.10 m/s。因此第四轮保持稳定时间，
只把移动时间降速到当前的 2.0 秒。第四轮把最大跟踪误差降到 0.0749 m、
角点位置误差降到约 3.7 cm，但角点速度仍约 0.1095 m/s，继续降速的收益已经
很小。第五轮因此保持轨迹不变，只把水平速度阻尼从 2.0 调到 2.5
m/s² per (m/s)，用于减少残余摆动；其余控制参数不变。
第五轮现场运行 PASS。最大跟踪误差 0.06513 m；四个角点位置误差依次为
0.00538、0.00545、0.00534、0.00535 m，角点速度依次为 0.09508、
0.09587、0.09448、0.09448 m/s。计划速度峰值 0.140625 m/s，最大倾斜
2.7144 度，最大绝对航向误差 0.01870 度，电机限幅次数为零，最终高度
0.02000 m。精简证据：

- evidence/motor-square-path-smooth-summary-2026-09-24.json

原始逐采样结果保留在本机，不提交到 Git。该结果仍只覆盖理想 Gazebo 模型、
理想里程计、零航向和单一 0.15 m 边长，不证明避障、传感器误差下的导航或
真实飞行能力。状态仍为 ANALYSIS_ONLY，procurement_allowed=false。

## 保持机头航向的世界坐标方形（2026-09-24）

现在可以把 `--body-heading-deg` 与 `--square-path-side-m` 组合：
机头保持给定角度，移动路线始终沿世界 +X、+Y、−X、−Y。
从世界 +Z 向下看，这是逆时针方形；前文及旧证据中的 clockwise/顺时针
是方向命名错误，实际航点次序没有改变。

### 本次修正

Gazebo OdometryPublisher 在三维模式下把线速度转换到机体坐标后输出。
原控制器却将这份速度直接与世界坐标的目标速度相减，转向后阻尼方向就会混用。
现在通过当前姿态四元数，把线速度的三个分量转回世界坐标，再用于水平及高度
控制。角速度仍用于机体力矩控制。本轮未更改控制增益、电机模型或推力上限。
依据：[Gazebo OdometryPublisher 源码](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/odometry_publisher/OdometryPublisher.cc)。

新采样中的 `velocity_x_m_s`、`velocity_y_m_s`、`velocity_z_m_s`
均为世界坐标速度，并带有 `linear_velocity_frame=WORLD`。
此前同名 x/y 速度字段直接来自机体坐标，不应与新记录混用。
验收现在区分“绝对机头角度”和“相对于指定航向的误差”，并检查初始转向是否
实际生效、路径期间的目标航向是否正确。缺失角点数据时输出可保存的 FAIL。

### 怎么操作和观看

1. 使用已有的 motor world 和 Gazebo 图形窗口。Alt+Tab 切到 Gazebo；
   只有未运行 bridge 时，才按本文开头命令启动通信桥。
2. Gazebo 的播放/暂停按钮控制仿真时间；起飞由终端命令触发。
   本次没有点击界面按钮，`--reset-world` 会重置并恢复播放。
3. 在 Ubuntu 项目终端加载 ROS 和项目环境，确认没有另一个飞行控制脚本运行。
4. 先输入下面命令。机头应保持左偏 45°，路径仍沿地面的固定坐标方向；
   不要以相机画面中的左右代替世界坐标方向。
5. 四条边结束后会自动降落、停桨。等终端显示 PASS 或 FAIL 后再开始下一轮。
6. 负航向实验把 `45` 改成 `-45`，输出文件名也改成 `minus45`；
   零航向基准改成 `0`，文件名改成 `zero`。每次只改变这个航向参数。

```bash
ros2 run arachne_hx6_control gazebo_motor_scenario --reset-world \
  --square-path-side-m 0.15 --body-heading-deg 45 \
  --output /tmp/arachne_square_heading_plus45.json
```

运行期间保持播放，不拖动模型。暂停或反馈过期会触发停桨保护并把本轮记为失败。
航向参数允许 −180° 到 180°，但本轮现场只验证了 0° 和 ±45°。
边长上限仍为 0.15 m。方形实验不能混用位置脉冲、偏航脉冲或初始偏航恢复。

当前每条边移动 2.0 秒，随后保持角点 1.5 秒：

- 4.0–7.5 秒：沿世界 +X 到 (0.15, 0.00) m；
- 7.5–11.0 秒：沿世界 +Y 到 (0.15, 0.15) m；
- 11.0–14.5 秒：沿世界 −X 到 (0.00, 0.15) m；
- 14.5–18.0 秒：沿世界 −Y 回到原点；
- 18.7 秒开始下降，21.7 秒开始停桨，约 23.2 秒结束。

### 实际验证结果

首次 +45° 实验使用旧的 1.0 秒角点停留，第二角点速度为 0.10070 m/s，
超过 0.10 m/s，正确返回 FAIL。观察回到原点后的减速数据，再等待约 0.4 秒，
速度已降到约 0.0075 m/s，因此把角点停留延长为 1.5 秒后重新验证。
轨迹计划速度上限仍为 0.140625 m/s，跟踪误差上限 10 cm、角点位置误差
上限 8 cm、角点末端速度上限 0.10 m/s、路径航向误差上限 1° 均未改变。
方形实验沿用的整体水平范围是边长的对角线加 0.08 m，本例约 0.29213 m；
这与普通悬停实验的 0.25 m 范围不同。

最终同一参数下的三轮 Gazebo 实验均为 PASS：

- 0°：最大跟踪误差 6.5646 cm，最大航向误差 0.01357°；
- +45°：最大跟踪误差 6.5690 cm，最大航向误差 0.02689°；
- −45°：最大跟踪误差 6.5484 cm，最大航向误差 0.02785°。

三轮角点最终位置误差均不超过 1.51 cm，角点最终速度均小于 0.013 m/s，
无电机限幅，最终高度约 0.020 m。这里的角点速度是该段最后一个采样值，
不代表整个停留窗口持续低于此值。

控制包构建通过；本轮包测试 68 项通过、1 项原有版权检查跳过，
包括 flake8 和 pep257 检查。证据摘要：
[motor-square-held-heading-summary-2026-09-24.json](evidence/motor-square-held-heading-summary-2026-09-24.json)。
摘要包含最初的通过/失败记录、最终三轮指标、原始文件 SHA-256、复现命令。
逐采样原始文件保留在本机 /tmp，重启后可能清理；Git 保存精简摘要。

本轮只完成单次三航向、理想里程计、无外部扰动的仿真；尚未验证重复性、
任意航向、噪声或真实硬件。Gazebo 图形进程在运行，但本轮尚未收到用户的
视觉确认。下一步应先加入小幅外部横向扰动及恢复验收，继续在仿真中评估。
