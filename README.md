# BHARAT-SHIELD

Strategic Hydrocarbon Intelligence and Emergency Logistics Directive Platform.

## Track Flow & Development History

### Phase 1: Core Architecture & Data Pipelines (COMPLETED)
- **Initialized project directory structure**: `backend/app`, `frontend/src`, etc.
- **Environment**: Set up Python virtual environment and installed dependencies (FastAPI, Pyomo, Pandas, BeautifulSoup, Searoute, LangChain).
- **Agent 1 [NETRA - Risk Sentinel]**: Implemented UKMTO and GDELT scrapers, plus Event-Graph Memory with temporal decay for maritime intelligence.
- **Agent 2 [MARG - Logistics & Macro Quant]**: Added IMF PortWatch fetcher, VECM price & GDP/inflation shock model, Dead-Reckoning vessel tracking, and SPM/pipeline bottleneck constraints.
- **Agent 3 [RASAYAN - Chemical Metallurgy & LNG Trader]**: Integrated `searoute` for maritime routing, 22-grade crude assay matching with Asphaltene Instability Index (AII), and Wobbe index LNG matching.
- **Agent 4 [KOSH - Reserve Governor]**: Built Pyomo MILP solver for Two-Tier Strategic Petroleum Reserve (ISPRL Phase I/II + OMC) drawdown optimization and gas grid balancing.
- **Main App**: Built FastAPI skeleton endpoints.

### Phase 2: Solvers, Refinery Logic & Policy Switch Integration (COMPLETED)
- [x] Implement Agent 3 [RASAYAN] crude assay matching algorithm in Pandas.
- [x] Integrate SPM port discharge limits and pipeline throughput constraints in Agent 2 [MARG].
- [x] Wire FastAPI endpoints to execute the agent chain sequentially.

### Phase 3: Frontend & Audit Package (COMPLETED + ENHANCED)
- **Deck.gl & React UI**: Built a mesmerizing dark-mode frontend featuring interactive map layers and Framer Motion transitions.
- **Controls & Simulation**: Integrated chat-driven simulation, search for Intel Feed and PortWatch.
- **Agent 5 [KAUTILYA - Strategic Audit & War Room]**: Implemented cryptographic hashing (`generate_audit_package`) to produce a verified execution ledger (JSON + CSV) and SQLite session snapshots.
- **Agent 6 [CHAKRA - Red Team Adversarial Critic]**: Added vulnerability assessment, refinery run-rate degradation calculator, and product rationing horizon warnings.
- **Dynamic Map Focus (Fly-To)**: After each simulation, the map camera smoothly flies to the target port using `FlyToInterpolator`.
- **Live Maritime Route Arc**: After simulation, a `ArcLayer` draws the crude shipping route from Ras Tanura (Middle East) to the target Indian port, with distance shown in nautical miles.
- **Animated Pulsing Chokepoints**: Bab-el-Mandeb, Suez Canal, Strait of Hormuz, and Malacca pulse in red with real-time risk percentage bars.
- **KPI Status Bar**: 5 live KPI chips at the top of the map (Deficit, Refinery, Best Crude, Port, Route Distance) update on every simulation.
- **Hover Tooltips on Map**: Hovering over any port or chokepoint shows a floating tooltip card.
- **`.env` API Key Config**: Backend now loads from `C:\BHARAT\backend\.env`. Set `OPENAI_API_KEY` there to enable LLM-powered scenario parsing.
### Phase 4: Natural Gas Extension + Deep Strengthening (COMPLETED)
- **`agent3_gas_trader.py`**: Full LNG terminal DB (6 Indian terminals), 8-supplier LNG catalogue, Wobbe Index/methane matching, regasification headroom distribution.
- **`agent4_gas_governor.py`**: Pyomo MILP solver for gas supply across LNG terminals + domestic field fallback (ONGC, Reliance).
- **`shared_models.py`**: Risk(t) decay model `α·Severity·e^(−λ·Δt)`, VECM price shock stub, Cape of Good Hope rerouting by vessel type.
- **`assays.json`**: Expanded crude assay DB — 20 real global grades with API, Sulfur, TAN, yield curves, Brent differentials.
- **`isprl_data.json`**: ISPRL cavern fill levels, daily drawdown limits, OMC stock data loaded dynamically.
- **`main.py` v2**: Single `/api/v1/chat-simulate` handles crude + gas simultaneously. OpenAI → Gemini LLM fallback. AISStream vessel endpoint with mock fallback. `/api/v1/prices` and `/api/v1/lng-terminals` endpoints.
- **`.env`**: All API keys documented — OpenAI, Gemini, AISStream, Alpha Vantage.
- **`Dashboard.jsx`**: LNG terminal purple nodes, gas/crude pipeline PathLayers, dual color-coded ArcLayers (yellow=crude, purple=gas), animated vessel dots (cyan=LNG, yellow=tanker).
- **`Controls.jsx`**: Same chat tab shows both crude (yellow card) and gas (purple card) results side by side. Price shock card, rerouting impact, LNG regasification plan, LNG supplier viability ranking.
- **`App.jsx`**: Live price ticker bar (Brent/Dubai/WTI/JKM/TTF/Henry Hub), dual KPI bar for crude+gas, vessel fetch on mount.
