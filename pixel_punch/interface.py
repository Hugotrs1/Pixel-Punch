"""
L'INTERFACE : fenêtre, boucle de jeu, menus et effets.

Elle lit le clavier (ou l'IA), transmet les commandes au modèle, puis transforme les
événements du modèle en animations, sons et effets. Elle ne contient aucune règle.
"""
from __future__ import annotations

import asyncio
import math
import random
import sys

import pygame as pg

from . import animation as anim
from . import config as cfg
from .animation import clamp, ease_out_back
from .arene import Arene, Particules
from .boxeur import TENUE_P1, TENUE_P2, Boxeur
from .controles import DUO_J1, DUO_J2, NOMS_ACTIONS, SOLO, Clavier, etiquette
from .hud import Sons, melange, panneau, police, texte, touche, u, vignette
from .ia import IA, NIVEAUX
from .modele import COUPS, ENDURANCE_MAX, Combat, Combattant, Commande, Evenement

ANNONCES = {"jab": "JAB !", "hook": "CROCHET !", "up": "UPPERCUT !!"}
FORCE = {"jab": 0.5, "hook": 0.75, "up": 1.0}
NAV_HAUT = (pg.KSCAN_UP, pg.KSCAN_W)
NAV_BAS = (pg.KSCAN_DOWN, pg.KSCAN_S)
NAV_GAUCHE = (pg.KSCAN_LEFT, pg.KSCAN_A)
NAV_DROITE = (pg.KSCAN_RIGHT, pg.KSCAN_D)
VALIDER = (pg.KSCAN_RETURN, pg.KSCAN_KP_ENTER, pg.KSCAN_SPACE)


