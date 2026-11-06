# Zara AI — Milestones 1–3

Milestone 1 provides a modular, local-first conversation engine backed by
Ollama. It streams generated text, records explicit conversation states, and
supports cancelling an in-flight response. Milestone 2 adds optional,
user-controlled SQLite long-term memory. Milestone 3 adds optional,
push-to-talk Hindi voice input and local Hindi speech output.

The engine includes a fixed Zara identity instruction: the configured Ollama
model is treated only as the underlying model, and the assistant is instructed
to respond naturally in the user's language, including conversational
Romanized Hindi and Hinglish.

Voice is an optional terminal feature, not an always-on microphone. This is
still an engine and terminal chat, not the finished desktop app. The graphical
UI, web search, and animated character are not implemented yet.

## Requirements

- Windows 11 (other platforms may work but are not currently tested).
- Python 3.11 or newer.
- Ollama installed and running locally.
- An already-pulled Ollama chat model. The default is `qwen2.5:7b`; this
  workspace's current Ollama installation also has `sia:latest`.
- For voice, a Windows Vulkan-capable graphics driver is recommended, a
  working microphone and speaker, and enough disk space for about 1 GB of
  downloads. Voice assets are optional and are not installed by core setup.
- For voice alongside a local chat model, 16 GB system RAM and a Vulkan GPU
  with around 8 GB VRAM are recommended. These are planning estimates, not
  measured minimums. The ASR Q4 weights occupy 511 MB; upstream reports about
  0.67 GB memory for Q4 on an Apple M5, which is not a Windows/Vulkan
  measurement. TTS uses CPU and has 219 MB of BF16 weights. Zara AI has not
  benchmarked combined Ollama, ASR, and TTS performance.

## Setup

From the `Zara-AI` project directory, create and activate a virtual environment:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

If Python 3.14 is not available, use any installed Python 3.11+ interpreter
with `-m venv .venv`. The runtime dependency is `httpx`; tests use the standard
library and require no test framework.

No Ollama model is downloaded by these commands. To check the local server and
its available models:

