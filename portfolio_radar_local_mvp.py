from __future__ import annotations

import csv
from datetime import datetime, timedelta
import traceback
import json
import sqlite3
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "portfolio_radar_local.db"
HOST = "127.0.0.1"
PORT = 8765
AI_PROVIDER_NAME = "DeepSeek"
AI_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
AI_MODEL = "deepseek-chat"


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PortfolioRadar 本地 MVP</title>
<style>
:root{
  --font-sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif;
  --bg:#f7f9fb;--panel:#fff;--muted:#f6f8fa;--text:#182230;--sub:#5b6472;--weak:#858d99;
  --line:#e2e7ed;--line2:#cbd3dc;--blue:#185FA5;--green:#3B6D11;--amber:#854F0B;--red:#A32D2D;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font-sans);background:var(--bg);color:var(--text)}
.nav{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;border-bottom:.5px solid var(--line);background:#fff}
.logo{font-size:17px;font-weight:600;display:flex;align-items:center;gap:8px}.dot{width:8px;height:8px;border-radius:50%;background:var(--blue)}
.nav-right{font-size:13px;color:var(--sub)}.main{padding:20px 24px;max-width:1180px;margin:0 auto}.title{font-size:19px;font-weight:600}.sub{font-size:13px;color:var(--sub);margin-top:4px;margin-bottom:18px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}.metric{background:var(--muted);border-radius:6px;padding:14px 16px}
.label{font-size:12px;color:var(--sub);margin-bottom:6px}.value{font-size:22px;font-weight:600}.small{font-size:11px;color:var(--weak);margin-top:3px}
.workspace{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(320px,.85fr);gap:14px;align-items:start}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.panel{background:#fff;border:.5px solid var(--line);border-radius:8px;padding:16px 18px;margin-bottom:12px}
.section{font-size:13px;font-weight:600;color:var(--sub);margin:18px 0 10px;text-transform:uppercase;letter-spacing:.04em}
input,textarea,select{width:100%;border:.5px solid var(--line2);border-radius:6px;padding:9px 10px;font-size:13px;background:#fff;color:var(--text)}
textarea{min-height:126px;resize:vertical;line-height:1.55}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}
button{border:.5px solid var(--line2);border-radius:6px;background:#fff;padding:9px 12px;font-size:13px;cursor:pointer;color:var(--text)}
button:hover{background:var(--muted)}.primary{background:var(--blue);border-color:var(--blue);color:#fff}.primary:hover{background:#124d86}
.fund{border:.5px solid var(--line);border-radius:8px;padding:15px 16px;background:#fff;margin-bottom:10px}.fund-head{display:flex;justify-content:space-between;gap:12px;margin-bottom:10px}
.fund-name{font-size:15px;font-weight:600}.fund-code{font-size:12px;color:var(--weak);margin-top:2px}.badge{padding:4px 11px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
.buy{background:#EAF3DE;color:var(--green)}.hold{background:#FAEEDA;color:var(--amber)}.sell{background:#FCEBEB;color:var(--red)}.watch{background:#E6F1FB;color:var(--blue)}
.bar-row{display:flex;align-items:center;gap:10px;margin:8px 0}.bar-label{font-size:12px;color:var(--sub);width:72px}.bar{height:6px;flex:1;border-radius:3px;overflow:hidden;background:var(--muted)}.fill{height:100%;background:var(--blue)}
.hint{font-size:12px;color:var(--sub);line-height:1.6;background:var(--muted);border:.5px solid var(--line);border-radius:6px;padding:10px;margin-top:10px}
.warn{background:#fff7ed;border-color:#fed7aa;color:#9a3412}.ok{background:#f0f9eb;border-color:#cbe7b7;color:#315f0c}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}.table th,.table td{border-bottom:.5px solid var(--line);padding:8px;text-align:left}.table th{color:var(--sub);font-weight:600}
.seg{display:flex;gap:6px;margin:10px 0}.seg button{flex:1;padding:7px 8px;font-size:12px}.seg button.active{background:#E6F1FB;border-color:#9cc5e8;color:var(--blue);font-weight:600}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.stat{background:var(--muted);border:.5px solid var(--line);border-radius:6px;padding:10px}.stat .label{margin-bottom:4px}.stat .value{font-size:16px}.hidden-row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 0;border-bottom:.5px solid var(--line);font-size:12px}.hidden-row:last-child{border-bottom:none}
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px}.step{border:.5px solid var(--line);background:#fff;border-radius:8px;padding:10px 12px;font-size:12px;color:var(--sub)}.step.active{border-color:#9cc5e8;background:#E6F1FB;color:var(--blue);font-weight:600}.step.done{border-color:#cbe7b7;background:#f0f9eb;color:var(--green)}.step.disabled{opacity:.52}
.rank-list{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}.rank-row{display:grid;grid-template-columns:120px 1fr 56px;gap:8px;align-items:center;font-size:12px}.rank-bar{height:8px;border-radius:4px;background:var(--muted);overflow:hidden}.rank-fill{height:100%;background:var(--blue)}.delta-up{color:var(--red);font-weight:600}.delta-down{color:var(--green);font-weight:600}.delta-flat{color:var(--weak)}
.conclusion{border:.5px solid var(--line);border-left:4px solid var(--blue);background:#f8fafc;border-radius:8px;padding:12px;margin-bottom:10px}.conclusion-title{font-size:15px;font-weight:700;margin-bottom:4px}.conclusion-text{font-size:13px;color:var(--sub);line-height:1.55}
.fill.tech{background:var(--blue)}.fill.event{background:var(--green)}.fill.senti{background:var(--amber)}
.mini-chart{width:100%;height:160px;border:.5px solid var(--line);border-radius:8px;background:#fff;margin-top:10px}
.toast-wrap{position:fixed;right:18px;top:18px;z-index:50;display:flex;flex-direction:column;gap:8px}.toast{min-width:220px;max-width:320px;background:#fff;border:.5px solid var(--line);border-left:4px solid var(--blue);box-shadow:0 12px 28px rgba(15,23,42,.12);border-radius:8px;padding:12px 14px;font-size:13px;color:var(--text);animation:slideIn .18s ease-out}.toast.ok{border-left-color:var(--green)}.toast.warn{border-left-color:var(--amber)}.toast.err{border-left-color:var(--red)}
.modal-mask{position:fixed;inset:0;background:rgba(24,34,48,.28);display:none;align-items:center;justify-content:center;z-index:40;padding:18px}.modal{width:min(720px,100%);max-height:82vh;overflow:auto;background:#fff;border:.5px solid var(--line);border-radius:8px;box-shadow:0 20px 60px rgba(15,23,42,.18)}.modal-head{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:.5px solid var(--line)}.modal-title{font-size:16px;font-weight:600}.modal-body{padding:16px 18px}.modal-close{padding:5px 9px}.detail-block{border:.5px solid var(--line);border-radius:8px;padding:12px;margin-bottom:10px;background:#fff}.detail-title{font-size:13px;font-weight:600;margin-bottom:5px}.detail-meta{font-size:11px;color:var(--weak);margin-top:6px;word-break:break-all}.detail-val{font-size:12px;color:var(--blue);font-weight:600}.mini-link{font-size:12px;color:var(--blue);text-decoration:none}
button[disabled]{opacity:.55;cursor:wait}
@keyframes slideIn{from{transform:translateY(-4px);opacity:0}to{transform:translateY(0);opacity:1}}
@media(max-width:900px){.workspace,.metrics,.grid,.row,.steps{grid-template-columns:1fr}.nav{align-items:flex-start;gap:8px;flex-direction:column}.main{padding:16px 14px}.fund-head{flex-direction:column}.rank-row{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="nav"><div class="logo"><span class="dot"></span>PortfolioRadar 本地 MVP</div><div class="nav-right" id="status">本地运行 · 数据只保存在你的电脑</div></div>
<div class="main">
  <div class="title">我的基金雷达</div>
  <div class="sub">先添加你持有的基金。系统会尝试获取前十大持仓；如果抓不到，可以手动上传。</div>
  <div class="metrics">
    <div class="metric"><div class="label">持有基金</div><div class="value" id="metricFunds">0</div><div class="small">本地配置</div></div>
    <div class="metric"><div class="label">已录入持仓</div><div class="value" id="metricHoldings">0</div><div class="small">股票条目</div></div>
    <div class="metric"><div class="label">今日建议</div><div class="value" id="metricAdvice" style="font-size:14px;padding-top:6px">待计算</div><div class="small">MVP 简化模型</div></div>
    <div class="metric"><div class="label">隐私状态</div><div class="value" style="font-size:14px;padding-top:6px;color:var(--green)">本地保存</div><div class="small">不会上传云端</div></div>
  </div>
  <div class="steps" id="stepGuide"></div>
  <div class="panel">
    <div class="section" style="margin-top:0">基金信号横向排名</div>
    <div id="rankingPanel" class="hint">添加基金并计算信号后展示排序。</div>
  </div>

  <div class="workspace">
    <div class="left-col">
      <div class="grid">
        <div class="panel">
          <div class="section" style="margin-top:0">添加基金</div>
          <div class="row">
            <input id="fundCode" placeholder="基金代码，例如 161725">
            <input id="fundName" placeholder="基金名称，例如 煤炭主题基金">
          </div>
          <button class="primary" onclick="addFund()">添加到我的基金</button>
          <div class="hint">如果你只知道基金代码，也可以先添加代码，名称以后再补。</div>
        </div>
        <div class="panel">
          <div class="section" style="margin-top:0">上传持仓</div>
          <select id="holdingFund"></select>
          <textarea id="holdingText" placeholder="粘贴持仓，每行一条：&#10;600188,0.22&#10;601898,0.15&#10;601225,0.12"></textarea>
          <div class="actions">
            <button id="fetchHoldingsBtn" onclick="fetchHoldings()">尝试自动抓取持仓</button>
            <button id="uploadHoldingsBtn" class="primary" onclick="uploadHoldings()">保存手动持仓</button>
          </div>
          <div class="hint warn">持仓格式：股票代码,权重。权重可以写 0.22，也可以写 22%。抓取失败时请从基金季报或平台页面复制前十大持仓。</div>
        </div>
      </div>

      <div class="section">今日信号</div>
      <div id="fundList"></div>
    </div>
    <div class="right-col">
      <div class="panel">
        <div class="section" style="margin-top:0">AI 新闻判断 Agent</div>
        <input id="aiKey" type="password" placeholder="输入 DeepSeek API Key，仅保存在本次浏览器会话">
        <div class="seg">
          <button id="prefConclusion" class="active" onclick="setAiPreference('conclusion')">直接给结论</button>
          <button id="prefDetailed" onclick="setAiPreference('detailed')">展开分析逻辑</button>
        </div>
        <div class="actions">
          <button id="aiNewsBtn" class="primary" onclick="analyzeActiveFund()">AI 分析当前基金新闻</button>
          <button id="aiWatchBtn" onclick="watchActiveFund()">AI 看盘</button>
          <button id="followupBtn" onclick="runFollowup()">事后回访</button>
          <button id="backfillBtn" onclick="backfillWeek()">回填近一周数据</button>
        </div>
        <div class="hint">当前默认使用 DeepSeek 兼容接口；API Key 默认每次使用后自动清空。勾选暂存时也只存在当前页面内存，到 15:00 自动失效。</div>
      </div>
      <div class="panel">
        <div class="section" style="margin-top:0">历史相关性分析</div>
        <div id="analyticsPanel" class="hint">暂无时间序列样本。每次计算信号会形成一条历史样本；十只持仓股票用于当前暴露判断，不等同于历史涨跌相关性样本。</div>
      </div>
      <div class="panel">
        <div class="section" style="margin-top:0">已隐藏基金</div>
        <div id="hiddenFunds" class="hint">暂无隐藏基金。</div>
      </div>
    </div>
  </div>
</div>
<div class="toast-wrap" id="toasts"></div>
<div class="modal-mask" id="modalMask" onclick="closeModal(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div class="modal-head"><div class="modal-title" id="modalTitle">详情</div><button class="modal-close" onclick="closeModal()">关闭</button></div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<script>
let state = {funds: [], holdings: {}, signals: {}};
const $ = id => document.getElementById(id);
let aiPreference = "conclusion";
let sessionApiKey = "";
let sessionApiKeyExpiresAt = 0;
let seenNotificationIds = new Set();
function pct(v){ return Math.round((v || 0) * 100) + "%"; }
function badgeClass(advice){ return {BUY:"buy",HOLD:"hold",SELL:"sell",WATCH:"watch"}[advice] || "watch"; }
function badgeText(advice){ return {BUY:"建议买入",HOLD:"建议持有",SELL:"建议卖出",WATCH:"持有，关注"}[advice] || "待计算"; }
function activeFundCode(){ return $("holdingFund").value || (state.funds[0] && state.funds[0].fund_code) || ""; }
function todayAt1500(){
  const d = new Date();
  d.setHours(15,0,0,0);
  return d.getTime();
}
function hasFund(){ return (state.funds || []).length > 0; }
function hasHoldings(){ return Object.values(state.holdings || {}).some(rows => rows.length > 0); }
function hasSignal(){ return Object.values(state.signals || {}).length > 0; }
function stepState(index){
  const done = [hasFund(), hasHoldings(), hasSignal(), sessionApiKey || $("aiKey").value.trim()][index];
  const active = index === 0 || (index === 1 && hasFund()) || (index === 2 && hasHoldings()) || (index === 3 && hasSignal());
  return done ? "done" : active ? "active" : "disabled";
}
function requireStep(kind){
  if(kind === "fund" && !hasFund()){ showToast("请先完成第 1 步：添加基金", "err"); return false; }
  if(kind === "holding" && !hasHoldings()){ showToast("请先完成第 2 步：上传持仓", "err"); return false; }
  if(kind === "signal" && !hasSignal()){ showToast("请先完成第 3 步：回填或计算信号", "err"); return false; }
  return true;
}
function effectiveApiKey(){
  if(sessionApiKey && Date.now() < sessionApiKeyExpiresAt) return sessionApiKey;
  sessionApiKey = ""; sessionApiKeyExpiresAt = 0;
  return $("aiKey").value.trim();
}
function prepareApiKey(){
  const key = effectiveApiKey();
  if(!key) return "";
  if(!sessionApiKey && Date.now() < todayAt1500()){
    const keep = window.confirm("是否仅在当前页面内存中保留到今日 15:00？用于 12:00 / 14:40 盘中 AI 看盘。不会写入数据库或文件，刷新页面后失效。");
    if(keep){
      sessionApiKey = key;
      sessionApiKeyExpiresAt = todayAt1500();
      $("aiKey").value = "";
      showToast("API Key 已仅在本页面暂存到今日 15:00", "ok");
      scheduleIntradayAiWatch();
    }
  }
  return key;
}
function afterApiUse(rawKey){
  if(sessionApiKey && rawKey === sessionApiKey && Date.now() < sessionApiKeyExpiresAt) return;
  sessionApiKey = ""; sessionApiKeyExpiresAt = 0; $("aiKey").value = "";
}
function scheduleIntradayAiWatch(){
  ["12:00", "14:40"].forEach(t => {
    const [h,m] = t.split(":").map(Number);
    const d = new Date();
    d.setHours(h,m,0,0);
    const delay = d.getTime() - Date.now();
    if(delay > 0 && delay < 8 * 60 * 60 * 1000){
      setTimeout(() => {
        if(sessionApiKey && Date.now() < sessionApiKeyExpiresAt){
          showToast(`${t} 自动触发 AI 看盘`, "warn");
          watchActiveFund();
        }
      }, delay);
    }
  });
}
function showToast(text, type="ok"){
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = text;
  $("toasts").appendChild(el);
  setTimeout(()=>el.remove(), 2800);
}
function showModal(title, html){
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  $("modalMask").style.display = "flex";
}
function closeModal(event){
  if(event && event.target !== $("modalMask")) return;
  $("modalMask").style.display = "none";
}
function setBusy(text){
  document.querySelectorAll("button").forEach(btn => btn.disabled = true);
  $("status").textContent = text;
}
function clearBusy(){
  document.querySelectorAll("button").forEach(btn => btn.disabled = false);
  $("status").textContent = "本地运行 · 数据只保存在你的电脑";
}
async function api(path, data){
  const res = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data || {})});
  const text = await res.text();
  try{
    const payload = JSON.parse(text || "{}");
    if(!res.ok && !payload.error) payload.error = `本地服务返回 ${res.status}`;
    return payload;
  }catch(err){
    return {error: text || `本地服务返回 ${res.status}`};
  }
}
async function apiWithFeedback(path, data, loading, success){
  setBusy(loading);
  showToast(loading, "warn");
  try{
    const res = await api(path, data);
    if(res.error){
      showToast(res.error, "err");
      showModal("操作未完成", `<div class="hint warn">${res.error}</div>`);
    }else{
      showToast(success || "操作成功", "ok");
    }
    return res;
  }catch(err){
    showToast("本地服务没有响应", "err");
    showModal("操作失败", `<div class="hint warn">${err}</div>`);
    return {error:String(err)};
  }finally{
    clearBusy();
  }
}
async function refresh(){
  state = await (await fetch("/api/state")).json();
  $("metricFunds").textContent = state.funds.length;
  $("metricHoldings").textContent = Object.values(state.holdings).reduce((n, rows)=>n+rows.length,0);
  const lastSignal = Object.values(state.signals)[0];
  $("metricAdvice").textContent = lastSignal ? badgeText(lastSignal.advice) : "待计算";
  $("holdingFund").innerHTML = state.funds.map(f => `<option value="${f.fund_code}">${f.fund_name || f.fund_code} · ${f.fund_code}</option>`).join("");
  $("fundList").innerHTML = state.funds.length ? state.funds.map(renderFund).join("") : `<div class="panel"><div class="hint warn">还没有基金。请先在上方添加你持有的基金。</div></div>`;
  renderHiddenFunds();
  renderAnalytics();
  renderStepGuide();
  renderRanking();
  renderNotifications();
}
function renderStepGuide(){
  const labels = ["① 添加基金", "② 上传持仓", "③ 回填/计算信号", "④ AI 分析"];
  $("stepGuide").innerHTML = labels.map((label, idx) => `<div class="step ${stepState(idx)}">${label}</div>`).join("");
  ["fetchHoldingsBtn","uploadHoldingsBtn"].forEach(id => { if($(id)) $(id).disabled = !hasFund(); });
  if($("backfillBtn")) $("backfillBtn").disabled = !hasHoldings();
  ["aiNewsBtn","aiWatchBtn","followupBtn"].forEach(id => { if($(id)) $(id).disabled = !hasSignal(); });
}
function renderRanking(){
  const rows = state.ranking || [];
  if(!rows.length){
    $("rankingPanel").innerHTML = `<div class="hint">添加基金并计算信号后展示排序。</div>`;
    return;
  }
  $("rankingPanel").innerHTML = `<div class="rank-list">${rows.map((r, idx) => `<div class="rank-row"><div>${idx+1}. ${r.fund_name || r.fund_code}</div><div class="rank-bar"><div class="rank-fill" style="width:${pct(r.conf_final)}"></div></div><div>${pct(r.conf_final)}</div></div>`).join("")}</div>`;
}
function renderNotifications(){
  (state.notifications || []).forEach(n => {
    if(!seenNotificationIds.has(n.id)){
      seenNotificationIds.add(n.id);
      showToast(`${n.title}：${n.body}`, "ok");
    }
  });
}
function renderHiddenFunds(){
  const hidden = state.hidden_funds || [];
  $("hiddenFunds").innerHTML = hidden.length ? hidden.map(f => `<div class="hidden-row"><span>${f.fund_name || f.fund_code} · ${f.fund_code}</span><button onclick="restoreFund('${f.fund_code}')">恢复</button></div>`).join("") : `<div class="hint">暂无隐藏基金。</div>`;
}
function renderAnalytics(){
  const analytics = state.analytics || [];
  if(!analytics.length){
    $("analyticsPanel").innerHTML = `<div class="hint warn">暂无时间序列样本。每次计算信号会形成一条历史样本；十只持仓股票用于当前暴露判断，不等同于历史涨跌相关性样本。</div>`;
    return;
  }
  $("analyticsPanel").innerHTML = analytics.map(item => `<div class="detail-block"><div class="detail-title">${item.fund_name || item.fund_code}</div><div class="stat-grid"><div class="stat"><div class="label">样本数</div><div class="value">${item.n_total}</div></div><div class="stat"><div class="label">命中率</div><div class="value">${item.hit_rate || "样本不足"}</div></div><div class="stat"><div class="label">平均后续收益</div><div class="value">${item.avg_return || "等待数据"}</div></div><div class="stat"><div class="label">综合相关</div><div class="value">${item.final_corr || "样本不足"}</div></div></div><div class="hint">${item.message}</div><button onclick="showHistory('${item.fund_code}')">查看历史明细</button></div>`).join("");
}
function renderFund(f){
  const hs = state.holdings[f.fund_code] || [];
  const s = state.signals[f.fund_code] || {advice:"WATCH", conf_final:0.5, conf_tech:0.5, conf_event:0.5, conf_senti:0.5, note:"请先录入持仓后再计算。"};
  const delta = s.delta_final == null ? "" : `<span class="${s.delta_final > 0 ? "delta-up" : s.delta_final < 0 ? "delta-down" : "delta-flat"}">较上次${s.delta_final > 0 ? "+" : ""}${pct(s.delta_final)}</span>`;
  const conclusion = `${badgeText(s.advice)}。综合信号 ${pct(s.conf_final)}，${delta || "暂无上次信号变化"}。`;
  return `<div class="fund">
    <div class="fund-head"><div><div class="fund-name">${f.fund_name || "未命名基金"}</div><div class="fund-code">${f.fund_code} · 已录入 ${hs.length} 条持仓</div></div><div><span class="badge ${badgeClass(s.advice)}">${badgeText(s.advice)}</span></div></div>
    <div class="conclusion"><div class="conclusion-title">结论摘要</div><div class="conclusion-text">${conclusion}<br>${s.note || ""}</div></div>
    <div class="bar-row"><span class="bar-label">综合</span><div class="bar"><div class="fill" style="width:${pct(s.conf_final)}"></div></div><span>${pct(s.conf_final)}</span></div>
    <div class="bar-row"><span class="bar-label">技术</span><div class="bar"><div class="fill tech" style="width:${pct(s.conf_tech)}"></div></div><span>${pct(s.conf_tech)}</span></div>
    <div class="bar-row"><span class="bar-label">事件</span><div class="bar"><div class="fill event" style="width:${pct(s.conf_event)}"></div></div><span>${pct(s.conf_event)}</span></div>
    <div class="bar-row"><span class="bar-label">情绪</span><div class="bar"><div class="fill senti" style="width:${pct(s.conf_senti)}"></div></div><span>${pct(s.conf_senti)}</span></div>
    <div class="hint ${hs.length ? "ok" : "warn"}">${s.note || "已计算。"}</div>
    ${hs.length ? `<table class="table"><tr><th>股票代码</th><th>公司简称 + 行业</th><th>权重</th></tr>${hs.slice(0,10).map(h=>`<tr><td><button onclick="showStockCard('${h.stock_code}')" title="查看走势">${h.stock_code}</button></td><td>${h.stock_name || "未知公司"} · ${h.sector || "未知行业"}</td><td>${pct(h.weight)}</td></tr>`).join("")}</table>` : ""}
    <div class="actions"><button onclick="runSignal('${f.fund_code}')">计算今日信号</button><button onclick="selectFund('${f.fund_code}')">编辑持仓</button><button onclick="showDetails('${f.fund_code}')">查看判断依据</button><button onclick="showHistory('${f.fund_code}')">历史回顾</button><button onclick="hideFund('${f.fund_code}')">隐藏基金</button></div>
  </div>`;
}
function drawLineChart(canvasId, points, color="#185FA5"){
  const canvas = $(canvasId);
  if(!canvas || !points.length) return;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(320, Math.floor(rect.width * 2));
  canvas.height = Math.max(160, Math.floor(rect.height * 2));
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height, pad = 34;
  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle = "#e2e7ed"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad, pad); ctx.lineTo(pad, h-pad); ctx.lineTo(w-pad, h-pad); ctx.stroke();
  const vals = points.map(p => Number(p.value)).filter(v => !Number.isNaN(v));
  if(!vals.length) return;
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max === min ? 1 : max - min;
  ctx.strokeStyle = color; ctx.lineWidth = 4; ctx.beginPath();
  points.forEach((p, i) => {
    const x = pad + (w - pad * 2) * (points.length === 1 ? 0.5 : i / (points.length - 1));
    const y = h - pad - ((Number(p.value) - min) / span) * (h - pad * 2);
    if(i === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
  ctx.fillStyle = color;
  points.forEach((p, i) => {
    const x = pad + (w - pad * 2) * (points.length === 1 ? 0.5 : i / (points.length - 1));
    const y = h - pad - ((Number(p.value) - min) / span) * (h - pad * 2);
    ctx.beginPath(); ctx.arc(x,y,5,0,Math.PI*2); ctx.fill();
  });
  ctx.fillStyle = "#5b6472"; ctx.font = "22px sans-serif";
  ctx.fillText(points[0].label || "", pad, h - 8);
  ctx.textAlign = "right"; ctx.fillText(points[points.length-1].label || "", w-pad, h - 8); ctx.textAlign = "left";
}
function setAiPreference(mode){
  aiPreference = mode;
  $("prefConclusion").classList.toggle("active", mode === "conclusion");
  $("prefDetailed").classList.toggle("active", mode === "detailed");
}
async function addFund(){
  const fund_code = $("fundCode").value.trim(), fund_name = $("fundName").value.trim();
  if(!fund_code){ showToast("请先填写基金代码", "err"); showModal("需要基金代码", `<div class="hint warn">请先填写基金代码，例如 161725。</div>`); return; }
  const res = await apiWithFeedback("/api/funds", {fund_code, fund_name}, "正在添加基金...", "基金已添加");
  if(res.error) return;
  $("fundCode").value = ""; $("fundName").value = "";
  await refresh();
}
function selectFund(code){
  $("holdingFund").value = code;
  const rows = state.holdings[code] || [];
  $("holdingText").value = rows.map(h => `${h.stock_code},${h.weight}`).join("\n");
  showToast("已切换到持仓编辑区", "ok");
  window.scrollTo({top:0, behavior:"smooth"});
}
async function uploadHoldings(){
  if(!requireStep("fund")) return;
  const fund_code = $("holdingFund").value;
  if(!fund_code){ showToast("请先添加基金", "err"); return; }
  const res = await apiWithFeedback("/api/holdings", {fund_code, text:$("holdingText").value}, "正在保存持仓...", "手动持仓已保存");
  if(res.error) return;
  await refresh();
  showModal("持仓保存成功", `<div class="hint ok">已保存 ${res.count || 0} 条持仓。你现在可以点击“计算今日信号”。</div>`);
}
async function fetchHoldings(){
  if(!requireStep("fund")) return;
  const fund_code = $("holdingFund").value;
  if(!fund_code){ showToast("请先添加基金", "err"); return; }
  const res = await apiWithFeedback("/api/fetch_holdings", {fund_code}, "正在尝试自动抓取持仓...", "自动持仓已保存");
  await refresh();
  if(res.error){
    showModal("自动抓取失败", `<div class="hint warn">${res.error}<br><br>你可以从基金季报或交易平台复制前十大持仓，然后粘贴到“上传持仓”。</div>`);
  }
}
async function runSignal(fund_code){
  if(!requireStep("holding")) return;
  const res = await apiWithFeedback("/api/run_signal", {fund_code}, "正在计算信号与依据...", "信号已更新");
  if(res.error) return;
  await refresh();
  showDetails(fund_code);
}
async function hideFund(fund_code){
  const res = await apiWithFeedback("/api/funds/hide", {fund_code}, "正在隐藏基金...", "基金已隐藏");
  if(res.error) return;
  await refresh();
}
async function restoreFund(fund_code){
  const res = await apiWithFeedback("/api/funds/restore", {fund_code}, "正在恢复基金...", "基金已恢复");
  if(res.error) return;
  await refresh();
}
async function analyzeActiveFund(){
  if(!requireStep("signal")) return;
  const fund_code = activeFundCode();
  const api_key = prepareApiKey();
  if(!fund_code){ showToast("请先添加基金", "err"); return; }
  if(!api_key){ showToast("请先输入 API Key", "err"); showModal("需要 API Key", `<div class="hint warn">AI 分析只需要输入 API Key。密钥仅保存在本次浏览器会话，不会写入本地数据库。</div>`); return; }
  const res = await apiWithFeedback("/api/ai/analyze_news", {fund_code, api_key, preference: aiPreference}, "AI 正在分析新闻...", "AI 新闻判断已完成");
  afterApiUse(api_key);
  if(res.error) return;
  await refresh();
  const rows = res.judgments || [];
  const body = rows.length ? rows.map(j => `<div class="detail-block"><div class="detail-title">${j.direction} · ${j.event_type}</div><div>${j.reason}</div>${j.analysis_steps ? `<div class="hint">${j.analysis_steps.join("<br>")}</div>` : ""}<div class="detail-meta"><span class="detail-val">影响 ${Math.round((j.impact_score || 0) * 100)}% · 置信 ${Math.round((j.confidence || 0) * 100)}%</span>${j.source_url ? ` · <a class="mini-link" href="${j.source_url}" target="_blank">打开新闻</a>` : ""}</div></div>`).join("") : `<div class="hint warn">没有足够相关新闻形成判断。</div>`;
  showModal(aiPreference === "detailed" ? "AI 详细分析逻辑" : "AI 新闻判断结论", body);
}
async function watchActiveFund(){
  if(!requireStep("signal")) return;
  const fund_code = activeFundCode();
  const api_key = prepareApiKey();
  if(!fund_code){ showToast("请先添加基金", "err"); return; }
  if(!api_key){ showToast("请先输入 API Key", "err"); showModal("需要 API Key", `<div class="hint warn">AI 看盘同样需要本次输入 API Key；使用后会自动清空，不会保存。</div>`); return; }
  const res = await apiWithFeedback("/api/ai/market_watch", {fund_code, api_key, preference: aiPreference}, "AI 正在看盘...", "AI 看盘已完成");
  afterApiUse(api_key);
  if(res.error) return;
  await refresh();
  const rows = res.watch || [];
  const body = rows.length ? rows.map(j => `<div class="detail-block"><div class="detail-title"><button onclick="showStockCard('${j.stock_code}')">${j.stock_code}</button> · ${j.direction}</div><div>${j.reason}</div><div class="hint">1日：${j.date_1d_start || "无"} → ${j.date_latest || "无"}；5日：${j.date_5d_start || "无"} → ${j.date_latest || "无"}</div>${j.analysis_steps ? `<div class="hint">${j.analysis_steps.join("<br>")}</div>` : ""}<div class="detail-meta"><span class="detail-val">技术 ${Math.round((j.tech_score || 0) * 100)}% · 情绪 ${Math.round((j.sentiment_score || 0) * 100)}% · 资金 ${Math.round((j.money_flow_score || 0) * 100)}%</span></div></div>`).join("") : `<div class="hint warn">暂未拿到足够行情或资金流数据。</div>`;
  showModal(aiPreference === "detailed" ? "AI 看盘逻辑" : "AI 看盘摘要", body);
}
async function runFollowup(){
  if(!requireStep("signal")) return;
  const fund_code = activeFundCode();
  if(!fund_code){ showToast("请先添加基金", "err"); return; }
  const res = await apiWithFeedback("/api/ai/followup", {fund_code}, "正在做事后回访...", "事后回访已完成");
  if(res.error) return;
  const rows = res.followups || [];
  const body = rows.length ? rows.map(f => `<div class="detail-block"><div class="detail-title">${f.verdict}</div><div>${f.note}</div><div class="detail-meta">判断时间：${f.judgment_created_at} · 回访天数：${f.days_checked} · 实际收益：${f.actual_return == null ? "待结算" : pct(f.actual_return)}</div></div>`).join("") : `<div class="hint warn">还没有达到可回访的 AI 判断，或行情数据暂时不足。</div>`;
  showModal("AI 事后回访", body);
}
async function backfillWeek(){
  if(!requireStep("holding")) return;
  const fund_code = activeFundCode();
  if(!fund_code){ showToast("请先添加基金", "err"); return; }
  const res = await apiWithFeedback("/api/backfill/week", {fund_code}, "正在回填近一周走势、资金流和新闻...", "近一周数据已回填");
  if(res.error) return;
  await refresh();
  const body = `<div class="hint ok">已处理 ${res.stocks || 0} 只持仓股，写入/更新 ${res.daily_rows || 0} 条日线、${res.flow_rows || 0} 条资金流，生成 ${res.history_rows || 0} 条启动历史样本。</div><div class="hint">这类样本来自用户持仓的一周回填，用于降低首次使用的大面积“样本不足”；长期历史胜率仍会随着每天实际运行继续积累。</div>`;
  showModal("近一周数据回填", body);
}
async function showDetails(fund_code){
  setBusy("正在读取判断依据...");
  try{
    const data = await api("/api/details", {fund_code});
    const rows = data.details || [];
    if(!rows.length){
      showModal("判断依据", `<div class="hint warn">还没有判断依据。请先点击“计算今日信号”。</div>`);
      return;
    }
    const html = rows.map(d => `<div class="detail-block"><div class="detail-title">${d.category} · ${d.title}</div><div>${d.body}</div><div class="detail-meta"><span class="detail-val">${d.value || ""}</span>${d.source_url ? ` · <a class="mini-link" href="${d.source_url}" target="_blank">打开来源</a>` : ""}</div></div>`).join("");
    showModal("四大判断依据", html);
  }finally{ clearBusy(); }
}
async function showHistory(fund_code){
  setBusy("正在读取历史回顾...");
  try{
    const data = await api("/api/history", {fund_code});
    const stats = data.stats || {};
    const summary = `<div class="hint ${stats.n_total ? "ok" : "warn"}">样本数：${stats.n_total || 0}。${stats.message || "历史样本会随着每次计算逐步累积；真实涨跌需要交易日行情数据。"}<br>技术相关：${stats.tech_corr || "样本不足"} · 事件相关：${stats.event_corr || "样本不足"} · 情绪相关：${stats.senti_corr || "样本不足"} · 综合相关：${stats.final_corr || "样本不足"}</div>`;
    const rows = (data.history || []).map(h => `<tr><td>${h.created_at}</td><td>${pct(h.conf_final)}</td><td>${badgeText(h.advice)}</td><td>${h.actual_return == null ? "等待数据" : pct(h.actual_return)}</td><td>${h.hit == null ? "待结算" : (h.hit ? "命中" : "未命中")}</td></tr>`).join("");
    showModal("历史数据回顾", `${summary}<canvas id="historyChart" class="mini-chart"></canvas><table class="table"><tr><th>时间</th><th>综合</th><th>建议</th><th>持仓涨跌</th><th>结果</th></tr>${rows || `<tr><td colspan="5">暂无历史记录</td></tr>`}</table>`);
    const points = (data.history || []).slice().reverse().map(h => ({label:(h.created_at || "").slice(5,10), value:h.conf_final || 0.5}));
    setTimeout(()=>drawLineChart("historyChart", points, "#185FA5"), 50);
  }finally{ clearBusy(); }
}
async function showStockCard(stock_code){
  setBusy("正在读取股票走势...");
  try{
    const data = await api("/api/stock/detail", {stock_code});
    if(data.error){ showModal("股票走势", `<div class="hint warn">${data.error}</div>`); return; }
    const title = `${data.stock_name || "未知公司"} · ${stock_code}`;
    const rows = (data.daily || []).map(d => `<tr><td>${d.trade_date}</td><td>${d.close}</td><td>${d.pct_change == null ? "无" : pct(d.pct_change)}</td><td>${d.super_net_in == null ? "无" : d.super_net_in}</td></tr>`).join("");
    showModal(title, `<div class="detail-block"><div class="detail-title">${data.sector || "未知行业"}</div><div>近5日日线与资金流。1日/5日判断基于这些具体交易日。</div><canvas id="stockChart" class="mini-chart"></canvas></div><table class="table"><tr><th>日期</th><th>收盘</th><th>涨跌</th><th>主力/超大单净流入</th></tr>${rows}</table>`);
    const points = (data.daily || []).map(d => ({label:(d.trade_date || "").slice(5,10), value:d.close}));
    setTimeout(()=>drawLineChart("stockChart", points, "#185FA5"), 50);
  }finally{ clearBusy(); }
}
refresh();
setInterval(refresh, 45000);
</script>
</body>
</html>"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS fund (fund_code TEXT PRIMARY KEY, fund_name TEXT NOT NULL DEFAULT '', is_hidden INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS holding (fund_code TEXT NOT NULL, stock_code TEXT NOT NULL, weight REAL NOT NULL, PRIMARY KEY (fund_code, stock_code))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS signal (fund_code TEXT PRIMARY KEY, conf_tech REAL, conf_event REAL, conf_senti REAL, conf_final REAL, advice TEXT, note TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS signal_detail (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_code TEXT NOT NULL, category TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, value TEXT NOT NULL DEFAULT '', source_url TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS signal_history (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_code TEXT NOT NULL, created_at TEXT NOT NULL, conf_tech REAL, conf_event REAL, conf_senti REAL, conf_final REAL, advice TEXT, actual_return REAL, hit INTEGER, note TEXT NOT NULL DEFAULT '', ai_event_score REAL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ai_news_judgment (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_code TEXT NOT NULL, news_title TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '', relevant INTEGER NOT NULL DEFAULT 0, event_type TEXT NOT NULL DEFAULT '', direction TEXT NOT NULL DEFAULT '', impact_score REAL NOT NULL DEFAULT 0.5, confidence REAL NOT NULL DEFAULT 0.5, reason TEXT NOT NULL DEFAULT '', risk_note TEXT NOT NULL DEFAULT '', matched_holdings_or_sector TEXT NOT NULL DEFAULT '', analysis_steps TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ai_followup (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_code TEXT NOT NULL, judgment_created_at TEXT NOT NULL, checked_at TEXT NOT NULL, expected_direction TEXT NOT NULL DEFAULT '', days_checked INTEGER NOT NULL DEFAULT 0, actual_return REAL, verdict TEXT NOT NULL DEFAULT 'pending', note TEXT NOT NULL DEFAULT '')"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS stock_daily_cache (stock_code TEXT NOT NULL, trade_date TEXT NOT NULL, close REAL, volume REAL, pct_change REAL, PRIMARY KEY(stock_code, trade_date))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS money_flow_cache (stock_code TEXT NOT NULL, trade_date TEXT NOT NULL, super_net_in REAL, PRIMARY KEY(stock_code, trade_date))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS local_notification (id INTEGER PRIMARY KEY AUTOINCREMENT, fund_code TEXT NOT NULL, notify_time TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    ensure_column(conn, "fund", "is_hidden", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "signal_history", "ai_event_score", "REAL")
    ensure_column(conn, "ai_news_judgment", "source_name", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "ai_news_judgment", "publish_time", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "ai_news_judgment", "snippet_only", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "ai_news_judgment", "source_quality", "REAL NOT NULL DEFAULT 0.65")
    ensure_column(conn, "ai_news_judgment", "recency_weight", "REAL NOT NULL DEFAULT 1.0")
    conn.commit()
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def parse_holdings(text: str) -> list[dict]:
    rows: list[dict] = []
    reader = csv.reader(StringIO(text.strip()))
    for line in reader:
        if not line or len(line) < 2:
            continue
        stock_code = line[0].strip()
        raw_weight = line[1].strip().replace("%", "")
        if not stock_code or stock_code.lower() in {"stock_code", "股票代码"}:
            continue
        weight = float(raw_weight) / (100 if "%" in line[1] or float(raw_weight) > 1 else 1)
        rows.append({"stock_code": stock_code.zfill(6), "weight": max(0.0, min(1.0, weight))})
    return rows


def state() -> dict:
    with connect() as conn:
        funds = [
            dict(row)
            for row in conn.execute("SELECT * FROM fund WHERE is_hidden = 0 ORDER BY fund_code")
        ]
        hidden_funds = [
            dict(row)
            for row in conn.execute("SELECT * FROM fund WHERE is_hidden = 1 ORDER BY fund_code")
        ]
        holdings: dict[str, list[dict]] = {}
        for row in conn.execute("SELECT * FROM holding ORDER BY fund_code, weight DESC"):
            holdings.setdefault(row["fund_code"], []).append(
                {
                    "stock_code": row["stock_code"],
                    "stock_name": STOCK_NAME_HINTS.get(row["stock_code"], "未知公司"),
                    "sector": STOCK_SECTOR_HINTS.get(row["stock_code"], "未知行业"),
                    "weight": row["weight"],
                }
            )
        signals = {}
        for row in conn.execute("SELECT * FROM signal"):
            history = [
                dict(item)
                for item in conn.execute(
                    "SELECT conf_final FROM signal_history WHERE fund_code = ? ORDER BY id DESC LIMIT 2",
                    (row["fund_code"],),
                )
            ]
            delta = None
            if len(history) >= 2 and history[0]["conf_final"] is not None and history[1]["conf_final"] is not None:
                delta = float(history[0]["conf_final"]) - float(history[1]["conf_final"])
            signals[row["fund_code"]] = {
                "conf_tech": row["conf_tech"],
                "conf_event": row["conf_event"],
                "conf_senti": row["conf_senti"],
                "conf_final": row["conf_final"],
                "advice": row["advice"],
                "note": row["note"],
                "delta_final": delta,
            }
        notifications = [
            dict(row)
            for row in conn.execute(
                "SELECT id, fund_code, notify_time, title, body, created_at FROM local_notification ORDER BY id DESC LIMIT 10"
            )
        ]
    return {
        "funds": funds,
        "hidden_funds": hidden_funds,
        "holdings": holdings,
        "signals": signals,
        "analytics": analytics_summary(),
        "notifications": notifications,
        "ranking": ranking_summary(signals, funds),
    }


def fund_by_code(fund_code: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM fund WHERE fund_code = ?", (fund_code,)).fetchone()
    return dict(row) if row else None


def ranking_summary(signals: dict, funds: list[dict]) -> list[dict]:
    rows = []
    by_fund = {fund["fund_code"]: fund for fund in funds}
    for fund_code, signal in signals.items():
        if fund_code not in by_fund:
            continue
        rows.append(
            {
                "fund_code": fund_code,
                "fund_name": by_fund[fund_code].get("fund_name", fund_code),
                "conf_final": signal.get("conf_final") or 0.5,
                "advice": signal.get("advice") or "WATCH",
                "delta_final": signal.get("delta_final"),
            }
        )
    return sorted(rows, key=lambda item: item["conf_final"], reverse=True)


def add_fund(data: dict) -> dict:
    code = str(data.get("fund_code", "")).strip()
    name = str(data.get("fund_name", "")).strip()
    if not code:
        return {"error": "基金代码不能为空"}
    with connect() as conn:
        conn.execute(
            "INSERT INTO fund(fund_code, fund_name, is_hidden) VALUES(?, ?, 0) ON CONFLICT(fund_code) DO UPDATE SET fund_name=excluded.fund_name, is_hidden=0",
            (code, name or code),
        )
        conn.commit()
    return {"ok": True}


def hide_fund(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    if not fund_code:
        return {"error": "请先选择基金"}
    with connect() as conn:
        conn.execute("UPDATE fund SET is_hidden = 1 WHERE fund_code = ?", (fund_code,))
        conn.commit()
    return {"ok": True}


def restore_fund(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    if not fund_code:
        return {"error": "请先选择基金"}
    with connect() as conn:
        conn.execute("UPDATE fund SET is_hidden = 0 WHERE fund_code = ?", (fund_code,))
        conn.commit()
    return {"ok": True}


def save_holdings(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    rows = parse_holdings(str(data.get("text", "")))
    if not fund_code:
        return {"error": "请先选择基金"}
    if not rows:
        return {"error": "没有识别到持仓。格式示例：600188,0.22"}
    with connect() as conn:
        for row in rows:
            conn.execute(
                "INSERT INTO holding(fund_code, stock_code, weight) VALUES(?, ?, ?) ON CONFLICT(fund_code, stock_code) DO UPDATE SET weight=excluded.weight",
                (fund_code, row["stock_code"], row["weight"]),
            )
        conn.commit()
    return {"ok": True, "count": len(rows)}


def fetch_holdings(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    try:
        import akshare as ak  # type: ignore

        df = ak.fund_portfolio_hold_em(symbol=fund_code)
        if df.empty:
            return {"error": "自动抓取没有返回持仓数据"}
        rows = []
        for _, item in df.head(10).iterrows():
            rows.append(
                {
                    "stock_code": str(item.get("股票代码", "")).zfill(6),
                    "weight": float(item.get("占净值比例", 0)) / 100,
                }
            )
        return save_holdings(
            {
                "fund_code": fund_code,
                "text": "\n".join(f'{row["stock_code"]},{row["weight"]}' for row in rows),
            }
        )
    except Exception as exc:
        return {"error": f"自动抓取失败：{exc}"}


def advice_from_conf(conf: float) -> str:
    if conf >= 0.65:
        return "BUY"
    if conf < 0.35:
        return "SELL"
    if conf >= 0.55 or conf < 0.45:
        return "WATCH"
    return "HOLD"


KEYWORDS = {
    "coal": ["煤", "煤炭", "煤矿", "动力煤", "焦煤", "限产", "安全整顿"],
    "semiconductor": ["半导体", "芯片", "晶圆", "光刻机", "国产替代", "先进封装"],
    "nonferrous": ["有色", "铜", "铝", "锂", "金属", "矿"],
    "chinext": ["创业板", "成长", "科技", "新能源", "医药", "流动性"],
}
POSITIVE_WORDS = ["上涨", "利好", "扩产", "创新高", "宽松", "增长", "景气", "突破"]
NEGATIVE_WORDS = ["下跌", "事故", "禁令", "限制", "监管趋严", "整顿", "回落", "承压"]
SOURCE_QUALITY = {
    "东方财富": 0.82,
    "财新": 0.78,
    "财联社": 0.76,
    "央视": 0.84,
    "官方": 0.86,
    "证券时报": 0.75,
    "新浪财经": 0.68,
    "新闻聚合": 0.62,
}
STOCK_NAME_HINTS = {
    "300750": "宁德时代",
    "300308": "中际旭创",
    "300274": "阳光电源",
    "300124": "汇川技术",
    "300760": "迈瑞医疗",
    "300014": "亿纬锂能",
    "300015": "爱尔眼科",
    "600188": "兖矿能源",
    "601898": "中煤能源",
    "601225": "陕西煤业",
    "601001": "晋控煤业",
    "600546": "山煤国际",
    "600519": "贵州茅台",
    "000858": "五粮液",
    "600036": "招商银行",
    "601318": "中国平安",
    "002594": "比亚迪",
    "688981": "中芯国际",
    "002371": "北方华创",
    "603986": "兆易创新",
    "603501": "韦尔股份",
    "600489": "中金黄金",
    "601899": "紫金矿业",
    "002466": "天齐锂业",
}
STOCK_SECTOR_HINTS = {
    "300750": "新能源电池",
    "300308": "光模块通信",
    "300274": "新能源电力设备",
    "300124": "工业自动化",
    "300760": "医疗器械",
    "300014": "新能源电池",
    "300015": "医疗服务",
    "600188": "煤炭",
    "601898": "煤炭",
    "601225": "煤炭",
    "601001": "煤炭",
    "600546": "煤炭",
    "600519": "白酒消费",
    "000858": "白酒消费",
    "600036": "银行金融",
    "601318": "保险金融",
    "300750": "新能源电池",
    "002594": "新能源车",
    "688981": "半导体",
    "002371": "半导体",
    "603986": "半导体",
    "603501": "半导体",
    "600489": "有色金属",
    "601899": "有色金属",
    "002466": "锂矿有色",
}


def infer_group(fund: dict | None, holdings: list[dict]) -> str:
    text = ((fund or {}).get("fund_name", "") + " " + (fund or {}).get("fund_code", "")).lower()
    if any(word in text for word in ["煤", "coal"]):
        return "coal"
    if any(word in text for word in ["半导体", "芯片", "semiconductor"]):
        return "semiconductor"
    if any(word in text for word in ["有色", "金属", "nonferrous"]):
        return "nonferrous"
    if any(word in text for word in ["创业", "chinext"]):
        return "chinext"
    return "coal" if holdings else "unknown"


def infer_holding_sectors(fund: dict | None, holdings: list[dict]) -> list[str]:
    sectors = []
    group = infer_group(fund, holdings)
    group_label = {
        "coal": "煤炭",
        "semiconductor": "半导体",
        "nonferrous": "有色金属",
        "chinext": "创业板成长",
    }.get(group)
    if group_label:
        sectors.append(group_label)
    for row in holdings:
        sector = STOCK_SECTOR_HINTS.get(str(row.get("stock_code", "")).zfill(6))
        if sector and sector not in sectors:
            sectors.append(sector)
    return sectors or ["未知板块"]


def parse_news_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidates = [
        text,
        text[:19],
        text[:16],
        text[:10],
    ]
    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
    if len(text) >= 8 and text[:8].isdigit():
        try:
            return datetime.strptime(text[:8], "%Y%m%d")
        except ValueError:
            return None
    return None


def news_recency_weight(publish_time: str) -> float:
    published = parse_news_time(publish_time)
    if not published:
        return 0.72
    days = max(0, (datetime.now().date() - published.date()).days)
    if days == 0:
        return 1.0
    if days == 1:
        return 0.82
    if days <= 3:
        return 0.58
    if days <= 7:
        return 0.35
    return 0.18


def news_source_quality(source_name: str) -> float:
    for key, value in SOURCE_QUALITY.items():
        if key and key in source_name:
            return value
    return SOURCE_QUALITY["新闻聚合"]


def normalize_news_item(title: str, source_url: str, source_name: str, publish_time: str, matched: list[str]) -> dict:
    source = source_name or "新闻聚合"
    return {
        "title": title.strip(),
        "source_url": source_url.strip(),
        "source_name": source,
        "publish_time": publish_time.strip(),
        "matched": matched,
        "snippet_only": True,
        "source_quality": news_source_quality(source),
        "recency_weight": news_recency_weight(publish_time),
    }


def collect_news(group: str, limit: int = 12) -> list[dict]:
    keywords = KEYWORDS.get(group, [])
    if not keywords:
        return []
    rows = []
    seen = set()
    try:
        import akshare as ak  # type: ignore

        fetchers = [
            (
                "东方财富",
                lambda: ak.stock_news_em(),
                ["新闻标题", "标题", "title"],
                ["新闻链接", "链接", "url"],
                ["文章来源", "来源", "source"],
                ["发布时间", "时间", "publish_time"],
            ),
            (
                "财新/聚合",
                lambda: ak.stock_news_main_cx(),
                ["summary", "标题", "新闻标题", "title"],
                ["url", "链接", "新闻链接"],
                ["source", "来源", "文章来源"],
                ["pub_time", "发布时间", "时间"],
            ),
            (
                "财联社",
                lambda: getattr(ak, "stock_news_main_cx")(),
                ["summary", "标题", "新闻标题", "title"],
                ["url", "链接", "新闻链接"],
                ["source", "来源", "文章来源"],
                ["pub_time", "发布时间", "时间"],
            ),
            (
                "新浪财经",
                lambda: getattr(ak, "stock_news_em")(),
                ["新闻标题", "标题", "title"],
                ["新闻链接", "链接", "url"],
                ["文章来源", "来源", "source"],
                ["发布时间", "时间", "publish_time"],
            ),
            (
                "央视/官方",
                lambda: getattr(ak, "news_cctv")(),
                ["title", "标题", "新闻标题"],
                ["url", "链接", "新闻链接"],
                ["source", "来源", "文章来源"],
                ["date", "发布时间", "时间"],
            ),
        ]
        per_source_limit = max(4, min(limit, 8))
        for fetcher_name, fetcher, title_keys, url_keys, source_keys, time_keys in fetchers:
            source_count = 0
            try:
                df = fetcher()
            except Exception:
                continue
            for _, item in df.head(120).iterrows():
                title = first_present(item, title_keys)
                source_url = first_present(item, url_keys)
                source_name = first_present(item, source_keys) or fetcher_name
                publish_time = first_present(item, time_keys)
                matched = [word for word in keywords if word in title]
                if not title or not matched or title in seen:
                    continue
                seen.add(title)
                rows.append(normalize_news_item(title, source_url, source_name, publish_time, matched))
                source_count += 1
                if source_count >= per_source_limit:
                    break
    except Exception:
        return rows[:limit]
    return sorted(rows, key=lambda item: item["recency_weight"] * item["source_quality"], reverse=True)[:limit]


def first_present(item: object, keys: list[str]) -> str:
    for key in keys:
        try:
            value = item.get(key, "")  # type: ignore[attr-defined]
        except AttributeError:
            value = ""
        text = str(value or "").strip()
        if text and text.lower() != "nan":
            return text
    return ""


def collect_news_for_holdings(fund: dict | None, holdings: list[dict], limit: int = 12) -> list[dict]:
    group = infer_group(fund, holdings)
    news = collect_news(group, limit=limit)
    sectors = infer_holding_sectors(fund, holdings)
    for item in news:
        sector_hits = [sector for sector in sectors if sector != "未知板块" and any(part in item["title"] for part in sector.split())]
        item["holding_sectors"] = sectors
        item["sector_relevance_hint"] = "、".join(sector_hits or sectors[:3])
    return news


def score_news(news: list[dict]) -> tuple[float, float, list[str]]:
    if not news:
        return 0.5, 0.5, []
    weighted_count = sum(float(item.get("recency_weight", 0.72)) * float(item.get("source_quality", 0.62)) for item in news)
    event_score = min(0.75, 0.5 + weighted_count * 0.055)
    senti_scores = []
    reasons = []
    for item in news:
        title = item["title"]
        score = 0.5
        if any(word in title for word in POSITIVE_WORDS):
            score += 0.18
            reasons.append("正面词命中")
        if any(word in title for word in NEGATIVE_WORDS):
            score -= 0.18
            reasons.append("负面词命中")
        reliability = float(item.get("recency_weight", 0.72)) * float(item.get("source_quality", 0.62))
        senti_scores.append(max(0.1, min(0.9, 0.5 + (score - 0.5) * reliability)))
    return event_score, sum(senti_scores) / len(senti_scores), reasons


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return cleaned.strip()


def bool_from_ai(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "相关", "直接影响", "间接影响"}
    return False


def float_from_ai(value: object, default: float = 0.5) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_ai_prompt(fund: dict, holdings: list[dict], news: list[dict], preference: str) -> str:
    sectors = infer_holding_sectors(fund, holdings)
    holdings_text = "\n".join(
        f"- {item['stock_code']}，权重 {round(item['weight'] * 100, 2)}%，领域：{STOCK_SECTOR_HINTS.get(item['stock_code'], '按基金主题/板块推断')}"
        for item in holdings[:20]
    )
    news_text = "\n".join(
        f"{idx + 1}. 标题/摘要：{item['title']}\n   来源：{item.get('source_name', '新闻聚合')}；发布时间：{item.get('publish_time', '未知')}；链接：{item.get('source_url', '')}\n   关键词命中：{','.join(item.get('matched', []))}；持仓领域提示：{item.get('sector_relevance_hint', '')}\n   信息完整性：{'仅标题/摘要，未获取付费全文' if item.get('snippet_only', True) else '全文或结构化摘要'}；来源可靠度：{item.get('source_quality', 0.62)}；时效权重：{item.get('recency_weight', 0.72)}"
        for idx, item in enumerate(news[:10])
    )
    need_steps = preference == "detailed"
    return f"""
你是 PortfolioRadar 的 A 股基金事件驱动信号分析 Agent。

产品目标：帮助普通基金持有人理解“新闻事件是否真正影响自己基金的持仓板块”，不能因为标题里出现一个关键词就直接判定相关。

基金信息：
- 基金代码：{fund.get('fund_code', '')}
- 基金名称：{fund.get('fund_name', '')}

已录入持仓：
{holdings_text or "- 暂无持仓明细"}

持仓领域约束：
{', '.join(sectors)}

候选新闻：
{news_text or "- 暂无候选新闻"}

你的任务：
1. 逐条判断新闻和基金持仓股票/持仓领域的关系，必须区分“直接影响”“间接影响”“无关”。若新闻只和泛市场有关，不能判为直接影响。
2. 判断影响方向：利好、利空、中性、无关。
3. 给出 0 到 1 的 impact_score 和 confidence。impact_score 表示事件对基金持仓板块的影响强度，不是上涨概率。
4. reason 面向普通用户，必须短、清楚、可解释。
5. risk_note 说明这个判断可能失效的原因。
6. matched_holdings_or_sector 说明命中的持仓股票或板块。
7. 如果信息完整性提示为“仅标题/摘要”，不得声称已经阅读全文；confidence 原则上不应高于 0.72，除非多来源相互印证。
8. 发布时间越旧，影响越要降低。T 日和 T-1 日新闻权重较高，超过 3 天的新闻只能作为背景信息。
9. {"如果用户偏好为展开分析逻辑，analysis_steps 必须包含新闻筛选、相关性判断、影响路径、时间衰减、风险说明五步。" if need_steps else "用户偏好为直接给结论，analysis_steps 可以省略或返回空数组。"}

只返回 JSON，不要返回 Markdown。结构必须是：
{{
  "judgments": [
    {{
      "news_title": "新闻标题",
      "source_url": "新闻链接",
      "relevant": true,
      "event_type": "直接影响/间接影响/无关",
      "direction": "利好/利空/中性/无关",
      "impact_score": 0.0,
      "confidence": 0.0,
      "reason": "一句话判断依据",
      "risk_note": "风险说明",
      "matched_holdings_or_sector": "股票或板块",
      "analysis_steps": []
    }}
  ]
}}
""".strip()


def call_ai_agent(api_key: str, prompt: str) -> dict:
    body = json.dumps(
        {
            "model": AI_MODEL,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "你是严谨的 A 股基金事件驱动信号分析 Agent。只输出可解析 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        AI_CHAT_COMPLETIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    return json.loads(strip_json_fence(content))


def normalize_ai_judgments(payload: dict, news: list[dict], preference: str) -> list[dict]:
    raw_rows = payload.get("judgments")
    if not isinstance(raw_rows, list):
        raise ValueError("AI 返回缺少 judgments 数组")
    by_title = {item["title"]: item for item in news}
    rows: list[dict] = []
    for idx, item in enumerate(raw_rows[:10]):
        if not isinstance(item, dict):
            continue
        fallback = news[idx] if idx < len(news) else {}
        title = str(item.get("news_title") or item.get("title") or fallback.get("title", "")).strip()
        source_url = str(item.get("source_url") or by_title.get(title, fallback).get("source_url", "")).strip()
        direction = str(item.get("direction", "中性")).strip() or "中性"
        event_type = str(item.get("event_type", "间接影响")).strip() or "间接影响"
        reason = str(item.get("reason", "")).strip() or "AI 未返回明确解释。"
        risk_note = str(item.get("risk_note", "")).strip()
        matched = item.get("matched_holdings_or_sector", "")
        if isinstance(matched, list):
            matched_text = "、".join(str(value) for value in matched)
        else:
            matched_text = str(matched).strip()
        steps = item.get("analysis_steps", [])
        if not isinstance(steps, list):
            steps = [str(steps)]
        if preference != "detailed":
            steps = []
        rows.append(
            {
                "news_title": title or "未命名新闻",
                "source_url": source_url,
                "source_name": str(by_title.get(title, fallback).get("source_name", item.get("source_name", "新闻聚合"))).strip(),
                "publish_time": str(by_title.get(title, fallback).get("publish_time", item.get("publish_time", ""))).strip(),
                "snippet_only": 1 if by_title.get(title, fallback).get("snippet_only", True) else 0,
                "source_quality": clamp(float_from_ai(by_title.get(title, fallback).get("source_quality", 0.62))),
                "recency_weight": clamp(float_from_ai(by_title.get(title, fallback).get("recency_weight", 0.72))),
                "relevant": 1 if bool_from_ai(item.get("relevant")) else 0,
                "event_type": event_type,
                "direction": direction,
                "impact_score": clamp(float_from_ai(item.get("impact_score", 0.5))),
                "confidence": clamp(float_from_ai(item.get("confidence", 0.5))),
                "reason": reason,
                "risk_note": risk_note,
                "matched_holdings_or_sector": matched_text,
                "analysis_steps": [str(step).strip() for step in steps if str(step).strip()],
            }
        )
    return rows


def latest_ai_judgments(fund_code: str) -> list[dict]:
    with connect() as conn:
        latest = conn.execute(
            "SELECT MAX(created_at) AS created_at FROM ai_news_judgment WHERE fund_code = ?",
            (fund_code,),
        ).fetchone()
        if not latest or not latest["created_at"]:
            return []
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT news_title, source_url, relevant, event_type, direction, impact_score, confidence, reason, risk_note, matched_holdings_or_sector, analysis_steps, created_at, source_name, publish_time, snippet_only, source_quality, recency_weight FROM ai_news_judgment WHERE fund_code = ? AND created_at = ? ORDER BY id",
                (fund_code, latest["created_at"]),
            )
        ]
    for row in rows:
        try:
            row["analysis_steps"] = json.loads(row.get("analysis_steps") or "[]")
        except json.JSONDecodeError:
            row["analysis_steps"] = []
    return rows


def latest_ai_event_score(fund_code: str) -> float | None:
    rows = [row for row in latest_ai_judgments(fund_code) if row.get("relevant")]
    if not rows:
        return None
    scores = []
    for row in rows:
        impact = float(row.get("impact_score") or 0.5)
        direction = str(row.get("direction", "中性"))
        if "利空" in direction or "负" in direction:
            scores.append(1 - impact)
        elif "利好" in direction or "正" in direction:
            scores.append(impact)
        else:
            scores.append(0.5)
    return clamp(sum(scores) / len(scores), 0.1, 0.9)


def analyze_news(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    api_key = str(data.get("api_key", "")).strip()
    preference = str(data.get("preference", "conclusion")).strip()
    if not fund_code:
        return {"error": "请先选择基金"}
    if not api_key:
        return {"error": f"请先输入 {AI_PROVIDER_NAME} API Key"}
    fund = fund_by_code(fund_code)
    if not fund:
        return {"error": "没有找到该基金"}
    current = state()
    holdings = current["holdings"].get(fund_code, [])
    news = collect_news_for_holdings(fund, holdings, limit=10)
    if not news:
        return {"ok": True, "judgments": []}
    try:
        payload = call_ai_agent(api_key, build_ai_prompt(fund, holdings, news, preference))
        judgments = normalize_ai_judgments(payload, news, preference)
    except Exception as exc:
        return {"error": f"{AI_PROVIDER_NAME} 分析失败，旧判断未被覆盖：{exc}"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        for item in judgments:
            conn.execute(
                "INSERT INTO ai_news_judgment(fund_code, news_title, source_url, relevant, event_type, direction, impact_score, confidence, reason, risk_note, matched_holdings_or_sector, analysis_steps, created_at, source_name, publish_time, snippet_only, source_quality, recency_weight) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    fund_code,
                    item["news_title"],
                    item["source_url"],
                    item["relevant"],
                    item["event_type"],
                    item["direction"],
                    item["impact_score"],
                    item["confidence"],
                    item["reason"],
                    item["risk_note"],
                    item["matched_holdings_or_sector"],
                    json.dumps(item["analysis_steps"], ensure_ascii=False),
                    now,
                    item.get("source_name", ""),
                    item.get("publish_time", ""),
                    item.get("snippet_only", 1),
                    item.get("source_quality", 0.62),
                    item.get("recency_weight", 0.72),
                ),
            )
        conn.commit()
    return {"ok": True, "judgments": judgments}


def money_flow_score(value: float | None) -> float:
    if value is None:
        return 0.5
    if value >= 50000:
        return 0.9
    if value >= 10000:
        return 0.7
    if value >= 0:
        return 0.55
    if value >= -10000:
        return 0.45
    if value >= -50000:
        return 0.3
    return 0.1


def safe_float(value: object, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").replace("%", "").strip()
        if not text or text.lower() == "nan":
            return default
        return float(text)
    except (TypeError, ValueError):
        return default


def normalize_trade_date(value: object) -> str:
    text = str(value or "").strip()
    parsed = parse_news_time(text)
    if parsed:
        return parsed.strftime("%Y-%m-%d")
    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text[:10]


def fetch_and_cache_stock_daily(stock_code: str, lookback_days: int = 21) -> int:
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return 0
    start = (datetime.now() - timedelta(days=max(lookback_days * 3, 30))).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
    except Exception:
        return 0
    count = 0
    with connect() as conn:
        for _, row in df.tail(lookback_days).iterrows():
            trade_date = normalize_trade_date(row.get("日期", ""))
            close = safe_float(row.get("收盘"))
            volume = safe_float(row.get("成交量"))
            pct_change_raw = safe_float(row.get("涨跌幅"))
            pct_change = pct_change_raw / 100 if pct_change_raw is not None and abs(pct_change_raw) > 1 else pct_change_raw
            if not trade_date or close is None:
                continue
            conn.execute(
                "INSERT INTO stock_daily_cache(stock_code, trade_date, close, volume, pct_change) VALUES(?, ?, ?, ?, ?) ON CONFLICT(stock_code, trade_date) DO UPDATE SET close=excluded.close, volume=excluded.volume, pct_change=excluded.pct_change",
                (stock_code, trade_date, close, volume, pct_change),
            )
            count += 1
        conn.commit()
    return count


def fetch_and_cache_money_flow(stock_code: str, lookback_days: int = 10) -> int:
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return 0
    try:
        df = ak.stock_individual_fund_flow(stock=stock_code, market="沪深A股")
    except Exception:
        return 0
    count = 0
    with connect() as conn:
        for _, row in df.tail(lookback_days).iterrows():
            trade_date = normalize_trade_date(first_present(row, ["日期", "date", "时间"]))
            super_net_in = None
            for key in ["超大单净流入", "主力净流入-净额", "主力净流入净额", "主力净流入"]:
                super_net_in = safe_float(row.get(key))
                if super_net_in is not None:
                    break
            if not trade_date or super_net_in is None:
                continue
            conn.execute(
                "INSERT INTO money_flow_cache(stock_code, trade_date, super_net_in) VALUES(?, ?, ?) ON CONFLICT(stock_code, trade_date) DO UPDATE SET super_net_in=excluded.super_net_in",
                (stock_code, trade_date, super_net_in),
            )
            count += 1
        conn.commit()
    return count


def cached_daily(stock_code: str) -> list[dict]:
    with connect() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT stock_code, trade_date, close, volume, pct_change FROM stock_daily_cache WHERE stock_code = ? ORDER BY trade_date",
                (stock_code,),
            )
        ]


def cached_money_flow(stock_code: str, trade_date: str | None = None) -> float | None:
    with connect() as conn:
        if trade_date:
            row = conn.execute(
                "SELECT super_net_in FROM money_flow_cache WHERE stock_code = ? AND trade_date = ?",
                (stock_code, trade_date),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT super_net_in FROM money_flow_cache WHERE stock_code = ? ORDER BY trade_date DESC LIMIT 1",
                (stock_code,),
            ).fetchone()
    return float(row["super_net_in"]) if row and row["super_net_in"] is not None else None


def stock_tech_from_cache(stock_code: str, trade_date: str) -> dict:
    rows = cached_daily(stock_code)
    idx = next((i for i, row in enumerate(rows) if row["trade_date"] == trade_date), -1)
    if idx < 0:
        return {"tech_score": 0.5, "change_1d": None, "change_5d": None, "volume_ratio": None, "money_flow_score": 0.5}
    current = rows[idx]
    prev = rows[idx - 1] if idx >= 1 else None
    base = rows[max(0, idx - 5)]
    change_1d = None
    change_5d = None
    if prev and prev.get("close"):
        change_1d = float(current["close"]) / float(prev["close"]) - 1
    if base and base.get("close") and base["trade_date"] != current["trade_date"]:
        change_5d = float(current["close"]) / float(base["close"]) - 1
    prev_vols = [float(row["volume"]) for row in rows[max(0, idx - 5):idx] if row.get("volume")]
    volume_ratio = None
    if prev_vols and current.get("volume"):
        volume_ratio = float(current["volume"]) / (sum(prev_vols) / len(prev_vols))
    flow = cached_money_flow(stock_code, trade_date)
    flow_score = money_flow_score(flow)
    change_score = 0.5 if change_5d is None else clamp(0.5 + float(change_5d) * 3, 0.15, 0.85)
    volume_score = 0.5
    if volume_ratio is not None:
        volume_score = 0.7 if volume_ratio > 1.5 else 0.35 if volume_ratio < 0.7 else 0.5
    return {
        "tech_score": clamp(change_score * 0.45 + volume_score * 0.25 + flow_score * 0.30, 0.1, 0.9),
        "change_1d": change_1d,
        "change_5d": change_5d,
        "volume_ratio": volume_ratio,
        "super_net_in": flow,
        "money_flow_score": flow_score,
        "date_latest": current.get("trade_date"),
        "date_1d_start": prev.get("trade_date") if prev else "",
        "date_5d_start": base.get("trade_date") if base else "",
    }


def fetch_stock_watch(stock_code: str) -> dict:
    item = {
        "stock_code": stock_code,
        "sector": STOCK_SECTOR_HINTS.get(stock_code, "按基金主题推断"),
        "latest_close": None,
        "change_1d": None,
        "change_5d": None,
        "volume_ratio": None,
        "super_net_in": None,
        "date_latest": "",
        "date_1d_start": "",
        "date_5d_start": "",
        "money_flow_score": 0.5,
        "tech_score": 0.5,
    }
    try:
        import akshare as ak  # type: ignore

        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=45)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start, end_date=end, adjust="qfq")
        if not df.empty and len(df) >= 2:
            closes = [float(value) for value in df["收盘"].tail(6).tolist()]
            volumes = [float(value) for value in df["成交量"].tail(10).tolist()]
            dates = [normalize_trade_date(value) for value in df["日期"].tail(6).tolist()] if "日期" in df else []
            item["latest_close"] = closes[-1]
            item["change_1d"] = closes[-1] / closes[-2] - 1 if closes[-2] else None
            item["change_5d"] = closes[-1] / closes[0] - 1 if len(closes) >= 6 and closes[0] else None
            if dates:
                item["date_latest"] = dates[-1]
                item["date_1d_start"] = dates[-2] if len(dates) >= 2 else ""
                item["date_5d_start"] = dates[0] if len(dates) >= 6 else ""
            if len(volumes) >= 6 and sum(volumes[:-1]) > 0:
                item["volume_ratio"] = volumes[-1] / (sum(volumes[:-1]) / len(volumes[:-1]))
    except Exception:
        pass
    try:
        import akshare as ak  # type: ignore

        flow = ak.stock_individual_fund_flow(stock=stock_code, market="沪深A股")
        if not flow.empty:
            latest = flow.tail(1).iloc[0]
            for key in ["超大单净流入", "主力净流入-净额", "主力净流入净额"]:
                if key in latest:
                    item["super_net_in"] = float(latest[key])
                    break
    except Exception:
        pass
    cached_rows = cached_daily(stock_code)
    if item["change_1d"] is None and cached_rows:
        latest = stock_tech_from_cache(stock_code, cached_rows[-1]["trade_date"])
        item.update({key: latest.get(key) for key in ["change_1d", "change_5d", "volume_ratio", "super_net_in", "money_flow_score", "tech_score", "date_latest", "date_1d_start", "date_5d_start"] if latest.get(key) is not None})
    flow_score = money_flow_score(item["super_net_in"])
    change_score = 0.5
    if item["change_5d"] is not None:
        change_score = clamp(0.5 + float(item["change_5d"]) * 3, 0.15, 0.85)
    volume_score = 0.5
    if item["volume_ratio"] is not None:
        volume_score = 0.7 if float(item["volume_ratio"]) > 1.5 else 0.35 if float(item["volume_ratio"]) < 0.7 else 0.5
    item["money_flow_score"] = flow_score
    item["tech_score"] = clamp(change_score * 0.45 + volume_score * 0.25 + flow_score * 0.30, 0.1, 0.9)
    return item


def collect_market_watch(holdings: list[dict]) -> list[dict]:
    rows = []
    for holding in holdings[:10]:
        item = fetch_stock_watch(str(holding["stock_code"]).zfill(6))
        item["weight"] = holding["weight"]
        rows.append(item)
    return rows


def build_market_watch_prompt(fund: dict, holdings: list[dict], watch_rows: list[dict], preference: str) -> str:
    need_steps = preference == "detailed"
    rows_text = "\n".join(
        f"- {row['stock_code']}，权重 {round(row.get('weight', 0) * 100, 2)}%，领域 {row.get('sector')}，1日涨跌 {row.get('change_1d')}（{row.get('date_1d_start')}→{row.get('date_latest')}），5日涨跌 {row.get('change_5d')}（{row.get('date_5d_start')}→{row.get('date_latest')}），量比 {row.get('volume_ratio')}，主力/超大单净流入 {row.get('super_net_in')}，本地技术分 {row.get('tech_score')}"
        for row in watch_rows
    )
    return f"""
你是 PortfolioRadar 的 A 股基金 AI 看盘 Agent。你的分析对象不是单只股票投机，而是基金前十大持仓的加权技术面、资金流和短期情绪。

基金：{fund.get('fund_name', '')}（{fund.get('fund_code', '')}）
持仓领域：{', '.join(infer_holding_sectors(fund, holdings))}

持仓看盘数据：
{rows_text or "- 暂未拿到行情数据"}

任务：
1. 逐只持仓判断走势、量能、主力资金是否支持后续行情。
2. 必须结合持仓权重，权重低的股票不能主导基金级结论。
3. 不得给出保证性预测，只能给出概率化、风险提示式判断。
4. 如果某项数据为 null，必须说明该项缺失，不能编造。
5. {"用户要求展开分析逻辑，analysis_steps 需要包括走势、量能、资金流、基金权重、风险五步。" if need_steps else "用户只要结论，analysis_steps 可为空。"}

只返回 JSON：
{{
  "watch": [
    {{
      "stock_code": "股票代码",
      "direction": "偏强/偏弱/中性",
      "tech_score": 0.0,
      "money_flow_score": 0.0,
      "sentiment_score": 0.0,
      "reason": "一句话解释",
      "risk_note": "风险提示",
      "analysis_steps": []
    }}
  ],
  "fund_summary": "基金级别摘要"
}}
""".strip()


def normalize_market_watch(payload: dict, source_rows: list[dict], preference: str) -> list[dict]:
    raw_rows = payload.get("watch")
    if not isinstance(raw_rows, list):
        raise ValueError("AI 返回缺少 watch 数组")
    by_code = {row["stock_code"]: row for row in source_rows}
    rows = []
    for raw in raw_rows[:10]:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("stock_code", "")).zfill(6)
        source = by_code.get(code, {})
        steps = raw.get("analysis_steps", [])
        if not isinstance(steps, list):
            steps = [str(steps)]
        if preference != "detailed":
            steps = []
        rows.append(
            {
                "stock_code": code,
                "direction": str(raw.get("direction", "中性")),
                "tech_score": clamp(float_from_ai(raw.get("tech_score", source.get("tech_score", 0.5)))),
                "money_flow_score": clamp(float_from_ai(raw.get("money_flow_score", source.get("money_flow_score", 0.5)))),
                "sentiment_score": clamp(float_from_ai(raw.get("sentiment_score", 0.5))),
                "reason": str(raw.get("reason", "AI 未返回明确解释。")).strip(),
                "risk_note": str(raw.get("risk_note", "")).strip(),
                "date_latest": source.get("date_latest", ""),
                "date_1d_start": source.get("date_1d_start", ""),
                "date_5d_start": source.get("date_5d_start", ""),
                "analysis_steps": [str(step).strip() for step in steps if str(step).strip()],
            }
        )
    return rows


def analyze_market_watch(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    api_key = str(data.get("api_key", "")).strip()
    preference = str(data.get("preference", "conclusion")).strip()
    if not fund_code:
        return {"error": "请先选择基金"}
    if not api_key:
        return {"error": f"请先输入 {AI_PROVIDER_NAME} API Key"}
    fund = fund_by_code(fund_code)
    if not fund:
        return {"error": "没有找到该基金"}
    holdings = state()["holdings"].get(fund_code, [])
    if not holdings:
        return {"error": "请先录入持仓"}
    watch_rows = collect_market_watch(holdings)
    try:
        payload = call_ai_agent(api_key, build_market_watch_prompt(fund, holdings, watch_rows, preference))
        rows = normalize_market_watch(payload, watch_rows, preference)
    except Exception as exc:
        return {"error": f"{AI_PROVIDER_NAME} 看盘失败：{exc}"}
    details = [
        {
            "category": "AI看盘",
            "title": f"{row['stock_code']} · {row['direction']}",
            "body": f"{row['reason']} 风险：{row['risk_note']}".strip(),
            "value": f"技术 {round(row['tech_score'] * 100)}% · 资金 {round(row['money_flow_score'] * 100)}% · 情绪 {round(row['sentiment_score'] * 100)}%",
        }
        for row in rows
    ]
    if details:
        save_details(fund_code, details)
    return {"ok": True, "watch": rows, "fund_summary": payload.get("fund_summary", "")}


def estimate_holding_return(fund_code: str, start: datetime, days: int) -> float | None:
    holdings = state()["holdings"].get(fund_code, [])
    if not holdings:
        return None
    total_weight = 0.0
    weighted_return = 0.0
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return None
    start_date = start.strftime("%Y%m%d")
    end_date = (start + timedelta(days=max(days + 8, 10))).strftime("%Y%m%d")
    for row in holdings[:10]:
        try:
            df = ak.stock_zh_a_hist(symbol=row["stock_code"], period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            if df.empty or len(df) < 2:
                continue
            closes = [float(value) for value in df["收盘"].head(days + 1).tolist()]
            if len(closes) < 2 or closes[0] == 0:
                continue
            ret = closes[-1] / closes[0] - 1
            weighted_return += ret * float(row["weight"])
            total_weight += float(row["weight"])
        except Exception:
            continue
    if total_weight == 0:
        return None
    return weighted_return / total_weight


def common_trade_dates(holdings: list[dict], min_count: int = 2) -> list[str]:
    counts: dict[str, int] = {}
    for row in holdings[:10]:
        for daily in cached_daily(row["stock_code"]):
            counts[daily["trade_date"]] = counts.get(daily["trade_date"], 0) + 1
    threshold = min(len(holdings), max(min_count, min(3, len(holdings))))
    return sorted(date for date, count in counts.items() if count >= threshold)


def weighted_return_on_dates(holdings: list[dict], start_date: str, end_date: str) -> float | None:
    total_weight = 0.0
    weighted_return = 0.0
    for holding in holdings[:10]:
        rows = {row["trade_date"]: row for row in cached_daily(holding["stock_code"])}
        start = rows.get(start_date)
        end = rows.get(end_date)
        if not start or not end or not start.get("close"):
            continue
        ret = float(end["close"]) / float(start["close"]) - 1
        weighted_return += ret * float(holding["weight"])
        total_weight += float(holding["weight"])
    if total_weight == 0:
        return None
    return weighted_return / total_weight


def backfilled_note_for_date(trade_date: str) -> str:
    return f"近一周回填 {trade_date}"


def backfill_week(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    if not fund_code:
        return {"error": "请先选择基金"}
    fund = fund_by_code(fund_code)
    if not fund:
        return {"error": "没有找到该基金"}
    holdings = state()["holdings"].get(fund_code, [])
    if not holdings:
        return {"error": "请先录入持仓"}
    daily_rows = 0
    flow_rows = 0
    for holding in holdings[:10]:
        code = str(holding["stock_code"]).zfill(6)
        daily_rows += fetch_and_cache_stock_daily(code, lookback_days=16)
        flow_rows += fetch_and_cache_money_flow(code, lookback_days=10)
    news = collect_news_for_holdings(fund, holdings, limit=12)
    conf_event, conf_senti, _ = score_news(news)
    dates = common_trade_dates(holdings)[-7:]
    history_rows = 0
    with connect() as conn:
        for idx, trade_date in enumerate(dates[:-1]):
            next_date = dates[idx + 1]
            note = backfilled_note_for_date(trade_date)
            exists = conn.execute(
                "SELECT 1 FROM signal_history WHERE fund_code = ? AND note = ? LIMIT 1",
                (fund_code, note),
            ).fetchone()
            if exists:
                continue
            weighted_tech = 0.0
            total_weight = 0.0
            for holding in holdings[:10]:
                tech = stock_tech_from_cache(holding["stock_code"], trade_date)["tech_score"]
                weighted_tech += tech * float(holding["weight"])
                total_weight += float(holding["weight"])
            if total_weight == 0:
                continue
            conf_tech = clamp(weighted_tech / total_weight, 0.1, 0.9)
            actual_return = weighted_return_on_dates(holdings, trade_date, next_date)
            if actual_return is None:
                continue
            final = conf_tech * 0.4 + conf_event * 0.35 + conf_senti * 0.25
            advice = advice_from_conf(final)
            hit = int((advice in {"BUY", "HOLD", "WATCH"} and actual_return > 0) or (advice == "SELL" and actual_return < 0))
            conn.execute(
                "INSERT INTO signal_history(fund_code, created_at, conf_tech, conf_event, conf_senti, conf_final, advice, actual_return, hit, note, ai_event_score) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    fund_code,
                    f"{trade_date} 15:00:00",
                    conf_tech,
                    conf_event,
                    conf_senti,
                    final,
                    advice,
                    actual_return,
                    hit,
                    note,
                    None,
                ),
            )
            history_rows += 1
        latest = conn.execute(
            "SELECT conf_tech, conf_event, conf_senti, conf_final, advice, note FROM signal_history WHERE fund_code = ? ORDER BY created_at DESC, id DESC LIMIT 1",
            (fund_code,),
        ).fetchone()
        if latest:
            conn.execute(
                "INSERT INTO signal(fund_code, conf_tech, conf_event, conf_senti, conf_final, advice, note) VALUES(?, ?, ?, ?, ?, ?, ?) ON CONFLICT(fund_code) DO UPDATE SET conf_tech=excluded.conf_tech, conf_event=excluded.conf_event, conf_senti=excluded.conf_senti, conf_final=excluded.conf_final, advice=excluded.advice, note=excluded.note",
                (
                    fund_code,
                    latest["conf_tech"],
                    latest["conf_event"],
                    latest["conf_senti"],
                    latest["conf_final"],
                    latest["advice"],
                    "已用近一周持仓走势、资金流和新闻完成启动回填。",
                ),
            )
        conn.commit()
    save_details(
        fund_code,
        [
            {
                "category": "启动回填",
                "title": "近一周持仓走势与资金流",
                "body": f"已按当前持仓倒推近一周交易日，缓存日线与资金流，生成 {history_rows} 条可用于历史面板的启动样本。长期胜率仍以后续真实运行积累为主。",
                "value": f"日线 {daily_rows} 条 · 资金流 {flow_rows} 条",
            }
        ],
    )
    return {"ok": True, "stocks": len(holdings[:10]), "daily_rows": daily_rows, "flow_rows": flow_rows, "history_rows": history_rows}


def add_notification(fund_code: str, notify_time: str, title: str, body: str) -> None:
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM local_notification WHERE fund_code = ? AND notify_time = ? AND title = ? LIMIT 1",
            (fund_code, notify_time, title),
        ).fetchone()
        if exists:
            return
        conn.execute(
            "INSERT INTO local_notification(fund_code, notify_time, title, body, created_at) VALUES(?, ?, ?, ?, ?)",
            (fund_code, notify_time, title, body, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()


def intraday_refresh_once(slot: str) -> None:
    current = state()
    for fund in current.get("funds", []):
        fund_code = fund["fund_code"]
        before = (current.get("signals", {}).get(fund_code) or {}).get("conf_final")
        backfill = backfill_week({"fund_code": fund_code})
        signal = run_signal({"fund_code": fund_code})
        if backfill.get("error") or signal.get("error"):
            body = backfill.get("error") or signal.get("error") or "刷新失败"
        else:
            after = (state().get("signals", {}).get(fund_code) or {}).get("conf_final")
            delta = ""
            if before is not None and after is not None:
                diff = float(after) - float(before)
                delta = f"，较上次信号{'+' if diff > 0 else ''}{round(diff * 100)}%"
            body = f"已刷新近一周行情/资金流，新增 {backfill.get('history_rows', 0)} 条启动样本{delta}。"
        add_notification(fund_code, f"{datetime.now().strftime('%Y-%m-%d')} {slot}", "盘中刷新完成", body)


def scheduler_loop() -> None:
    slots = {"12:00", "14:40"}
    while True:
        now = datetime.now()
        slot = now.strftime("%H:%M")
        if slot in slots:
            marker = f"{now.strftime('%Y-%m-%d')} {slot}"
            with connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM local_notification WHERE notify_time = ? AND title = ? LIMIT 1",
                    (marker, "盘中刷新完成"),
                ).fetchone()
            if not exists:
                try:
                    intraday_refresh_once(slot)
                except Exception:
                    print(traceback.format_exc())
            time.sleep(65)
        else:
            time.sleep(30)


def run_ai_followup(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    min_days = int(data.get("min_days", 2) or 2)
    max_days = int(data.get("max_days", 5) or 5)
    if not fund_code:
        return {"error": "请先选择基金"}
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT fund_code, created_at, direction, impact_score, confidence FROM ai_news_judgment WHERE fund_code = ? AND relevant = 1 AND confidence >= 0.65 AND created_at <= ? ORDER BY created_at DESC LIMIT 50",
                (fund_code, (datetime.now() - timedelta(days=min_days)).strftime("%Y-%m-%d %H:%M:%S")),
            )
        ]
    followups = []
    for row in rows:
        created = parse_news_time(row["created_at"])
        if not created:
            continue
        elapsed = (datetime.now().date() - created.date()).days
        if elapsed < min_days:
            continue
        days_checked = min(max_days, max(min_days, elapsed))
        actual_return = estimate_holding_return(fund_code, created, days_checked)
        direction = str(row.get("direction", ""))
        if actual_return is None:
            verdict = "pending"
            note = "行情数据暂时不足，已记录为待结算。"
        elif ("利好" in direction or "正" in direction) and actual_return < 0:
            verdict = "miss"
            note = f"AI 当时偏利好，但后续 {days_checked} 天持仓加权收益为负，需要复盘新闻影响是否被高估。"
        elif ("利空" in direction or "负" in direction) and actual_return > 0:
            verdict = "miss"
            note = f"AI 当时偏利空，但后续 {days_checked} 天持仓加权收益为正，需要复盘风险判断。"
        else:
            verdict = "hit"
            note = f"AI 判断方向与后续 {days_checked} 天持仓加权表现基本一致。"
        item = {
            "fund_code": fund_code,
            "judgment_created_at": row["created_at"],
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "expected_direction": direction,
            "days_checked": days_checked,
            "actual_return": actual_return,
            "verdict": verdict,
            "note": note,
        }
        with connect() as conn:
            conn.execute(
                "INSERT INTO ai_followup(fund_code, judgment_created_at, checked_at, expected_direction, days_checked, actual_return, verdict, note) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item["fund_code"],
                    item["judgment_created_at"],
                    item["checked_at"],
                    item["expected_direction"],
                    item["days_checked"],
                    item["actual_return"],
                    item["verdict"],
                    item["note"],
                ),
            )
            conn.commit()
        followups.append(item)
    return {"ok": True, "followups": followups}


def save_details(fund_code: str, details: list[dict]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        for item in details:
            conn.execute(
                "INSERT INTO signal_detail(fund_code, category, title, body, value, source_url, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    fund_code,
                    item["category"],
                    item["title"],
                    item["body"],
                    item.get("value", ""),
                    item.get("source_url", ""),
                    now,
                ),
            )
        conn.commit()


def latest_actual_return(fund_code: str) -> float | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT actual_return FROM signal_history WHERE fund_code = ? AND actual_return IS NOT NULL ORDER BY id DESC LIMIT 1",
            (fund_code,),
        ).fetchone()
    return float(row["actual_return"]) if row else None


def record_history(
    fund_code: str,
    conf_tech: float,
    conf_event: float,
    conf_senti: float,
    conf_final: float,
    advice: str,
    note: str,
    ai_event_score: float | None = None,
) -> None:
    actual_return = latest_actual_return(fund_code)
    hit = None
    if actual_return is not None:
        hit = int((advice in {"BUY", "HOLD", "WATCH"} and actual_return > 0) or (advice == "SELL" and actual_return < 0))
    with connect() as conn:
        conn.execute(
            "INSERT INTO signal_history(fund_code, created_at, conf_tech, conf_event, conf_senti, conf_final, advice, actual_return, hit, note, ai_event_score) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fund_code,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                conf_tech,
                conf_event,
                conf_senti,
                conf_final,
                advice,
                actual_return,
                hit,
                note,
                ai_event_score,
            ),
        )
        conn.commit()


def correlation(xs: list[float], ys: list[float]) -> str | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs) ** 0.5
    den_y = sum((y - my) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return f"{num / (den_x * den_y):.2f}"


def format_rate(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{value * 100:.0f}%"


def analytics_for_fund(fund: dict, limit: int = 200) -> dict:
    fund_code = str(fund.get("fund_code", "")).strip()
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT created_at, conf_tech, conf_event, conf_senti, conf_final, advice, actual_return, hit, note, ai_event_score FROM signal_history WHERE fund_code = ? ORDER BY id DESC LIMIT ?",
                (fund_code, limit),
            )
        ]
    actual_rows = [row for row in rows if row["actual_return"] is not None]
    actuals = [float(row["actual_return"]) for row in actual_rows]
    hits = [int(row["hit"]) for row in actual_rows if row["hit"] is not None]
    enough = len(actual_rows) >= 3
    avg_return = sum(actuals) / len(actuals) if actuals else None
    hit_rate = sum(hits) / len(hits) if hits else None
    stats = {
        "fund_code": fund_code,
        "fund_name": fund.get("fund_name", fund_code),
        "n_total": len(rows),
        "n_actual": len(actual_rows),
        "hit_rate": format_rate(hit_rate),
        "avg_return": format_rate(avg_return),
        "tech_corr": correlation([float(row["conf_tech"]) for row in actual_rows], actuals),
        "event_corr": correlation([float(row["conf_event"]) for row in actual_rows], actuals),
        "senti_corr": correlation([float(row["conf_senti"]) for row in actual_rows], actuals),
        "final_corr": correlation([float(row["conf_final"]) for row in actual_rows], actuals),
        "ai_event_corr": correlation(
            [float(row["ai_event_score"]) for row in actual_rows if row["ai_event_score"] is not None],
            [float(row["actual_return"]) for row in actual_rows if row["ai_event_score"] is not None],
        ),
    }
    if not rows:
        stats["message"] = "暂无历史样本。计算信号后会逐步累积。"
    elif not enough:
        stats["message"] = "样本不足，暂不形成统计结论。真实涨跌需要后续交易日行情数据积累。"
    else:
        stats["message"] = "已基于历史快照和后续涨跌样本形成初步统计，可继续随计算次数积累。"
    return stats


def analytics_summary() -> list[dict]:
    with connect() as conn:
        funds = [dict(row) for row in conn.execute("SELECT * FROM fund ORDER BY is_hidden, fund_code")]
    return [analytics_for_fund(fund) for fund in funds]


def run_signal(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    current = state()
    rows = current["holdings"].get(fund_code, [])
    fund = fund_by_code(fund_code)
    if not rows:
        note = "还没有持仓数据。请先自动抓取或手动上传前十大持仓。"
        conf_tech = conf_event = conf_senti = conf_final = 0.5
        ai_event_score = None
        details = [
            {
                "category": "配置",
                "title": "缺少持仓",
                "body": note,
                "value": "中性 50%",
            }
        ]
    else:
        total_weight = sum(row["weight"] for row in rows)
        concentration = max((row["weight"] for row in rows), default=0)
        coverage = min(total_weight, 1.0)
        conf_tech = max(0.35, min(0.72, 0.48 + coverage * 0.12 - concentration * 0.08))
        group = infer_group(fund, rows)
        news = collect_news_for_holdings(fund, rows)
        conf_event, conf_senti, senti_reasons = score_news(news)
        ai_event_score = latest_ai_event_score(fund_code)
        ai_rows = latest_ai_judgments(fund_code)
        if ai_event_score is not None:
            conf_event = clamp(conf_event * 0.45 + ai_event_score * 0.55, 0.1, 0.9)
        conf_final = conf_tech * 0.4 + conf_event * 0.35 + conf_senti * 0.25
        note = "已生成第三版 MVP 信号：技术依据来自持仓覆盖度与集中度；事件/情绪依据来自当前新闻，若已触发 AI 分析则纳入事件驱动判断。"
        details = [
            {
                "category": "技术",
                "title": "持仓覆盖度与集中度",
                "body": f"已录入 {len(rows)} 只持仓，权重覆盖 {round(coverage * 100)}%，最大单一持仓 {round(concentration * 100)}%。覆盖越完整、集中度越低，技术侧置信度越稳定。",
                "value": f"{round(conf_tech * 100)}%",
            },
            {
                "category": "事件",
                "title": "板块新闻与 AI 事件判断",
                "body": f"识别板块：{group}。已优先尝试东方财富新闻，再补充新闻聚合；本地新闻命中 {len(news)} 条，并按发布时间和来源可靠度降权。{'已纳入 AI 事件分数。' if ai_event_score is not None else '尚未触发 AI 分析，该项使用本地新闻基础分。'}",
                "value": f"{round(conf_event * 100)}%",
            },
            {
                "category": "情绪",
                "title": "新闻标题情绪",
                "body": "；".join(senti_reasons[:3]) if senti_reasons else "未命中明显正负面词，情绪维持中性。",
                "value": f"{round(conf_senti * 100)}%",
            },
            {
                "category": "历史",
                "title": "历史相关性样本",
                "body": "每次计算都会写入历史回顾。真实涨跌相关性需要后续交易日行情数据积累，目前不会伪造收益。",
                "value": "持续积累",
            },
        ]
        for item in news[:5]:
            details.append(
                {
                    "category": "事件来源",
                    "title": f"{item.get('source_name', '新闻聚合')} · {item.get('publish_time', '时间未知') or '时间未知'}",
                    "body": item["title"],
                    "value": f"命中：{','.join(item['matched'])} · 时效 {round(float(item.get('recency_weight', 0.72)) * 100)}% · 来源 {round(float(item.get('source_quality', 0.62)) * 100)}%",
                    "source_url": item.get("source_url", ""),
                }
            )
        for item in ai_rows[:5]:
            details.append(
                {
                    "category": "AI事件",
                    "title": f"{item.get('direction', '中性')} · {item.get('event_type', '事件判断')}",
                    "body": f"{item.get('reason', '')} 风险：{item.get('risk_note', '')}".strip(),
                    "value": f"影响 {round(float(item.get('impact_score') or 0) * 100)}% · 置信 {round(float(item.get('confidence') or 0) * 100)}%",
                    "source_url": item.get("source_url", ""),
                }
            )
    advice = advice_from_conf(conf_final)
    with connect() as conn:
        conn.execute(
            "INSERT INTO signal(fund_code, conf_tech, conf_event, conf_senti, conf_final, advice, note) VALUES(?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(fund_code) DO UPDATE SET conf_tech=excluded.conf_tech, conf_event=excluded.conf_event, conf_senti=excluded.conf_senti, conf_final=excluded.conf_final, advice=excluded.advice, note=excluded.note",
            (fund_code, conf_tech, conf_event, conf_senti, conf_final, advice, note),
        )
        conn.commit()
    save_details(fund_code, details)
    record_history(fund_code, conf_tech, conf_event, conf_senti, conf_final, advice, note, ai_event_score)
    return {"ok": True}


def details_for(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    with connect() as conn:
        latest = conn.execute(
            "SELECT MAX(created_at) AS created_at FROM signal_detail WHERE fund_code = ?",
            (fund_code,),
        ).fetchone()
        if not latest or not latest["created_at"]:
            return {"details": []}
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT category, title, body, value, source_url, created_at FROM signal_detail WHERE fund_code = ? AND created_at = ? ORDER BY id",
                (fund_code, latest["created_at"]),
            )
        ]
    return {"details": rows}


def history_for(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    fund = fund_by_code(fund_code) or {"fund_code": fund_code, "fund_name": fund_code}
    with connect() as conn:
        rows = [
            dict(row)
            for row in conn.execute(
                "SELECT created_at, conf_tech, conf_event, conf_senti, conf_final, advice, actual_return, hit, note, ai_event_score FROM signal_history WHERE fund_code = ? ORDER BY id DESC LIMIT 30",
                (fund_code,),
            )
        ]
    return {"history": rows, "stats": analytics_for_fund(fund)}


def stock_detail(data: dict) -> dict:
    stock_code = str(data.get("stock_code", "")).strip().zfill(6)
    if not stock_code:
        return {"error": "缺少股票代码"}
    if len(cached_daily(stock_code)) < 5:
        fetch_and_cache_stock_daily(stock_code, lookback_days=8)
        fetch_and_cache_money_flow(stock_code, lookback_days=8)
    rows = cached_daily(stock_code)[-5:]
    daily = []
    for row in rows:
        item = dict(row)
        item["super_net_in"] = cached_money_flow(stock_code, row["trade_date"])
        daily.append(item)
    if not daily:
        return {"error": "暂未获取到该股票近5日日线数据"}
    return {
        "stock_code": stock_code,
        "stock_name": STOCK_NAME_HINTS.get(stock_code, "未知公司"),
        "sector": STOCK_SECTOR_HINTS.get(stock_code, "未知行业"),
        "daily": daily,
    }


def history_analytics(data: dict) -> dict:
    fund_code = str(data.get("fund_code", "")).strip()
    if fund_code:
        fund = fund_by_code(fund_code)
        if not fund:
            return {"error": "没有找到该基金"}
        return {"analytics": analytics_for_fund(fund)}
    return {"analytics": analytics_summary()}


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/api/state":
                self._json(state())
                return
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            self._json({"error": f"本地服务处理失败：{exc}"}, 500)

    def do_POST(self) -> None:
        try:
            path = urlparse(self.path).path
            data = self._read_json()
            routes = {
                "/api/funds": add_fund,
                "/api/funds/hide": hide_fund,
                "/api/funds/restore": restore_fund,
                "/api/holdings": save_holdings,
                "/api/fetch_holdings": fetch_holdings,
                "/api/run_signal": run_signal,
                "/api/backfill/week": backfill_week,
                "/api/ai/analyze_news": analyze_news,
                "/api/ai/market_watch": analyze_market_watch,
                "/api/ai/followup": run_ai_followup,
                "/api/details": details_for,
                "/api/stock/detail": stock_detail,
                "/api/history": history_for,
                "/api/history/analytics": history_analytics,
            }
            if path not in routes:
                self._json({"error": "not found"}, 404)
                return
            self._json(routes[path](data))
        except Exception as exc:
            print(traceback.format_exc())
            self._json({"error": f"本地服务处理失败：{exc}"}, 500)

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    connect().close()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"PortfolioRadar 本地 MVP 已启动：{url}")
    print("按 Ctrl+C 停止。数据保存在：", DB_PATH)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        assert parse_holdings("600188,22%\n601898,0.15")[0]["weight"] == 0.22
        print("self-test ok")
    else:
        main()
