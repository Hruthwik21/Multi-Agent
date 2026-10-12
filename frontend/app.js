/* SSE client: POST /api/review -> stream events -> render claims + diff */
const $ = (id) => document.getElementById(id);
let allClaims = [];

function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function setPill(t){$('statusPill').textContent=t;}

function renderClaims(){
  const onlyV = $('onlyVerified').checked;
  const box = $('claims'); box.innerHTML='';
  const list = allClaims.filter(c=>!onlyV || c.verification_status==='verified');
  if(!list.length){box.innerHTML='<p style="color:#9aa4c7">No findings yet.</p>';return;}
  const order={critical:0,high:1,medium:2,low:3,nit:4};
  list.sort((a,b)=>(order[a.severity]??9)-(order[b.severity]??9));
  for(const c of list){
    const d=document.createElement('div');
    d.className='claim '+c.verification_status;
    d.innerHTML=`<div><span class="sev">${esc(c.severity)}</span> <b>${esc(c.file)}${c.line?':'+c.line:''}</b>
      <span class="badge">${c.verification_status==='verified'?'✅ Verified':'⚠️ '+(c.verification_status||'pending')}</span></div>
      <div>${esc(c.issue)}</div><div style="color:#9aa4c7;font-size:.85em">${esc(c.evidence||'')}</div>`;
    d.onclick=()=>{const el=$('diffView');el.scrollIntoView({behavior:'smooth'});};
    box.appendChild(d);
  }
}
$('onlyVerified').onchange=renderClaims;
$('copyBtn').onclick=()=>{navigator.clipboard.writeText($('comment').textContent||'');};

$('reviewForm').onsubmit=async(e)=>{
  e.preventDefault();
  allClaims=[];renderClaims();$('comment').textContent='';$('progress').textContent='starting…';setPill('running');
  const pr_url=$('prUrl').value.trim()||'https://github.com/local/local/pull/0';
  const diff=$('diffInput').value.trim()||null;
  if(diff){$('diffView').textContent=diff.slice(0,20000);}
  const r=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({pr_url,diff,post_to_github:$('postGh').checked})});
  const {session_id,stream_url}=await r.json();
  const es=new EventSource(stream_url);
  es.onmessage=()=>{};
  es.addEventListener('session_started',ev=>{$('progress').textContent='session '+JSON.parse(ev.data).session_id;});
  es.addEventListener('ingestion_done',ev=>{const d=JSON.parse(ev.data);$('progress').textContent=`ingested ${d.files_changed} files`;});
  es.addEventListener('agent_started',ev=>{setPill('agent:'+JSON.parse(ev.data).agent);});
  es.addEventListener('agent_claim',ev=>{const d=JSON.parse(ev.data);allClaims.push(d.claim);renderClaims();});
  es.addEventListener('claim_verified',()=>{});
  es.addEventListener('synthesis_done',ev=>{const d=JSON.parse(ev.data);$('comment').textContent=d.final_comment||'';
    $('costPill').textContent='$'+(d.cost_usd||0);$('latPill').textContent=(d.latency_ms||0)+'ms';});
  es.addEventListener('done',ev=>{const d=JSON.parse(ev.data);if(d.claims){allClaims=d.claims;renderClaims();}
    if(d.comment)$('comment').textContent=d.comment;setPill('done');$('progress').textContent='done · report: '+d.report_url;es.close();});
  es.addEventListener('error',ev=>{$('progress').textContent='error: '+ev.data;setPill('failed');es.close();});
  es.onerror=()=>{/* keep open; backend closes on done */};
};
