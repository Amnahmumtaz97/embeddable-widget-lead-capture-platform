(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) return;
  var scriptUrl = new URL(script.src);
  var widgetId = scriptUrl.searchParams.get("id");
  if (!widgetId) { console.error("Lead widget: missing id query parameter"); return; }
  var apiBase = scriptUrl.origin;
  var host = document.createElement("div");
  host.setAttribute("data-lead-widget", widgetId);
  script.insertAdjacentElement("afterend", host);
  var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
  function el(name, attrs, text) {
    var node = document.createElement(name);
    Object.keys(attrs || {}).forEach(function (key) { node.setAttribute(key, attrs[key]); });
    if (text) node.textContent = text;
    return node;
  }
  fetch(apiBase + "/widgets/" + encodeURIComponent(widgetId) + "/config")
    .then(function (response) { if (!response.ok) throw new Error("Widget configuration unavailable"); return response.json(); })
    .then(function (config) {
      var style = el("style");
      style.textContent = ".card{font:14px system-ui,sans-serif;max-width:380px;padding:20px;border:1px solid #dbe3ea;border-radius:12px;box-shadow:0 8px 24px #0f172a12;background:#fff;color:#172033}.card h2{margin:0 0 6px;font-size:20px}.card p{color:#526174}.field{display:block;margin:12px 0}.field span{display:block;margin-bottom:5px;font-weight:600}.field input,.field textarea{box-sizing:border-box;width:100%;padding:9px;border:1px solid #b8c4cf;border-radius:7px}.card button{padding:10px 16px;border:0;border-radius:7px;background:#176b52;color:white;font-weight:700;cursor:pointer}.message{margin-top:10px}.hp{position:absolute;left:-10000px}";
      root.appendChild(style);
      var card = el("section", { "class": "card" });
      card.appendChild(el("h2", {}, config.title));
      if (config.description) card.appendChild(el("p", {}, config.description));
      var form = el("form");
      (config.fields || []).forEach(function (field) {
        var label = el("label", { "class": "field" });
        label.appendChild(el("span", {}, field.label));
        var tag = field.type === "textarea" ? "textarea" : "input";
        var input = el(tag, { name: field.name, maxlength: String(field.max_length || 255) });
        if (tag === "input") input.type = field.type === "email" ? "email" : "text";
        input.required = Boolean(field.required);
        label.appendChild(input);
        form.appendChild(label);
      });
      form.appendChild(el("input", { name: "website", tabindex: "-1", autocomplete: "off", "class": "hp", "aria-hidden": "true" }));
      form.appendChild(el("button", { type: "submit" }, config.button_text || "Submit"));
      var message = el("div", { "class": "message", role: "status" });
      form.appendChild(message);
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var values = new FormData(form);
        var data = {};
        (config.fields || []).forEach(function (field) { data[field.name] = String(values.get(field.name) || ""); });
        fetch(config.submit_url, { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) }, body: JSON.stringify({ widget_id: config.id, data: data, website: String(values.get("website") || "") }) })
          .then(function (response) { return response.json().then(function (body) { if (!response.ok) throw new Error(body.error || "Submission failed"); return body; }); })
          .then(function () { form.reset(); message.textContent = "Thanks - your response was received."; })
          .catch(function (error) { message.textContent = error.message; });
      });
      card.appendChild(form);
      root.appendChild(card);
    }).catch(function (error) { console.error("Lead widget:", error); });
}());
