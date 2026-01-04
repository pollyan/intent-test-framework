import '@testing-library/jest-dom';
import { beforeAll, afterEach, afterAll } from 'vitest';
import { server } from './mocks/server';
import { cleanup } from '@testing-library/react';

// Establish API mocking before all tests.
beforeAll(() => server.listen());

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => {
    server.resetHandlers();
    cleanup();
});

// Clean up after the tests are finished.
afterAll(() => server.close());

// Polyfill for TextEncoder/TextDecoder if needed (Node 18+ usually has them)
// JSDOM environment might need this for MSW streaming response
if (typeof TextEncoder === 'undefined') {
    const { TextEncoder, TextDecoder } = require('util');
    global.TextEncoder = TextEncoder;
    global.TextDecoder = TextDecoder;
}

// Polyfill for ReadableStream
if (typeof ReadableStream === 'undefined') {
    const { ReadableStream } = require('stream/web');
    global.ReadableStream = ReadableStream;
}