```powershell
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

## Start a chat

```powershell
python -m zara_ai
```

The first run writes a default configuration file to
`%APPDATA%\ZaraAI\config.toml` (normally
`C:\Users\<you>\AppData\Roaming\ZaraAI\config.toml`). Edit its `model` field to
select an already-installed model. Type `/exit` to end the conversation. Press
Ctrl+C to interrupt generation and exit.

Override the model or local server URL for a single run:

```powershell
$env:ZARA_OLLAMA_MODEL = "sia:latest"
python -m zara_ai
Remove-Item Env:ZARA_OLLAMA_MODEL
```

The equivalent environment overrides are `ZARA_OLLAMA_BASE_URL` and
`ZARA_OLLAMA_MODEL`. The terminal reports the interrupted state when cancelled;
an interrupted or failed assistant response is not added to conversation
history.

## Local Hindi voice

Voice uses a replaceable recorder, ASR, TTS, and playback interface. The
approved default backends are:

- **ASR:** Qwen3-ASR-0.6B Q4_K GGUF, Apache-2.0, run by `speech.cpp` 0.8.11
  (MIT). The recognizer detects supported languages, including Hindi. The
  quantized model's Hindi/Hinglish accuracy has not been benchmarked here.
- **TTS:** Pocket TTS Hindi female voice weights, declared MIT by the model
  repository, using `pocket-tts` 4.0.1 (MIT) and PyTorch (BSD-3-Clause). This
  voice supports Hindi, not verified natural Hinglish output; voice replies
  are requested in Devanagari Hindi. The training-source licensing for the
  voice sample was not independently established.
- The speech model's temporary WAV input is deleted after recognition. Audio
  and transcripts are not written to long-term memory or application logs.
  The transcript is part of ordinary in-process conversation history, which
  is not persisted. If you configure Ollama to use a non-local server, the
  recognized transcript is sent to that configured server.

Install the optional dependencies in the project virtual environment and
explicitly download the approved assets:

```powershell
python -m pip install -e ".[voice]"
python -m zara_ai --setup-voice
```

`--setup-voice` downloads pinned model revisions into
`%LOCALAPPDATA%\ZaraAI\voice` and the verified Windows x64 Vulkan runtime. It
does not enable the microphone. Expected downloads are approximately:

- Qwen3-ASR-0.6B Q4_K weights: 511 MB (plus a small metadata file).
- Hindi Pocket TTS BF16 weights: 219 MB (plus its config, tokenizer, and voice
  prompt).
- `speech.cpp` Windows Vulkan runtime archive: 29 MB.
- Optional Python wheels: approximately 201 MB, depending on Python and
  platform; PyTorch is the largest dependency.
- Total download estimate: roughly 960 MB. Extracted disk use is higher and
  depends on the Python environment.

The optional Python dependencies support Python 3.14 on Windows. The models
run locally after installation; setup requires internet access, but voice
capture, recognition, synthesis, and default Ollama inference do not require
internet access. Model performance, VRAM use, and recognition accuracy have
not been benchmarked on this machine. ASR uses the Windows Vulkan runtime;
ASR finishes before Ollama generation starts, while TTS runs on CPU. If
resources are constrained, use a smaller existing Ollama model and close other
GPU-heavy applications.

Enable voice by editing `%APPDATA%\ZaraAI\config.toml`:

```toml
[voice]
enabled = true
max_record_seconds = 60
```

The voice asset directory defaults to `%LOCALAPPDATA%\ZaraAI\voice`. To use
another directory, add `data_directory = "D:\\path\\to\\voice"` to `[voice]`.
The default TTS voice reference is the project's
`assets\voice_samples\speech-1792953435497.wav`. To use another reference WAV,
add `reference_wav = "D:\\path\\to\\voice-reference.wav"` to `[voice]`.
Relative reference paths are resolved from the directory containing
`config.toml`. The maximum push-to-talk recording duration can be set from 1
to 300 seconds.

Start Zara as usual and enter `/voice`. Press Enter to begin recording, then
press Enter again to stop; the microphone is never open between turns. Zara
shows the recognized transcript before responding. The Hindi voice requires
Devanagari text; voice mode asks the conversation model to respond in
Devanagari Hindi and will show, but not speak, a segment if it contains no
Devanagari. Press Ctrl+C to cancel a voice turn. Use `/exit` to quit.

The selected Hindi TTS model is a single fixed voice, not an animated character
or a voice selector. Hinglish input may be recognized because the ASR supports
Hindi and English, but code-switching accuracy is unbenchmarked. Hinglish TTS
is not supported or claimed by this milestone.

### Microphone and speaker test procedure

1. Confirm the Windows microphone and speaker work in Windows Sound settings.
2. Check Windows **Settings → Privacy & security → Microphone** and allow
   desktop apps to access the microphone.
3. Start Zara, enter `/voice`, press Enter to start recording, say a short
   Hindi sentence, then press Enter to stop.
4. Confirm the transcript is shown, Zara's Hindi response streams, and the
   selected speaker plays it. Repeat once using a short Hinglish utterance.
5. Enter `/memory` and `/memories` to verify no voice turn was stored as a
   long-term memory.

This workspace's microphone and speaker endpoints were enumerated, but no
recording, permission prompt, or real playback test has been performed.

## Long-term memory

Long-term memory is **off by default** and is separate from in-process
conversation history. Prompts and assistant responses are never automatically
saved as memories. Opting in lets Zara use explicitly saved notes as context;
it does not authorize automatic saving. Each add or edit requires a separate
confirmation. Review notes and do not save sensitive information. Saved memory
is local SQLite data, not encrypted by this application.

Available terminal commands:

```text
/memory                         Show opt-in status
/memory-on                      Opt in to using saved memories as context
/memory-off                     Stop including memory in model requests
/remember <text>                Request saving this exact note; asks for confirmation
/memories                       List saved notes and their IDs
/edit-memory <id> <new text>    Request replacing a note; asks for confirmation
/forget <id>                    Request deleting one note; asks for confirmation
/clear-memories                 Request clearing all notes; asks for confirmation
```

Type `y` at a save, edit, delete, or clear confirmation; any other answer
cancels the operation. Turning memory off preserves the notes so they can still
be reviewed and deleted, but they are not sent to Ollama. Deleting one note or
clearing all notes is allowed while memory is off. Conversation history remains
in process memory and is not persisted in the SQLite database.

The database is created on first launch at
`%LOCALAPPDATA%\ZaraAI\memory.sqlite3` (normally
`C:\Users\<you>\AppData\Local\ZaraAI\memory.sqlite3`). SQLite schema changes
are versioned through the database `user_version`; no model or database service
needs to be downloaded or installed separately.

Example opt-in and explicit save:

```text
You: /memory-on
You: /remember I prefer concise answers
This saves only the text you entered to local SQLite. Do not save sensitive information. Save it? [y/N] y
You: /memories
[1] I prefer concise answers
```

## Configuration, logs, and privacy

The generated TOML configuration supports:

```toml
[ollama]
base_url = "http://127.0.0.1:11434"
model = "qwen2.5:7b"
request_timeout_seconds = 300

