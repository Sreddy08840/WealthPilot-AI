"""
WealthPilot AI - Multi-Agent Rebalancing Crew

This module defines the CrewAI setup for our Autonomous Portfolio Rebalancing System.
It establishes a 7-agent council with dedicated tasks, backstories, and tools.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Attempt to import actual CrewAI and LangChain components.
# If they are not installed, we fall back to a high-fidelity simulation layer
# so that the system runs out-of-the-box.
try:
    from crewai import Agent as CrewAgent, Task as CrewTask, Crew as CrewApp, Process
    from langchain.tools import tool as langchain_tool
    from langchain_openai import ChatOpenAI
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False

# ============================================================================
# 1. Custom Tools Definitions
# ============================================================================
# We use standard Python functions that can be wrapped as LangChain tools.

def drift_check_tool(current_weights: dict, target_weights: dict) -> str:
    """Computes absolute drift index and individual asset drift deviations."""
    all_assets = set(current_weights.keys()).union(target_weights.keys())
    total_drift = 0.0
    allocations = {}
    for asset in all_assets:
        w_curr = current_weights.get(asset, 0.0)
        w_targ = target_weights.get(asset, 0.0)
        diff = w_curr - w_targ
        total_drift += abs(diff)
        allocations[asset] = {"current": w_curr, "target": w_targ, "drift": diff}
    abs_drift = total_drift / 2.0
    return json.dumps({
        "absolute_drift": abs_drift,
        "needs_rebalance": abs_drift >= 0.05,
        "allocations": allocations
    }, indent=2)

def tax_lot_harvest_tool(portfolio_id: str, symbol: str, price: float, lots: list) -> str:
    """Sorts tax lots by HIFO and identifies loss harvesting lots."""
    # Sort lots by cost basis descending
    sorted_lots = sorted(lots, key=lambda x: x.get("purchase_price", 0.0), reverse=True)
    harvested = []
    total_loss = 0.0
    for lot in sorted_lots:
        cost = lot["purchase_price"]
        shares = lot["shares"]
        current_val = shares * price
        cost_basis = shares * cost
        gain_loss = current_val - cost_basis
        if gain_loss < 0:
            total_loss += abs(gain_loss)
            harvested.append({
                "lot_id": lot.get("id"),
                "shares": shares,
                "cost_basis": cost,
                "realized_loss": abs(gain_loss)
            })
    return json.dumps({
        "symbol": symbol,
        "current_price": price,
        "hifo_lots": sorted_lots,
        "harvested_lots": harvested,
        "total_harvested_loss": total_loss
    }, indent=2)

def compliance_screening_tool(symbol: str, action: str, weight: float) -> str:
    """Screens ticker buys against restricted lists and single asset caps (80%)."""
    restricted = ["BTC", "COIN", "TSLA", "MSTR"]
    is_restricted = symbol in restricted
    over_limit = weight > 0.80
    return json.dumps({
        "symbol": symbol,
        "action": action,
        "passes_restricted_check": not is_restricted,
        "passes_concentration_check": not over_limit,
        "action_required": "BLOCK" if is_restricted else ("SCALE_DOWN" if over_limit else "PASS")
    }, indent=2)

# ============================================================================
# 2. CrewAI Layer (Fallback Simulator / Production Wrapper)
# ============================================================================

class SimulatedAgent:
    def __init__(self, role: str, goal: str, backstory: str, tools: list = None, verbose: bool = True):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.verbose = verbose

    def execute_task(self, task_description: str, context: str = "") -> str:
        # Generate custom mock reasoning based on agent role
        if "Monitor" in self.role:
            return f"[{self.role}] Analysed weights: current {context.get('current_weights')}, target {context.get('target_weights')}. Drift detected: 6.2%. Trigger active."
        elif "Market" in self.role:
            return f"[{self.role}] Checked market feeds. VIX is at 18.5 (moderate volatility). Tickers SPY ($515.20) and AGG ($98.40) verified."
        elif "Risk" in self.role:
            return f"[{self.role}] Tracking error calculated: 1.85% (within 2% limit). Volatility-based risk score is 11.2."
        elif "Tax" in self.role:
            return f"[{self.role}] Commenced HIFO selection. Selling SPY shares at a loss from Lot-2. Total loss harvested: $2,976.00."
        elif "Compliance" in self.role:
            return f"[{self.role}] Screened trade block. Restricted tickers check: Passed. Wash sale warning resolved by substituting buying index with IVV."
        elif "Explanation" in self.role:
            return f"[{self.role}] Attributed SHAP values: Drift (+0.45), Tax Shield (+0.35), Volatility (+0.12). Rebalance triggered due to overweight S&P index."
        elif "Orchestrator" in self.role:
            return f"[{self.role}] Consolidated rebalance orders. Execution block signed: SELL 120 SPY, BUY 560 AGG. Proposal queued."
        return f"[{self.role}] Executed task: {task_description}."

class SimulatedTask:
    def __init__(self, description: str, expected_output: str, agent: SimulatedAgent):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent

class SimulatedCrew:
    def __init__(self, agents: list, tasks: list, verbose: int = 2):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose

    def kickoff(self, inputs: dict) -> str:
        logs = []
        logs.append("=== CrewAI Autonomous Council Dispatch ===")
        logs.append(f"Ingested Portfolio ID: {inputs.get('portfolio_id')} | Target Profile: {inputs.get('target_profile')}\n")
        
        context = {
            "current_weights": {"SPY": 0.56, "AGG": 0.44},
            "target_weights": {"SPY": 0.50, "AGG": 0.50}
        }
        
        # Execute each task sequentially, aggregating outputs
        for task in self.tasks:
            logs.append(f"Task: {task.description[:60]}...")
            out = task.agent.execute_task(task.description, context)
            logs.append(out)
            logs.append("-" * 50)
            
        logs.append("\n=== Rebalancing Recommendation Compiled ===")
        return "\n".join(logs)

# Resolve execution references
AgentClass = CrewAgent if CREWAI_AVAILABLE else SimulatedAgent
TaskClass = CrewTask if CREWAI_AVAILABLE else SimulatedTask
CrewClass = CrewApp if CREWAI_AVAILABLE else SimulatedCrew

# ============================================================================
# 3. Multi-Agent Setup
# ============================================================================

def create_rebalancing_crew(llm_key: Optional[str] = None) -> CrewClass:
    """
    Creates and returns the multi-agent Crew for rebalancing.
    """
    # Initialize LLM if actual CrewAI is available and key is provided
    llm = None
    if CREWAI_AVAILABLE and llm_key:
        llm = ChatOpenAI(api_key=llm_key, model="gpt-4o-mini", temperature=0.2)

    # 1. Portfolio Monitoring Agent
    monitor_agent = AgentClass(
        role="Portfolio Monitoring Analyst",
        goal="Continually scan active client holdings, compute absolute drift, and detect target target allocation deviations.",
        backstory="You are a precise quantitative analyst. You monitor assets, calculate drift metrics, and alert the team when portfolios deviate by more than 5%.",
        tools=[drift_check_tool] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # 2. Market Analysis Agent
    market_agent = AgentClass(
        role="Market Analysis Specialist",
        goal="Retrieve real-time asset pricing feeds, monitor asset volatility index (VIX), and verify trading liquidity.",
        backstory="You are a market expert. You monitor ticker prices, track macroeconomic events, and ensure the trade execution block has sufficient liquidity.",
        tools=[] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # 3. Risk Assessment Agent
    risk_agent = AgentClass(
        role="Quantitative Risk Auditor",
        goal="Compute portfolio variance, evaluate tracking error limits, and map volatility metrics to risk scores.",
        backstory="You are a risk manager trained in Modern Portfolio Theory. You ensure active risk (tracking error) remains below 2.0% and trigger warnings if volatility spikes.",
        tools=[] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # 4. Tax Optimization Agent
    tax_agent = AgentClass(
        role="Tax Overlay Architect",
        goal="Scan lot histories, apply HIFO tax-lot optimization, and harvest capital loss offsets to minimize tax drags.",
        backstory="You are a tax overlay specialist. You check asset lots, match purchase costs, and selectively sell lots to harvest capital losses while avoiding capital gains taxes.",
        tools=[tax_lot_harvest_tool] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # 5. Compliance Agent
    compliance_agent = AgentClass(
        role="Regulatory Compliance Officer",
        goal="Enforce firm restricted list blockades, validate wash sale rules, and maintain single-stock concentration caps.",
        backstory="You are a compliance officer. You screen all trades. You block restricted assets and reroute wash-sale orders to equivalent proxies (e.g. SPY to IVV).",
        tools=[compliance_screening_tool] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # 6. Explanation Agent
    explanation_agent = AgentClass(
        role="Financial AI Explainer",
        goal="Interpret Game-Theoretic Shapley values (SHAP) and compile a clear, human-readable rebalancing summary.",
        backstory="You are a financial writer. You explain complex ML metrics. You write summaries explaining why the rebalance occurred (e.g. SPY drift or GLD volatility).",
        tools=[] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # 7. Orchestrator Agent
    orchestrator_agent = AgentClass(
        role="Portfolio Rebalancing Director",
        goal="Coordinate the Multi-Agent council outputs, build trade execution blocks, and submit proposals to review queues.",
        backstory="You are the lead director of the portfolio engine. You aggregate inputs from drift, risk, tax, and compliance, sign off on trade blocks, and queue them for override approval.",
        tools=[] if CREWAI_AVAILABLE else [],
        verbose=True
    )

    # Establish tasks mapping to each agent
    task_monitor = TaskClass(
        description="Calculate absolute drift for portfolio {portfolio_id} using targets for risk category {target_profile}.",
        expected_output="Drift Index report detailing which assets have drifted out of bounds.",
        agent=monitor_agent
    )

    task_market = TaskClass(
        description="Analyze market feeds for the drifted assets, verify current prices, and check the VIX volatility index.",
        expected_output="Liquid price matrix and market condition summary.",
        agent=market_agent
    )

    task_risk = TaskClass(
        description="Compute annualized portfolio variance and tracking error standard deviations for the target profile.",
        expected_output="Risk score mapping and tracking error risk analysis.",
        agent=risk_agent
    )

    task_tax = TaskClass(
        description="Evaluate tax-lot list, sort by purchase cost descending (HIFO), and compile capital loss harvesting offsets.",
        expected_output="Tax lot execution instructions maximizing tax shields.",
        agent=tax_agent
    )

    task_compliance = TaskClass(
        description="Audit proposed trades list. Confirm wash-sale rules compliance and verify single asset concentration limit.",
        expected_output="Compliance audited orders block (with clean/modified flags).",
        agent=compliance_agent
    )

    task_explain = TaskClass(
        description="Format Shapley trigger values (SHAP) and write a clear rebalancing justification memo for the manager.",
        expected_output="Explainable AI attribution summary and narrative text.",
        agent=explanation_agent
    )

    task_orchestrate = TaskClass(
        description="Consolidate target trade orders block, attach compliance and tax offsets signatures, and submit to pending review queue.",
        expected_output="Final rebalance proposal package ready for manager execution override.",
        agent=orchestrator_agent
    )

    # Bind agents and tasks to the Crew
    if CREWAI_AVAILABLE:
        crew = CrewClass(
            agents=[monitor_agent, market_agent, risk_agent, tax_agent, compliance_agent, explanation_agent, orchestrator_agent],
            tasks=[task_monitor, task_market, task_risk, task_tax, task_compliance, task_explain, task_orchestrate],
            process=Process.sequential,
            verbose=2
        )
    else:
        crew = SimulatedCrew(
            agents=[monitor_agent, market_agent, risk_agent, tax_agent, compliance_agent, explanation_agent, orchestrator_agent],
            tasks=[task_monitor, task_market, task_risk, task_tax, task_compliance, task_explain, task_orchestrate],
            verbose=2
        )
        
    return crew

if __name__ == "__main__":
    # Test script run
    my_crew = create_rebalancing_crew()
    result = my_crew.kickoff(inputs={
        "portfolio_id": "WP-000451",
        "target_profile": "Balanced"
    })
    print(result)
