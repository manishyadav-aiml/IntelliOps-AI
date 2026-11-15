# Contributing

1. Create a branch from `main`.
2. Backend: `make backend-lint` and `make backend-test` must pass. Frontend: `npm run lint && npm test`.
3. Never commit `.env` files, API keys, datasets, uploaded logs/documents or trained model files.
4. Update documentation in the same change when behaviour changes.
5. Do not report test results or model metrics you have not actually produced.
