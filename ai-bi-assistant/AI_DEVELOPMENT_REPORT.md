# AI-Assisted Development Report

> Complete or edit the bracketed sections to reflect your actual development process before submitting.

## AI tools used

[Fill in the tools you actually used, such as ChatGPT, Cursor, GitHub Copilot, or another assistant.]

## How AI assisted development

[Describe the actual tasks where AI helped: architecture planning, code explanation, test design, debugging, documentation, or UI refinement.]

## Problems encountered

[Record the real errors or design challenges encountered while running the project. Include the error message and the affected component.]

## Debugging steps

[Describe what you actually checked, the changes you made, and the tests you ran to confirm the fix.]

## Technical decisions

- SQLite was selected to keep local setup lightweight for the supplied small CSV.
- FastAPI separates the API from the UI and provides request validation and interactive documentation.
- Streamlit provides a simple Python dashboard.
- The LLM is limited to intent interpretation. SQL analytics calculate the numerical answers deterministically.
- A rule-based fallback keeps core functionality available without an API key.
- Parameterized queries and an allowlist reduce the risk of unsafe query execution.

## What I would improve with one additional day

Potential improvements to consider (include only the ones you would actually pursue):

- Add richer natural-language filters and more robust date parsing.
- Add an explicit preview of flagged records and a data-quality export.
- Add more tests for ties, empty databases, malformed LLM JSON, and extreme values.
- Improve authentication, request limits, logging, and deployment configuration for production use.
- Add business-approved handling for returns and revenue recognition.
