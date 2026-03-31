from __future__ import annotations

from langsmith import traceable

try:
    from ..chains.synthesis_chain import SynthesisInput, build_synthesis_chain
except ImportError:
    from chains.synthesis_chain import SynthesisInput, build_synthesis_chain


@traceable(name="synthesis", run_type="chain", tags=["synthesis"])
def trace_synthesis(evidence, plan):
    chain = build_synthesis_chain()
    return chain.invoke(SynthesisInput(evidence=evidence, plan=plan))


def synthesise_output(evidence, plan):
    return trace_synthesis(evidence, plan)
