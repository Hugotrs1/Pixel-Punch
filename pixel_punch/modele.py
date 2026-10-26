"""
Le MODÈLE : les règles du combat en temps réel, en POO pure (aucun import de pygame).

Chaque image, l'interface envoie une Commande par combattant (touches enfoncées), puis
appelle Combat.maj(dt) qui fait avancer la simulation et renvoie la liste des
événements (coup qui touche, esquive, K.O...) que l'interface transforme en effets.

Règles :
  * un coup se déroule en deux temps : la préparation (on peut être interrompu), puis
    l'impact ; s'il touche, l'adversaire est sonné un court instant et recule
  * reculer met en garde : elle bloque tous les coups mais laisse passer un quart des dégâts
  * l'esquive (on se baisse) évite le jab et le crochet... mais pas l'uppercut !
  * toucher un adversaire pendant la préparation de son coup = CONTRE (dégâts x1,5)
  * chaque action coûte de l'endurance, qui remonte quand on souffle
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

VIE_DEPART = 200
DUREE_ROUND = 99.0
ENDURANCE_MAX = 100.0
VITESSE = 55.0              # pixels du ring par seconde
DISTANCE_MIN = 28.0         # les boxeurs ne peuvent pas se traverser


@dataclass(frozen=True)
class Coup:
    nom: str
    cle: str                # "jab", "hook", "up"
    degats: int
    demarrage: float        # secondes avant l'impact
    duree: float            # durée totale du mouvement
    portee: float           # distance maximale entre les deux boxeurs pour toucher
    endurance: float        # coût
    sonne: float            # temps pendant lequel l'adversaire est sonné
    recul: float            # distance de recul de l'adversaire
    son: str

    @property
    def le(self) -> str:
        nom = self.nom.lower()
        return f"l'{nom}" if nom[0] in "aeiouy" else f"le {nom}"


# Mêmes dégâts que la version de 2024 : le jab est rapide, l'uppercut lent mais terrible
JAB = Coup("Jab", "jab", 10, 0.13, 0.36, 58, 9, 0.28, 5, "Jab_sound.mp3")
CROCHET = Coup("Crochet", "hook", 15, 0.21, 0.52, 54, 16, 0.38, 9, "hook_sound.mp3")
UPPERCUT = Coup("Uppercut", "up", 30, 0.32, 0.74, 50, 28, 0.65, 16, "final_punch.mp3")
COUPS = (JAB, CROCHET, UPPERCUT)

ESQUIVE_DUREE, ESQUIVE_INVINCIBLE, ESQUIVE_RECHARGE, ESQUIVE_COUT = 0.45, (0.03, 0.36), 0.7, 14


@dataclass
class Commande:
    """Ce que le joueur (ou l'IA) demande pendant cette image."""
    gauche: bool = False
    droite: bool = False
    garde: bool = False
    esquive: bool = False           # vrai seulement à l'image où la touche est pressée
    coup: Coup | None = None        # idem


@dataclass
class Evenement:
    type: str                       # attaque, touche, bloque, esquive, rate, ko, fin
    num: int = 0                    # combattant qui fait l'action
    coup: Coup | None = None
    degats: int = 0
    contre: bool = False


@dataclass
class Stats:
    envoyes: int = 0
    touches: int = 0
    bloques: int = 0                # coups adverses bloqués
    esquives: int = 0               # coups adverses esquivés
    degats: int = 0
    combo_max: int = 0

    @property
    def precision(self) -> float:
        return self.touches / self.envoyes if self.envoyes else 0.0


class Combattant:
    def __init__(self, nom: str, x: float, humain: bool = True):
        self.nom = nom
        self.humain = humain
        self.vie_max = VIE_DEPART
        self.vie = VIE_DEPART
        self.endurance = ENDURANCE_MAX
        self.x = x
        self.sens = 1
        self.etat = "libre"         # libre, garde, attaque, esquive, sonne, ko
        self.t = 0.0                # temps passé dans l'état actuel
        self.coup: Coup | None = None
        self.coup_recu: Coup | None = None
        self.impact_fait = False
        self.nb_attaques = 0
        self.recharge_esquive = 0.0
        self.marche = 0             # -1, 0, +1 : sens du déplacement (pour l'animation)
        self.combo = 0
        self.t_combo = 0.0
        self.stats = Stats()

    @property
    def ko(self) -> bool:
        return self.vie <= 0

    @property
    def peut_agir(self) -> bool:
        return self.etat in ("libre", "garde")

    @property
    def invincible(self) -> bool:
        a, b = ESQUIVE_INVINCIBLE
        return self.etat == "esquive" and a <= self.t <= b

    def changer(self, etat: str):
        self.etat, self.t = etat, 0.0


class Combat:
    def __init__(self, p1: Combattant, p2: Combattant, largeur_ring: float):
        self.joueurs = (p1, p2)
        self.gauche, self.droite = 34.0, largeur_ring - 34.0
        self.temps_restant = DUREE_ROUND
        self.fini = False
        self.raison = ""            # "ko" ou "temps"

    def joueur(self, num: int) -> Combattant:
        return self.joueurs[num - 1]

    @property
    def distance(self) -> float:
        return abs(self.joueurs[1].x - self.joueurs[0].x)

    @property
    def gagnant(self) -> int | None:
        p1, p2 = self.joueurs
        if p1.vie == p2.vie:
            return None
        return 1 if p1.vie > p2.vie else 2

    # -- une image de simulation ---------------------------------------------
    def maj(self, dt: float, commandes: tuple[Commande, Commande]) -> list[Evenement]:
        ev: list[Evenement] = []
        if self.fini:
            for c in self.joueurs:
                c.t += dt
            return ev
        self.temps_restant = max(0.0, self.temps_restant - dt)
        p1, p2 = self.joueurs
        p1.sens, p2.sens = (1, -1) if p1.x <= p2.x else (-1, 1)

        for num, (c, cmd) in enumerate(zip(self.joueurs, commandes), start=1):
            self._agir(num, c, cmd, dt, ev)
        for num, c in enumerate(self.joueurs, start=1):
            self._avancer(num, c, dt, ev)
        self._separer()

        if any(c.ko for c in self.joueurs):
            self.fini, self.raison = True, "ko"
            perdant = 1 if p1.ko else 2
            self.joueur(perdant).changer("ko")
            ev.append(Evenement("ko", 3 - perdant))
        elif self.temps_restant <= 0:
            self.fini, self.raison = True, "temps"
            ev.append(Evenement("fin", self.gagnant or 0))
        return ev

    def _agir(self, num, c: Combattant, cmd: Commande, dt, ev):
        c.recharge_esquive = max(0.0, c.recharge_esquive - dt)
        c.marche = 0
        if not c.peut_agir:
            return
        if cmd.coup and c.endurance >= cmd.coup.endurance:
            c.changer("attaque")
            c.coup, c.impact_fait = cmd.coup, False
            c.nb_attaques += 1
            c.endurance -= cmd.coup.endurance
            c.stats.envoyes += 1
            ev.append(Evenement("attaque", num, cmd.coup))
            return
        if cmd.esquive and c.recharge_esquive <= 0 and c.endurance >= ESQUIVE_COUT:
            c.changer("esquive")
            c.endurance -= ESQUIVE_COUT
            c.recharge_esquive = ESQUIVE_RECHARGE
            ev.append(Evenement("esquive_debut", num))
            return
        direction = (1 if cmd.droite else 0) - (1 if cmd.gauche else 0)
        garde = cmd.garde or (direction != 0 and direction == -c.sens)    # reculer = se protéger
        if garde != (c.etat == "garde"):
            c.changer("garde" if garde else "libre")
        if direction:
            vitesse = VITESSE * (0.55 if c.etat == "garde" else 1.0)
            c.x = min(self.droite, max(self.gauche, c.x + direction * vitesse * dt))
            c.marche = direction

    def _avancer(self, num, c: Combattant, dt, ev):
        c.t += dt
        c.t_combo += dt
        if c.t_combo > 1.2:
            c.combo = 0
        regen = {"libre": 24, "garde": 10}.get(c.etat, 0)
        c.endurance = min(ENDURANCE_MAX, c.endurance + regen * dt)
        if c.etat == "attaque":
            if not c.impact_fait and c.t >= c.coup.demarrage:
                c.impact_fait = True
                self._impact(num, c, ev)
            if c.t >= c.coup.duree:
                c.changer("libre")
        elif c.etat == "esquive" and c.t >= ESQUIVE_DUREE:
            c.changer("libre")
        elif c.etat == "sonne" and c.t >= c.coup_recu.sonne:
            c.changer("libre")

    def _impact(self, num, att: Combattant, ev):
        dfn = self.joueur(3 - num)
        coup = att.coup
        if self.distance > coup.portee or dfn.ko:
            ev.append(Evenement("rate", num, coup))
            return
        if dfn.invincible and coup.cle != "up":
            dfn.stats.esquives += 1
            ev.append(Evenement("esquive", 3 - num, coup))
            return
        if dfn.etat == "garde":
            degats = math.ceil(coup.degats / 4)
            dfn.endurance = max(0.0, dfn.endurance - coup.endurance * 0.6)
            self._pousser(dfn, att, coup.recul * 0.5)
            dfn.stats.bloques += 1
            self._blesser(dfn, degats)
            ev.append(Evenement("bloque", num, coup, degats))
            return
        contre = dfn.etat == "attaque" and not dfn.impact_fait
        degats = round(coup.degats * (1.5 if contre else 1))
        self._blesser(dfn, degats)
        att.stats.touches += 1
        att.stats.degats += degats
        att.combo += 1
        att.t_combo = 0.0
        att.stats.combo_max = max(att.stats.combo_max, att.combo)
        dfn.combo = 0
        dfn.coup_recu = coup
        dfn.changer("sonne")
        self._pousser(dfn, att, coup.recul)
        ev.append(Evenement("touche", num, coup, degats, contre))

    @staticmethod
    def _blesser(c: Combattant, degats: int):
        c.vie = max(0, c.vie - degats)

    def _pousser(self, dfn: Combattant, att: Combattant, d: float):
        cible = dfn.x + d * att.sens
        bornee = min(self.droite, max(self.gauche, cible))
        dfn.x = bornee
        att.x -= (cible - bornee) * 0.6               # dos aux cordes : c'est l'attaquant qui recule

    def _separer(self):
        p1, p2 = self.joueurs
        ecart = p2.x - p1.x
        if abs(ecart) < DISTANCE_MIN:
            manque = (DISTANCE_MIN - abs(ecart)) / 2
            s = 1 if ecart >= 0 else -1
            p1.x = min(self.droite, max(self.gauche, p1.x - manque * s))
            p2.x = min(self.droite, max(self.gauche, p2.x + manque * s))
