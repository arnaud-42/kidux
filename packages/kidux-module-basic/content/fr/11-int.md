---
source_sha256 = "4523565c511ab744df0dddb45e8e375208b55f48d9087c6c8764e5703a8a3fdd"
---
# INT : les nombres entiers

Partage 7 poissons entre 2 pingouins, et l'ordinateur dit 3.5. Mais un
poisson coupé en deux, ça n'arrange personne. `INT` garde la partie
entière d'un nombre et jette le reste.

```basic
10 PRINT 7 / 2
20 PRINT INT(7 / 2)
30 PRINT INT(9.99)
```

`INT` n'arrondit pas : 9.99 devient 9, pas 10.

> [point] L'ordinateur écrit les nombres à virgule avec un point, comme
> en anglais : 3.5 veut dire trois virgule cinq.

## Combien chacun, et combien il en reste

```basic keys=17,Enter,5,Enter
10 INPUT "COMBIEN DE POISSONS ? "; F
20 INPUT "COMBIEN DE PINGOUINS ? "; P
30 LET CHACUN = INT(F / P)
40 LET RESTE = F - CHACUN * P
50 PRINT "CHACUN EN RECOIT "; CHACUN
60 PRINT "ET IL EN RESTE "; RESTE
```

> [think] Pour arrondir au nombre entier le plus proche, ajoute d'abord
> une moitié : `INT(X + 0.5)`. Essaie avec 9.99 et avec 9.2.

## Continue d'essayer

- Un nombre est-il pair ? Il l'est quand `INT(N / 2) * 2 = N`. Écris un
  programme qui dit si un nombre est pair ou impair.
- Partage des bonbons entre des amis, et dis combien chacun en reçoit et
  combien il en reste.

::: adult
`INT` donne le nombre entier égal ou inférieur : `INT(-2.5)` vaut -3. Le
chapitre 12 en a besoin pour transformer le hasard en nombres entiers.
:::
