---
source_sha256 = "ff5767efc5809b0318c6e2f2fd02ec3852988a2906ba6bbc3e69b93d5a897245"
---
# DIM : une étagère de boîtes

Quand un programme a besoin de beaucoup de boîtes du même genre, une pour
chaque ami ou pour chaque jour, il peut en avoir toute une **étagère**,
avec un seul nom et un numéro pour chaque boîte. `DIM` fabrique
l'étagère :

```basic
10 DIM F(7)
20 FOR D = 1 TO 7
30 READ F(D)
40 NEXT D
50 PRINT "POISSONS LE JOUR 3 : "; F(3)
60 LET T = 0
70 FOR D = 1 TO 7
80 LET T = T + F(D)
90 NEXT D
100 PRINT "POISSONS DE LA SEMAINE : "; T
110 DATA 4, 6, 3, 8, 5, 9, 2
```

`F(3)` est la boîte numéro 3 de l'étagère `F`. Le nombre entre
parenthèses peut lui aussi être une boîte, comme `F(D)`, et c'est là toute
la magie : une seule boucle parcourt toute l'étagère.

![Une étagère de boîtes](boxes.svg)

## Une étagère de mots

```basic
10 DIM N$(4)
20 FOR I = 1 TO 4: READ N$(I): NEXT I
30 FOR I = 4 TO 1 STEP -1
40 PRINT N$(I)
50 NEXT I
60 DATA PIP, TOM, LULU, BEA
```

Il écrit les amis à l'envers. Un `FOR` avec son `NEXT` sur une seule
ligne, avec des deux-points, reste une boucle.

## Un tableau

Une étagère peut avoir des rangées et des colonnes, comme une armoire.
`DIM C(3, 4)` fabrique trois rangées de quatre boîtes ; `C(2, 3)`, c'est
la rangée 2, boîte 3. Ici, trois pingouins notent les poissons qu'ils
pêchent pendant quatre jours :

```basic
10 DIM C(3, 4)
20 FOR P = 1 TO 3
30 FOR D = 1 TO 4
40 READ C(P, D)
50 NEXT D
60 NEXT P
70 FOR P = 1 TO 3
80 LET T = 0
90 FOR D = 1 TO 4
100 LET T = T + C(P, D)
110 NEXT D
120 PRINT "LE PINGOUIN "; P; " A PECHE "; T
130 NEXT P
140 DATA 3, 5, 2, 4
150 DATA 6, 1, 4, 4
160 DATA 2, 2, 7, 5
```

> [cheer] Avec une étagère, un programme pour cent amis n'est pas plus long
> qu'un programme pour quatre.

## Continue d'essayer

- Quel a été le meilleur jour de pêche dans le premier programme ? Trouve
  le plus grand nombre de l'étagère.
- Dans le tableau, additionne les poissons de chaque jour pour les trois
  pingouins.

::: adult
`DIM` déclare un tableau ; les boîtes sont numérotées à partir de 0, même
si le guide les utilise à partir de 1. Ce BASIC permettrait d'utiliser une
étagère sans `DIM`, mais le guide l'écrit toujours : dire quelle taille a
l'étagère avant de s'en servir est une habitude que tous les langages
récompensent.
:::
