from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class ChessBoard:
    """Represents the chess board state and provides utility methods"""
    
    def __init__(self):
        # Use Unicode chess pieces for better visualization
        self.piece_map = {
            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',  # White pieces
            'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',  # Black pieces
            '.': ' '  # Empty square
        }
        
        self.board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],  # Black pieces
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],  # Black pawns
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
            ['.', '.', '.', '.', '.', '.', '.', '.'],  # Empty row
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],  # White pawns
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']   # White pieces
        ]
    
    def get_board_state(self) -> str:
        """Returns a formatted string representation of the current board state"""
        # Unicode characters for board edges and pieces
        border = "  ┌───┬───┬───┬───┬───┬───┬───┬───┐"
        middle = "  ├───┼───┼───┼───┼───┼───┼───┼───┤"
        bottom = "  └───┴───┴───┴───┴───┴───┴───┴───┘"
        files  = "    a   b   c   d   e   f   g   h  "
        
        board_str = []
        board_str.append(files)
        board_str.append(border)
        
        for i, row in enumerate(self.board):
            # Add rank number and pieces
            board_row = f"{8-i} │"
            for piece in row:
                # Convert piece to Unicode character
                piece_char = self.piece_map[piece]
                board_row += f" {piece_char} │"
            
            board_str.append(board_row)
            board_str.append(middle if i < 7 else bottom)
        
        return "\n".join(board_str)
    
    def update_position(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> None:
        """Updates the board with a new move"""
        piece = self.board[from_pos[0]][from_pos[1]]
        self.board[from_pos[0]][from_pos[1]] = '.'
        self.board[to_pos[0]][to_pos[1]] = piece
    
    def is_valid_position(self, pos: Tuple[int, int]) -> bool:
        """Checks if a position is within the board boundaries"""
        return 0 <= pos[0] < 8 and 0 <= pos[1] < 8 

    def is_valid_move(self, move: str) -> bool:
        """Validates if a move string is in the correct format (e.g., 'e2e4')"""
        if len(move) != 4:
            return False
        
        file_chars = 'abcdefgh'
        rank_chars = '12345678'
        
        from_file, from_rank = move[0], move[1]
        to_file, to_rank = move[2], move[3]
        
        return all([
            from_file in file_chars,
            from_rank in rank_chars,
            to_file in file_chars,
            to_rank in rank_chars
        ])

    def algebraic_to_index(self, move: str) -> tuple[tuple[int, int], tuple[int, int]]:
        """Converts algebraic notation (e.g., 'e2e4') to board indices"""
        file_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}
        
        from_file, from_rank = move[0], int(move[1])
        to_file, to_rank = move[2], int(move[3])
        
        from_pos = (8 - from_rank, file_map[from_file])
        to_pos = (8 - to_rank, file_map[to_file])
        
        return from_pos, to_pos 

    def get_piece_name(self, piece: str) -> str:
        """Returns the full name of a piece from its symbol"""
        piece_names = {
            'K': 'King',
            'Q': 'Queen',
            'R': 'Rook',
            'B': 'Bishop',
            'N': 'Knight',
            'P': 'Pawn',
            'k': 'King',
            'q': 'Queen',
            'r': 'Rook',
            'b': 'Bishop',
            'n': 'Knight',
            'p': 'Pawn'
        }
        return piece_names.get(piece, 'Unknown')

    def get_piece_at_position(self, pos: Tuple[int, int]) -> str:
        """Returns the piece at the given position"""
        return self.board[pos[0]][pos[1]] 