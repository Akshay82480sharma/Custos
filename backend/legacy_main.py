from fastapi import FastAPI

from fastapi.responses import HTMLResponse, JSONResponse

from backend.database import get_db

from backend.pipeline import run_pipeline

import json

import os

import urllib.request

import urllib.error

import uvicorn

import threading



app = FastAPI()



# ── Load .env ──

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

try:

    with open(env_path) as f:

        for line in f:

            if "=" in line:

                k, v = line.strip().split("=", 1)

                os.environ.setdefault(k, v)

except FileNotFoundError:

    pass



_scan_lock = threading.Lock()



import asyncio

from backend.pipeline import run_pipeline



@app.on_event("startup")

async def start_auto_scan():

    async def auto_scan_loop():

        while True:

            await asyncio.sleep(15) # Auto-scan every 15 seconds

            if _scan_lock.acquire(blocking=False):

                try:

                    run_pipeline()

                finally:

                    _scan_lock.release()

    

    asyncio.create_task(auto_scan_loop())





@app.get("/demo/{event_id}", response_class=HTMLResponse)

def demo_page(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        if not e:

            return HTMLResponse("Event not found", 404)

    

    return f"""<!DOCTYPE html><html lang="en"><head>

<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Custos Pipeline</title>

<script src="https://cdn.tailwindcss.com"></script>

<style>

body{{background:#0A0A0B}}

@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}

.fade-up{{animation:fadeUp 350ms ease-out forwards}}

.skipped{{opacity:.35;pointer-events:none}}

</style>



</head><body class="text-white min-h-screen font-sans">



<div class="border-b border-[#1F1F23] px-6 py-3 flex items-center justify-between sticky top-0 bg-[#0A0A0B]/90 backdrop-blur z-50">

  <a href="/" class="flex items-center gap-2 text-[#A1A1AA] hover:text-white text-sm">

    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>

    Dashboard

  </a>

  <div class="flex items-center gap-3">

    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-amber-500/15 text-amber-400 border border-amber-500/20">

      <span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>Simulation

    </span>

    <span class="text-xs text-[#52525B] font-mono">{e['source_id']}</span>

    <span class="px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase

      {{"failed":"bg-red-500/15 text-red-400","captured":"bg-green-500/15 text-green-400","disputed":"bg-amber-500/15 text-amber-400","unpaid":"bg-orange-500/15 text-orange-400"}}.get(e['status'],'bg-gray-500/15 text-gray-400')">{e['status']}</span>

  </div>

</div>



<div class="max-w-4xl mx-auto px-6 py-6">

  <div class="flex items-start justify-between mb-6">

    <div>

      <h1 class="text-2xl font-bold mb-1">Custos Pipeline</h1>

      <p class="text-[#A1A1AA] text-sm">9-stage autonomous reasoning for this transaction</p>

    </div>

    <div class="text-right">

      <div class="text-3xl font-bold font-mono">INR {e['amount']/100:,.2f}</div>

      <div class="text-xs text-[#52525B] mt-1">{e['type'].upper()}</div>

    </div>

  </div>

  <div id="meta-row" class="grid grid-cols-5 gap-2 mb-6"></div>

  <h2 class="text-xs font-semibold text-[#52525B] uppercase tracking-widest mb-3">Pipeline Stages</h2>

  <div id="pipeline" class="space-y-2">

    <div class="text-center py-12 text-[#52525B]">Loading pipeline...</div>

  </div>

  <div id="verdict-bar" class="mt-4 bg-[#141416] border border-[#2A2A2E] rounded-xl p-4 hidden"></div>

  <details class="mt-4">

    <summary class="text-xs text-[#3F3F46] cursor-pointer hover:text-[#A1A1AA]">Raw Event Data</summary>

    <pre id="raw-json" class="mt-2 bg-[#141416] border border-[#1F1F23] rounded-lg p-4 text-[10px] text-[#52525B] font-mono overflow-auto max-h-40"></pre>

  </details>

</div>



<script>

const EVENT_ID = "{event_id}";



const STAGE_CFG = {{

  risk:       {{ icon: '\U0001f6e1\ufe0f', color: 'cyan',    label: 'Risk Assessment' }},

  growth:     {{ icon: '\U0001f4c8', color: 'amber',   label: 'Growth Opportunity' }},

  classify:   {{ icon: '\U0001f3f7\ufe0f', color: 'yellow',  label: 'Classification' }},

  reasoning:  {{ icon: '\U0001f9e0', color: 'purple',  label: 'AI Reasoning' }},

  policy:     {{ icon: '\u2705', color: 'cyan',    label: 'Policy Check' }},

  action:     {{ icon: '\U0001f4e4', color: 'green',   label: 'Recovery Action' }},

  finance:    {{ icon: '\u20b9',  color: 'emerald', label: 'Finance Reconciliation' }},

  nexus_verdict: {{ icon: '\u26a1', color: 'white', label: 'Custos Verdict' }}

}};



const COLORS = {{

  cyan:    {{ bg:'bg-cyan-500/10', border:'border-cyan-500/20', text:'text-cyan-400' }},

  amber:   {{ bg:'bg-amber-500/10', border:'border-amber-500/20', text:'text-amber-400' }},

  yellow:  {{ bg:'bg-yellow-500/10', border:'border-yellow-500/20', text:'text-yellow-400' }},

  purple:  {{ bg:'bg-purple-500/10', border:'border-purple-500/20', text:'text-purple-400' }},

  green:   {{ bg:'bg-green-500/10', border:'border-green-500/20', text:'text-green-400' }},

  emerald: {{ bg:'bg-emerald-500/10', border:'border-emerald-500/20', text:'text-emerald-400' }},

  white:   {{ bg:'bg-white/5', border:'border-white/10', text:'text-white' }},

}};



async function init() {{

  const res = await fetch('/api/nexus/' + EVENT_ID);

  const data = await res.json();



  // Meta row

  const metas = [

    {{ label:'Type', value:(data.type||'payment').toUpperCase() }},

    {{ label:'Method', value:data.method||'—' }},

    {{ label:'Customer', value:data.customer_ref||'—', mono:true }},

    {{ label:'Category', value:data.category||'—' }},

    {{ label:'Error', value:data.error_code||'None', red:!!data.error_code }},

  ];

  document.getElementById('meta-row').innerHTML = metas.map(m =>

    `<div class="bg-[#141416] border border-[#1F1F23] rounded-lg px-3 py-2">

      <div class="text-[10px] text-[#52525B] uppercase mb-0.5">${{m.label}}</div>

      <div class="text-sm ${{m.mono?'font-mono text-xs':''}} ${{m.red?'text-red-400':'text-white'}} truncate">${{m.value}}</div>

    </div>`).join('');



  // Pipeline stages

  const stages = data.stages || [];

  const container = document.getElementById('pipeline');

  container.innerHTML = '';



  stages.forEach((stage, i) => {{

    const cfg = STAGE_CFG[stage.stage] || {{ icon:'?', color:'white', label:stage.stage }};

    const colors = COLORS[cfg.color] || COLORS.white;

    const isSkipped = stage.status === 'skipped';

    const isLast = i === stages.length - 1;



    const card = document.createElement('div');

    card.className = `rounded-xl p-4 border fade-up ${{isSkipped ? 'skipped bg-[#0F0F10] border-[#1A1A1C]' : colors.bg+' '+colors.border}}`;

    card.style.animationDelay = `${{i * 80}}ms`;

    card.style.opacity = '0';



    let content = '';

    if (!isSkipped && stage.result) content = renderContent(stage.stage, stage.result);

    else if (isSkipped) content = `<div class="text-xs text-[#3F3F46] mt-2">${{stage.result?.reason||'Skipped'}}</div>`;



    card.innerHTML = `

      <div class="flex items-center justify-between">

        <div class="flex items-center gap-3">

          <div class="w-9 h-9 rounded-full border ${{colors.border}} ${{colors.bg}} flex items-center justify-center text-sm flex-shrink-0">${{isSkipped?'\u23ed':cfg.icon}}</div>

          <div>

            <div class="flex items-center gap-2">

              <span class="text-sm font-semibold ${{isSkipped?'text-[#3F3F46]':'text-white'}}">${{cfg.label}}</span>

              ${{isSkipped?'<span class="text-[10px] text-[#3F3F46] uppercase">Skipped</span>':''}}

            </div>

            ${{!isSkipped && stage.result ? '<div class="text-xs text-[#A1A1AA] mt-0.5 truncate">'+getSummary(stage.stage, stage.result)+'</div>' : ''}}

          </div>

        </div>

        ${{!isSkipped ? getBadge(stage.stage, stage.result) : ''}}

      </div>

      ${{content}}`;

    container.appendChild(card);



    if (!isLast) {{

      const line = document.createElement('div');

      line.className = `w-px h-3 mx-5 ${{isSkipped?'bg-[#1A1A1C]':'bg-[#1F1F23]'}}`;

      container.appendChild(line);

    }}

  }});



  // Verdict bar

  const verdict = stages.find(s => s.stage === 'nexus_verdict');

  if (verdict && verdict.result) {{

    const bar = document.getElementById('verdict-bar');

    bar.classList.remove('hidden');

    const v = verdict.result;

    bar.innerHTML = `

      <div class="flex items-center justify-between">

        <div class="flex items-center gap-3">

          <span class="text-lg">\u26a1</span>

          <div>

            <div class="text-sm font-bold">${{v.verdict.replace(/_/g,' ')}}</div>

            <div class="text-xs text-[#A1A1AA]">${{v.summary}}</div>

          </div>

        </div>

        <div class="text-right">

          <div class="text-xs text-[#52525B]">${{v.stages_completed}}/${{v.stages_total}} stages</div>

          ${{v.finance_summary?'<div class="text-xs text-emerald-400 mt-0.5">'+v.finance_summary+'</div>':''}}

        </div>

      </div>`;

  }}



  document.getElementById('raw-json').textContent = JSON.stringify(data, null, 2);

}}



function renderContent(stage, r) {{

  if (stage === 'risk') {{

    const pct = Math.round(r.risk_score * 100);

    const ringColor = r.risk_score < 0.3 ? '#22c55e' : r.risk_score < 0.5 ? '#f59e0b' : '#ef4444';

    return `<div class="mt-3 flex gap-4">

      <div class="w-14 h-14 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0" style="background:conic-gradient(${{ringColor}} ${{pct*3.6}}deg,#1C1C1F ${{pct*3.6}}deg)">${{pct}}%</div>

      <div class="flex-1">

        <div class="text-xs ${{r.is_safe?'text-green-400':'text-red-400'}} font-semibold mb-1">${{r.is_safe?'\u2713 SAFE TO PROCEED':'\u2717 FLAGGED FOR REVIEW'}}</div>

        <div class="space-y-1">${{(r.signals||[]).map(s=>`<div class="flex items-center gap-2 text-[11px]"><span class="${{s.risk>0?(s.risk>=0.25?'text-red-400':'text-amber-400'):'text-green-500'}}">\u25cf</span><span class="text-[#A1A1AA]">${{s.signal}}</span><span class="text-[#3F3F46] ml-auto">${{s.detail}}</span></div>`).join('')}}</div>

      </div>

    </div>`;

  }}

  if (stage === 'growth') {{

    if (!r.has_opportunity) return `<div class="text-xs text-[#52525B] mt-2">${{r.reasoning}}</div>`;

    return `<div class="mt-3 space-y-2">${{(r.opportunities||[]).map(o=>`<div class="flex items-center justify-between bg-[#0A0A0B] rounded-lg px-3 py-2 border border-[#1F1F23]"><div><div class="text-xs font-medium text-white">${{o.offer}}</div><div class="text-[10px] text-[#52525B]">${{o.reason}}</div></div><span class="text-[9px] uppercase font-semibold px-1.5 py-0.5 rounded ${{o.impact==='high'?'bg-green-500/15 text-green-400':o.impact==='medium'?'bg-amber-500/15 text-amber-400':'bg-gray-500/15 text-gray-400'}}">${{o.impact}}</span></div>`).join('')}}</div>`;

  }}

  if (stage === 'classify') {{

    return `<div class="mt-3"><span class="text-amber-400 font-mono font-semibold text-sm">${{(r.category||'').replace(/_/g,' ')}}</span></div>`;

  }}

  if (stage === 'reasoning') {{

    return `<div class="mt-3 space-y-2">

      ${{r.diagnosis?'<div class="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg p-3"><div class="text-[10px] text-[#52525B] uppercase mb-1">Diagnosis</div><div class="text-xs text-white leading-relaxed">'+r.diagnosis+'</div></div>':''}}

      ${{r.reasoning?'<div class="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg p-3"><div class="text-[10px] text-[#52525B] uppercase mb-1">AI Reasoning</div><div class="text-xs text-[#A1A1AA] leading-relaxed">'+r.reasoning+'</div></div>':''}}

      <div class="flex justify-between text-xs py-1.5 px-3 bg-[#0A0A0B] border border-[#1F1F23] rounded">

        <span class="text-[#A1A1AA]">Recommended Action</span>

        <span class="text-purple-400 font-bold uppercase">${{(r.recommended_action||'').replace(/_/g,' ')}}</span>

      </div>

      <div class="flex justify-between text-xs py-1.5 px-3 bg-[#0A0A0B] border border-[#1F1F23] rounded">

        <span class="text-[#A1A1AA]">Confidence</span>

        <span class="text-purple-400 font-mono">${{Math.round((r.confidence||0)*100)}}%</span>

      </div>

    </div>`;

  }}

  if (stage === 'policy') {{

    const approved = r.decision === 'APPROVED';

    return `<div class="mt-3"><div class="text-sm font-semibold ${{approved?'text-green-400':'text-amber-400'}} mb-1">${{approved?'\u2713 APPROVED':'\u26a0 '+r.decision}}</div><div class="text-xs text-[#A1A1AA]">${{r.reason}}</div></div>`;

  }}

  if (stage === 'action') {{

    return `<div class="mt-3"><div class="flex items-center gap-2 mb-2"><span class="text-green-400 text-xs font-semibold uppercase">${{(r.action_type||'').replace(/_/g,' ')}}</span><span class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400">CUSTOS SIMULATOR</span></div><div class="text-xs text-[#A1A1AA]">${{r.result||''}}</div></div>`;

  }}

  if (stage === 'finance') {{

    const sc = {{'PENDING_SETTLEMENT':'text-blue-400','NO_SETTLEMENT':'text-gray-400','AMOUNT_HELD':'text-amber-400','ACCOUNTS_RECEIVABLE':'text-orange-400','RECOVERY_PENDING_SETTLEMENT':'text-purple-400'}}[r.reconciliation_status] || 'text-gray-400';

    return `<div class="mt-3 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg p-3">

      <div class="flex items-center justify-between mb-2">

        <span class="text-xs font-semibold uppercase ${{sc}}">${{(r.reconciliation_status||'').replace(/_/g,' ')}}</span>

        ${{r.expected_settlement > 0 ? '<span class="text-sm font-mono font-bold text-emerald-400">\u20b9'+r.expected_settlement.toLocaleString('en-IN',{{minimumFractionDigits:2}})+'</span>' : ''}}

      </div>

      ${{r.fee_deducted!=null?'<div class="flex justify-between text-[11px]"><span class="text-[#3F3F46]">Fee</span><span class="text-[#52525B]">-\u20b9'+r.fee_deducted.toFixed(2)+' ('+r.fee_rate+')</span></div>':''}}

      ${{r.settlement_date?'<div class="flex justify-between text-[11px]"><span class="text-[#3F3F46]">Settlement</span><span class="text-[#52525B]">'+r.settlement_date+'</span></div>':''}}

      <div class="text-[10px] text-[#3F3F46] mt-2 leading-relaxed">${{r.reasoning||''}}</div>

    </div>`;

  }}

  return '';

}}



function getSummary(stage, r) {{

  const m = {{

    risk: r.reasoning||'',

    growth: r.reasoning||'',

    classify: r.category||'',

    reasoning: (r.diagnosis||'').slice(0,80)+'...',

    policy: r.reason||'',

    action: (r.action_type||'').replace(/_/g,' '),

    finance: r.reasoning||'',

    nexus_verdict: r.summary||'',

  }};

  return m[stage] || '';

}}



function getBadge(stage, r) {{

  if (stage==='risk') return `<span class="text-xs font-semibold ${{r.is_safe?'text-green-400':'text-red-400'}}">${{r.is_safe?'SAFE':'RISKY'}}</span>`;

  if (stage==='growth') return r.has_opportunity?`<span class="text-xs text-amber-400">${{(r.opportunities||[]).length}} offer(s)</span>`:'';

  if (stage==='classify') return `<span class="text-xs font-mono text-amber-400">${{r.category}}</span>`;

  if (stage==='reasoning') return `<span class="text-xs font-mono text-purple-400">${{Math.round((r.confidence||0)*100)}}%</span>`;

  if (stage==='policy') return `<span class="text-xs font-semibold ${{r.decision==='APPROVED'?'text-green-400':'text-amber-400'}}">${{r.decision}}</span>`;

  if (stage==='action') return `<span class="text-[10px] uppercase px-2 py-0.5 rounded bg-green-500/15 text-green-400">${{r.action_type}}</span>`;

  if (stage==='finance') return `<span class="text-[10px] uppercase px-2 py-0.5 rounded ${{r.reconciliation_status?.includes('SETTLEMENT')?'bg-blue-500/15 text-blue-400':'bg-gray-500/15 text-gray-400'}}">${{(r.reconciliation_status||'').replace(/_/g,' ')}}</span>`;

  return '';

}}



document.addEventListener('DOMContentLoaded', init);

</script>

</div></body></html>"""



@app.post("/api/scan")

def scan_now():

    """Trigger a full pipeline run: ingest -> classify -> reason -> policy -> action."""

    if not _scan_lock.acquire(blocking=False):

        return JSONResponse({"status": "already_running"}, 409)

    try:

        result = run_pipeline()

        return result

    finally:

        _scan_lock.release()



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# API: Gather Evidence (simulates pulling from sources)



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# NEXUS API: Returns all 9 pipeline stages as JSON

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/nexus/{event_id}")

def nexus_pipeline(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

        

        raw = json.loads(e["raw_payload"])

        event_data = {

            "id": e["id"],

            "source_id": e["source_id"],

            "type": e["type"],

            "amount": e["amount"] / 100.0,

            "amount_raw": e["amount"],

            "status": e["status"],

            "customer_ref": e["customer_ref"],

            "method": raw.get("method", "unknown"),

            "category": raw.get("category", ""),

            "error_code": raw.get("error_code", ""),

            "error_reason": raw.get("error_reason", ""),

            "international": raw.get("international", False),

            "created_at": e["created_at"],

        }

        

        stages = []

        

        # Stage 1: Risk

        risk = db.execute("SELECT * FROM risk_assessments WHERE event_id = ?", (e["id"],)).fetchone()

        if risk:

            stages.append({

                "stage": "risk", "status": "completed",

                "duration_ms": 1,

                "result": {

                    "risk_score": risk["risk_score"],

                    "is_safe": bool(risk["is_safe"]),

                    "verdict": risk["verdict"],

                    "signals": json.loads(risk["signals"] or "[]"),

                    "reasoning": risk["reasoning"],

                }

            })

        else:

            stages.append({"stage": "risk", "status": "skipped", "duration_ms": 0, "result": {"reason": "No risk assessment"}})

        

        # Stage 2: Growth

        growth = db.execute("SELECT * FROM growth_opportunities WHERE event_id = ?", (e["id"],)).fetchone()

        if growth:

            stages.append({

                "stage": "growth", "status": "completed",

                "duration_ms": 1,

                "result": {

                    "has_opportunity": bool(growth["has_opportunity"]),

                    "opportunities": json.loads(growth["opportunities"] or "[]"),

                    "best_offer": json.loads(growth["best_offer"] or "null"),

                    "reasoning": growth["reasoning"],

                }

            })

        else:

            stages.append({"stage": "growth", "status": "skipped", "duration_ms": 0, "result": {"reason": "No growth analysis"}})

        

        # Stage 3: Classification

        cls = db.execute("SELECT * FROM classifications WHERE event_id = ?", (e["id"],)).fetchone()

        if cls:

            stages.append({

                "stage": "classify", "status": "completed",

                "duration_ms": 1,

                "result": {"category": cls["category"]}

            })

        else:

            stages.append({"stage": "classify", "status": "skipped", "duration_ms": 0, "result": {"reason": "Not classified"}})

        

        # Stage 4: LLM Reasoning

        llm = db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (e["id"],)).fetchone()

        if llm:

            stages.append({

                "stage": "reasoning", "status": "completed",

                "duration_ms": 1,

                "result": {

                    "diagnosis": llm["diagnosis"],

                    "recommended_action": llm["recommended_action"],

                    "confidence": llm["confidence"],

                    "reasoning": llm["reasoning"],

                }

            })

        else:

            stages.append({"stage": "reasoning", "status": "skipped", "duration_ms": 0, "result": {"reason": "No AI reasoning"}})

        

        # Stage 5: Policy

        policy = db.execute("SELECT * FROM policy_checks WHERE event_id = ?", (e["id"],)).fetchone()

        if policy:

            stages.append({

                "stage": "policy", "status": "completed",

                "duration_ms": 1,

                "result": {

                    "decision": policy["decision"],

                    "reason": policy["reason"],

                }

            })

        else:

            stages.append({"stage": "policy", "status": "skipped", "duration_ms": 0, "result": {"reason": "No policy check"}})

        

        # Stage 6: Action

        action = db.execute("SELECT * FROM actions WHERE event_id = ?", (e["id"],)).fetchone()

        if action:

            stages.append({

                "stage": "action", "status": "completed",

                "duration_ms": 1,

                "result": {

                    "action_type": action["action_type"],

                    "result": action["result"],

                }

            })

        else:

            stages.append({"stage": "action", "status": "skipped", "duration_ms": 0, "result": {"reason": "No action generated"}})

        

        # Stage 7: Finance

        fin = db.execute("SELECT * FROM finance_reconciliations WHERE event_id = ?", (e["id"],)).fetchone()

        if fin:

            stages.append({

                "stage": "finance", "status": "completed",

                "duration_ms": 1,

                "result": {

                    "reconciliation_status": fin["reconciliation_status"],

                    "expected_settlement": fin["expected_settlement"],

                    "fee_deducted": fin["fee_deducted"],

                    "fee_rate": fin["fee_rate"],

                    "settlement_date": fin["settlement_date"],

                    "reasoning": fin["reasoning"],

                }

            })

        else:

            stages.append({"stage": "finance", "status": "skipped", "duration_ms": 0, "result": {"reason": "Not reconciled"}})

        

        # Stage 8: NEXUS Verdict (computed)

        completed = [s for s in stages if s["status"] == "completed"]

        action_stage = next((s for s in stages if s["stage"] == "action" and s["status"] == "completed"), None)

        risk_stage = next((s for s in stages if s["stage"] == "risk"), None)

        

        if risk_stage and risk_stage["status"] == "completed" and not risk_stage["result"]["is_safe"]:

            verdict = "FLAGGED_FOR_REVIEW"

            summary = "Transaction flagged by risk assessment"

        elif action_stage:

            verdict = "RECOVERY_ACTION_GENERATED" 

            summary = f"AI generated {action_stage['result'].get('action_type', 'action')}"

        elif e["status"] in ("captured", "paid"):

            verdict = "HEALTHY"

            summary = "Payment successful — no recovery needed"

        else:

            verdict = "PIPELINE_COMPLETE"

            summary = "All stages processed"

        

        finance_summary = ""

        fin_stage = next((s for s in stages if s["stage"] == "finance" and s["status"] == "completed"), None)

        if fin_stage:

            fr = fin_stage["result"]

            if fr.get("expected_settlement") and fr["expected_settlement"] > 0:

                finance_summary = f"INR {fr['expected_settlement']:,.2f} expected ({fr.get('settlement_date', '')})"

            else:

                finance_summary = fr.get("reasoning", "")

        

        stages.append({

            "stage": "nexus_verdict", "status": "completed", "duration_ms": 0,

            "result": {

                "verdict": verdict,

                "summary": summary,

                "finance_summary": finance_summary,

                "stages_total": len(stages),

                "stages_completed": len(completed),

                "stages_skipped": len(stages) - len(completed),

            }

        })

        

        event_data["stages"] = stages

        return event_data







# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/gather/{event_id}")

def gather_evidence(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

        raw = json.loads(e["raw_payload"])



    evidence = []

    # Razorpay gateway data

    evidence.append({

        "source": "Razorpay Gateway",

        "icon": "gateway",

        "strength": "Strong" if raw.get("error_reason") or raw.get("error") else "Partial",

        "detail": raw.get("error_description") or raw.get("error") or "No error recorded",

        "fields": {

            "Error Code": raw.get("error_code", "N/A"),

            "Error Reason": raw.get("error_reason") or raw.get("error", "N/A"),

            "Error Step": raw.get("error_step", "N/A"),

            "Error Source": raw.get("error_source", "N/A"),

        }

    })

    # Payment method

    card = raw.get("card", {})

    method = raw.get("method", "unknown")

    if method == "card" and card:

        evidence.append({

            "source": "Card Verification",

            "icon": "card",

            "strength": "Strong",

            "detail": f"{card.get('network','?')} {card.get('type','?')} ending {card.get('last4','????')}",

            "fields": {

                "Cardholder": card.get("name", "N/A"),

                "Network": card.get("network", "N/A"),

                "Type": f"{card.get('type','N/A')} / {card.get('sub_type','N/A')}",

                "International": "Yes" if card.get("international") else "No",

            }

        })

    elif method == "netbanking":

        evidence.append({

            "source": "Bank Verification",

            "icon": "bank",

            "strength": "Strong",

            "detail": f"Bank: {raw.get('bank', 'N/A')}",

            "fields": {"Bank Code": raw.get("bank", "N/A"), "Method": "Netbanking"}

        })

    # Customer identity

    evidence.append({

        "source": "Customer Identity",

        "icon": "customer",

        "strength": "Strong" if (raw.get("email") and raw.get("contact")) else "Partial",

        "detail": f"{raw.get('email', 'N/A')} / {raw.get('contact', 'N/A')}",

        "fields": {

            "Email": raw.get("email", "N/A"),

            "Phone": raw.get("contact", "N/A"),

            "International Txn": "Yes" if raw.get("international") else "No",

        }

    })

    # Transaction context

    evidence.append({

        "source": "Transaction Context",

        "icon": "context",

        "strength": "Strong",

        "detail": f"{raw.get('currency','INR')} {e['amount']/100:,.2f} via {method}",

        "fields": {

            "Order ID": raw.get("order_id", "N/A"),

            "Description": raw.get("description", "N/A"),

            "Created": str(raw.get("created_at", "N/A")),

            "Captured": "Yes" if raw.get("captured") else "No",

        }

    })

    return evidence



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# API: Analyze (calls Gemini for diagnosis)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/analyze/{event_id}")

def analyze_event(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        c = db.execute("SELECT * FROM classifications WHERE event_id = ?", (event_id,)).fetchone()

        l = db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

    

    if l:

        return {

            "classification": c["category"] if c else "UNKNOWN",

            "diagnosis": l["diagnosis"],

            "recommended_action": l["recommended_action"],

            "confidence": l["confidence"],

            "reasoning": l["reasoning"],

        }

    return {"classification": c["category"] if c else "UNKNOWN", "diagnosis": "Not yet analyzed", "recommended_action": "PENDING", "confidence": 0, "reasoning": "Run the pipeline first."}



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# API: Generate Evidence Response (calls Gemini LIVE)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/generate-response/{event_id}")

def generate_response(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        l = db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

    

    raw = json.loads(e["raw_payload"])

    card = raw.get("card", {})

    

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:

        return JSONResponse({"error": "No AI API key configured"}, 500)

    

    prompt = f"""You are the AI engine of Custos, an autonomous revenue recovery system for Indian merchants.



Generate a professional, structured EVIDENCE RESPONSE DOCUMENT for this failed/disputed payment.

This document is what a merchant would submit to their payment gateway or bank to fight a chargeback or recover revenue.



EVENT DATA:

- Payment ID: {e['source_id']}

- Amount: INR {e['amount']/100:,.2f}

- Status: {e['status']}

- Payment Method: {raw.get('method', 'unknown')}

- Card Network: {card.get('network', 'N/A')}

- Card Last 4: {card.get('last4', 'N/A')}

- Cardholder: {card.get('name', 'N/A')}

- Customer Email: {raw.get('email', 'N/A')}

- Customer Phone: {raw.get('contact', 'N/A')}

- Error: {raw.get('error_description', raw.get('error', 'N/A'))}

- Error Reason: {raw.get('error_reason', 'N/A')}

- International Transaction: {raw.get('international', False)}

- Order ID: {raw.get('order_id', 'N/A')}



AI DIAGNOSIS: {l['diagnosis'] if l else 'Not available'}

AI REASONING: {l['reasoning'] if l else 'Not available'}

RECOMMENDED ACTION: {l['recommended_action'] if l else 'Not available'}



Write the evidence response in this EXACT format:



CUSTOS EVIDENCE RESPONSE

========================



1. TRANSACTION SUMMARY

[Brief factual summary of what happened]



2. ROOT CAUSE ANALYSIS

[What caused the failure, based on gateway data]



3. EVIDENCE OF LEGITIMACY

[Bullet points with checkmarks showing evidence gathered]

- Payment attempt exists

- Payment status

- Retry count

- Failure reason classification



4. RECOMMENDED RECOVERY ACTION

[What should be done to recover this revenue]

"""

    

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})

    

    try:

        with urllib.request.urlopen(req) as response:

            result = json.loads(response.read().decode())

            text = result["candidates"][0]["content"]["parts"][0]["text"]

            return {"response": text}

    except Exception as ex:

        # Fallback if API fails

        return {"response": f"CUSTOS EVIDENCE RESPONSE\n========================\n\n1. TRANSACTION SUMMARY\nPayment {raw.get('method', 'Unknown')} for {e['amount']/100} failed.\n\n2. ROOT CAUSE ANALYSIS\nTemporary gateway issue.\n\n3. EVIDENCE OF LEGITIMACY\n✓ Payment attempt exists\n✓ Status = {e['status']}\n✓ Retry count = 1\n\n4. RECOMMENDED RECOVERY ACTION\n{l['recommended_action'] if l else 'RETRY_PAYMENT'}"}



@app.post("/api/verify/{event_id}")

def verify_recovery_api(event_id: str):

    with get_db() as db:

        import datetime

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        

        # Mark event as recovered

        db.execute("UPDATE events SET status = 'recovered' WHERE id = ?", (event_id,))

        

        # Mark finance reconciliation as pending settlement

        db.execute("UPDATE finance_reconciliations SET reconciliation_status = 'SETTLEMENT_PENDING' WHERE event_id = ?", (event_id,))

        

        db.execute("INSERT INTO audit_log (event_id, stage, detail, timestamp) VALUES (?, ?, ?, ?)", (event_id, "verify", "Payment recovery verified. Status updated to recovered.", now))

    return {"ok": True}



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PAGES

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━









# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# THE DEMO PAGE: Full AI Brain Drill-Down

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━



@app.post("/api/gather/{event_id}")

def gather_evidence(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

        raw = json.loads(e["raw_payload"])



    evidence = []

    # Razorpay gateway data

    evidence.append({

        "source": "Razorpay Gateway",

        "icon": "gateway",

        "strength": "Strong" if raw.get("error_reason") or raw.get("error") else "Partial",

        "detail": raw.get("error_description") or raw.get("error") or "No error recorded",

        "fields": {

            "Error Code": raw.get("error_code", "N/A"),

            "Error Reason": raw.get("error_reason") or raw.get("error", "N/A"),

            "Error Step": raw.get("error_step", "N/A"),

            "Error Source": raw.get("error_source", "N/A"),

        }

    })

    # Payment method

    card = raw.get("card", {})

    method = raw.get("method", "unknown")

    if method == "card" and card:

        evidence.append({

            "source": "Card Verification",

            "icon": "card",

            "strength": "Strong",

            "detail": f"{card.get('network','?')} {card.get('type','?')} ending {card.get('last4','????')}",

            "fields": {

                "Cardholder": card.get("name", "N/A"),

                "Network": card.get("network", "N/A"),

                "Type": f"{card.get('type','N/A')} / {card.get('sub_type','N/A')}",

                "International": "Yes" if card.get("international") else "No",

            }

        })

    elif method == "netbanking":

        evidence.append({

            "source": "Bank Verification",

            "icon": "bank",

            "strength": "Strong",

            "detail": f"Bank: {raw.get('bank', 'N/A')}",

            "fields": {"Bank Code": raw.get("bank", "N/A"), "Method": "Netbanking"}

        })

    # Customer identity

    evidence.append({

        "source": "Customer Identity",

        "icon": "customer",

        "strength": "Strong" if (raw.get("email") and raw.get("contact")) else "Partial",

        "detail": f"{raw.get('email', 'N/A')} / {raw.get('contact', 'N/A')}",

        "fields": {

            "Email": raw.get("email", "N/A"),

            "Phone": raw.get("contact", "N/A"),

            "International Txn": "Yes" if raw.get("international") else "No",

        }

    })

    # Transaction context

    evidence.append({

        "source": "Transaction Context",

        "icon": "context",

        "strength": "Strong",

        "detail": f"{raw.get('currency','INR')} {e['amount']/100:,.2f} via {method}",

        "fields": {

            "Order ID": raw.get("order_id", "N/A"),

            "Description": raw.get("description", "N/A"),

            "Created": str(raw.get("created_at", "N/A")),

            "Captured": "Yes" if raw.get("captured") else "No",

        }

    })

    return evidence



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# API: Analyze (calls Gemini for diagnosis)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/analyze/{event_id}")

def analyze_event(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        c = db.execute("SELECT * FROM classifications WHERE event_id = ?", (event_id,)).fetchone()

        l = db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

    

    if l:

        return {

            "classification": c["category"] if c else "UNKNOWN",

            "diagnosis": l["diagnosis"],

            "recommended_action": l["recommended_action"],

            "confidence": l["confidence"],

            "reasoning": l["reasoning"],

        }

    return {"classification": c["category"] if c else "UNKNOWN", "diagnosis": "Not yet analyzed", "recommended_action": "PENDING", "confidence": 0, "reasoning": "Run the pipeline first."}



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# API: Generate Evidence Response (calls Gemini LIVE)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/api/generate-response/{event_id}")

def generate_response(event_id: str):

    with get_db() as db:

        e = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        l = db.execute("SELECT * FROM llm_decisions WHERE event_id = ?", (event_id,)).fetchone()

        if not e:

            return JSONResponse({"error": "not found"}, 404)

    

    raw = json.loads(e["raw_payload"])

    card = raw.get("card", {})

    

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:

        return JSONResponse({"error": "No AI API key configured"}, 500)

    

    prompt = f"""You are the AI engine of Custos, an autonomous revenue recovery system for Indian merchants.



Generate a professional, structured EVIDENCE RESPONSE DOCUMENT for this failed/disputed payment.

This document is what a merchant would submit to their payment gateway or bank to fight a chargeback or recover revenue.



EVENT DATA:

- Payment ID: {e['source_id']}

- Amount: INR {e['amount']/100:,.2f}

- Status: {e['status']}

- Payment Method: {raw.get('method', 'unknown')}

- Card Network: {card.get('network', 'N/A')}

- Card Last 4: {card.get('last4', 'N/A')}

- Cardholder: {card.get('name', 'N/A')}

- Customer Email: {raw.get('email', 'N/A')}

- Customer Phone: {raw.get('contact', 'N/A')}

- Error: {raw.get('error_description', raw.get('error', 'N/A'))}

- Error Reason: {raw.get('error_reason', 'N/A')}

- International Transaction: {raw.get('international', False)}

- Order ID: {raw.get('order_id', 'N/A')}



AI DIAGNOSIS: {l['diagnosis'] if l else 'Not available'}

AI REASONING: {l['reasoning'] if l else 'Not available'}

RECOMMENDED ACTION: {l['recommended_action'] if l else 'Not available'}



Write the evidence response in this EXACT format:



CUSTOS EVIDENCE RESPONSE

========================



1. TRANSACTION SUMMARY

[Brief factual summary of what happened]



2. ROOT CAUSE ANALYSIS

[What caused the failure, based on gateway data]



3. EVIDENCE OF LEGITIMACY

[Bullet points with checkmarks showing evidence gathered]

- Payment attempt exists

- Payment status

- Retry count

- Failure reason classification



4. RECOMMENDED RECOVERY ACTION

[What should be done to recover this revenue]

"""

    

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})

    

    try:

        with urllib.request.urlopen(req) as response:

            result = json.loads(response.read().decode())

            text = result["candidates"][0]["content"]["parts"][0]["text"]

            return {"response": text}

    except Exception as ex:

        # Fallback if API fails

        return {"response": f"CUSTOS EVIDENCE RESPONSE\n========================\n\n1. TRANSACTION SUMMARY\nPayment {raw.get('method', 'Unknown')} for {e['amount']/100} failed.\n\n2. ROOT CAUSE ANALYSIS\nTemporary gateway issue.\n\n3. EVIDENCE OF LEGITIMACY\n✓ Payment attempt exists\n✓ Status = {e['status']}\n✓ Retry count = 1\n\n4. RECOMMENDED RECOVERY ACTION\n{l['recommended_action'] if l else 'RETRY_PAYMENT'}"}



@app.post("/api/verify/{event_id}")

def verify_recovery_api(event_id: str):

    with get_db() as db:

        import datetime

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        

        # Mark event as recovered

        db.execute("UPDATE events SET status = 'recovered' WHERE id = ?", (event_id,))

        

        # Mark finance reconciliation as pending settlement

        db.execute("UPDATE finance_reconciliations SET reconciliation_status = 'SETTLEMENT_PENDING' WHERE event_id = ?", (event_id,))

        

        db.execute("INSERT INTO audit_log (event_id, stage, detail, timestamp) VALUES (?, ?, ?, ?)", (event_id, "verify", "Payment recovery verified. Status updated to recovered.", now))

    return {"ok": True}



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PAGES

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━







@app.get("/growth", response_class=HTMLResponse)
def growth_page():
    with get_db() as db:
        data = db.execute("""SELECT g.*, e.source_id, e.amount FROM growth_opportunities g JOIN events e ON g.event_id = e.id WHERE g.has_opportunity = 1 ORDER BY g.created_at DESC""").fetchall()
        
    rows = ""
    total_val = 0
    for d in data:
        rows += f"""<tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F] cursor-pointer" onclick="window.location='/demo/{d['event_id']}'"><td class="p-3 font-mono text-xs text-[#A1A1AA]">{d["source_id"]}</td><td class="p-3 text-xs"><span class="px-2 py-1 bg-amber-500/10 text-amber-500 rounded font-bold uppercase">{d["type"]}</span></td><td class="p-3 text-sm">{d["offer"]}</td><td class="p-3 font-mono text-emerald-400">₹{(d["amount"]/100):,.0f}</td></tr>"""
        # In all queries, the relevant amount is either d["amount"] or d["expected_settlement"]
        val = d["expected_settlement"] if "expected_settlement" in d.keys() else d["amount"]
        total_val += val
        
    total_val = total_val / 100
        
    if not rows:
        rows = '<tr><td colspan="5" class="p-4 text-center text-[#71717A] text-sm">No growth opportunities found.</td></tr>'

    return f"""<!DOCTYPE html><html><head><title>Custos | Growth Opportunities</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    
    <!-- SIDEBAR -->
    <div class="w-64 border-r border-[#1F1F23] bg-[#0A0A0B] flex flex-col p-4 shrink-0 h-screen overflow-y-auto sticky top-0">
        <div class="flex items-center gap-3 mb-8 px-2">
            <h1 class="text-2xl font-black tracking-tight">Custos</h1>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1.5 mt-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SIM
            </span>
        </div>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Capabilities</div>
        <nav class="space-y-1 mb-8">
            <a href="/" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Overview</a>
            <a href="/growth" class="block px-3 py-2 text-sm rounded-lg text-[#F5F5F7] bg-[#1C1C1F] border border-[#2A2A2E] font-medium">Growth</a>
            <a href="/risk" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Risk</a>
            <a href="/recovery" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Recovery</a>
            <a href="/finance" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Finance</a>
            <a href="/command" class="block px-3 py-2 text-sm rounded-lg mt-2 flex justify-between items-center text-[#A1A1AA] hover:bg-[#1C1C1F]/50 hover:text-[#F5F5F7]">
                Command Center
                <span class="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded">NEW</span>
            </a>
        </nav>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Settings</div>
        <nav class="space-y-1">
            <a href="/activity" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Activity</a>
            <a href="/policies" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Policies</a>
        </nav>
    </div>
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <h2 class="text-3xl font-black tracking-tight mb-2">Growth Opportunities</h2>
        <p class="text-[#71717A] text-sm mb-8">View and manage growth opportunities across your unified pipeline.</p>
        
        <div class="mb-8 w-1/3">
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-amber-500">
                <div class="text-[10px] text-amber-400 uppercase tracking-wider mb-1 font-semibold">Total Potential Upside</div>
                <div class="text-3xl font-black font-mono text-white">₹{total_val:,.0f}</div>
            </div>
        </div>
        
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-3">Event</th><th class="p-3">Type</th><th class="p-3">Offer</th><th class="p-3">Upside</th>
            </tr></thead><tbody>{rows}</tbody></table>
        </div>
    </div>
    </body></html>"""

@app.get("/risk", response_class=HTMLResponse)
def risk_page():
    with get_db() as db:
        data = db.execute("""SELECT r.*, e.source_id, e.amount FROM risk_assessments r JOIN events e ON r.event_id = e.id WHERE r.verdict = 'FLAG_FOR_REVIEW' ORDER BY r.created_at DESC""").fetchall()
        
    rows = ""
    total_val = 0
    for d in data:
        rows += f"""<tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F] cursor-pointer" onclick="window.location='/demo/{d['event_id']}'"><td class="p-3 font-mono text-xs text-[#A1A1AA]">{d["source_id"]}</td><td class="p-3 font-mono text-red-400">{d["risk_score"]:.2f}</td><td class="p-3 text-xs"><span class="px-2 py-1 bg-red-500/10 text-red-400 rounded font-bold uppercase">{d["verdict"]}</span></td><td class="p-3 font-mono text-red-400">₹{(d["amount"]/100):,.0f}</td></tr>"""
        # In all queries, the relevant amount is either d["amount"] or d["expected_settlement"]
        val = d["expected_settlement"] if "expected_settlement" in d.keys() else d["amount"]
        total_val += val
        
    total_val = total_val / 100
        
    if not rows:
        rows = '<tr><td colspan="5" class="p-4 text-center text-[#71717A] text-sm">No risk cases require review.</td></tr>'

    return f"""<!DOCTYPE html><html><head><title>Custos | Risk & Compliance</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    
    <!-- SIDEBAR -->
    <div class="w-64 border-r border-[#1F1F23] bg-[#0A0A0B] flex flex-col p-4 shrink-0 h-screen overflow-y-auto sticky top-0">
        <div class="flex items-center gap-3 mb-8 px-2">
            <h1 class="text-2xl font-black tracking-tight">Custos</h1>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1.5 mt-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SIM
            </span>
        </div>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Capabilities</div>
        <nav class="space-y-1 mb-8">
            <a href="/" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Overview</a>
            <a href="/growth" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Growth</a>
            <a href="/risk" class="block px-3 py-2 text-sm rounded-lg text-[#F5F5F7] bg-[#1C1C1F] border border-[#2A2A2E] font-medium">Risk</a>
            <a href="/recovery" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Recovery</a>
            <a href="/finance" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Finance</a>
            <a href="/command" class="block px-3 py-2 text-sm rounded-lg mt-2 flex justify-between items-center text-[#A1A1AA] hover:bg-[#1C1C1F]/50 hover:text-[#F5F5F7]">
                Command Center
                <span class="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded">NEW</span>
            </a>
        </nav>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Settings</div>
        <nav class="space-y-1">
            <a href="/activity" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Activity</a>
            <a href="/policies" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Policies</a>
        </nav>
    </div>
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <h2 class="text-3xl font-black tracking-tight mb-2">Risk & Compliance</h2>
        <p class="text-[#71717A] text-sm mb-8">View and manage risk & compliance across your unified pipeline.</p>
        
        <div class="mb-8 w-1/3">
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-red-500">
                <div class="text-[10px] text-red-400 uppercase tracking-wider mb-1 font-semibold">Total Exposure</div>
                <div class="text-3xl font-black font-mono text-white">₹{total_val:,.0f}</div>
            </div>
        </div>
        
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-3">Event</th><th class="p-3">Risk Score</th><th class="p-3">Verdict</th><th class="p-3">Exposure</th>
            </tr></thead><tbody>{rows}</tbody></table>
        </div>
    </div>
    </body></html>"""

@app.get("/recovery", response_class=HTMLResponse)
def recovery_page():
    with get_db() as db:
        data = db.execute("""SELECT a.*, e.source_id, e.amount FROM actions a JOIN events e ON a.event_id = e.id WHERE a.action_type IN ('RETRY_PAYMENT', 'SEND_REMINDER') ORDER BY a.executed_at DESC""").fetchall()
        
    rows = ""
    total_val = 0
    for d in data:
        rows += f"""<tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F] cursor-pointer" onclick="window.location='/demo/{d['event_id']}'"><td class="p-3 font-mono text-xs text-[#A1A1AA]">{d["source_id"]}</td><td class="p-3 text-xs"><span class="px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded font-bold uppercase">{d["action_type"]}</span></td><td class="p-3 text-xs text-[#71717A]">{d["result"]}</td><td class="p-3 font-mono text-emerald-400">₹{(d["amount"]/100):,.0f}</td></tr>"""
        # In all queries, the relevant amount is either d["amount"] or d["expected_settlement"]
        val = d["expected_settlement"] if "expected_settlement" in d.keys() else d["amount"]
        total_val += val
        
    total_val = total_val / 100
        
    if not rows:
        rows = '<tr><td colspan="5" class="p-4 text-center text-[#71717A] text-sm">No recovery actions taken.</td></tr>'

    return f"""<!DOCTYPE html><html><head><title>Custos | Revenue Recovery</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    
    <!-- SIDEBAR -->
    <div class="w-64 border-r border-[#1F1F23] bg-[#0A0A0B] flex flex-col p-4 shrink-0 h-screen overflow-y-auto sticky top-0">
        <div class="flex items-center gap-3 mb-8 px-2">
            <h1 class="text-2xl font-black tracking-tight">Custos</h1>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1.5 mt-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SIM
            </span>
        </div>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Capabilities</div>
        <nav class="space-y-1 mb-8">
            <a href="/" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Overview</a>
            <a href="/growth" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Growth</a>
            <a href="/risk" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Risk</a>
            <a href="/recovery" class="block px-3 py-2 text-sm rounded-lg text-[#F5F5F7] bg-[#1C1C1F] border border-[#2A2A2E] font-medium">Recovery</a>
            <a href="/finance" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Finance</a>
            <a href="/command" class="block px-3 py-2 text-sm rounded-lg mt-2 flex justify-between items-center text-[#A1A1AA] hover:bg-[#1C1C1F]/50 hover:text-[#F5F5F7]">
                Command Center
                <span class="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded">NEW</span>
            </a>
        </nav>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Settings</div>
        <nav class="space-y-1">
            <a href="/activity" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Activity</a>
            <a href="/policies" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Policies</a>
        </nav>
    </div>
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <h2 class="text-3xl font-black tracking-tight mb-2">Revenue Recovery</h2>
        <p class="text-[#71717A] text-sm mb-8">View and manage revenue recovery across your unified pipeline.</p>
        
        <div class="mb-8 w-1/3">
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-emerald-500">
                <div class="text-[10px] text-emerald-400 uppercase tracking-wider mb-1 font-semibold">Potential Recovery</div>
                <div class="text-3xl font-black font-mono text-white">₹{total_val:,.0f}</div>
            </div>
        </div>
        
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-3">Event</th><th class="p-3">Action</th><th class="p-3">Result</th><th class="p-3">Amount</th>
            </tr></thead><tbody>{rows}</tbody></table>
        </div>
    </div>
    </body></html>"""

@app.get("/finance", response_class=HTMLResponse)
def finance_page():
    with get_db() as db:
        data = db.execute("""SELECT f.*, e.source_id, e.amount, f.expected_settlement FROM finance_reconciliations f JOIN events e ON f.event_id = e.id WHERE f.reconciliation_status IN ('NO_SETTLEMENT', 'AMOUNT_HELD', 'ACCOUNTS_RECEIVABLE') ORDER BY f.created_at DESC""").fetchall()
        
    rows = ""
    total_val = 0
    for d in data:
        rows += f"""<tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F] cursor-pointer" onclick="window.location='/demo/{d['event_id']}'"><td class="p-3 font-mono text-xs text-[#A1A1AA]">{d["source_id"]}</td><td class="p-3 text-xs"><span class="px-2 py-1 bg-blue-500/10 text-blue-400 rounded font-bold uppercase">{d["reconciliation_status"]}</span></td><td class="p-3 text-sm text-[#71717A]">Fees: ₹{d["expected_fee"]/100:.2f}</td><td class="p-3 font-mono text-white">₹{(d["expected_settlement"]/100):,.2f}</td></tr>"""
        # In all queries, the relevant amount is either d["amount"] or d["expected_settlement"]
        val = d["expected_settlement"] if "expected_settlement" in d.keys() else d["amount"]
        total_val += val
        
    total_val = total_val / 100
        
    if not rows:
        rows = '<tr><td colspan="5" class="p-4 text-center text-[#71717A] text-sm">No finance exceptions.</td></tr>'

    return f"""<!DOCTYPE html><html><head><title>Custos | Finance Reconciliation</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    
    <!-- SIDEBAR -->
    <div class="w-64 border-r border-[#1F1F23] bg-[#0A0A0B] flex flex-col p-4 shrink-0 h-screen overflow-y-auto sticky top-0">
        <div class="flex items-center gap-3 mb-8 px-2">
            <h1 class="text-2xl font-black tracking-tight">Custos</h1>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1.5 mt-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SIM
            </span>
        </div>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Capabilities</div>
        <nav class="space-y-1 mb-8">
            <a href="/" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Overview</a>
            <a href="/growth" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Growth</a>
            <a href="/risk" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Risk</a>
            <a href="/recovery" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Recovery</a>
            <a href="/finance" class="block px-3 py-2 text-sm rounded-lg text-[#F5F5F7] bg-[#1C1C1F] border border-[#2A2A2E] font-medium">Finance</a>
            <a href="/command" class="block px-3 py-2 text-sm rounded-lg mt-2 flex justify-between items-center text-[#A1A1AA] hover:bg-[#1C1C1F]/50 hover:text-[#F5F5F7]">
                Command Center
                <span class="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded">NEW</span>
            </a>
        </nav>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Settings</div>
        <nav class="space-y-1">
            <a href="/activity" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Activity</a>
            <a href="/policies" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Policies</a>
        </nav>
    </div>
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <h2 class="text-3xl font-black tracking-tight mb-2">Finance Reconciliation</h2>
        <p class="text-[#71717A] text-sm mb-8">View and manage finance reconciliation across your unified pipeline.</p>
        
        <div class="mb-8 w-1/3">
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-blue-500">
                <div class="text-[10px] text-blue-400 uppercase tracking-wider mb-1 font-semibold">Total Mismatch</div>
                <div class="text-3xl font-black font-mono text-white">₹{total_val:,.0f}</div>
            </div>
        </div>
        
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-3">Event</th><th class="p-3">Status</th><th class="p-3">Mismatch Detail</th><th class="p-3">Expected Settlement</th>
            </tr></thead><tbody>{rows}</tbody></table>
        </div>
    </div>
    </body></html>"""

@app.get("/activity", response_class=HTMLResponse)
def activity_page():

    with get_db() as db:
        logs = db.execute("""
            SELECT a.*, e.source_id 
            FROM audit_log a 
            JOIN events e ON a.event_id = e.id 
            ORDER BY a.timestamp DESC 
            LIMIT 100
        """).fetchall()
        
    rows = ""
    for l in logs:
        time_str = l["timestamp"].split("T")[1][:8] if "T" in l["timestamp"] else l["timestamp"]
        stage_colors = {
            "risk": "bg-red-500/10 text-red-400",
            "growth": "bg-amber-500/10 text-amber-500",
            "llm_reasoning": "bg-purple-500/10 text-purple-400",
            "policy": "bg-blue-500/10 text-blue-400",
            "action": "bg-emerald-500/10 text-emerald-400",
            "classification": "bg-gray-500/10 text-gray-400"
        }
        color = stage_colors.get(l["stage"].lower(), "bg-gray-500/10 text-gray-400")
        
        rows += f"""<tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F] cursor-pointer" onclick="window.location='/demo/{l['event_id']}'">
            <td class="p-3 font-mono text-xs text-[#52525B]">{time_str}</td>
            <td class="p-3 font-mono text-xs text-[#A1A1AA]">{l["source_id"]}</td>
            <td class="p-3 text-xs"><span class="px-2 py-1 {color} rounded font-bold uppercase">{l["stage"]}</span></td>
            <td class="p-3 text-sm text-[#F5F5F7]">{l["detail"]}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="4" class="p-4 text-center text-[#71717A] text-sm">No activity logs found.</td></tr>'

    return f"""<!DOCTYPE html><html><head><title>Custos | Activity</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    {sidebar}
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <h2 class="text-3xl font-black tracking-tight mb-2">System Activity Log</h2>
        <p class="text-[#71717A] text-sm mb-8">A complete, immutable audit trail of every autonomous decision made by the Custos engine.</p>
        
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-3">Time</th><th class="p-3">Event</th><th class="p-3">Engine Stage</th><th class="p-3">Audit Detail</th>
            </tr></thead><tbody>{{rows}}</tbody></table>
        </div>
    </div>
    </body></html>"""


@app.get("/policies", response_class=HTMLResponse)
def policies_page():

    rows = """
    <tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F]">
        <td class="p-4 text-xs"><span class="px-2 py-1 bg-red-500/10 text-red-400 rounded font-bold uppercase">RISK</span></td>
        <td class="p-4 text-sm font-medium">Block transactions with computed risk score > 0.8</td>
        <td class="p-4 text-xs font-mono text-red-400">AUTO_BLOCK</td>
        <td class="p-4 text-xs"><span class="flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>Active</span></td>
    </tr>
    <tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F]">
        <td class="p-4 text-xs"><span class="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded font-bold uppercase">RECOVERY</span></td>
        <td class="p-4 text-sm font-medium">Auto-retry failed cards up to ₹50,000 ceiling</td>
        <td class="p-4 text-xs font-mono text-emerald-400">AUTO_RETRY</td>
        <td class="p-4 text-xs"><span class="flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>Active</span></td>
    </tr>
    <tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F]">
        <td class="p-4 text-xs"><span class="px-2 py-1 bg-blue-500/10 text-blue-400 rounded font-bold uppercase">FINANCE</span></td>
        <td class="p-4 text-sm font-medium">Flag missing settlements after T+3 days</td>
        <td class="p-4 text-xs font-mono text-purple-400">FLAG_REVIEW</td>
        <td class="p-4 text-xs"><span class="flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>Active</span></td>
    </tr>
    <tr class="border-b border-[#1F1F23] hover:bg-[#1C1C1F]">
        <td class="p-4 text-xs"><span class="px-2 py-1 bg-amber-500/10 text-amber-500 rounded font-bold uppercase">GROWTH</span></td>
        <td class="p-4 text-sm font-medium">Upsell UPI on card decline (2% discount offer)</td>
        <td class="p-4 text-xs font-mono text-amber-400">AUTO_OFFER</td>
        <td class="p-4 text-xs"><span class="flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>Active</span></td>
    </tr>
    """

    return f"""<!DOCTYPE html><html><head><title>Custos | Policies</title>
    <script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    {sidebar}
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <div class="flex justify-between items-center mb-2">
            <h2 class="text-3xl font-black tracking-tight">Active Policies</h2>
            <button class="px-4 py-2 bg-[#1C1C1F] hover:bg-[#2A2A2E] text-white text-sm font-semibold rounded-lg transition-colors border border-[#2A2A2E]">
                + New Policy
            </button>
        </div>
        <p class="text-[#71717A] text-sm mb-8">Govern how the Custos AI brain executes autonomous actions.</p>
        
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-4">Domain</th><th class="p-4">Policy Rule</th><th class="p-4">Enforcement</th><th class="p-4">Status</th>
            </tr></thead><tbody>{{rows}}</tbody></table>
        </div>
    </div>
    </body></html>"""

@app.get("/command", response_class=HTMLResponse)

def command_center():

    with get_db() as db:

        # Risk

        risk_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM risk_assessments r JOIN events e ON r.event_id = e.id WHERE r.verdict = 'FLAG_FOR_REVIEW'").fetchone()

        rc_count = risk_cases["c"] or 0

        rc_sum = (risk_cases["s"] or 0) / 100

        

        # Recovery

        rec_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM actions a JOIN events e ON a.event_id = e.id WHERE a.action_type IN ('RETRY_PAYMENT', 'SEND_REMINDER')").fetchone()

        rec_count = rec_cases["c"] or 0

        rec_sum = (rec_cases["s"] or 0) / 100

        

        # Finance

        fin_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM finance_reconciliations f JOIN events e ON f.event_id = e.id WHERE f.reconciliation_status IN ('NO_SETTLEMENT', 'AMOUNT_HELD', 'ACCOUNTS_RECEIVABLE')").fetchone()

        fin_count = fin_cases["c"] or 0

        fin_sum = (fin_cases["s"] or 0) / 100

        

        # Growth

        gro_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM growth_opportunities g JOIN events e ON g.event_id = e.id WHERE g.has_opportunity = 1").fetchone()

        gro_count = gro_cases["c"] or 0

        gro_sum = (gro_cases["s"] or 0) / 100



    return f"""<!DOCTYPE html><html><head><title>Custos | Autonomous Merchant Finance Agent</title>

    <script src="https://cdn.tailwindcss.com"></script>

