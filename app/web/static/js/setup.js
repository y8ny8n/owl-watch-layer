/* OWL 설치 마법사 — 5단계 클라이언트 스테퍼 + 저장 API 호출.
   준비체크 → AI엔진 → 데이터소스 → 분석설정 → 완료. 각 '다음'에서 해당 단계 저장. */
(function () {
  "use strict";

  var steps = Array.prototype.slice.call(document.querySelectorAll(".step"));
  var cur = 0;

  // 마법사 누적 상태
  var wizard = {
    engine: "local",
    model: null,
    sources: {},   // key -> on
    sensitivity: "balanced",
    workhour_start: "09:00",
    workhour_end: "18:00",
    auto_adjust: true,
  };

  // 실제 채널교차 분석 대상(exfil.py UNION)과 1:1. key = 채널 코드, tbl = 실제 PCFILTER 테이블.
  var SOURCES = [
    { key: "media", name: "매체 반출 (USB·외장)", desc: "USB·외장장치로 파일 반출", tbl: "log_dlp_media_t", rows: "1,284,502행" },
    { key: "fileattach", name: "파일 첨부", desc: "메신저·메일·웹 첨부 전송", tbl: "log_dlp_fileattach_t", rows: "902,140행" },
    { key: "website", name: "웹 업로드", desc: "웹사이트 업로드·게시", tbl: "log_dlp_website_t", rows: "512,880행" },
    { key: "sharedfolder", name: "공유폴더", desc: "네트워크 공유폴더 반출", tbl: "log_dlp_sharedfolder_t", rows: "88,120행" },
    { key: "chatgpt", name: "생성형 AI", desc: "ChatGPT 등 붙여넣기·업로드", tbl: "log_dlp_chatgpt_t", rows: "12,043행" },
  ];
  SOURCES.forEach(function (s) { wizard.sources[s.key] = true; });

  var ENGINE_LABEL = { local: "로컬 Ollama", internal: "사내 LLM", cloud: "외부 클라우드 API" };
  var SENS_LABEL = { strict: "엄격", balanced: "균형", lenient: "관대" };

  function show(n) {
    steps.forEach(function (el, i) { el.classList.toggle("hide", i !== n); });
    cur = n;
    window.scrollTo(0, 0);
    if (n === 0) loadChecks();
    if (n === 1) loadEngine();
    if (n === 2) loadDatasource();
    if (n === 4) renderSummary();
  }

  function api(method, url, body) {
    var opts = { method: method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    return fetch(url, opts).then(function (r) { return r.json(); });
  }

  /* ── STEP 0 · 준비 체크 ── */
  function checkRow(state, name, detail) {
    var ico = state === "ok" ? '<span class="check-ico ok">✓</span>'
      : state === "warn" ? '<span class="check-ico warn">!</span>'
      : '<span class="check-ico wait">…</span>';
    return '<div class="check-row">' + ico +
      '<div class="check-main"><div class="check-name">' + name + '</div>' +
      '<div class="check-detail">' + detail + '</div></div></div>';
  }
  function loadChecks() {
    var box = document.getElementById("checkList");
    api("GET", "/api/setup/checks").then(function (c) {
      box.innerHTML =
        checkRow(c.server.ok ? "ok" : "warn", "서버 환경", c.server.detail) +
        checkRow(c.pfdb.ok ? "ok" : "warn", "PCFILTER DB (pfdb) 연결", c.pfdb.detail) +
        checkRow("ok", "localhost 전용", c.localhost.detail) +
        checkRow(c.ai_engine.ok ? "ok" : "wait", "AI 엔진", c.ai_engine.detail);
    }).catch(function () {
      box.innerHTML = checkRow("warn", "환경 확인 실패", "서버 응답 없음 — 새로고침 해보세요");
    });
  }

  /* ── STEP 1 · AI 엔진 ── */
  function enginePanelHtml(engine, models, stat) {
    if (engine === "local") {
      var opts = (models && models.length ? models : ["gemma3:4b"]).map(function (m) {
        return '<option' + (m === wizard.model ? " selected" : "") + '>' + m + "</option>";
      }).join("");
      return '<p class="subhead">로컬 Ollama 설정</p>' +
        '<div class="field-row"><span class="field-label">모델</span><select id="modelSelect">' + opts + '</select></div>' +
        '<div class="stat-line">' + stat + '</div>' +
        '<button class="test-btn" id="testBtn" type="button">연결 테스트</button>';
    }
    if (engine === "internal") {
      return '<p class="subhead">사내 LLM 설정</p>' +
        '<div class="field-row"><span class="field-label">서버 URL</span><input id="intUrl" type="text" value="http://llm.internal:8000" style="flex:1"></div>' +
        '<div class="field-row"><span class="field-label">모델</span><input id="intModel" type="text" value="qwen2.5:14b" style="flex:1"></div>' +
        '<div class="stat-line"><span class="stat-ok">회사 내부 · 무유출</span></div>';
    }
    return '<p class="subhead">외부 클라우드 설정</p>' +
      '<div class="field-row"><span class="field-label">제공자</span><select id="cloudProvider"><option>Claude</option><option>OpenAI GPT</option></select></div>' +
      '<div class="stat-line"><span class="opt-badge warn">마스킹 강제 (끌 수 없음)</span><span class="muted" style="font-size:13px">개인정보·고객코드는 가려서 전송</span></div>';
  }
  function loadEngine() {
    setEngineSelection(wizard.engine);
    api("GET", "/api/setup/models").then(function (m) {
      var stat = m.ok
        ? '<span class="stat-ok">✓ ' + (m.detail || "실행 중") + "</span>"
        : '<span class="stat-wait">Ollama 대기 중 — 실행되면 감지돼요</span>';
      wizard._models = m.models || [];   // ★ 드롭다운 옵션 소스 — 이걸 안 채워서 항상 폴백(gemma3:4b)만 떴음
      if (!wizard.model && wizard._models.length) wizard.model = wizard._models[0];
      rerenderPanel(stat);
    }).catch(function () { rerenderPanel('<span class="stat-wait">감지 실패</span>'); });
  }
  function rerenderPanel(stat) {
    var panel = document.getElementById("enginePanel");
    panel.innerHTML = enginePanelHtml(wizard.engine, wizard._models, stat || "");
    bindPanel();
  }
  function bindPanel() {
    var sel = document.getElementById("modelSelect");
    if (sel) sel.addEventListener("change", function () { wizard.model = sel.value; });
    var tb = document.getElementById("testBtn");
    if (tb) tb.addEventListener("click", function () {
      tb.textContent = "테스트 중…";
      api("GET", "/api/setup/models").then(function (m) {
        tb.textContent = m.ok ? "✓ 연결 성공" : "✗ 응답 없음";
        setTimeout(function () { tb.textContent = "연결 테스트"; }, 2000);
      });
    });
  }
  function setEngineSelection(engine) {
    wizard.engine = engine;
    Array.prototype.forEach.call(document.querySelectorAll("#engineOpts .opt"), function (o) {
      o.classList.toggle("sel", o.getAttribute("data-engine") === engine);
    });
    rerenderPanel(document.querySelector("#enginePanel .stat-line") ? document.querySelector("#enginePanel .stat-line").innerHTML : "");
  }
  Array.prototype.forEach.call(document.querySelectorAll("#engineOpts .opt"), function (o) {
    o.addEventListener("click", function () { setEngineSelection(o.getAttribute("data-engine")); });
  });

  /* ── STEP 2 · 데이터 소스 ── */
  function loadDatasource() {
    api("GET", "/api/setup/checks").then(function (c) {
      var badge = document.getElementById("connBadge");
      var detail = document.getElementById("connDetail");
      var card = document.getElementById("connCard");
      if (c.pfdb.ok) {
        detail.textContent = c.pfdb.detail; badge.textContent = "정상"; badge.classList.remove("fail");
      } else {
        detail.textContent = c.pfdb.detail; badge.textContent = "연결 안 됨"; badge.classList.add("fail");
        card.querySelector(".check-ico").classList.remove("ok");
        card.querySelector(".check-ico").classList.add("warn");
        card.querySelector(".check-ico").textContent = "!";
      }
    });
    renderSources();
  }
  function renderSources() {
    var box = document.getElementById("srcList");
    box.innerHTML = SOURCES.map(function (s) {
      var on = wizard.sources[s.key];
      return '<div class="src-row">' +
        '<div class="src-main"><span class="src-name">' + s.name + '</span><span class="src-rows">' + s.rows + '</span>' +
        '<div class="src-desc">' + s.desc + '</div>' +
        '<span class="src-tbl">' + s.tbl + '</span></div>' +
        '<div class="toggle' + (on ? " on" : "") + '" data-src="' + s.key + '"><span class="knob"></span></div></div>';
    }).join("");
    Array.prototype.forEach.call(box.querySelectorAll(".toggle"), function (t) {
      t.addEventListener("click", function () {
        var k = t.getAttribute("data-src");
        wizard.sources[k] = !wizard.sources[k];
        t.classList.toggle("on", wizard.sources[k]);
      });
    });
  }

  /* ── STEP 3 · 분석 설정 ── */
  Array.prototype.forEach.call(document.querySelectorAll("#presetGrid .preset"), function (p) {
    p.addEventListener("click", function () {
      wizard.sensitivity = p.getAttribute("data-preset");
      Array.prototype.forEach.call(document.querySelectorAll("#presetGrid .preset"), function (x) {
        var sel = x === p;
        x.classList.toggle("sel", sel);
        var chk = x.querySelector(".p-check");
        if (sel && !chk) { var c = document.createElement("div"); c.className = "p-check"; c.textContent = "✓"; x.appendChild(c); }
        if (!sel && chk) chk.remove();
      });
    });
  });
  var autoT = document.getElementById("autoAdjust");
  autoT.addEventListener("click", function () {
    wizard.auto_adjust = !wizard.auto_adjust;
    autoT.classList.toggle("on", wizard.auto_adjust);
  });

  /* ── STEP 4 · 완료 요약 ── */
  function renderSummary() {
    var srcOn = SOURCES.filter(function (s) { return wizard.sources[s.key]; }).length;
    var rows = [
      ["AI 엔진", ENGINE_LABEL[wizard.engine] + (wizard.engine === "local" && wizard.model ? " · " + wizard.model : ""), wizard.engine === "cloud" ? "마스킹" : "무유출"],
      ["데이터 소스", srcOn + "종 연결 · pfdb 읽기 전용", "실시간"],
      ["민감도", SENS_LABEL[wizard.sensitivity] + " (겹치는 신호부터)", wizard.sensitivity === "balanced" ? "권장" : ""],
      ["자동 기준 조정", wizard.auto_adjust ? "30일 학습 켜짐" : "꺼짐", ""],
    ];
    document.getElementById("summaryCard").innerHTML = rows.map(function (r) {
      return '<div class="summary-row"><span class="summary-key">' + r[0] + '</span>' +
        '<span class="summary-val">' + r[1] + '</span>' +
        (r[2] ? '<span class="summary-tag">' + r[2] + "</span>" : "") + "</div>";
    }).join("");
  }

  /* ── 저장 (각 단계 '다음'에서) ── */
  function saveCurrent() {
    if (cur === 1) return api("POST", "/api/setup/ai-engine", { engine: wizard.engine, model: wizard.model });
    if (cur === 2) {
      var on = SOURCES.filter(function (s) { return wizard.sources[s.key]; }).map(function (s) { return s.key; });
      return api("POST", "/api/setup/datasource", { sources: on });
    }
    if (cur === 3) return api("POST", "/api/setup/analysis", {
      sensitivity: wizard.sensitivity,
      workhour_start: document.getElementById("whStart").value,
      workhour_end: document.getElementById("whEnd").value,
      auto_adjust: wizard.auto_adjust,
    });
    return Promise.resolve();
  }

  /* ── 내비게이션 ── */
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.hasAttribute && t.hasAttribute("data-next")) {
      saveCurrent().finally(function () { if (cur < steps.length - 1) show(cur + 1); });
    } else if (t.hasAttribute && t.hasAttribute("data-prev")) {
      if (cur > 0) show(cur - 1);
    }
  });

  document.getElementById("finishBtn").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true; btn.textContent = "완료 중…";
    api("POST", "/api/setup/complete").then(function () { window.location.href = "/"; })
      .catch(function () { btn.disabled = false; btn.textContent = "대시보드 시작하기"; });
  });

  // 이미 저장된 설정을 마법사에 미리 채움 → /setup 이 '설정 변경' 화면 겸용
  function reflectPreload() {
    Array.prototype.forEach.call(document.querySelectorAll("#presetGrid .preset"), function (p) {
      var sel = p.getAttribute("data-preset") === wizard.sensitivity;
      p.classList.toggle("sel", sel);
      var chk = p.querySelector(".p-check");
      if (sel && !chk) { var c = document.createElement("div"); c.className = "p-check"; c.textContent = "✓"; p.appendChild(c); }
      if (!sel && chk) chk.remove();
    });
    document.getElementById("whStart").value = wizard.workhour_start || "09:00";
    document.getElementById("whEnd").value = wizard.workhour_end || "18:00";
    document.getElementById("autoAdjust").classList.toggle("on", wizard.auto_adjust);
  }

  function preload() {
    return api("GET", "/api/setup/status").then(function (s) {
      var cfg = s.config || {};
      var eng = cfg.ai_engine || {};
      var ds = cfg.datasource || {};
      var ana = cfg.analysis || {};
      if (eng.engine) wizard.engine = eng.engine;
      if (eng.model) wizard.model = eng.model;
      if (ds && Array.isArray(ds.sources)) {
        SOURCES.forEach(function (sx) { wizard.sources[sx.key] = ds.sources.indexOf(sx.key) >= 0; });
      }
      if (ana.sensitivity) wizard.sensitivity = ana.sensitivity;
      if (ana.workhour_start) wizard.workhour_start = ana.workhour_start;
      if (ana.workhour_end) wizard.workhour_end = ana.workhour_end;
      if (typeof ana.auto_adjust === "boolean") wizard.auto_adjust = ana.auto_adjust;
      reflectPreload();
    }).catch(function () { /* 최초 설치(저장값 없음) — 기본값 그대로 */ });
  }

  preload().then(function () { show(0); });
})();
