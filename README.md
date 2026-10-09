# 🍔 麦门双预算军师 (McDualBudget Coach)

> **钱是一个预算，热量是另一个预算。两个都不超，一顿配到位。**

告诉它「30 块 600 卡，中午想吃点扎实的」，它基于麦当劳官方 MCP 实时菜单、营养数据和你的优惠券，配出三个能直接下单的组合——并诚实地告诉你：这顿等于慢跑 50 分钟。

![WorkBuddy](https://img.shields.io/badge/Built_with-WorkBuddy-blue) ![MCP](https://img.shields.io/badge/Powered_by-麦当劳_MCP-orange) ![License](https://img.shields.io/badge/License-MIT-green)

## 为什么做这个

想吃麦当劳的人心里都有两杆秤：

- 💸 **钱包秤**：「这个月得省着点」
- 🔥 **热量秤**：「今天热量余额只够 600 卡了」

市面上的点餐工具只管「点得快」，没人管「配得对」。本 Skill 把两杆秤做成**双闸门**：金额与热量任何一个超限的组合直接淘汰，剩下的按「最划算 / 最扎实 / 最均衡」给你三个答案，选哪个都不用做数学题。

## 快速开始

### 1. 获取麦当劳 MCP Token

访问 [麦当劳 MCP 开放平台](https://open.mcd.cn/mcp) → 手机号登录 → 右上角「控制台」→「激活」→ 复制 Token。

### 2. 在 WorkBuddy 中配置 MCP 连接器

左侧边栏【专家·技能·连接器】→【连接器】→ 右上角【自定义连接器】→【配置 MCP】→ 粘贴 [mcp-config.example.json](mcp-config.example.json) 的内容并将 `${MCD_MCP_TOKEN}` 替换为你的实际 Token → 保存并**启用** `mcd-mcp`。

### 3. 装载本 Skill

将本仓库的 `SKILL.md` 放入 WorkBuddy 技能目录（或在对话中直接粘贴给 AI 加载）。详细步骤参考 [WorkBuddy 官方文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Connector)。

## 使用示例

```
你：30 块 600 卡，中午想吃点扎实的

军师：🍔 麦门双预算战报
─────────────────────
方案一 · 最划算
  板烧鸡腿堡 + 零度可乐
  实付 ¥26.0（券已抵 ¥3）｜总热量 541 kcal
方案二 · 最扎实
  巨无霸 + 圆筒冰淇淋
  实付 ¥29.5｜总热量 586 kcal
方案三 · 最均衡
  麦辣鸡腿堡 + 玉米杯
  实付 ¥24.0｜总热量 520 kcal
─────────────────────
💰 预算执行：¥26.0 / ¥30，剩余 ¥4.0
🔥 热量执行：541 / 600 kcal，剩余 59 kcal
🏃 运动等价物：这顿 = 慢跑 54 分钟 = 游泳 32 分钟
🧧 省钱心情：今天用券省了 ¥3，相当于白赚一个圆筒冰淇淋
```

其他玩法：

```
你：健身完只敢吃 500 卡，麦门还有救吗
你：25 块，早餐，要喝咖啡
你：帮我领下今天的券再配一顿 35 块的
```

> ⚠️ 示例中的价格为演示数据。真实输出全部基于麦当劳 MCP 实时返回（`query-meals` / `list-nutrition-foods` / `calculate-price`），菜单随时段变化，早餐和正餐配出来的组合不一样。

## 目标用户

| 人群 | 场景 |
|---|---|
| 🏃 健身/控糖人群 | 热量预算内吃麦当劳不破防 |
| 💰 学生党/省钱党 | 券+预算双卡，顿顿不超支 |
| 👨‍👩‍👧 宝妈/家庭用户 | 给孩子配一顿热量可控的开心乐园餐 |
| 🍔 麦门信徒 | 把「随便吃吃」升级成「精确吃吃」 |

## 安全设计

- **只配餐不下单**：默认不调用 `create-order`，杜绝误支付（用户两次明确确认后才放行）
- **不默认领券**：`auto-bind-coupons` 仅在用户明确要求时执行
- **零硬编码数据**：价格/热量全部来自 MCP 实时返回，Skill 本体不保存任何餐品数据
- 详见 [CONTEST_DECLARATION.md](CONTEST_DECLARATION.md) 与 [MCP_INTEGRATION.md](MCP_INTEGRATION.md)

## 文件结构

```
mcd-dual-budget-coach/
├── SKILL.md                  # Skill 本体（触发判定/调用链/组合算法/输出格式）
├── README.md                 # 本文件
├── MCP_INTEGRATION.md        # 麦当劳 MCP 集成说明（Server/Tool/流程/价值）
├── mcp-config.example.json   # 脱敏 MCP 配置示例（环境变量占位符）
├── CONTEST_DECLARATION.md    # 参赛声明（官方原文）
└── references/
    └── tools.md              # 本 Skill 使用的 MCP 工具速查
```

## 参赛信息

本项目参加 [麦当劳程序员创意开发大赛](https://github.com/M-China/mcd-developer-innovation-challenge)（2026.10.9 - 10.25），使用 [WorkBuddy](https://www.workbuddy.cn) 开发，参与 WorkBuddy 专项奖励。

---

*项目输出仅供参考，不构成医疗或营养建议。餐品信息、价格及供应状态以麦当劳官方渠道实时结果为准。*
