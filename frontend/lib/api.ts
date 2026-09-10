export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function jfetch(path:string, init?:RequestInit){
 const r=await fetch(`${API}${path}`,init);
 if(!r.ok){let detail=`HTTP ${r.status}`;try{const j=await r.json();detail=j.detail||detail}catch{}throw new Error(detail)}
 return r.json();
}
