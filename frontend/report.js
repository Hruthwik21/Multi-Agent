fetch(location.pathname.replace('/report/','/api/sessions/')).then(r=>r.json()).then(j=>{
  const c=(j.result&&j.result.comment)||JSON.stringify(j).slice(0,4000);
  document.getElementById('report').innerHTML='<pre>'+c.replace(/[<>&]/g,m=>({'<':'&lt;','>':'&gt;','&':'&amp;'}[m]))+'</pre>';
}).catch(e=>{document.getElementById('report').textContent='Failed to load: '+e;});
