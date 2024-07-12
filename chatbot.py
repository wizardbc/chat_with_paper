from io import StringIO
import os
import shutil
import json
import tarfile
import numpy as np
import pandas as pd
from ast import literal_eval
import google.generativeai as genai
import streamlit as st

from rag.latex_extractor import process, extract_title
from rag.gemini_embd import get_embedding

### set_page
st.set_page_config(
    page_title="Chat with a Paper",
    page_icon=":books:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': 'https://github.com/wizardbc/chat_with_paper',
        'Report a bug': "https://github.com/wizardbc/chat_with_paper/issues",
        'About': "# Chat with a Paper\nMade by Byung Chun Kim\n\nhttps://github.com/wizardbc/chat_with_paper"
    }
)

def ftn_codeblock(fn, args):
  res = "```python\n"
  res += str(fn)
  res += '(\n'
  for k,v in args.items():
    if isinstance(v, str):
      res += f'  {k}="{v}"\n'
    else:
      res += f'  {k}={v}\n'
  res += ')\n```'
  return res

### stream wrapper
### gemini does not provide the `automatic_function_calling` and stream output simultaneously.
def gemini_stream_text(response):
  for chunk in response:
    if parts:=chunk.parts:
      if text:=parts[0].text:
        yield text

@st.experimental_dialog("🚨 Error")
def error(err, msg=''):
  st.write(f"We've got error\n```python\n{err}\n```")
  if msg:
    st.text(msg)
  if st.button("Ok"):
    st.rerun()

### Google API key
if "api_key" not in st.session_state:
  try:
    st.session_state.api_key = st.secrets["GOOGLE_API_KEY"]
  except:
    st.session_state.api_key = ''

with st.sidebar:
  if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
  else:
    st.session_state.api_key = st.text_input("Google API Key", type="password")

### Papers
try:
  with open('data/papers.json', 'r') as fp:
    papers = json.load(fp)
except FileNotFoundError:
  st.warning("`data/papers.json` file is not found. Please upload tex file in the `Upload` tab.")
  papers = {}
  _system_instruction = ''

with st.sidebar:
  st.header("Paper")
  title = st.selectbox("Paper", [None] + list(papers.keys()))

# load data
if title:
  df_csv = pd.read_csv(papers.get(title).get('csv')).fillna('')
  df_csv["embedding"] = df_csv.embedding.apply(literal_eval).apply(np.array)

  with open(papers.get(title).get('inst'), 'r') as fp:
    _system_instruction = fp.read()

else:
    _system_instruction = ''

# call when change system_instruction
def _save_sys_inst():
  if title:
    with open(papers.get(title).get('inst'), 'w') as fp:
      fp.write(st.session_state.sys_inst)

### search tools
def search_from_section_names(query:list[str]) -> str:
  """Retrieves LaTeX chunks from the paper using the [section, subsection, subsubsection] names.

Args:
    query: A python list of three strings in the format `[section, subsection, subsubsection]`.
  """
  query = [name if name else '' for name in list(query)]
  query += ['']*(3-len(query))
  df = df_csv.copy()
  res_df = df[
    (df['section'] == query[0])
    & (df['subsection'] == query[1])
    & (df['subsubsection'] == query[2])
  ]
  if len(res_df)==0:
    res_df = df[
      df['section'].str.contains(query[0])
      & df['subsection'].str.contains(query[1])
      & df['subsubsection'].str.contains(query[2])
    ]
  return res_df[['section', 'subsection', 'subsubsection', 'content']].to_json()

def search_from_text(query:str, top_n:int=5, s:float=.0):
  """Retrieves LaTeX chunks from the paper using cosine similarity of text.

Args:
  query: The user's query string.
  top_n: The number of chunks to retrieve. The default value is 5. Start at 3 and recommend increasing it if needed.
  """
  df = df_csv.copy()
  query_embedding = np.array(genai.embed_content(
    model="models/text-embedding-004",
    content=query,
    task_type="retrieval_query",
  )["embedding"])
  top_n = int(top_n)
  df["similarity"] = df.embedding.apply(lambda x: np.dot(x, query_embedding))
  return df[df.similarity >= s].sort_values("similarity", ascending=False).head(top_n)[['section', 'subsection', 'subsubsection', 'content', 'similarity']].to_json()

tools = {
  'search_from_section_names': search_from_section_names,
  'search_from_text': search_from_text,
}

### Layout
with st.sidebar:
  st.header("Visibility")
  st.caption("Panel on Right")
  help_checkbox = st.checkbox("Help", value=False)
  memo_checkbox = st.checkbox("Memo", value=True)
  st.caption("Messages")
  f_call_checkbox = st.checkbox("Function Call", value=False)
  f_response_checkbox = st.checkbox("Function Response", value=False)

