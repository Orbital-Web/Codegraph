from codegraph.agent.prompts.prompt_utils import PromptTemplate

ANALYSIS_EXIT_KEYWORD = "[END]"

INTENT_ANALYSIS_PROMPT = PromptTemplate(
    f"""\
You are a helpful coding assistant that must extract the user's intent and produce a concise, high \
level plan for accomplishing it using the various tools made available to you.
You should format your response as:
'''
The user is looking to ... (1-3 sentences)
To do this, I should ... (list out the steps and purposes. Keep each step concise)
Ultimately, my goal is to ... (1-line desired end-state/success criteria)
'''

You should assume that any information that isn't clear from the user prompt will be available \
through the various tools.
In the off case that the question is truly unanswerable, either because the user prompt appears to \
be incomplete (accidentally sent mid-way) or requires tools you definitely do not have access to, \
you should immediately respond with '{ANALYSIS_EXIT_KEYWORD}', followed by a 1-liner explaining \
why. Do not respond in any other format in this case.

Here are the list of tools you have access to. Note that not every tool might have a comprehensive \
description of what it does:
---tool_summaries---

Finally, here is the user prompt:
---user_prompt---\
"""
)


PARALLEL_TOOL_CLAUSE = """
You are allowed and encouraged to call multiple tools in parallel to maximize efficiency. \
Consider which steps you can run already in parallel, including the steps that you may not need \
yet but are likely to be useful.\
"""

CONTINUATION_CLAUSE = PromptTemplate(
    """
Here are the steps you've taken, and your continuation reason from the previous step:
---previous_steps_summary---

Continuation Reason: ---continuation_reason---\
"""
)

CHOOSE_TOOL_PROMPT = PromptTemplate(
    """\
You are a helpful coding assistant that must call the various tools to accomplish the user prompt. \
---parallel_tool_clause---

Note that you do not need to fully address the user prompt in one step.
Consider the information you currently have and call the relevant tools to accomplish your goals \
as quickly as possible.
You are currently on step ---current_iteration--- and MUST finish within ---remaining_iteration---.

The user prompt is:
---user_prompt---

Here is your previous reasoning on the user intent and your high level plan:
---analysis_result---
---continuation_clause---\
"""
)

CHOOSE_TOOL_NO_TC_PROMPT = PromptTemplate(
    """\
You are a helpful coding assistant that must decide which tool to call to accomplish the user \
prompt.

Note that you do not need to fully address the user prompt in one step.
Consider the information you currently have and call the relevant tools to accomplish your goals \
as quickly as possible.
You are currently on step ---current_iteration--- and MUST finish within ---remaining_iteration---.

The user prompt is:
---user_prompt---

Here is your previous reasoning on the user intent and your high level plan:
---analysis_result---
---continuation_clause---

Here are the list of available tools. Note that not every tool might have a comprehensive \
description of what it does:
---tool_specs---
---previous_attempt_clause---

You MUST respond with a json dictionary with the following format. Do not include backticks or \
any other response other than the json object:
{
    "name": <string, name of tool to call>,
    "args": <string, stringified json of the argument to pass to tool, making sure to follow the \
parameter specification of that tool and escaping special characters>
}\
"""
)

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
tool call meant to do.
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
---tool_spec---
"""
)
