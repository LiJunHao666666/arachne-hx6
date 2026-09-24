# 离线开发自检

本工具用于验证当前代码，不依赖 Fusion、网络或实体设备。
项目状态仍为 `ANALYSIS_ONLY / NOT_FOR_PROCUREMENT`。
它不改变 G1 模型、分析算法、现有 YAML 授权或报告格式。

## 执行位置

设备：当前 Windows 电脑的 WSL Ubuntu。
终端：Ubuntu / WSL 终端。
Git 影响：原工作区的文件、索引、分支和提交保持原状；不推送。

```bash
cd /home/lijunhao/workspace/arachne-hx6

# CLI 输入校验与编排回归
python3 scripts/check_offline.py --suite cli

# 全部离线分析回归（默认）
python3 scripts/check_offline.py

# 分析、URDF 展开检查和自检工具自身的测试
source /opt/ros/jazzy/setup.bash
python3 scripts/check_offline.py --suite all
```

依赖 Python 3、Git、pytest 和 PyYAML。`all` 还需要 ROS Jazzy 的 xacro。
检查器会主动检查这些前置条件，不会自动安装软件。
纯分析检查直接从源码导入，无需先执行 colcon build 或 source install/setup.bash。

## 为什么使用临时副本

现有 D1A 测试要求 Git 工作区干净；对正在开发的工作区直接跑全套测试，
会把合法的未提交修改也判为失败。该检查器保留原测试，在独立临时仓库中：

1. 从当前本地仓库复制 Git 历史，不连接远端。
2. 应用相对于 HEAD 的完整补丁，包括暂存及未暂存修改、删除、重命名和二进制变更。
3. 复制未被 Git 忽略的未跟踪文件；跳过被忽略的 build、install、log 等缓存。已跟踪或已强制暂存的文件即使匹配忽略规则，也会保留在快照提交中。
4. 仅在临时仓库生成测试快照提交，并移除其 origin。
5. 从临时源码运行所选测试，保持冻结文件哈希、历史范围和几何断言有效。

测试不代表正式提交已经获得审核。原仓库不会自动暂存、提交、切换分支或同步。
请在运行期间暂停编辑源文件；快照不保证捕获并发修改的一致时刻。
不支持把嵌套仓库或子模块的未提交改动自动打包到快照。

pytest 第三方插件自动加载被禁用，外部 `PYTEST_ADDOPTS` 和
`PYTEST_PLUGINS` 被移除，防止环境中残留的筛选条件漏跑测试。
源码路径优先于已安装版本。`--suite` 是明确的测试范围选择，不更改生产采样规模。

## 查看失败

检查器返回 pytest 的退出码；依赖或快照错误返回 1，参数错误返回 2，
用户中断返回 130。不把测试启动成功当成测试通过。

需要保留副本复查时：

```bash
python3 scripts/check_offline.py --suite all --keep-snapshot
```

命令结束会打印保留副本的绝对路径。默认自动清理临时副本。
测试可能在自己的临时目录生成用于验证的报告，但不会在正式仓库提交生产报告。

`all` 包含离线分析、URDF 和本工具测试，不等于全工作区 colcon 验收；
它没有覆盖 ament 的 XML、CMake 等构建检查。需要完整构建验证时仍执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

在原工作区有未提交更改时，原有“工作区干净”断言仍可能使 colcon 全量检查失败；
应在审核后的干净提交或独立验证快照上进行该验收，不跳过或修改冻结检查。

## CLI 配置格式

G4 CLI 的三份显式 YAML 在进入分析前都进行结构检查：

- 必须是 UTF-8 编码的映射，所有映射键必须是字符串。
- 禁止重复键，包括相同值的重复和嵌套映射中的重复。
- 禁止 YAML 合并键 `<<`，避免隐藏覆盖；普通标量锚点/别名可使用。
- 禁止 Python 对象等不安全 YAML 标签。
- 错误返回 1，并在 stderr 输出单行 `ERROR:`；不开始求值或发布新报告。

D1A 和 D1B 原加载器继续负责领域字段与授权语义检查，原生产模块未修改。
这一层检查适用于 D1C CLI；直接调用旧 D1A/D1B 加载器不经过此预检。
