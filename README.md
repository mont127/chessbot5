# Chess Bot

Run the GUI:

```bash
python3 -m pip install -r requirements.txt
python3 Main.py
```

`Main.py` starts a local browser GUI. The bot uses iterative-deepening alpha-beta search, move ordering, quiescence search, positional evaluation, pruning, and a transposition cache. The GUI allows bot depth 1-10 and a per-move time budget. Depth is a ceiling; the bot searches as deep as it can before the time budget expires.

Optional GPU evaluator:

```bash
python3 -m pip install -r requirements-gpu.txt
```

When PyTorch can see CUDA or Apple MPS, the engine uses it for leaf position evaluation and the GUI shows the active backend.

For this pure-Python alpha-beta engine, CPU is usually faster than GPU because chess positions are tiny and move generation/search branching stay CPU-bound. Keep GPU off unless you want to compare it.
