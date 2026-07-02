import json
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import chess as ch

from ChessEngine import Engine


HOST = "127.0.0.1"
DEFAULT_PORT = 8765


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chess Bot</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #171c22;
      --panel: #242d36;
      --panel-2: #2e3945;
      --line: #45515f;
      --text: #eef2f6;
      --muted: #a8b2bf;
      --light: #ede6cf;
      --dark: #6f9458;
      --accent: #edc65a;
      --blue: #529cf5;
      --danger: #d65c5c;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }

    .app {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(320px, 680px) minmax(260px, 340px);
      gap: 24px;
      align-items: start;
      justify-content: center;
      padding: 28px;
    }

    .board-wrap {
      width: min(86vw, 680px);
    }

    .board {
      width: 100%;
      aspect-ratio: 1;
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      grid-template-rows: repeat(8, 1fr);
      border: 2px solid #101419;
      user-select: none;
    }

    .square {
      position: relative;
      display: grid;
      place-items: center;
      cursor: default;
    }

    .square.light { background: var(--light); }
    .square.dark { background: var(--dark); }
    .square.selected { outline: 4px solid var(--blue); outline-offset: -4px; }
    .square.last::before {
      content: "";
      position: absolute;
      inset: 0;
      background: rgba(237, 198, 90, 0.42);
    }
    .square.check::before {
      content: "";
      position: absolute;
      inset: 0;
      background: rgba(214, 92, 92, 0.55);
    }
    .square.legal::after {
      content: "";
      position: absolute;
      width: 18%;
      height: 18%;
      border-radius: 50%;
      background: rgba(24, 31, 39, 0.58);
    }

    .piece {
      position: relative;
      z-index: 1;
      font-family: "Segoe UI Symbol", "Apple Symbols", "DejaVu Sans", Arial, sans-serif;
      font-size: clamp(34px, 8vw, 66px);
      line-height: 1;
      transform: translateY(-2px);
    }

    .piece.white { color: #fafafa; text-shadow: 0 2px 0 rgba(0, 0, 0, 0.28); }
    .piece.black { color: #111820; text-shadow: 0 1px 0 rgba(255, 255, 255, 0.26); }

    .coords {
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      padding-top: 8px;
    }

    .coords span { text-align: center; }

    .panel {
      width: min(86vw, 340px);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
    }

    h1 {
      margin: 0 0 18px;
      font-size: 30px;
      letter-spacing: 0;
    }

    .stat {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 15px;
    }

    .stat span:first-child { color: var(--muted); }
    .stat span:last-child { text-align: right; }

    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin: 18px 0;
    }

    button {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-2);
      color: var(--text);
      min-height: 38px;
      padding: 0 12px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
    }

    button:hover:enabled { background: #394757; }
    button.active { background: var(--accent); color: #1f252b; border-color: var(--accent); }
    button:disabled { opacity: 0.45; cursor: default; }

    .wide { grid-column: 1 / -1; }

    .status {
      min-height: 58px;
      color: var(--text);
      line-height: 1.35;
      margin: 12px 0 18px;
    }

    .moves {
      max-height: 220px;
      overflow: auto;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.7;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 12px;
    }

    .moves strong {
      color: var(--accent);
      display: block;
      margin-bottom: 6px;
    }

    @media (max-width: 900px) {
      .app {
        grid-template-columns: 1fr;
        padding: 14px;
      }
      .board-wrap,
      .panel {
        width: 100%;
        max-width: 680px;
        margin: 0 auto;
      }
    }
  </style>
</head>
<body>
  <main class="app">
    <section class="board-wrap">
      <div id="board" class="board"></div>
      <div id="coords" class="coords"></div>
    </section>
    <aside class="panel">
      <h1>Chess Bot</h1>
      <div class="stat"><span>Turn</span><span id="turn">White</span></div>
      <div class="stat"><span>You</span><span id="side">White</span></div>
      <div class="stat"><span>Depth</span><span id="depth">3</span></div>
      <div class="stat"><span>Move Time</span><span id="timeLimit">2.5s</span></div>
      <div class="stat"><span>Backend</span><span id="backend">Auto</span></div>

      <div class="controls">
        <button id="newGame">New Game</button>
        <button id="undo">Undo</button>
        <button id="white">White</button>
        <button id="black">Black</button>
        <button id="depthDown">- Depth</button>
        <button id="depthUp">+ Depth</button>
        <button id="timeDown">- Time</button>
        <button id="timeUp">+ Time</button>
        <button id="gpu" class="wide">GPU: On</button>
      </div>

      <div id="status" class="status">Loading.</div>
      <div id="moves" class="moves"><strong>Moves</strong></div>
    </aside>
  </main>

  <script>
    const symbols = {
      K: "\u2654", Q: "\u2655", R: "\u2656", B: "\u2657", N: "\u2658", P: "\u2659",
      k: "\u265A", q: "\u265B", r: "\u265C", b: "\u265D", n: "\u265E", p: "\u265F"
    };

    let state = null;
    let selected = null;
    let thinking = false;

    async function api(path, body = null) {
      const options = body ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      } : {};
      const response = await fetch(path, options);
      state = await response.json();
      thinking = false;
      selected = null;
      render();
    }

    function squareAt(row, col) {
      const files = "abcdefgh";
      if (state.humanColor === "white") {
        return files[col] + String(8 - row);
      }
      return files[7 - col] + String(row + 1);
    }

    function pieceIsHuman(piece) {
      if (!piece) return false;
      const whitePiece = piece === piece.toUpperCase();
      return (state.humanColor === "white" && whitePiece) ||
             (state.humanColor === "black" && !whitePiece);
    }

    function legalTargets(fromSquare) {
      return state.legalMoves
        .filter(move => move.slice(0, 2) === fromSquare)
        .map(move => move.slice(2, 4));
    }

    function legalMove(fromSquare, toSquare) {
      const base = fromSquare + toSquare;
      return state.legalMoves.find(move => move === base + "q") ||
             state.legalMoves.find(move => move === base) ||
             null;
    }

    function onSquare(square) {
      if (thinking || state.gameOver || state.turn !== state.humanColor) return;
      const piece = state.pieces[square];
      if (!selected) {
        if (pieceIsHuman(piece)) selected = square;
        render();
        return;
      }
      if (pieceIsHuman(piece)) {
        selected = square;
        render();
        return;
      }
      const move = legalMove(selected, square);
      if (!move) {
        selected = null;
        render();
        return;
      }
      thinking = true;
      document.getElementById("status").textContent = "Bot is thinking.";
      api("/api/move", { move });
    }

    function renderBoard() {
      const board = document.getElementById("board");
      board.innerHTML = "";
      const targets = selected ? legalTargets(selected) : [];
      for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
          const square = squareAt(row, col);
          const div = document.createElement("div");
          div.className = "square " + ((row + col) % 2 === 0 ? "light" : "dark");
          if (square === selected) div.classList.add("selected");
          if (targets.includes(square)) div.classList.add("legal");
          if (state.lastMove && state.lastMove.includes(square)) div.classList.add("last");
          if (state.checkSquare === square) div.classList.add("check");
          div.addEventListener("click", () => onSquare(square));

          const piece = state.pieces[square];
          if (piece) {
            const span = document.createElement("span");
            span.className = "piece " + (piece === piece.toUpperCase() ? "white" : "black");
            span.textContent = symbols[piece];
            div.appendChild(span);
          }
          board.appendChild(div);
        }
      }
    }

    function renderCoords() {
      const coords = document.getElementById("coords");
      coords.innerHTML = "";
      const files = state.humanColor === "white" ? "abcdefgh" : "hgfedcba";
      for (const file of files) {
        const span = document.createElement("span");
        span.textContent = file;
        coords.appendChild(span);
      }
    }

    function renderMoves() {
      const moves = document.getElementById("moves");
      moves.innerHTML = "<strong>Moves</strong>";
      for (let i = 0; i < state.history.length; i += 2) {
        const line = document.createElement("div");
        line.textContent = `${Math.floor(i / 2) + 1}. ${state.history[i] || ""} ${state.history[i + 1] || ""}`;
        moves.appendChild(line);
      }
    }

    function render() {
      renderBoard();
      renderCoords();
      renderMoves();
      document.getElementById("turn").textContent = state.turn[0].toUpperCase() + state.turn.slice(1);
      document.getElementById("side").textContent = state.humanColor[0].toUpperCase() + state.humanColor.slice(1);
      document.getElementById("depth").textContent = state.depth;
      document.getElementById("timeLimit").textContent = `${state.timeLimit.toFixed(1)}s`;
      document.getElementById("backend").textContent = state.backend;
      document.getElementById("status").textContent = thinking ? "Bot is thinking." : state.message;

      document.getElementById("white").classList.toggle("active", state.humanColor === "white");
      document.getElementById("black").classList.toggle("active", state.humanColor === "black");
      document.getElementById("gpu").classList.toggle("active", state.useGpu);
      document.getElementById("gpu").textContent = state.useGpu ? "GPU: On" : "GPU: Off";
      document.getElementById("undo").disabled = thinking || state.history.length === 0;
    }

    document.getElementById("newGame").onclick = () => api("/api/new", {});
    document.getElementById("undo").onclick = () => api("/api/undo", {});
    document.getElementById("white").onclick = () => api("/api/settings", { humanColor: "white" });
    document.getElementById("black").onclick = () => api("/api/settings", { humanColor: "black" });
    document.getElementById("depthDown").onclick = () => api("/api/settings", { depth: Math.max(1, state.depth - 1) });
    document.getElementById("depthUp").onclick = () => api("/api/settings", { depth: Math.min(10, state.depth + 1) });
    document.getElementById("timeDown").onclick = () => api("/api/settings", { timeLimit: Math.max(0.5, state.timeLimit - 0.5) });
    document.getElementById("timeUp").onclick = () => api("/api/settings", { timeLimit: Math.min(20, state.timeLimit + 0.5) });
    document.getElementById("gpu").onclick = () => api("/api/settings", { useGpu: !state.useGpu });

    api("/api/state");
  </script>