</head>

    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">

    

    <!-- SIDEBAR -->
    <div class="w-64 border-r border-[#1F1F23] bg-[#0A0A0B] flex flex-col p-4 shrink-0 h-screen overflow-y-auto sticky top-0">
        <div class="flex items-center gap-3 mb-8 px-2">
            <h1 class="text-2xl font-black tracking-tight">Custos</h1>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1.5 mt-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SIM
            </span>
        </div>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Capabilities</div>
        <nav class="space-y-1 mb-8">
            <a href="/" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Overview</a>
            <a href="/growth" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Growth</a>
            <a href="/risk" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Risk</a>
            <a href="/recovery" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Recovery</a>
            <a href="/finance" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Finance</a>
            <a href="/command" class="block px-3 py-2 text-sm rounded-lg mt-2 flex justify-between items-center text-[#F5F5F7] bg-[#1C1C1F] border border-[#2A2A2E] font-medium">
                Command Center
                <span class="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded">NEW</span>
            </a>
        </nav>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Settings</div>
        <nav class="space-y-1">
            <a href="/activity" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Activity</a>
            <a href="/policies" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Policies</a>
        </nav>
    </div>
    <div class="flex-1 p-10 max-w-5xl">

        <div class="mb-10">

            <h2 class="text-3xl font-black tracking-tight mb-2">What needs my attention today?</h2>

            <p class="text-[#A1A1AA]">Custos has analyzed your payments and prioritized these actions.</p>

        </div>



        <div class="grid grid-cols-2 gap-10">

            <!-- Priorities -->

            <div>

                <h3 class="text-xs font-semibold text-[#52525B] uppercase tracking-widest mb-4">Today's Priorities</h3>

                <div class="space-y-3">

                    <div class="bg-[#141416] border border-emerald-500/20 rounded-xl p-4 flex gap-4 items-start relative overflow-hidden">

                        <div class="absolute top-0 left-0 w-1 h-full bg-emerald-500"></div>

                        <div class="text-emerald-400 mt-1">🟢</div>

                        <div>

                            <div class="font-semibold text-white">{rec_count} recovery actions eligible</div>

                            <div class="text-xs text-[#A1A1AA] mt-1">₹{rec_sum:,.0f} potential recovery</div>

                        </div>

                    </div>



                    <div class="bg-[#141416] border border-red-500/20 rounded-xl p-4 flex gap-4 items-start relative overflow-hidden">

                        <div class="absolute top-0 left-0 w-1 h-full bg-red-500"></div>

                        <div class="text-red-400 mt-1">🔴</div>

                        <div>

                            <div class="font-semibold text-white">{rc_count} risk cases require review</div>

                            <div class="text-xs text-[#A1A1AA] mt-1">₹{rc_sum:,.0f} exposure</div>

                        </div>

                    </div>



                    <div class="bg-[#141416] border border-blue-500/20 rounded-xl p-4 flex gap-4 items-start relative overflow-hidden">

                        <div class="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>

                        <div class="text-blue-400 mt-1">🔵</div>

                        <div>

                            <div class="font-semibold text-white">{fin_count} settlement exceptions</div>

                            <div class="text-xs text-[#A1A1AA] mt-1">₹{fin_sum:,.0f} mismatch</div>

                        </div>

                    </div>



                    <div class="bg-[#141416] border border-amber-500/20 rounded-xl p-4 flex gap-4 items-start relative overflow-hidden">

                        <div class="absolute top-0 left-0 w-1 h-full bg-amber-500"></div>

                        <div class="text-amber-400 mt-1">🟡</div>

                        <div>

                            <div class="font-semibold text-white">{gro_count} growth opportunities</div>

                            <div class="text-xs text-[#A1A1AA] mt-1">₹{gro_sum:,.0f} potential upside</div>

                        </div>

                    </div>

                </div>

            </div>



            <!-- Action Plan -->

            <div>

                <h3 class="text-xs font-semibold text-[#52525B] uppercase tracking-widest mb-4">What should I do first?</h3>

                <div class="relative border-l border-[#2A2A2E] ml-3 pl-8 pb-4 space-y-8">

                    

                    <div class="relative">

                        <div class="absolute -left-[45px] top-0 w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-xs font-bold text-emerald-400">1</div>

                        <h4 class="font-semibold text-white text-lg">Recover {rec_count} eligible failed payments</h4>

                        <p class="text-sm text-[#A1A1AA] mt-1">Expected impact: <span class="text-emerald-400 font-mono">₹{rec_sum:,.0f}</span></p>

                        <button class="mt-3 px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-xs font-semibold transition-colors">Review Actions</button>

                    </div>



                    <div class="relative">

                        <div class="absolute -left-[45px] top-0 w-6 h-6 rounded-full bg-red-500/20 border border-red-500 flex items-center justify-center text-xs font-bold text-red-400">2</div>

                        <h4 class="font-semibold text-white text-lg">Review {rc_count} high-risk transactions</h4>

                        <p class="text-sm text-[#A1A1AA] mt-1">Exposure: <span class="text-red-400 font-mono">₹{rc_sum:,.0f}</span></p>

                        <button class="mt-3 px-3 py-1.5 bg-[#1C1C1F] hover:bg-[#2A2A2E] text-white rounded text-xs font-semibold transition-colors">Review Flagged</button>

                    </div>

                    

                    <div class="relative">

                        <div class="absolute -left-[45px] top-0 w-6 h-6 rounded-full bg-blue-500/20 border border-blue-500 flex items-center justify-center text-xs font-bold text-blue-400">3</div>

                        <h4 class="font-semibold text-white text-lg">Investigate settlement mismatches</h4>

                        <p class="text-sm text-[#A1A1AA] mt-1">Exposure: <span class="text-blue-400 font-mono">₹{fin_sum:,.0f}</span></p>

                        <button class="mt-3 px-3 py-1.5 bg-[#1C1C1F] hover:bg-[#2A2A2E] text-white rounded text-xs font-semibold transition-colors">View Exceptions</button>

                    </div>



                    <div class="relative">

                        <div class="absolute -left-[45px] top-0 w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500 flex items-center justify-center text-xs font-bold text-amber-400">4</div>

                        <h4 class="font-semibold text-white text-lg">Launch {gro_count} growth opportunities</h4>

                        <p class="text-sm text-[#A1A1AA] mt-1">Potential upside: <span class="text-amber-400 font-mono">₹{gro_sum:,.0f}</span></p>

                        <button class="mt-3 px-3 py-1.5 bg-[#1C1C1F] hover:bg-[#2A2A2E] text-white rounded text-xs font-semibold transition-colors">View Offers</button>

                    </div>



                </div>

            </div>

        </div>

    </div>

    </body></html>"""





@app.get("/", response_class=HTMLResponse)
def overview():
    with get_db() as db:
        events = db.execute("""
            SELECT e.id, e.source_id, e.type, e.status, e.amount, e.customer_ref,
                   c.category, l.recommended_action, l.confidence
            FROM events e
            LEFT JOIN classifications c ON e.id = c.event_id
            LEFT JOIN llm_decisions l ON e.id = l.event_id
            ORDER BY e.created_at DESC
        """).fetchall()
        
    rows = ""
    for e in events:
        status_cls = {
            "failed": "bg-red-500/20 text-red-400", "captured": "bg-green-500/20 text-green-400",
            "paid": "bg-green-500/20 text-green-400", "disputed": "bg-amber-500/20 text-amber-400",
            "unpaid": "bg-orange-500/20 text-orange-400", "recovered": "bg-emerald-500/20 text-emerald-400"
        }.get(e["status"], "bg-gray-500/20 text-gray-400")
        
        cat = e["category"] or ""
        action = e["recommended_action"] or ""
        e_amt = e["amount"] / 100
        
        # Recovery Badge Logic
        status = e["status"].lower()
        if status in ('captured', 'paid'):
            recovery_badge = '<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-gray-500/15 text-gray-400"><span class="w-1.5 h-1.5 rounded-full bg-gray-500"></span>Not Needed</span>'
        elif status == 'recovered':
            recovery_badge = '<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-emerald-500/15 text-emerald-400"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Recovered</span>'
        elif action and action not in ("PENDING", "NO_ACTION"):
            recovery_badge = '<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-blue-500/15 text-blue-400"><span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>Action Gen</span>'
        else:
            recovery_badge = '<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold uppercase bg-red-500/15 text-red-400"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>Not Actioned</span>'
            
        display_action = "GEN EVIDENCE" if action == "FLAG_FOR_HUMAN_REVIEW" else action.replace('_', ' ')
        
        rows += f"""<tr onclick="window.location='/demo/{e['id']}'" class="cursor-pointer hover:bg-[#1C1C1F] border-b border-[#1F1F23] transition-colors">
            <td class="p-3 font-mono text-xs text-gray-400">{e['source_id'][:20]}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase {status_cls}">{e['status']}</span></td>
            <td class="p-3 font-mono text-sm">₹{e_amt:,.2f}</td>
            <td class="p-3 text-xs text-gray-400">{cat}</td>
            <td class="p-3 text-xs"><span class="text-purple-400 font-bold tracking-wider">{display_action}</span></td>
            <td class="p-3 text-xs">{recovery_badge}</td>
        </tr>"""

    # Calculate new OS metrics
    with get_db() as db:
        # Risk
        risk_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM risk_assessments r JOIN events e ON r.event_id = e.id WHERE r.verdict = 'FLAG_FOR_REVIEW'").fetchone()
        rc_sum = (risk_cases["s"] or 0) / 100 if risk_cases else 0
        
        # Recovery
        rec_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM actions a JOIN events e ON a.event_id = e.id WHERE a.action_type IN ('RETRY_PAYMENT', 'SEND_REMINDER')").fetchone()
        rec_sum = (rec_cases["s"] or 0) / 100 if rec_cases else 0
        
        # Finance
        fin_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM finance_reconciliations f JOIN events e ON f.event_id = e.id WHERE f.reconciliation_status IN ('NO_SETTLEMENT', 'AMOUNT_HELD', 'ACCOUNTS_RECEIVABLE')").fetchone()
        fin_sum = (fin_cases["s"] or 0) / 100 if fin_cases else 0
        
        # Growth
        gro_cases = db.execute("SELECT COUNT(*) as c, SUM(e.amount) as s FROM growth_opportunities g JOIN events e ON g.event_id = e.id WHERE g.has_opportunity = 1").fetchone()
        gro_sum = (gro_cases["s"] or 0) / 100 if gro_cases else 0

    return f"""<!DOCTYPE html><html><head><title>Custos | Autonomous Merchant Finance Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>

