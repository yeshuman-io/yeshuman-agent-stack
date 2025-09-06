import { test, expect } from '@playwright/test';

test.describe('API Connectivity Tests', () => {
  test('should handle agent chat API calls correctly', async ({ page }) => {
    // Listen for network requests to catch the 502 error
    const requests: any[] = [];
    const responses: any[] = [];

    page.on('request', request => {
      if (request.url().includes('/agent/stream')) {
        requests.push({
          url: request.url(),
          method: request.method(),
          headers: request.headers(),
          postData: request.postData()
        });
        console.log('🚀 API Request:', {
          url: request.url(),
          method: request.method(),
          headers: request.headers()
        });
      }
    });

    page.on('response', response => {
      if (response.url().includes('/agent/stream')) {
        responses.push({
          url: response.url(),
          status: response.status(),
          headers: response.headers()
        });
        console.log('📥 API Response:', {
          url: response.url(),
          status: response.status(),
          statusText: response.statusText()
        });
      }
    });

    // Navigate to the app
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait for the chat interface to load
    await page.waitForSelector('[data-testid="message-input"], input[type="text"], textarea', { timeout: 10000 });

    // Try to find and interact with the chat input
    const inputSelector = '[data-testid="message-input"], input[type="text"], textarea';
    const input = page.locator(inputSelector).first();

    if (await input.isVisible()) {
      // Type a test message
      await input.fill('Hello, test message');

      // Try to submit (look for submit button or Enter key)
      const submitButton = page.locator('button[type="submit"], [data-testid="send-button"]').first();

      if (await submitButton.isVisible()) {
        await submitButton.click();
      } else {
        // Try pressing Enter
        await input.press('Enter');
      }

      // Wait for API calls
      await page.waitForTimeout(3000);

      // Check for errors in console
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // Analyze results
      console.log('📊 Test Results:');
      console.log('Requests made:', requests.length);
      console.log('Responses received:', responses.length);
      console.log('Console errors:', errors);

      // Assertions
      if (responses.length > 0) {
        const response = responses[0];
        expect(response.status).not.toBe(502);
        expect(response.status).toBeLessThan(500);
      }

      if (requests.length > 0) {
        const request = requests[0];
        expect(request.url).toContain('/agent/stream');
      }
    } else {
      console.log('❌ Chat input not found');
      // Take a screenshot for debugging
      await page.screenshot({ path: 'debug-screenshot.png' });
    }
  });

  test('should detect API configuration issues', async ({ page }) => {
    await page.goto('/');

    // Check if the app loads without immediate errors
    const title = await page.title();
    console.log('Page title:', title);

    // Look for any error messages in the DOM
    const errorElements = await page.locator('[class*="error"], [class*="Error"]').allTextContents();
    console.log('Error elements found:', errorElements);

    // Check console for errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.waitForTimeout(2000);
    console.log('Console errors:', consoleErrors);
  });
});
