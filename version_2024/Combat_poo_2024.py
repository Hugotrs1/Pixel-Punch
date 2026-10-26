import random as rd
from tkinter import *
from PIL import Image, ImageTk
import pygame
import os
import time

repertoire = os.path.dirname(os.path.abspath(__file__)) #variable associé avec celle du dessous qui permet de cherche automatiquement un fichier dans un dossier

affichage = os.path.join(repertoire)


class Personnage:
    def __init__(self, nom, nbreDeVie): #le nom et les pts de vie du personnage
        self.nom = nom
        self.vie = nbreDeVie

    def pvrestant(self): #ses pv restants
        return self.vie

    def jab(self): #Le jab qui inflique 10 de dégâts
        self.vie -= 10

    def uppercut(self): #L'uppercut qui inflige 30 de dégâts
        self.vie -= 30

    def hook(self): #Le crochet qui inflige 15 de dégâts
        self.vie -= 15

class Combat:
    def __init__(self, fenetre): #definition de la fenêtre
        self.fenetre = fenetre
        self.can = Canvas(self.fenetre, width=1000, height=680, bg='white')
        self.can.pack()
        self.photo = None

    def afficher(self, image_path): #affichage de la fenêtre à l'aide du chemin d'accès de l'image
        image = Image.open(image_path)
        self.photo = ImageTk.PhotoImage(image)
        self.can.delete("all") #supprime tous ce qu'il y a dans la fenêtre
        self.can.create_image(0, 0, anchor=NW, image=self.photo)
        fen.update() #actualise l'image


def son(file): #Fonction qui joue un son à l'aide de la bibliothèque pygame et du chemin d'accès du son
    pygame.mixer.init()
    pygame.mixer.music.load(file)
    pygame.mixer.music.play()



def recap(jp1, jesp1, up1, upes1, h1, hes1, jp2, jesp2, up2, upes2, h2, hes2): #Fonction qui renvoie un récap de la partie avec les coups infligés et esquivés
    print('Récapitulatif du combat :')
    print('------------------------------')
    print(perso1.nom ,':')
    print(f"Jabs envoyés : {jp1}\nJabs esquivés : {jesp1}\nUppercuts envoyés : {up1}\nUppercuts esquivés : {upes1}\nCrochets envoyés : {h1}\nCrochets esquivés : {hes1}")
    print('------------------------------')
    print(perso2.nom ,':')
    print(f"Jabs envoyés : {jp2}\nJabs esquivés : {jesp2}\nUppercuts envoyés : {up2}\nUppercuts esquivés : {upes2}\nCrochets envoyés : {h2}\nCrochets esquivés : {hes2}")
    print('------------------------------')

