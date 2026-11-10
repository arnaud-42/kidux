---
source_sha256 = "d52cd8c8ad5c2955e45a5762a2d5aa2f093d4753ad2557e7844f7ea79dc95555"
---
# CLS : un écran tout propre

`CLS` efface l'écran et recommence à écrire en haut. Il ne touche ni à
ton programme ni à ses boîtes : il efface seulement ce qui est affiché.

```basic
10 PRINT "CECI VA DISPARAITRE"
20 PRINT "ET CECI AUSSI"
30 CLS
40 PRINT "UN ECRAN TOUT PROPRE"
```

Un quiz est plus joli quand chaque question a l'écran pour elle toute
seule :

```basic keys=2,Enter,POISSON,Enter
10 CLS
20 PRINT "QUESTION 1"
30 INPUT "COMBIEN DE PATTES A UN PINGOUIN ? "; A
40 IF A = 2 THEN PRINT "JUSTE !" ELSE PRINT "IL EN A DEUX"
50 CLS
60 PRINT "QUESTION 2"
70 INPUT "QUE MANGE UN PINGOUIN ? "; F$
80 IF F$ = "POISSON" THEN PRINT "JUSTE !" ELSE PRINT "SURTOUT DU POISSON"
```

> [think] La réponse à la question 1 disparaît avant que tu puisses la
> lire. Saurais-tu faire attendre le programme ? Le chapitre 21 montre
> comment, et le chapitre 27 comment attendre une touche.

## Trois façons de repartir à zéro

- `CLS` efface l'**écran**. Le programme continue.
- Chaque **Lancer** commence avec des boîtes vides, comme l'a montré le
  chapitre 16.
- **Nouveau** efface l'**éditeur**, et le programme qui s'y trouvait
  disparaît. Il demande d'abord, pour que rien ne soit perdu par erreur.

## Continue d'essayer

- Ajoute une troisième question au quiz, sur son propre écran propre.
- Compte les bonnes réponses dans une boîte, et montre le score sur un
  écran propre à la fin.

::: adult
`CLS` est la première instruction de la plupart des programmes qui
utilisent l'écran comme une page plutôt que comme un rouleau de texte.
Ici, chaque lancement commence avec ses variables vides : un programme
n'a donc jamais besoin de les vider lui-même.
:::
