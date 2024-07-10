# Chat with a Paper

- Clone this repo

### Google API Key

Put your Google API Key in `.streamlit/secrets.toml` or provide it in the sidebar for temporary use.
```config
GOOGLE_API_KEY = "YOUR_API_KEY"
```
You can obtain your Google API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### RAG
- Place your tex files in `data/arXiv-????.?????v?/`
- Process the LaTeX file
  ```bash
  python ./rag/latex_extractor.py \
    ./data/arXiv-????.?????v?/main.tex \
    -o ./data/paper.csv \
    -t ./rag/instruction_template.txt \
    --inst ./data/instruction.txt
  ```
- Get embeddings.
  ```bash
  python ./rag/gemini_embd.py ./data/paper.csv
  ```

