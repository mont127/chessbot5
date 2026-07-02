import math
import time

import chess as ch


MATE_SCORE = 100000
EXACT = 0
LOWER_BOUND = 1
UPPER_BOUND = 2

PIECE_VALUES = {
    ch.PAWN: 100,
    ch.KNIGHT: 320,
    ch.BISHOP: 330,
    ch.ROOK: 500,
    ch.QUEEN: 900,
    ch.KING: 0,
}

PIECE_SQUARE_TABLES = {
    ch.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5, 5, 10, 25, 25, 10, 5, 5,
        0, 0, 0, 20, 20, 0, 0, 0,
        5, -5, -10, 0, 0, -10, -5, 5,
        5, 10, 10, -20, -20, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0,
    ],
    ch.KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50,
    ],
    ch.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20,
    ],
    ch.ROOK: [
        0, 0, 0, 5, 5, 0, 0, 0,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        5, 10, 10, 10, 10, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0,
    ],
    ch.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20,
    ],
    ch.KING: [
        20, 30, 10, 0, 0, 10, 30, 20,
        20, 20, 0, 0, 0, 0, 20, 20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
    ],
}


class SearchTimeout(Exception):
    pass


class Engine:
    def __init__(self, board=None, maxDepth=3, color=None, use_gpu=True, time_limit=2.5):
        self.board = board or ch.Board()
        self.color = color if color is not None else self.board.turn
        self.maxDepth = max(1, int(maxDepth or 1))
        self.time_limit = max(0.1, float(time_limit or 2.5))
        self.nodes = 0
        self.best_score = 0
        self.completed_depth = 0
        self.elapsed = 0
        self._start_time = 0
        self._deadline = 0
        self._table = {}
        self._killer_moves = {}
        self._history_scores = {}
        self._best_root_move = None
        self._torch = None
        self.gpu_device = None
        self.backend_name = "CPU"
        if use_gpu:
            self._init_gpu_backend()

    def getBestMove(self):
        move, score = self.find_best_move()
        self.best_score = score
        return move

    def find_best_move(self):
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            return None, self.evaluate()

        self.nodes = 0
        self.completed_depth = 0
        self._start_time = time.perf_counter()
        self._deadline = self._start_time + self.time_limit
        best_move = legal_moves[0]
        best_score = -math.inf

        for depth in range(1, self.maxDepth + 1):
            try:
                move, score = self._search_root(depth)
            except SearchTimeout:
                break
            if move is not None:
                best_move = move
                best_score = score
                self._best_root_move = move
                self.completed_depth = depth
            if abs(best_score) > MATE_SCORE - 100:
                break

        if best_score == -math.inf:
            best_score = self.evaluate()
        self.elapsed = time.perf_counter() - self._start_time
        return best_move, best_score

    def _search_root(self, depth):
        alpha = -math.inf
        beta = math.inf
        best_move = None
        best_score = -math.inf

        for move in self._ordered_moves(list(self.board.legal_moves), 0):
            self._check_time()
            self.board.push(move)
            score = -self._negamax(depth - 1, -beta, -alpha, 1)
            self.board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)

        return best_move, best_score

    def _negamax(self, depth, alpha, beta, ply):
        self.nodes += 1
        if self.nodes & 2047 == 0:
            self._check_time()

        alpha_original = alpha
        key = self._board_key()
        entry = self._table.get(key)
        if entry and entry["depth"] >= depth:
            if entry["flag"] == EXACT:
                return entry["score"]
            if entry["flag"] == LOWER_BOUND:
                alpha = max(alpha, entry["score"])
            elif entry["flag"] == UPPER_BOUND:
                beta = min(beta, entry["score"])
            if alpha >= beta:
                return entry["score"]

        if self.board.is_checkmate():
            return -MATE_SCORE + ply
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            return 0
        if depth <= 0:
            return self._quiescence(alpha, beta, ply)

        best_score = -math.inf
        best_move = None
        legal_moves = list(self.board.legal_moves)
        in_check = self.board.is_check()

        # Null-move pruning cuts obvious quiet positions. Avoid it in check and shallow nodes.
        if depth >= 3 and beta < math.inf and not in_check and self._has_non_pawn_material(self.board.turn):
            self.board.push(ch.Move.null())
            score = -self._negamax(depth - 3, -beta, -beta + 1, ply + 1)
            self.board.pop()
            if score >= beta:
                return beta

        for move in self._ordered_moves(legal_moves, ply):
            self.board.push(move)
            extension = 1 if self.board.is_check() and depth <= 3 else 0
            score = -self._negamax(depth - 1 + extension, -beta, -alpha, ply + 1)
            self.board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
            if alpha >= beta:
                self._record_cutoff(move, depth, ply)
                break

        flag = EXACT
        if best_score <= alpha_original:
            flag = UPPER_BOUND
        elif best_score >= beta:
            flag = LOWER_BOUND
        self._table[key] = {
            "depth": depth,
            "score": best_score,
            "flag": flag,
            "move": best_move,
        }
        return best_score

    def _quiescence(self, alpha, beta, ply):
        self.nodes += 1
        stand_pat = self.evaluate()
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
        if ply >= self.maxDepth + 5:
            return alpha

        moves = [
            move for move in self.board.legal_moves
            if self.board.is_capture(move) or move.promotion or self.board.gives_check(move)
        ]
        for move in self._ordered_moves(moves, ply):
            self._check_time()
            self.board.push(move)
            score = -self._quiescence(-beta, -alpha, ply + 1)
            self.board.pop()
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _ordered_moves(self, moves, ply):
        table_move = None
        entry = self._table.get(self._board_key())
        if entry:
            table_move = entry.get("move")
        return sorted(
            moves,
            key=lambda move: self._move_score(move, ply, table_move),
            reverse=True,
        )

    def _move_score(self, move, ply, table_move=None):
        if move == table_move:
            return 1_000_000
        if move == self._best_root_move:
            return 900_000

        score = 0
        if self.board.is_capture(move):
            victim = self._captured_piece_type(move)
            attacker = self.board.piece_type_at(move.from_square)
            score += 100_000 + 10 * PIECE_VALUES.get(victim, 0) - PIECE_VALUES.get(attacker, 0)
        if move.promotion:
            score += 80_000 + PIECE_VALUES.get(move.promotion, 0)
        if self.board.gives_check(move):
            score += 20_000

        killers = self._killer_moves.get(ply, ())
        if move in killers:
            score += 15_000
        score += self._history_scores.get((move.from_square, move.to_square), 0)
        if self.board.is_castling(move):
            score += 500
        return score

    def _record_cutoff(self, move, depth, ply):
        if not self.board.is_capture(move):
            killers = list(self._killer_moves.get(ply, ()))
            if move not in killers:
                killers.insert(0, move)
                self._killer_moves[ply] = tuple(killers[:2])
            key = (move.from_square, move.to_square)
            self._history_scores[key] = self._history_scores.get(key, 0) + depth * depth

    def _captured_piece_type(self, move):
        if self.board.is_en_passant(move):
            return ch.PAWN
        return self.board.piece_type_at(move.to_square)

    def evaluate(self):
        if self.board.is_checkmate():
            return -MATE_SCORE if self.board.turn == self.color else MATE_SCORE
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            return 0

        score = self._gpu_piece_score() if self.gpu_device is not None else self._cpu_piece_score()
        score += self._pawn_structure_score()
        score += self._king_safety_score()
        score += self._mobility_score_fast()

        return score if self.board.turn == self.color else -score

    def _cpu_piece_score(self):
        score = 0
        for square, piece in self.board.piece_map().items():
            piece_score = PIECE_VALUES[piece.piece_type] + self._piece_square_score(piece, square)
            if piece.color == self.color:
                score += piece_score
            else:
                score -= piece_score
        return score

    def _gpu_piece_score(self):
        pieces = self.board.piece_map()
        if not pieces:
            return 0

        channels = []
        squares = []
        for square, piece in pieces.items():
            channel = (0 if piece.color == ch.WHITE else 6) + piece.piece_type - 1
            channels.append(channel)
            squares.append(square)

        torch = self._torch
        channel_tensor = torch.tensor(channels, dtype=torch.long, device=self.gpu_device)
        square_tensor = torch.tensor(squares, dtype=torch.long, device=self.gpu_device)
        return int(self._gpu_piece_weights[channel_tensor, square_tensor].sum().item())

    def _piece_square_score(self, piece, square):
        table = PIECE_SQUARE_TABLES[piece.piece_type]
        table_square = square if piece.color == ch.WHITE else ch.square_mirror(square)
        return table[table_square]

    def _pawn_structure_score(self):
        score = 0
        for color in (self.color, not self.color):
            sign = 1 if color == self.color else -1
            pawns = self.board.pieces(ch.PAWN, color)
            files = [ch.square_file(square) for square in pawns]
            for file_index in set(files):
                count = files.count(file_index)
                if count > 1:
                    score -= sign * 12 * (count - 1)
            for square in pawns:
                file_index = ch.square_file(square)
                neighbor_files = {file_index - 1, file_index + 1}
                if not any(file in files for file in neighbor_files):
                    score -= sign * 10
                rank = ch.square_rank(square)
                advance = rank if color == ch.WHITE else 7 - rank
                if advance >= 4:
                    score += sign * 8 * advance
        return score

    def _mobility_score_fast(self):
        # Exact mobility costs full legal move generation twice. This cheap proxy rewards active pieces.
        score = 0
        for color in (self.color, not self.color):
            sign = 1 if color == self.color else -1
            score += sign * 4 * len(self.board.pieces(ch.KNIGHT, color))
            score += sign * 5 * len(self.board.pieces(ch.BISHOP, color))
            score += sign * 2 * len(self.board.pieces(ch.ROOK, color))
            score += sign * 1 * len(self.board.pieces(ch.QUEEN, color))
        return score

    def _king_safety_score(self):
        score = 0
        for color in (self.color, not self.color):
            sign = 1 if color == self.color else -1
            king_square = self.board.king(color)
            if king_square is None:
                continue
            file_index = ch.square_file(king_square)
            rank_index = ch.square_rank(king_square)
            home_rank = 0 if color == ch.WHITE else 7
            if rank_index == home_rank and file_index in (1, 2, 6):
                score += sign * 30
            if self.board.has_kingside_castling_rights(color):
                score += sign * 10
            if self.board.has_queenside_castling_rights(color):
                score += sign * 8
        return score

    def _has_non_pawn_material(self, color):
        return bool(
            self.board.pieces(ch.KNIGHT, color)
            or self.board.pieces(ch.BISHOP, color)
            or self.board.pieces(ch.ROOK, color)
            or self.board.pieces(ch.QUEEN, color)
        )

    def _check_time(self):
        if time.perf_counter() >= self._deadline:
            raise SearchTimeout

    def _init_gpu_backend(self):
        try:
            import torch
        except Exception:
            return

        device_name = None
        if torch.cuda.is_available():
            device_name = "cuda"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            device_name = "mps"

        if device_name is None:
            return

        self._torch = torch
        self.gpu_device = torch.device(device_name)
        self.backend_name = f"GPU ({device_name.upper()})"
        self._gpu_piece_weights = self._build_gpu_piece_weights()

    def _build_gpu_piece_weights(self):
        torch = self._torch
        weights = torch.zeros((12, 64), dtype=torch.float32, device=self.gpu_device)
        for color in (ch.WHITE, ch.BLACK):
            for piece_type in PIECE_VALUES:
                channel = (0 if color == ch.WHITE else 6) + piece_type - 1
                sign = 1 if color == self.color else -1
                table = PIECE_SQUARE_TABLES[piece_type]
                for square in ch.SQUARES:
                    table_square = square if color == ch.WHITE else ch.square_mirror(square)
                    weights[channel, square] = sign * (PIECE_VALUES[piece_type] + table[table_square])
        return weights

    def _board_key(self):
        try:
            return self.board._transposition_key()
        except AttributeError:
            return (
                self.board.board_fen(),
                self.board.turn,
                self.board.castling_rights,
                self.board.ep_square,
            )

    # Compatibility wrappers for the recovered console code names.
    def evalFunct(self):
        return self.evaluate()

    def engine(self, candidate=None, depth=1):
        return self.getBestMove()
