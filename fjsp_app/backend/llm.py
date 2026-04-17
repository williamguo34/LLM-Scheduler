import os, json, io, streamlit as st
from openai import OpenAI

# ---------------- Credential helpers -----------------
def _get_api_key():
    return st.session_state.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')

def _get_base_url():
    return st.session_state.get('OPENAI_BASE_URL') or os.environ.get('OPENAI_BASE_URL') or 'https://models.inference.ai.azure.com'

def _client():
    key = _get_api_key()
    if not key:
        raise RuntimeError('OPENAI_API_KEY not set (session_state or env)')
    return OpenAI(base_url=_get_base_url(), api_key=key)

# ---------------- Schema -----------------
def load_fjsp_schema():
    with open('schema_openai.txt') as f:
        return json.load(f)["schema"]

def get_openai_functions():
    fjsp_schema = load_fjsp_schema()
    return [
        {
            "name": "generate_schedule_json",
            "description": "Generate initial FJSP schedule JSON from the provided user message (returned as `schedule_json`).",
            "parameters": {"type": "object","properties": {"schedule_json": fjsp_schema},"required": ["schedule_json"]}
        },
        {
            "name": "update_schedule_json",
            "description": "Return an updated FJSP schedule JSON (as `schedule_json`).",
            "parameters": {"type": "object","properties": {"schedule_json": fjsp_schema},"required": ["schedule_json"]}
        }
    ]

# --------------- Core LLM calls ----------------
def generate_schedule_json(user_message, model=None):
    model = model or (st.session_state.get('MODEL_NAME') or 'gpt-4o')
    client = _client()
    system_prompt = open('prompt_openai.txt').read()
    functions = get_openai_functions()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_message}],
        functions=functions,
        function_call={"name":"generate_schedule_json"}
    )
    st.info('🔧 Used OpenAI function calling for schedule generation.')
    choice = response.choices[0]
    if hasattr(choice,'message') and hasattr(choice.message,'function_call'):
        args = choice.message.function_call.arguments
        if isinstance(args,str):
            try:
                args = json.loads(args)
            except Exception as e:
                raise ValueError(f'JSON decode error: {e}\nRaw arguments:\n{args}\nResponse:{response}')
        schedule_json = args.get('schedule_json') or args
        if isinstance(schedule_json,dict) and 'user_message' in schedule_json and not all(k in schedule_json for k in ['J','M','instances']):
            raise ValueError('Model echoed user_message instead of schedule_json.')
        if not all(k in schedule_json for k in ['J','M','instances']):
            raise ValueError('Missing keys J/M/instances in schedule_json.')
        st.json(schedule_json)
        return schedule_json
    raise RuntimeError(f'No valid function_call in response: {response}')

def update_schedule_json(current_json, instruction, prev_messages=None, model=None):
    model = model or (st.session_state.get('MODEL_NAME') or 'gpt-4o')
    client = _client()
    system_prompt = open('prompt_for_update.txt').read()
    functions = get_openai_functions()
    messages = [{"role":"system","content":system_prompt}]
    if prev_messages:
        messages.extend(prev_messages)
    messages.append({"role":"assistant","content":"Current schedule JSON (do not modify directly):"})
    messages.append({"role":"assistant","content":json.dumps(current_json)})
    messages.append({"role":"user","content":instruction})
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        functions=functions,
        function_call={"name":"update_schedule_json"}
    )
    st.info('🔧 Used OpenAI function calling for schedule update.')
    choice = response.choices[0]
    if hasattr(choice,'message') and hasattr(choice.message,'function_call'):
        args = choice.message.function_call.arguments
        if isinstance(args,str):
            try:
                args = json.loads(args)
            except Exception as e:
                raise ValueError(f'JSON decode error (update): {e}\nRaw: {args}')
        schedule_json = args.get('schedule_json') or args
        if isinstance(schedule_json,dict) and 'current_json' in schedule_json and not all(k in schedule_json for k in ['J','M','instances']):
            raise ValueError('Model echoed current_json instead of updated schedule_json.')
        if not all(k in schedule_json for k in ['J','M','instances']):
            raise ValueError('Invalid updated schedule_json structure (missing keys).')
        return schedule_json
    raise RuntimeError(f'No valid function_call in update response: {response}')

def update_solution_csv_llm(csv_path, user_instruction, model=None):
    model = model or (st.session_state.get('MODEL_NAME') or 'gpt-4o')
    df = __import__('pandas').read_csv(csv_path)
    prompt = f"""
You are an expert in Flexible Job Shop Scheduling (FJSP).
Below is the current solution pool in CSV format. Each row represents an operation in a job, with columns: instance_id, job, operation, machine, start_time, end_time, duration.

User instruction: "{user_instruction}"

Update the CSV minimally. Return ONLY the updated CSV with headers.

Current CSV:
{df.to_csv(index=False)}
"""
    client = _client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"You are a scheduling assistant. Only output the updated CSV, no explanations."},
            {"role":"user","content":prompt}
        ]
    )
    updated_csv = response.choices[0].message.content
    import pandas as pd
    return pd.read_csv(io.StringIO(updated_csv))

def get_llm_update_decision(user_instruction, model=None):
    model = model or (st.session_state.get('MODEL_NAME') or 'gpt-4o')
    decision_prompt = f"""
You are an expert in Flexible Job Shop Scheduling (FJSP).
Instruction:\n{user_instruction}\n
Decide which update method:
- Structural change -> update_schedule_json
- Local adjustment  -> update_solution_csv_llm

Reply ONLY with: update_schedule_json or update_solution_csv_llm
"""
    client = _client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":"You are a scheduling assistant."},{"role":"user","content":decision_prompt}]
    )
    return response.choices[0].message.content.strip()
