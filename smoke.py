"""Smoke test: can we reach JEV from this project?"""

from typesafe_sdk import Noul
from jev_guardrail.jev import ask_jev

response = ask_jev(
    state="A user is about to run this shell command: ls -la",
    questions={
        "is_destructive": Noul(instructions="Is this command destructive?"),
        },

)


answer = response.answers["is_destructive"]

print(f"Probability destructive: {answer.noul:.3f}")

print(f"Model: {response.model}")
