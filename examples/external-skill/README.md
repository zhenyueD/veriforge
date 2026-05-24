# Example: monetize a third-party skill in one line

This skill is **not part of VeriForge** — it lives outside `skills/` to play the role
of an external author. It shows the marketplace's supply side: anyone can list a
skill and earn per call without touching the marketplace repo.

## What the author did

1. Copied one file — [`veriforge.py`](./veriforge.py) — next to their skill.
2. Added one line to their FastAPI app ([`skill.py`](./skill.py)):

```python
from veriforge import monetize

monetize(app, skill_id="community-readability", price_usdc=0.003,
         pay_to="0xC0MMUN1TY...", registry="http://localhost:8000", self_register=True)
```

That single call gives the skill: an x402 pay-per-call gate (payment routes to the
author's `pay_to`, minus the platform fee), and self-registration to the marketplace
on startup.

## Run the demo

With the VeriForge stack already up (`docker compose up -d`):

```bash
bash examples/external-skill/run-demo.sh
```

You'll see the marketplace go from 10 → 11 skills as the external skill self-registers,
the new skill appear in `GET /skills` with its earnings split, its `/invoke` return
`402` without payment, and a paid call return a readability score — all with **zero
changes to the marketplace repo**.

> The demo registers the skill into the *running* registry only. The committed seed
> `registry.json` stays at 10 — listing happens live, which is the point.
