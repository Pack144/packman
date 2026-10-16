const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");

const source = readFileSync("packman/mail/static/mail/js/preview.js", "utf8");

function setup(fetch) {
  const timers = new Map();
  const listeners = {};
  const classes = new Set();
  const button = {
    dataset: { previewUrl: "/mail/preview/" },
    disabled: false,
    focusCount: 0,
    closest: () => ({
      elements: {
        subject: { value: "Subject" },
        body: { value: "<p>Body</p>" },
        csrfmiddlewaretoken: { value: "token" },
      },
    }),
    addEventListener: (event, callback) => { listeners[event] = callback; },
    focus: () => {
      assert.equal(button.disabled, false);
      button.focusCount++;
    },
  };
  const dialog = {
    dataset: { errorMessage: "Unable to load the preview. Please try again.", loadingMessage: "Loading preview..." },
    addEventListener: (event, callback) => { listeners[event] = callback; },
  };
  const frame = {
    hidden: true,
    removeAttribute: () => { delete frame.srcdoc; },
  };
  const status = {
    textContent: "",
    classList: { add: (value) => classes.add(value), remove: (value) => classes.delete(value) },
  };
  const elements = {
    "message-preview-button": button,
    "message-preview-modal": dialog,
    "message-preview-frame": frame,
    "message-preview-status": status,
  };
  runInNewContext(source, {
    document: { getElementById: (id) => elements[id] },
    window: {},
    bootstrap: { Modal: class { show() {} } },
    AbortController,
    URLSearchParams,
    fetch,
    setTimeout: (callback, delay) => {
      assert.equal(delay, 15000);
      const id = Symbol();
      timers.set(id, callback);
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
  });
  return { button, dialog, frame, status, classes, timers, listeners };
}

function untilAbort(signal) {
  return new Promise((resolve, reject) => {
    signal.addEventListener("abort", () => reject(signal.reason), { once: true });
  });
}

test("stalled fetch times out, shows an error, and permits a successful retry", async () => {
  let attempts = 0;
  const ui = setup((url, { signal }) => {
    if (++attempts === 1) return untilAbort(signal);
    return Promise.resolve({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ html: "<p>Preview</p>" }),
    });
  });
  const request = ui.listeners.click();
  assert.equal(ui.button.disabled, true);
  assert.equal(ui.status.textContent, ui.dialog.dataset.loadingMessage);
  [...ui.timers.values()][0]();
  await request;
  assert.equal(ui.status.textContent, ui.dialog.dataset.errorMessage);
  assert.equal(ui.classes.has("text-danger"), true);
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.frame.hidden, true);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.button.focusCount, 0);

  await ui.listeners.click();
  assert.equal(ui.frame.srcdoc, "<p>Preview</p>");
  assert.equal(ui.frame.hidden, false);
  assert.equal(ui.status.textContent, "");
  assert.equal(ui.classes.has("text-danger"), false);
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.timers.size, 0);
});

test("timeout also covers a stalled response body", async () => {
  let startedBody;
  const bodyStarted = new Promise((resolve) => { startedBody = resolve; });
  const ui = setup(async (url, { signal }) => ({
    ok: true,
    headers: { get: () => "application/json" },
    json: () => {
      startedBody();
      return untilAbort(signal);
    },
  }));
  const request = ui.listeners.click();
  await bodyStarted;
  [...ui.timers.values()][0]();
  await request;
  assert.equal(ui.status.textContent, ui.dialog.dataset.errorMessage);
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.timers.size, 0);
});

test("closing the modal aborts without a timeout error and clears the timer", async () => {
  const ui = setup((url, { signal }) => untilAbort(signal));
  const request = ui.listeners.click();
  ui.listeners["hidden.bs.modal"]();
  assert.equal(ui.button.disabled, true);
  assert.equal(ui.button.focusCount, 0);
  await request;
  assert.equal(ui.classes.has("text-danger"), false);
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.timers.size, 0);
  assert.equal(ui.button.focusCount, 1);
});

test("closing after a successful preview restores focus immediately", async () => {
  const ui = setup(async () => ({
    ok: true,
    headers: { get: () => "application/json" },
    json: async () => ({ html: "<p>Preview</p>" }),
  }));
  await ui.listeners.click();
  assert.equal(ui.button.focusCount, 0);
  ui.listeners["hidden.bs.modal"]();
  assert.equal(ui.button.focusCount, 1);
});

test("request failures clear the timeout and re-enable Preview", async () => {
  const ui = setup(() => Promise.reject(new Error("Request failed")));
  await ui.listeners.click();
  assert.equal(ui.status.textContent, "Request failed");
  assert.equal(ui.classes.has("text-danger"), true);
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.timers.size, 0);
});
