# Project architecture

```mermaid
flowchart TD
    A["Pinned requirements and Python test sources"] --> B["Requirement conditions with source spans"]
    A --> C["Test assertions and available helper references"]
    B --> D["JSON records and SQLite evidence index"]
    C --> D
    D --> E["Keyword and embedding retrieval"]
    E --> F["One hop helper expansion"]
    F --> G["LLM interpretation and deterministic comparison"]
    G --> H{"Potential absence or partial support"}
    H -- Yes --> I["Review remaining eligible collection"]
    H -- No --> J["Validate evidence and context"]
    I --> J
    J --> K["Completeness route conflict and uncertainty"]
    K --> L["Local engineer review report"]
```

Implemented now: source-span contracts, finding validation, SQLite storage and artificial CLI demonstration. Other blocks remain planned. Human labels and matched baselines form a separate evaluation workflow; system predictions must not be shown to independent annotators. Historical attribution remains optional and requires verified earlier alignment and later mismatch.