def rendre_net_sous_windows():
    """Sans ça, Windows agrandit la fenêtre en la floutant quand l'affichage est zoomé (125 %, 150 %...)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (OSError, AttributeError):
            pass


class Jeu:
    def __init__(self, plein_ecran: bool = True):
        rendre_net_sous_windows()
        pg.init()
        pg.display.set_caption(cfg.TITRE)
        self.horloge = pg.time.Clock()
        self.rng = random.Random()
        self.arene = Arene(self.rng)
        self.plein_ecran = plein_ecran
        self.ouvrir_fenetre()
        self.sons = Sons()
        self.clavier = Clavier()
        self.particules = Particules()
        self.noms = ["Rocky", "L'Ordi"]
        self.deux_joueurs = False
        self.niveaux = list(NIVEAUX)
        self.niveau = 1
        self.choix = 0                      # élément sélectionné dans le menu courant
        self.edition = None                 # numéro du nom en cours de modification
        self.zones: list[tuple[pg.Rect, int]] = []
        self.temps = 0.0
        self.boxeurs = (Boxeur(cfg.LW / 2 - 40, 1, TENUE_P1), Boxeur(cfg.LW / 2 + 40, -1, TENUE_P2))
        self.combat: Combat | None = None
        self.reinitialiser_effets()
        self.etat, self.t_etat = "menu", 0.0
        self.retour = "menu"                # écran où revenir après « Commandes »

    # -- fenêtre --------------------------------------------------------------
    def ouvrir_fenetre(self, taille=None):
        if self.plein_ecran:
            self.ecran = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        else:
            self.ecran = pg.display.set_mode(taille or (1280, 720), pg.RESIZABLE)
        cfg.configurer(*self.ecran.get_size())
        police.cache_clear()
        self.monde = pg.Surface((cfg.LW, cfg.LH))
        self.vignette = vignette()
        self.arene.construire()

    # -- déroulement ------------------------------------------------------------
    def reinitialiser_effets(self):
        self.programme: list[tuple[float, object]] = []
        self.t_monde = 0.0
        self.gel = 0.0
        self.ralenti, self.t_ralenti = 1.0, 0.0
        self.zoom, self.zoom_cible = 1.0, 1.0
        self.focus = (cfg.LW / 2, cfg.LH / 2)
        self.secousse = self.flash = 0.0
        self.annonce = None
        self.flottants: list[list] = []
        self.etoile = None
        self.cam = pg.Rect(0, 0, cfg.LW, cfg.LH)

    def changer(self, etat: str, choix: int = 0):
        self.etat, self.t_etat, self.choix = etat, 0.0, choix

    def plus_tard(self, delai: float, fonction):
        self.programme.append((self.t_monde + delai, fonction))

    def nouveau_combat(self):
        n1 = self.noms[0].strip() or "Joueur 1"
        n2 = self.noms[1].strip() or ("Joueur 2" if self.deux_joueurs else "L'Ordi")
        milieu = cfg.LW / 2
        p1, p2 = Combattant(n1, milieu - 45), Combattant(n2, milieu + 45, humain=self.deux_joueurs)
        self.combat = Combat(p1, p2, cfg.LW)
        self.ia = None if self.deux_joueurs else IA(2, self.niveaux[self.niveau], self.rng)
        self.vie_aff = [float(p1.vie_max)] * 2
        self.vie_fantome = [float(p1.vie_max)] * 2
        self.delai_fantome = [0.0, 0.0]
        self.reinitialiser_effets()
        self.particules.p.clear()
        self.boxeurs = (Boxeur(p1.x, 1, TENUE_P1), Boxeur(p2.x, -1, TENUE_P2))
        for b in self.boxeurs:
            b.jouer([(1.0, anim.GARDE)], anim.Pose(dx=-90))
        self.sons.jouer("Bell.mp3", 0.7)
        self.arene.acclamer(0.6, 6)
        self.changer("intro")

    # -- réactions aux événements du modèle ------------------------------------
    def reagir(self, e: Evenement):
        c = self.combat
        if e.type == "attaque":
            self.boxeurs[e.num - 1].attaquer(e.coup, c.distance)
        elif e.type == "esquive_debut":
            self.boxeurs[e.num - 1].jouer(anim.esquive())
        elif e.type == "touche":
            self.touche(e)
        elif e.type == "bloque":
            dfn = self.boxeurs[2 - e.num]
            dfn.jouer(anim.bloque())
            self.sons.jouer("Jab_sound.mp3", 0.35)
            x, y = dfn.point("av_poing")
            self.particules.jet(x, y, 8, [(220, 235, 255), (255, 255, 255)], vitesse=50, vie=0.3)
            self.flottant((x, y - 12), "BLOQUÉ", cfg.GRIS)
            self.gel, self.secousse = 0.03, 1.0
        elif e.type == "esquive":
            self.sons.jouer("esquive.mp3", 0.8)
            x, y = self.boxeurs[e.num - 1].point("tete")
            self.flottant((x, y - 14), "ESQUIVE", cfg.BLEU)
            self.arene.acclamer(0.15)
        elif e.type == "ko":
            self.ko(e.num)
        elif e.type == "fin":
            self.fin_au_temps(e.num)

    def touche(self, e: Evenement):
        coup, att, dfn = e.coup, self.combat.joueur(e.num), self.combat.joueur(3 - e.num)
        b = self.boxeurs[2 - e.num]
        f = FORCE[coup.cle] * (1.3 if e.contre else 1)
        self.delai_fantome[2 - e.num] = 0.45
        self.sons.jouer(coup.son)
        if not dfn.ko:
            b.jouer(anim.encaisse(coup))
        tx, ty = b.point("tete")
        self.particules.jet(tx, ty, int(12 + 18 * f), [(255, 255, 255), (255, 230, 120), cfg.OR], vitesse=60 + 60 * f)
        self.particules.jet(tx, ty, 5, [(170, 220, 255)], vitesse=40, vie=0.7)
        self.gel = 0.04 + 0.07 * f
        self.secousse, self.flash = 1.5 + 2.5 * f, 0.12 * f
        self.arene.acclamer(0.2 + 0.35 * f, int(3 * f))
        self.etoile = (tx, ty, 0.12)
        self.flottant((tx, ty - 10), f"-{e.degats}", cfg.ROUGE)
        if e.contre:
            self.annoncer("CONTRE !", f"{att.nom} punit {dfn.nom}", cfg.OR)
        elif att.combo >= 3:
            self.annoncer(f"COMBO x{att.combo}", att.nom, cfg.OR)
        elif coup.cle == "up":
            self.annoncer(ANNONCES["up"], f"{att.nom} décroche un uppercut", cfg.OR)

    def ko(self, gagnant: int):
        perdant = self.boxeurs[2 - gagnant]
        perdant.jouer(anim.chute_ko())
        perdant.fige = True
        self.sons.jouer("final_punch.mp3")
        self.ralenti, self.t_ralenti = 0.3, 1.1
        self.zoom_cible, self.focus = 1.6, perdant.point("hanche")
        self.flash = 0.45
        self.annonce = None
        self.arene.acclamer(1.0, 14)
        self.plus_tard(0.62, lambda: self.particules.jet(perdant.point("hanche")[0], cfg.SOL, 26,
                                                         [(200, 230, 245), (150, 200, 230)], vitesse=45, gravite=120,
                                                         vie=0.6))
        self.plus_tard(0.62, lambda: setattr(self, "secousse", 4))
        self.changer("ko")

    def fin_au_temps(self, gagnant: int):
        self.sons.jouer("Bell.mp3")
        if gagnant:
            self.boxeurs[2 - gagnant].jouer([(0.4, anim.DEFAITE)])
            self.boxeurs[2 - gagnant].fige = True
        self.changer("ko")

    def victoire(self):
        g = self.combat.gagnant
        if g:
            self.boxeurs[g - 1].jouer(anim.victoire(), anim.VICTOIRE, boucle=True)
            self.particules.confettis(160, self.rng)
            self.arene.acclamer(1.0, 10)
        self.zoom_cible = 1.0
        if self.combat.raison == "ko":
            self.sons.jouer("Bell.mp3")
        self.changer("fin")

    def flottant(self, pos_monde, msg, couleur):
        recents = sum(1 for f in self.flottants if f[4] < 0.4)          # on empile au lieu de superposer
        self.flottants.append([pos_monde[0], pos_monde[1] - 9 * recents, msg, couleur, 0.0])

    def annoncer(self, titre, sous, couleur):
        self.annonce = [titre, sous, couleur, 0.0]

    # -- menus ----------------------------------------------------------------------
    def elements_menu(self):
        if self.etat == "pause":
            return ["Reprendre", "Recommencer", "Commandes", "Menu principal", "Quitter"]
        n2 = "Joueur 2" if self.deux_joueurs else "Adversaire"
        return ["Combat contre l'ordi", "Combat à 2 joueurs", f"Difficulté   ‹  {self.niveaux[self.niveau]}  ›",
                f"Joueur 1   :   {self.noms[0]}", f"{n2}   :   {self.noms[1]}", "Commandes", "Quitter"]

    def activer(self, i: int) -> bool:
        if self.etat == "pause":
            action = ("reprendre", "recommencer", "commandes", "menu", "quitter")[i]
        else:
            action = ("solo", "duo", "niveau", "nom0", "nom1", "commandes", "quitter")[i]
        if action == "quitter":
            return False
        if action in ("solo", "duo"):
            self.deux_joueurs = action == "duo"
            if self.deux_joueurs and self.noms[1] == "L'Ordi":
                self.noms[1] = "Apollo"
            self.nouveau_combat()
        elif action == "niveau":
            self.niveau = (self.niveau + 1) % len(self.niveaux)
        elif action.startswith("nom"):
            self.edition = int(action[-1])
            self.noms[self.edition] = ""
        elif action == "commandes":
            self.retour = self.etat
            self.changer("commandes")
        elif action == "reprendre":
            self.changer("combat")
        elif action == "recommencer":
            self.nouveau_combat()
        elif action == "menu":
            self.retour_menu()
        return True

    def retour_menu(self):
        self.combat = None
        self.reinitialiser_effets()
        self.particules.p.clear()
        self.boxeurs = (Boxeur(cfg.LW / 2 - 40, 1, TENUE_P1), Boxeur(cfg.LW / 2 + 40, -1, TENUE_P2))
        self.changer("menu")

    # -- événements ---------------------------------------------------------------
    def evenement(self, e: pg.event.Event) -> bool:
        if e.type == pg.QUIT:
            return False
        self.clavier.evenement(e)
        if e.type == pg.VIDEORESIZE and not self.plein_ecran:
            self.ouvrir_fenetre((max(640, e.w), max(360, e.h)))
            return True
        if e.type == pg.KEYDOWN and e.key == pg.K_F11:
            self.plein_ecran = not self.plein_ecran
            self.ouvrir_fenetre()
            return True

        if self.edition is not None:                       # saisie d'un nom
            if e.type == pg.TEXTINPUT and len(self.noms[self.edition]) < 12:
                self.noms[self.edition] += e.text
            elif e.type == pg.KEYDOWN:
                if e.key == pg.K_BACKSPACE:
                    self.noms[self.edition] = self.noms[self.edition][:-1]
                elif e.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_ESCAPE, pg.K_TAB):
                    if not self.noms[self.edition].strip():
                        self.noms[self.edition] = "Rocky" if self.edition == 0 else "L'Ordi"
                    self.edition = None
            return True

        sc = e.scancode if e.type == pg.KEYDOWN else None
        if self.etat in ("menu", "pause"):
            n = len(self.elements_menu())
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_ESCAPE:
                    if self.etat == "pause":
                        self.changer("combat")
                        return True
                    return False
                if sc in NAV_HAUT:
                    self.choix = (self.choix - 1) % n
                elif sc in NAV_BAS:
                    self.choix = (self.choix + 1) % n
                elif sc in NAV_GAUCHE + NAV_DROITE and self.etat == "menu" and self.choix == 2:
                    self.niveau = (self.niveau + (1 if sc in NAV_DROITE else -1)) % len(self.niveaux)
                elif sc in VALIDER:
                    return self.activer(self.choix)
            elif e.type == pg.MOUSEMOTION:
                for r, i in self.zones:
                    if r.collidepoint(e.pos):
                        self.choix = i
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                for r, i in self.zones:
                    if r.collidepoint(e.pos):
                        return self.activer(i)
        elif self.etat == "commandes":
            if e.type == pg.KEYDOWN and (e.key == pg.K_ESCAPE or sc in VALIDER) or \
                    e.type == pg.MOUSEBUTTONDOWN:
                self.changer(self.retour, 2 if self.retour == "pause" else 5)
        elif self.etat in ("combat", "intro"):
            if e.type == pg.KEYDOWN and e.key in (pg.K_ESCAPE, pg.K_p):
                self.changer("pause")
        elif self.etat == "fin" and self.t_etat > 1.0 and e.type == pg.KEYDOWN:
            if sc in VALIDER or e.key == pg.K_r:
                self.nouveau_combat()
            elif e.key == pg.K_ESCAPE:
                self.retour_menu()
        return True

    # -- mise à jour ------------------------------------------------------------------
    def maj(self, dt: float):
        self.temps += dt
        self.t_etat += dt
        if self.etat in ("menu", "commandes"):
            for b in self.boxeurs:
                b.maj(dt)
            self.arene.maj(dt)
            return
        if self.etat == "pause":
            return

        if self.t_ralenti > 0:
            self.t_ralenti -= dt
            if self.t_ralenti <= 0:
                self.ralenti = 1.0
        if self.gel > 0:
            self.gel -= dt
            dt_monde = 0.0
        else:
            dt_monde = dt * self.ralenti
        self.t_monde += dt_monde
        for quand, fonction in [x for x in self.programme if x[0] <= self.t_monde]:
            self.programme.remove((quand, fonction))
            fonction()

        c = self.combat
        if self.etat == "combat":
            if self.deux_joueurs:
                cmds = (self.clavier.commande(DUO_J1), self.clavier.commande(DUO_J2))
            else:
                cmds = (self.clavier.commande(SOLO), self.ia.commande(c, dt_monde))
        else:
            cmds = (Commande(), Commande())
        if self.etat != "intro":
            for ev in c.maj(dt_monde, cmds):
                self.reagir(ev)
        for b, comb in zip(self.boxeurs, c.joueurs):
            if self.etat != "intro":
                b.suivre(comb)
            b.maj(dt_monde)
        self.arene.maj(dt)
        self.particules.maj(dt_monde)
        self.secousse = max(0.0, self.secousse - dt * 14)
        self.flash *= 0.85
        self.zoom += (self.zoom_cible - self.zoom) * min(1, dt * 5)
        if self.etoile:
            x, y, v = self.etoile
            self.etoile = (x, y, v - dt) if v > 0 else None
        for i, p in enumerate(c.joueurs):
            self.vie_aff[i] += (p.vie - self.vie_aff[i]) * min(1, dt * 12)
            self.delai_fantome[i] -= dt
            if self.delai_fantome[i] <= 0:
                self.vie_fantome[i] += (self.vie_aff[i] - self.vie_fantome[i]) * min(1, dt * 4)
        for f in self.flottants:
            f[1] -= 10 * dt
            f[4] += dt
        self.flottants = [f for f in self.flottants if f[4] < 1.0]
        if self.annonce:
            self.annonce[3] += dt
            if self.annonce[3] > 1.6:
                self.annonce = None

        if self.etat == "intro" and self.t_etat > 2.4:
            self.changer("combat")
        elif self.etat == "ko" and self.t_etat > 3.0:
            self.victoire()

    # -- dessin du monde -------------------------------------------------------------
    def dessiner(self):
        m = self.monde
        self.arene.dessiner(m, self.temps)
        ordre = sorted(self.boxeurs, key=lambda b: (not b.fige, b.anim is not None))
        for b in ordre:
            b.dessiner(m)
        if self.etoile:
            self.dessiner_etoile(m, *self.etoile)
        self.particules.dessiner(m)
        self.arene.lumieres(m)

        z = self.zoom
        cw, ch = cfg.LW / z, cfg.LH / z
        cx = clamp(cfg.LW / 2 + (self.focus[0] - cfg.LW / 2) * (1 - 1 / z) - cw / 2, 0, cfg.LW - cw)
        cy = clamp(cfg.LH / 2 + (self.focus[1] - cfg.LH / 2) * (1 - 1 / z) - ch / 2, 0, cfg.LH - ch)
        self.cam = pg.Rect(round(cx), round(cy), max(1, round(cw)), max(1, round(ch)))
        vue = pg.transform.scale(m.subsurface(self.cam), (cfg.LW * cfg.ECHELLE, cfg.LH * cfg.ECHELLE))
        sx = round(self.rng.uniform(-1, 1) * self.secousse) * cfg.ECHELLE
        sy = round(self.rng.uniform(-1, 1) * self.secousse) * cfg.ECHELLE
        self.ecran.fill((0, 0, 0))
        self.ecran.blit(vue, (sx, sy))
        self.ecran.blit(self.vignette, (0, 0), special_flags=pg.BLEND_RGB_MULT)

        if self.etat in ("menu", "commandes") or (self.etat == "pause" and self.combat is None):
            self.voile(150)
        if self.combat and self.etat in ("intro", "combat", "pause", "ko"):
            self.dessiner_hud()
        for x, y, msg, coul, age in self.flottants:
            texte(self.ecran, msg, 30, coul, self.vers_ecran(x, y), style="titre", alpha=int(255 * clamp((1 - age) * 3)),
                  echelle=0.6 + 0.4 * ease_out_back(age * 4), contour=2)
        if self.annonce and self.etat == "combat":
            self.dessiner_annonce()
        getattr(self, f"dessiner_{self.etat}", lambda: None)()
        if self.flash > 0.01:
            v = int(255 * self.flash)
            self.ecran.fill((v, v, v), special_flags=pg.BLEND_RGB_ADD)

    def vers_ecran(self, x, y):
        k = cfg.ECHELLE * cfg.LW / self.cam.w
        return (x - self.cam.x) * k, (y - self.cam.y) * k

    def voile(self, alpha):
        s = pg.Surface((cfg.W, cfg.H), pg.SRCALPHA)
        s.fill((8, 6, 14, alpha))
        self.ecran.blit(s, (0, 0))

    @staticmethod
    def dessiner_etoile(m, x, y, vie):
        r = 4 + (0.12 - vie) * 60
        pts = [(x + math.cos(k * math.tau / 16) * (r if k % 2 == 0 else r * 0.4),
                y + math.sin(k * math.tau / 16) * (r if k % 2 == 0 else r * 0.4)) for k in range(16)]
        pg.draw.polygon(m, (255, 240, 150), pts)
        pg.draw.circle(m, (255, 255, 255), (x, y), r * 0.35)

    # -- interface de combat -------------------------------------------------------------
    def dessiner_hud(self):
        W = cfg.W
        bw, bh, y = u(440), u(26), u(54)
        marge = u(28)
        reste = self.combat.temps_restant
        coul = cfg.ROUGE if reste < 10 else cfg.BLANC
        self.ecran.blit(panneau(u(96), u(80), 200, 18), (W / 2 - u(48), u(10)))
        texte(self.ecran, str(math.ceil(reste)), 46, coul, (W / 2, u(50)), style="titre",
              echelle=1 + (0.12 * (1 - (reste % 1)) if reste < 10 else 0))
        for i, p in enumerate(self.combat.joueurs):
            x = marge if i == 0 else W - marge - bw
            self.ecran.blit(panneau(bw + u(24), u(98), 175, 16), (x - u(12), u(10)))
            nom_pos = (x, u(20)) if i == 0 else (x + bw, u(20))
            texte(self.ecran, p.nom.upper(), 24, cfg.BLANC, nom_pos, "topleft" if i == 0 else "topright")
            texte(self.ecran, f"{p.vie}", 20, cfg.BLANC, (x + bw, u(23)) if i == 0 else (x, u(23)),
                  "topright" if i == 0 else "topleft", style="titre", ombre=False)
            self.barre(x, y, bw, bh, i, p)
            ew = bw * 0.62
            ex = x if i == 0 else x + bw - ew
            pg.draw.rect(self.ecran, (25, 28, 40), (ex, y + bh + u(9), ew, u(8)), border_radius=u(4))
            r = p.endurance / ENDURANCE_MAX
            couleur = cfg.BLEU if r > 0.25 else melange(cfg.ROUGE, cfg.BLEU, r * 4)
            lw = ew * r
            pg.draw.rect(self.ecran, couleur, (ex if i == 0 else ex + ew - lw, y + bh + u(9), lw, u(8)),
                         border_radius=u(4))
            if p.combo >= 2:
                texte(self.ecran, f"{p.combo} coups", 18, cfg.OR, (x + bw, y + bh + u(14)) if i == 0 else
                      (x, y + bh + u(14)), "midright" if i == 0 else "midleft", ombre=False)
        if self.etat in ("intro", "combat") and self.t_etat < 7 and self.etat != "pause":
            a = int(255 * clamp(7 - self.t_etat) if self.etat == "combat" else 255)
            self.aide_touches(DUO_J1 if self.deux_joueurs else SOLO, u(28), cfg.H - u(30), "bottomleft", a)
            if self.deux_joueurs:
                self.aide_touches(DUO_J2, cfg.W - u(28), cfg.H - u(30), "bottomright", a)

    def barre(self, x, y, bw, bh, i, p):
        pg.draw.rect(self.ecran, (25, 25, 32), (x, y, bw, bh), border_radius=u(7))
        for val, coul in ((self.vie_fantome[i], (255, 240, 200)), (self.vie_aff[i], None)):
            r = clamp(val / p.vie_max)
            if coul is None:
                coul = melange((240, 60, 50), (255, 205, 60), r * 2) if r < 0.5 else \
                    melange((255, 205, 60), (90, 220, 110), (r - 0.5) * 2)
            w = int(bw * r)
            if w > 0:
                rect = pg.Rect(x if i == 0 else x + bw - w, y, w, bh)
                pg.draw.rect(self.ecran, coul, rect, border_radius=u(7))
                pg.draw.rect(self.ecran, melange(coul, cfg.BLANC, 0.35), (rect.x + u(4), rect.y + u(3),
                                                                           max(0, rect.w - u(8)), u(5)),
                             border_radius=u(3))
        pg.draw.rect(self.ecran, cfg.BLANC, (x, y, bw, bh), u(2), border_radius=u(7))

    def aide_touches(self, schema, x, y, ancre, alpha):
        s = pg.Surface((u(640), u(56)), pg.SRCALPHA)
        cx = u(16)
        court = self.deux_joueurs                          # deux bandeaux côte à côte : textes courts
        for action, lib in (("gauche", ""), ("droite", "bouger" if court else "bouger (reculer = garde)"),
                            ("esquive", "esquive"), ("jab", ""), ("hook", ""),
                            ("up", "coups" if court else "jab · crochet · uppercut")):
            r = touche(s, etiquette(schema, action), (cx, s.get_height() / 2), 16, "midleft")
            cx = r.right + u(4)
            if lib:
                cx = texte(s, lib, 15, (215, 220, 235), (cx + u(4), s.get_height() / 2), "midleft", "normal",
                           ombre=False).right + u(16)
        fond = panneau(min(s.get_width(), cx), s.get_height(), 170, 16)
        fond.blit(s, (0, 0))
        s = fond
        s.set_alpha(alpha)
        r = s.get_rect(**{ancre: (x, y)})
        self.ecran.blit(s, r)

    def dessiner_annonce(self):
        titre, sous, coul, age = self.annonce
        alpha = int(255 * clamp((1.6 - age) / 0.3))
        texte(self.ecran, titre, 52, coul, (cfg.W / 2, u(178)), style="titre", alpha=alpha, contour=3,
              echelle=1 + 0.8 * (1 - clamp(age / 0.2)) ** 2)
        texte(self.ecran, sous, 22, cfg.BLANC, (cfg.W / 2, u(228)), alpha=alpha)

    def dessiner_intro(self):
        t = self.t_etat
        p1, p2 = self.combat.joueurs
        texte(self.ecran, f"{p1.nom}   VS   {p2.nom}", 26, cfg.BLANC, (cfg.W / 2, u(300)), alpha=int(255 * clamp(t * 3)))
        if t < 1.2:
            texte(self.ecran, "ROUND 1", 90, cfg.BLANC, (cfg.W / 2, u(220)), style="titre", contour=4,
                  echelle=0.6 + 0.4 * ease_out_back(t * 3), alpha=int(255 * clamp((1.2 - t) * 4)))
        else:
            texte(self.ecran, "FIGHT !", 100, cfg.OR, (cfg.W / 2, u(220)), style="titre", contour=4,
                  echelle=0.6 + 0.4 * ease_out_back((t - 1.2) * 3), alpha=int(255 * clamp((2.4 - t) * 3)))

    def dessiner_ko(self):
        t = self.t_etat
        if self.combat.raison == "ko":
            texte(self.ecran, "K.O. !", 120, cfg.ROUGE, (cfg.W / 2 + self.rng.uniform(-3, 3), u(220)), style="titre",
                  contour=5, echelle=(0.5 + 0.5 * ease_out_back(t * 2.5)) * (1 + 0.04 * math.sin(t * 12)))
        else:
            texte(self.ecran, "TEMPS !", 110, cfg.OR, (cfg.W / 2, u(220)), style="titre", contour=5,
                  echelle=0.5 + 0.5 * ease_out_back(t * 2.5))

    def dessiner_fin(self):
        W, H = cfg.W, cfg.H
        g = self.combat.gagnant
        k = ease_out_back((self.t_etat - 1.8) * 2.5)
        if k > 0:
            self.voile(int(90 * clamp(self.t_etat - 1.8)))
        titre = "ÉGALITÉ" if g is None else "VICTOIRE"
        texte(self.ecran, titre, 96, cfg.OR, (W / 2, u(96)), style="titre", contour=4,
              echelle=0.7 + 0.3 * ease_out_back(self.t_etat * 2))
        if g:
            texte(self.ecran, self.combat.joueur(g).nom.upper(), 30, cfg.BLANC, (W / 2, u(160)),
                  alpha=int(255 * clamp(self.t_etat * 2)))
        if k <= 0:
            return
        pw, ph = u(760), u(372)
        x, y = (W - pw) / 2, H - ph - u(30) + (1 - k) * H * 0.6
        self.ecran.blit(panneau(pw, ph, 225, 22, cfg.OR), (x, y))
        p1, p2 = self.combat.joueurs
        cols = (x + u(56), x + u(470), x + u(640))
        texte(self.ecran, "RÉCAPITULATIF", 22, cfg.OR, (W / 2, y + u(32)))
        lignes = [("", p1.nom, p2.nom),
                  ("Coups envoyés", p1.stats.envoyes, p2.stats.envoyes),
                  ("Coups touchés", p1.stats.touches, p2.stats.touches),
                  ("Précision", f"{p1.stats.precision:.0%}", f"{p2.stats.precision:.0%}"),
                  ("Dégâts infligés", p1.stats.degats, p2.stats.degats),
                  ("Coups bloqués", p1.stats.bloques, p2.stats.bloques),
                  ("Coups esquivés", p1.stats.esquives, p2.stats.esquives),
                  ("Meilleur combo", p1.stats.combo_max, p2.stats.combo_max)]
        for i, (lib, a, b) in enumerate(lignes):
            yy = y + u(76) + i * u(32)
            if i:
                pg.draw.line(self.ecran, (50, 55, 75), (x + u(36), yy - u(16)), (x + pw - u(36), yy - u(16)))
            texte(self.ecran, lib, 18, (200, 205, 222), (cols[0], yy), "midleft", "normal", ombre=False)
            for col, val, num in ((cols[1], a, 1), (cols[2], b, 2)):
                gagne = i == 0 and g == num
                texte(self.ecran, str(val), 20 if i == 0 else 18, cfg.OR if gagne else cfg.BLANC, (col, yy),
                      ombre=False)
        cx = W / 2 - u(170)
        r = touche(self.ecran, "Entrée", (cx, y + ph - u(34)), 15, "midleft")
        r = texte(self.ecran, "revanche", 17, cfg.BLANC, (r.right + u(10), r.centery), "midleft", "normal", False)
        r = touche(self.ecran, "Échap", (r.right + u(40), r.centery), 15, "midleft")
        texte(self.ecran, "menu principal", 17, cfg.BLANC, (r.right + u(10), r.centery), "midleft", "normal", False)

    # -- menus --------------------------------------------------------------------------------
    def dessiner_logo(self, y):
        t = self.temps
        r1 = texte(self.ecran, "PIXEL", 104, cfg.BLANC, (cfg.W / 2 - u(18), y), "midright", "titre", contour=5,
                   echelle=0.85 + 0.15 * ease_out_back(t * 2))
        texte(self.ecran, "PUNCH", 104, cfg.OR, (r1.right + u(18), y), "midleft", "titre", contour=5,
              echelle=0.85 + 0.15 * ease_out_back(t * 2 - 0.25))
        texte(self.ecran, "boxe en temps réel", 20, (225, 228, 240), (cfg.W / 2, y + u(66)), style="normal")

    def dessiner_menu(self):
        self.dessiner_logo(u(108))
        self.dessiner_liste(u(250))
        texte(self.ecran, "↑ ↓ choisir   ·   Entrée valider   ·   F11 plein écran / fenêtre   ·   Échap quitter", 15,
              (190, 195, 215), (cfg.W / 2, cfg.H - u(26)), style="normal", ombre=False)

    def dessiner_pause(self):
        self.voile(140)
        texte(self.ecran, "PAUSE", 80, cfg.BLANC, (cfg.W / 2, u(200)), style="titre", contour=4)
        self.dessiner_liste(u(300))

    def dessiner_liste(self, y0):
        elements = self.elements_menu()
        lw, lh = u(460), u(46)
        x = (cfg.W - lw) / 2
        self.zones = []
        for i, lib in enumerate(elements):
            r = pg.Rect(x, y0 + i * (lh + u(7)), lw, lh)
            self.zones.append((r, i))
            sel = i == self.choix
            if sel:
                pulse = 0.5 + 0.5 * math.sin(self.temps * 5)
                self.ecran.blit(panneau(lw, lh, 235, 14, melange(cfg.OR, cfg.BLANC, pulse * 0.3), 2), r)
                pg.draw.rect(self.ecran, cfg.OR, (r.x + u(14), r.centery - u(9), u(6), u(18)), border_radius=u(3))
            else:
                self.ecran.blit(panneau(lw, lh, 150, 14), r)
            en_edition = self.edition is not None and i == 3 + self.edition
            if en_edition:
                nom = self.noms[self.edition]
                lib = lib.split(":")[0] + ":   " + nom + ("|" if int(self.temps * 2) % 2 == 0 else " ")
            texte(self.ecran, lib, 22, cfg.OR if sel else cfg.BLANC, (r.x + u(34), r.centery), "midleft",
                  ombre=False)

    def dessiner_commandes(self):
        W = cfg.W
        texte(self.ecran, "COMMANDES", 64, cfg.BLANC, (W / 2, u(70)), style="titre", contour=4)
        pw, ph, gap = u(340), u(312), u(26)
        x0 = (W - 3 * pw - 2 * gap) / 2
        for k, (schema, titre, sous) in enumerate(((SOLO, "SOLO", "contre l'ordi"), (DUO_J1, "JOUEUR 1", "à 2 joueurs"),
                                                   (DUO_J2, "JOUEUR 2", "à 2 joueurs"))):
            x, y = x0 + k * (pw + gap), u(130)
            self.ecran.blit(panneau(pw, ph, 215, 20, cfg.OR if k == 0 else None), (x, y))
            texte(self.ecran, titre, 24, cfg.OR, (x + pw / 2, y + u(30)))
            texte(self.ecran, sous, 15, cfg.GRIS, (x + pw / 2, y + u(56)), style="normal", ombre=False)
            yy = y + u(98)
            for action in ("gauche", "esquive", "jab", "hook", "up"):
                r = touche(self.ecran, etiquette(schema, action), (x + u(30), yy), 18, "midleft")
                if action == "gauche":
                    touche(self.ecran, etiquette(schema, "droite"), (r.right + u(8), yy), 18, "midleft")
                texte(self.ecran, NOMS_ACTIONS[action], 19, cfg.BLANC, (x + u(130), yy), "midleft", "normal",
                      ombre=False)
                yy += u(43)
        regles = ["Recule pour te mettre en garde : elle bloque tout, mais laisse passer 1/4 des dégâts.",
                  "L'esquive évite le jab et le crochet... pas l'uppercut !",
                  "Frapper pendant que l'adversaire arme son coup = CONTRE (dégâts x1,5).",
                  "Chaque action fatigue : surveille ta barre d'endurance (bleue).",
                  "En solo, les flèches et Espace marchent aussi."]
        self.ecran.blit(panneau(u(860), u(170), 215, 20), (W / 2 - u(430), u(478)))
        for i, ligne in enumerate(regles):
            texte(self.ecran, ligne, 18, (220, 224, 238), (W / 2, u(500) + i * u(30)), style="normal", ombre=False)
        texte(self.ecran, "Échap ou Entrée pour revenir", 15, (180, 185, 205), (W / 2, cfg.H - u(26)),
              style="normal", ombre=False)

    # -- boucle principale ------------------------------------------------------------------
    async def run(self):
        """Boucle « async » pour pouvoir tourner dans le navigateur (pygbag).

        `await asyncio.sleep(0)` rend la main au navigateur à chaque image, sinon la page se fige.
        Sur PC, asyncio.run() lance cette boucle exactement comme avant.
        """
        while True:
            dt = min(self.horloge.tick(cfg.FPS) / 1000, 0.05)
            for e in pg.event.get():
                if not self.evenement(e):
                    pg.quit()
                    return
            self.maj(dt)
            self.clavier.nouvelle_image()
            self.dessiner()
            pg.display.flip()
            await asyncio.sleep(0)