tab_chat, tab_memo, tab_system, tab_upload = st.tabs(["Chat", "Memo", "System Instruction", "Upload"])

with tab_chat:
  st.title("💬 Chat with a Paper")
  if title:
    st.caption(f":books: Read \"{title}\" with Gemini 1.5")
  st.divider()
  if not st.session_state.api_key:
    st.warning("Your Google API Key is not provided in `.streamlit/secrets.toml`, but you can input one in the sidebar for temporary use.", icon="⚠️")

  if help_checkbox or memo_checkbox:
    col_l, col_r = st.columns([6,4], vertical_alignment='bottom')
    with col_l:
      messages = st.container()
  else:
    messages = st.container()

# memo
if "memo" not in st.session_state:
  st.session_state.memo = []

with tab_memo:
  st.header("Memo", divider=True)
  for m in st.session_state.memo:
    st.write(m)
    st.divider()

# system prompt
with tab_system:
  system_instruction = st.text_area("system instruction", _system_instruction, height=512, key='sys_inst', on_change=_save_sys_inst)

# help, memo in col_r of tab_chat
if help_checkbox:
  with col_r:
    with st.container(border=True):
      st.write("Retrieve the contents of the paper and answer.")
      st.write("""Two functions are used to retrieve the contents:
-	`search_from_section_names`: Extracts the section names of the paper where the answer to the question is expected to be found and retrieves the contents of those sections.
- `search_from_text`: Retrieves the contents using the cosine similarity between the embedding representing the section content of the paper and the embedding of the question.

The language model determines which function to use and may be explicitly instructed to use a particular function by mentioning its name.""")
if memo_checkbox:
  with col_r, st.container(border=True):
    st.subheader("Memo", divider=True)
    len_memo_m_1 = len(st.session_state.memo) - 1
    for i, m in enumerate(st.session_state.memo):
      st.write(m)
      st.button("Remove", on_click=st.session_state.memo.remove, args=[m], key=f'_memo_{i}')
      if i < len_memo_m_1:
        st.divider()

### Upload

# Function to handle file upload and extraction
def handle_upload(uploaded_file):
  upload_dir = os.path.join("uploads", uploaded_file.file_id)
  if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
      f.write(uploaded_file.getbuffer())
    if tarfile.is_tarfile(file_path):
      with tarfile.open(file_path, "r:gz") as tar:
        tar.extractall(upload_dir)
  return upload_dir

# Function to find all .tex files in the upload directory and subdirectories
def find_tex_files(directory):
  tex_files = []
  for root, _, files in os.walk(directory):
    for file in files:
      if file.endswith(".tex"):
        tex_files.append(os.path.join(root, file))
  return tex_files

with tab_upload:
  uploaded_file = st.file_uploader("Upload `.tex` file or `.tar.gz` file", type=["tex", ".gz"], key='uploader')

  if uploaded_file is not None:
    upload_dir = handle_upload(uploaded_file)
    st.success(f"Uploaded {uploaded_file.name}")
    tex_files = find_tex_files(upload_dir)
    if tex_files:
      selected_file = st.selectbox("Choose a `.tex` file to process", ['/'.join(f.split('/')[2:]) for f in tex_files])
      try:
        with open(os.path.join(upload_dir, selected_file), 'r') as fp:
          _title = extract_title(fp.read())
          if not _title:
            _title = "Title is not found."
      except:
        _title = "Title is not found."
      uploaded_title = st.text_input("Display name", _title)
    else:
      st.info("No .tex files found. Please upload another one.")
      shutil.rmtree(upload_dir)
    if st.button("Process", type="primary"):
      with st.status(f"Processing {selected_file}...", expanded=True) as status:
        st.write("Extracting...")
        with open("rag/instruction_template.txt") as f:
          template = f.read()
        df, inst = process(os.path.join(upload_dir, selected_file), template)
        fname = hex(pd.util.hash_pandas_object(df).sum())[-8:]
        st.write("Getting embeddings...")
        if os.path.exists(f"data/{fname}.csv"):
          st.warning(f"`{fname}.csv` already exists.")
        else:
          df['embedding'] = get_embedding(df)
          df.to_csv(f"data/{fname}.csv")
          with open(f"data/{fname}.txt", 'w') as f:
            f.write(inst)
        st.write("Adding...")
        papers.update({
          uploaded_title: {
            "csv": f"data/{fname}.csv",
            "inst": f"data/{fname}.txt"
          }
        })
        with open('data/papers.json', 'w') as fp:
          json.dump(papers, fp)
        status.update(label=f"{selected_file} processed successfully", state="complete", expanded=False)
      shutil.rmtree(upload_dir)
      st.warning("Successed. Please reload the page. Press `CTRL+R` or `CMD+R`.")

