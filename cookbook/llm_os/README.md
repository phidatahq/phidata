# LLM OS

This cook contains an initial implementation of the LLM OS, inspired by @karpathy's [tweet](https://twitter.com/karpathy/status/1723140519554105733) on LLMs emerging as the kernel process of a new Operating System.

He talks about it:
- [In this tweet](https://twitter.com/karpathy/status/1723140519554105733)
- [In this tweet](https://twitter.com/karpathy/status/1707437820045062561)
- [In this video](https://youtu.be/zjkBMFhNj_g?t=2535)

## Running the LLM OS:

### 1. Create a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 2. Install libraries

```shell
pip install -r cookbook/llm_os/requirements.txt
```

### 3. Run the LLM OS App

```shell
streamlit run cookbook/llm_os/app.py
```

- Open [localhost:8501](http://localhost:8501) to view your LLM OS.

### 4. Message on [discord](https://discord.gg/4MtYHHrgA8) if you have any questions

### 5. Star ⭐️ the project if you like it.

## The LLM OS philosophy

- LLM is the kernel process of an emerging operating system.
- This process (LLM) is coordinating a lot of resources (like memory or computation tools) for problem-solving.

- The LLM OS Vision:
  - [x] It can read/generate text
  - [x] It has more knowledge than any single human about all subjects
  - [x] It can browse the internet
  - [x] It can use existing software infra (calculator, python, mouse/keyboard)
  - [ ] It can see and generate images and video
  - [ ] It can hear and speak, and generate music
  - [ ] It can think for a long time using a system 2
  - [ ] It can “self-improve” in domains
  - [ ] It can be customized and fine-tuned for specific tasks
  - [x] It can communicate with other LLMs

[x] indicates functionality that is implemented in the LLM OS app
