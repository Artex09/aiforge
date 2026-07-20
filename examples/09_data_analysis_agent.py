"""Data Analysis Agent — computes metrics over structured data.

Run: python examples/09_data_analysis_agent.py
"""
import json

from aiforge.sdk import AIForge

DATA = json.dumps({"revenue": [120, 340, 220, 500], "costs": [80, 200, 150, 260]})


def main() -> None:
    forge = AIForge()
    agent = forge.agent("data_analysis_agent", template="data_analysis_agent")

    total_revenue = forge.call_tool("calculator", expression="120 + 340 + 220 + 500")
    print("Total revenue:", total_revenue.output)

    margin = forge.call_tool("calculator", expression="(1180 - 690) / 1180 * 100")
    print(f"Overall margin: {margin.output:.1f}%")

    result = agent.run("Summarise the profitability trend in this dataset: " + DATA)
    print("INSIGHT:", result.output)


if __name__ == "__main__":
    main()
