import pyomo.environ as pyo
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class Phase(Enum):
    PHASE_1 = 1
    PHASE_2 = 2

def solve_drawdown(daily_deficit: float, phase: Phase = Phase.PHASE_1) -> dict:
    """
    Optimizes the drawdown of OMC Tier 1 and ISPRL Tier 2 stocks to meet the daily crude deficit.
    Uses Slack Variables so the solver NEVER returns Infeasible — if total capacity < demand,
    the model computes the maximum possible drawdown and reports the exact unmet deficit.
    """
    tier_1_stocks = {
        'IOCL': 3.0,
        'BPCL': 2.0,
        'HPCL': 2.0
    }
    tier_2_phase_1 = {
        'Visakhapatnam': round(1.33 * 0.64, 4),
        'Mangaluru':     round(1.50 * 0.64, 4),
        'Padur':         round(2.50 * 0.64, 4),
    }
    tier_2_phase_2 = {
        'Chandikhol': round(4.0 * 0.64, 4),
        'Padur_II':   round(2.5 * 0.64, 4),
    }
    tier_2_stocks = tier_2_phase_1.copy()
    if phase == Phase.PHASE_2:
        tier_2_stocks.update(tier_2_phase_2)

    total_capacity = sum(tier_1_stocks.values()) + sum(tier_2_stocks.values())

    model = pyo.ConcreteModel()
    model.OMC   = pyo.Set(initialize=tier_1_stocks.keys())
    model.ISPRL = pyo.Set(initialize=tier_2_stocks.keys())

    model.tier_1_cap = pyo.Param(model.OMC,   initialize=tier_1_stocks)
    model.tier_2_cap = pyo.Param(model.ISPRL,  initialize=tier_2_stocks)
    model.daily_deficit = pyo.Param(initialize=daily_deficit)

    model.drawdown_omc   = pyo.Var(model.OMC,   domain=pyo.NonNegativeReals)
    model.drawdown_isprl = pyo.Var(model.ISPRL,  domain=pyo.NonNegativeReals)
    # Slack variable: absorbs any infeasibility when demand > physical capacity
    model.unmet_demand   = pyo.Var(domain=pyo.NonNegativeReals)

    def obj_rule(m):
        return (
            sum(m.drawdown_omc[o]   * 1.0       for o in m.OMC)   +
            sum(m.drawdown_isprl[i] * 1_000.0   for i in m.ISPRL) +
            m.unmet_demand          * 100_000.0   # Massive penalty — solver avoids this at all cost
        )
    model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # Soft equality constraint — always feasible because unmet_demand absorbs any gap
    def deficit_rule(m):
        return (sum(m.drawdown_omc[o] for o in m.OMC) +
                sum(m.drawdown_isprl[i] for i in m.ISPRL) +
                m.unmet_demand == m.daily_deficit)
    model.deficit_con = pyo.Constraint(rule=deficit_rule)

    def omc_cap_rule(m, o):   return m.drawdown_omc[o]   <= m.tier_1_cap[o]
    def isprl_cap_rule(m, i): return m.drawdown_isprl[i] <= m.tier_2_cap[i]
    model.omc_cap_con   = pyo.Constraint(model.OMC,   rule=omc_cap_rule)
    model.isprl_cap_con = pyo.Constraint(model.ISPRL,  rule=isprl_cap_rule)

    try:
        solver = pyo.SolverFactory('glpk')
        result = solver.solve(model, tee=False)
        termination = str(result.solver.termination_condition)

        omc_draw   = {o: round(pyo.value(model.drawdown_omc[o]), 4)   for o in model.OMC}
        isprl_draw = {i: round(pyo.value(model.drawdown_isprl[i]), 4) for i in model.ISPRL}
        unmet      = round(pyo.value(model.unmet_demand), 4)
        covered    = round(daily_deficit - unmet, 4)

        out = {
            "Status": "optimal_with_slack" if unmet > 0.001 else termination,
            "Solver": "GLPK",
            "OMC_Drawdown":   omc_draw,
            "ISPRL_Drawdown": isprl_draw,
            "Total_Covered":  covered,
            "Unmet_Deficit_MMT": unmet,
            "Total_Capacity_MMT": round(total_capacity, 3),
        }
        return out

    except Exception as e:
        logger.error(f"Solver error (GLPK may not be installed): {e}")
        # Pure proportional fallback — always returns sane values
        cap_ratio  = min(1.0, total_capacity / max(daily_deficit, 0.001))
        covered    = round(daily_deficit * cap_ratio, 4)
        unmet      = round(daily_deficit - covered, 4)
        mock_omc   = round(covered * 0.6, 4)
        mock_isprl = round(covered * 0.4, 4)
        return {
            "Status": "Mocked (Solver not found)",
            "Solver": "None — proportional fallback",
            "OMC_Drawdown": {
                "IOCL": round(mock_omc * 0.50, 4),
                "BPCL": round(mock_omc * 0.30, 4),
                "HPCL": round(mock_omc * 0.20, 4),
            },
            "ISPRL_Drawdown": {
                "Visakhapatnam": round(mock_isprl * 0.40, 4),
                "Mangaluru":     round(mock_isprl * 0.30, 4),
                "Padur":         round(mock_isprl * 0.30, 4),
            },
            "Total_Covered":     covered,
            "Unmet_Deficit_MMT": unmet,
            "Total_Capacity_MMT": round(total_capacity, 3),
        }

if __name__ == "__main__":
    print("--- Test 1: Normal demand (5 MMT) ---")
    print(solve_drawdown(5.0, Phase.PHASE_1))
    print("\n--- Test 2: Infeasible demand (99 MMT) — Slack must absorb ---")
    print(solve_drawdown(99.0, Phase.PHASE_1))