</body>
</html>
"""


class ChessGame:
    def __init__(self):
        self.board = ch.Board()
        self.human_color = ch.WHITE
        self.depth = 3
        self.time_limit = 2.5
        self.use_gpu = False
        self.backend = "CPU"
        self.message = "Your move."
        self.history = []
        self.last_move = None
        self.lock = threading.Lock()

    def state(self):
        with self.lock:
            return self._state_unlocked()

    def new_game(self):
        with self.lock:
            self.board.reset()
            self.history = []
            self.last_move = None
            self.message = "Your move." if self.human_color == ch.WHITE else "Bot is thinking."
            if self.board.turn != self.human_color:
                self._engine_move_unlocked()
            return self._state_unlocked()

    def undo(self):
        with self.lock:
            pops = 2 if len(self.board.move_stack) >= 2 else 1
            for _ in range(pops):
                if self.board.move_stack:
                    self.board.pop()
                if self.history:
                    self.history.pop()
            self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
            self.message = "Move undone."
            return self._state_unlocked()

    def settings(self, payload):
        with self.lock:
            reset_needed = False
            if "humanColor" in payload:
                next_color = ch.WHITE if payload["humanColor"] == "white" else ch.BLACK
                if next_color != self.human_color:
                    self.human_color = next_color
                    reset_needed = True
            if "depth" in payload:
                self.depth = max(1, min(10, int(payload["depth"])))
            if "timeLimit" in payload:
                self.time_limit = max(0.5, min(20.0, float(payload["timeLimit"])))
            if "useGpu" in payload:
                self.use_gpu = bool(payload["useGpu"])
                self.backend = "Auto" if self.use_gpu else "CPU forced"

            if reset_needed:
                self.board.reset()
                self.history = []
                self.last_move = None
                self.message = "Your move." if self.human_color == ch.WHITE else "Bot is thinking."
                if self.board.turn != self.human_color:
                    self._engine_move_unlocked()
            return self._state_unlocked()

    def play_human_move(self, move_uci):
        with self.lock:
            if self.board.is_game_over() or self.board.turn != self.human_color:
                return self._state_unlocked()

            move = ch.Move.from_uci(move_uci)
            if move not in self.board.legal_moves:
                self.message = "Illegal move."
                return self._state_unlocked()

            self.history.append(self.board.san(move))
            self.board.push(move)
            self.last_move = move

            if self.board.is_game_over():
                self.message = self._status_unlocked()
                return self._state_unlocked()

            self.message = "Bot is thinking."
            self._engine_move_unlocked()
            return self._state_unlocked()

    def _engine_move_unlocked(self):
        engine = Engine(
            self.board.copy(stack=False),
            self.depth,
            self.board.turn,
            use_gpu=self.use_gpu,
            time_limit=self.time_limit,
        )
        move = engine.getBestMove()
        self.backend = engine.backend_name
        if move is None:
            self.message = self._status_unlocked() or "Bot has no legal move."
            return

        real_move = ch.Move.from_uci(move.uci())
        if real_move not in self.board.legal_moves:
            self.message = "Bot produced an illegal move."
            return

        san = self.board.san(real_move)
        self.board.push(real_move)
        self.history.append(san)
        self.last_move = real_move
        status = self._status_unlocked()
        if status:
            self.message = status
        else:
            self.message = (
                f"Bot played {san}. Depth {engine.completed_depth}/{self.depth}, "
                f"{engine.nodes:,} nodes in {engine.elapsed:.2f}s. Score {engine.best_score}."
            )

    def _state_unlocked(self):
        status = self._status_unlocked()
        legal_moves = []
        if not self.board.is_game_over() and self.board.turn == self.human_color:
            legal_moves = [move.uci() for move in self.board.legal_moves]

        return {
            "turn": "white" if self.board.turn == ch.WHITE else "black",
            "humanColor": "white" if self.human_color == ch.WHITE else "black",
            "depth": self.depth,
            "timeLimit": self.time_limit,
            "useGpu": self.use_gpu,
            "backend": self.backend,
            "message": status or self.message,
            "gameOver": self.board.is_game_over(),
            "pieces": {
                ch.square_name(square): piece.symbol()
                for square, piece in self.board.piece_map().items()
            },
            "legalMoves": legal_moves,
            "lastMove": [
                ch.square_name(self.last_move.from_square),
                ch.square_name(self.last_move.to_square),
            ] if self.last_move else None,
            "checkSquare": ch.square_name(self.board.king(self.board.turn))
            if self.board.is_check() else None,
            "history": list(self.history),
        }

    def _status_unlocked(self):
        if self.board.is_checkmate():
            winner = "White" if self.board.turn == ch.BLACK else "Black"
            return f"Checkmate. {winner} wins."
        if self.board.is_stalemate():
            return "Draw by stalemate."
        if self.board.is_insufficient_material():
            return "Draw by insufficient material."
        if self.board.is_seventyfive_moves():
            return "Draw by seventy-five move rule."
        if self.board.is_fivefold_repetition():
            return "Draw by fivefold repetition."
        if self.board.is_check():
            return "Check."
        return None


class ChessRequestHandler(BaseHTTPRequestHandler):
    game = ChessGame()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_html(HTML)
        elif path == "/api/state":
            self._send_json(self.game.state())
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self._read_json()
        try:
            if path == "/api/move":
                self._send_json(self.game.play_human_move(payload.get("move", "")))
            elif path == "/api/new":
                self._send_json(self.game.new_game())
            elif path == "/api/undo":
                self._send_json(self.game.undo())
            elif path == "/api/settings":
                self._send_json(self.game.settings(payload))
            else:
                self.send_error(404)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        data = self.rfile.read(length).decode("utf-8")
        return json.loads(data)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class ChessApp:
    def __init__(self, host=HOST, port=DEFAULT_PORT, open_browser=True):
        self.host = host
        self.port = port
        self.open_browser = open_browser

    def run(self):
        port = _available_port(self.host, self.port)
        server = ThreadingHTTPServer((self.host, port), ChessRequestHandler)
        url = f"http://{self.host}:{port}/"
        print(f"Chess Bot GUI running at {url}")
        if self.open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


def _available_port(host, preferred_port):
    for port in range(preferred_port, preferred_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found.")
