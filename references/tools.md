# 本 Skill 使用的麦当劳 MCP 工具速查

> Server：`mcd-mcp`（https://mcp.mcd.cn，Streamable HTTP，Token 限流 600 次/分钟）
> 完整 34 个工具见官方仓库：https://github.com/M-China/mcd-mcp-server

## 核心链路（每次必调）

| 工具 | 作用 | 本 Skill 中的角色 |
|---|---|---|
| `now-time-info` | 获取当前时间 | 推断早餐/正餐/下午茶/宵夜时段，决定拉哪张菜单 |
| `query-meals` | 查当前门店可售餐品列表 | 组合候选池（注意：随时段变化） |
| `list-nutrition-foods` | 餐品营养信息（能量/蛋白/脂肪/碳水/钠/钙） | 热量预算闸门的数据源 |
| `calculate-price` | 按商品列表（可含券）计算金额、配送费、优惠、应付总价 | 组合核价 + 券后实付价，输出前必调 |

## 增强链路（按需调用）

| 工具 | 作用 | 调用条件 |
|---|---|---|
| `query-nearby-stores` | 查附近可用门店。**city 与 keyword 必须同时非空**（只传 city 报 600058）；beType=1 自提无 beCode，beType=5 得来速必传 | 用户给了地址/区域时 |
| `query-meal-detail` | 查套餐/1+1 的 rounds 构成（候选 code + diffPrice 差价） | 组合候选确认环节 |
| `query-my-coupons` | 查用户已有优惠券（返回 markdown，含用券价格） | 默认调用（省钱军师本分） |
| `query-store-coupons` | 查当前门店可用券 | 用户想对比门店券时 |
| `available-coupons` | 查可领取的麦麦省券列表 | 仅用户明确问「有什么券能领」 |
| `auto-bind-coupons` | 一键领取所有可领券 | 仅用户明确说「帮我领券」，**不默认执行** |
| `delivery-query-addresses` | 查可配送地址 | 用户要外送场景时 |

## 红线工具（默认禁用）

| 工具 | 作用 | 禁用规则 |
|---|---|---|
| `create-order` | 创建订单 | 本 Skill 只配餐不下单。用户两次明确确认后（门店+餐品+就餐方式）才可放行 |
| `cancel-order` | 取消订单 | 仅在因本 Skill 流程误创建了订单时作为补救手段使用 |

## 调用预算

单次配餐任务总调用次数 ≤ 10 次（核心链路 4 次 + 增强按需），远低于 600 次/分钟限流。
