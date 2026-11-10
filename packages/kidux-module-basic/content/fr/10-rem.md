---
source_sha256 = "d89cc6366742446f78edbca7c8be0c79ab3b2edb8bb31e716b0f3277307ed123"
---
# REM : des notes pour soi

Un programme écrit la semaine dernière peut être difficile à comprendre
aujourd'hui. Les lignes `REM` sont des notes pour les humains :
l'ordinateur les saute.

```basic keys=4,Enter
10 REM LA POISSONNERIE
20 REM PAR MOI
30 LET PRIX = 3
40 INPUT "COMBIEN DE POISSONS ? "; N
50 REM CALCULER LE PRIX
60 PRINT "CA FAIT "; N * PRIX; " PIECES"
```

Une apostrophe, `'`, est un `REM` plus court, et elle peut aussi se
mettre au bout d'une ligne :

```basic
10 LET PRIX = 3 ' LE PRIX D'UN POISSON
20 ' UNE LIGNE ENTIERE DE NOTE
30 PRINT PRIX
```

> [point] Une bonne note dit *pourquoi*, pas seulement *quoi*. Toi, plus
> tard, tu seras content de la trouver.

## Continue d'essayer

- Ajoute des notes à ton quiz du chapitre 6.
- Écris en haut de chaque programme son nom et ce qu'il fait.

::: adult
Les notes sont une habitude qui vaut la peine d'être prise tôt. Un
programme lu à voix haute, notes comprises, est aussi une bonne façon
pour un enfant d'expliquer ce qu'il a fait.
:::
