from __future__ import annotations

from langsmith import traceable

try:
    from ..chains.intent_chain import build_intent_chain
    from ..chains.planner_chain import build_planner_chain
    from ..schemas.intent_schema import IntentInput
except ImportError:
    from chains.intent_chain import build_intent_chain
    from chains.planner_chain import build_planner_chain
    from schemas.intent_schema import IntentInput


@traceable(name="intent_classification", run_type="chain", tags=["intent"])
def trace_intent(raw_query: str):
    chain = build_intent_chain()
    return chain.invoke(IntentInput(raw_query=raw_query))


@traceable(name="planning", run_type="chain", tags=["planner"])
def trace_plan(intent):
    chain = build_planner_chain()
    return chain.invoke(intent)


def classify_and_plan(raw_query: str):
    intent = trace_intent(raw_query)
    plan = trace_plan(intent)
    return intent, plan


def plan_from_intent(intent):
    return trace_plan(intent)
