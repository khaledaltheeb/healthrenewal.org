"use strict";

const { test, expect } = require("@playwright/test");

test("provider platform boots without runtime errors and exposes semantic tabs", async ({ page }) => {
  const runtimeErrors = [];
  page.on("pageerror", error => runtimeErrors.push(error.message));

  await page.goto("/provider-assessment-demo/?release=2026.07.24-live.7#workspace", { waitUntil: "networkidle" });
  await expect(page.locator(".tabs")).toHaveAttribute("role", "tablist");

  const tabs = page.locator('.tab[data-view]');
  const tabCount = await tabs.count();
  expect(tabCount).toBeGreaterThanOrEqual(8);
  for (let index = 0; index < tabCount; index += 1) {
    const tab = tabs.nth(index);
    await expect(tab).toHaveAttribute("role", "tab");
    const controls = await tab.getAttribute("aria-controls");
    expect(controls).toBeTruthy();
    const panel = page.locator(`#${controls}`);
    await expect(panel).toHaveAttribute("role", "tabpanel");
    await expect(panel).toHaveAttribute("aria-labelledby", await tab.getAttribute("id"));
  }

  const protectedRows = page.locator("#professional-list .catalog-row");
  await expect(protectedRows.first()).toBeVisible();
  await expect(page.locator("#professional-list")).toContainText("مقفل");
  await expect(page.locator("#professional-list")).not.toContainText("مسار عمل متاح");

  expect(runtimeErrors).toEqual([]);
});