### gemini parameters
with st.sidebar:
  st.header("Gemini Parameters")
  model_name = st.selectbox("model", ["gemini-1.5-flash", "gemini-1.5-pro"])
  generation_config = {
    "temperature": st.slider("temperature", min_value=0.0, max_value=1.0, value=1.0),
    "top_p": st.slider("top_p", min_value=0.0, max_value=1.0, value=0.95),
    "top_k": st.number_input("top_k", min_value=1, value=64),
    "max_output_tokens": st.number_input("max_output_tokens", min_value=1, value=8192),
  }

safety_settings={
  'harassment':'block_none',
  'hate':'block_none',
  'sex':'block_none',
  'danger':'block_none'
}

### gemini
if "history" not in st.session_state:
  st.session_state.history = []

model = genai.GenerativeModel(
  model_name=model_name,
  generation_config=generation_config,
  safety_settings=safety_settings,
  system_instruction=system_instruction if system_instruction else None,
  tools=tools.values(),
)
chat_session = model.start_chat(
  history=st.session_state.history,
  enable_automatic_function_calling=False
)

### chat controls
def rewind():
  if len(chat_session.history) >= 2:
    chat_session.rewind()
  if len(chat_session.history) >= 2:
    part = chat_session.history[-1].parts[0]
    if part.function_call:
      chat_session.rewind()
  st.session_state.history = chat_session.history

def clear():
  chat_session.history.clear()
  st.session_state.history = chat_session.history

with st.sidebar:
  st.header("Chat Control")
  btn_col1, btn_col2 = st.columns(2)
  with btn_col1:
    st.button("Rewind", on_click=rewind, use_container_width=True, type='primary')
  with btn_col2:
    st.button("Clear", on_click=clear, use_container_width=True)

### display messages in history
for i, content in enumerate(chat_session.history):
  for part in content.parts:
    if text:=part.text:
      with messages.chat_message('human' if content.role == 'user' else 'ai'):
        st.write(text)
        if content.role == 'model':
          st.button("Memo", on_click=st.session_state.memo.append, args=[text], key=f'_btn_{i}')
    if f_call_checkbox and (fc:=part.function_call):
      with messages.chat_message('ai'):
        st.write(f"**Function Call**:\n\n{ftn_codeblock(fc.name, fc.args)}")
    if f_response_checkbox and (fr:=part.function_response):
      with messages.chat_message('retriever', avatar="📜"):
        if "search_" in fr.name:
          retriever_df = pd.read_json(StringIO(fr.response["result"]))
          st.dataframe(retriever_df.loc[:, (retriever_df.columns != "text")])
          with st.expander("Content"):
            for text in retriever_df.content:
              st.text(text)
        else:
          st.write(f"Function Response\n- name: {fr.name}\n- response\n  - `result`")
          st.json(fr.response["result"])

### chat input

if prompt := st.chat_input("Ask me anything...", disabled=False if st.session_state.api_key else True):
  with messages.chat_message('human'):
    st.write(prompt)
  err_msg_content = "You may have triggered Google's content filter.\nThis is likely because you are trying to generate copyrighted documents."
  with messages.chat_message('ai'):
    with st.spinner("Generating..."):
      try:
        response = chat_session.send_message(prompt, stream=True)
        text = st.write_stream(gemini_stream_text(response))
        st.session_state.history = chat_session.history
      except genai.types.StopCandidateException as e:
        error(e, err_msg_content)
      except genai.types.BrokenResponseError as e:
        error(e, err_msg_content)
      # function response
      fr_parts = []
      for part in response.parts:
        if fc := part.function_call:
          st.toast(f"**Function Calling**\n`{fc.name}`")
          fr_parts.append(
            genai.protos.Part(
              function_response=genai.protos.FunctionResponse(
                name=fc.name,
                response={"result": tools[fc.name](**fc.args)}))
          )
      if fr_parts:
        try:
          response = chat_session.send_message(fr_parts)
          text = st.write_stream(gemini_stream_text(response))
          st.session_state.history = chat_session.history
          if f_call_checkbox or f_response_checkbox:
            st.rerun()
        except genai.types.StopCandidateException as e:
          st.session_state.history = st.session_state.history[:-2]
          error(e, err_msg_content)
        except genai.types.BrokenResponseError as e:
          st.session_state.history = st.session_state.history[:-2]
          error(e, err_msg_content)
    st.button("Memo", on_click=st.session_state.memo.append, args=[text], key=f'_btn_last')