[generation]
temperature = 0.7
num_ctx = 4096

[voice]
enabled = false
max_record_seconds = 60
```

Voice paths are derived from the per-user voice data directory unless
`voice.data_directory` is set.

The application logs operational events and errors to
`%LOCALAPPDATA%\ZaraAI\logs\zara-ai.log`, rotating the log at 1 MiB and keeping
three backups. Prompts and generated responses are deliberately not logged.
Conversation history exists only in process memory; it is not saved to disk.
Long-term memories are persisted separately only after opt-in and per-item
confirmation, as described above.

## Tests

The HTTP provider and voice tests use mocks and do not require Ollama, a
microphone, speaker, voice model, or optional voice dependencies. Run them
with:

```powershell
python -m unittest discover -s tests -v
```

For a live text smoke test, start Ollama first and run `python -m zara_ai`.
The microphone and speaker procedure above is a separate hardware test.

## Troubleshooting

- **Connection refused / Ollama unavailable:** start the Ollama application and
  check `Invoke-RestMethod http://127.0.0.1:11434/api/tags`.
- **Model not found:** run `ollama list` and set `model` in the configuration
  file (or `ZARA_OLLAMA_MODEL`) to an installed model. Zara AI does not pull
  models automatically.
- **Slow responses or memory pressure:** use a smaller already-installed model,
  reduce `num_ctx`, or close other GPU-heavy applications. This milestone does
  not perform hardware benchmarking.
- **Different Ollama host:** set `base_url` in the config or
  `ZARA_OLLAMA_BASE_URL`; do not expose the server to an untrusted network.
- **Voice dependencies missing:** activate the project `.venv` and run
  `python -m pip install -e ".[voice]"`.
- **Voice model or runtime missing:** run `python -m zara_ai --setup-voice`.
  This downloads only the pinned ASR/TTS files and the verified `speech.cpp`
  runtime.
- **Microphone unavailable or denied:** check Windows microphone privacy
  settings, close other recording apps, and confirm the default input device in
  Windows Sound settings.
- **Speaker unavailable:** check the default Windows output device and volume.
- **ASR startup failure:** check that the ASR file is present under the
  configured voice data directory and that the graphics driver supports
  Vulkan. Recognition failure does not send an empty prompt to Ollama.
- **TTS model/configuration error:** rerun `python -m zara_ai --setup-voice`
  and confirm that the configured voice data directory has enough free disk
  space.

## Current limits

There is no graphical interface, animated avatar, lip-sync, web search, or
tool execution yet. Voice TTS is Hindi-only and fixed-voice; Hinglish TTS is
not verified. Real microphone/speaker testing and model performance
benchmarking remain outstanding.
