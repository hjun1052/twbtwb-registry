# TWBTWB Registry

GitHub JSON source of truth for TWBTWB `tw://` resolution.

Current live Big Registry:

```text
https://raw.githubusercontent.com/hjun1052/twbtwb-registry/main/big-registry.json
```

Validation runs in GitHub Actions on every push and pull request. The validator
checks schema version, duplicate names, HTTPS-only URLs, local-host blocking,
and Big Registry references to local registry files.
