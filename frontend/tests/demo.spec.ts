import { expect, test } from "@playwright/test";

test("demo flow runs two attempts and finalizes after approval", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /alphagraph/i })).toBeVisible();
  await page.getByRole("button", { name: /run demo/i }).click();

  await expect(page.getByText(/attempt 1/i)).toBeVisible();
  await expect(page.getByText(/attempt 2/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /approve result/i })).toBeVisible();

  await page.getByRole("button", { name: /approve result/i }).click();

  await expect(page.getByText(/status/i)).toContainText(/completed/i);
  await expect(page.getByText(/final artifact bundle/i)).toBeVisible();
});
