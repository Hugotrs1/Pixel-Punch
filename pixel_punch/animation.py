"""
Animation par images clés.

Une Pose décrit la position du squelette d'un boxeur (angles des bras, inclinaison
du buste...). Une Animation enchaîne des poses en interpolant en douceur entre elles.

Convention des angles des bras : 0° = vers l'adversaire, 90° = vers le haut,
-90° = vers le bas. Le coude ajoute son angle à celui de l'épaule.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, fields, replace

from .modele import ESQUIVE_DUREE, Coup


def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x: float) -> float:
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


@dataclass(frozen=True)
class Pose:
    dx: float = 0.0         # élan vers l'adversaire (pixels)
    dy: float = 0.0         # déplacement vertical (négatif = vers le haut)
    buste: float = 6.0      # inclinaison du buste (positif = vers l'avant)
    tete: float = 0.0       # inclinaison de la tête par rapport au buste
    av_epaule: float = -40.0
    av_coude: float = 120.0
    ar_epaule: float = -60.0
    ar_coude: float = 135.0
    ecart: float = 7.0      # écart des pieds
    genou: float = 2.0      # flexion des genoux
    chute: float = 0.0      # 0 = debout, 1 = allongé sur le dos
    yeux: float = 1.0       # 1 = ouverts, 0 = fermés

    def vers(self, autre: Pose, t: float) -> Pose:
        """Pose intermédiaire entre self (t=0) et autre (t=1)."""
        return Pose(**{f.name: getattr(self, f.name) + (getattr(autre, f.name) - getattr(self, f.name)) * t
                       for f in fields(Pose)})


GARDE = Pose()
GARDE_HAUTE = Pose(buste=2, genou=4, av_epaule=25, av_coude=105, ar_epaule=5, ar_coude=120)   # on se protège
JAB_ARMER = Pose(dx=4, buste=10, av_epaule=-55, av_coude=135)
JAB = Pose(dx=14, buste=16, av_epaule=4, av_coude=0, ecart=11, genou=3)
CROCHET_ARMER = Pose(dx=4, buste=-6, av_epaule=-150, av_coude=40, genou=4)
CROCHET = Pose(dx=12, buste=22, av_epaule=8, av_coude=35, ecart=10)
UPPER_ARMER = Pose(dx=5, dy=2, buste=16, genou=8, av_epaule=-100, av_coude=55)
UPPER = Pose(dx=10, dy=-4, buste=-8, genou=0, av_epaule=45, av_coude=55, ecart=6)
TOUCHE = Pose(buste=-16, tete=-22, av_epaule=-70, av_coude=100, ar_epaule=-80, ar_coude=110)
TOUCHE_FORT = Pose(dy=-2, buste=-26, tete=-38, av_epaule=-20, av_coude=40, ar_epaule=-30, ar_coude=60, yeux=0)
BLOQUE = replace(GARDE_HAUTE, buste=-6, dx=-2)
ESQUIVE_BAS = Pose(dx=-3, buste=30, genou=10, tete=10)
KO = Pose(buste=0, chute=1, tete=-15, av_epaule=100, av_coude=-15, ar_epaule=75, ar_coude=20, ecart=9,
          genou=3, yeux=0)
VICTOIRE = Pose(buste=0, av_epaule=55, av_coude=25, ar_epaule=125, ar_coude=-25)
VICTOIRE_SAUT = replace(VICTOIRE, dy=-5, genou=0, av_epaule=65, ar_epaule=115)
DEFAITE = Pose(buste=24, tete=20, av_epaule=-90, av_coude=10, ar_epaule=-95, ar_coude=5, genou=4)

_POSES_COUPS = {"jab": (JAB_ARMER, JAB), "hook": (CROCHET_ARMER, CROCHET), "up": (UPPER_ARMER, UPPER)}


class Animation:
    """Suite d'étapes (durée, pose cible), à partir d'une pose de départ."""

    def __init__(self, depart: Pose, etapes: list[tuple[float, Pose]], boucle: bool = False):
        self.depart = depart
        self.etapes = etapes
        self.boucle = boucle
        self.duree = sum(d for d, _ in etapes)
        self.t = 0.0

    @property
    def finie(self) -> bool:
        return not self.boucle and self.t >= self.duree

    def avancer(self, dt: float) -> Pose:
        self.t += dt
        t = self.t % self.duree if self.boucle else min(self.t, self.duree)
        precedente = self.depart
        for duree, cible in self.etapes:
            if t <= duree:
                return precedente.vers(cible, ease_in_out(t / duree) if duree else 1)
            t -= duree
            precedente = cible
        return precedente


# -- séquences : leurs durées suivent exactement le timing du modèle -----------
def attaque(coup: Coup) -> list[tuple[float, Pose]]:
    armer, frapper = _POSES_COUPS[coup.cle]
    d = coup.demarrage
    reste = coup.duree - d
    return [(d * 0.6, armer), (d * 0.4, frapper), (reste * 0.35, frapper), (reste * 0.65, GARDE)]


def encaisse(coup: Coup) -> list[tuple[float, Pose]]:
    p = TOUCHE_FORT if coup.cle == "up" else TOUCHE
    return [(0.05, p), (coup.sonne * 0.45, p), (coup.sonne * 0.5, GARDE)]


def bloque() -> list[tuple[float, Pose]]:
    return [(0.04, BLOQUE), (0.12, GARDE_HAUTE)]


def esquive() -> list[tuple[float, Pose]]:
    return [(0.07, ESQUIVE_BAS), (ESQUIVE_DUREE - 0.2, ESQUIVE_BAS), (0.13, GARDE)]


def chute_ko() -> list[tuple[float, Pose]]:
    rebond = replace(KO, chute=0.9, dy=-4)
    return [(0.06, TOUCHE_FORT), (0.5, KO), (0.14, rebond), (0.16, KO)]


def victoire() -> list[tuple[float, Pose]]:
    return [(0.22, VICTOIRE_SAUT), (0.22, VICTOIRE)]


def respiration(pose: Pose, t: float, marche: int = 0) -> Pose:
    """Sautillement de boxeur ajouté par-dessus la pose de repos ; jeu de jambes en marchant."""
    s = math.sin(t * (11 if marche else 7))
    p = replace(pose, dy=pose.dy - abs(s) * (1.6 if marche else 1.2), av_epaule=pose.av_epaule + s * 4,
                ar_epaule=pose.ar_epaule - s * 3, genou=pose.genou + abs(s) * 0.8)
    if marche:
        p = replace(p, ecart=pose.ecart + s * 3, buste=pose.buste + 3 * marche)
    return p
