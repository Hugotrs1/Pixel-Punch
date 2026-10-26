"""
L'ordinateur adversaire. Il « regarde » le combat comme un joueur, avec un temps de
réaction, et produit une Commande à chaque image — exactement comme le clavier.
"""
from __future__ import annotations

import random

from .modele import CROCHET, JAB, UPPERCUT, Combat, Commande

NIVEAUX = {
    #            réaction (s)   réflexes   agressivité
    "Facile":    (0.38,         0.15,      0.35),
    "Normal":    (0.24,         0.40,      0.55),
    "Difficile": (0.14,         0.70,      0.75),
}


class IA:
    def __init__(self, num: int, niveau: str = "Normal", rng: random.Random | None = None):
        self.num = num
        self.reaction, self.reflexes, self.agressivite = NIVEAUX[niveau]
        self.rng = rng or random.Random()
        self.attente = 0.5          # temps avant la prochaine décision
        self.plan = Commande()      # décision en cours (déplacement / garde)
        self.duree_plan = 0.0
        self.vu = None              # dernière attaque adverse déjà traitée

    def commande(self, combat: Combat, dt: float) -> Commande:
        moi, adv = combat.joueur(self.num), combat.joueur(3 - self.num)
        d = combat.distance
        vers_adv = adv.x > moi.x
        cmd = Commande(gauche=self.plan.gauche, droite=self.plan.droite, garde=self.plan.garde)
        self.duree_plan -= dt
        if self.duree_plan <= 0:
            self.plan = Commande()

        # Réflexes : réagir à un coup adverse qui se prépare
        if adv.etat == "attaque" and not adv.impact_fait and self.vu != adv.nb_attaques:
            if adv.t >= self.reaction * 0.5 and d <= adv.coup.portee + 6:
                self.vu = adv.nb_attaques
                if self.rng.random() < self.reflexes:
                    if adv.coup is UPPERCUT or moi.recharge_esquive > 0:
                        self._planifier(Commande(garde=True), 0.5)
                    else:
                        return Commande(esquive=True)
            return cmd

        self.attente -= dt
        if self.attente > 0:
            return cmd
        self.attente = self.reaction * self.rng.uniform(0.7, 1.4)

        if moi.endurance < 22:                                   # à bout de souffle : on recule en garde
            self._planifier(Commande(gauche=vers_adv, droite=not vers_adv, garde=self.rng.random() < 0.6), 0.6)
        elif d > 54:                                             # trop loin : on avance
            self._planifier(Commande(gauche=not vers_adv, droite=vers_adv), 0.25)
        elif d < 34 and self.rng.random() < 0.3:                 # trop près : petit pas en arrière
            self._planifier(Commande(gauche=vers_adv, droite=not vers_adv), 0.2)
        elif self.rng.random() < self.agressivite:
            return Commande(coup=self._choisir_coup(adv, d))
        elif self.rng.random() < 0.3:
            self._planifier(Commande(garde=True), 0.4)
        return Commande(gauche=self.plan.gauche, droite=self.plan.droite, garde=self.plan.garde)

    def _planifier(self, cmd: Commande, duree: float):
        self.plan, self.duree_plan = cmd, duree

    def _choisir_coup(self, adv, d):
        if adv.etat == "sonne":                                  # on enchaîne
            return self.rng.choice((JAB, CROCHET))
        if adv.etat == "esquive" or (adv.etat == "garde" and self.rng.random() < 0.3):
            return UPPERCUT if d <= UPPERCUT.portee else JAB
        possibles = [c for c in (JAB, CROCHET, UPPERCUT) if d <= c.portee] or [JAB]
        return self.rng.choices(possibles, weights=[6, 3, 1][:len(possibles)])[0]
