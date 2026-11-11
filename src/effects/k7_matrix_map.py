"""
ASUS TUF Gaming K7 - Keyboard LED Matrix Map (CORRETTO)

I LED sono organizzati per COLONNE VERTICALI (scansione colonna-per-colonna).
Matrice 6 righe x 24 colonne = 105 LED totali (alcune celle vuote).
"""

# Mapping completo: (row, col) -> LED index
# Basato sull'analisi che i LED sono scansionati per colonne verticali
K7_MATRIX_MAP = {
    # COLONNA 0: ESC, `, Tab, Caps, LShift, LCtrl
    (0, 0): 0,   # ESC
    (1, 0): 1,   # `
    (2, 0): 2,   # Tab
    (3, 0): 3,   # Caps Lock
    (4, 0): 4,   # Left Shift
    (5, 0): 5,   # Left Control

    # COLONNA 1: gap, 1, \ISO, LWin, F1, 2 (*)
    # (*) Nota: l'ordine suggerisce che F1 è nella riga function, non nella posizione fisica
    (1, 1): 6,   # 1
    (4, 1): 7,   # \ (ISO)
    (5, 1): 8,   # Left Windows
    # F1 è fuori ordine - salta alla riga 0
    (0, 2): 9,   # F1 (in realtà colonna separata)
    (1, 2): 10,  # 2

    # COLONNA 2-3: Q, A, Z, LAlt, F2, 3
    (2, 2): 11,  # Q
    (3, 2): 12,  # A
    (4, 2): 13,  # Z
    (5, 2): 14,  # Left Alt
    (0, 3): 15,  # F2
    (1, 3): 16,  # 3

    # COLONNA 3-4: W, S, X, (gap), F3, 4
    (2, 3): 17,  # W
    (3, 3): 18,  # S
    (4, 3): 19,  # X
    (0, 4): 20,  # F3
    (1, 4): 21,  # 4

    # COLONNA 4-5: E, D, C, (gap), F4, 5
    (2, 4): 22,  # E
    (3, 4): 23,  # D
    (4, 4): 24,  # C
    (0, 5): 25,  # F4
    (1, 5): 26,  # 5

    # COLONNA 5-6: R, F, V, (gap), (gap), 6
    (2, 5): 27,  # R
    (3, 5): 28,  # F
    (4, 5): 29,  # V
    (1, 6): 30,  # 6

    # COLONNA 3-9: Space (wide key spanning from X to comma)
    (5, 3): 34,  # Space (starts under X, extends to comma)

    # COLONNA 6-7: T, G, B, F5, 7
    (2, 6): 31,  # T
    (3, 6): 32,  # G
    (4, 6): 33,  # B
    (0, 7): 35,  # F5
    (1, 7): 36,  # 7

    # COLONNA 7-8: Y, H, N, (gap), F6, 8
    (2, 7): 37,  # Y
    (3, 7): 38,  # H
    (4, 7): 39,  # N
    (0, 8): 40,  # F6
    (1, 8): 41,  # 8

    # COLONNA 8-9: U, J, M, (gap), F7, 9
    (2, 8): 42,  # U
    (3, 8): 43,  # J
    (4, 8): 44,  # M
    (0, 9): 45,  # F7
    (1, 9): 46,  # 9

    # COLONNA 9-10: I, K, comma, (gap), F8, 0
    (2, 9): 47,  # I
    (3, 9): 48,  # K
    (4, 9): 49,  # ,
    (0, 10): 50, # F8
    (1, 10): 51, # 0

    # COLONNA 10-11: O, L, period, RAlt, F9, -
    (2, 10): 52, # O
    (3, 10): 53, # L
    (4, 10): 54, # .
    (5, 10): 55, # Right Alt
    (0, 11): 56, # F9
    (1, 11): 57, # -

    # COLONNA 11-12: P, semicolon, slash, RFn, F10, =
    (2, 11): 58, # P
    (3, 11): 59, # ;
    (4, 11): 60, # /
    (5, 11): 61, # Right Fn
    (0, 12): 62, # F10
    (1, 12): 63, # =

    # COLONNA 12-13: [, apostrophe, Menu, F11, Backspace
    (2, 12): 64, # [
    (3, 12): 65, # '
    (5, 12): 66, # Menu
    (0, 13): 67, # F11
    (1, 13): 68, # Backspace

    # COLONNA 13-14: ], #ISO, RShift, F12, Enter ISO, RCtrl
    (2, 13): 69, # ]
    (3, 13): 70, # # (ISO)
    (4, 13): 71, # Right Shift
    (0, 14): 72, # F12
    (2, 14): 73, # Enter (ISO) - multirow
    (5, 13): 74, # Right Control

    # === ZONA NAVIGATION ===
    # COLONNA 15: PrtSc, Ins, Del, Left, ScrLk, Home
    (0, 15): 75, # Print Screen
    (1, 15): 76, # Insert
    (2, 15): 77, # Delete
    (5, 15): 78, # Left Arrow
    (0, 16): 79, # Scroll Lock
    (1, 16): 80, # Home

    # COLONNA 16-17: End, Up, Pause, PgUp, PgDn
    (2, 16): 81, # End
    (4, 16): 82, # Up Arrow
    (5, 16): 83, # Down Arrow
    (0, 17): 84, # Pause/Break
    (1, 17): 85, # Page Up
    (2, 17): 86, # Page Down
    (5, 17): 87, # Right Arrow

    # === TASTIERINO NUMERICO ===
    # COLONNA 19: NumLock, Num7, Num4, Num1, Num0
    (1, 19): 88, # Num Lock
    (2, 19): 89, # Numpad 7
    (3, 19): 90, # Numpad 4
    (4, 19): 91, # Numpad 1
    (5, 19): 92, # Numpad 0 (wide key)

    # COLONNA 20: Num/, Num8, Num5, Num2, (Num0 continua)
    (1, 20): 93, # Numpad /
    (2, 20): 94, # Numpad 8
    (3, 20): 95, # Numpad 5
    (4, 20): 96, # Numpad 2

    # COLONNA 21: Num*, Num9, Num6, Num3, NumDot
    (1, 21): 97, # Numpad *
    (2, 21): 98, # Numpad 9
    (3, 21): 99, # Numpad 6
    (4, 21): 100, # Numpad 3
    (5, 21): 101, # Numpad .

    # COLONNA 22: Num-, Num+, (gap), NumEnter
    (1, 22): 102, # Numpad -
    (2, 22): 103, # Numpad + (tall key)
    (4, 22): 104, # Numpad Enter (tall key)
}