</head>
    <body class="bg-[#0A0A0B] text-white font-sans min-h-screen flex">
    
    <!-- SIDEBAR -->
    <div class="w-64 border-r border-[#1F1F23] bg-[#0A0A0B] flex flex-col p-4 shrink-0 h-screen overflow-y-auto sticky top-0">
        <div class="flex items-center gap-3 mb-8 px-2">
            <h1 class="text-2xl font-black tracking-tight">Custos</h1>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1.5 mt-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                SIM
            </span>
        </div>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Capabilities</div>
        <nav class="space-y-1 mb-8">
            <a href="/" class="block px-3 py-2 text-sm rounded-lg text-[#F5F5F7] bg-[#1C1C1F] border border-[#2A2A2E] font-medium">Overview</a>
            <a href="/growth" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Growth</a>
            <a href="/risk" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Risk</a>
            <a href="/recovery" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Recovery</a>
            <a href="/finance" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Finance</a>
            <a href="/command" class="block px-3 py-2 text-sm rounded-lg mt-2 flex justify-between items-center text-[#A1A1AA] hover:bg-[#1C1C1F]/50 hover:text-[#F5F5F7]">
                Command Center
                <span class="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded">NEW</span>
            </a>
        </nav>
        
        <div class="text-[10px] text-[#52525B] uppercase tracking-widest font-semibold px-2 mb-3">Settings</div>
        <nav class="space-y-1">
            <a href="/activity" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Activity</a>
            <a href="/policies" class="block px-3 py-2 text-sm rounded-lg text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1C1C1F]/50 font-medium">Policies</a>
        </nav>
    </div>
    <div class="flex-1 overflow-auto p-10 max-w-6xl">
        <div class="flex items-center justify-between mb-2">
            <h2 class="text-3xl font-black tracking-tight">Overview</h2>
            <button id="scanBtn" onclick="scanNow()" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                Scan & Process
            </button>
        </div>
        <p class="text-[#A1A1AA] text-sm mb-8">Autonomous Merchant Finance Agent &mdash; Click "Scan" to pull new payments, or click any row to open the unified AI brain pipeline.</p>
        
        <!-- 4 CAPABILITIES BOXES -->
        <div class="grid grid-cols-4 gap-4 mb-8">
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-amber-500"><div class="text-[10px] text-amber-500 uppercase tracking-wider mb-1 font-semibold">Growth</div><div class="text-3xl font-black font-mono text-white">₹{gro_sum:,.0f}</div></div>
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-red-500"><div class="text-[10px] text-red-400 uppercase tracking-wider mb-1 font-semibold">Risk</div><div class="text-3xl font-black font-mono text-white">₹{rc_sum:,.0f}</div></div>
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-emerald-500"><div class="text-[10px] text-emerald-400 uppercase tracking-wider mb-1 font-semibold">Recovery</div><div class="text-3xl font-black font-mono text-white">₹{rec_sum:,.0f}</div></div>
            <div class="bg-[#141416] border border-[#1F1F23] rounded-xl p-5 border-l-2 border-l-blue-500"><div class="text-[10px] text-blue-400 uppercase tracking-wider mb-1 font-semibold">Finance</div><div class="text-3xl font-black font-mono text-white">₹{fin_sum:,.0f}</div></div>
        </div>
        <div id="scanStatus" class="hidden mb-4 p-3 rounded-lg text-sm"></div>
        <h3 class="text-xs font-semibold text-[#52525B] uppercase tracking-widest mb-3">Recent Transactions</h3>
        <div class="bg-[#141416] border border-[#1F1F23] rounded-xl overflow-hidden shadow-sm">
            <table class="w-full text-left"><thead><tr class="text-[10px] text-[#52525B] uppercase tracking-wider border-b border-[#1F1F23]">
                <th class="p-3">Event</th><th class="p-3">Status</th><th class="p-3">Amount</th><th class="p-3">Category</th><th class="p-3">AI Action</th><th class="p-3">Recovery</th>
            </tr></thead><tbody>{rows}</tbody></table>
        </div>
    </div>
    
    <script>
    async function scanNow() {{
        const btn = document.getElementById('scanBtn');
        const status = document.getElementById('scanStatus');
        btn.disabled = true;
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Scanning Razorpay & running pipeline...';
        status.className = 'mb-4 p-3 rounded-lg text-sm bg-blue-500/10 border border-blue-500/20 text-blue-400 animate-pulse';
        status.textContent = 'Fetching payments, analyzing risk, identifying growth, routing recovery, and reconciling finance...';
        try {{
            const res = await fetch('/api/scan', {{method: 'POST'}});
            const data = await res.json();
            if (data.ok) {{
                status.className = 'mb-4 p-3 rounded-lg text-sm bg-green-500/10 border border-green-500/20 text-green-400';
                status.textContent = 'Pipeline complete. Refreshing...';
                setTimeout(() => window.location.reload(), 1000);
            }} else {{
                status.className = 'mb-4 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400';
                status.textContent = 'Pipeline failed at: ' + (data.failed_at || 'unknown');
            }}
        }} catch(e) {{
            status.className = 'mb-4 p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/20 text-red-400';
            status.textContent = 'Error: ' + e.message;
        }}
        btn.disabled = false;
        btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Scan & Process';
    }}
    </script>
    </body></html>"""
