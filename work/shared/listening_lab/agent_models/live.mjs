import fs from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scratch = path.dirname(fileURLToPath(import.meta.url));
const model = process.argv[2];
const name = process.argv[3];
const cases = JSON.parse(fs.readFileSync(path.resolve(scratch,"../probes.json")));
const example = cases.find(x=>x.id===name);
const key = process.env.GEMINI_API_KEY;
if (!key || !example || !model) process.exit(2);
const pcm = execFileSync("ffmpeg", ["-v","error","-i",example.file,"-f","s16le","-ar","16000","-ac","1","-"]);
const instruction = "I will send one recording with two short instrumental passages A and B separated by a second of silence. A is first. They can be identical. " + example.question + " Speak only one answer: A, B, SAME, or UNSURE. Wait for the entire input to finish.";
const ws = new WebSocket("wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key="+encodeURIComponent(key));
const send = x=>ws.send(JSON.stringify(x));
const seen = [];
let transcript = [];
let complete = false;
const extended = model.includes("extended-thinking");
let interactionStarted = false;
const finish = (error) => {
  if (complete) return;
  complete=true;
  clearTimeout(timeout);
  fs.writeFileSync(path.join(scratch,model+"_"+name+".json"),JSON.stringify({expected:example.answer,transcript:transcript.join(""),seen,error},null,2));
  console.log(model,name,JSON.stringify({transcript:transcript.join(""),seen,error}));
  if(ws.readyState<2) ws.close();
};
const timeout=setTimeout(()=>finish("deadline"), 75000);
ws.addEventListener("open",()=>send({setup:{model:"models/"+model,generationConfig:{responseModalities:["AUDIO"],...(model.includes("extended-thinking") ? {thinkingConfig:{thinkingLevel:"LOW"}} : {})},systemInstruction:{parts:[{text:instruction}]},outputAudioTranscription:{},realtimeInputConfig:{automaticActivityDetection:{disabled:true}}}}));
ws.addEventListener("error",()=>seen.push("socket error"));
ws.addEventListener("close",e=>finish(e.code+" "+e.reason.replaceAll(key,"[redacted]")));
ws.addEventListener("message", async e => {
  const msg=JSON.parse(typeof e.data==="string" ? e.data : await e.data.text());
  if(msg.setupComplete) {
    seen.push("setupComplete");
    send({realtimeInput:{activityStart:{}}});
    for(let i=0;i<pcm.length;i+=6400) {
      if(ws.readyState!==1) break;
      send({realtimeInput:{audio:{mimeType:"audio/pcm;rate=16000",data:pcm.subarray(i,i+6400).toString("base64")}}});
      await new Promise(r=>setTimeout(r,8));
    }
    if(ws.readyState===1)send({realtimeInput:{activityEnd:{}}});
  }
  const sc=msg.serverContent;
  if(sc?.outputTranscription?.text) transcript.push(sc.outputTranscription.text);
  const status=msg.interactionStatus || sc?.interactionStatus;
  if(status) seen.push(status);
  if(status==="IN_PROGRESS") interactionStarted=true;
  if(sc?.turnComplete) seen.push("turnComplete");
  if(extended ? (status==="IDLE" && (interactionStarted || transcript.length>0)) : sc?.turnComplete) finish(null);
});
