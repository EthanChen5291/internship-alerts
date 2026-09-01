"""Private, browser-local resume tailoring page."""

from __future__ import annotations

import json
import os

from . import paths

_EXAMPLE = {
    "name": "Jordan Student",
    "contact": {
        "email": "jordan@example.com",
        "phone": "(312) 555-0100",
        "location": "Chicago, IL",
        "linkedin": "linkedin.com/in/jordan-student",
        "github": "github.com/jordan-student",
    },
    "summary": "Computer science student focused on reliable software and data systems.",
    "education": [{
        "school": "Example University",
        "degree": "B.S. Computer Science",
        "start": "Aug 2024",
        "end": "May 2028",
        "details": ["Relevant coursework: Data Structures, Algorithms, Databases"],
    }],
    "skills": [
        {"category": "Languages", "items": ["Python", "Java", "JavaScript", "SQL"]},
        {"category": "Tools", "items": ["Git", "Docker", "React", "PostgreSQL"]},
    ],
    "experience": [{
        "company": "Example Lab",
        "role": "Software Assistant",
        "start": "Jan 2026",
        "end": "Present",
        "bullets": [
            "Built Python data validation scripts for research datasets.",
            "Collaborated with three researchers using Git and code review.",
        ],
    }],
    "projects": [{
        "name": "Campus Events App",
        "technologies": ["React", "Python", "PostgreSQL"],
        "bullets": [
            "Created a React interface for searching campus events.",
            "Designed a Python API backed by PostgreSQL.",
        ],
    }],
}

