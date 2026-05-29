---
name: no-anthropic-in-code
enabled: false
---

RETIRED 2026-05-10: Original rule was based on a wrong premise.

Anthropic SDK IS the correct provider for browser-use automation.
claude-haiku-4-5 at ~$0.001/post is covered by the $200/mo Anthropic plan.
OpenAI API (ChatOpenAI) is blocked due to zero API credits on the $20 ChatGPT Plus plan.

Correct usage:
  from browser_use.llm.anthropic.chat import ChatAnthropic
  ChatAnthropic(model="claude-haiku-4-5", api_key=os.environ["ANTHROPIC_API_KEY"])
