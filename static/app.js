const $ = (id) => document.getElementById(id);
$("todayDate").textContent = new Date().toLocaleDateString(undefined, {weekday:"short", month:"short", day:"numeric"});

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {"Content-Type":"application/json", ...(options.headers || {})},
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
}

async function loadTasks() {
  const tasks = await api("/api/tasks");
  $("pendingCount").textContent = tasks.filter(t => !t.done).length;
  $("doneCount").textContent = tasks.filter(t => t.done).length;
  $("taskList").innerHTML = tasks.length ? tasks.map(t => `
    <div class="task-row">
      <input type="checkbox" aria-label="Mark task complete" data-toggle="${t.id}" ${t.done ? "checked" : ""}>
      <div class="task-main"><div class="task-title ${t.done ? "done" : ""}">${escapeHtml(t.title)}</div>
      <div class="task-meta">${escapeHtml(t.category)}${t.due_date ? " · " + escapeHtml(t.due_date) : ""}</div></div>
      <button class="delete-btn" data-delete="${t.id}" type="button">Delete</button>
    </div>`).join("") : '<p class="muted">No tasks yet. Add your first task above.</p>';
}

async function loadResources() {
  const resources = await api("/api/resources");
  $("resourceCount").textContent = resources.length;
  $("resourceList").innerHTML = resources.map(r => `
    <a class="resource-card" href="${escapeHtml(r.url)}" target="_blank" rel="noopener noreferrer">
      <strong>${escapeHtml(r.title)}</strong><p>${escapeHtml(r.summary)}</p><span>Open resource ↗</span>
    </a>`).join("");
}

let currentUnstopCategory = "hackathons";

