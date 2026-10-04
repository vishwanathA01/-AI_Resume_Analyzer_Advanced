const form = document.getElementById("uploadForm");
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);
    const box = document.getElementById("result");
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    box.textContent = "Analyzing your resume...";
    try {
      const res = await fetch("/api/resume/upload", {method:"POST", body:data});
      const json = await res.json();
      if (!res.ok) {
        box.textContent = json.error || "Resume analysis failed. Please try again.";
        return;
      }
      box.textContent = `${json.message}\nResume quality: ${json.score}%\nATS checklist: ${json.ats_score}%\nExperience: ${json.experience_years == null ? "Not detected" : `${json.experience_years} years`}\nSkills found: ${json.skills.join(", ") || "No recognized skills found"}`;
      setTimeout(() => location.reload(), 1400);
    } catch (error) {
      box.textContent = "Could not reach the server. Check your connection and try again.";
    } finally {
      button.disabled = false;
    }
  });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

async function recommend(id){
  const box = document.getElementById("jobs");
  box.textContent = "Finding the best jobs for this resume...";
  try {
    const res = await fetch("/api/recommendations/" + encodeURIComponent(id));
    const data = await res.json();
    if (!res.ok) {
      box.textContent = data.error || "We could not find recommendations. Please try again.";
      return;
    }
    if (!data.length) {
      box.textContent = "There are no active roles to match right now.";
      return;
    }
    box.innerHTML = data.map(job => `
      <article class="job-card">
        <div class="job-heading"><div><p class="card-kicker">${escapeHtml(job.company)}</p><h3>${escapeHtml(job.title)}</h3></div><strong class="recommendation-score">${escapeHtml(job.final_score)}% <small>match</small></strong></div>
        <p class="job-location">${escapeHtml(job.location)}</p>
        <p>${escapeHtml(job.matching_method)} similarity: ${escapeHtml(job.semantic_score)}% · Skills: ${escapeHtml(job.skill_score)}% · Experience: ${escapeHtml(job.experience_score)}% · Education: ${escapeHtml(job.education_score)}% · Projects: ${escapeHtml(job.project_score)}%</p>
        <p>Matched skills: ${job.matched_skills.map(escapeHtml).join(", ") || "None identified"}</p>
        <div>${job.missing_skills.length ? job.missing_skills.map(skill => `<span class="badge gap-badge">${escapeHtml(skill)}</span>`).join("") : "<span class='badge success-badge'>No major skill gaps found</span>"}</div>
      </article>
    `).join("");
  } catch (error) {
    box.textContent = "Could not reach the server. Check your connection and try again.";
  }
}
