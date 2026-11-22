"use strict";
const $ = id => document.getElementById(id);
const canvas = $("canvas");
const ctx = canvas.getContext("2d");
let photo, blob, points = [], available = false, generation = 0, busy = false, practiceImage = false;
const instructions = ["Click one end of the scale bar.", "Now click the other end.",
  "Click just above and to the left of one cell to start the box.", "Click below and to the right. Leave a little smear around the cell.",
  "Your bar and cell box are marked."];

function selection() {
  const [a,b,c,d] = points;
  return {bar: [...a,...b], cell: [Math.min(c[0],d[0]), Math.min(c[1],d[1]),
    Math.max(c[0],d[0]), Math.max(c[1],d[1])]};
}
function repaint() {
  if (photo) {
    ctx.drawImage(photo,0,0);
    ctx.lineWidth = Math.max(2, canvas.width/300);
    points.forEach(([x,y],i) => {
      ctx.fillStyle = i<2 ? "#ec9420" : "#00a79f";
      ctx.beginPath(); ctx.arc(x,y,ctx.lineWidth*1.6,0,2*Math.PI); ctx.fill();
    });
    if (points.length>=2) {
      ctx.strokeStyle = "#ec9420";ctx.beginPath();ctx.moveTo(...points[0]);ctx.lineTo(...points[1]);ctx.stroke();
    }
    if (points.length===4) {
      const [x,y,r,b]=selection().cell;ctx.strokeStyle="#00a79f";ctx.strokeRect(x,y,r-x,b-y);
    }
  }
  $("reset").disabled = !photo;
  $("measure").disabled = points.length!==4 || busy;
  $("classify").disabled = practiceImage || !available || points.length!==4 || busy;
  $("step").textContent = photo ? instructions[points.length] : "Open your image or try the practice image.";
}
function clearReadout() { $("message").textContent=""; $("result").replaceChildren(); }
function markChanged() { generation++; busy=false; clearReadout(); repaint(); }
async function openImage(file, name, practice=false) {
  const ticket = ++generation;
  points=[]; photo=null; blob=null; busy=false; ctx.clearRect(0,0,canvas.width,canvas.height);
  $("empty").hidden=false; $("caption").textContent=""; $("bar").value=""; $("cell").value="";
  clearReadout(); repaint();
  try {
    if (!file || !file.size || file.size>8*1024*1024 || !["image/jpeg","image/png"].includes(file.type))
      throw Error("Use a PNG or JPEG no larger than 8 MiB.");
    const url=URL.createObjectURL(file); const img=new Image();
    try { img.src=url; await img.decode(); } finally { URL.revokeObjectURL(url); }
    if (img.width*img.height>12000000) throw Error("Use an image no larger than 12 megapixels.");
    // If the user opened another image while this one loaded, keep the newer image.
    if (ticket!==generation) return;
    canvas.width=img.width;canvas.height=img.height;photo=img;blob=file;
    $("empty").hidden=true;
    practiceImage=practice;
    $("caption").textContent=name+" · "+img.width+" × "+img.height+" px";
    repaint();
  } catch(e) { if(ticket===generation) $("message").textContent=e.message; }
}
$("file").onchange=e=>openImage(e.target.files[0],e.target.files[0]?.name || "Image");
$("example").onclick=async()=>{
  try { const response=await fetch("/example.png");
    if (!response.ok) throw Error("Couldn’t open the practice image. Try opening it again.");
    await openImage(await response.blob(),"Practice image · synthetic",true);
  } catch(e) { $("message").textContent=e.message; }
};
canvas.onclick=e=>{
  if(!photo || points.length===4) return;
  // The browser can shrink the image to fit the screen. Record clicks in the original image pixels.
  const bounds=canvas.getBoundingClientRect();
  points.push([Math.round((e.clientX-bounds.left)*canvas.width/bounds.width),
    Math.round((e.clientY-bounds.top)*canvas.height/bounds.height)]);
  if(points.length>=2) $("bar").value=points.slice(0,2).flat().join(", ");
  if(points.length===4) $("cell").value=selection().cell.join(", ");
  markChanged();
};
$("reset").onclick=()=>{ points=[]; $("bar").value=""; $("cell").value=""; markChanged(); };
$("apply").onclick=()=>{
  if(!photo) return;
  const nums=id=>$(id).value.trim().split(/[,\s]+/).map(Number);
  const bar=nums("bar"), cell=nums("cell");
  if([bar,cell].some(v=>v.length!==4 || !v.every(Number.isSafeInteger))) {
    $("message").textContent="Enter four whole numbers in each field in this order (x1, y1, x2, y2)."; return;
  }
  points=[bar.slice(0,2),bar.slice(2),cell.slice(0,2),cell.slice(2)]; markChanged();
};
async function run(action) {
  const ticket=++generation; busy=true; clearReadout(); repaint();
  try {
    const r=await fetch("/api/"+action,{method:"POST",body:blob,
      headers:{"Content-Type":blob.type,"X-Selection":JSON.stringify(selection())}});
    const v=await r.json(); if(ticket!==generation) return;
    if(!r.ok) throw Error(v.error || "Couldn’t finish analyzing this image.");
    const rows=[["Scale bar",v.bar_um+" µm / "+v.bar_px+" px"],["Pixel size",v.um_per_pixel+" µm/px"],
      ["Box size",v.box_width_um+" × "+v.box_height_um+" µm"]];
    if(v.cell_label) rows.push(["Model call",v.cell_label]);
    for(const [key,val] of rows) { const pair=document.createElement("div"), dt=document.createElement("dt"),
      dd=document.createElement("dd");dt.textContent=key;dd.textContent=val;pair.append(dt,dd);$("result").append(pair); }
  } catch(e) { if(ticket===generation) $("message").textContent=e.message; }
  finally { if(ticket===generation) { busy=false; repaint(); } }
}
$("measure").onclick=()=>run("measure"); $("classify").onclick=()=>run("classify");
fetch("/api/status").then(r=>r.json()).then(s=>{
  available=s.classification_available;
  $("model").textContent=available ? "Local model ready." : "Cell classification is unavailable.";
  repaint();
}).catch(()=>{ $("model").textContent="Couldn’t reach the local server. Check the terminal where you started the app."; });

