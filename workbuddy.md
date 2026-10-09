# WorkBuddy 开发过程记录

> 本项目由 [WorkBuddy](https://www.workbuddy.cn)（AI 工作台）全程开发。以下是本次参赛项目的真实开发对话过程摘要，可作为 WorkBuddy 使用的实证。

## 开发时间线（单日完成，2026-10-09）

### 阶段一：赛事调研（~30 分钟）

- 用户发来麦当劳程序员创意开发大赛截图与微信推文链接，WorkBuddy 尝试抓取微信文章正文（发现 JS 动态渲染无法直接抓取），随即转向**官方一手源头**——GitHub 上的 `M-China/mcd-developer-innovation-challenge` 仓库，拉取完整活动规则（readme / guidelines / declaration 三件套）。
- 与用户确认创意方向：在多个候选中选定 **「双预算规划师」**——金额 + 热量双闸门配餐。

### 阶段二：MCP 真机实测校准（~40 分钟）

- 用户提供麦当劳 MCP Token 后，WorkBuddy 通过 JSON-RPC 直连 `https://mcp.mcd.cn`（initialize 握手 → tools/list → tools/call），完成：
  - **35 个工具全量 schema 抓取**（官方 README 只列了 34 个）
  - 关键枚举实测锁定：`beType`（1=到店自提/2=麦乐送/5=得来速/6=团餐）、`orderType`、`searchType`
  - **7 个隐藏坑实测发现**：价格单位是「分」、city+keyword 必须同时非空（否则 600058）、query-meals 只返回 code 不返回名称价格、饮品单独核价返回 ¥0（必须挂套餐走 diffPrice）、到店自提无 beCode 等
- 在真实门店（麦当劳福州金洲南路餐厅，storeCode 1410075）完成批量核价，拿到真实价格样例（随心配 1+1 ¥13.9/14.9、「堡」你欢乐套餐 ¥28 等）。

### 阶段三：Skill 开发与参赛材料产出（~30 分钟）

- 编写 `SKILL.md`：触发判定、7 步调用链、双预算组合算法、「麦门双预算战报」输出格式（含运动等价物换算表、省钱心情）。
- 产出全套参赛材料：README、MCP_INTEGRATION、CONTEST_DECLARATION（官方原文一字未改）、脱敏 mcp-config.example.json、防 Token 泄漏的 .gitignore、工具速查表。
- README 使用示例直接采用**真实实测战报**，不用演示假数据。

### 阶段四：知识沉淀与开源发布

- 将赛事规则、实测情报等 7 份资料沉淀到 IMA 知识库（COS 临时凭证 + HMAC-SHA1 签名上传三跳入库）。
- 创建 GitHub 仓库 `erikzeng2008-del/mcd-dual-budget-coach` 并推送全部文件，向官方仓库提交报名 Issue。

## WorkBuddy 能力使用清单

| 能力 | 用途 |
|---|---|
| MCP 自定义连接器 | 配置麦当劳 MCP（streamablehttp + Bearer Token） |
| 文件系统读写 | 全部项目文件的编写与管理 |
| Shell 执行 | MCP JSON-RPC 直连测试、批量核价脚本（Python urllib） |
| 网络抓取 | 赛事规则获取、微信推文分析 |
| GitHub 连接器 | 仓库文件推送、Issue 提交 |
| IMA 知识库 | 赛事资料与实测情报长期沉淀 |
| 记忆系统 | 跨会话延续参赛上下文 |

## 开发模式说明

本项目采用「用户拍板方向 + AI 全程执行」的协作模式：用户做关键决策（创意方向、Token 提供、账号确认），AI 负责调研、实测、编码、文档、发布的全链路执行，全程在一个 WorkBuddy 会话内完成。
