# NEXUS

**NEXUS** is a demo for exploring scientific literature as an interactive research map.

Instead of returning a flat list of papers, NEXUS starts from a natural-language research intent, generates Semantic Scholar queries, lets the user select interesting seed papers, expands the search through recommendations, and visualizes the result as a weighted 3D graph.

The current demo focuses on the research pipeline up to the **user profile vector** and the visual graph. The RAG agent is represented as an interface layer and is planned as the next integration step.

## Demo

The main demo is the standalone visual experience:

```text
nexus.html
```

Open `nexus.html` in a browser. It loads:

- `three.min.js` for the 3D globe
- `nexus_real.js` for real precomputed Semantic Scholar data

This mode is designed for the pitch: fast, offline-safe, and without API latency on stage.

## What It Does

1. Takes onboarding answers from the user:
   - specific topic
   - approach or method
   - research field / known state of the art
   - sorting preference: citations, year, or mixed

2. Generates 3 editable Semantic Scholar queries.

3. Fetches 2 seed papers per query.

4. Lets the user mark papers as interesting or not interesting.

5. Sends selected papers as positive IDs and rejected papers as negative IDs to Semantic Scholar Recommendations.

6. Fetches paper embeddings with the Semantic Scholar Graph API.

7. Builds a weighted graph using:
   - embedding similarity
   - co-citation / shared references
   - direct citation links
   - user feedback

8. Computes a user profile vector from the selected papers.

9. Displays the resulting research landscape as an interactive 3D graph.

## Architecture

```text
User onboarding
      |
      v
Query builder
      |
      v
Semantic Scholar search
      |
      v
Seed paper selection
      |
      v
Positive / negative paper IDs
      |
      v
Semantic Scholar recommendations
      |
      v
Paper details + SPECTER embeddings
      |
      v
Weighted graph + user profile vector
      |
      v
3D research map + RAG
```

## Backend

The backend is in `backend/` and uses only the Python standard library.

No `pip install` is required for the current backend.

### Configure API Key

Copy the example env file:

```powershell
Copy-Item backend\.env.example backend\.env
```

Then set:

```text
S2_API_KEY=your-semantic-scholar-api-key
```

The `.env` file is ignored by git and must not be committed.

### Generate Real Demo Data

Run the pipeline and export real data for the frontend:

```powershell
cd backend
python export_demo.py "spiking neural networks" "optimization" "neuromorphic computing"
```

This creates:

```text
backend/out/graph.json
backend/out/nexus_real.json
nexus_real.js
```

`nexus_real.js` is the file loaded by `nexus.html`.

### Run Live Backend

For a live version connected through HTTP:

```powershell
cd backend
python server.py
```

Server URL:

```text
http://localhost:8000
```

Available endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/queries` | Generate 3 queries from onboarding |
| `POST` | `/api/seed` | Fetch seed papers from Semantic Scholar |
| `POST` | `/api/graph` | Build recommendations, graph, and profile vector |

## Graph Scoring

Edges are weighted with (*weights are fixed for the demo*):

```text
weight = 0.50 * cosine_similarity
       + 0.30 * co_citation
       + 0.15 * direct_citation
       + 0.05 * user_feedback
```

The profile vector is computed as a weighted average of the embeddings of the papers selected by the user, with a small recency boost for newer papers.


## RAG and Chat Agent Integration Plan

The final agent layer is not fully implemented in this demo. The intended flow is:

1. Use the graph, selected papers, rejected papers, and profile vector as context.
2. Retrieve relevant graph nodes and nearby papers for a user question.
3. Ask a RAG agent to suggest:
   - promising research directions
   - missing concepts
   - new Semantic Scholar queries
   - positive and negative seed papers for expansion
4. Can create useful context for starting experiments (e.g. with FlyWhale):
   - concept name
   - selected paper IDs
   - graph cluster context
   - open research questions

## Notes

- The polished NEXUS demo is `nexus.html`.
- The Vite/React scaffold in `src/` is not required to run the NEXUS pitch demo.
- The recommended pitch mode is precomputed real data via `export_demo.py`, because it avoids live network delays and Semantic Scholar rate limits.
