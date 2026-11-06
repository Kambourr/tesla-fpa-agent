import { describe, expect, it } from "vitest";
import { hashForView, initialView, viewFromHashChange } from "./hashView";

describe("hash views", () => {
  it("treats a missing hash, a slash, and /overview as Overview", () => {
    expect(initialView("")).toBe("overview");
    expect(initialView("#")).toBe("overview");
    expect(initialView("#/")).toBe("overview");
    expect(initialView("#/overview")).toBe("overview");
  });

  it("maps each destination and the old section anchors", () => {
    expect(viewFromHashChange("#/bridge")).toBe("bridge");
    expect(viewFromHashChange("#/memo")).toBe("memo");
    expect(viewFromHashChange("#/forecast")).toBe("forecast");
    expect(viewFromHashChange("#/accuracy")).toBe("accuracy");
    expect(viewFromHashChange("#/ask")).toBe("ask");
    expect(viewFromHashChange("#/method")).toBe("method");
    expect(viewFromHashChange("#method-title")).toBe("method");
    expect(viewFromHashChange("#analyst-memo-title")).toBe("memo");
    expect(viewFromHashChange("#forecast-heading")).toBe("forecast");
    expect(viewFromHashChange("#accuracy-heading")).toBe("accuracy");
    expect(viewFromHashChange("#ask-heading")).toBe("ask");
  });

  it("does not treat About as a view switch", () => {
    expect(viewFromHashChange("#about-title")).toBeNull();
    expect(initialView("#about-title")).toBe("overview");
  });

  it("writes a shareable hash for each view", () => {
    expect(hashForView("overview")).toBe("#/overview");
    expect(hashForView("method")).toBe("#/method");
  });
});
