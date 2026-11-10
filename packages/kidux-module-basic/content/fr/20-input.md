---
source_sha256 = "2340034df0e1f3f1a21d45ff99de8675fcded02d6a79c9ce532ef98c06032b80"
---
# INPUT, plus loin

`INPUT` peut poser une question et attendre une réponse en une seule
ligne, comme tu le fais depuis le chapitre 4. Il peut aussi prendre
plusieurs réponses à la fois : mets leurs boîtes après la question,
séparées par des virgules, et tape les réponses séparées par des virgules
elles aussi.

```basic keys=6,Comma,4,Enter
10 INPUT "LARGEUR ET LONGUEUR DU JARDIN ? "; W, L
20 PRINT "IL FAIT "; W * L; " METRES CARRES"
30 PRINT "ET UNE CLOTURE DE "; 2 * W + 2 * L; " METRES"
```

Pour répondre, tape `6,4` et appuie sur Entrée.

## Des mots et des nombres ensemble

```basic keys=PIP,Comma,7,Comma,POISSON,Enter
10 INPUT "PRENOM, AGE ET PLAT PREFERE ? "; N$, A, F$
20 PRINT N$; " A "; A; " ANS ET ADORE LE "; F$
```

> [point] Dis dans la question combien de réponses tu veux, et dans quel
> ordre. La personne qui tape ne voit pas ton programme.

## Une machine à histoires

```basic keys=PIP,Comma,DANSAIT,Comma,LA,Space,GLACE,Enter
10 PRINT "DONNE-MOI QUELQU'UN, UNE ACTION ET UN ENDROIT."
20 INPUT "SEPARE-LES PAR DES VIRGULES : "; W$, A$, P$
30 PRINT "IL ETAIT UNE FOIS "; W$; " QUI "; A$; " SUR "; P$; "."
40 PRINT "ET TOUT LE MONDE APPLAUDIT."
```

## Continue d'essayer

- Demande les trois côtés d'un triangle et écris la longueur du tour.
- Fais demander cinq mots à la machine à histoires, et raconter une
  histoire plus longue.

::: adult
Une virgule dans une réponse la sépare de la suivante : une réponse qui
contient une virgule ne peut donc pas être tapée de cette façon dans une
boîte à mots. Quand on tape moins de réponses que demandé, un nombre
manquant s'affiche `NaN`, *not a number*, « pas un nombre » ; c'est pour
ça que la question doit dire combien elle en veut.
:::
