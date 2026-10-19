"use strict";

// The access token is kept only for this browser tab. The API verifies it and
// reads the current role from the database; no role or server secret is trusted here.
const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_KEY = "forma_access_token";
const state = { token: sessionStorage.getItem(TOKEN_KEY), user: null, classes: [], bookedClassIds: new Set() };
const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];

function apiError(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) return payload.detail.map((item) => item.msg).join(" ");
  return fallback;
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let response;
  try { response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers }); }
  catch { throw new Error("Could not reach the API. Start the FastAPI server and try again."); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) {
      logout(false);
      throw new Error("Your session has expired. Please log in again.");
    }
    throw new Error(apiError(body, "Something went wrong. Please try again."));
  }
  return body;
}

function formatDate(value, includeYear = false) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "numeric", month: "short", ...(includeYear ? { year: "numeric" } : {}), hour: "numeric", minute: "2-digit", hour12: true }).format(date) + " IST";
}

function setMessage(form, message = "", type = "") { const element = $(".form-message", form); element.textContent = message; element.className = `form-message ${type}`; }
let toastTimer;
function toast(message) { const element = $("#toast"); element.textContent = message; element.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => element.classList.remove("show"), 4200); }
function escapeHTML(value) { const node = document.createElement("span"); node.textContent = value; return node.innerHTML; }

function setAuthenticatedUI() {
  const authenticated = Boolean(state.token && state.user);
  $$('[data-auth-only], [data-auth-section]').forEach((element) => { element.hidden = !authenticated; });
  $$('[data-roles]').forEach((element) => {
    const permittedRoles = element.dataset.roles.split(" ");
    element.hidden = !authenticated || !permittedRoles.includes(state.user.role);
  });
  $(".nav-login").hidden = authenticated; $(".nav-join").hidden = authenticated; $(".nav-logout").hidden = !authenticated;
}

function canManageClass(item) { return state.user && (state.user.role === "admin" || (state.user.role === "host" && item.creator_id === state.user.id)); }

function renderClasses() {
  const grid = $("#classes-grid");
  if (!state.classes.length) { grid.innerHTML = '<div class="empty-state">No upcoming classes yet. Check back soon.</div>'; return; }
  grid.innerHTML = state.classes.map((item) => {
    const isBooked = state.bookedClassIds.has(item.id);
    const isFull = item.available_slots === 0;
    const label = isBooked ? "Already booked" : isFull ? "Class full" : state.user ? "Reserve your spot →" : "Log in to book →";
    const cancelControl = canManageClass(item) ? `<button class="cancel-button" data-cancel-class-id="${item.id}">Cancel this class</button>` : "";
    return `<article class="class-card"><div class="card-top"><span>CLASS ${String(item.id).padStart(2, "0")}</span><span>${item.available_slots}/${item.total_slots} spots</span></div><h3>${escapeHTML(item.name)}</h3><p class="instructor">with ${escapeHTML(item.instructor)}</p><p class="time">${formatDate(item.date_time)}</p><button class="button button-dark book-button" data-class-id="${item.id}" ${isBooked || isFull ? "disabled" : ""}>${label}</button>${cancelControl}</article>`;
  }).join("");
}

async function loadClasses() {
  $("#classes-status").textContent = "Loading the schedule…";
  try { state.classes = await request("/classes", { method: "GET" }); renderClasses(); $("#classes-status").textContent = ""; }
  catch (error) { $("#classes-status").textContent = error.message; $("#classes-grid").innerHTML = '<div class="empty-state">The schedule could not load. Please try again.</div>'; }
}

function renderBookings(bookings) {
  const list = $("#bookings-list");
  if (!bookings.length) { list.innerHTML = '<div class="empty-state">You have no reservations yet. Find a class that feels good.</div>'; return; }
  list.innerHTML = bookings.map((booking, index) => {
    const cancelled = booking.fitness_class.is_cancelled ? '<span class="cancelled-label">Cancelled</span>' : "";
    return `<article class="booking-card"><span class="booking-number">${String(index + 1).padStart(2, "0")}</span><div><h3>${escapeHTML(booking.fitness_class.name)} ${cancelled}</h3><p>with ${escapeHTML(booking.fitness_class.instructor)} · Booking #${booking.id}</p></div><time class="booking-time">${formatDate(booking.fitness_class.date_time, true)}</time></article>`;
  }).join("");
}

async function loadBookings() {
  if (!state.user) return;
  $("#bookings-status").textContent = "Loading your bookings…";
  try { const bookings = await request("/bookings", { method: "GET" }); state.bookedClassIds = new Set(bookings.filter((item) => !item.fitness_class.is_cancelled).map((item) => item.class_id)); renderBookings(bookings); renderClasses(); $("#bookings-status").textContent = ""; }
  catch (error) { $("#bookings-status").textContent = error.message; }
}

async function bookClass(classId, button) {
  if (!state.user) { openAuth("login"); return; }
  button.disabled = true; button.textContent = "Reserving…";
  try { await request("/book", { method: "POST", body: JSON.stringify({ class_id: Number(classId) }) }); state.bookedClassIds.add(Number(classId)); toast("Your spot is reserved. See you in the studio!"); await Promise.all([loadClasses(), loadBookings()]); }
  catch (error) { toast(error.message); await loadClasses(); }
}

