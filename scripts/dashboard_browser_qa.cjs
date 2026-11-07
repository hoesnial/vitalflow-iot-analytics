/* Local visual QA; install Playwright separately. Does not start or modify the pipeline. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const url = process.env.VITALFLOW_QA_URL || "http://127.0.0.1:8512";
const out = path.resolve(__dirname, "../outputs/dashboard-qa/screenshots");
fs.mkdirSync(out, { recursive: true });

async function check(browser, width, height, walkthrough) {
  const page = await browser.newPage({ viewport: { width, height }, acceptDownloads: true });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.route("**/*", route =>
    route.request().url().startsWith(url + "/") ? route.continue() : route.abort()
  );
  await page.routeWebSocket("**/*", socket => {
    if (new URL(socket.url()).host === new URL(url).host) socket.connectToServer();
    else socket.close();
  });
  const title = name => page.getByRole("heading", { name, exact: true });
  const nav = name => page.getByTestId("stSidebar").getByText(new RegExp(name + "$")).click();
  const lab = name => page.locator(".st-key-vf_lab").getByText(name, { exact: true }).click();
  const choose = async (key, label) => {
    const combobox = page.locator(".st-key-" + key).getByRole("combobox");
    await combobox.click();
    const option = page.getByRole("option", { name: label, exact: true });
    if (!(await option.isVisible())) await combobox.fill(label);
    await option.click();
  };
  const screenshot = async label => {
    await page.locator('[data-testid="stMain"]').evaluate(el => { el.scrollTop = 0; });
    await page.waitForFunction(() => !document.querySelector('[data-testid="stException"]'));
    const overflow = await page.evaluate(() => {
      const main = document.querySelector('[data-testid="stMain"]');
      return Math.max(document.documentElement.scrollWidth - innerWidth, main.scrollWidth - main.clientWidth);
    });
    assert(overflow <= 2, `${label} ${width}×${height} overflow: ${overflow}px`);
    await page.screenshot({ path: path.join(out, `${label}-${width}x${height}.png`), animations: "disabled" });
  };
  const chart = (key, count = 1) => page.waitForFunction(([id, minimum]) => {
    const chart = document.querySelector(`.st-key-${id} .js-plotly-plot`);
    return chart?.data?.length >= minimum;
  }, [key, count]);
  const metric = value => page.getByTestId("stMetricValue").getByText(value, { exact: true }).first();

  const start = Date.now();
  await page.goto(url);
  await title("VitalFlow").waitFor();
  await chart("overview-trend");
  console.log(`Overview ${width}x${height} with external requests blocked: ${Date.now() - start} ms`);
  await screenshot("overview");
  if (width < 1000) {
    assert.deepEqual(errors, []);
    await page.close();
    return;
  }
  if (walkthrough) {
    await choose("vf_mode", "Fast · 3 rekaman");
    await metric("3").waitFor();
    await choose("vf_mode", "Default · 10 rekaman");
    await metric("10").waitFor();
    await choose("vf_mode", "Complete · 53 rekaman");
    await metric("53").waitFor();
  }
  await nav("Recording Explorer");
  await title("Recording Explorer").waitFor();
  await choose("explorer_complete_recording", "bidmc_13");
  await choose("explorer_complete_channel", "RESP");
  await title("RESP · bidmc_13").waitFor();
  await chart("recording-trend", 2);
  const trend = page.locator(".st-key-recording-trend .js-plotly-plot");
  const checks = await trend.evaluate(el => ({
    gap: el.data[0].y.includes(null), line: el.data[0].connectgaps, marker: el.data[1].yaxis,
  }));
  assert.deepEqual(checks, { gap: true, line: false, marker: "y2" });
  await screenshot("recording-explorer");
  if (!walkthrough) {
    assert.deepEqual(errors, []);
    await page.close();
    return;
  }
  await page.locator(".st-key-explorer_complete_gaps label").click();
  await page.waitForFunction(() => document.querySelector(".st-key-recording-trend .js-plotly-plot")?.data?.length === 1);
  await page.getByRole("button", { name: "Reset filter" }).click();
  await title("HR · bidmc_01").waitFor();
  await page.locator(".st-key-explorer_complete_reset_1_compare_hr label").click();
  await title("HR + PULSE · bidmc_01").waitFor();
  await chart("recording-trend", 2);

  await nav("Big Data 5Vs Lab");
  await title("Benchmark Spark").waitFor();
  await page.getByText("Per percobaan", { exact: true }).click();
  await chart("volume-timing", 2);
  await screenshot("lab-volume");

  await lab("Velocity");
  await title("Historical Dataset Replay — Simulated IoT Ingestion").waitFor();
  await page.getByRole("button", { name: "Mulai replay" }).click();
  await page.getByText(/Diputar · \d+ \/ 6 batch/).waitFor();
  await page.getByRole("button", { name: "Jeda", exact: true }).click();
  const paused = page.getByText(/Dijeda · \d+ \/ 6 batch/);
  const held = await paused.textContent();
  await page.waitForTimeout(1250); // Longer than one recorded interval; paused position must not advance.
  assert.equal(await paused.textContent(), held);
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await page.getByText("Siap · 0 / 6 batch", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Langkah berikutnya" }).click();
  await page.getByText("Dijeda · 1 / 6 batch", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Mulai replay" }).click();
  await page.getByText("Selesai · 6 / 6 batch", { exact: true }).waitFor({ timeout: 12000 });
  await chart("replay-latency", 3);
  await screenshot("lab-velocity");

  await lab("Variety");
  await title("Dua representasi, satu recording_id").waitFor();
  await page.getByText("Metadata JSON dan contoh hasil join", { exact: true }).click();
  await choose("variety_rid", "bidmc_13");
  await screenshot("lab-variety");

  await lab("Veracity");
  await title("Sel hilang menurut kanal").waitFor();
  await page.locator(".st-key-quality_scenario").getByText("Fixture sintetis", { exact: true }).click();
  await title("Uji aturan validasi").waitFor();
  await page.getByText(/Fixture ini sengaja dibuat/).waitFor();
  await chart("fixture_issues");
  await screenshot("lab-veracity-fixture");
  await page.locator(".st-key-quality_scenario").getByText("Sumber PhysioNet", { exact: true }).click();
  await title("Sel hilang menurut kanal").waitFor();

  await lab("Value");
  await choose("value_channel", "SpO₂");
  await title("Rata-rata SpO₂ per recording").waitFor();
  await choose("value_rid_complete", "bidmc_13");
  await title("SpO₂ sepanjang bidmc_13").waitFor();
  await chart("value_trend");
  await screenshot("lab-value");

  await nav("System Architecture");
  await title("System Architecture").waitFor();
  await page.waitForFunction(() => document.querySelector(".vf-flow img")?.naturalWidth > 0);
  await choose("architecture_stage", "Penyimpanan Parquet");
  const [svg] = await Promise.all([
    page.waitForEvent("download"), page.getByRole("button", { name: "Unduh diagram SVG" }).click(),
  ]);
  assert.match(fs.readFileSync(await svg.path(), "utf8"), /<svg.*1040 318/s);
  await screenshot("architecture");

  await nav("Evidence & Methodology");
  await title("Evidence & Methodology").waitFor();
  await page.getByText("Inspeksi dan unduh artefak", { exact: true }).click();
  const [run] = await Promise.all([
    page.waitForEvent("download"), page.getByRole("button", { name: "Unduh berkas" }).click(),
  ]);
  assert.equal(JSON.parse(fs.readFileSync(await run.path(), "utf8")).recording_count, 53);
  await screenshot("evidence");
  assert.deepEqual(errors, []);
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ channel: process.env.VITALFLOW_QA_CHANNEL || "chrome" });
  try {
    await check(browser, 1440, 900, true);
    await check(browser, 1280, 720, false);
    await check(browser, 390, 844, false);
    console.log("All browser walkthrough checks passed.");
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
