'use strict';
const $=id=>document.getElementById(id), audio=$('audio');
let score=null, lastIndex=-99, loadId=0, blobURL=null, selectedFiles=[], playable=false;
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const bars=Array.from({length:48},()=>{const b=document.createElement('i');$('spectrum').append(b);return b;});
const fmt=t=>`${String(Math.floor((t||0)/60)).padStart(2,'0')}:${String(Math.floor((t||0)%60)).padStart(2,'0')}`;
const num=(v,d=3)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(d):'—';
function status(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
function trail(index){
  $('trail').replaceChildren();
  const start=Math.max(0,Math.min(index-2,score.timeline.length-5));
  score.timeline.slice(start,start+5).forEach((e,j)=>{
    const i=start+j,b=document.createElement('button'); b.classList.toggle('current',i===index);
    if(i===index)b.setAttribute('aria-current','true');
    const label=document.createElement('small');label.textContent=i===index?'NOW':i<index?'PREVIOUS':'UP NEXT';
    const title=document.createElement('strong');title.textContent=e.label;
    const time=document.createElement('time');time.textContent=fmt(e.at_s);
    b.append(label,title,time);b.disabled=!playable;b.onclick=()=>{audio.currentTime=e.at_s;draw(true);};$('trail').append(b);
  });
}
function draw(force=false){
  if(!score)return;
  const time=audio.currentTime||0,s=MusicusTimeline.stateAt(score,time),e=s.event,d=s.data;
  $('position').textContent=fmt(time);$('seek').value=time;
  if(force||lastIndex!==s.index){
    lastIndex=s.index;
    $('event-label').textContent=e?e.label:'Prelude';
    $('event-type').textContent=e?(e.kind==='measurement'?'MEASUREMENT CASE':e.kind?.replaceAll('_',' ').toUpperCase()||'PROTOCOL'):'THE MUSIC COMES FIRST';
    $('stage').classList.toggle('reset',!!e&&['soft_reset','hard_reset'].includes(e.kind));
    $('stage').classList.toggle('hard',e?.kind==='hard_reset');
    $('stage').classList.toggle('measurement',e?.kind==='measurement');
    $('stage').classList.toggle('fault',Array.isArray(e?.data?.statuses)&&e.data.statuses.some(s=>s.startsWith('failed')));
    const packet=e&&e.kind!=='measurement'&&e.sop==='SOP'&&!String(e.status).startsWith('VBUS');
    $('direction').textContent=packet?(e.role==='SRC'?'→':e.role==='SNK'?'←':'···'):'···';
    $('source').classList.toggle('active',packet&&e.role==='SRC');$('sink').classList.toggle('active',packet&&e.role==='SNK');
    const request=d?.voltage_V??d?.target_voltage_V;
    $('event-detail').textContent=e?.kind==='measurement'?`${e.data?.statuses?.join(' · ')||'Measurement'} · ${num(request,1)} V target`:
      e?`${e.sop||''} ${e.sop!=='SOP'?'Cable / alternate SOP':e.role==='SRC'?'Source → Sink':e.role==='SNK'?'Sink → Source':''}${request!==undefined?` · Request ${num(request,1)} V / ${num(d?.current_A,2)} A`:''}`:'Press play to follow the exchange.';
    $('provenance').textContent=e?.timing==='interpolated_between_arranged_events'?'Reset position interpolated in musical time.':e?'Aligned to the arrangement, not wire timing.':'Accompaniment before the first event.';
    $('source-ref').textContent=e?.source_row?`PD ROW ${e.source_row}`:e?.source_lines?`ASD ROWS ${e.source_lines.join(', ')}`:'PRELUDE';
    $('watts').textContent=num(s.power,1);$('voltage').textContent=`${num(d?.actual_voltage_V)} V`;$('current').textContent=`${num(d?.actual_current_A)} A`;
    $('power-fill').style.width=`${s.intensity*100}%`;
    $('mood').textContent=s.power===null?'NO MEASUREMENT':s.power>200?'FULL POWER':s.power>100?'BUILDING ENERGY':s.power>30?'IN MOTION':'GENTLE';
    $('measurement-caption').textContent=s.power===null?'No measured power is attached to this event.':`Measurement for this arranged point${d?.asd_line?` · ASD row ${d.asd_line}`:''}.`;
    document.documentElement.style.setProperty('--accent',s.power>180?'#ffac85':'#b6a1ff');
    trail(s.index);
  }
  const age=e?time-e.at_s:99,active=!audio.paused&&!audio.ended;
  $('packet').style.opacity=active&&age<.5&&e?.kind==='protocol'&&e?.sop==='SOP'&&!String(e?.status).startsWith('VBUS')&&!reduced.matches?'1':'0';
  $('packet').style.left=`${e?.role==='SRC'?Math.min(100,age*200):Math.max(0,100-age*200)}%`;
  bars.forEach((b,i)=>{b.style.height=`${active&&!reduced.matches?5+(10+25*s.intensity)*Math.abs(Math.sin(time*(4+s.intensity*6)+i*.65))*Math.sin((i+1)/49*Math.PI):5}px`;b.style.opacity=active?'.65':'.25';});
}
function stopForLoad(){audio.pause();playable=false;$('play').disabled=true;$('seek').disabled=true;score=null;lastIndex=-99;if(blobURL){URL.revokeObjectURL(blobURL);blobURL=null;}audio.removeAttribute('src');audio.load();}
async function loadSample(name){
  const id=++loadId;stopForLoad();status('Loading recording…');
  document.querySelectorAll('.sample').forEach(b=>b.classList.toggle('selected',b.dataset.sample===name));
  try{const response=await fetch(`/samples/${name}.json`);if(!response.ok)throw Error('Start the local player with python pd_musicus.py --player to use samples.');const plan=MusicusTimeline.validate(await response.json());if(id!==loadId)return;activate(plan,`/examples/${name}.wav`,name==='avs_5a'?'Delta AVS · 5 A':'Delta AVS · 0.5 A');}
  catch(e){if(id===loadId)status(e.message,true);}
}
function activate(plan,url,title){score=plan;lastIndex=-99;$('mode').textContent=`${plan.mode||'RECORDING'} / ${plan.bpm||'—'} BPM`;$('event-count').textContent=`${plan.timeline.length} EVENTS`;$('track').textContent=title;$('duration').textContent=fmt(plan.duration_s);audio.src=url;audio.load();draw(true);}
$('files').addEventListener('change',async event=>{
  selectedFiles=Array.from(event.target.files);const wav=selectedFiles.filter(f=>/\.wav$/i.test(f.name)),json=selectedFiles.filter(f=>/\.json$/i.test(f.name));
  if(wav.length!==1||json.length!==1){status('Select exactly one WAV and one matching .score.json together.',true);return;}
  const id=++loadId;stopForLoad();status('Opening local recording…');
  try{if(json[0].size>25*1024*1024)throw Error('Score JSON is too large (25 MB limit).');const plan=MusicusTimeline.validate(JSON.parse(await json[0].text()));if(id!==loadId)return;blobURL=URL.createObjectURL(wav[0]);document.querySelectorAll('.sample').forEach(b=>b.classList.remove('selected'));activate(plan,blobURL,wav[0].name);}
  catch(e){if(id===loadId)status(`Could not open recording: ${e.message}`,true);}
});
audio.addEventListener('loadedmetadata',()=>{if(!score)return;if(!Number.isFinite(audio.duration)||Math.abs(audio.duration-score.duration_s)>.3){status('The WAV duration does not match this score. Choose the matching pair.',true);return;}playable=true;$('play').disabled=false;$('seek').disabled=false;$('seek').max=audio.duration;status('Ready. Press play. Display follows musical time; measurements are per-point values.');draw(true);});
audio.addEventListener('error',()=>{if(score){playable=false;$('play').disabled=true;$('seek').disabled=true;status('Audio could not be loaded. Check that the matching WAV is available.',true);}});
$('play').onclick=async()=>{if(!playable)return;if(audio.paused){try{await audio.play();}catch(e){status(`Playback could not start: ${e.message}`,true);}}else audio.pause();};
for(const event of ['play','pause','ended','seeked','timeupdate'])audio.addEventListener(event,()=>{$('play').textContent=audio.paused?'▶':'Ⅱ';$('play').setAttribute('aria-label',audio.paused?'Play':'Pause');draw();});
$('seek').addEventListener('input',()=>{audio.currentTime=Number($('seek').value);draw(true);});
$('volume').oninput=()=>{audio.volume=Number($('volume').value);};audio.volume=.65;
document.querySelectorAll('.sample').forEach(b=>b.onclick=()=>loadSample(b.dataset.sample));
function frame(){draw();requestAnimationFrame(frame);}requestAnimationFrame(frame);
if(location.protocol==='http:'||location.protocol==='https:')loadSample('avs_0p5a');else status('Open a local WAV + score JSON, or run python pd_musicus.py --player for bundled samples.');
