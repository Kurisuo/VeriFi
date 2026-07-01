# AGENTS.md

## Cursor Cloud specific instructions

### Repo state (important)
VeriFi is an early-stage project. On `main` the code is a skeleton:
- `core-vector-db.cpp` — placeholder (comments only, no `main`); compiles to an empty object.
- `API_Connector/SETUP.md` — describes a backend that is not yet committed (no `CMakeLists.txt`/`src/` yet).
- `README.md` — project overview (C++ vector DB + backend bridge + React frontend + Python ingestion).

Actual component code lives on feature branches. For example, the `data-ingestion`
branch contains the Python ingestion pipeline (`data_ingestion/`, `requirements.txt`
pinning `PyMuPDF`, and a sample PDF in `source_files/`). Expect files referenced in
docs to be absent on `main` until the corresponding branch is merged.

### Toolchains (all preinstalled, no install needed)
g++ 13, CMake 3.28, GNU Make, Python 3.12 (`pip`), Node 22, npm 10.

### Gotchas
- Default `c++`/`cc` resolves to **Clang 18, which cannot link `-lstdc++`** in this
  image. Use **g++/gcc** for C++ builds. For CMake, pass
  `-DCMAKE_CXX_COMPILER=g++ -DCMAKE_C_COMPILER=gcc` (or compile directly with
  `g++ -std=c++17 ...`). Building with `g++` directly works out of the box.
- The planned `API_Connector` backend uses CMake `FetchContent` to pull
  `cpp-httplib`, `nlohmann/json`, and `cpr` at configure time — this needs network
  access (available here).
- `pip install` works and installs to `~/.local`; console scripts land in
  `~/.local/bin`, which is not on `PATH` by default (import-based usage is fine).

### Build / run
- C++ (single file): `g++ -std=c++17 -O2 -Wall file.cpp -o out && ./out`
- C++ (CMake project, once added): `cmake -S . -B build -DCMAKE_CXX_COMPILER=g++ && cmake --build build`
- Python ingestion (on `data-ingestion`): `pip install -r requirements.txt` then `python3 data_ingestion/main.py`

The update script installs deps only when a manifest is present: `requirements.txt`
(pip) and/or `package.json` (npm). On `main` neither exists, so it is a no-op.