# Dimensioni della matrice
MATRIX_HEIGHT = 6
MATRIX_WIDTH = 23

def get_matrix():
    """Restituisce la matrice 6x23 con gli indici LED (None per celle vuote)."""
    matrix = [[None for _ in range(MATRIX_WIDTH)] for _ in range(MATRIX_HEIGHT)]

    for (row, col), led_idx in K7_MATRIX_MAP.items():
        matrix[row][col] = led_idx

    return matrix


def visualize_matrix():
    """Visualizza la matrice in formato ASCII."""
    matrix = get_matrix()

    print("ASUS TUF Gaming K7 - LED Matrix Map")
    print("=" * 120)
    print(f"Dimensioni: {MATRIX_HEIGHT} righe x {MATRIX_WIDTH} colonne = {len(K7_MATRIX_MAP)} LED")
    print()

    # Header con numeri colonna
    print("       ", end="")
    for col in range(MATRIX_WIDTH):
        print(f"{col:4d}", end=" ")
    print()
    print("     " + "-" * (MATRIX_WIDTH * 5))

    for row_idx, row in enumerate(matrix):
        print(f"R{row_idx} | ", end="")
        for led_idx in row:
            if led_idx is None:
                print("  --", end=" ")
            else:
                print(f"{led_idx:4d}", end=" ")
        print()

    print()
    print(f"Totale LED mappati: {len(K7_MATRIX_MAP)}")


if __name__ == "__main__":
    visualize_matrix()
