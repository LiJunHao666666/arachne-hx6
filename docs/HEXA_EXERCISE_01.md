# 练习 01：改变六旋翼布局，观察检查结果

目标：为最终能起飞的无下肢六旋翼建立几何基础。当前仅离线几何计算，
不接硬件，不代表动力学或飞行验证。默认尺寸是学习假设，不是采购或制造尺寸。

在本机 Ubuntu / WSL 终端执行：

```bash
cd /home/lijunhao/workspace/arachne-hx6
python3 scripts/hexa_layout.py --output-dir /tmp/arachne-hexa-normal
```

打开输出目录的 `layout.svg`，同时查看 `layout.json`。
Windows 文件资源管理器可访问 `\\wsl.localhost\Ubuntu\tmp\arachne-hexa-normal`。
图上前方朝上，R1 在前左，CW/CCW 为从上向下看的旋转方向。
R1–R6 是几何槽位，CH1–CH6 是模拟通道，不是具体飞控接线编号。

第一次观察：默认机臂中心距 0.12 m，桨盘半径 0.045 m，中心机体半径 0.035 m。
相邻桨盘边缘相距约 0.03 m，桨盘与中心机体边缘相距约 0.04 m。
PASS 只表示这两个平面间距检查通过，不包括机臂干涉、结构强度或升力。

第二次操作：缩短机臂，先预测会发生什么，再执行。

```bash
python3 scripts/hexa_layout.py --arm-m 0.08 --output-dir /tmp/arachne-hexa-overlap
```

这次应输出 FAIL，进程退出码为 1，但仍生成图和报告供检查。
六旋翼相邻电机中心距在本对称布局下等于机臂中心距，因此 0.08 m 小于两个桨盘半径之和 0.09 m。
这里观察的是平面占位重叠，不是实际螺旋桨测试。

第三次操作：保持几何不变，只调换前两个模拟通道。

```bash
python3 scripts/hexa_layout.py --channels 2 1 3 4 5 6 --output-dir /tmp/arachne-hexa-remap
```

检查 R1/R2 的通道标签已交换、位置未移动。尝试重复编号时，程序应拒绝输入。
这解释了为什么“安装位置”和“控制编号”必须分别记录。

练习后记录三件事：哪个参数改变了间距、通道交换改变了什么、为什么 PASS 不能证明能飞。
下一步研发是桌面离线状态测试及闭环模型设计；最终路线仍包括实际起飞、悬停和降落。
学习板实践将单独按练习需求选择，目前没有选定板型或发出采购许可。

开发验证命令（本练习不需要 ROS 或联网）：

```bash
python3 -m pytest -q scripts/tests/test_hexa_layout.py
```
