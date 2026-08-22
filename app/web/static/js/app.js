(function () {
  "use strict";

  var CHANNEL_LABEL = {
    media: "매체(USB)",
    fileattach: "파일첨부",
    website: "웹사이트",
    sharedfolder: "공유폴더",
    chatgpt: "생성형AI",
    capture: "캡처"
  };

  var SEVERITY_LABEL = { high: "고위험", mid: "주의", watch: "관심", low: "낮음" };

  // 워크플로우 상태 뱃지 (신규는 기본값이라 표시 안 함)
  var STATUS_LABEL = { reviewed: "검토됨", actioned: "조치됨", dismissed: "기각" };

  var state = {
    currentPno: null,
    currentTargetAgentId: null,
    currentTargetName: null,
    currentWindow: "7d", // 일(1d)/주(7d)/월(30d) 기간 렌즈. 기본 주.
    view: "reports",     // reports(피드) | watch(감시목록 상태 그룹)
    watchPins: [],       // 지속 관찰 핀된 pno 목록
    watchItems: [],      // 감시목록 현재 아이템(핀 토글 후 재렌더용)
    pendingPreview: null // {slots, target_agent_id, target_name}
  };

  var feedEl = document.getElementById("feed");
  var detailEl = document.getElementById("detail");
  var statusFilterEl = document.getElementById("statusFilter");
  var runBtn = document.getElementById("runBtn");
  var viewSeg = document.getElementById("viewSeg");
  var paneHead = document.getElementById("paneHead");
  var summaryBarEl = document.getElementById("summaryBar");

  var chatToggle = document.getElementById("chatToggle");
  var chatPanel = document.getElementById("chatPanel");
  var chatClose = document.getElementById("chatClose");
  var chatTargetInfo = document.getElementById("chatTargetInfo");
  var chatLog = document.getElementById("chatLog");
  var chatForm = document.getElementById("chatForm");
  var chatInput = document.getElementById("chatInput");

  var previewModal = document.getElementById("previewModal");
  var previewTarget = document.getElementById("previewTarget");
  var editScope = document.getElementById("editScope");
  var changePreview = document.getElementById("changePreview");
  var previewCancel = document.getElementById("previewCancel");
  var previewApprove = document.getElementById("previewApprove");

  var toastEl = document.getElementById("toast");
  var toastTimer = null;

  function showToast(message, isError) {
    toastEl.textContent = message;
    toastEl.classList.remove("hidden");
    toastEl.classList.toggle("error", !!isError);
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.add("hidden");
    }, 3200);
  }

  function severityBadgeClass(severity) {
    if (severity === "high") return "badge-high";
    if (severity === "mid") return "badge-mid";
    if (severity === "watch") return "badge-watch-sev";
    return "badge-low";
  }

  function persistBadge(weeks) {
    weeks = weeks || 0;
    if (weeks < 2) return "";
    return '<span class="badge badge-persist">🔁 지속 ' + weeks + "주</span>";
  }

  function statusBadge(status) {
    var label = STATUS_LABEL[status];
    if (!label) return "";
    return '<span class="badge badge-status badge-status-' + status + '">' + label + "</span>";
  }

  function formatTime(value) {
    if (!value) return "";
    var d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return d.toLocaleString("ko-KR", { hour12: false });
  }

  // 로컬 AI 모델 태그 — 온프레미스 로컬 분석임을 명시 (클라우드 아님)
  function modelTag(modelName) {
    if (!modelName) return "";
    return ' <span class="model-tag" title="온프레미스 로컬 AI로 분석">🔒 로컬 ' + escapeHtml(modelName) + "</span>";
  }

  // 분석 기간 한 줄 — 이 판정이 어느 구간 로그를 본 것인지
  function periodText(start, end) {
    var s = new Date(start), e = new Date(end);
    if (isNaN(s.getTime()) || isNaN(e.getTime())) return "";
    var md = function (d) { return (d.getMonth() + 1) + "/" + d.getDate(); };
    var days = Math.max(1, Math.round((e - s) / 86400000));
    return "분석 기간 " + md(s) + " ~ " + md(e) + " (최근 " + days + "일)";
  }

  function channelChips(channels) {
    channels = channels || [];
    return channels.map(function (ch) {
      return '<span class="chip">' + (CHANNEL_LABEL[ch] || ch) + "</span>";
    }).join("");
  }

  // ── 스캔 요약바 ──

  function loadSummary() {
    fetch("/api/summary?window=" + encodeURIComponent(state.currentWindow))
      .then(function (res) { return res.json(); })
      .then(function (s) {
        var bar = document.getElementById("summaryBar");
        if (!bar) return;
        var parts = [];
        if (s.high) parts.push('<span class="sum-sev sum-high">고위험 ' + s.high + "</span>");
        if (s.mid) parts.push('<span class="sum-sev sum-mid">주의 ' + s.mid + "</span>");
        if (s.watch) parts.push('<span class="sum-sev sum-watch">관심 ' + s.watch + "</span>");
        bar.innerHTML =
          '전체 <b>' + (s.scanned != null ? s.scanned : "-") + "</b>명 스캔 &nbsp;→&nbsp; " +
          (parts.length ? parts.join(" ") : '<span class="sum-clear">이상 징후 없음</span>');
      })
      .catch(function () { /* 요약바는 부가정보 — 실패해도 피드는 정상 */ });
  }

  // ── 리포트 피드 ──

  function loadReports() {
    var params = ["window=" + encodeURIComponent(state.currentWindow)];
    if (state.view !== "watch") {
      var status = statusFilterEl.value;
      if (status) params.push("status=" + encodeURIComponent(status));
    }
    fetch("/api/reports?" + params.join("&"))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (state.view === "watch") {
          // 핀 목록을 먼저 받아 그룹 배치에 반영
          fetch("/api/watchlist/pins")
            .then(function (r) { return r.json(); })
            .then(function (p) { state.watchPins = p.pinned || []; renderWatchlist(data.items || []); })
            .catch(function () { renderWatchlist(data.items || []); });
        } else {
          renderFeed(data.items || []);
        }
      })
      .catch(function () { showToast("리포트 목록 조회 실패", true); });
  }

  function renderFeed(items) {
    if (!items.length) {
      feedEl.innerHTML = '<div class="empty-state">이 기간에는 표시할 리포트가 없습니다.</div>';
      detailEl.innerHTML = '<div class="empty-state">이 기간에는 이상 징후가 없습니다.</div>';
      state.currentPno = null;
      return;
    }
    feedEl.innerHTML = items.map(renderCard).join("");
    Array.prototype.forEach.call(feedEl.querySelectorAll(".report-card"), function (card) {
      card.addEventListener("click", function () {
        var pno = parseInt(card.getAttribute("data-pno"), 10);
        loadDetail(pno);
      });
    });

    // 최초 로드 시 상단 리포트 자동 선택 — 첫 화면부터 상세가 채워지도록
    if (state.currentPno == null && items.length) {
      loadDetail(items[0].pno);
    }
  }

  function renderCard(item) {
    var active = item.pno === state.currentPno ? " active" : "";
    return (
      '<div class="report-card' + active + '" data-pno="' + item.pno + '">' +
      '<div class="card-top">' +
      '<span class="badge ' + severityBadgeClass(item.severity) + '">' + (SEVERITY_LABEL[item.severity] || item.severity || "") + "</span>" +
      persistBadge(item.recurrence_weeks) +
      statusBadge(item.status) +
      '<span class="card-target">' + (item.target_user_name || item.target_user_id || "알 수 없음") + "</span>" +
      '<span class="card-score">위험도 ' + (item.risk_score != null ? item.risk_score : "-") + "</span>" +
      "</div>" +
      '<div class="chips">' + channelChips(item.channels) + "</div>" +
      '<div class="card-summary">' + escapeHtml(item.summary_text || "") + "</div>" +
      '<div class="card-time">' + formatTime(item.reg_time) + "</div>" +
      "</div>"
    );
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // ── 감시목록 (상태 그룹) ──

  function _isDone(it) { return it.status === "actioned" || it.status === "dismissed"; }
  function _isPersist(it) { return (it.recurrence_weeks || 0) >= 2; }

  // 리포트를 4그룹으로 배정 (우선순위: 마무리 > 핀(지속관찰) > 반출(고위험) > 2주반복(지속관찰) > 추적)
  function bucketReports(items) {
    var pins = state.watchPins || [];
    var g = { exfil: [], tracking: [], persist: [], done: [] };
    items.forEach(function (it) {
      if (_isDone(it)) g.done.push(it);
      else if (pins.indexOf(it.pno) >= 0) g.persist.push(it);  // 관리자 핀 = 지속 관찰 고정
      else if (it.severity === "high") g.exfil.push(it);
      else if (_isPersist(it)) g.persist.push(it);
      else g.tracking.push(it);
    });
    return g;
  }

  var WATCH_GROUPS = [
    ["exfil", "반출로 이어짐", "킬체인 완성 · 반출 발생", "wg-exfil"],
    ["tracking", "추적 중", "은폐 정황 · 지켜보는 중", "wg-track"],
    ["persist", "지속 관찰", "2주+ 반복 · 관리자 핀", "wg-persist"],
    ["done", "마무리됨", "조치됨 · 기각", "wg-done"]
  ];

  function renderWatchlist(items) {
    state.watchItems = items;
    if (!items.length) {
      feedEl.innerHTML = '<div class="empty-state">이 기간에는 감시 대상이 없습니다.</div>';
      detailEl.innerHTML = '<div class="empty-state">이 기간에는 이상 징후가 없습니다.</div>';
      state.currentPno = null;
      return;
    }
    var pins = state.watchPins || [];
    var g = bucketReports(items);
    feedEl.innerHTML = WATCH_GROUPS.map(function (o) {
      var arr = g[o[0]];
      if (!arr.length) return "";
      var cards = arr.map(function (it) {
        var card = renderCard(it);
        if (o[0] === "exfil") {
          card = card.replace('<div class="chips">', '<div class="chips"><span class="exfil-tag">USB 반출됨</span>');
        }
        if (o[0] !== "done") {
          var pinned = pins.indexOf(it.pno) >= 0;
          var label = pinned ? "📌 지속 관찰 중" : "지속 관찰 고정";
          card = card.replace('<div class="card-time">',
            '<div class="wg-pinrow"><button type="button" class="pin-btn' + (pinned ? " pinned" : "") +
            '" data-pno="' + it.pno + '" data-pinned="' + pinned + '">' + label + '</button></div><div class="card-time">');
        }
        return card;
      }).join("");
      return '<div class="watch-group ' + o[3] + '">' +
        '<div class="wg-head"><span class="wg-dot"></span>' +
        '<span class="wg-title">' + o[1] + '</span>' +
        '<span class="wg-count">' + arr.length + '</span>' +
        '<span class="wg-hint">' + o[2] + '</span></div>' +
        cards + "</div>";
    }).join("");

    Array.prototype.forEach.call(feedEl.querySelectorAll(".report-card"), function (card) {
      card.addEventListener("click", function () {
        loadDetail(parseInt(card.getAttribute("data-pno"), 10));
      });
    });
    Array.prototype.forEach.call(feedEl.querySelectorAll(".pin-btn"), function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var pno = parseInt(btn.getAttribute("data-pno"), 10);
        var newPinned = btn.getAttribute("data-pinned") !== "true";
        fetch("/api/watchlist/pin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pno: pno, pinned: newPinned })
        })
          .then(function (res) { return res.json(); })
          .then(function (d) {
            state.watchPins = d.pinned || [];
            showToast(newPinned ? "지속 관찰로 고정했습니다" : "지속 관찰 해제");
            renderWatchlist(state.watchItems);  // 그룹 재배치
          })
          .catch(function () { showToast("핀 저장 실패", true); });
      });
    });

    if (state.currentPno == null && items.length) loadDetail(items[0].pno);
  }

  function switchView(v) {
    if (v === state.view) return;
    state.view = v;
    Array.prototype.forEach.call(viewSeg.querySelectorAll(".vseg-btn"), function (b) {
      b.classList.toggle("vseg-active", b.getAttribute("data-view") === v);
    });
    paneHead.textContent = v === "watch" ? "감시 목록 · 상태별" : "감시 리포트";
    statusFilterEl.classList.toggle("hide", v === "watch");
    if (summaryBarEl) summaryBarEl.classList.toggle("hide", v === "watch");
    state.currentPno = null;
    if (v !== "watch") loadSummary();
    loadReports();
  }

  Array.prototype.forEach.call(viewSeg.querySelectorAll(".vseg-btn"), function (b) {
    b.addEventListener("click", function () { switchView(b.getAttribute("data-view")); });
  });

  // ── 리포트 상세 ──

  function loadDetail(pno) {
    fetch("/api/reports/" + pno)
      .then(function (res) { return res.json(); })
      .then(function (data) { renderDetail(data); })
      .catch(function () { showToast("리포트 상세 조회 실패", true); });
  }

  function renderDetail(report) {
    if (!report || !report.pno) {
      detailEl.innerHTML = '<div class="empty-state">리포트를 찾을 수 없습니다.</div>';
      return;
    }
    var targetChanged = state.currentPno !== report.pno;
    state.currentPno = report.pno;
    state.currentTargetAgentId = report.target_agent_id;
    state.currentTargetName = report.target_user_name || report.target_user_id;

    var signalsJson = report.signals_json || {};
    var signals = signalsJson.signals || [];
    var riskScore = report.risk_score != null ? report.risk_score : (signalsJson.risk_score || 0);
    var channels = signalsJson.channels || [];
    state.currentChannels = channels; // 챗 인사에 사용

    detailEl.innerHTML =
      '<div class="detail-header">' +
      '<span class="badge ' + severityBadgeClass(report.severity) + '">' + (SEVERITY_LABEL[report.severity] || report.severity || "") + "</span>" +
      persistBadge(signalsJson.recurrence_weeks) +
      '<span class="detail-title">' + escapeHtml(state.currentTargetName || "알 수 없음") + "</span>" +
      "</div>" +
      '<div class="detail-period">' + periodText(report.period_start, report.period_end) + "</div>" +
      '<div class="allow-note">⚠ 아래 반출은 모두 정책상 <b>‘허용’</b>으로 통과된 건입니다 — 룰이 못 잡는 회색지대</div>' +
      '<div class="chips">' + channelChips(channels) + "</div>" +
      '<div class="gauge-wrap">' +
      '<div class="gauge-label"><span>위험 점수</span><span>' + riskScore + ' / 100 · <b style="color:' + gaugeColor(report.severity) + '">' + (SEVERITY_LABEL[report.severity] || "") + "</b></span></div>" +
      segGauge(riskScore) +
      '<div class="gauge-scale">임계 — 관심 <b>20</b> · 주의 <b>35</b> · 고위험 <b>60</b> &nbsp;·&nbsp; 위험 신호가 겹칠수록 점수가 올라갑니다</div>' +
      "</div>" +
      '<div class="section-title">AI 진단' + modelTag(report.model_name) + "</div>" +
      '<div class="summary-box">' + escapeHtml(report.summary_text || "요약 없음") + "</div>" +
      '<div class="section-title">탐지된 위험 신호 · ' + signals.length + '개 겹침</div>' +
      '<div class="section-hint">각 신호의 <b>위험 +N</b>은 유출 정황의 강도(가중치)입니다. 회피가 뚜렷할수록 크고, 겹친 가중치의 합이 위 위험 점수예요.</div>' +
      '<button type="button" class="raw-log-btn" data-pno="' + report.pno + '">🔍 이 판정의 원본 로그 근거 보기</button>' +
      (signals.length ? signals.map(renderSignal).join("") : '<div class="empty-state">발동된 신호가 없습니다.</div>');

    // 피드의 active 표시 갱신
    Array.prototype.forEach.call(feedEl.querySelectorAll(".report-card"), function (card) {
      card.classList.toggle("active", parseInt(card.getAttribute("data-pno"), 10) === report.pno);
    });

    chatTargetInfo.textContent = "대상: " + (state.currentTargetName || "-") + " (agent_id: " + (state.currentTargetAgentId != null ? state.currentTargetAgentId : "-") + ")";

    // 다른 대상으로 전환하면 이전 대화·미리보기 초기화 (같은 리포트 재로드 시엔 유지)
    if (targetChanged) {
      state.pendingPreview = null;
      if (chatPanel && !chatPanel.classList.contains("hidden")) {
        renderChatIntro(); // 챗 열려 있으면 새 대상 인사·칩으로 갱신
      } else {
        chatLog.innerHTML = "";
      }
    }
  }

  function gaugeColor(severity) {
    if (severity === "high") return "#d64540";
    if (severity === "mid") return "#f5820a";
    if (severity === "watch") return "#3f83c9";
    return "#a89a86";
  }

  // 세그먼트 게이지 — 20칸, 점수만큼 채우고 초록→주황→빨강 스펙트럼으로 물듦
  function segGauge(score) {
    var n = 20;
    var s = Math.max(0, Math.min(100, score));
    var filled = Math.round((s / 100) * n);
    var out = '<div class="seg-gauge" role="img" aria-label="위험 점수 ' + s + ' / 100">';
    for (var i = 0; i < n; i++) {
      if (i < filled) {
        out += '<span class="seg on" style="background:' + segColor(i / (n - 1)) + '"></span>';
      } else {
        out += '<span class="seg"></span>';
      }
    }
    out += "</div>";
    out += '<div class="seg-ends"><span class="seg-safe">안전</span><span class="seg-danger">위험</span></div>';
    return out;
  }
  function segColor(t) {
    var g = [47, 158, 111], a = [245, 130, 10], r = [224, 85, 79];
    var c = t < 0.5 ? mixRgb(g, a, t / 0.5) : mixRgb(a, r, (t - 0.5) / 0.5);
    return "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
  }
  function mixRgb(a, b, t) {
    return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)];
  }

  var CATEGORY_LABEL = { 1: "웹하드", 2: "메신저", 6: "메일", 7: "개인 클라우드", 10: "원격제어", 100: "브라우저" };
  // 각 신호가 "왜 위험한지 / 왜 이 가중치인지" 한 줄 설명 (처음 보는 사용자용)
  var SIGNAL_DESC = {
    S1_ext_spoof: "확장자·이름을 바꿔 내용검사 회피 — 의도적이라 위험 큼",
    S2_zip_hide: "압축으로 내용을 가려 검사 우회",
    S3_enc_evade: "암호화로 검사 자체를 무력화",
    S4_mass_pri: "반출물에 개인정보가 대량 포함",
    S5_unofficial: "메일·정식경로가 아닌 채널로 반출",
    S6_night: "업무시간 외 반출 — 단독으론 약한 신호",
    S7_cross_channel: "여러 채널에 분산 반출 — 가장 강한 유출 정황",
    S8_genai_secret: "외부 생성형 AI에 개인정보·기밀 유출",
    S9_persistence: "일회성이 아니라 지속 반복 — 우발적이 아님"
  };

  var FAIL_REASON_LABEL = {
    password_protected_archive: "비밀번호 걸린 압축파일",
    encrypted_zip: "암호화된 압축파일",
    encrypted: "암호화되어 검사 불가"
  };

  function shortTime(v) {
    if (!v) return "";
    var d = new Date(v);
    if (isNaN(d.getTime())) return v;
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    return (d.getMonth() + 1) + "/" + d.getDate() + " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }

  // 신호 증거를 사람이 읽는 한 줄로 (영문 키·ISO 시각 대신)
  function evidenceLine(code, ev) {
    ev = ev || {};
    var t = ev.log_time ? ' <span class="ev-time">· ' + shortTime(ev.log_time) + "</span>" : "";
    switch (code) {
      case "S1_ext_spoof":
        return '<span class="ev-file">' + escapeHtml(ev.file_name || "") + '</span> <span class="ev-arrow">→</span> ' +
               '<span class="ev-file ev-danger">' + escapeHtml(ev.dst_file_name || "") + "</span>" + t;
      case "S2_zip_hide":
        return "압축으로 은닉: " + escapeHtml(ev.zip_filelist || "") + t;
      case "S3_enc_evade":
        return "검사 회피 — " + (FAIL_REASON_LABEL[ev.hash_extract_fail_reason] || escapeHtml(ev.hash_extract_fail_reason || "검사 불가")) + t;
      case "S4_mass_pri":
        return "개인정보 <b>" + escapeHtml(String(ev.total_pri_cnt != null ? ev.total_pri_cnt : "?")) + "건</b> 포함" + t;
      case "S5_unofficial":
        return "비공식 반출 경로: <b>" + (CATEGORY_LABEL[ev.category] || ("코드 " + ev.category)) + "</b>" + t;
      case "S6_night":
        return "업무시간 외(야간·주말) 반출" + t;
      case "S7_cross_channel":
        return (ev.channels || []).map(function (c) { return CHANNEL_LABEL[c] || c; }).join(" · ") + " <b>동시 반출</b>";
      case "S8_genai_secret":
        return "생성형 AI에 개인정보 <b>" + escapeHtml(String(ev.pri_cnt != null ? ev.pri_cnt : "?")) + "건</b> 붙여넣기" + t;
      case "S9_persistence":
        return "<b>" + escapeHtml(String(ev.weeks || 0)) + "주</b>에 걸쳐 반복" + (ev.first_seen ? " (최초 " + escapeHtml(ev.first_seen) + ")" : "");
      default:
        return Object.keys(ev).map(function (k) { return escapeHtml(k) + ": " + escapeHtml(String(ev[k])); }).join(" · ");
    }
  }

  function renderSignal(signal) {
    var weight = signal.weight || 0;
    var widthPct = Math.min(100, Math.round((weight / 30) * 100));
    var ev = signal.evidence || {};
    var chTag = ev.channel ? '<span class="signal-ch">' + (CHANNEL_LABEL[ev.channel] || ev.channel) + "</span>" : "";
    var desc = SIGNAL_DESC[signal.code] || "";
    return (
      '<div class="signal-row">' +
      '<div class="signal-top">' +
      '<span class="signal-name">' + escapeHtml(signal.name || signal.code || "") + "</span>" +
      chTag +
      (signal.mitre ? '<span class="signal-mitre">' + escapeHtml(signal.mitre) + "</span>" : "") +
      '<span class="signal-weight" title="위험 가중치">위험 +' + weight + "</span>" +
      "</div>" +
      (desc ? '<div class="signal-desc">' + desc + "</div>" : "") +
      '<div class="weight-bar"><div class="weight-fill" style="width:' + widthPct + '%"></div></div>' +
      '<div class="evidence-line">' + evidenceLine(signal.code, ev) + "</div>" +
      "</div>"
    );
  }

  // ── 지금 분석 ──

  runBtn.addEventListener("click", function () {
    runBtn.disabled = true;
    runBtn.textContent = "분석 중...";
    fetch("/api/reports/run", { method: "POST" })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        showToast("분석 완료 — " + (data.loaded != null ? data.loaded : 0) + "건 적재");
        loadSummary();
        loadReports();
      })
      .catch(function () { showToast("분석 실행 실패", true); })
      .finally(function () {
        runBtn.disabled = false;
        runBtn.textContent = "지금 분석";
      });
  });

  statusFilterEl.addEventListener("change", loadReports);

  // ── 기간 렌즈 세그먼트 (일/주/월) ──
  Array.prototype.forEach.call(document.querySelectorAll("#windowSeg .seg-btn"), function (btn) {
    btn.addEventListener("click", function () {
      var w = btn.getAttribute("data-window");
      if (w === state.currentWindow) return;
      state.currentWindow = w;
      Array.prototype.forEach.call(document.querySelectorAll("#windowSeg .seg-btn"), function (b) {
        b.classList.toggle("seg-active", b === btn);
      });
      state.currentPno = null; // 새 기간의 상단 리포트를 자동 선택하도록 초기화
      loadSummary();
      loadReports();
    });
  });

  // ── 챗 패널 (가이드형 정책봇) ──

  // 백엔드가 실제 적용 가능한 조치 = USB 매체 차단(야간/주말/상시). 칩은 결정적(ollama 우회).
  var SUGGEST_CHIPS = [
    { scope: "night", label: "야간 USB 차단", sub: "오늘 밤 22–06시" },
    { scope: "weekend", label: "주말 USB 차단", sub: "이번 주말" },
    { scope: "all", label: "상시 USB 차단", sub: "기간 제한 없음" }
  ];

  chatToggle.addEventListener("click", function () {
    chatPanel.classList.toggle("hidden");
    if (!chatPanel.classList.contains("hidden") && !chatLog.children.length) {
      renderChatIntro();
    }
  });
  chatClose.addEventListener("click", function () {
    chatPanel.classList.add("hidden");
  });

  function appendChatMsg(text, role) {
    var div = document.createElement("div");
    div.className = "chat-msg " + role;
    div.textContent = text;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function appendChatChips() {
    var wrap = document.createElement("div");
    wrap.className = "chat-chips";
    SUGGEST_CHIPS.forEach(function (ch) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "chat-chip";
      b.innerHTML = escapeHtml(ch.label) + '<span class="chip-sub">' + escapeHtml(ch.sub) + "</span>";
      b.addEventListener("click", function () { requestPreview({ scope: ch.scope }, ch.label); });
      wrap.appendChild(b);
    });
    chatLog.appendChild(wrap);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  // 챗 열 때(또는 대상 바뀔 때) 상황 인사 + 추천 칩
  function renderChatIntro() {
    chatLog.innerHTML = "";
    if (state.currentTargetAgentId == null) {
      appendChatMsg("먼저 왼쪽에서 리포트를 선택해주세요.", "bot");
      return;
    }
    var chans = (state.currentChannels || []).map(function (c) { return CHANNEL_LABEL[c] || c; });
    var chanText = chans.length ? chans.join(" · ") : "여러 채널";
    appendChatMsg("🦉 " + (state.currentTargetName || "이 대상") + " 님은 최근 " + chanText + "(으)로 반복 반출이 확인됐어요. 어떻게 조치할까요?", "bot");
    appendChatChips();
  }

  // 자유입력/칩 공통 — 미리보기 요청
  function requestPreview(payload, userLabel) {
    if (state.currentTargetAgentId == null) {
      showToast("먼저 리포트를 선택해주세요", true);
      return;
    }
    if (userLabel) appendChatMsg(userLabel, "user");
    var reqPno = state.currentPno; // 응답 지연 중 대상 바뀌면 버림
    var body = { target_agent_id: state.currentTargetAgentId };
    if (payload.scope) body.scope = payload.scope;
    if (payload.utterance) body.utterance = payload.utterance;
    fetch("/api/chat/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (state.currentPno !== reqPno) return;
        if (!data.understood) {
          appendChatMsg(data.message || "무슨 뜻인지 잘 모르겠어요. 아래에서 골라주세요.", "bot");
          appendChatChips();
          return;
        }
        appendChatMsg(data.message, "bot");
        openPreview(data);
      })
      .catch(function () { showToast("챗 요청 실패", true); });
  }

  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var utterance = chatInput.value.trim();
    if (!utterance) return;
    chatInput.value = "";
    requestPreview({ utterance: utterance }, utterance);
  });

  // 적용 시점(scope) → 사람이 읽는 한 줄 (서버 _scope_line 과 동일 개념)
  function scopeText(scope) {
    if (scope === "night") return "적용: 오늘 22:00 ~ 내일 06:00 (1회성)";
    if (scope === "weekend") return "적용: 이번 주말 (토·일)";
    return "적용: 상시 (기간 제한 없음)";
  }

  // 편집한 값으로 "허용 통과 → 차단" 변경 미리보기를 다시 그림
  function renderChangePreview() {
    if (!state.pendingPreview) return;
    var name = state.pendingPreview.target_name || "대상";
    changePreview.innerHTML =
      '<div class="cp-flow"><span class="cp-before">지금 · 허용 통과</span>' +
      '<span class="cp-arrow">→</span><span class="cp-after">차단</span></div>' +
      '<div class="cp-line">' + escapeHtml(name) + " · USB 매체 차단 · " + scopeText(state.pendingPreview.scope) + "</div>";
  }

  function setScope(scope) {
    if (!state.pendingPreview) return;
    state.pendingPreview.scope = scope;
    Array.prototype.forEach.call(editScope.querySelectorAll(".es-btn"), function (b) {
      b.classList.toggle("es-active", b.getAttribute("data-scope") === scope);
    });
    renderChangePreview();
  }

  // 적용 시점 세그먼트 편집 — 승인 전 관리자가 직접 조정
  Array.prototype.forEach.call(editScope.querySelectorAll(".es-btn"), function (b) {
    b.addEventListener("click", function () { setScope(b.getAttribute("data-scope")); });
  });

  function openPreview(data) {
    var scope = (data.slots && data.slots.scope) || "all";
    state.pendingPreview = {
      target_agent_id: state.currentTargetAgentId,
      target_name: data.target_name || state.currentTargetName,
      scope: scope
    };
    previewTarget.textContent = "대상: " + (data.target_name || state.currentTargetName || "-");
    setScope(scope);
    previewModal.classList.remove("hidden");
  }

  previewCancel.addEventListener("click", function () {
    previewModal.classList.add("hidden");
    state.pendingPreview = null;
  });

  previewApprove.addEventListener("click", function () {
    if (!state.pendingPreview) return;
    previewApprove.disabled = true;

    fetch("/api/config")
      .then(function (res) { return res.json(); })
      .then(function (cfg) {
        return fetch("/api/policy/apply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            license_code: cfg.license_code,
            agent_id: state.pendingPreview.target_agent_id,
            slots: {
              intent: "block_media",
              target_agent_id: state.pendingPreview.target_agent_id,
              scope: state.pendingPreview.scope
            },
            report_pno: state.currentPno
          })
        });
      })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.applied) {
          showToast("정책 반영됨 (pvn=" + data.pvn + ")");
          appendChatMsg("✅ 정책 반영 완료 (pvn=" + data.pvn + ")", "bot");
        } else {
          showToast("정책 반영 실패: " + JSON.stringify(data), true);
        }
        previewModal.classList.add("hidden");
        state.pendingPreview = null;
        loadReports();
        if (state.currentPno) loadDetail(state.currentPno);
      })
      .catch(function () { showToast("정책 반영 요청 실패", true); })
      .finally(function () {
        previewApprove.disabled = false;
      });
  });

  // ── 원본 로그 근거 모달 ──

  var eventsModal = document.getElementById("eventsModal");
  var eventsBody = document.getElementById("eventsBody");
  var eventsCount = document.getElementById("eventsCount");
  var eventsClose = document.getElementById("eventsClose");

  // 상세 안의 "원본 로그 보기" 버튼 (renderDetail 로 매번 새로 그려지므로 위임)
  detailEl.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".raw-log-btn");
    if (btn) openEventsModal(parseInt(btn.getAttribute("data-pno"), 10));
  });
  if (eventsClose) eventsClose.addEventListener("click", function () { eventsModal.classList.add("hidden"); });
  if (eventsModal) eventsModal.addEventListener("click", function (e) {
    if (e.target === eventsModal) eventsModal.classList.add("hidden"); // 오버레이 클릭 닫기
  });

  function openEventsModal(pno) {
    eventsCount.textContent = "";
    eventsBody.innerHTML = '<div class="empty-state">불러오는 중…</div>';
    eventsModal.classList.remove("hidden");
    fetch("/api/reports/" + pno + "/events")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var evs = data.events || [];
        eventsCount.textContent = evs.length + "건";
        eventsBody.innerHTML = evs.length
          ? evs.map(renderEvent).join("")
          : '<div class="empty-state">이 기간에 수집된 원본 로그가 없습니다.</div>';
      })
      .catch(function () { eventsBody.innerHTML = '<div class="empty-state">원본 로그 조회 실패</div>'; });
  }

  function renderEvent(ev) {
    var lj = ev.log_json || {};
    var chan = CHANNEL_LABEL[ev.channel] || ev.channel;
    var blocked = String(lj.is_block) === "true";
    return (
      '<div class="ev-item">' +
      '<div class="ev-head">' +
      '<span class="ev-chan">' + chan + "</span>" +
      '<span class="ev-time2">' + formatTime(ev.log_time) + "</span>" +
      (ev.pc ? '<span class="ev-pc">💻 ' + escapeHtml(ev.pc) + "</span>" : "") +
      '<span class="ev-flag ' + (blocked ? "ev-blocked" : "ev-allowed") + '">' + (blocked ? "차단됨" : "허용 통과") + "</span>" +
      "</div>" +
      '<div class="ev-detail">' + eventDetailLines(ev.channel, lj) + "</div>" +
      "</div>"
    );
  }

  // 원본 log_json → 사람이 읽는 사실 목록 (채널마다 필드가 달라 있는 것만 표시)
  function eventDetailLines(channel, lj) {
    var out = [];
    if (lj.file_name) {
      var f = '<span class="ev-file">' + escapeHtml(lj.file_name) + "</span>";
      if (lj.dst_file_name && lj.dst_file_name !== lj.file_name) {
        f += ' <span class="ev-arrow">→</span> <span class="ev-file ev-danger">' + escapeHtml(lj.dst_file_name) +
             '</span> <span class="ev-tag">이름 바꿔치기</span>';
      }
      out.push('<div class="ev-fact">📄 ' + f + "</div>");
    }
    if (lj.zip_filelist) out.push('<div class="ev-fact">🗜 압축 내용: ' + escapeHtml(lj.zip_filelist) + "</div>");
    if (lj.hash_extract_fail_reason) {
      out.push('<div class="ev-fact ev-warn">🔒 검사 회피: ' +
        (FAIL_REASON_LABEL[lj.hash_extract_fail_reason] || escapeHtml(lj.hash_extract_fail_reason)) + "</div>");
    }
    var pri = (lj.total_pri_cnt != null) ? lj.total_pri_cnt : lj.pri_cnt;
    if (pri) out.push('<div class="ev-fact">🪪 개인정보 <b>' + escapeHtml(String(pri)) + "건</b> 포함</div>");
    if (lj.device_type) out.push('<div class="ev-fact">🔌 매체: ' + escapeHtml(lj.device_type) + "</div>");
    if (lj.browser_url) out.push('<div class="ev-fact">🌐 업로드: ' + escapeHtml(lj.browser_url) + "</div>");
    if (lj.category != null && CATEGORY_LABEL[lj.category]) {
      out.push('<div class="ev-fact">📤 경로: ' + CATEGORY_LABEL[lj.category] + "</div>");
    }
    if (lj.payload) out.push('<div class="ev-fact ev-payload">💬 붙여넣은 내용: “' + escapeHtml(String(lj.payload)) + "”</div>");
    return out.length ? out.join("") : '<div class="ev-fact ev-dim">추가 상세 없음</div>';
  }

  // ── 초기 로드 ──
  loadSummary();
  loadReports();
})();
