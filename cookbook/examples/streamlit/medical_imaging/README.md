# Medical Imaging Diagnosis Agent

Medical Imaging Diagnosis Agent is a medical imaging analysis agent that analyzes medical images and provides detailed findings by utilizing models and external tools.

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install requirements

```shell
pip install -r cookbook/examples/streamlit/medical_imaging/requirements.txt
```

### 3. Export `OPENAI_API_KEY`

```shell
export OPENAI_API_KEY=sk-***
```

### 4. Run Streamlit App

```shell
streamlit run cookbook/examples/streamlit/medical_imaging/app.py
```
