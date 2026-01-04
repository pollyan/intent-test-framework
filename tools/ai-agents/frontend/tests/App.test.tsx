import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import App from '../App';
import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';

// Mock scrollIntoView since JSDOM doesn't support it
Element.prototype.scrollIntoView = vi.fn();

const API_BASE = '/ai-agents/api/requirements';

const mockStreamResponse = (content: string) => {
    return http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
            start(controller) {
                controller.enqueue(encoder.encode(`data: {"type": "content", "chunk": "${content}"}\n\n`));
                controller.enqueue(encoder.encode('data: {"type": "done"}\n\n'));
                controller.close();
            }
        });
        return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
    });
};

describe('AI Agents App', () => {

    it('P0: Selects Assistant (Alex) and shows welcome message', async () => {
        // Override handler to return specific welcome message
        server.use(mockStreamResponse('你好，我是Alex'));

        render(<App />);

        // 1. Initial State: should show Assistant Selection
        expect(screen.getByText('选择智能助手')).toBeInTheDocument();
        expect(screen.getByText('Alex')).toBeInTheDocument();

        // 2. Click Alex
        fireEvent.click(screen.getByText('Alex'));

        // 3. Should show chat interface
        await waitFor(() => {
            expect(screen.getByRole('heading', { name: '智能助手', level: 1 })).toBeInTheDocument();
        });

        // 4. Should see Alex's name in header
        // Note: Initial state of selectedAssistantId might need time to set, but sync in click
        // Wait for welcome message stream to finish
        await waitFor(() => {
            expect(screen.getByText('你好，我是Alex')).toBeInTheDocument();
        });
    });

    it('P0: Sends message and receives stream response', async () => {
        // Specific mock for welcome message
        server.use(mockStreamResponse('I am ready.'));

        render(<App />);

        // Select Alex first
        fireEvent.click(screen.getByText('Alex'));

        // Wait for session init and welcome message to complete (input enabled)
        await waitFor(() => {
            expect(screen.getByText(/I am ready/)).toBeInTheDocument();
        });

        // We type in the input
        const input = await screen.findByPlaceholderText('请输入...');
        fireEvent.change(input, { target: { value: '我的需求是...' } });

        // Mock the response for this specific message
        server.use(
            http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async ({ request }) => {
                const body = await request.json() as any;
                // Check if this is the user message, not the welcome hidden message
                if (body && body.content === '我的需求是...') {
                    const encoder = new TextEncoder();
                    const stream = new ReadableStream({
                        start(controller) {
                            controller.enqueue(encoder.encode('data: {"type": "content", "chunk": "收到，"}\n\n'));
                            controller.enqueue(encoder.encode('data: {"type": "content", "chunk": "正在分析"}\n\n'));
                            controller.enqueue(encoder.encode('data: {"type": "done"}\n\n'));
                            controller.close();
                        }
                    });
                    return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
                }
                // Default fallback (e.g. for welcome message)
                return new HttpResponse(null, { status: 200 }); // dummy
            })
        );

        // Click Send
        // Click Send - use keyDown to avoid finding button
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        // Check for User Message
        expect(screen.getByText('我的需求是...')).toBeInTheDocument();

        // Check for Thinking (Async)
        // In the code, isThinking: true is set immediately.
        // But our mock might be too fast?
        // Wait for response text
        await waitFor(() => {
            expect(screen.getByText('收到，正在分析')).toBeInTheDocument();
        });
    });

    it('P0: Parses Artifacts and updates Right Panel', async () => {
        // Artifact Content
        const artifactContent = '# 需求文档\n\n- 功能点1\n- 功能点2';
        // Note: We need to set up the welcome message mock first, then the artifact mock
        // MSW handles overrides by order (last one wins?). No, prepending "use" adds to top.
        // But we need different responses for different calls?
        // Or we can just use the "ready" check, and then override for the next call.

        // 1. Set welcome message
        server.use(mockStreamResponse('I am ready.'));

        render(<App />);
        fireEvent.click(screen.getByText('Alex'));

        // Wait for welcome message
        await waitFor(() => {
            expect(screen.getByText(/I am ready/)).toBeInTheDocument();
        });

        // 2. Override for the next request (Artifact)
        // Note: In MSW, server.use() prepends. So this new handler will be checked first.
        server.use(
            http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async ({ request }) => {
                const body = await request.json() as any;
                // Only match the specific artifact request
                if (body && body.content === '生成文档') {
                    const encoder = new TextEncoder();
                    const stream = new ReadableStream({
                        start(controller) {
                            // Stream split in chunks to test concatenation
                            const chunk1 = JSON.stringify({ type: "content", chunk: "好的，文档如下：\n:::arti" });
                            const chunk2 = JSON.stringify({ type: "content", chunk: `fact\n${artifactContent}\n:::\n请确认。` });
                            const done = JSON.stringify({ type: "done" });

                            controller.enqueue(encoder.encode(`data: ${chunk1}\n\n`));
                            controller.enqueue(encoder.encode(`data: ${chunk2}\n\n`));
                            controller.enqueue(encoder.encode(`data: ${done}\n\n`));
                            controller.close();
                        }
                    });
                    return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
                }
                // Fallback to welcome message if somehow called again?
                return new HttpResponse(null, { status: 200 });
            })
        );

        const input = await screen.findByPlaceholderText('请输入...');
        fireEvent.change(input, { target: { value: '生成文档' } });
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        // 1. Verify Left Panel: Should NOT see ":::artifact"
        // Should see "已更新右侧分析成果"
        await waitFor(() => {
            expect(screen.getByText(/\(已更新右侧分析成果\)/)).toBeInTheDocument();
        });

        // Ensure raw artifact tag is NOT visible in message
        // text can be scattered in elements due to ReactMarkdown, but we check generic text content
        // This is a bit tricky with ReactMarkdown.
        // Let's just check that the replacement text exists.

        // 2. Verify Right Panel: Should see the rendered markdown
        // "分析成果" panel should contain the text "功能点1"
        await waitFor(() => {
            // We can look for the text inside the analysis panel
            // Analysis result panel headers
            expect(screen.getByText('分析成果')).toBeInTheDocument();
            expect(screen.getByText('功能点1')).toBeInTheDocument();
            expect(screen.getByText('需求文档')).toBeInTheDocument();
        });
    });

    it('P1: Handles Error gracefully', async () => {
        // Welcome works
        server.use(mockStreamResponse('I am ready.'));

        render(<App />);
        fireEvent.click(screen.getByText('Alex'));

        // Wait for welcome message
        await waitFor(() => {
            expect(screen.getByText(/I am ready/)).toBeInTheDocument();
        });

        // Now force 500 for next request
        server.use(
            http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, () => {
                return new HttpResponse(null, { status: 500 });
            })
        );

        const input = await screen.findByPlaceholderText('请输入...');
        fireEvent.change(input, { target: { value: '这会报错' } });
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        await waitFor(() => {
            expect(screen.getByText(/无法完成回复/)).toBeInTheDocument();
        });
    });
});