def combat():

    jp1, jesp1, up1, upes1, h1, hes1, jp2, jesp2, up2, upes2, h2, hes2 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 #On definit les variables des statistiques à 0
    while perso1.pvrestant() > 0 and perso2.pvrestant() > 0: #tant que les deux persos on encore des pv
        atckfrst = rd.randint(1, 2) #Choix random entre 1 et 2 pour connaître qui porte un coup à l'autre
        jabpro = rd.randint(1, 5) #choisi un nb entre 1 et 5 pour le jab
        hookproba = rd.randint(1, 7) #choisi un nb entre 1 et 7 pour le hook
        uppercutproba = rd.randint(1, 10) #choisi un nb entre 1 et 10 pour l'uppercut

        if atckfrst == 1: #Si le variable "atckfrst" est à 1 alrs le joueur 1 commence
            choixatt = input('Quel coup voulez vous envoyer ? jab, uppercut, hook ') #choix parmis les coups possibles
            if choixatt == 'jab':
                if jabpro > 2: #si le nombre de jabpro est supérieur à 2 soit 3,4 ou 5 alors le coup peut être porté
                    perso2.jab() #inflige les dégats
                    jp1+=1 #ajoute 1 au compteur de jab envoyés
                    print(perso1.nom, 'envoie un jab')
                    son(os.path.join(affichage, "Jab_sound.mp3")) #joue le son correspondant au jab
                    aff.afficher(os.path.join(affichage, "P1_jab_p2.png")) #puis affiche son image


                else: #Sinon le coup sera esquivé
                    jesp1+=1
                    print(perso1.nom, 'a raté son coup')
                    son(os.path.join(affichage, "esquive.mp3"))
                    aff.afficher(os.path.join(affichage, "P2_esj_p1.png"))


            if choixatt == 'uppercut':
                if uppercutproba > 8: #De même pour l'uppercut si le nombre est supérieur à 8 soit 9 ou 10
                    perso2.uppercut() #inflige les dégats
                    up1+=1 #ajoute 1 au compteur d'uppercuts envoyés
                    print(perso1.nom, 'décroche un uppercut')
                    son(os.path.join(affichage, "final_punch.mp3"))
                    aff.afficher(os.path.join(affichage, "P1_up_p2.png"))

                else: #sinon l'adversaire esquive
                    upes1+=1
                    print(perso1.nom, 'a raté son coup')
                    son(os.path.join(affichage, "esquive.mp3"))
                    aff.afficher(os.path.join(affichage, "P2_esu_p1.png"))

            if choixatt == 'hook': #même raisonnement pour le crochet seul la probabilité de porter le coup change
                if hookproba > 3:
                    perso2.hook()
                    h1+=1
                    print(perso1.nom, 'qui corrige', perso2.nom, 'avec un crochet')
                    son(os.path.join(affichage, "hook_sound.mp3"))
                    aff.afficher(os.path.join(affichage, "P1_hook_p2.png"))

                else:
                    hes1+=1
                    print(perso1.nom, 'a raté son coup')
                    son(os.path.join(affichage, "esquive.mp3"))
                    aff.afficher(os.path.join(affichage, "P2_esh_p1.png"))

        elif atckfrst == 2: #la totalité du raisonnement qui suit est la même seulement elle n'est pas contrôle pour l'utilisteur mais par l'ordinateur

            c = rd.randint(1, 3)
            if c == 1:
                if jabpro > 2:
                    perso1.jab()
                    jp2+=1
                    print(perso2.nom, 'envoie un jab')
                    son(os.path.join(affichage, "Jab_sound.mp3"))
                    aff.afficher(os.path.join(affichage, "P2_jab_p1.png"))

                else:
                    jesp2+=1
                    print(perso2.nom, 'a raté son coup')
                    son(os.path.join(affichage, "esquive.mp3"))
                    aff.afficher(os.path.join(affichage, "P1_esj_p2.png"))


            elif c == 2:
                if uppercutproba > 8:
                    perso1.uppercut()
                    up2+=1
                    print(perso2.nom, 'décroche un uppercut')
                    son(os.path.join(affichage, "final_punch.mp3"))
                    aff.afficher(os.path.join(affichage, "P2_up_p1.png"))
                    fen.after(2000,fen.update)
                else:
                    upes2+=1
                    print(perso2.nom, 'a raté son coup')
                    son(os.path.join(affichage, "esquive.mp3"))
                    aff.afficher(os.path.join(affichage, "P1_esu_p2.png"))


            elif c == 3:
                if hookproba > 3:
                    perso1.hook()
                    h2+=1
                    print(perso2.nom, 'qui corrige', perso1.nom, 'avec un crochet')
                    son(os.path.join(affichage, "hook_sound.mp3"))
                    aff.afficher(os.path.join(affichage, "P2_hook_p1.png"))

                else:
                    hes2+=1
                    print(perso2.nom, 'a raté son coup')
                    son(os.path.join(affichage, "esquive.mp3"))
                    aff.afficher(os.path.join(affichage, "P1_esh_p2.png"))



        time.sleep(1) #fait une pause de 1 sec
        print('-------------------------------') #affiche les pv restants des deux combattants
        print('PV de', perso1.nom, ':', perso1.pvrestant())
        print('PV de', perso2.nom, ':', perso2.pvrestant())
        print('-------------------------------')
        time.sleep(2)



    if perso2.pvrestant() <= 0: #si le perso2 n'a plus de pv
        print(perso1.nom, 'remporte le combat')
        recap(jp1, jesp1, up1, upes1, h1, hes1, jp2, jesp2, up2, upes2, h2, hes2) #affiche les stats
        fen.title(perso1.nom +' à gagné') #renome le titre de la fenêtre par le nom du gagnant + "à gagné"
        son(os.path.join(affichage, "final_punch.mp3")) #joue le son du coup final
        aff.afficher(os.path.join(affichage, "p1 KO p2.png")) #affiche l'image du KO
        time.sleep(2) #pause de 2
        son(os.path.join(affichage, "Bell.mp3")) #joue le son de la cloche de fin de combat
        aff.afficher(os.path.join(affichage, "p1_win.png")) #puis l'image associé
        time.sleep(10) #pause de 10sec
        fen.destroy() #fermeture de la fenêtre


    if perso1.pvrestant() <= 0: #même principe mais si le perso1 n'a plus de pv
        print(perso2.nom, 'remporte le combat')
        recap(jp1, jesp1, up1, upes1, h1, hes1, jp2, jesp2, up2, upes2, h2, hes2)
        fen.title(perso2.nom +' à gagné')
        son(os.path.join(affichage, "final_punch.mp3"))
        aff.afficher(os.path.join(affichage, "p2 KO p1.png"))
        time.sleep(2)
        son(os.path.join(affichage, "Bell.mp3"))
        aff.afficher(os.path.join(affichage, "p2_win.png"))
        time.sleep(10)
        fen.destroy()
    fen.mainloop()




nom_perso1 = input('Quel est votre nom ? ') #nom de l'utilisateur
nom_perso2 = input('Quel est le nom de l\'adversaire ? ') #nom de l'adversaire
perso1 = Personnage(nom_perso1, 75) #pv des deux personnages
perso2 = Personnage(nom_perso2, 75)
fen = Tk() #fenêtre de départ
fen.title('Combat Start')
aff = Combat(fen) #variable qui nous sert à afficher les images
aff.afficher(os.path.join(affichage,"Start.png"))
fen.after(4000,combat) # attend 4sec puis lance le combat

fen.mainloop() #permet de laisser la fenêtre active