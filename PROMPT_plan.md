0a. Study `specs/*` with up to 250 parallel Sonnet subagents to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md (if present) to understand the plan so far.
0c. Study `src/orion/data/*` with up to 250 parallel Sonnet subagents to understand the existing data layer (models, providers, cache).
0d. Study `src/orion/*` with up to 500 Sonnet subagents to understand what code already exists.
0e. For reference, the application source code is in `src/orion/*`.

1. Study @IMPLEMENTATION_PLAN.md (if present; it may be incorrect) and use up to 500 Sonnet subagents to study existing source code in `src/orion/*` and compare it against `specs/*`. Use an Opus subagent to analyze findings, prioritize tasks, and create/update @IMPLEMENTATION_PLAN.md as a bullet point list sorted in priority of items yet to be implemented. Ultrathink. Consider searching for TODO, minimal implementations, placeholders, skipped/flaky tests, and inconsistent patterns. Study @IMPLEMENTATION_PLAN.md to determine starting point for research and keep it up to date with items considered complete/incomplete using subagents.

IMPORTANT: Plan only. Do NOT implement anything. Do NOT assume functionality is missing; confirm with code search first. Treat `src/orion/data` as the project's standard library for shared utilities and components. The data layer (Phase 1-2) is complete - Quote, OptionChain, OHLCV, TechnicalIndicators, DataProvider interface, YahooFinanceProvider, AlphaVantageProvider, and CacheManager are all implemented. Focus planning on Phase 3+: Technical Analysis, Strategy Engine, Screening Orchestration, CLI/Storage, and Cloud Deployment.

ULTIMATE GOAL: We want to achieve a fully functional trading signals platform called Orion that implements the Option for Income (OFI) strategy. Consider missing elements and plan accordingly. If an element is missing, search first to confirm it doesn't exist, then if needed author the specification at specs/FILENAME.md. If you create a new element then document the plan to implement it in @IMPLEMENTATION_PLAN.md using a subagent.