_PAGE = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Private resume tailor</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--accent:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}
.toolbar{max-width:920px;margin:24px auto;padding:20px;background:var(--panel);border:1px solid var(--border);border-radius:12px}
h1{margin:0 0 6px;font-size:22px}.muted{color:var(--muted)}button,.file{display:inline-block;margin:8px 8px 0 0;padding:9px 13px;border:1px solid var(--border);border-radius:7px;background:#21262d;color:var(--text);cursor:pointer}
button.primary{background:#238636;border-color:#2ea043}input[type=file]{max-width:100%}.status{margin-top:10px}.match{color:#3fb950}
.paper{width:8.5in;min-height:11in;margin:18px auto 40px;padding:.42in .55in;background:white;color:#111;box-shadow:0 8px 35px #0008;font:9.5pt/1.25 Arial,sans-serif}
.paper h2{text-align:center;font-size:18pt;line-height:1.05;margin:0 0 3px}.contact{text-align:center;font-size:8.5pt;margin-bottom:7px}.section{font-size:10.5pt;font-weight:bold;color:#17365d;border-bottom:1px solid #17365d;margin:7px 0 3px;padding-bottom:1px}.entry{margin:2px 0 4px}.entry-head{display:flex;justify-content:space-between;gap:12px;font-weight:bold}.dates{white-space:nowrap;font-weight:normal}.sub{font-size:8.5pt}.paper ul{margin:2px 0 2px 17px;padding:0}.paper li{margin:0 0 1px}.skill{margin:1px 0}.setup{padding:28px;text-align:center;color:#555}.target{font-size:12px;margin-top:6px}
@media(max-width:900px){.paper{width:calc(100% - 20px);min-height:0;padding:24px}.toolbar{margin:10px}}
@media print{@page{size:letter;margin:0}.toolbar{display:none}.paper{margin:0;box-shadow:none;width:8.5in;min-height:11in}.target{display:none}body{background:white}}
</style></head><body>
<div class="toolbar">
  <h1>Private resume tailor</h1>
  <div class="muted">Nothing is uploaded. The tool only reorders your existing bullets and skills for the selected role; it never rewrites or invents claims.</div>
  <label class="file">Load base resume JSON <input id="file" type="file" accept="application/json,.json"></label>
  <button id="remember">Remember on this browser</button>
  <button id="clear">Clear saved resume</button>
  <button id="print" class="primary" disabled>Save as PDF</button>
  <a class="file" href="resume.example.json" download>Download template</a>
  <div id="status" class="status muted">Loading job...</div>
</div>
<main id="paper" class="paper"><div class="setup">Choose your resume JSON above. The selected role will be applied automatically.</div></main>
<script>
(function(){
  'use strict';
  var KEY='ie.resume.v1', job=null, resume=null;
  var paper=document.getElementById('paper'), status=document.getElementById('status'), print=document.getElementById('print');
  function node(tag, cls, text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e}
  function safeUrl(value){try{var u=new URL(value.indexOf('://')<0?'https://'+value:value);return /^https?:$/.test(u.protocol)?u.href:''}catch(e){return ''}}
  function words(value){return String(value||'').toLowerCase().match(/[a-z0-9+#.]{2,}/g)||[]}
  function termsFor(j){
    var generic={and:1,the:1,for:1,with:1,intern:1,internship:1,engineering:1,engineer:1,software:1,summer:1,fall:1,role:1,technology:1};
    var raw=(j.skills||[]).concat(words((j.title||'')+' '+(j.category||''))), seen={}, out=[];
    raw.forEach(function(v){var key=String(v).toLowerCase();if(!seen[key]&&!generic[key]){seen[key]=1;out.push(String(v))}});return out;
  }
  function score(value,terms){var text=String(value||'').toLowerCase(),n=0;terms.forEach(function(t){if(text.indexOf(t.toLowerCase())!==-1)n+=3});return n}
  function ordered(values,fn){return (values||[]).map(function(v,i){return{v:v,i:i,s:fn(v)}}).sort(function(a,b){return b.s-a.s||a.i-b.i}).map(function(x){return x.v})}
  function tailored(base,j){
    var out=JSON.parse(JSON.stringify(base)), terms=termsFor(j);
    out.skills=ordered(out.skills||[],function(g){return(g.items||[]).reduce(function(n,v){return n+score(v,terms)},0)});
    out.skills.forEach(function(g){g.items=ordered(g.items||[],function(v){return score(v,terms)})});
    ['experience','projects'].forEach(function(section){
      (out[section]||[]).forEach(function(item){item.bullets=ordered(item.bullets||[],function(v){return score(v,terms)})});
      out[section]=ordered(out[section]||[],function(item){return(item.bullets||[]).reduce(function(n,v){return n+score(v,terms)},0)});
    });
    return{resume:out,terms:terms};
  }
  function section(title){paper.appendChild(node('div','section',title))}
  function bullets(values,parent){if(!values||!values.length)return;var ul=node('ul');values.forEach(function(v){ul.appendChild(node('li','',v))});parent.appendChild(ul)}
  function render(){
    if(!job||!resume)return;
    var result=tailored(resume,job), r=result.resume;paper.replaceChildren();
    paper.appendChild(node('h2','',r.name||'Your Name'));
    var c=r.contact||{}, contact=['email','phone','location','linkedin','github','website'].map(function(k){return c[k]}).filter(Boolean).join(' | ');
    paper.appendChild(node('div','contact',contact));
    paper.appendChild(node('div','target','Prepared for '+(job.company||'')+' - '+(job.title||'')));
    if(r.summary){section('SUMMARY');paper.appendChild(node('div','',r.summary))}
    if((r.education||[]).length){section('EDUCATION');r.education.forEach(function(x){var e=node('div','entry'),h=node('div','entry-head');h.appendChild(node('span','',(x.school||'')+(x.degree?' - '+x.degree:'')));h.appendChild(node('span','dates',[x.start,x.end].filter(Boolean).join(' - ')));e.appendChild(h);bullets(x.details,e);paper.appendChild(e)})}
    if((r.skills||[]).length){section('SKILLS');r.skills.forEach(function(g){var line=node('div','skill'),b=node('b','',(g.category||'Skills')+': ');line.appendChild(b);line.appendChild(document.createTextNode((g.items||[]).join(', ')));paper.appendChild(line)})}
    function entries(title,key){if(!(r[key]||[]).length)return;section(title);r[key].forEach(function(x){var e=node('div','entry'),h=node('div','entry-head'),label=x.role||x.name||'',org=x.company||'';h.appendChild(node('span','',label+(org?' - '+org:'')));h.appendChild(node('span','dates',[x.start,x.end].filter(Boolean).join(' - ')));e.appendChild(h);if((x.technologies||[]).length)e.appendChild(node('div','sub',x.technologies.join(', ')));bullets(x.bullets,e);paper.appendChild(e)})}
    entries('EXPERIENCE','experience');entries('PROJECTS','projects');
    var matched=result.terms.filter(function(t){return score(JSON.stringify(r),[t])>0});
    status.replaceChildren(document.createTextNode(job.company+' - '+job.title+' | '));var m=node('span','match',matched.length?'Matched existing keywords: '+matched.join(', '):'No exact keyword matches; original order preserved.');status.appendChild(m);print.disabled=false;
  }
  function accept(value){if(!value||typeof value!=='object'||!value.name)throw new Error('Resume JSON needs at least a name field.');resume=value;render()}
  document.getElementById('file').addEventListener('change',function(ev){var f=ev.target.files&&ev.target.files[0];if(!f)return;f.text().then(function(text){accept(JSON.parse(text));status.textContent='Resume loaded locally.'}).catch(function(e){status.textContent='Could not read resume: '+e.message})});
  document.getElementById('remember').addEventListener('click',function(){if(!resume){status.textContent='Load a resume first.';return}localStorage.setItem(KEY,JSON.stringify(resume));status.textContent='Saved only in this browser.'});
  document.getElementById('clear').addEventListener('click',function(){localStorage.removeItem(KEY);resume=null;print.disabled=true;paper.innerHTML='<div class="setup">Saved resume cleared. Load a JSON file to continue.</div>';status.textContent='Saved resume cleared.'});
  print.addEventListener('click',function(){window.print()});
  try{var saved=JSON.parse(localStorage.getItem(KEY)||'null');if(saved)resume=saved}catch(e){localStorage.removeItem(KEY)}
  var id=new URLSearchParams(location.search).get('job');
  fetch('api/jobs.json').then(function(r){if(!r.ok)throw new Error('jobs API unavailable');return r.json()}).then(function(data){job=(data.jobs||[]).find(function(x){return x.id===id});if(!job)throw new Error('Role not found or no longer open.');status.textContent=job.company+' - '+job.title;if(resume)render()}).catch(function(e){status.textContent=e.message});
})();
</script></body></html>'''


def write() -> None:
    os.makedirs(paths.DOCS_DIR, exist_ok=True)
    with open(os.path.join(paths.DOCS_DIR, "resume.html"), "w", encoding="utf-8") as stream:
        stream.write(_PAGE)
    with open(os.path.join(paths.DOCS_DIR, "resume.example.json"), "w", encoding="utf-8") as stream:
        json.dump(_EXAMPLE, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
