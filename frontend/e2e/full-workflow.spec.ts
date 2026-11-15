import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import type { Investigation } from '../src/types/incidents'

// Resolve the project data directory correctly in ES modules.
const specDir = path.dirname(fileURLToPath(import.meta.url))
const SAMPLES = path.resolve(specDir, '../../data')

const unique = `e2e-${Date.now()}@example.com`

test(
  'register -> upload logs -> detect -> incident -> AI (mocked) -> RAG -> report -> resolve -> logout',
  async ({ page }) => {
    // Store the mocked investigation so the subsequent GET request
    // returns it as latest_investigation.
    let mockedInvestigation: Investigation | null = null

    const mockResult: Investigation['result'] = {
      incident_summary: 'Mocked summary',

      observed_symptoms: [
        {
          text: 'Mocked symptom',
          evidence: ['E1'],
        },
      ],

      potential_contributing_factors: [],
      suspected_root_causes: [],
      recommended_investigation: [],
      relevant_historical_incidents: [],
      relevant_documentation: [],

      confidence: 'low',
      limitations: ['mock'],

      evidence: [
        {
          id: 'E1',
          kind: 'log',
          text: 'mock evidence',
        },
      ],

      status: 'AI-generated suggestion - not human-confirmed',
      validation_notes: [],
    }

    // Intercept incident detail GET requests.
    // The actual backend still provides the incident data.
    await page.route(
      (url) => /\/incidents\/\d+$/.test(url.pathname),
      async (route) => {
        if (route.request().method() !== 'GET') {
          await route.continue()
          return
        }

        const response = await route.fetch()

        if (!response.ok()) {
          await route.fulfill({ response })
          return
        }

        const incident = await response.json()

        if (mockedInvestigation) {
          incident.latest_investigation = mockedInvestigation
        }

        await route.fulfill({
          response,
          json: incident,
        })
      },
    )

    // Intercept the AI investigation POST request.
    await page.route(
      '**/incidents/*/investigate',
      async (route) => {
        const url = new URL(route.request().url())

        const match = url.pathname.match(
          /\/incidents\/(\d+)\/investigate$/,
        )

        if (!match) {
          await route.continue()
          return
        }

        const incidentId = Number(match[1])

        const requestBody = route.request().postDataJSON() as {
          question?: string | null
        }

        mockedInvestigation = {
          id: 1,
          incident_id: incidentId,
          question: requestBody.question ?? '',
          status: 'COMPLETED',
          provider: 'mock',
          result: mockResult,
          error_code: null,
          error_message: null,
          created_at: new Date().toISOString(),
        }

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockedInvestigation),
        })
      },
    )

    // 1-2. Register a new user.
    await page.goto('/register')

    await page.getByLabel('Full name').fill('E2E User')
    await page.getByLabel('Email').fill(unique)

    await page
      .getByLabel('Password', { exact: true })
      .fill('E2ePassw0rd')

    await page
      .getByLabel('Confirm password')
      .fill('E2ePassw0rd')

    await page
      .getByRole('button', { name: 'Create account' })
      .click()

    await expect(
      page.getByRole('heading', { name: 'Overview' }),
    ).toBeVisible()

    // 3-4. Upload the synthetic incident log.
    await page.getByRole('link', { name: 'Logs' }).click()

    await page
      .getByLabel('Log file')
      .setInputFiles(
        path.join(
          SAMPLES,
          'sample_logs',
          'incident_payment_failure.log',
        ),
      )

    // Target the actual status badge.
    await expect(
      page.getByRole('cell', { name: 'COMPLETED' }).locator('span'),
    ).toBeVisible({ timeout: 30_000 })

    // 5-6. Run anomaly detection.
    await page.getByRole('link', { name: 'Anomalies' }).click()

    await page
      .getByRole('button', { name: 'Run anomaly detection' })
      .click()

    await expect(
      page.getByText(/Incidents created: 1/),
    ).toBeVisible({ timeout: 30_000 })

    // 7-9. Open the incident and inspect its details.
    await page
      .getByRole('link', { name: /^INC-/ })
      .first()
      .click()

    await expect(
      page.getByText('Severity explanation (rule-based)'),
    ).toBeVisible()

    await expect(
      page.getByText('Related incidents'),
    ).toBeVisible()

    // 10. AI investigation (mocked).
    await page
      .getByRole('button', { name: 'Investigate' })
      .click()

    await expect(
      page.getByText('Mocked summary'),
    ).toBeVisible({ timeout: 10_000 })

    await expect(
      page.getByText(/not confirmed findings/),
    ).toBeVisible()

    // 11-13. Upload a runbook and test RAG.
    await page
      .getByRole('link', { name: 'Documents' })
      .click()

    await page
      .getByLabel('Document file')
      .setInputFiles(
        path.join(
          SAMPLES,
          'sample_documents',
          'payment_service_runbook.md',
        ),
      )

    // Target the actual document status badge.
    await expect(
      page.getByRole('cell', { name: 'COMPLETED' }).locator('span'),
    ).toBeVisible({ timeout: 30_000 })

    await page
      .getByRole('link', { name: 'Assistant' })
      .click()

    await page
      .getByLabel('Question')
      .fill('payment failed gateway timeout circuit breaker')

    await page
      .getByRole('button', { name: 'Ask' })
      .click()

    await expect(
      page.getByLabel('Sources'),
    ).toContainText('payment_service_runbook.md')

    // 14. Generate a PDF report.
    await page
      .getByRole('link', { name: 'Incidents' })
      .click()

    await page
      .getByRole('link', { name: /^INC-/ })
      .first()
      .click()

    const downloadPromise = page.waitForEvent('download')

    await page
      .getByRole('button', { name: 'pdf', exact: true })
      .click()

    const download = await downloadPromise

    expect(download.suggestedFilename()).toMatch(/\.pdf$/)

    // 15. Update the incident status.
    await page
      .getByRole('button', { name: 'Mark INVESTIGATING' })
      .click()

    await page
      .getByRole('button', { name: 'Mark RESOLVED' })
      .click()

    await expect(
      page.getByText('RESOLVED', { exact: true }).first(),
    ).toBeVisible()

    // 16. Logout.
    await page
      .getByRole('button', { name: 'Log out' })
      .click()

    await expect(
      page.getByRole('heading', {
        name: 'Sign in to your account',
      }),
    ).toBeVisible()
  },
)

test(
  'protected pages redirect anonymous visitors to the login page',
  async ({ page }) => {
    await page.goto('/incidents')

    await expect(page).toHaveURL(/\/login/)
  },
)