async function loadUnstop(category = currentUnstopCategory, search = "") {
  const list = $("unstopList");
  list.innerHTML = '<p class="muted">Fetching opportunities from Unstop…</p>';
  try {
    const data = await api(`/api/unstop?category=${category}&search=${encodeURIComponent(search)}`);
    const items = data.results || [];
    if (!items.length) {
      list.innerHTML = '<p class="muted">No opportunities found for this query. Try a different keyword or category.</p>';
      return;
    }
    list.innerHTML = items.map(o => {
      const isLive = o.status === "STARTED" || o.status === "ACTIVE";
      const deadlineText = o.deadline ? o.deadline.slice(0, 10) : o.remain_days;
      const taskPayload = encodeURIComponent(JSON.stringify({
        title: `${o.title} (${o.organisation})`,
        due: deadlineText,
        cat: category === "internships" || category === "jobs" ? "Assignment" : "Project"
      }));
      const resPayload = encodeURIComponent(JSON.stringify({
        title: `${o.title} - Unstop`,
        url: o.url,
        summary: `${o.organisation} · ${o.remain_days}${o.skills && o.skills.length ? ' · Skills: ' + o.skills.join(', ') : ''}`
      }));

      return `
        <div class="unstop-card">
          <div class="unstop-card-head">
            <span class="unstop-badge ${isLive ? 'badge-live' : 'badge-ended'}">${escapeHtml(o.remain_days)}</span>
            <span class="unstop-type-badge">${escapeHtml(o.category)}</span>
            <span class="unstop-reg-count">👥 ${o.registrations || 0}</span>
          </div>
          <h3 class="unstop-card-title">${escapeHtml(o.title)}</h3>
          <div class="unstop-org">🏢 ${escapeHtml(o.organisation)}</div>
          ${o.prizes && o.prizes.length ? `<div class="unstop-prizes">🎁 ${escapeHtml(o.prizes.join(' · '))}</div>` : ''}
          <div class="unstop-tags">
            ${(o.skills || []).map(s => `<span class="tag-pill">${escapeHtml(s)}</span>`).join('')}
            ${(o.filters || []).slice(0, 2).map(f => `<span class="tag-pill filter-pill">${escapeHtml(f)}</span>`).join('')}
          </div>
          <div class="unstop-card-footer">
            <a class="unstop-link" href="${escapeHtml(o.url)}" target="_blank" rel="noopener noreferrer">View details ↗</a>
            <div class="unstop-actions">
              <button class="action-btn sm" data-add-task="${taskPayload}" type="button">+ Task</button>
              <button class="action-btn sm secondary" data-add-res="${resPayload}" type="button">★ Save</button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch (error) {
    list.innerHTML = `<p class="muted">Could not load Unstop opportunities: ${escapeHtml(error.message)}</p>`;
  }
}

// Category tabs
const tabsContainer = $("unstopTabs");
if (tabsContainer) {
  tabsContainer.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    tabsContainer.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentUnstopCategory = btn.dataset.cat;
    const searchVal = $("unstopSearchInput").value.trim();
    loadUnstop(currentUnstopCategory, searchVal);
  });
}

// Search form
const unstopSearchForm = $("unstopSearchForm");
if (unstopSearchForm) {
  unstopSearchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    loadUnstop(currentUnstopCategory, $("unstopSearchInput").value.trim());
  });
}

// Click delegator for adding to tasks or saving to resources
$("unstopList").addEventListener("click", async (e) => {
  const taskBtn = e.target.closest("[data-add-task]");
  if (taskBtn) {
    try {
      const data = JSON.parse(decodeURIComponent(taskBtn.dataset.addTask));
      await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({title: data.title, category: data.cat, due_date: data.due})
      });
      taskBtn.textContent = "✓ Added!";
      taskBtn.disabled = true;
      await loadTasks();
    } catch (err) { alert(err.message); }
    return;
  }

  const resBtn = e.target.closest("[data-add-res]");
  if (resBtn) {
    try {
      const data = JSON.parse(decodeURIComponent(resBtn.dataset.addRes));
      await api("/api/resources", {
        method: "POST",
        body: JSON.stringify({title: data.title, url: data.url, summary: data.summary})
      });
      resBtn.textContent = "✓ Saved!";
      resBtn.disabled = true;
      await loadResources();
    } catch (err) { alert(err.message); }
    return;
  }
});

// Task form submission
$("taskForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/tasks", {method:"POST", body:JSON.stringify({
      title:$("taskTitle").value, category:$("taskCategory").value, due_date:$("taskDue").value
    })});
    $("taskTitle").value = ""; $("taskDue").value = "";
    await loadTasks();
  } catch (error) { alert(error.message); }
});

$("taskList").addEventListener("change", async (event) => {
  const id = event.target.dataset.toggle;
  if (!id) return;
  try { await api(`/api/tasks/${id}`, {method:"PATCH", body:JSON.stringify({done:event.target.checked})}); await loadTasks(); }
  catch (error) { alert(error.message); }
});

$("taskList").addEventListener("click", async (event) => {
  const id = event.target.dataset.delete;
  if (!id) return;
  try { await api(`/api/tasks/${id}`, {method:"DELETE"}); await loadTasks(); }
  catch (error) { alert(error.message); }
});

// Scraper submission
$("scrapeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const resultBox = $("scrapeResult");
  resultBox.classList.remove("hidden");
  resultBox.innerHTML = '<p class="muted">Reading and extracting page details…</p>';
  try {
    const data = await api("/api/scrape", {method:"POST", body:JSON.stringify({url:$("scrapeUrl").value})});
    
    let actionsHtml = "";
    if (data.is_unstop && data.unstop_data) {
      const u = data.unstop_data;
      const deadlineText = u.deadline ? u.deadline.slice(0, 10) : u.remain_days;
      const taskPayload = encodeURIComponent(JSON.stringify({
        title: `${u.title} (${u.organisation})`,
        due: deadlineText,
        cat: u.category === "internships" || u.category === "jobs" ? "Assignment" : "Project"
      }));
      const resPayload = encodeURIComponent(JSON.stringify({
        title: `${u.title} - Unstop`,
        url: u.url,
        summary: data.summary
      }));
      actionsHtml = `
        <div class="unstop-actions" style="margin-top:14px;">
          <button class="action-btn" data-add-task="${taskPayload}" type="button">+ Add as Task</button>
          <button class="action-btn secondary" data-add-res="${resPayload}" type="button">★ Save to Resources</button>
        </div>
      `;
    }

    resultBox.innerHTML = `
      <h3>${escapeHtml(data.title)}</h3>
      <p class="muted"><a href="${escapeHtml(data.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(data.url)} ↗</a></p>
      ${data.headings && data.headings.length ? "<strong>Highlights & Metadata</strong><ul>"+data.headings.map(h=>`<li>${escapeHtml(h)}</li>`).join("")+"</ul>" : ""}
      <strong>Summary</strong>
      <p class="muted">${escapeHtml(data.summary || "No readable content found.")}</p>
      ${actionsHtml}
    `;

    // Hook action buttons if present
    const tBtn = resultBox.querySelector("[data-add-task]");
    if (tBtn) {
      tBtn.addEventListener("click", async () => {
        const payload = JSON.parse(decodeURIComponent(tBtn.dataset.addTask));
        await api("/api/tasks", {method:"POST", body:JSON.stringify({title:payload.title, category:payload.cat, due_date:payload.due})});
        tBtn.textContent = "✓ Added to Tasks!";
        tBtn.disabled = true;
        await loadTasks();
      });
    }
    const rBtn = resultBox.querySelector("[data-add-res]");
    if (rBtn) {
      rBtn.addEventListener("click", async () => {
        const payload = JSON.parse(decodeURIComponent(rBtn.dataset.addRes));
        await api("/api/resources", {method:"POST", body:JSON.stringify({title:payload.title, url:payload.url, summary:payload.summary})});
        rBtn.textContent = "✓ Saved to Resources!";
        rBtn.disabled = true;
        await loadResources();
      });
    }
  } catch (error) { resultBox.textContent = error.message; }
});

Promise.all([loadTasks(), loadResources(), loadUnstop()]).catch(error => {
  $("taskList").innerHTML = `<p class="muted">Could not load data: ${escapeHtml(error.message)}</p>`;
});
