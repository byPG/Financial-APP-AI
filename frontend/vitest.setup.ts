import "@testing-library/jest-dom/vitest";

// jsdom has no EventSource implementation; PriceProvider only needs enough
// of the interface to mount without throwing in component tests that don't
// exercise live streaming.
class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;

  readyState = FakeEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(_url: string) {
    void _url;
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
}

// @ts-expect-error -- partial stub sufficient for tests
globalThis.EventSource = FakeEventSource;
