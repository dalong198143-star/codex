import json
d = json.load(open("D:/maozhua/Codex/dash/data.json"))
DATA = json.dumps(d, ensure_ascii=False)

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>INTEL DASH</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#070b14;--surface:#0d1321;--surface2:#151d30;--border:#1e2a45;--text:#e2e8f0;--text2:#94a3b8;--text3:#475569;--accent:#3b82f6;--green:#22c55e;--orange:#f59e0b;--purple:#a855f7}
body{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;min-height:100vh;overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;background-image:linear-gradient(rgba(59,130,246,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,0.04) 1px,transparent 1px);background-size:48px 48px;pointer-events:none;z-index:0}
canvas#bgCanvas{position:fixed;inset:0;width:100vw;height:100vh;z-index:0;pointer-events:none;opacity:.1}
.scanLine{position:fixed;left:0;width:100%;height:1px;background:linear-gradient(90deg,transparent,rgba(59,130,246,0.3),transparent);z-index:99;pointer-events:none;animation:scanMove 3s linear infinite}
@keyframes scanMove{0%{top:0}100%{top:100%}}
.glowA,.glowB{position:fixed;width:400px;height:400px;border-radius:50%;filter:blur(100px);pointer-events:none;z-index:0}
.glowA{top:-100px;right:-100px;background:rgba(59,130,246,0.08)}
.glowB{bottom:-100px;left:-100px;background:rgba(168,85,247,0.06)}
.nav{display:flex;align-items:center;justify-content:space-between;padding:14px 36px;background:rgba(7,11,20,0.85);backdrop-filter:blur(16px);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
.nLeft{display:flex;align-items:center;gap:20px}
.brand{font-size:15px;font-weight:800;letter-spacing:3px;background:linear-gradient(135deg,var(--accent),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.live{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2)}
.liveDot{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);animation:pulseAnim 2s infinite}
@keyframes pulseAnim{0%,100%{opacity:1}50%{opacity:0.4}}
.nRight{display:flex;align-items:center;gap:24px;font-size:12px;color:var(--text3)}
.tag{padding:4px 14px;border-radius:100px;background:var(--surface2);border:1px solid var(--border);font-size:11px;color:var(--text2)}
.clock{color:var(--accent2)}
.container{max-width:1360px;margin:0 auto;padding:24px 36px;position:relative;z-index:1}
.kpiRow{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.kpi{position:relative;padding:22px 24px;background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.kpi::after{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),var(--purple));opacity:.4}
.kpiL{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:1.2px;margin-bottom:10px;font-weight:500}
.kpiV{font-size:30px;font-weight:700;letter-spacing:-1px}
.kpiS{font-size:12px;color:var(--text3);margin-top:6px}
.cBlue{color:var(--accent)}.cGreen{color:var(--green)}.cOrange{color:var(--orange)}.cPurple{color:var(--purple)}
.mainGrid{display:grid;grid-template-columns:1.2fr 1fr;gap:14px;margin-bottom:20px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px}
.cardH{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.cardT{font-size:13px;font-weight:600;color:var(--text2)}.cardC{font-size:11px;color:var(--text3)}
.nodeList{display:flex;flex-direction:column;gap:3px}
.nodeItem{display:grid;grid-template-columns:22px 1fr 44px 32px;align-items:center;gap:10px;padding:5px 8px;border-radius:6px;font-size:12px;transition:background .12s}
.nodeItem:hover{background:var(--surface2)}
.nodeRank{font-size:10px;color:var(--text3);text-align:center}
.nodeName{color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nodeName .hot{display:inline-block;font-size:9px;padding:1px 5px;border-radius:3px;background:rgba(245,158,11,0.12);color:var(--orange);font-weight:600;margin-left:4px}
.nodeBar{height:4px;background:var(--surface2);border-radius:2px;overflow:hidden}
.nodeBarFill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent),#60a5fa);transition:width .6s}
.nodeBarFill.hot{background:linear-gradient(90deg,var(--orange),var(--purple))}
.nodeTotal{font-size:11px;color:var(--text2);text-align:right;font-weight:500}
.nodeNew{font-size:10px;color:var(--text3);text-align:right}
.chartWrap{height:200px;position:relative}.chartWrap canvas{width:100%!important;height:100%!important}
.botRow{display:grid;grid-template-columns:260px 1fr;gap:14px}
.svcGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.svc{display:flex;flex-direction:column;align-items:center;gap:5px;padding:14px 8px;background:var(--surface2);border-radius:8px;border:1px solid var(--border)}
.svcDot{width:8px;height:8px;border-radius:50%;margin-bottom:2px}
.svcDot.on{background:var(--green);box-shadow:0 0 6px var(--green)}
.svcName{font-size:11px;color:var(--text2);font-weight:600}.svcPort{font-size:9px;color:var(--text3)}
.rssGrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:4px}
.rssItem{display:flex;align-items:center;gap:4px;padding:3px 6px;background:var(--surface2);border-radius:4px;font-size:10px;overflow:hidden}
.rssDot{width:4px;height:4px;border-radius:50%;flex-shrink:0}.rssName{color:var(--text2);overflow:hidden;text-overflow:ellipsis;flex:1}
.logList{margin-top:8px;border-top:1px solid var(--border);padding-top:6px;max-height:120px;overflow-y:auto}
.logItem{display:flex;gap:10px;padding:2px 6px;font-size:10px;align-items:center}
.logTime{color:var(--text3);width:55px;flex-shrink:0}.logText{color:var(--accent2)}.logWarn{color:var(--orange)}
@media(max-width:900px){.kpiRow{grid-template-columns:repeat(2,1fr)}.mainGrid,.botRow,.threeCol{grid-template-columns:1fr}.container{padding:16px}.nav{padding:12px 16px}}
</style>
</head>
<body>
<div class="glowA"></div><div class="glowB"></div>
<canvas id="bgCanvas"></canvas><div class="scanLine"></div>
<nav class="nav"><div class="nLeft"><span class="brand">INTEL DASH</span><span class="live"><span class="liveDot"></span>LIVE</span></div><div class="nRight"><span class="tag" id="scanTag">-</span><span class="clock" id="clock">-</span></div></nav>
<div class="container">
<div class="kpiRow">
<div class="kpi"><div class="kpiL">总采集</div><div class="kpiV cBlue" id="k1">0</div><div class="kpiS">原始条目</div></div>
<div class="kpi"><div class="kpiL">新增入库</div><div class="kpiV cGreen" id="k2">0</div><div class="kpiS">去重后</div></div>
<div class="kpi"><div class="kpiL">去重总数</div><div class="kpiV cOrange" id="k3">0</div><div class="kpiS">有效情报</div></div>
<div class="kpi"><div class="kpiL">冷却节点</div><div class="kpiV cPurple" id="k4">0</div><div class="kpiS">节流中</div></div>
</div>
<div class="mainGrid">
<div class="card"><div class="cardH"><span class="cardT">节点采集排名</span><span class="cardC" id="nodeCount"></span></div><div class="nodeList" id="nodeList"></div></div>
<div class="card"><div class="cardH"><span class="cardT">24h 采集趋势</span><span class="cardC">24h</span></div><div class="chartWrap"><canvas id="chart"></canvas></div></div></div>
<div class="botRow">
<div class="card"><div class="cardH"><span class="cardT">服务状态</span></div><div class="svcGrid"><div class="svc"><div class="svcDot on"></div><div class="svcName">Proxy</div><div class="svcPort">:1234</div></div><div class="svc"><div class="svcDot on"></div><div class="svcName">LiteLLM</div><div class="svcPort">:1235</div></div><div class="svc"><div class="svcDot on"></div><div class="svcName">KB</div><div class="svcPort">:8765</div></div></div></div>
<div class="card"><div class="cardH"><span class="cardT">RSS 数据源</span><span class="cardC" id="rssCount"></span></div><div class="rssGrid" id="rssGrid"></div><div class="logList" id="logList"></div></div></div></div>
<script>
var d=""" + DATA.replace('"', '\\"') + """;
k1.textContent=d.total_fetched;k2.textContent=d.total_new;k3.textContent=d.total_dedup;k4.textContent=d.cooling;
var t3=d.nodes.slice(0,3).map(function(n){return n.name.split(":").pop()||n.name}).join(", ");
scanTag.textContent=d.total_scans+" scans | "+t3;
nodeCount.textContent=d.nodes.length+" 节点";rssCount.textContent=d.rss_sources.length+" 源";
var mx=Math.max.apply(null,d.nodes.map(function(n){return n.total}))||1;
nodeList.innerHTML=d.nodes.map(function(n,i){var p=(n.total/mx*100).toFixed(1);return '<div class=nodeItem><div class=nodeRank>'+(i+1)+'</div><div class=nodeName>'+n.name+(n.new?'<span class=hot>+'+n.new+'</span>':'')+'</div><div class=nodeBar><div class="nodeBarFill'+(n.name.indexOf("金融")>=0?' hot':'')+'" style=width:'+p+'%></div></div><div class=nodeTotal>'+n.total+'</div><div class=nodeNew>'+(n.new?'+'+n.new:'')+'</div></div>'}).join("");
var ra=d.rss_activity||d.rss_sources;
rssGrid.innerHTML=ra.map(function(s){var a=s.today||1;var b="";for(var i=0;i<5;i++)b+="<span style=display:inline-block;width:"+(3+i*2)+"px;height:"+(3+i*2)+"px;background:"+(i<a/3?"#3b82f6":"#1e293b")+";border-radius:1px;margin:0 1px></span>";return '<div class=rssItem><span class=rssDot style=background:'+(s.enabled?"#22c55e":"#ef4444")+'></span><span class=rssName>'+s.name+'</span><span style=margin-left:auto;display:flex;align-items:flex-end;height:14px>'+b+'</span></div>'}).join("");
var lg=d.recent_logs||[];
logList.innerHTML=lg.length?lg.map(function(l){return '<div class=logItem><span class=logTime>'+l.time+'</span><span class="'+(l.ok?'logText':'logWarn')+'">'+(l.ok?'OK':'!!')+' '+l.text+'</span></div>'}).join(""):"";
var tf=d.trend_full||{hours:d.trend.map(function(t){return t.hour+":00"}),values:d.trend.map(function(t){return t.fetched})};
new Chart(document.getElementById("chart"),{type:"line",data:{labels:tf.hours,datasets:[{label:"采集",data:tf.values,borderColor:"#3b82f6",backgroundColor:"rgba(59,130,246,0.06)",fill:true,tension:0.3,pointRadius:0,pointHoverRadius:4,borderWidth:1.5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{backgroundColor:"#0d1321",titleColor:"#e2e8f0",bodyColor:"#94a3b8",borderColor:"#1e2a45",borderWidth:1,padding:10,cornerRadius:6,displayColors:false,callbacks:{title:function(t){return t[0].label},label:function(t){return t.raw+" 条"}}}},scales:{x:{ticks:{color:"#475569",font:{size:9},maxTicksLimit:6},grid:{color:"rgba(30,42,69,0.3)"}},y:{ticks:{color:"#475569",font:{size:9},maxTicksLimit:4},grid:{color:"rgba(30,42,69,0.3)"}}}}});
setInterval(function(){clock.textContent=new Date().toLocaleTimeString("zh-CN",{hour12:false})},1000);
</script></body></html>"""

with open("D:/maozhua/Codex/dash/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("OK:", len(html))