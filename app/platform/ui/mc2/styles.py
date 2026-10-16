"""Mission Control v2 styles: the calm light look approved in the redesign prototype (v3).

One accent, readable type, 44px touch targets, and colors that keep 4.5:1 contrast. Status tones
differ in lightness as well as hue so they can be told apart without color.
"""
from __future__ import annotations

MC2_CSS = r"""
:root{--ground:#F6F5F2;--surface:#FFFFFF;--ink:#17181C;--muted:#5E6470;--soft:#3F444D;--line:#E3E1DC;
--line-soft:#EFEDE8;--field:#CFCCC5;--accent:#2648C9;--accent-ink:#1A3496;--accent-soft:#EEF1FC;
--needs-bg:#FFF4DD;--needs:#8A4F00;--run-bg:#E8ECFB;--run:#1A3496;--stuck-bg:#FBE8E5;--stuck:#8E2318;
--done-bg:#E5F3EA;--done:#1E6B3A;--plain-bg:#EFEDE8;--plain:#3F444D}
*{box-sizing:border-box}
html,body{margin:0;background:var(--ground);color:var(--ink);
font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;font-size:16px;line-height:1.5}
a{color:var(--accent)}a:hover{color:var(--accent-ink)}
button,input,select,textarea{font:inherit;color:inherit}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.mc-app{min-height:100vh;display:flex;flex-wrap:wrap;align-items:stretch}
.mc-nav{flex:1 1 200px;max-width:100%;padding:24px 16px;background:var(--surface);border-right:1px solid var(--line);
display:flex;flex-direction:column;gap:4px}
.mc-brand{padding:4px 12px 20px;display:flex;flex-direction:column;gap:2px}
.mc-brand strong{font-size:16px}.mc-brand span{font-size:13px;color:var(--muted)}
.mc-nav a{text-decoration:none;padding:12px;border-radius:8px;color:var(--ink);font-size:15px;min-height:44px}
.mc-nav a[aria-current="page"]{background:var(--accent-soft);color:var(--accent-ink);font-weight:600}
.mc-nav .mc-spacer{flex-grow:1;min-height:24px}
.mc-nav .mc-classic{font-size:13px;color:var(--muted)}
.mc-main{flex:999 1 520px;min-width:0;padding:32px 40px 64px;display:flex;flex-direction:column;gap:28px}
.mc-head{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:flex-start}
.mc-head h1{margin:0;font-size:32px;font-weight:700;letter-spacing:-.01em}
.mc-head p{margin:6px 0 0;font-size:17px;color:var(--muted)}
h2.mc-h2{margin:0;font-size:20px;font-weight:600}
.mc-section{display:flex;flex-direction:column;gap:12px}
.mc-card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px}
.mc-decision{display:flex;flex-wrap:wrap;gap:14px;align-items:center}
.mc-decision .mc-text{flex:1 1 320px;min-width:0;display:flex;flex-direction:column;gap:6px}
.mc-decision h3{margin:0;font-size:17px;font-weight:600}
.mc-decision p{margin:0;font-size:15px;color:var(--muted)}
.mc-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.mc-btn{min-height:44px;padding:0 18px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-size:15px;
font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center}
.mc-btn:hover{background:var(--accent-ink);color:#fff}
.mc-btn.secondary{background:var(--surface);color:var(--ink);border:1px solid var(--field)}
.mc-btn.quiet{background:transparent;color:var(--accent);padding:0 12px}
.mc-btn[disabled]{opacity:.6;cursor:progress}
.mc-tag{align-self:flex-start;display:inline-flex;font-size:13px;font-weight:600;padding:3px 10px;border-radius:999px;
background:var(--plain-bg);color:var(--plain)}
.mc-tag.needs{background:var(--needs-bg);color:var(--needs)}.mc-tag.run{background:var(--run-bg);color:var(--run)}
.mc-tag.stuck{background:var(--stuck-bg);color:var(--stuck)}.mc-tag.done{background:var(--done-bg);color:var(--done)}
.mc-empty{color:var(--muted);font-size:15px;margin:0}
.mc-tabs{display:flex;flex-wrap:wrap;gap:6px}
.mc-tabs button{min-height:40px;padding:0 14px;border-radius:999px;border:1px solid var(--field);background:var(--surface);
font-size:14px;font-weight:600;cursor:pointer}
.mc-tabs button[aria-selected="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.mc-work{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}
.mc-list{list-style:none;margin:0;padding:0;flex:1 1 280px;min-width:0;display:flex;flex-direction:column;gap:8px}
.mc-row{width:100%;text-align:left;cursor:pointer;padding:12px 14px;border-radius:10px;background:var(--surface);
border:1px solid var(--line)}
.mc-row[aria-current="true"]{border:2px solid var(--accent)}
.mc-row strong{display:block;font-size:15px;line-height:1.35}
.mc-row .mc-meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:6px;font-size:13px;color:var(--muted)}
.mc-detail{flex:2 1 380px;min-width:0;display:flex;flex-direction:column;gap:16px}
.mc-detail h3{margin:0;font-size:20px;font-weight:700;line-height:1.3}
.mc-next{background:var(--ground);border-radius:10px;padding:14px 16px}
.mc-next span{font-size:13px;font-weight:600;color:var(--muted)}.mc-next p{margin:4px 0 0}
.mc-tasks{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px}
.mc-task{border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
.mc-task .mc-task-head{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;font-weight:600}
.mc-task small{color:var(--muted);font-size:14px}
.mc-detail details{font-size:14px;color:var(--soft)}
.mc-detail summary{cursor:pointer;font-weight:600;min-height:32px}
.mc-detail pre{white-space:pre-wrap;background:var(--ground);border-radius:8px;padding:10px;max-height:220px;overflow:auto;font-size:12px}
.mc-jarvis{flex:1 1 340px;max-width:100%;background:var(--surface);border-left:1px solid var(--line);padding:20px;
display:flex;flex-direction:column;gap:14px;max-height:100vh;position:sticky;top:0}
.mc-jarvis[hidden]{display:none}
.mc-jarvis-head{display:flex;justify-content:space-between;align-items:center;gap:8px}
.mc-jarvis-head h2{margin:0;font-size:18px}
.mc-convo{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px;overflow:auto;flex-grow:1}
.mc-msg{max-width:92%;font-size:15px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}
.mc-msg.me{align-self:flex-end;background:var(--accent);color:#fff;border-radius:12px 12px 4px 12px;padding:10px 14px}
.mc-msg.jarvis{align-self:flex-start}
.mc-msg.error{color:var(--stuck)}
.mc-msg .mc-actions{margin-top:10px}
.mc-composer{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--line-soft);padding-top:14px}
.mc-composer label{font-size:14px;font-weight:600;color:var(--soft)}
.mc-composer textarea{font-size:15px;padding:10px 12px;border:1px solid var(--field);border-radius:10px;resize:vertical;
background:#fff}
.mc-composer .mc-btn{align-self:flex-end}
.mc-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.mc-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.mc-metric{display:flex;flex-direction:column;gap:4px}.mc-metric span{font-size:14px;color:var(--muted)}
.mc-metric strong{font-size:28px;font-weight:700;line-height:1.2}
.mc-decision details{font-size:14px;color:var(--soft)}.mc-decision summary{cursor:pointer;font-weight:600;min-height:32px}
.mc-decision pre{white-space:pre-wrap;background:var(--ground);border-radius:8px;padding:10px;max-height:240px;overflow:auto;font-size:13px}
.mc-result{font-size:14px;color:var(--soft)}.mc-result:empty{display:none}
.mc-table-wrap{padding:0;overflow-x:auto}
.mc-table{width:100%;border-collapse:collapse;font-size:15px}
.mc-table th,.mc-table td{text-align:left;vertical-align:top;padding:12px 16px;border-bottom:1px solid var(--line-soft)}
.mc-table thead th{font-size:13px;font-weight:600;color:var(--muted)}
.mc-table tbody th{font-weight:600}.mc-table tbody th small{display:block;font-weight:400;font-size:13px;color:var(--muted)}
.mc-table tr:last-child>*{border-bottom:0}
.mc-app-line{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:4px}
.mc-steps,.mc-team,.mc-insights{list-style:none;margin:0;padding:0;display:grid;gap:12px;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.mc-steps span{font-size:13px;font-weight:600;color:var(--accent-ink)}
.mc-steps h3,.mc-person h3{margin:4px 0 6px;font-size:17px;font-weight:600}.mc-steps p,.mc-person p{margin:0;font-size:15px;color:var(--muted)}
.mc-person-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.mc-person-head h3{margin-top:0}
.mc-planned{background:var(--ground);border-style:dashed}.mc-planned ul{margin:0;padding-left:18px;font-size:14px;color:var(--soft);display:flex;flex-direction:column;gap:6px}
.mc-insights a{display:flex;flex-direction:column;gap:4px;text-decoration:none;color:var(--ink);height:100%}
.mc-insights a:hover{border-color:var(--accent)}.mc-insights span{font-size:14px;color:var(--muted)}
.mc-group{display:flex;flex-direction:column;gap:10px}.mc-group p{margin:0}.mc-h3{margin:8px 0 0;font-size:16px;font-weight:600}
.mc-fields{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}
.mc-fields label{display:flex;flex-direction:column;gap:4px;font-size:14px;font-weight:600;color:var(--soft);flex:1 1 200px;max-width:360px}
.mc-fields select,.mc-fields input,.mc-inline input{min-height:44px;padding:0 12px;border:1px solid var(--field);border-radius:10px;background:#fff;font-size:15px;font-weight:400;color:var(--ink)}
.mc-status{font-size:14px;color:var(--soft)}.mc-status:empty{display:none}.mc-status.bad{color:var(--stuck)}
.mc-rows{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.mc-rows>li{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;padding:10px 0;border-top:1px solid var(--line-soft)}
.mc-rows>li:first-child{border-top:0}.mc-rows small{display:block;font-size:13px;color:var(--muted)}
.mc-secret{font-family:ui-monospace,monospace;word-break:break-all;color:var(--ink)!important}
.mc-inline{display:flex;flex-wrap:wrap;gap:8px;width:100%}.mc-inline input{flex:1 1 220px}
.mc-app[hidden],.mc-login[hidden]{display:none}
.mc-login{min-height:100vh;display:grid;place-items:center;padding:24px 16px}
.mc-login-card{width:min(420px,100%);display:flex;flex-direction:column;gap:12px}.mc-login-card[hidden]{display:none}
.mc-login-card h1{margin:0;font-size:26px}.mc-login-card p{margin:0}
.mc-login-card label{display:flex;flex-direction:column;gap:4px;font-size:14px;font-weight:600;color:var(--soft)}
.mc-login-card input{min-height:44px;padding:0 12px;border:1px solid var(--field);border-radius:10px;font-size:15px;font-weight:400}
.mc-login-card .mc-btn.quiet{align-self:flex-start;padding:0}
@media (max-width:720px){.mc-nav{flex:1 1 100%;flex-direction:row;flex-wrap:wrap;align-items:center;gap:4px;padding:12px 12px;border-right:0;border-bottom:1px solid var(--line)}.mc-brand{width:100%;padding:4px 8px 8px;flex-direction:row;gap:8px;align-items:baseline}.mc-nav .mc-spacer{display:none}.mc-nav a{padding:10px 12px}.mc-main{padding:24px 16px 48px}.mc-table th,.mc-table td{padding:10px}.mc-metric strong{font-size:24px}.mc-jarvis{position:static;max-height:none;border-left:0;
border-top:1px solid var(--line)}}
"""
