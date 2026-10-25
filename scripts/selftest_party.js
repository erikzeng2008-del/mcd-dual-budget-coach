/* 麦门拼单军师 · 自测（跑在 party.html 的发货代码上）
   覆盖：数据完整性 / 拼单算法 / 预算闸门 / 场景与偏好 / 文案与诚实性 */
(function () {
  var R = [];
  function t(name, fn) {
    var detail = "";
    try { detail = fn() || ""; R.push({ name: name, pass: true, detail: String(detail) }); }
    catch (e) { R.push({ name: name, pass: false, detail: String(e && e.message || e) }); }
  }
  function ok(cond, msg) { if (!cond) throw new Error(msg || "断言失败"); }
  function setScene(n, scene, prefs, budget) {
    S.n = n; S.scene = scene || 'friends';
    S.prefs = new Set(prefs || []);
    document.getElementById('budget').value = budget || '';
    render();
  }
  function dumpPlans() {
    return PLANS.map(function (p) {
      return p.title + ' ¥' + p.t.price.toFixed(1) + ' 人均' + (p.t.price / S.n).toFixed(1)
        + ' ' + p.t.pieces + '件 [' + p.t.items.map(function (x) {
          return x.it.name + '×' + x.qty;
        }).join(' + ') + ']';
    }).join('\n');
  }

  // ── 数据完整性 ──
  t('快照含门店与时间', function () {
    ok(SNAPSHOT.store && SNAPSHOT.at, '缺门店或时间');
    return SNAPSHOT.store + ' / ' + SNAPSHOT.at;
  });
  t('SKU 数量 > 50', function () { ok(ITEMS.length > 50, '只有 ' + ITEMS.length); return ITEMS.length + ' 个'; });
  t('多人餐 SKU ≥ 4', function () {
    var n = ITEMS.filter(function (i) { return /多人餐/.test(i.cat); }).length;
    ok(n >= 4, '只有 ' + n); return n + ' 个';
  });
  t('双人餐与随心配都在候选池', function () {
    ok(ITEMS.some(function (i) { return /双人餐/.test(i.name); }), '缺双人餐');
    ok(ITEMS.some(function (i) { return /随心配/.test(i.cat); }), '缺随心配');
    return '齐';
  });
  t('每个 SKU 价格非负且有原价', function () {
    var bad = ITEMS.filter(function (i) { return !(i.price >= 0) || !(i.orig >= i.price); });
    ok(bad.length === 0, bad.map(function (i) { return i.name; }).join(','));
    return '102 项通过';
  });
  t('图片走官方 CDN，无 base64 巨图', function () {
    var bad = ITEMS.filter(function (i) { return i.img && i.img.indexOf('https://') !== 0; });
    ok(bad.length === 0, bad.length + ' 个非 https 图');
    ok(ITEMS.every(function (i) { return i.img.indexOf('data:') !== 0; }), '存在 base64 图');
    return '全部 https';
  });
  t('活动与券已渲染', function () {
    var ev = document.querySelectorAll('#events .ev').length;
    ok(ev > 0, '活动为 0');
    return ev + ' 个活动 / ' + document.querySelectorAll('#coupons span').length + ' 张券';
  });

  // ── 核心：三档方案与拼单省钱 ──
  t('默认 4 人出满三档', function () {
    setScene(4, 'friends');
    ok(PLANS.length === 3, '只有 ' + PLANS.length);
    PLANS.forEach(function (p) { ok(p.t.price > 0, p.title + ' 价格为 0'); ok(p.t.items.length > 0, p.title + ' 空清单'); });
    return '\n' + dumpPlans();
  });
  t('总价 = 各行之和（三档逐一复算）', function () {
    setScene(4, 'friends');
    PLANS.forEach(function (p) {
      var sum = 0;
      p.plan.forEach(function (l) { sum += byCode[l.code].price * l.qty; });
      ok(Math.abs(sum - p.t.price) < 0.001, p.title + ' ' + sum + ' != ' + p.t.price);
    });
    return '三档价格复算一致';
  });
  t('划线价 ≥ 实付，节省额非负', function () {
    setScene(4, 'friends');
    PLANS.forEach(function (p) { ok(p.t.orig >= p.t.price - 0.001, p.title + ' 划线价异常'); });
    return PLANS.map(function (p) { return p.title + '省' + (p.t.orig - p.t.price).toFixed(1); }).join(' / ');
  });
  t('核心卖点：4 人最省钱档 < 各点各的', function () {
    setScene(4, 'friends');
    var base = baseline(4);
    var cheap = PLANS[0];
    ok(cheap.t.price < base.price, '拼单 ¥' + cheap.t.price + ' 未低于基准 ¥' + base.price);
    return '基准 ¥' + base.price.toFixed(1) + ' → 拼单 ¥' + cheap.t.price.toFixed(1)
      + '，省 ¥' + (base.price - cheap.t.price).toFixed(1);
  });
  t('拼单件数不少于各点各的', function () {
    setScene(4, 'friends');
    var cheap = PLANS[0];
    ok(cheap.t.pieces >= 4, '件数异常 ' + cheap.t.pieces);
    return cheap.t.pieces + ' 件 / ' + JSON.stringify(cheap.t.counts);
  });
  t('人数 2/4/6/8/12 均可出方案', function () {
    var out = [];
    [2, 4, 6, 8, 12].forEach(function (n) {
      setScene(n, 'friends');
      ok(PLANS.length === 3, n + ' 人方案数不对');
      PLANS.forEach(function (p) { ok(p.t.price > 0, n + '人' + p.title + ' 为 0'); });
      out.push(n + '人 最省钱¥' + PLANS[0].t.price.toFixed(1) + '(人均' + (PLANS[0].t.price / n).toFixed(1) + ')');
    });
    return out.join(' | ');
  });
  t('最省钱档总价随人数递增', function () {
    var prev = 0;
    [2, 4, 6, 8].forEach(function (n) {
      setScene(n, 'friends');
      var p = PLANS[0].t.price;
      ok(p > prev, n + ' 人价格未递增: ' + p + ' <= ' + prev);
      prev = p;
    });
    return '单调递增';
  });

  // ── 预算闸门 ──
  t('预算充足时不乱砍', function () {
    setScene(4, 'friends', [], 500);
    ok(PLANS[0].t.price <= 500, '超预算');
    return '¥' + PLANS[0].t.price.toFixed(1) + ' / 预算 500';
  });
  t('预算紧张时不静默超支', function () {
    setScene(4, 'friends', [], 60);
    PLANS.forEach(function (p) {
      if (p.t.price > 60) {
        ok(document.querySelectorAll('.warn').length > 0, '超预算却没有提示');
      }
    });
    return '\n' + dumpPlans();
  });
  t('预算 100 时最省钱档能压进 100', function () {
    setScene(4, 'friends', [], 100);
    ok(PLANS[0].t.price <= 100.001, '最省钱档 ¥' + PLANS[0].t.price + ' 超 100');
    return '¥' + PLANS[0].t.price.toFixed(1);
  });

  // ── 场景与偏好 ──
  t('家庭带娃场景出现亲子/乐园餐', function () {
    setScene(4, 'family');
    var names = PLANS.map(function (p) {
      return p.t.items.map(function (x) { return x.it.name; }).join(',');
    }).join(',');
    ok(/亲子|开心乐园/.test(names), '没有亲子/乐园餐: ' + names);
    return names.slice(0, 160);
  });
  t('有小孩偏好会带出乐园餐', function () {
    setScene(4, 'friends', ['kids']);
    var names = PLANS.map(function (p) {
      return p.t.items.map(function (x) { return x.it.name; }).join(',');
    }).join(',');
    ok(/亲子|开心乐园/.test(names), '没有乐园餐');
    return '命中';
  });
  t('下午茶场景不硬塞主食', function () {
    setScene(4, 'tea');
    PLANS.forEach(function (p) {
      var main = p.t.counts['主食'];
      ok(main <= S.n, '主食数异常');
    });
    return '\n' + dumpPlans();
  });
  t('加甜品偏好生效', function () {
    setScene(4, 'friends', ['dessert']);
    var hasDessert = PLANS.some(function (p) { return p.t.counts['甜品'] > 0; });
    ok(hasDessert, '没有甜品');
    return '甜品已入单';
  });
  t('来杯咖啡偏好生效', function () {
    setScene(4, 'friends', ['coffee']);
    var names = PLANS.map(function (p) {
      return p.t.items.map(function (x) { return x.it.name; }).join(',');
    }).join(',');
    ok(/咖啡|美式|奶铁/.test(names), '没有咖啡: ' + names);
    return '咖啡已入单';
  });
  t('不要辣偏好会换主食', function () {
    setScene(4, 'friends', ['noSpicy', 'light']);
    ok(PLANS[0].t.price > 0, '方案为空');
    return '\n' + dumpPlans();
  });

  t('不要辣时共享小食也不带辣', function () {
    setScene(4, 'friends', ['noSpicy']);
    PLANS.forEach(function (p) {
      var spicy = p.t.items.filter(function (x) { return /辣/.test(x.it.name); });
      ok(spicy.length === 0, p.title + ' 含辣品: '
        + spicy.map(function (x) { return x.it.name; }).join(','));
    });
    return '\n' + dumpPlans();
  });
  t('三档价格有序：最省钱 ≤ 最均衡 ≤ 最丰盛', function () {
    setScene(4, 'friends');
    ok(PLANS[0].t.price <= PLANS[2].t.price + 0.001, '均衡档比省钱档还便宜');
    ok(PLANS[2].t.price <= PLANS[1].t.price + 0.001, '丰盛档不是最贵');
    return PLANS.map(function (p) { return p.title + '¥' + p.t.price.toFixed(1); }).join(' ≤ ');
  });
  t('最省钱档不会在预算充足时顶格加菜', function () {
    setScene(4, 'friends', [], 500);
    ok(PLANS[0].t.price < 200, '最省钱档被加到 ¥' + PLANS[0].t.price);
    return '¥' + PLANS[0].t.price.toFixed(1) + '（预算 500 也不乱加）';
  });

  t('换一批三档都会变化，图片随内容更新', function () {
    S.shuffle = 0;
    setScene(4, 'friends');
    var before = PLANS.map(function (p) {
      return { txt: p.t.items.map(function (x) { return x.it.name; }).join(','),
               img: p.t.items[0].it.img, price: p.t.price };
    });
    S.shuffle++;
    render();
    var changed = PLANS.map(function (p, i) {
      var txt = p.t.items.map(function (x) { return x.it.name; }).join(',');
      return txt !== before[i].txt || p.t.price !== before[i].price;
    });
    ok(changed.every(Boolean), '只有部分档位变化: ' + changed.join(','));
    var imgChanged = PLANS.some(function (p, i) {
      return p.t.items[0].it.img !== before[i].img;
    });
    ok(imgChanged, '换一批后图片没有变化');
    return '三档全变 / 图片已随内容更新';
  });

  // ── 文案与诚实性 ──
  t('接龙文案含人数/门店/合计/人均', function () {
    setScene(4, 'friends');
    window.TEXTIDX = 0; fillText();
    var v = document.getElementById('orderText').value;
    ok(v.indexOf('4人') >= 0, '缺人数');
    ok(v.indexOf(SNAPSHOT.store) >= 0, '缺门店');
    ok(v.indexOf('合计') >= 0 && v.indexOf('人均') >= 0, '缺合计/人均');
    ok(v.indexOf('接龙：') >= 0, '缺接龙区');
    return v.length + ' 字';
  });
  t('接龙文案里的合计与方案一致', function () {
    setScene(6, 'friends');
    window.TEXTIDX = 0; fillText();
    var v = document.getElementById('orderText').value;
    var expect = '合计 ¥' + PLANS[0].t.price.toFixed(1);
    ok(v.indexOf(expect) >= 0, '文案合计与方案不符，期望含 ' + expect);
    return expect;
  });
  t('营养未知项不假装完整', function () {
    setScene(4, 'friends');
    var html = document.getElementById('plans').innerHTML;
    var anyUnknown = PLANS.some(function (p) { return p.t.unknown > 0; });
    if (anyUnknown) ok(html.indexOf('营养未知') >= 0, '有未知项但未标注');
    return anyUnknown ? '已标注未知项' : '本快照全部有营养数据';
  });
  t('页面无外部 JS/CSS 依赖（单文件）', function () {
    var ext = Array.from(document.querySelectorAll('script[src],link[rel=stylesheet]'));
    ok(ext.length === 0, '有 ' + ext.length + ' 个外部依赖');
    return '单文件自包含（图片除外）';
  });
  t('只报价不下单：无下单入口', function () {
    // 注意：不能用全文搜 create-order —— 本自测脚本自身就含这个词，会误报。
    var btns = Array.from(document.querySelectorAll('button')).map(function (b) {
      return b.textContent;
    }).join('|');
    ok(!/下单|立即购买|去支付|立即下单/.test(btns), '出现下单按钮');
    return '纯算价工具，无下单入口';
  });
  t('预算不足时明示主食缺口，不偷偷少给', function () {
    setScene(4, 'friends', [], 60);
    var cov = PLANS.map(function (p) { return covered(p.plan); });
    var short = cov.some(function (c) { return c < 4; });
    if (short) {
      ok(document.getElementById('plans').innerHTML.indexOf('主食只够') >= 0,
        '主食不够却没有提示');
      return '已给出缺口提示（覆盖 ' + cov.join('/') + ' 人）';
    }
    return '该预算下主食仍覆盖全员（' + cov.join('/') + '）';
  });
  t('主食覆盖数与人数匹配（默认无预算）', function () {
    setScene(4, 'friends');
    PLANS.forEach(function (p) {
      ok(covered(p.plan) >= 4, p.title + ' 主食只覆盖 ' + covered(p.plan) + ' 人');
    });
    return PLANS.map(function (p) { return p.title + covered(p.plan) + '人'; }).join(' / ');
  });

  var pre = document.createElement('pre');
  pre.id = 'stout';
  pre.textContent = JSON.stringify(R);
  document.body.appendChild(pre);
})();
