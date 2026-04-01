import { test, expect, type Page } from '@playwright/test'

// Base URL comes from playwright.config.ts (use.baseURL).
// Helper API calls need a concrete URL — read it from the same env var / default.
const API = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5199'

// ── helpers ───────────────────────────────────────────────────────────────────

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function apiFetch(path: string, opts?: RequestInit) {
  const r = await fetch(`${API}${path}`, opts)
  return r.json()
}

async function createAction(text: string, extra: Record<string, string> = {}): Promise<number> {
  const data = await apiFetch('/actions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, ...extra }),
  })
  return data.id as number
}

async function deleteAction(id: number) {
  await fetch(`${API}/actions/${id}`, { method: 'DELETE' })
}

async function cleanupPW() {
  const data = await apiFetch('/actions')   // no done param → all
  for (const a of (data.actions ?? []) as { id: number; text: string }[]) {
    if (a.text.startsWith('PW ')) await deleteAction(a.id)
  }
}

function actionRow(page: Page, text: string) {
  return page.locator('[data-testid="action-item"]').filter({ hasText: text })
}

async function goToActions(page: Page) {
  await page.goto('/ui')
  await page.getByTestId('tab-bar').getByRole('button', { name: 'Actions' }).click()
  await page.waitForSelector('[data-testid="actions-page"]')
}

// ── suite ─────────────────────────────────────────────────────────────────────

test.beforeEach(async () => { await cleanupPW() })
test.afterEach(async ()  => { await cleanupPW() })

test.describe('List view', () => {
  test('open action is visible in list', async ({ page }) => {
    await createAction('PW list action')
    await goToActions(page)
    await expect(actionRow(page, 'PW list action')).toBeVisible()
  })

  test('All filter shows both open and done actions', async ({ page }) => {
    const openId  = await createAction('PW all-open')
    const doneId  = await createAction('PW all-done')
    await apiFetch(`/actions/${doneId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: true }),
    })

    await goToActions(page)
    await page.getByTestId('actions-page').getByRole('button', { name: 'All', exact: true }).click()
    await expect(actionRow(page, 'PW all-open')).toBeVisible()
    await expect(actionRow(page, 'PW all-done')).toBeVisible()

    await deleteAction(openId)
    await deleteAction(doneId)
  })

  test('Done filter shows completed action', async ({ page }) => {
    const id = await createAction('PW done action')
    await apiFetch(`/actions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: true }),
    })

    await goToActions(page)
    await page.getByTestId('actions-page').getByRole('button', { name: 'Done' }).click()
    await expect(actionRow(page, 'PW done action')).toBeVisible()
    await deleteAction(id)
  })

  test('can set deadline on an action', async ({ page }) => {
    await createAction('PW deadline action')
    await goToActions(page)
    const row = actionRow(page, 'PW deadline action')
    await row.hover()
    await row.getByRole('button', { name: 'Set deadline' }).click()
    await row.locator('input[type="date"]').fill(todayStr())
    await row.locator('input[type="date"]').press('Enter')
    await expect(row.getByText(/Due:/)).toBeVisible()
  })

  test('can mark action done via checkbox', async ({ page }) => {
    await createAction('PW toggle done')
    await goToActions(page)
    const row = actionRow(page, 'PW toggle done')
    await row.getByRole('checkbox').click()
    // Should disappear from Open tab
    await expect(row).not.toBeVisible()
  })
})

test.describe('New action form', () => {
  test('adds action from list view', async ({ page }) => {
    await goToActions(page)
    await page.getByRole('button', { name: 'New Action' }).click()
    await page.getByPlaceholder('What needs to be done?').fill('PW form action')
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/actions') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Add' }).click(),
    ])
    // Wait for loadActions GET (triggered after POST succeeds)
    await page.waitForResponse(r => r.url().includes('/actions') && r.request().method() === 'GET')
    await expect(actionRow(page, 'PW form action')).toBeVisible({ timeout: 5000 })
  })

  test('new action form accepts a deadline', async ({ page }) => {
    await goToActions(page)
    await page.getByRole('button', { name: 'New Action' }).click()
    await page.getByPlaceholder('What needs to be done?').fill('PW form deadline')
    await page.locator('input[type="date"]').fill(todayStr())
    await page.getByRole('button', { name: 'Add' }).click()
    await expect(actionRow(page, 'PW form deadline')).toBeVisible()
    await expect(page.getByText(`Due: ${todayStr()}`)).toBeVisible()
  })
})

