# Search V2 references and authorship boundary

Consulted official project descriptions on 2026-09-08. No engine implementation or network was downloaded, copied, translated or ported for this work.

- [Berserk README](https://github.com/jhonnold/berserk): its functional checklist includes staged generation, PVS, quiescence, TT, aspiration, IIR, null move, futility families, SEE, LMR, history and extensions. Use this as an inventory of questions for our own search, not a requirement to add every feature.
- [Ethereal README](https://github.com/AndyGrant/Ethereal): describes alpha-beta plus neural evaluation, emphasizes readable architecture, and identifies OpenBench as its testing platform. The applicable lesson is disciplined isolated testing. Its source licensing does not override competition authorship restrictions.
- [Viridithas README](https://github.com/cosmobobak/viridithas): describes its evaluation-development history and original self-play data. The applicable lesson is retaining data/model provenance and measuring successive versions. Its neural networks and source are not inputs to this project.
- [Competition rules](https://aichessathon.com/docs/rules.md) and [agent contract](https://aichessathon.com/docs/agent-contract.md): canonical packaging/runtime restrictions. Browser fetch returned an error; direct retrieval subsequently succeeded. Fresh copies are competition_rules_20260908.md and agent_contract_20260908.md in this directory. Refresh again before eventual packaging.

All Search V2 implementations must be our own Python/Numba over our own board/search code. Offline Stockfish labeling and opposition stay outside the shipped runtime. No published model, engine binary, engine-derived lookup table or runtime external-engine process is permitted by the standing project scope. No cross-engine Elo or depth mapping is assumed.
