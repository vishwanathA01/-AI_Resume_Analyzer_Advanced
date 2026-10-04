const form = document.getElementById("uploadForm");
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);
    const box = document.getElementById("result");
    box.textContent = "Analyzing resume...";
    const res = await fetch("/api/resume/upload", {method:"POST", body:data});
    const json = await res.json();
    box.textContent = JSON.stringify(json, null, 2);
    if (res.ok) setTimeout(() => location.reload(), 1200);
  });
}

async function recommend(id){
  const box = document.getElementById("jobs");
  box.innerHTML = "<p>Finding the best jobs...</p>";
  const res = await fetch("/api/recommendations/" + id);
  const data = await res.json();
  if (!res.ok) { box.innerHTML = "<p>"+data.error+"</p>"; return; }
  box.innerHTML = data.map(j => `
    <div class="job-card">
      <h3>${j.title}</h3>
      <p>${j.company} · ${j.location}</p>
      <strong>Match: ${j.final_score}%</strong>
      <p>Semantic: ${j.semantic_score}% · Skills: ${j.skill_score}%</p>
      <div>${j.missing_skills.length ? j.missing_skills.map(s=>`<span class="badge">${s}</span>`).join("") : "<span class='badge'>No major skill gap</span>"}</div>
    </div>
  `).join("");
}
