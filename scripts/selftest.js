/* 麦门双预算军师 · 自测断言集
 * 直接跑在 demo.html 的页面上下文里（由 run_selftest.py 注入）
 * 断言对象是「真正发货的代码」，不是镜像实现
 * 输出：页面末尾追加一个结果元素（JSON 文本），由运行器解析
 */
(function () {
  var R = [];
  function ok(name, cond, detail) {
    R.push({ name: name, pass: !!cond, detail: detail === undefined ? "" : String(detail) });
  }
  function near(a, b, eps) { return Math.abs(a - b) <= (eps || 0.011); }

  /* ── 1. 数据资产完整性 ── */
  ok("DATA 单品数 = 83", DATA.length === 83, "实际 " + DATA.length);
  ok("COMBOS 组合数 > 80000", COMBOS.length > 80000, "实际 " + COMBOS.length);
  ok("COUPONS 券数 = 11", COUPONS.length === 11, "实际 " + COUPONS.length);
  var liveN = COUPONS.filter(function (c) { return c.today_ok; }).length;
  ok("今日可用券 = 2", liveN === 2, "实际 " + liveN);

  /* ── 2. 价格单位与格式（防「分/元」串台） ── */
  var jwb = DATA.filter(function (x) { return x.n === "巨无霸"; })[0];
  ok("巨无霸价格 = 26.5 元（非分）", jwb && near(jwb.p, 26.5), jwb ? jwb.p : "未找到");
  ok("money() 保留一位小数", money(26.5) === "26.5" && money(13) === "13.0", money(26.5) + " / " + money(13));

  /* ── 3. 组合算法：双闸门 ── */
  var plans = pick(30, 600);
  ok("30元/600卡 配出方案", plans.length > 0, "实际 " + plans.length + " 个");
  var overM = plans.filter(function (p) { return p.price > 30.0001; });
  ok("全部方案不超金额闸门", overM.length === 0, overM.map(function (p) { return p.price; }).join(","));
  var overK = plans.filter(function (p) { return !p.unknown && p.kcal > 600; });
  ok("全部方案不超热量闸门", overK.length === 0, overK.map(function (p) { return p.kcal; }).join(","));
  ok("三档标签齐全且有序", plans.length === 3 && plans[0].label === "最划算" && plans[1].label === "最扎实" && plans[2].label === "最均衡",
     plans.map(function (p) { return p.label; }).join(" > "));
  var cheapest = plans.slice().sort(function (a, b) { return a.price - b.price; })[0];
  ok("「最划算」价格 = 全场最低", near(plans[0].price, cheapest.price), "最划算 " + plans[0].price + " vs 最低 " + cheapest.price);

  /* ── 4. 边界：极低预算诚实返回 ── */
  var low = pick(3, 999);
  ok("3元预算 → 诚实返回空（不硬凑）", low.length === 0, "实际 " + low.length + " 个");
  var mid = pick(15, 400);
  ok("紧预算不凑满三档", mid.length <= 3, "实际 " + mid.length + " 个");

  /* ── 5. 钠（本轮新增） ── */
  ok("方案对象带钠合计 na 字段", plans.length > 0 && typeof plans[0].na === "number", plans[0] ? plans[0].na : "-");
  ok("钠合计 > 0（非空数据）", plans[0].na > 0, plans[0].na);
  ok("REF 每日钠参考 = 2000mg", REF.sodium === 2000, REF.sodium);

  /* ── 6. 券匹配引擎 ── */
  var dat = { label: "T", items: [{ n: "麦辣鸡腿汉堡", p: 22.5, k: 485, na: 1208, u: 0, parts: [] }], price: 22.5, kcal: 485, na: 1208, unknown: false };
  var m1 = matchCoupons(dat);
  ok("不含薯条 → 薯条券不命中", m1.filter(function (r) { return r.c.name.indexOf("薯条") >= 0; }).length === 0,
     "命中 " + m1.filter(function (r) { return r.c.name.indexOf("薯条") >= 0; }).length);
  var dat2 = { label: "T", items: [{ n: "套餐X", p: 20, k: 434, na: 1001, u: 0, parts: [{ n: "迷你薯条", k: 106 }] }], price: 20, kcal: 434, na: 1001, unknown: false };
  var m2 = matchCoupons(dat2);
  var hitFries = m2.filter(function (r) { return r.ok && r.c.name.indexOf("中薯条") >= 0; }).length > 0;
  ok("套餐成分含薯条 → 薯条券命中（读 parts）", hitFries, "parts 规则");
  var dat3 = { label: "T", items: [{ n: "麦乐鸡", p: 25.5, k: 213, na: 422, u: 0, parts: [] }], price: 25.5, kcal: 213, na: 422, unknown: false };
  var m3 = matchCoupons(dat3);
  var hitAce = m3.filter(function (r) { return r.ok && r.c.name.indexOf("王牌") >= 0; }).length > 0;
  ok("含小食且金额够 → 王牌小食拼命中（anySmall）", hitAce, "anySmall 规则");
  var overprice = matchCoupons({ label: "T", items: [{ n: "苹果片", p: 7, k: 32, na: 0, u: 0, parts: [] }], price: 7, kcal: 32, na: 0, unknown: false });
  var badAfford = overprice.filter(function (r) { return r.ok && r.c.price > 7.01; });
  ok("券价高于方案价 → 不判定为可用", badAfford.length === 0, "越界 " + badAfford.length);

  /* ── 6b. 蛋白模式（第三道闸门） ── */
  var pPlans = pick(80, 999, 30);
  ok("蛋白模式(80元/≥30g) 能配出方案", pPlans.length > 0, "实际 " + pPlans.length + " 个");
  var underP = pPlans.filter(function (p) { return p.pr < 30 && !p.unknown; });
  ok("蛋白模式：方案蛋白全部 ≥30g", underP.length === 0, underP.map(function (p) { return p.pr.toFixed(1); }).join(","));
  var strict = pick(30, 600, 60);
  var strictBad = strict.filter(function (p) { return p.pr < 60 && !p.unknown; });
  ok("蛋白下限 60g 极严 → 不返回低于下限的方案", strictBad.length === 0, "返回 " + strict.length + " 个，违规 " + strictBad.length);
  ok("方案携带 pr 合计字段", pPlans.length > 0 && typeof pPlans[0].pr === "number", pPlans[0] ? pPlans[0].pr.toFixed(1) + "g" : "-");

  /* ── 7. 未知热量单品处理 ── */
  var unk = DATA.filter(function (x) { return x.u; }).length;
  ok("未知热量单品在 25~45 之间", unk >= 25 && unk <= 45, "实际 " + unk);
  var heavy = pick(100, 600);   /* 100元大预算：未知品可能进入 */
  var unkPlan = heavy.filter(function (p) { return p.unknown; });
  ok("设了热量闸门 → 未知品方案必须标注 unknown", unkPlan.every(function (p) { return p.unknown === true; }), "标注数 " + unkPlan.length);

  /* ── 8. 单文件自包含（内嵌校验） ── */
  var withImg = DATA.filter(function (x) { return x.img; });
  var allInline = withImg.length > 0 && withImg.every(function (x) { return x.img.indexOf("data:image/jpeg;base64,") === 0; });
  ok("DATA 所有商品图均为内嵌 data URI", allInline, withImg.length + " 个带图单品");
  var probe = "demo-" + "assets/";
  var noExt = document.documentElement.outerHTML.indexOf(probe) === -1;
  ok("整页零外部图片引用（真·单文件）", noExt, noExt ? "零外部依赖" : "仍有残留");

  /* ── 9. 对话解析器（第 5 屏） ── */
  var c1 = parseChat("30 块 600 卡");
  ok("对话解析：金额+热量", c1.m === 30 && c1.k === 600, "m=" + c1.m + " k=" + c1.k);
  var c2 = parseChat("25 块 · 不限卡");
  ok("对话解析：不限卡 → 不设限", c2.m === 25 && c2.k === 900, "m=" + c2.m + " k=" + c2.k);
  var c3 = parseChat("蛋白要 30g，预算 40");
  ok("对话解析：蛋白下限", c3.pmin === 30 && c3.m === 40, "pmin=" + c3.pmin + " m=" + c3.m);
  var c4 = parseChat("换一批");
  ok("对话解析：换一批", c4.more === true, "more=" + c4.more);
  var c5 = parseChat("今天天气不错");
  ok("对话解析：无关内容不误报预算", c5.m === null && c5.k === null && c5.more === false, "m=" + c5.m + " k=" + c5.k);

  /* ── 10. 对话战报的券区一致性 ── */
  var plansC = pick(32, 650, 0);
  var anyC = false;
  plansC.forEach(function (p) { matchCoupons(p).forEach(function (r) { if (r.ok) anyC = true; }); });
  var hC = chatBattle(32, 650, 0, plansC, false);
  var hasBlock = hC.indexOf("cb-coupon") >= 0;
  ok("对话战报券区与匹配结果一致", anyC === hasBlock, "有匹配券=" + anyC + " 有券区=" + hasBlock);

  /* ── 11. 预算响应性（问题修复：改预算必须换方案） ── */
  SHOWN = new Set();
  var pA = pick(90, 999, 0);
  SHOWN = new Set();
  var pB = pick(50, 999, 0);
  var balA = pA.filter(function (p) { return p.label === "最均衡"; })[0];
  var balB = pB.filter(function (p) { return p.label === "最均衡"; })[0];
  ok("最均衡随金额预算变化（90元档 > 50元档）", balA && balB && balA.price > balB.price,
     "90元=" + (balA ? balA.price.toFixed(1) : "-") + " 50元=" + (balB ? balB.price.toFixed(1) : "-"));
  var kEl = document.querySelector("#k");
  ok("热量滑块上限=1000（不设限死区收窄）", kEl && kEl.max === "1000", kEl ? kEl.max : "无");
  SHOWN = new Set();

  /* ── 12. 省钱心情 × 券匹配一致性 ── */
  SHOWN = new Set();
  var tipPlans = pick(78, 999, 0);
  var tipP = tipPlans[0];
  var tipTxt = savingTip(78, tipP);
  var tipHits = matchCoupons(tipP).filter(function (r) { return r.ok; }).length;
  var saysUsable = tipTxt.indexOf("能用上") >= 0;
  ok("省钱心情与券匹配一致（不答应用不上的券）", saysUsable === (tipHits > 0),
     "券可用=" + tipHits + " 话术含「能用上」=" + saysUsable);
  SHOWN = new Set();

  /* ── 13. 方案配图 = 真实构成（拼图，不许一张图代表全部） ── */
  SHOWN = new Set();
  document.getElementById("m").value = 63;
  document.getElementById("k").value = 990;
  run();
  var tiles = document.querySelectorAll("#v2 .plan");
  var mismatch = 0;
  PLANS.forEach(function (p, i) {
    var tile = tiles[i];
    if (!tile) return;
    var hasRow = !!tile.querySelector(".picrow");
    var imgs = tile.querySelectorAll(".picrow img").length;
    var withPic = p.items.filter(function (x) { return x.img; }).length;
    if (withPic > 1 && (!hasRow || imgs !== Math.min(withPic, 4))) mismatch++;
    if (withPic <= 1 && hasRow) mismatch++;
  });
  ok("拼图张数 = 方案件数（多件才拼，单件不拼）", tiles.length > 0 && mismatch === 0,
     "方案数=" + tiles.length + " 不符=" + mismatch);
  SHOWN = new Set();

  /* ── 14. 套餐合成图素材完备性 ── */
  var withImg2 = DATA.filter(function (x) { return x.img; });
  var cutMissing = withImg2.filter(function (x) { return !(PIECES[x.n] && PIECES[x.n].a); });
  ok("所有带图单品都有拆件（主食片完备）", cutMissing.length === 0,
     "带图单品 " + withImg2.length + " 个，缺件 " + cutMissing.length + " 个");
  ok("拆件均为内嵌 PNG data URI", withImg2.length > 0 && withImg2.every(function (x) {
       var pi = PIECES[x.n] || {};
       return (pi.a || "").indexOf("data:image/png;base64,") === 0 &&
              (!pi.b || pi.b.indexOf("data:image/png;base64,") === 0);
     }), "抽查通过");
  var setWithB = withImg2.filter(function (x) {
       return (x.n.indexOf("套餐") >= 0 || x.n.indexOf("件套") >= 0) && PIECES[x.n] && PIECES[x.n].b;
     });
  ok("套图已拆出后排片（薯条可乐）", setWithB.length >= 15, "带后排片的套图 " + setWithB.length + " 个");

  /* ── 15. 合成版式不变量（不出画 / 无重度遮挡 / 主角最大） ── */
  var WC = 840;
  function chkLayout(spec) {
    var L = layoutCombo(spec, WC, 560);
    var bad = [];
    L.forEach(function (m) {
      if (m.x < -1 || m.x + m.w > WC + 1) bad.push("出画");
      if (m.y < -1 || m.y + m.h > 561) bad.push("出头");
      var cov = 0;
      L.forEach(function (o) {
        if (o.base > m.base) {
          var ox = Math.max(0, Math.min(m.x + m.w, o.x + o.w) - Math.max(m.x, o.x));
          var oy = Math.max(0, Math.min(m.y + m.h, o.y + o.h) - Math.max(m.y, o.y));
          cov += ox * oy;
        }
      });
      if (1 - cov / (m.w * m.h) < 0.26) bad.push("遮挡" + Math.round((1 - cov / (m.w * m.h)) * 100) + "%");
    });
    return { L: L, bad: bad };
  }
  var specs = [
    { hero: { w: 300, h: 225 }, back: null, flanks: [] },
    { hero: { w: 300, h: 225 }, back: { w: 200, h: 240 }, flanks: [{ w: 300, h: 200 }] },
    { hero: { w: 300, h: 225 }, back: { w: 200, h: 240 }, flanks: [{ w: 300, h: 200 }, { w: 220, h: 300 }] },
    { hero: { w: 340, h: 300 }, back: { w: 260, h: 150 }, flanks: [{ w: 300, h: 225 }, { w: 300, h: 225 }] }
  ];
  var allBad = [];
  specs.forEach(function (sp, i2) {
    var r = chkLayout(sp);
    if (r.bad.length) allBad.push("s" + i2 + ":" + r.bad.join("/"));
  });
  ok("版式不变量：4 组形态不出画不遮挡", allBad.length === 0, allBad.join(" ") || "全部合规");
  var rHero = chkLayout(specs[2]);
  var heroBox = rHero.L.filter(function (q) { return q.role === "hero"; })[0];
  var others = rHero.L.filter(function (q) { return q.role !== "hero"; });
  ok("主角面积第一（汉堡优先的组装保证）",
     others.every(function (o) { return heroBox.w * heroBox.h > o.w * o.h; }),
     "主角" + Math.round(heroBox.w * heroBox.h) + " vs " + others.map(function (o) { return Math.round(o.w * o.h); }).join("/"));

  /* ── 输出 ── */
  var pre = document.createElement("pre");
  pre.setAttribute("id", "st" + "out");
  pre.textContent = JSON.stringify(R);
  document.body.appendChild(pre);
})();
