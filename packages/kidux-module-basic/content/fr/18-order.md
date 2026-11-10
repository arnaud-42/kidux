---
source_sha256 = "c68f879ec8f5d88ecebf132604e23fe4d2965ec9ac3e048b60a51b3ac3f3f31c"
---
# Ce que l'ordinateur fait d'abord

Combien font 2 + 3 × 4 ? Si on additionne d'abord, ça fait 20 ; si on
multiplie d'abord, ça fait 14. L'ordinateur fait toujours les choses dans
le même ordre :

1. ce qui est entre parenthèses, `(` et `)` ;
2. les puissances, `^` ;
3. `*` et `/`, de gauche à droite ;
4. `+` et `-`, de gauche à droite.

```basic
10 PRINT 2 + 3 * 4
20 PRINT (2 + 3) * 4
30 PRINT 10 - 4 - 3
40 PRINT 2 * 3 ^ 2
```

## La mauvaise monnaie

Pip achète 2 poissons à 4 pièces chacun et 3 coquillages à 1 pièce
chacun, et paie avec 20 pièces. Combien doit-on lui rendre ?

```basic
10 LET MONNAIE = 20 - 2 * 4 + 3 * 1
20 PRINT "MAUVAISE MONNAIE : "; MONNAIE
30 LET MONNAIE = 20 - (2 * 4 + 3 * 1)
40 PRINT "BONNE MONNAIE : "; MONNAIE
```

La ligne 10 enlève les poissons puis *ajoute* les coquillages : on
rendrait 15 pièces à Pip pour 11 pièces d'achats. Les parenthèses de la
ligne 30 font d'abord additionner les achats à l'ordinateur.

> [oops] Quand tu n'es pas sûr de ce que l'ordinateur fera d'abord, mets
> des parenthèses. Elles ne font jamais de mal.

## La moyenne

La moyenne de trois notes, c'est leur somme divisée par trois :

```basic
10 LET A = 7: LET B = 8: LET C = 9
20 PRINT "SANS PARENTHESES : "; A + B + C / 3
30 PRINT "AVEC PARENTHESES : "; (A + B + C) / 3
```

Deux-points, `:`, mettent deux instructions sur une seule ligne.

## Continue d'essayer

- Calcule 100 - 10 * 5 + 2 sur papier, puis demande à l'ordinateur.
- Écris un programme qui demande quatre notes et écrit leur moyenne.

::: adult
Ce sont les règles habituelles du calcul. Une erreur courante, ici comme
dans tous les langages, est la moyenne sans parenthèses ; une bonne
habitude est de mettre entre parenthèses toute somme qu'on divise.
:::
