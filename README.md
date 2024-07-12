# Chat with a Paper

https://chatwithpaper.streamlit.app/

### Dependencies
`google-generativeai`, `streamlit`, `pandas`, `tqdm`.

### Google API Key

Put your Google API Key in `.streamlit/secrets.toml` or provide it in the sidebar for temporary use.
```config
GOOGLE_API_KEY = "YOUR_API_KEY"
```
You can obtain your Google API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Chatbot
Run the Streamlit app.
```bash
streamlit run chatbot.py
```

### RAG

You can upload `.tex` files or `.tar.gz` archives on the `Upload` tab in the chatbot.

You can also manually process `.tex` files and generate embeddings.

- Clone this repository and install the requirements.
- Place your tex files in `uploads/arXiv-????.?????v?/`
- Process the LaTeX file
  ```bash
  python rag/latex_extractor.py \
    uploads/arXiv-????.?????v?/main.tex \
    -o data/paper.csv \
    -t rag/instruction_template.txt \
    --inst data/instruction.txt
  ```
- Generate embeddings:
  ```bash
  python rag/gemini_embd.py data/paper.csv
  ```
- `data/papers.json` contains the titles, embeddings, and system instruction file information.