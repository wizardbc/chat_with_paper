import numpy as np
import pandas as pd
import google.generativeai as genai
import streamlit as st
from tqdm.auto import tqdm

def get_embedding(df:pd.DataFrame, model:str="models/text-embedding-004") -> list[list]:
  """
  Generate embeddings for the content of a DataFrame using a specified model.

  Args:
    df (pd.DataFrame): A pandas DataFrame containing the sections, subsections,
                       subsubsections, and content to be embedded. The DataFrame
                       should have the columns: 'section', 'subsection',
                       'subsubsection', and 'content'.
    model (str, optional): The model to be used for generating embeddings. Defaults
                           to "models/text-embedding-004".

  Returns:
    list: A list of embeddings for each row's content in the DataFrame.

  The function iterates over each row of the DataFrame and extracts the section, subsection,
  subsubsection, and content. It determines the most specific title available from the section,
  subsection, or subsubsection and uses this title along with the content to generate an embedding
  using the specified model. The generated embeddings are returned as a list.
  """
  embds = []
  pbar = tqdm(df[['section','subsection','subsubsection','content']].iterrows(), total=len(df))
  for _, (s, ss, sss, text) in pbar:
    for t in [s, ss, sss]:
     if t:
      title = t
    pbar.set_description(title)
    if len(text) > 10000:
      n_chunks = len(text)//9000
      chunks = [text[(0 if i==0 else (i*9000-1000)) + (i+1)*9000] for i in range(n_chunks)]
      embd_chunks = [
        np.array(genai.embed_content(
          model=model,
          content=chunk,
          task_type="retrieval_document",
          title=title,
        )["embedding"]) * max(len(chunk)-1000, 0) / n_chunks
        for chunk in chunks
      ]
      embd = np.stack(embd_chunks).sum(axis=0).tolist()
      
    else:
      embd = genai.embed_content(
        model=model,
        content=text,
        task_type="retrieval_document",
        title=title,
      )["embedding"]
    embds.append(embd)
  return embds

if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description='Process a csv file to generate embeddings for RAG.')
  parser.add_argument('csv_file', type=str, help='Path to the input CSV file')
  parser.add_argument('-o', '--output', type=str, help='Path to the output CSV file (optional, if not specified, input file will be overridden)')
  args = parser.parse_args()

  ### Google API key
  try:
    api_key = st.secrets["GOOGLE_API_KEY"]
  except:
    api_key = input("Enter your Google API Key: ")
  genai.configure(api_key=api_key)

  # Load the input CSV file into a DataFrame
  df = pd.read_csv(args.csv_file).fillna('')

  # Generate embeddings and add as a new column to the DataFrame
  df['embedding'] = get_embedding(df)

  # Determine the output file path
  output_file = args.output if args.output else args.csv_file

  # Save the DataFrame to the output CSV file
  df.to_csv(output_file, index=False)