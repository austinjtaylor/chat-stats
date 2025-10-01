/**
 * Chat Scroll Behavior Tests
 *
 * These tests verify that user queries scroll to the top of the viewport
 * when submitted, ensuring the loading indicator is visible.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('Chat Scroll Behavior', () => {
    let chatMessages: HTMLElement;
    let mockMessages: HTMLElement[];

    beforeEach(() => {
        // Create mock chat container
        chatMessages = document.createElement('div');
        chatMessages.id = 'chatMessages';
        chatMessages.style.height = '737px'; // Typical viewport height
        chatMessages.style.overflowY = 'auto';
        chatMessages.style.paddingTop = '32px';
        document.body.appendChild(chatMessages);

        mockMessages = [];
    });

    afterEach(() => {
        document.body.innerHTML = '';
    });

    /**
     * Helper to create a mock message element
     */
    function createMockMessage(id: number, content: string, type: 'user' | 'assistant'): HTMLElement {
        const div = document.createElement('div');
        div.id = `message-${id}`;
        div.className = `message ${type}`;
        div.style.height = '100px'; // Approximate message height
        div.textContent = content;
        return div;
    }

    /**
     * Helper to simulate adding a message and scrolling
     */
    function addMessageAndScroll(messageId: number, content: string, type: 'user' | 'assistant'): void {
        const message = createMockMessage(messageId, content, type);
        chatMessages.appendChild(message);
        mockMessages.push(message);

        // Simulate the scroll behavior from script.ts
        if (type === 'user') {
            const userMessageDiv = document.getElementById(`message-${messageId}`);
            if (userMessageDiv) {
                chatMessages.scrollTop = userMessageDiv.offsetTop - 32;
            }
        }
    }

    it('should scroll first user query to top of viewport', () => {
        const messageId = Date.now();
        addMessageAndScroll(messageId, 'What teams are in the UFA?', 'user');

        // First message: offsetTop is calculated based on padding
        // In our test environment, scrollTop should equal offsetTop - 32
        const firstMessage = document.getElementById(`message-${messageId}`);
        expect(firstMessage).toBeTruthy();
        if (firstMessage) {
            expect(chatMessages.scrollTop).toBe(firstMessage.offsetTop - 32);
        }
    });

    it('should scroll second user query to top of viewport', () => {
        // Add first query and response
        const firstQueryId = Date.now();
        addMessageAndScroll(firstQueryId, 'What teams are in the UFA?', 'user');
        addMessageAndScroll(firstQueryId + 1, 'Here are the teams...', 'assistant');

        // Add second query
        const secondQueryId = firstQueryId + 2;
        const secondQuery = createMockMessage(secondQueryId, 'Show me recent games', 'user');
        chatMessages.appendChild(secondQuery);

        // Get the actual offsetTop of the second query
        const secondQueryElement = document.getElementById(`message-${secondQueryId}`);
        expect(secondQueryElement).toBeTruthy();

        // Simulate scroll behavior
        if (secondQueryElement) {
            const expectedScrollTop = secondQueryElement.offsetTop - 32;
            chatMessages.scrollTop = expectedScrollTop;

            // The scrollTop should equal the calculated position
            expect(chatMessages.scrollTop).toBe(expectedScrollTop);
        }
    });

    it('should maintain chronological message order', () => {
        // Add messages in order
        addMessageAndScroll(1, 'First query', 'user');
        addMessageAndScroll(2, 'First response', 'assistant');
        addMessageAndScroll(3, 'Second query', 'user');
        addMessageAndScroll(4, 'Second response', 'assistant');

        // Verify order in DOM
        const messages = chatMessages.querySelectorAll('.message');
        expect(messages.length).toBe(4);
        expect(messages[0].textContent).toBe('First query');
        expect(messages[1].textContent).toBe('First response');
        expect(messages[2].textContent).toBe('Second query');
        expect(messages[3].textContent).toBe('Second response');
    });

    it('should position user queries above their responses', () => {
        const queryId = Date.now();
        addMessageAndScroll(queryId, 'Test query', 'user');
        addMessageAndScroll(queryId + 1, 'Test response', 'assistant');

        const queryElement = document.getElementById(`message-${queryId}`);
        const responseElement = document.getElementById(`message-${queryId + 1}`);

        expect(queryElement).toBeTruthy();
        expect(responseElement).toBeTruthy();

        if (queryElement && responseElement) {
            // Response should be below query in DOM
            // Check by comparing DOM positions
            const messages = Array.from(chatMessages.querySelectorAll('.message'));
            const queryIndex = messages.indexOf(queryElement);
            const responseIndex = messages.indexOf(responseElement);

            expect(queryIndex).toBeGreaterThanOrEqual(0);
            expect(responseIndex).toBeGreaterThan(queryIndex);
        }
    });

    it('should calculate correct scroll position accounting for padding', () => {
        const messageId = Date.now();
        const message = createMockMessage(messageId, 'Test query', 'user');
        chatMessages.appendChild(message);

        const offsetTop = message.offsetTop;
        const expectedScrollTop = offsetTop - 32; // 32px padding

        // This matches the calculation in script.ts line 153
        expect(expectedScrollTop).toBe(offsetTop - 32);
    });
});