async function cancelClass(classId, button) {
  if (!window.confirm("Cancel this class? Existing bookings will be preserved and marked as cancelled.")) return;
  button.disabled = true; button.textContent = "Cancelling…";
  try { await request(`/classes/${classId}/cancel`, { method: "PATCH" }); toast("Class cancelled. Existing bookings remain in history."); await Promise.all([loadClasses(), loadBookings()]); }
  catch (error) { toast(error.message); button.disabled = false; button.textContent = "Cancel this class"; }
}

function openAuth(tab = "login") { $("#auth-modal").hidden = false; switchAuthTab(tab); $(".modal-panel input").focus(); }
function closeAuth() { $("#auth-modal").hidden = true; }
function switchAuthTab(tab) { $$('[data-auth-tab]').forEach((button) => button.classList.toggle("active", button.dataset.authTab === tab)); $("#login-form").hidden = tab !== "login"; $("#signup-form").hidden = tab !== "signup"; $("#auth-title").textContent = tab === "login" ? "Welcome back." : "Your next class starts here."; }

async function loadVerifiedUser() { state.user = await request("/me", { method: "GET" }); setAuthenticatedUI(); }
async function authenticate(form, endpoint) {
  if (!form.reportValidity()) return;
  setMessage(form); const button = $("button[type=submit]", form); button.disabled = true;
  const payload = Object.fromEntries(new FormData(form));
  try {
    if (endpoint === "/signup") { await request(endpoint, { method: "POST", body: JSON.stringify(payload) }); toast("Account created — now log in to reserve a class."); form.reset(); switchAuthTab("login"); $("#login-form input[name=email]").value = payload.email; }
    else { const result = await request(endpoint, { method: "POST", body: JSON.stringify(payload) }); state.token = result.access_token; sessionStorage.setItem(TOKEN_KEY, state.token); await loadVerifiedUser(); closeAuth(); toast("You are logged in. Welcome to Forma!"); await Promise.all([loadClasses(), loadBookings()]); }
  } catch (error) { setMessage(form, error.message, "error"); } finally { button.disabled = false; }
}

function logout(showMessage = true) { state.token = null; state.user = null; state.bookedClassIds = new Set(); sessionStorage.removeItem(TOKEN_KEY); setAuthenticatedUI(); renderClasses(); $("#bookings-list").innerHTML = ""; if (showMessage) toast("You have been logged out."); }
async function createClass(form) {
  if (!form.reportValidity()) return;
  const data = Object.fromEntries(new FormData(form)); const localDate = new Date(data.date_time);
  if (localDate <= new Date()) { setMessage(form, "Choose a future date and time.", "error"); return; }
  const istLocalValue = data.date_time.length === 16 ? `${data.date_time}:00` : data.date_time;
  data.date_time = `${istLocalValue}+05:30`; data.total_slots = Number(data.total_slots);
  const button = $("button[type=submit]", form); button.disabled = true; setMessage(form);
  try { await request("/classes", { method: "POST", body: JSON.stringify(data) }); form.reset(); setMessage(form, "Class published to the live schedule.", "success"); toast("Class published successfully."); await loadClasses(); }
  catch (error) { setMessage(form, error.message, "error"); } finally { button.disabled = false; }
}

$(".menu-toggle").addEventListener("click", (event) => { const open = $(".nav-links").classList.toggle("open"); event.currentTarget.setAttribute("aria-expanded", open); });
$$('.nav-links a').forEach((link) => link.addEventListener("click", () => $(".nav-links").classList.remove("open")));
$$('[data-open-auth]').forEach((button) => button.addEventListener("click", () => openAuth(button.dataset.openAuth)));
$$('[data-close-modal]').forEach((button) => button.addEventListener("click", closeAuth)); $$('[data-auth-tab]').forEach((button) => button.addEventListener("click", () => switchAuthTab(button.dataset.authTab)));
$("#login-form").addEventListener("submit", (event) => { event.preventDefault(); authenticate(event.currentTarget, "/login"); });
$("#signup-form").addEventListener("submit", (event) => { event.preventDefault(); authenticate(event.currentTarget, "/signup"); });
$("#class-form").addEventListener("submit", (event) => { event.preventDefault(); createClass(event.currentTarget); });
$("#classes-grid").addEventListener("click", (event) => { const book = event.target.closest(".book-button"); const cancel = event.target.closest(".cancel-button"); if (book) bookClass(book.dataset.classId, book); if (cancel) cancelClass(cancel.dataset.cancelClassId, cancel); });
$("#refresh-classes").addEventListener("click", loadClasses); $("#refresh-bookings").addEventListener("click", loadBookings); $$('[data-logout]').forEach((button) => button.addEventListener("click", () => logout()));
setAuthenticatedUI(); loadClasses();
if (state.token) loadVerifiedUser().then(loadBookings).catch((error) => toast(error.message));
