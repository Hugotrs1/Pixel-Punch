"""
Touches du clavier.

On utilise les « scancodes » (position physique de la touche) plutôt que la lettre :
ainsi les commandes tombent au même endroit sur un clavier AZERTY ou QWERTY.
Seules les étiquettes affichées changent selon la disposition détectée.

La garde n'a pas de touche : comme dans les jeux de combat classiques,
on se protège en reculant (en s'éloignant de l'adversaire).
"""
from __future__ import annotations

import sys

import pygame as pg

from .modele import COUPS, Commande


def clavier_azerty() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        langue = ctypes.windll.user32.GetKeyboardLayout(0) & 0xFFFF
        return langue & 0xFF == 0x0C        # français (France, Belgique, Suisse...)
    except (OSError, AttributeError):
        return False


AZERTY = clavier_azerty()

# action -> (scancodes, étiquette AZERTY, étiquette QWERTY)
# Solo : main gauche pour bouger, main droite posée sur J K L pour frapper.
SOLO = {
    "gauche": ((pg.KSCAN_A, pg.KSCAN_LEFT), "Q", "A"),
    "droite": ((pg.KSCAN_D, pg.KSCAN_RIGHT), "D", "D"),
    "esquive": ((pg.KSCAN_S, pg.KSCAN_DOWN, pg.KSCAN_SPACE), "S", "S"),
    "jab": ((pg.KSCAN_J,), "J", "J"),
    "hook": ((pg.KSCAN_K,), "K", "K"),
    "up": ((pg.KSCAN_L,), "L", "L"),
}
# 2 joueurs : chacun un bloc de 6 touches, chaque doigt a sa touche et celle juste au-dessus.
DUO_J1 = {
    "gauche": ((pg.KSCAN_A,), "Q", "A"),
    "droite": ((pg.KSCAN_D,), "D", "D"),
    "esquive": ((pg.KSCAN_S,), "S", "S"),
    "jab": ((pg.KSCAN_Q,), "A", "Q"),
    "hook": ((pg.KSCAN_W,), "Z", "W"),
    "up": ((pg.KSCAN_E,), "E", "E"),
}
DUO_J2 = {
    "gauche": ((pg.KSCAN_J, pg.KSCAN_LEFT), "J", "J"),
    "droite": ((pg.KSCAN_L, pg.KSCAN_RIGHT), "L", "L"),
    "esquive": ((pg.KSCAN_K, pg.KSCAN_DOWN), "K", "K"),
    "jab": ((pg.KSCAN_U, pg.KSCAN_KP_1), "U", "U"),
    "hook": ((pg.KSCAN_I, pg.KSCAN_KP_2), "I", "I"),
    "up": ((pg.KSCAN_O, pg.KSCAN_KP_3), "O", "O"),
}
NOMS_ACTIONS = {"gauche": "Se déplacer", "esquive": "Esquive", "jab": "Jab", "hook": "Crochet", "up": "Uppercut"}


def etiquette(schema: dict, action: str) -> str:
    _, az, qw = schema[action]
    return az if AZERTY else qw


class Clavier:
    """Mémorise les touches enfoncées et celles pressées pendant l'image en cours."""

    def __init__(self):
        self.enfoncees: set[int] = set()
        self.pressees: set[int] = set()

    def evenement(self, e: pg.event.Event):
        if e.type == pg.KEYDOWN:
            self.enfoncees.add(e.scancode)
            self.pressees.add(e.scancode)
        elif e.type == pg.KEYUP:
            self.enfoncees.discard(e.scancode)

    def nouvelle_image(self):
        self.pressees.clear()

    def commande(self, schema: dict) -> Commande:
        def tenu(action):
            return any(sc in self.enfoncees for sc in schema[action][0])

        def presse(action):
            return any(sc in self.pressees for sc in schema[action][0])

        coup = next((c for c in COUPS if presse(c.cle)), None)
        return Commande(gauche=tenu("gauche"), droite=tenu("droite"), esquive=presse("esquive"), coup=coup)
