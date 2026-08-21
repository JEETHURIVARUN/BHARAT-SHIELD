import pyomo.environ as pyo
import logging
from typing import Dict, Any
from app.agents.agent3_gas_trader import LNG_TERMINALS

logger = logging.getLogger(__name__)

DOMESTIC_GAS_FIELDS = {
    "ONGC_KG_Basin":  {"available_mmscmd": 20.0, "cost_factor": 0.3},
    "Reliance_KGD6":  {"available_mmscmd": 12.0, "cost_factor": 0.4},
    "ONGC_Mumbai_HF": {"available_mmscmd": 18.0, "cost_factor": 0.3},
    "GSPC_Deendayal": {"available_mmscmd":  5.0, "cost_factor": 0.5},
}

def solve_gas_drawdown(daily_deficit_mmscmd: float, disrupted_terminals: list = None) -> Dict[str, Any]:
    """
    Optimizes gas supply distribution across LNG terminals and domestic fields.
    Uses Slack Variable so the solver NEVER returns Infeasible.
    Priority: available LNG terminal headroom → domestic gas fields.
    """
    terminal_headroom = {}
    for name, t in LNG_TERMINALS.items():
        if disrupted_terminals and name in disrupted_terminals:
            continue
        headroom = round(t["send_out_mmscmd"] * (1 - t["utilization_pct"] / 100), 2)
        if headroom > 0:
            terminal_headroom[name] = headroom

    total_t_cap = sum(terminal_headroom.values())
    total_d_cap = sum(v["available_mmscmd"] for v in DOMESTIC_GAS_FIELDS.values())
    total_capacity = total_t_cap + total_d_cap

    model = pyo.ConcreteModel()
    model.TERMINALS = pyo.Set(initialize=terminal_headroom.keys())
    model.DOMESTIC  = pyo.Set(initialize=DOMESTIC_GAS_FIELDS.keys())

    model.t_cap  = pyo.Param(model.TERMINALS, initialize=terminal_headroom)
    model.d_cap  = pyo.Param(model.DOMESTIC,  initialize={k: v["available_mmscmd"] for k, v in DOMESTIC_GAS_FIELDS.items()})
    model.d_cost = pyo.Param(model.DOMESTIC,  initialize={k: v["cost_factor"]       for k, v in DOMESTIC_GAS_FIELDS.items()})
    model.demand = pyo.Param(initialize=daily_deficit_mmscmd)

    model.draw_terminal = pyo.Var(model.TERMINALS, domain=pyo.NonNegativeReals)
    model.draw_domestic = pyo.Var(model.DOMESTIC,  domain=pyo.NonNegativeReals)
    # Slack variable: absorbs any infeasibility when demand > capacity
    model.unmet_demand  = pyo.Var(domain=pyo.NonNegativeReals)

    def obj_rule(m):
        return (
            sum(m.draw_terminal[t] * 1.0    for t in m.TERMINALS) +
            sum(m.draw_domestic[d] * 50.0   for d in m.DOMESTIC)  +
            m.unmet_demand         * 100_000.0
        )
    model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # Soft equality: always feasible, unmet_demand absorbs any gap
    def deficit_rule(m):
        return (sum(m.draw_terminal[t] for t in m.TERMINALS) +
                sum(m.draw_domestic[d] for d in m.DOMESTIC)  +
                m.unmet_demand == m.demand)
    model.deficit_con = pyo.Constraint(rule=deficit_rule)

    def t_cap_rule(m, t): return m.draw_terminal[t] <= m.t_cap[t]
    def d_cap_rule(m, d): return m.draw_domestic[d] <= m.d_cap[d]
    model.t_cap_con = pyo.Constraint(model.TERMINALS, rule=t_cap_rule)
    model.d_cap_con = pyo.Constraint(model.DOMESTIC,  rule=d_cap_rule)

    try:
        solver = pyo.SolverFactory('glpk')
        result = solver.solve(model, tee=False)
        status = str(result.solver.termination_condition)

        t_draw  = {t: round(pyo.value(model.draw_terminal[t]), 3) for t in model.TERMINALS}
        d_draw  = {d: round(pyo.value(model.draw_domestic[d]),  3) for d in model.DOMESTIC}
        unmet   = round(pyo.value(model.unmet_demand), 3)
        covered = round(daily_deficit_mmscmd - unmet, 3)

        return {
            "Status":                  "optimal_with_slack" if unmet > 0.01 else status,
            "Solver":                  "GLPK",
            "Terminal_Drawdown_MMSCMD": t_draw,
            "Domestic_Rampup_MMSCMD":  d_draw,
            "Total_Covered_MMSCMD":    covered,
            "Unmet_Deficit_MMSCMD":    unmet,
            "Total_Capacity_MMSCMD":   round(total_capacity, 2),
        }

    except Exception as e:
        logger.error(f"Gas solver error: {e}")
        cap_ratio  = min(1.0, total_capacity / max(daily_deficit_mmscmd, 0.001))
        covered    = round(daily_deficit_mmscmd * cap_ratio, 3)
        unmet      = round(daily_deficit_mmscmd - covered, 3)
        mock_t     = round(covered * 0.70, 3)
        mock_d     = round(covered * 0.30, 3)
        return {
            "Status": "Mocked (Solver not found)",
            "Solver": "None — proportional fallback",
            "Terminal_Drawdown_MMSCMD": {"Dahej": round(mock_t * 0.60, 3), "Hazira": round(mock_t * 0.40, 3)},
            "Domestic_Rampup_MMSCMD":  {"ONGC_KG_Basin": mock_d},
            "Total_Covered_MMSCMD":    covered,
            "Unmet_Deficit_MMSCMD":    unmet,
            "Total_Capacity_MMSCMD":   round(total_capacity, 2),
        }

if __name__ == "__main__":
    print("--- Test 1: Normal gas deficit 15 MMSCMD ---")
    print(solve_gas_drawdown(15.0, disrupted_terminals=["Dahej"]))
    print("\n--- Test 2: Infeasible 999 MMSCMD — Slack must absorb ---")
    print(solve_gas_drawdown(999.0))
