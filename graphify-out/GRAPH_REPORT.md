# Graph Report - asya-ai-assistant  (2026-10-31)

## Corpus Check
- 113 files · ~116,227 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .example 1, .css 1)

## Summary
- 916 nodes · 2028 edges · 72 communities (37 shown, 35 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 176 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Frontend Pages
- Speech Job Queue
- Installation and HTTPS
- Agent Storage Gateway
- Runtime Verification Utilities
- Chat API Tests
- Agent Integration Documentation
- Agent Runtime Installer
- Backend HTTP Routes
- Chat Text Processing
- Browser Audio Capture
- Studio Audio Processing
- TTS Runtime Provisioning
- Async Network Verification
- Agent Service Modules
- Agent API Security
- Backend API Schemas
- Server Discovery Probes
- Frontend Build Configuration
- TypeScript Compiler Configuration
- Speech Chunk Segmentation
- Agent Job Ownership
- Installer Test Utilities
- Browser End To End Tests
- Windows Setup Workflow
- Streaming Cancellation Tests
- Streaming Speech Design
- Conversation Screenshot
- LAN Access Configuration
- Network Security Tests
- Frontend Development Dependencies
- Studio Interface Screenshot
- Local Agent Administration
- LAN Gateway Launcher
- MCP Stdio Adapter
- Speech Provider Registry
- Backend Python Dependencies
- Desktop Packaging Proposal
- Legacy Settings Screenshot
- Stored Resource Routes
- Frontend NPM Scripts
- Voice Chat Screenshot
- Agent Credential Storage
- Voice Input Validation
- Main Runtime Dependencies
- Agent Python Dependencies
- Generated API Types
- Historical Streamlit Architecture
- Agent Administration Schemas
- TTS Provider Protocol
- Stream Response Helpers
- Frontend Runtime Dependencies
- Audio Worklet Capture
- Isolated STT Dependencies
- Frontend HTML Entry
- Request Access Limits

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 61 edges
2. `Store` - 50 edges
3. `Engines` - 31 edges
4. `APITests` - 24 edges
5. `api` - 24 edges
6. `create_app()` - 23 edges
7. `AgentStore` - 23 edges
8. `AgentRuntime` - 22 edges
9. `Generation` - 22 edges
10. `SpeechChunker` - 19 edges

## Surprising Connections (you probably didn't know these)
- `ASYA Local CA client trust` --semantically_similar_to--> `LAN HTTPS with trusted local CA`  [INFERRED] [semantically similar]
  docs/HTTPS_ACCESS.md → KURULUM.md
- `voice-lab runtime junctions` --semantically_similar_to--> `voice-lab .venv .venv-stt data chatterbox junctions`  [INFERRED] [semantically similar]
  KURULUM.md → docs/VOICE_STUDIO.md
- `Shared GPU job queue` --semantically_similar_to--> `Existing ASYA speech queue without separate model loading`  [INFERRED] [semantically similar]
  README.md → docs/AGENTS_API.md
- `main()` --calls--> `convert_audio()`  [EXTRACTED]
  scripts/verify-streaming-speech.py → apps/backend/app/audio.py
- `main()` --calls--> `convert_audio()`  [EXTRACTED]
  scripts/verify-tts.py → apps/backend/app/audio.py

## Import Cycles
- None detected.

## Communities (72 total, 35 thin omitted)

### Community 0 - "Frontend Pages"
Cohesion: 0.09
Nodes (62): api, audioUrl(), date(), generateAudio(), seconds(), statusLabel, App(), FakeAudio (+54 more)

### Community 1 - "Speech Job Queue"
Cohesion: 0.07
Nodes (16): Store, Engines, LMClient, Generation, SetupSettingsTests, FakeProvider, LMTests, client() (+8 more)

### Community 2 - "Installation and HTTPS"
Cohesion: 0.06
Nodes (48): Contribution guide, Separate CUDA Torch and STT environments, OpenAPI generated TypeScript API types, Exclude voices databases certificates and environment secrets, Backend frontend tests and production build, evolution/voice-studio shared Git history, Historical voice studio migration plan, Legacy Streamlit Ollama Edge-TTS architecture (+40 more)

### Community 3 - "Agent Storage Gateway"
Cohesion: 0.08
Nodes (7): AgentStore, GatewayTests, realtime(), prepare_audio(), start_response(), stop_response(), turn()

### Community 6 - "Agent Integration Documentation"
Cohesion: 0.12
Nodes (29): Agent access defaults disabled, Asynchronous speech jobs query cancel and audio download, Main backend must remain localhost for gateway LAN mode, data/agents/gateway.sqlite3 token hashes and job ownership, /.well-known/asya-agent.json capability discovery, Agent HTTP and MCP integration, Agent gateway on port 8002, Idempotency-Key prevents duplicate generation (+21 more)

### Community 7 - "Agent Runtime Installer"
Cohesion: 0.14
Nodes (4): AgentRuntime, work(), main(), InstallerTests

### Community 8 - "Backend HTTP Routes"
Cohesion: 0.08
Nodes (9): create_app(), audio(), create_voice(), gpu(), recording(), transcribe(), upload(), warmup() (+1 more)

### Community 9 - "Chat Text Processing"
Cohesion: 0.15
Nodes (10): ChatService, event(), speak(), now(), completed_context(), speech_text(), split_sentences(), conversation_prompt() (+2 more)

### Community 10 - "Browser Audio Capture"
Cohesion: 0.15
Nodes (6): AudioQueue, Microphone, pcmWav(), SpeechCapture, feed(), vitest

### Community 11 - "Studio Audio Processing"
Cohesion: 0.22
Nodes (6): convert_audio(), export_mp3(), pace_audio(), peaks(), gpu_status(), wav_bytes()

### Community 12 - "TTS Runtime Provisioning"
Cohesion: 0.18
Nodes (10): ChatterboxProvider, main(), transcribe_request(), PacingTests, main(), check_runtime(), check_stt(), download_tts() (+2 more)

### Community 13 - "Async Network Verification"
Cohesion: 0.16
Nodes (3): serve(), SharedServer, verify()

### Community 15 - "Agent API Security"
Cohesion: 0.23
Nodes (15): guide(), create_app(), audio(), authorize(), cancel(), discovery(), dispatch(), execute() (+7 more)

### Community 16 - "Backend API Schemas"
Cohesion: 0.20
Nodes (9): settings(), Chat, ConversationCreate, Job, Metrics, Segment, Settings, Voice (+1 more)

### Community 18 - "Frontend Build Configuration"
Cohesion: 0.13
Nodes (14): engines, node, name, private, type, version, openapi-typescript, prettier (+6 more)

### Community 19 - "TypeScript Compiler Configuration"
Cohesion: 0.12
Nodes (15): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+7 more)

