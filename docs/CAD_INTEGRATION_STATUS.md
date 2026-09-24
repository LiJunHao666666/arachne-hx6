# CAD 工具部署记录

核验日期：2026-09-20。用户已授权部署以下五项集成。
本记录区分安装、MCP 握手与真实建模验收；不改变 ANALYSIS_ONLY 或 procurement_allowed=false。
未购买软件、创建付费订阅、执行加工或制造。没有改变机器人代码或硬件配置。

## 已完成的本机部署

- KiCad MCP：既有安装保留，KiCad 10.0.6。当前会话 get_backend_state 成功，
  后端为 SWIG，无加载工程、无脏修改；不是实时 GUI 同步模式。
- KiCad Happy：现有 kicad 技能及分析脚本可启动。实际生成隔离空板，
  analyze_pcb.py 成功输出可解析的 JSON；这只是解析冒烟验证，不是实际电路审查。
- SolidWorks MCP：已有 SolidPilot 源码补齐独立 Python 环境，MCP 握手及工具发现成功（47项）。
  源码提交 fc3c743228d717393c639ec7fcc5b562ab97662e。
- Onshape MCP：已有 hedless 实现补齐独立 Python 环境，握手及工具发现成功（48项）。
  源码提交 a9c2a5efbcebdf79d6d010184bff22658e7abfa6。
- Fusion MCP：已有 Faust Machines 实现补齐独立 Python 环境，真实 socket 模式下
  MCP 握手及工具发现成功（93项）；未使用 mock。源码提交 ba8560f321656aa493cdc775bc2fa7b2e7d8f005。
  发现 MCP 2.2.0 与其 list_tools API 不兼容，按上游 uv.lock 固定为 mcp==1.26.0，复测通过。
  Fusion360MCP 插件已复制至用户 AddIns 目录，runOnStartup=false；连接限定 127.0.0.1:9876。

三套新增服务均已注册到用户 .codex/config.toml；修改前有带时间戳备份。
TOML 解析及原有配置保持一致的检查通过。三个独立环境 pip check 均通过。
客户端需重新加载 MCP 配置后，新工具才会进入会话；重载不等于下列依赖已经满足。

本地工具根目录：Windows 用户目录下 Tools。
Tools/cad-integration-checks 保存 check-mcp.mjs、mcp-results.json、依赖快照和空板解析结果。
这些本机文件及含个人配置的备份不上传项目仓库；仓库只保存不含凭证的部署记录。

## 尚未完成，不能标记为可用的部分

1. SolidWorks：未检测到本体安装、Interop DLL 或 Visual Studio 2022 MSBuild。
   当前实现依赖 SolidWorks 2026、.NET Framework 4.8 及执行层编译；本地 5000 端口未开放。
   需要确认合法可用的安装和授权后构建执行层，再验证建模、参数修改、保存与导出。
2. Onshape：当前进程未设置 API 密钥，源码目录无 .env。尚未验证账号、API 访问权限或云端调用。
   不要把密钥发到聊天或写入仓库；应通过本机环境变量或受保护的本地配置提供。
   当前注册的是 hedless 的 REST API 集成，不能直接使用官方 FeatureScript MCP 的 OAuth 登录替代其密钥。
3. Fusion：未检测到运行程序，9876 和官方默认 27182 端口均未开放。
   交接记录中的个人版授权问题尚未重新核实；需实际可运行的 Fusion 和启用插件后做 ping 及建模验收。
   官方内置 Fusion MCP 是另一条可选路线，未同时配置，避免重复工具与端口混淆。
4. KiCad：尚未完成非空测试电路的原理图→PCB→布局布线→DRC/ERC→生产文件全流程验收。
5. KiCad Happy：尚未完成带有已知故障的非空电路审查、交叉验证和相应仿真验收。

因此当前结论为：五项都有本地安装基础；三套新增 MCP 的协议层已验证，
全部五项的端到端能力尚未验收，不能声明“所有建模操作”或“完整设计闭环”均已可用。

## 来源与后续验收

- KiCad MCP：https://github.com/mixelpixx/KiCAD-MCP-Server
- KiCad Happy：https://github.com/aklofas/kicad-happy
- SolidPilot：https://github.com/eyfel/mcp-server-solidworks
- Onshape REST MCP：https://github.com/hedless/onshape-mcp
- Fusion 插件 MCP：https://github.com/faust-machines/fusion360-mcp-server
- Fusion 官方内置接口：https://www.autodesk.com/products/fusion-360/blog/build-your-own-fusion-add-ins-with-the-fusion-mcp/
- Onshape 官方 FeatureScript 接口：https://www.onshape.com/de/resource-center/tech-tips/connect-featurescript-mcp-server-claude-code
- Codex 配置：https://developers.openai.com/codex/mcp

后续在独立测试工程中验收，保留失败和输出证据：
机械 CAD 创建简单参数化零件、修改尺寸后读回、保存并导出；
Onshape 另测装配与已知相交模型的干涉识别；
KiCad 使用有已知网络与故障的测试板验证生成、检查与导出，Happy 对相同文件交叉审查。
任何演示成功只证明实际覆盖的操作，不自动证明其他操作或机器人可制造、可飞。
