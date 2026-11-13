# Contributing

LIPE welcomes reproducible corrections, tests and documentation. Open an issue
before a large scientific change so the observable, reference theory, units and
validation authority can be agreed first.

## Development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements/validation.lock
python -m pip install --no-deps -e .
pytest
```

Every physics change must state the equation, frame, time scale, sign, units,
assumptions and expected accuracy. Add analytical tests and, where possible, an
independent reference fixture with provenance. Do not change constants or fit a
scale, offset or phase merely to improve agreement.

Keep gravitational forcing separate from illuminance and from unrelated
application-layer data. New reference data must have documented redistribution
terms and checksums. Never commit BSP kernels, credentials, personal data,
virtual environments, caches, generated plots or local paths.

Run `python -m build`, install the resulting wheel in a clean environment, and
exercise the API and CLI before requesting review. By contributing, you agree
that your LIPE contribution is provided under the MIT License; changes to the
separate MPL-covered experimental patch remain MPL-2.0.
