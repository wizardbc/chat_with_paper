# Chat with a Paper

- Clone this repo

### Dependencies
`google-generativeai`, `streamlit`, `pandas`, `tqdm`.

### Google API Key

Put your Google API Key in `.streamlit/secrets.toml` or provide it in the sidebar for temporary use.
```config
GOOGLE_API_KEY = "YOUR_API_KEY"
```
You can obtain your Google API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Chatbot
Run streamlit app.
```bash
streamlit run chatbot.py
```

### RAG

You can upload tex files with `.tex` or `.tar.gz` on `Upload` tab in chatbot.

Also you can manually process tex files and get embeddings.

- Place your tex files in `./uploads/arXiv-????.?????v?/`
- Process the LaTeX file
  ```bash
  python ./rag/latex_extractor.py \
    ./uploads/arXiv-????.?????v?/main.tex \
    -o ./data/paper.csv \
    -t ./rag/instruction_template.txt \
    --inst ./data/instruction.txt
  ```
- Get embeddings
  ```bash
  python ./rag/gemini_embd.py ./data/paper.csv
  ```

`data/papers.json` contains the titles, embedding and system instruction files info.