### Community 24 - "Windows Setup Workflow"
Cohesion: 0.32
Nodes (10): Assert-ServerStopped(), Find-Python311(), Initialize-Chatterbox(), Invoke-Checked(), Prepare-Venv(), Start-AsyaSetup(), Assert-True(), Expect-Error() (+2 more)

### Community 26 - "Streaming Speech Design"
Cohesion: 0.29
Nodes (11): FFmpeg atempo preserves pitch while changing duration, Cancellation stops subsequent segments and avoids queue deadlocks, Chatterbox completes inference per audio chunk, SpeechChunker punctuation aware phrase segmentation, Reference conditioning cached until voice or file changes, Streaming speech and pacing design, Exclude hidden thinking and code blocks from speech, Separate TTS producer from LLM consumer (+3 more)

### Community 27 - "Conversation Screenshot"
Cohesion: 0.20
Nodes (11): Audio playback, Clear conversation control, Conversation messages, LLM status, Memory status, Microphone active status, Spoken response enabled, Text and microphone input (+3 more)

### Community 30 - "Frontend Development Dependencies"
Cohesion: 0.20
Nodes (10): devDependencies, openapi-typescript, @playwright/test, prettier, @types/react, @types/react-dom, typescript, vite (+2 more)

### Community 31 - "Studio Interface Screenshot"
Cohesion: 0.27
Nodes (10): ASYA voice studio interface, Audio output panel, CFG weight slider, Chatterbox Multilingual V3 local CUDA engine, Expression intensity slider, Expression profile presets, Local processing notice, Text to speech editor (+2 more)

### Community 32 - "Local Agent Administration"
Cohesion: 0.25
Nodes (3): router(), access(), state()

### Community 34 - "MCP Stdio Adapter"
Cohesion: 0.33
Nodes (4): execute(), get_capabilities(), guide(), request()

### Community 36 - "Backend Python Dependencies"
Cohesion: 0.22
Nodes (9): Backend API dependencies, fastapi==0.146.0, httpx==0.28.1, imageio-ffmpeg==0.6.0, pydantic==2.14.1, python-multipart==0.0.32, soundfile==0.14.0, uvicorn==0.54.0 (+1 more)

