// Client-side list filtering on browse pages and the "/" shortcut for search. No network access.
document.querySelectorAll('input[data-filter]').forEach(input=>{
  const target=document.getElementById(input.dataset.filter),counter=document.getElementById(input.dataset.filter+'-count');
  if(!target)return;
  input.addEventListener('input',()=>{
    const tokens=input.value.toLowerCase().split(/\s+/).filter(Boolean);let shown=0;
    target.querySelectorAll('li.item').forEach(li=>{const hit=tokens.every(t=>li.textContent.toLowerCase().includes(t));li.hidden=!hit;if(hit)shown++;});
    target.querySelectorAll('[data-filter-group]').forEach(group=>{const any=!!group.querySelector('li.item:not([hidden])');group.hidden=!any;if(tokens.length&&group.tagName==='DETAILS')group.open=any;});
    if(counter)counter.textContent=tokens.length?shown+' shown':'';
  });
});
document.addEventListener('keydown',event=>{
  if(event.key!=='/'||/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName))return;
  const box=document.getElementById('q')||document.querySelector('.header-search input');
  if(box){event.preventDefault();box.focus();}
});
