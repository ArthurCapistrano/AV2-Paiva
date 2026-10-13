# Domain Docs

How the engineering skills should consume this repo's domain documentation when
exploring the codebase.

## Before exploring, read these

- **`organizacao-trabalho.md`**: the project proposal, research question,
  experimental methodology, and expected deliverables.
- **`docs/decisoes-experimentais/GLOSSARIO.md`**: canonical experimental vocabulary.
- **`docs/decisoes-experimentais/`**: read numbered decisions that touch the
  area you're about to work in.

The folder's `README.md` indexes accepted decisions and distinguishes planned
procedures from completed experiments.

## File structure

This is a single-context repository:

```text
/
|-- organizacao-trabalho.md
|-- docs/
|   `-- decisoes-experimentais/
|       |-- README.md
|       |-- GLOSSARIO.md
|       `-- 0001-*.md
`-- src/
```

## Use the glossary's vocabulary

When your output names a domain concept in an issue title, hypothesis, test name,
or report, use the term as defined in
`docs/decisoes-experimentais/GLOSSARIO.md`. Don't drift to synonyms the glossary
explicitly avoids.

If the concept you need isn't in the glossary yet, reconsider whether you're
inventing language the project doesn't use or note the real gap for
`/domain-modeling`.

## Flag decision conflicts

If your output contradicts a numbered experimental decision, surface it
explicitly rather than silently overriding:

> _Contradicts decision 0002, but worth reopening because..._
