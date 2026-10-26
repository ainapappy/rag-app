import { describe, expect, it } from "vitest";

import { createSseParser } from "./sse";

describe("createSseParser", () => {
  it("découpe plusieurs événements d'un même chunk", () => {
    const parser = createSseParser();
    const events = parser.push(
      'event: token\ndata: {"t":"a"}\n\nevent: done\ndata: {"id":1}\n\n',
    );
    expect(events).toEqual([
      { event: "token", data: '{"t":"a"}' },
      { event: "done", data: '{"id":1}' },
    ]);
  });

  it("gère un chunk coupé au milieu d'un événement", () => {
    const parser = createSseParser();
    expect(parser.push("event: sour")).toEqual([]);
    expect(parser.push('ces\ndata: [{"source":"a.pdf"}]\n')).toEqual([]);
    const events = parser.push("\n");
    expect(events).toEqual([{ event: "sources", data: '[{"source":"a.pdf"}]' }]);
  });

  it("ignore les blocs sans data", () => {
    const parser = createSseParser();
    const events = parser.push("event: token\n\nevent: done\ndata: {}\n\n");
    expect(events).toEqual([{ event: "done", data: "{}" }]);
  });

  it("transmet les événements error tels quels", () => {
    const parser = createSseParser();
    const events = parser.push('event: error\ndata: {"message":"LLM down"}\n\n');
    expect(events).toEqual([{ event: "error", data: '{"message":"LLM down"}' }]);
  });
});
