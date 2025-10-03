const $ = (s)=>document.querySelector(s);

async function ask(){
  const q = $('#q').value.trim();
  if(!q){ $('#answer').textContent = '请先输入问题'; return; }
  $('#btn').disabled = true; $('#btn').textContent = '查询中…';
  try{
    const res = await fetch('/qa',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({question:q})
    });
    const data = await res.json();
    $('#answer').textContent = data.answer ?? JSON.stringify(data, null, 2);
    $('#intent').textContent = data.intent ?? '';
    $('#payload').textContent = JSON.stringify(data.payload ?? {}, null, 2);
    $('#cypher').textContent = data.cypher ?? '';
    $('#params').textContent = JSON.stringify(data.params ?? {}, null, 2);
    $('#rows').textContent = JSON.stringify(data.rows ?? [], null, 2);
  }catch(err){
    $('#answer').textContent = '请求失败：' + err;
  }finally{
    $('#btn').disabled = false; $('#btn').textContent = '提问';
  }
}

$('#btn').addEventListener('click', ask);
$('#q').addEventListener('keydown', e=>{ if(e.key==='Enter') ask(); });

document.querySelectorAll('.hint').forEach(el=>{
  el.addEventListener('click', ()=>{ $('#q').value = el.dataset.q; ask(); });
});