test.describe('Calendar view', () => {
  test('renders month grid with weekday headers', async ({ page }) => {
    await goToActions(page)
    await page.getByRole('button', { name: 'Calendar' }).click()
    for (const d of ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']) {
      await expect(page.getByText(d).first()).toBeVisible()
    }
    await expect(page.getByRole('button', { name: 'Today' })).toBeVisible()
  })

  test('action with due_date appears on the correct calendar day', async ({ page }) => {
    await createAction('PW cal chip', { due_date: todayStr() })
    await goToActions(page)
    await page.getByRole('button', { name: 'Calendar' }).click()
    await expect(page.getByText('PW cal chip')).toBeVisible({ timeout: 8000 })
  })

  test('clicking a day pre-fills date in the new action form', async ({ page }) => {
    await goToActions(page)
    await page.getByRole('button', { name: 'Calendar' }).click()
    const dayNum = new Date().getDate()
    // Click a day cell (not a nav button or header)
    await page.locator('[role="button"][aria-label]')
      .filter({ hasText: String(dayNum) })
      .first()
      .click()
    await expect(page.getByPlaceholder('What needs to be done?')).toBeVisible()
    await expect(page.locator('input[type="date"]')).toHaveValue(todayStr())
  })

  test('can add action from calendar and it appears as a chip', async ({ page }) => {
    await goToActions(page)
    await page.getByRole('button', { name: 'Calendar' }).click()
    const dayNum = new Date().getDate()
    await page.locator('[role="button"][aria-label]')
      .filter({ hasText: String(dayNum) })
      .first()
      .click()
    await page.getByPlaceholder('What needs to be done?').fill('PW cal add')
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/actions') && r.request().method() === 'POST'),
      page.getByRole('button', { name: 'Add' }).click(),
    ])
    await expect(page.getByText('PW cal add')).toBeVisible({ timeout: 8000 })
  })

  test('toggling a calendar chip shows strikethrough, not removes it', async ({ page }) => {
    await createAction('PW cal toggle', { due_date: todayStr() })
    await goToActions(page)
    await Promise.all([
      page.waitForResponse(r => r.url().includes('/actions') && r.url().includes('limit=') && r.request().method() === 'GET'),
      page.getByRole('button', { name: 'Calendar' }).click(),
    ])
    const chip = page.getByText('PW cal toggle')
    await expect(chip).toBeVisible({ timeout: 5000 })
    // Click the checkbox (Mark done) button, not the text button
    const chipContainer = chip.locator('..')
    await chipContainer.getByRole('button', { name: 'Mark done' }).click()
    // Text button still visible but with strikethrough
    await expect(chip).toBeVisible()
    await expect(chip).toHaveClass(/line-through/)
  })

  test('month navigation prev/next', async ({ page }) => {
    await goToActions(page)
    await page.getByRole('button', { name: 'Calendar' }).click()
    const cal = page.getByTestId('actions-page')
    const today = new Date()
    const curMonth = today.toLocaleString('default', { month: 'long', year: 'numeric' })
    await expect(cal.getByText(curMonth)).toBeVisible()
    await page.getByLabel('Next month').click()
    await expect(cal.getByText(curMonth)).not.toBeVisible()
    await page.getByLabel('Previous month').click()
    await expect(cal.getByText(curMonth)).toBeVisible()
  })
})

test.describe('Assignee', () => {
  test('assign picker appears on hover when people exist', async ({ page }) => {
    const personsData = await apiFetch('/persons')
    if ((personsData.people ?? []).length === 0) {
      test.skip()
      return
    }
    await createAction('PW assignee action')
    await goToActions(page)
    const row = actionRow(page, 'PW assignee action')
    await row.hover()
    await expect(row.getByRole('button', { name: 'Assign', exact: true })).toBeVisible()
  })

  test('can assign action to a person', async ({ page }) => {
    const personsData = await apiFetch('/persons')
    const people = personsData.people ?? []
    if (people.length === 0) { test.skip(); return }
    const person = people[0] as { title: string }

    await createAction('PW assign person')
    await goToActions(page)
    const row = actionRow(page, 'PW assign person')
    await row.hover()
    await row.getByRole('button', { name: 'Assign', exact: true }).click()
    // Radix Select opens a popover — click the person option inside it
    await page.getByRole('option', { name: person.title }).click()
    // Person name should now appear in the row
    await expect(row.getByText(person.title)).toBeVisible()
  })
})
