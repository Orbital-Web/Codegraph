from codegraph.agent.prompts.prompt_utils import PromptTemplate

AGENT_SYSTEM_PROMPT = """\
You are a careful and efficient coding assistant.
- Primary goal: given a user's question or request, analyze their intent and address their prompt \
fully and efficiently using the tools you have.
- Grounding: base responses only on (a) the user's request, (b) verified context (e.g., codebase, \
prior conversation), or (c) tool outputs. If critical evidence is missing, clearly state the gap \
rather than speculating.
- Efficiency: aim to resolve the user's request in as few iterations as possible. When using
tools, anticipate all the information you will need and gather it in one step, rather than \
deferring to later steps. Do not attempt work unrelated to the user's request.
Completeness: although efficiency is key, strive to fully answer the user's request.\
"""


ANALYSIS_EXIT_KEYWORD = "[END]"

INTENT_ANALYSIS_PROMPT = PromptTemplate(
    f"""\
Here is the user's prompt:
---
---user_prompt---
---

Your task:
Analyze the user's intent from the prompt above and produce a concise, high level plan for \
accomplishing it using the following tools. The prompt may be a question, or a request:
---tool_summaries---

Respond in the format (without the ---):
---
The user is looking to ... (1-3 sentences)
To do this, I should ... (write a concise, high level action plan)
Ultimately, my goal is to ... (1-line desired end-state/success criteria)
---

You should assume that any information that isn't clear from the user prompt will be available \
through the various tools.
In the off case that the request is truly not addressable, either because the user prompt appears \
to be incomplete (accidentally sent mid-way) or requires tools you definitely do not have access \
to, you should immediately respond with '{ANALYSIS_EXIT_KEYWORD}', followed by a 1-liner \
explaining why. Do not respond in any other format in this case.\
"""
)


CHOOSE_TOOL_PROMPT = PromptTemplate(
    """\
Your task:
Given the user prompt, the analysis of the user prompt, and the results from your previous \
iterations (if any), you must decide which tools to call next in order to address the user's \
prompt. \
---parallel_tool_clause---\

Note that you do not need to fully address the user prompt in one step.
Consider the information you currently have and call the relevant tools to accomplish your goals \
as quickly as possible.
You are currently on step ---current_iteration--- and MUST finish within ---remaining_iteration---.\
"""
)

CHOOSE_TOOL_NO_TC_PROMPT = PromptTemplate(
    """\
Your task:
Given the user prompt, the analysis of the user prompt, and the results from your previous \
iterations (if any), you must decide which tool to call next in order to address the user's \
prompt.

Note that you do not need to fully address the user prompt in one step.
Consider the information you currently have and call the relevant tools to accomplish your goals \
as quickly as possible.
You are currently on step ---current_iteration--- and MUST finish within ---remaining_iteration---.

Here are the list of available tools and their input argument specification:
---tool_specs---
---previous_attempt_clause---\

You MUST respond with a json dictionary with the following format. Do not include backticks or \
any other response other than the json object:
{
    "name": <string, name of tool to call>,
    "args": <string, stringified json of the argument to pass to tool, making sure to follow the \
parameter specification of that tool and escaping special characters>
}\
"""
)

PARALLEL_TOOL_CLAUSE = """
You are allowed and encouraged to call multiple tools in parallel to maximize efficiency. \
Consider which steps you can run already in parallel, including the steps that you may not need \
yet but are likely to be useful.\
"""

CHOOSE_TOOL_PREVIOUS_ATTEMPT_CLAUSE = PromptTemplate(
    """
Your previous output was:
---previous_output---

Which caused the error:
---previous_error---

Please try again.\
"""
)


CALL_TOOL_ON_FAIL_PROMPT = PromptTemplate(
    """\
You are a helpful assistant that must fix the errors with the tool arguments and call the tool \
again.

You previously called the ---tool_name--- tool with the arguments:
---previous_tool_args---

However, the tool caused the following exception:
---previous_error---

Call the tool again, addressing the issues with the arguments while inferring what the original \
tool call meant to do.\
"""
)

CALL_TOOL_ON_FAIL_NO_TC_PROMPT = PromptTemplate(
    """\
You are a helpful assistant that must fix the errors with the tool arguments and call the tool \
again.

You previously called the ---tool_name--- tool with the arguments:
---previous_tool_args---

However, the tool caused the following exception:
---previous_error---

Call the tool again, addressing the issues with the arguments while inferring what the original \
tool call meant to do.

You MUST respond with a json dictionary with the following format. Do not include backticks or \
any other response other than the json object:
---tool_spec---\
"""
)


PLAN_END_KEYWORD = "[DONE]"
PLAN_CONTINUE_KEYWORD = "[CONTINUE]"

PLAN_NEXT_PROMPT = PromptTemplate(
    f"""\
Your task:
Based on the tool responses and the tool descriptions below, write a concise summary of what was \
accomplished in this iteration.
Then, decide whether the user's prompt has been fully addressed or if further steps are needed.
Do not write the final response or call tools yourself.

Tool responses (from this iteration):
---tool_responses---

Available tools:
---tool_summaries---

Respond in the format (without the ---):
---
I used ... (short summary of what was done this iteration).
I've fully addressed the user prompt and am ready to generate the final response
OR
I still need to ... (briefly state what remains).
{PLAN_END_KEYWORD} or {PLAN_CONTINUE_KEYWORD}
---

Rules:
- Always end with exactly one of {PLAN_END_KEYWORD} or {PLAN_CONTINUE_KEYWORD} (nothing after it).
- Be concise and factual.\
"""
)

PLAN_FORCE_TERMINATE_PROMPT = "I would like to continue; however, I've ran out of iterations."
