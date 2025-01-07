from evals.performance.instantiation.agno_agent import agno_instantiation_perf
from evals.performance.instantiation.crewai_agent import crew_instantiation_perf
from evals.performance.instantiation.pydantic_ai_agent import pydantic_instantiation_perf

perf_results = {
    'agno': agno_instantiation_perf.run(),
    'crewai': crew_instantiation_perf.run(),
    'pydantic_ai': pydantic_instantiation_perf.run()
}

if __name__ == "__main__":
    agno_perf = agno_instantiation_perf.run()
    crew_perf = crew_instantiation_perf.run()
    pydantic_perf = pydantic_instantiation_perf.run()