### Community 37 - "Desktop Packaging Proposal"
Cohesion: 0.28
Nodes (9): Backed up verified migration to OS application data directory, Tauri Electron packaging plan not implemented, LM Studio remains external, Versioned GPU runtime and isolated STT installation, Random localhost port and per-session access token, Tauri 2 or Electron shell decision, Stop only application owned processes, Python backend sidecar after health check (+1 more)

### Community 38 - "Legacy Settings Screenshot"
Cohesion: 0.28
Nodes (9): Audio playback, Conversation context usage tip, Conversation messages, Reset speech speed control, Speech speed slider, Spoken response enabled, Text and microphone input, Turkish AI assistant settings screenshot (+1 more)

### Community 39 - "Stored Resource Routes"
Cohesion: 0.25
Nodes (8): conversation(), delete_conversation(), delete_generation(), delete_voice(), get(), job(), update_voice(), voice()

### Community 40 - "Frontend NPM Scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, format, preview, test, test:e2e, types:api

### Community 41 - "Voice Chat Screenshot"
Cohesion: 0.29
Nodes (8): ASYA voice chat interface, Backend connection status, LM Studio model selection, Local processing notice, Microphone and text input, Speech interruption toggle, Spoken response toggle, Voice profile selection

### Community 44 - "Main Runtime Dependencies"
Cohesion: 0.29
Nodes (7): ./chatterbox, apps/backend/requirements.txt, Main speech runtime dependencies, huggingface-hub>=1.4,<2, torch==2.10.0, torchaudio==2.10.0, torchvision==0.25.0

### Community 45 - "Agent Python Dependencies"
Cohesion: 0.33
Nodes (6): Agent gateway dependencies, fastapi==0.162.0, httpx==0.28.1, mcp==2.3.0, python-multipart==0.0.32, uvicorn==0.54.0

### Community 46 - "Generated API Types"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 47 - "Historical Streamlit Architecture"
Cohesion: 0.53
Nodes (6): Historical ASYA Streamlit documentation, Microsoft Edge-TTS speech synthesis, Ollama Mistral 7B local LLM, SQLite conversation memory, Legacy Streamlit main.py UI, Whisper speech recognition

### Community 50 - "Stream Response Helpers"
Cohesion: 0.50
Nodes (5): cancel(), llm_chat(), stream(), emit(), run()

### Community 51 - "Frontend Runtime Dependencies"
Cohesion: 0.50
Nodes (4): dependencies, lucide-react, react, react-dom

### Community 53 - "Isolated STT Dependencies"
Cohesion: 0.67
Nodes (3): ctranslate2==4.8.3, Isolated STT dependencies, faster-whisper==1.2.1

### Community 54 - "Frontend HTML Entry"
Cohesion: 1.00
Nodes (3): ASYA Turkish HTML entry point, /src/main.tsx module entry, React root DOM container

## Knowledge Gaps
- **71 isolated node(s):** `@types/react`, `@types/react-dom`, `openapi-typescript`, `prettier`, `typescript` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 300 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `Backend HTTP Routes` to `Local Agent Administration`, `Speech Job Queue`, `Agent Storage Gateway`, `Agent Runtime Installer`, `Stored Resource Routes`, `Chat Text Processing`, `Agent Credential Storage`, `Voice Input Validation`, `Studio Audio Processing`, `Backend API Schemas`, `Stream Response Helpers`, `Installer Test Utilities`, `Request Access Limits`, `LAN Access Configuration`, `Network Security Tests`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `create_app()` (e.g. with `lifespan()` and `NetworkAccess`) actually correct?**
  _`create_app()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@types/react`, `@types/react-dom`, `openapi-typescript` to the rest of the system?**
  _71 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Frontend Pages` be split into smaller, more focused modules?**
  _Cohesion score 0.09192886456908345 - nodes in this community are weakly interconnected._
- **Why does `Store` connect `Speech Job Queue` to `Runtime Verification Utilities`, `Chat API Tests`, `Backend HTTP Routes`, `Chat Text Processing`, `Studio Audio Processing`, `TTS Runtime Provisioning`, `Backend API Schemas`, `Installer Test Utilities`, `Streaming Cancellation Tests`, `LAN Access Configuration`, `Network Security Tests`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `Store` (e.g. with `NetworkTests` and `SetupSettingsTests`) actually correct?**
  _`Store` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Should `Speech Job Queue` be split into smaller, more focused modules?**
  _Cohesion score 0.06811263318112633 - nodes in this community are weakly interconnected._

Token accounting: host-agent usage was not exposed; zero counters are placeholders, not measured usage.
